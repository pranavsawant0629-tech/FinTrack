"""
Comprehensive unit and integration test suite for the Equity Agent (Phase 2).
Covers:
1. Safety guardrail rules: advisory intent, stock tips, guaranteed returns.
2. Conceptual false-positive protection for educational questions with 'buy'/'sell'.
3. Strict LLM bypass on low-confidence/out-of-corpus retrieval.
4. Citation integrity, index mapping, and stripping of invalid citations.
5. TradeWise response contract validation.
6. FastAPI POST /agents/equity/ask endpoint integration.
7. Live end-to-end grounded query execution.
"""

from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.agents.equity.safety import equity_safety_guardrail, SAFETY_REFUSAL_MESSAGE
from app.agents.equity.prompts import UNGROUNDED_TOPIC_MESSAGE, build_equity_prompt, format_context_passages
from app.agents.equity.agent import EquityAgent, EQUITY_DISCLAIMER, equity_agent
from app.rag.service import RAGService, Citation, RAGAnswer
from app.rag.retriever import RetrievedChunk, RetrievalResponse

client = TestClient(app)


# =====================================================================
# 1. Safety Guardrail: Unsafe Advisory & Guaranteed Return Queries
# =====================================================================
@pytest.mark.parametrize(
    "query",
    [
        "Which stock should I buy today?",
        "Should I buy Reliance?",
        "Should I sell Tata Motors?",
        "Tell me what stock to buy",
        "Give me stock tips / intraday calls",
        "Suggest best stocks to buy now",
        "Can you guarantee 20% returns?",
        "How to double my money fast?",
        "I want 100% risk-free profit in shares",
        "Give me multibagger picks for quick gains",
    ],
)
def test_safety_blocks_unsafe_queries(query: str):
    result = equity_safety_guardrail.evaluate(query)
    assert not result.is_safe, f"Expected unsafe query to be blocked: '{query}'"
    assert result.refusal_message == SAFETY_REFUSAL_MESSAGE
    assert result.refusal_reason in ("personalized_advisory_intent", "guaranteed_returns_inquiry")


# =====================================================================
# 2. Safety Guardrail: False-Positive Protection for Conceptual Queries
# =====================================================================
@pytest.mark.parametrize(
    "query",
    [
        "What happens when I buy a share?",
        "How does a stock exchange execute a sell order?",
        "What does buying a stock mean?",
        "Explain the difference between buying and selling shares.",
        "What factors do investors study before deciding whether to buy a stock?",
        "What is an IPO?",
        "How do I lodge a complaint on SCORES?",
        "Explain how market orders work.",
        "What are corporate actions like bonus shares?",
    ],
)
def test_safety_allows_conceptual_queries(query: str):
    result = equity_safety_guardrail.evaluate(query)
    assert result.is_safe, f"Conceptual query was incorrectly blocked: '{query}'"
    assert result.refusal_message is None


@pytest.mark.parametrize(
    "query",
    [
        "should I buy shares before the dividend record date?",
        "should I hold my mutual funds during a market dip?",
    ],
)
def test_safety_allows_required_timing_and_dip_conceptual_queries(query: str):
    result = equity_safety_guardrail.evaluate(query)
    assert result.is_safe, f"Conceptual query was incorrectly blocked: '{query}'"
    assert result.refusal_message is None


# =====================================================================
# 3. Strict LLM Bypass on Low-Confidence / Out-of-Corpus Queries
# =====================================================================
def test_rag_service_bypasses_llm_when_no_chunks_found():
    mock_retriever = MagicMock()
    mock_retriever.retrieve.return_value = RetrievalResponse(query="crypto moon", total_results=0, chunks=[])
    mock_llm = MagicMock()
    mock_llm.model = "qwen2.5:7b-instruct"

    service = RAGService(retriever=mock_retriever, llm=mock_llm)
    ans = service.generate_answer("crypto moon")

    assert ans.grounding_status == "ungrounded"
    assert ans.answer == UNGROUNDED_TOPIC_MESSAGE
    assert ans.citations == []
    # Verify strict bypass: LLM was never called
    assert mock_llm.chat.call_count == 0


