"""
Tests for Finova AI — Phase 10: Tutor / Subject Sections & Domain Immutability.

Validates:
1. Domain assignment on creation for all tutor sections.
2. Domain immutability: sending messages to existing conversations NEVER mutates stored domain.
3. Authoritative stored domain: orchestrator receives stored domain, not caller override.
4. Domain filtering in list_conversations store and REST API.
5. Global safety remains strictly unbypassed inside tutor sections.
6. Tutor-biased direct routing to specialized agents.
7. Backward compatibility for general chat and unprovided domains.
"""

from unittest.mock import MagicMock
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.conversations.store import SQLiteConversationStore
import app.conversations.service as conv_service_mod
from app.router.orchestrator import CentralOrchestrator
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


def test_conversation_domain_assigned_on_creation():
    """Verify that creating a conversation assigns its domain from the tutor section."""
    service = conv_service_mod.conversation_service

    # Explicit creation with domain
    conv_deriv = service.create_conversation(user_id="usr_10", title="Derivatives Study", domain="derivatives")
    assert conv_deriv.domain == "derivatives"

    # Default domain is general
    conv_gen = service.create_conversation(user_id="usr_10", title="General Chat")
    assert conv_gen.domain == "general"


def test_first_send_turn_creates_conversation_with_specified_domain(monkeypatch):
    """Sending the first turn with a domain creates the conversation record in that domain."""
    mock_orchestrator = MagicMock()
    mock_orchestrator.ask.return_value = OrchestratorResponse(
        query="What is a call option?",
        answer="A call option gives the right to buy at strike price.",
        grounding_status="fully_grounded",
        citations=[],
        market_data=None,
        market_data_list=[],
        crypto_data=None,
        grounding_sources=["NSE Derivatives"],
        domain_detected="DERIVATIVES",
        sub_tasks=[
            SubTaskExecutionMetadata(
                task_id="task_1",
                domain="DERIVATIVES",
                intent="concept_explanation",
                status="success",
                latency_ms=80.0,
            )
        ],
        agent_name="Derivatives Tutor",
        disclaimer="Educational only.",
        model_used="qwen2.5:7b-instruct",
        latency_ms=80.0,
    )
    monkeypatch.setattr(conv_service_mod.conversation_service, "orchestrator", mock_orchestrator)

    res = conv_service_mod.conversation_service.send_turn(
        user_id="usr_deriv_user",
        query="What is a call option?",
        domain="derivatives",
    )

    assert res.conversation_id is not None
    detail = conv_service_mod.conversation_service.get_conversation_detail(res.conversation_id, "usr_deriv_user")
    assert detail.conversation.domain == "derivatives"

    # Check that orchestrator received domain_context="derivatives"
    mock_orchestrator.ask.assert_called_once()
    _, kwargs = mock_orchestrator.ask.call_args
    assert kwargs.get("domain_context") == "derivatives"


def test_conversation_domain_immutable_on_subsequent_turns(monkeypatch):
    """
    CRITICAL INVARIANT TEST:
    Rule 2 & 3: When sending a message to an EXISTING conversation, NEVER overwrite or mutate
    that conversation's stored domain based on current UI section. Stored domain is authoritative.
    """
    mock_orchestrator = MagicMock()
    mock_orchestrator.ask.return_value = OrchestratorResponse(
        query="Tell me more",
        answer="Here is more information.",
        grounding_status="fully_grounded",
        citations=[],
        market_data=None,
        market_data_list=[],
        crypto_data=None,
        grounding_sources=[],
        domain_detected="EQUITY",
        sub_tasks=[],
        agent_name="Equity Tutor",
        disclaimer="Educational only.",
        model_used="qwen2.5:7b-instruct",
        latency_ms=50.0,
    )
    monkeypatch.setattr(conv_service_mod.conversation_service, "orchestrator", mock_orchestrator)

    service = conv_service_mod.conversation_service

    # 1. Create conversation in EQUITY domain
    conv = service.create_conversation(user_id="usr_immut", title="Equity Analysis", domain="equity")
    conv_id = conv.conversation_id
    assert conv.domain == "equity"

    # 2. Turn 1
    service.send_turn(
        user_id="usr_immut",
        query="What is Reliance trading at?",
        conversation_id=conv_id,
        domain="equity",
    )

    # 3. Turn 2: Attempt to pass domain="crypto" (e.g. user switched tabs or UI sent different domain)
    service.send_turn(
        user_id="usr_immut",
        query="Can you compare it to something else?",
        conversation_id=conv_id,
        domain="crypto",  # Disagrees with stored domain!
    )

    # 4. Verify stored domain in database is STILL "equity" (never mutated!)
    stored_conv = service.verify_ownership(conv_id, "usr_immut")
    assert stored_conv.domain == "equity"

    # 5. Verify orchestrator received stored authoritative domain "equity", NOT "crypto"
    assert mock_orchestrator.ask.call_count == 2
    last_call_kwargs = mock_orchestrator.ask.call_args[1]
    assert last_call_kwargs.get("domain_context") == "equity"


