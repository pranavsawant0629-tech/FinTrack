"""
Integration tests for conversation turn flow, bounded history continuation, and failure handling.
"""

from unittest.mock import MagicMock
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.conversations.store import SQLiteConversationStore
import app.conversations.service as conv_service_mod
from app.router.models import OrchestratorResponse, SubTaskExecutionMetadata

client = TestClient(app)


@pytest.fixture(autouse=True)
def isolated_conversation_store(monkeypatch):
    """Use an isolated in-memory SQLite store for each test."""
    test_store = SQLiteConversationStore(db_path=":memory:")
    monkeypatch.setattr(conv_service_mod, "conversation_store", test_store)
    monkeypatch.setattr(conv_service_mod.conversation_service, "store", test_store)
    yield test_store
    test_store.close()


def test_send_first_message_creates_conversation_and_persists_turns(monkeypatch):
    """
    Test sending the initial message without a conversation_id:
    - Automatically creates a conversation with a deterministic title.
    - Persists user message.
    - Calls orchestrator.
    - Persists assistant response with metadata.
    """
    mock_orchestrator = MagicMock()
    mock_resp = OrchestratorResponse(
        query="What is a call option?",
        answer="A call option gives the buyer the right to buy an underlying stock at a specified strike price.",
        grounding_status="fully_grounded",
        citations=[],
        market_data=None,
        market_data_list=[],
        crypto_data=None,
        grounding_sources=["NSE Derivatives Manual"],
        domain_detected="DERIVATIVES",
        sub_tasks=[
            SubTaskExecutionMetadata(
                task_id="task_1",
                domain="DERIVATIVES",
                intent="concept_explanation",
                status="success",
                latency_ms=120.0,
            )
        ],
        agent_name="Derivatives Tutor",
        disclaimer="Finova AI is educational.",
        model_used="qwen2.5:7b-instruct",
        latency_ms=120.0,
    )
    mock_orchestrator.ask.return_value = mock_resp
    monkeypatch.setattr(conv_service_mod.conversation_service, "orchestrator", mock_orchestrator)

    # 1. Send first message
    turn_res = client.post(
        "/conversations/send",
        json={
            "user_id": "usr_trader",
            "query": "What is a call option?",
            "conversation_id": None,
        },
    )
    assert turn_res.status_code == 200
    data = turn_res.json()
    conv_id = data["conversation_id"]
    assert conv_id.startswith("conv_")
    assert data["user_message"]["content"] == "What is a call option?"
    assert data["user_message"]["status"] == "complete"
    assert data["assistant_message"]["status"] == "complete"
    assert "right to buy" in data["assistant_message"]["content"]
    
    # Verify metadata cleanliness and versioning
    meta = data["assistant_message"]["metadata"]
    assert meta["schema_version"] == 1
    assert meta["agent_name"] == "Derivatives Tutor"
    assert meta["domain_detected"] == "DERIVATIVES"
    assert meta["grounding_status"] == "fully_grounded"
    assert "sub_tasks" in meta
    assert "citations" in meta
    assert meta["latency_ms"] == 120.0
    assert meta["model_used"] == "qwen2.5:7b-instruct"

    # Redundant text fields MUST be absent from metadata
    assert "query" not in meta
    assert "answer" not in meta
    assert "disclaimer" not in meta

    # Verify conversation title generated deterministically
    conv_detail = client.get(f"/conversations/{conv_id}", params={"user_id": "usr_trader"}).json()
    assert conv_detail["conversation"]["title"].startswith("What is a call option")
    assert len(conv_detail["messages"]) == 2


def test_conversation_continuation_supplies_preceding_bounded_history(monkeypatch):
    """
    Test continuing an existing conversation:
    - Follow-up query supplies the preceding conversation history to the orchestrator.
    - Continues under the same conversation_id.
    """
    mock_orchestrator = MagicMock()
    mock_resp1 = OrchestratorResponse(
        query="What is a call option?",
        answer="Call option explanation.",
        grounding_status="ungrounded",
        citations=[],
        market_data=None,
        market_data_list=[],
        crypto_data=None,
        grounding_sources=[],
        domain_detected="DERIVATIVES",
        sub_tasks=[],
        agent_name="Derivatives Tutor",
        disclaimer="Disclaimer",
        model_used="qwen2.5:7b-instruct",
        latency_ms=50.0,
    )
    mock_resp2 = OrchestratorResponse(
        query="What about the breakeven?",
        answer="Breakeven is Strike Price + Premium Paid.",
        grounding_status="ungrounded",
        citations=[],
        market_data=None,
        market_data_list=[],
        crypto_data=None,
        grounding_sources=[],
        domain_detected="DERIVATIVES",
        sub_tasks=[],
        agent_name="Derivatives Tutor",
        disclaimer="Disclaimer",
        model_used="qwen2.5:7b-instruct",
        latency_ms=50.0,
    )
    mock_orchestrator.ask.side_effect = [mock_resp1, mock_resp2]
    monkeypatch.setattr(conv_service_mod.conversation_service, "orchestrator", mock_orchestrator)

    # First turn
    res1 = client.post(
        "/conversations/send",
        json={"user_id": "usr_continuer", "query": "What is a call option?"},
    )
    conv_id = res1.json()["conversation_id"]

    # In turn 1, preceding conversation_history passed to ask was empty
    assert mock_orchestrator.ask.call_args_list[0].kwargs["conversation_history"] == []

    # Second turn (follow-up) using the same conversation_id
    res2 = client.post(
        "/conversations/send",
        json={
            "user_id": "usr_continuer",
            "conversation_id": conv_id,
            "query": "What about the breakeven?",
        },
    )
    assert res2.status_code == 200
    assert res2.json()["conversation_id"] == conv_id

    # In turn 2, preceding conversation_history passed to ask MUST contain turn 1!
    history_passed = mock_orchestrator.ask.call_args_list[1].kwargs["conversation_history"]
    assert len(history_passed) == 2
    assert history_passed[0] == {"role": "user", "content": "What is a call option?"}
    assert history_passed[1] == {"role": "assistant", "content": "Call option explanation."}

    # Verify conversation has 4 messages in DB
    conv_detail = client.get(f"/conversations/{conv_id}", params={"user_id": "usr_continuer"}).json()
    assert len(conv_detail["messages"]) == 4