def test_equity_agent_bypasses_rag_and_llm_on_unsafe_query():
    mock_safety = MagicMock()
    mock_safety.evaluate.return_value = MagicMock(
        is_safe=False,
        refusal_message=SAFETY_REFUSAL_MESSAGE,
        refusal_reason="personalized_advisory_intent",
    )
    mock_rag = MagicMock()

    agent = EquityAgent(safety=mock_safety, rag=mock_rag)
    res = agent.ask("Should I buy Reliance?")

    assert res.grounding_status == "ungrounded"
    assert res.answer == SAFETY_REFUSAL_MESSAGE
    assert res.citations == []
    assert res.agent_name == "Equity Tutor"
    assert res.disclaimer == EQUITY_DISCLAIMER
    # Verify RAG service was NEVER called
    assert mock_rag.generate_answer.call_count == 0


# =====================================================================
# 4. Citation Integrity & Invalid Citation Stripping
# =====================================================================
def test_citation_integrity_and_hallucination_stripping():
    chunk1 = RetrievedChunk(
        chunk_id="igr_chunk_1",
        doc_id="igrbrochure",
        chunk_index=1,
        text="SCORES is a web-based centralized grievance redressal system.",
        score=0.88,
        source="SEBI",
        authority_level="Tier 1",
        url="https://investor.sebi.gov.in/pdf/reference-material/igrbrochure.pdf",
        page_numbers=[2, 3],
        metadata={"title": "Investor Grievance Redressal Mechanism & SCORES"},
    )
    chunk2 = RetrievedChunk(
        chunk_id="igr_chunk_2",
        doc_id="igrbrochure",
        chunk_index=2,
        text="Investors can lodge complaints online at scores.gov.in.",
        score=0.82,
        source="SEBI",
        authority_level="Tier 1",
        url="https://investor.sebi.gov.in/pdf/reference-material/igrbrochure.pdf",
        page_numbers=[4],
        metadata={"title": "Investor Grievance Redressal Mechanism & SCORES"},
    )

    mock_retriever = MagicMock()
    mock_retriever.retrieve.return_value = RetrievalResponse(
        query="What is SCORES?", total_results=2, chunks=[chunk1, chunk2]
    )
    mock_llm = MagicMock()
    mock_llm.model = "qwen2.5:7b-instruct"
    # LLM output references valid [1], [2] and an invalid hallucinated [9]
    mock_llm.chat.return_value = (
        "SCORES is a centralized grievance redressal system [1]. "
        "Complaints can be submitted online [2]. External fake claim [9]."
    )

    service = RAGService(retriever=mock_retriever, llm=mock_llm)
    ans = service.generate_answer("What is SCORES?")

    assert ans.grounding_status == "partially_grounded"
    assert len(ans.citations) == 2

    # Verify citation mapping
    cit1 = ans.citations[0]
    assert cit1.citation_id == 1
    assert cit1.chunk_id == "igr_chunk_1"
    assert cit1.doc_id == "igrbrochure"
    assert cit1.source == "SEBI"
    assert cit1.authority_level == "Tier 1"
    assert cit1.page_numbers == [2, 3]

    cit2 = ans.citations[1]
    assert cit2.citation_id == 2
    assert cit2.chunk_id == "igr_chunk_2"
    assert cit2.doc_id == "igrbrochure"

    # Verify hallucinated marker [9] was stripped from answer text
    assert "[9]" not in ans.answer
    assert "[1]" in ans.answer
    assert "[2]" in ans.answer