def test_list_conversations_filter_by_domain():
    """Verify that list_conversations filters correctly by domain and is case-insensitive."""
    service = conv_service_mod.conversation_service
    user_id = "usr_multi_domain"

    # Create conversations in different domains
    c_eq1 = service.create_conversation(user_id=user_id, title="Equity 1", domain="equity")
    c_eq2 = service.create_conversation(user_id=user_id, title="Equity 2", domain="equity")
    c_der = service.create_conversation(user_id=user_id, title="Deriv 1", domain="derivatives")
    c_gen = service.create_conversation(user_id=user_id, title="General 1", domain="general")

    # Add a message to each so message_count is consistent
    for cid in [c_eq1.conversation_id, c_eq2.conversation_id, c_der.conversation_id, c_gen.conversation_id]:
        service.add_message(cid, user_id, "user", "Hello")

    # Filter equity
    eq_list = service.list_conversations(user_id=user_id, domain="equity")
    assert len(eq_list) == 2
    assert all(c.domain == "equity" for c in eq_list)

    # Filter with uppercase (case-insensitive)
    eq_list_upper = service.list_conversations(user_id=user_id, domain="EQUITY")
    assert len(eq_list_upper) == 2

    # Filter derivatives
    der_list = service.list_conversations(user_id=user_id, domain="derivatives")
    assert len(der_list) == 1
    assert der_list[0].title == "Deriv 1"

    # No filter returns all 4
    all_list = service.list_conversations(user_id=user_id)
    assert len(all_list) == 4


def test_global_safety_guardrail_unbypassed_in_tutor_section():
    """
    Even when in a specialized tutor section (e.g. DERIVATIVES), an advisory query
    MUST trigger Step 1 Global Safety advice refusal immediately.
    """
    orchestrator = CentralOrchestrator()

    # Unsafe advisory prompt
    unsafe_query = "Should I buy NIFTY 24000 call options for tomorrow's expiry?"
    resp = orchestrator.ask(
        query=unsafe_query,
        domain_context="derivatives",
    )

    # Must be filtered by deterministic guardrail
    assert resp.model_used == "deterministic_guardrail"
    assert "refusal" in resp.sub_tasks[0].intent.lower() or resp.sub_tasks[0].status == "filtered"
    assert "advice" in resp.answer.lower() or "educational" in resp.answer.lower()
    assert resp.disclaimer is not None


def test_tutor_biased_routing_to_specialized_agents():
    """Safe queries in a tutor section route directly to the designated agent without cross-domain confusion."""
    orchestrator = CentralOrchestrator()

    # Derivatives tutor routing
    deriv_resp = orchestrator.ask(
        query="Teach me what a long call option payoff is",
        domain_context="derivatives",
    )
    assert deriv_resp.domain_detected == "DERIVATIVES"
    assert "Derivatives Tutor" in deriv_resp.agent_name

    # Personal Finance tutor routing
    pf_resp = orchestrator.ask(
        query="Calculate SIP for 5000 per month for 10 years",
        domain_context="personal_finance",
    )
    assert pf_resp.domain_detected == "PERSONAL_FINANCE"


def test_rest_api_domain_filtering_and_immutability(monkeypatch):
    """Test full HTTP endpoints for domain filtering and immutability."""
    mock_orchestrator = MagicMock()
    mock_orchestrator.ask.return_value = OrchestratorResponse(
        query="Mock query",
        answer="Mock answer.",
        grounding_status="fully_grounded",
        citations=[],
        market_data=None,
        market_data_list=[],
        crypto_data=None,
        grounding_sources=[],
        domain_detected="CRYPTO",
        sub_tasks=[],
        agent_name="Crypto Tutor",
        disclaimer="Educational only.",
        model_used="mock_model",
        latency_ms=10.0,
    )
    monkeypatch.setattr(conv_service_mod.conversation_service, "orchestrator", mock_orchestrator)

    # 1. Turn 1 creates conversation in "crypto" domain
    res1 = client.post(
        "/conversations/send",
        json={
            "user_id": "usr_api_tutor",
            "query": "What is Bitcoin Proof of Work?",
            "domain": "crypto",
        },
    )
    assert res1.status_code == 200
    data1 = res1.json()
    conv_id = data1["conversation_id"]

    # Check conversation detail
    detail = client.get(f"/conversations/{conv_id}", params={"user_id": "usr_api_tutor"}).json()
    assert detail["conversation"]["domain"] == "crypto"

    # 2. Filter via GET /conversations?domain=crypto
    crypto_list = client.get("/conversations", params={"user_id": "usr_api_tutor", "domain": "crypto"}).json()
    assert len(crypto_list) >= 1
    assert crypto_list[0]["conversation_id"] == conv_id

    # Filter via GET /conversations?domain=equity (should be empty for this user)
    equity_list = client.get("/conversations", params={"user_id": "usr_api_tutor", "domain": "equity"}).json()
    assert len(equity_list) == 0

    # 3. Turn 2: Attempt to pass domain="equity" to existing conversation
    res2 = client.post(
        "/conversations/send",
        json={
            "user_id": "usr_api_tutor",
            "query": "How does it compare to fiat currency?",
            "conversation_id": conv_id,
            "domain": "equity",  # Should be ignored by server!
        },
    )
    assert res2.status_code == 200

    # 4. Confirm stored domain remains "crypto"
    detail2 = client.get(f"/conversations/{conv_id}", params={"user_id": "usr_api_tutor"}).json()
    assert detail2["conversation"]["domain"] == "crypto"