def test_failure_handling_mid_turn_and_subsequent_recovery(monkeypatch):
    """
    CRITICAL RELIABILITY TEST (Section 6a):
    - When orchestrator fails mid-turn:
      - User message is preserved with status='complete' (NOT orphaned).
      - Assistant message is persisted with status='failed'.
      - Conversation remains completely intact and continuable.
      - Next turn on the same conversation succeeds.
    """
    mock_orchestrator = MagicMock()
    # First turn fails (e.g. Ollama connection timeout)
    mock_orchestrator.ask.side_effect = [
        RuntimeError("Ollama connection failed: Connection refused"),
        OrchestratorResponse(
            query="Let me retry: What is SIP?",
            answer="SIP stands for Systematic Investment Plan.",
            grounding_status="ungrounded",
            citations=[],
            market_data=None,
            market_data_list=[],
            crypto_data=None,
            grounding_sources=[],
            domain_detected="PERSONAL_FINANCE",
            sub_tasks=[],
            agent_name="Personal Finance Tutor",
            disclaimer="Disclaimer",
            model_used="qwen2.5:7b-instruct",
            latency_ms=80.0,
        ),
    ]
    monkeypatch.setattr(conv_service_mod.conversation_service, "orchestrator", mock_orchestrator)

    # Turn 1: Attempt to send
    res1 = client.post(
        "/conversations/send",
        json={"user_id": "usr_resilient", "query": "What is SIP?"},
    )
    assert res1.status_code == 200
    data1 = res1.json()
    conv_id = data1["conversation_id"]

    # User message was preserved!
    assert data1["user_message"]["content"] == "What is SIP?"
    assert data1["user_message"]["status"] == "complete"

    # Assistant turn has status='failed' with versioned metadata
    assert data1["assistant_message"]["status"] == "failed"
    assert "temporary issue" in data1["assistant_message"]["content"]
    failed_meta = data1["assistant_message"]["metadata"]
    assert failed_meta["schema_version"] == 1
    assert failed_meta["failed"] is True
    assert "Ollama connection failed" in failed_meta["error"]
    assert "query" not in failed_meta
    assert "answer" not in failed_meta
    assert "disclaimer" not in failed_meta

    # Conversation still exists in database and has both user message and failed message
    conv_detail = client.get(f"/conversations/{conv_id}", params={"user_id": "usr_resilient"}).json()
    assert len(conv_detail["messages"]) == 2
    assert conv_detail["messages"][0]["status"] == "complete"
    assert conv_detail["messages"][1]["status"] == "failed"
    assert conv_detail["messages"][1]["metadata"]["schema_version"] == 1

    # Turn 2: User retries or asks follow-up on the SAME conversation
    res2 = client.post(
        "/conversations/send",
        json={
            "user_id": "usr_resilient",
            "conversation_id": conv_id,
            "query": "Let me retry: What is SIP?",
        },
    )
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["conversation_id"] == conv_id
    assert data2["assistant_message"]["status"] == "complete"
    assert "Systematic Investment Plan" in data2["assistant_message"]["content"]

    # Ensure failed assistant turn was NOT passed in bounded history for turn 2
    history_passed = mock_orchestrator.ask.call_args_list[1].kwargs["conversation_history"]
    # Only completed messages can be in history
    assert all(h["role"] != "assistant" or "temporary issue" not in h["content"] for h in history_passed)