# =====================================================================
# 5. FastAPI Endpoint Integration: POST /agents/equity/ask
# =====================================================================
def test_api_equity_ask_blocked_by_safety():
    response = client.post(
        "/agents/equity/ask",
        json={"query": "Which stock should I buy today?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "Which stock should I buy today?"
    assert data["grounding_status"] == "ungrounded"
    assert data["citations"] == []
    assert data["agent_name"] == "Equity Tutor"
    assert data["disclaimer"] == EQUITY_DISCLAIMER
    assert "cannot provide personalized stock recommendations" in data["answer"]
    assert data["latency_ms"] >= 0


def test_api_equity_ask_out_of_corpus():
    # Force out-of-corpus query using a very high threshold
    response = client.post(
        "/agents/equity/ask",
        json={
            "query": "What is the nuclear physics reaction in a thorium reactor?",
            "score_threshold": 0.95,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["grounding_status"] == "ungrounded"
    assert data["citations"] == []
    assert data["agent_name"] == "Equity Tutor"
    assert "does not currently contain verified documents" in data["answer"]


def is_ollama_online() -> bool:
    """Helper to detect whether local Ollama daemon is reachable."""
    import httpx
    try:
        r = httpx.get("http://127.0.0.1:11434/api/tags", timeout=1.5)
        return r.status_code == 200
    except Exception:
        return False


def test_api_equity_ask_grounded_live():
    """
    Hermetic-safe integration test with indexed Qdrant vector store.
    If local Ollama is active, runs live end-to-end against Qwen.
    If Ollama is offline, falls back to a deterministic LLM mock so the suite remains
    fully automated and hermetic without weakening any grounding or provenance assertions.
    """
    if is_ollama_online():
        response = client.post(
            "/agents/equity/ask",
            json={"query": "How do I lodge a complaint in SCORES?"},
        )
    else:
        with patch("app.rag.service.llm_client.chat") as mock_chat:
            mock_chat.return_value = (
                "To lodge a complaint on SCORES, first approach the listed entity [1]. "
                "If unresolved, register on the SCORES portal with your PAN and details [1]."
            )
            response = client.post(
                "/agents/equity/ask",
                json={"query": "How do I lodge a complaint in SCORES?"},
            )

    assert response.status_code == 200
    data = response.json()
    assert data["query"] == "How do I lodge a complaint in SCORES?"
    assert data["grounding_status"] == "fully_grounded"
    assert len(data["citations"]) > 0
    # Provenance verification
    first_citation = data["citations"][0]
    assert first_citation["doc_id"] == "igrbrochure"
    assert first_citation["source"] == "SEBI"
    assert first_citation["authority_level"] == "Tier 1"
    assert "scores" in first_citation["url"].lower() or "sebi" in first_citation["url"].lower()
    assert data["agent_name"] == "Equity Tutor"
    assert data["disclaimer"] == EQUITY_DISCLAIMER
    assert len(data["answer"]) > 20
    assert data["latency_ms"] >= 0
    assert data["grounding_sources"] == ["sebi_rag"]
    assert data["market_data"] is None


def test_api_equity_ask_grounded_explicit_live():
    """Explicit opt-in live test requiring active Ollama daemon."""
    if not is_ollama_online():
        pytest.skip("Ollama daemon is not running locally.")
    response = client.post(
        "/agents/equity/ask",
        json={"query": "How do I lodge a complaint in SCORES?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["grounding_status"] == "fully_grounded"
    assert len(data["citations"]) > 0



# =====================================================================
# 6. Market Data Tools Integration Tests
# =====================================================================
def test_equity_agent_market_quote_live():
    """Verify live market quote routing with provenance and backward-compatible grounding."""
    res = equity_agent.ask("What is the current price of Reliance?")
    assert res.grounding_status == "fully_grounded"
    assert res.grounding_sources == ["live_market_data"]
    assert res.market_data is not None
    assert res.market_data.symbol == "RELIANCE"
    assert res.market_data.currency == "INR"
    assert res.market_data.price > 0.0
    assert res.market_data.provider == "Yahoo Finance"
    assert "RELIANCE" in res.answer
    assert "₹" in res.answer


def test_equity_agent_market_status():
    """Verify market status query returns trading session details."""
    res = equity_agent.ask("Is the stock market open today?")
    assert res.grounding_status == "fully_grounded"
    assert res.grounding_sources == ["live_market_data"]
    assert "stock market (NSE) is currently" in res.answer
    assert "Regular Trading Hours" in res.answer


def test_api_equity_ask_market_quote():
    """Verify API endpoint returns market_data payload and grounding_sources."""
    response = client.post(
        "/agents/equity/ask",
        json={"query": "Current price of TCS"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["grounding_status"] == "fully_grounded"
    assert data["grounding_sources"] == ["live_market_data"]
    assert data["market_data"] is not None
    assert data["market_data"]["symbol"] == "TCS"
    assert data["market_data"]["price"] > 0
    assert "TCS" in data["answer"]


def test_equity_agent_hybrid_query_signals_unserved_branch():
    """Verify that a hybrid multi-part query includes an explicit note about the unserved concept."""
    res = equity_agent.ask("What is an IPO and what is Reliance trading at?")
    assert res.grounding_status == "fully_grounded"
    assert res.grounding_sources == ["live_market_data"]
    assert res.market_data is not None
    assert "RELIANCE" in res.answer
    assert "Note:" in res.answer
    assert "ask me separately about what IPO is" in res.answer