def test_metadata_persistence_cleanliness_and_reconstruction(monkeypatch):
    """
    Test that:
    1. All 16 required UI reconstruction fields survive persistence in metadata.
    2. schema_version == 1 is present.
    3. Redundant text fields (query, answer, disclaimer) are NEVER stored in metadata.
    4. Upon fetching via GET /conversations/{id}, all cards/telemetry fields are intact.
    """
    mock_orchestrator = MagicMock()
    mock_resp = OrchestratorResponse(
        query="Compare Reliance and TCS and show portfolio simulation",
        answer="Here is the comparative equity analysis and stress test.",
        grounding_status="fully_grounded",
        citations=[
            {
                "citation_id": 1,
                "chunk_id": "chk_101",
                "doc_id": "doc_nse",
                "title": "NSE Market Bulletin",
                "source": "NSE",
                "authority_level": "STATUTORY",
                "url": "https://nseindia.com",
                "page_numbers": [1],
                "similarity_score": 0.95,
            }
        ],
        market_data={
            "symbol": "RELIANCE",
            "company_name": "Reliance Industries Ltd",
            "exchange": "NSE",
            "currency": "INR",
            "price": 2980.5,
            "change": 15.2,
            "change_percent": 0.51,
            "market_status": "regular_trading",
            "market_timestamp": "2026-09-12T15:30:00Z",
            "retrieved_at": "2026-09-12T15:30:05Z",
            "provider": "MockProvider",
            "source_url": "https://nseindia.com",
            "freshness_status": "realtime",
        },
        market_data_list=[
            {
                "symbol": "RELIANCE",
                "company_name": "Reliance Industries Ltd",
                "exchange": "NSE",
                "currency": "INR",
                "price": 2980.5,
                "change": 15.2,
                "change_percent": 0.51,
                "market_status": "regular_trading",
                "market_timestamp": "2026-09-12T15:30:00Z",
                "retrieved_at": "2026-09-12T15:30:05Z",
                "provider": "MockProvider",
                "source_url": "https://nseindia.com",
                "freshness_status": "realtime",
            },
            {
                "symbol": "TCS",
                "company_name": "Tata Consultancy Services",
                "exchange": "NSE",
                "currency": "INR",
                "price": 4120.0,
                "change": -10.0,
                "change_percent": -0.24,
                "market_status": "regular_trading",
                "market_timestamp": "2026-09-12T15:30:00Z",
                "retrieved_at": "2026-09-12T15:30:05Z",
                "provider": "MockProvider",
                "source_url": "https://nseindia.com",
                "freshness_status": "realtime",
            },
        ],
        crypto_data={"symbol": "BTC", "price_inr": 5500000},
        derivatives_data={"strike": 22000, "breakeven": 22150},
        portfolio_data={"total_value": 1500000, "simulated_drawdown": -150000},
        news_data=[{"headline": "Market Closes Higher", "source": "Reuters"}],
        quiz_data={"question_id": "q1", "text": "What is P/E?"},
        onboarding_data=[{"capability": "Market Quotes"}],
        grounding_sources=["NSE Realtime Data"],
        domain_detected="EQUITY",
        sub_tasks=[
            SubTaskExecutionMetadata(
                task_id="task_1",
                domain="EQUITY",
                intent="market_snapshot",
                status="success",
                latency_ms=150.0,
            )
        ],
        agent_name="Equity Tutor",
        disclaimer="Standard disclaimer text that should not be stored in metadata.",
        model_used="qwen2.5:7b-instruct",
        latency_ms=210.5,
    )
    mock_orchestrator.ask.return_value = mock_resp
    monkeypatch.setattr(conv_service_mod.conversation_service, "orchestrator", mock_orchestrator)

    res = client.post(
        "/conversations/send",
        json={
            "user_id": "usr_audit",
            "query": "Compare Reliance and TCS and show portfolio simulation",
        },
    )
    assert res.status_code == 200
    conv_id = res.json()["conversation_id"]

    # Retrieve persisted conversation details
    detail = client.get(f"/conversations/{conv_id}", params={"user_id": "usr_audit"}).json()
    assert len(detail["messages"]) == 2
    assistant_msg = detail["messages"][1]
    meta = assistant_msg["metadata"]

    # 1. Schema version present
    assert meta["schema_version"] == 1

    # 2. Redundant fields MUST NOT exist in metadata
    assert "query" not in meta
    assert "answer" not in meta
    assert "disclaimer" not in meta

    # 3. All 16 required UI reconstruction fields MUST exist and survive persistence
    assert meta["grounding_status"] == "fully_grounded"
    assert len(meta["citations"]) == 1
    assert meta["citations"][0]["chunk_id"] == "chk_101"
    assert meta["market_data"]["symbol"] == "RELIANCE"
    assert len(meta["market_data_list"]) == 2
    assert meta["crypto_data"]["symbol"] == "BTC"
    assert meta["derivatives_data"]["strike"] == 22000
    assert meta["portfolio_data"]["total_value"] == 1500000
    assert len(meta["news_data"]) == 1
    assert meta["quiz_data"]["question_id"] == "q1"
    assert meta["onboarding_data"][0]["capability"] == "Market Quotes"
    assert meta["grounding_sources"] == ["NSE Realtime Data"]
    assert meta["domain_detected"] == "EQUITY"
    assert len(meta["sub_tasks"]) == 1
    assert meta["agent_name"] == "Equity Tutor"
    assert meta["model_used"] == "qwen2.5:7b-instruct"
    assert meta["latency_ms"] == 210.5
