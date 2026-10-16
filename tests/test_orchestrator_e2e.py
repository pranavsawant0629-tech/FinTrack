"""
End-to-end and regression test suite for Finova AI Phase 4:
Central Orchestrator, Multi-Intent Routing, Crypto Agent, Personal Finance Agent, and API Contracts.

Covers:
1. Global Safety Pre-Filter on API endpoints (/orchestrator/ask, /chat, /agents/crypto/ask, /agents/personal-finance/ask)
2. Single-intent fast paths across all domains
3. Archetype C (Concept + Live Market Data) compound queries
4. Multi-company comparative market quote queries
5. Cross-domain compound queries (Equity + Personal Finance, Equity + Crypto)
6. Dedicated domain endpoints (/agents/crypto/ask, /agents/personal-finance/ask)
7. Phase 2/3 backward compatibility on legacy /agents/equity/ask
8. Numerical output preservation: numbers originate from deterministic tools without modification
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from app.main import app
from app.router.models import OrchestratorResponse
from app.rag.service import Citation, RAGAnswer

client = TestClient(app)


# =====================================================================
# 1. Global Safety Pre-Filtering Endpoints
# =====================================================================

@pytest.mark.parametrize(
    "query,expected_domain",
    [
        ("Which stock should I buy for guaranteed returns?", "EQUITY"),
        ("Which meme coin will 100x this week?", "CRYPTO"),
        ("Tell me how to allocate my exact 10 lakh portfolio", "PERSONAL_FINANCE"),
        ("Give me 100% risk free guaranteed profit", "GENERAL"),
    ],
)
def test_orchestrator_blocks_unsafe_queries_at_api(query: str, expected_domain: str):
    """Verify safety guardrail blocks unsafe inquiries at /orchestrator/ask and /chat in <5ms."""
    for endpoint in ["/orchestrator/ask", "/chat"]:
        resp = client.post(endpoint, json={"query": query})
        assert resp.status_code == 200
        data = resp.json()
        assert data["grounding_status"] == "ungrounded"
        ans = data["answer"].lower()
        assert "advice" in ans or "recommendation" in ans
        assert data["model_used"] == "deterministic_guardrail"
        assert data["sub_tasks"][0]["status"] == "filtered"
        assert data["domain_detected"] == expected_domain


def test_crypto_endpoint_blocks_unsafe_queries():
    """Verify POST /agents/crypto/ask enforces crypto safety guardrails."""
    resp = client.post("/agents/crypto/ask", json={"query": "Which coin to buy for 10x gains?"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["grounding_status"] == "ungrounded"
    ans = data["answer"].lower()
    assert "advice" in ans or "recommendation" in ans
    assert data["model_used"] == "deterministic_guardrail"


def test_personal_finance_endpoint_blocks_unsafe_queries():
    """Verify POST /agents/personal-finance/ask enforces personal finance safety guardrails."""
    resp = client.post("/agents/personal-finance/ask", json={"query": "Tell me which stocks to put my 5 lakh savings into"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["grounding_status"] == "ungrounded"
    ans = data["answer"].lower()
    assert "advice" in ans or "recommendation" in ans
    assert data["model_used"] == "deterministic_guardrail"


# =====================================================================
# 2. Single-Intent Fast-Path Endpoints
# =====================================================================

def test_single_intent_equity_quote():
    """Verify single-entity live equity quote via /orchestrator/ask."""
    resp = client.post("/orchestrator/ask", json={"query": "What is Reliance trading at?"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["domain_detected"] == "EQUITY"
    assert data["market_data"] is not None
    assert data["market_data"]["symbol"] == "RELIANCE"
    assert "RELIANCE" in data["answer"]
    assert "₹" in data["answer"]
    assert "live_market_data" in data["grounding_sources"]


def test_single_intent_crypto_quote():
    """Verify single-entity live crypto quote via /chat."""
    from app.tools.crypto.models import CryptoQuote
    mock_btc = CryptoQuote(
        symbol="BTC",
        name="Bitcoin",
        price_usd=64250.0,
        price_inr=5350000.0,
        change_24h=2.45,
        market_timestamp="2026-09-11T20:00:00Z",
        retrieved_at="2026-09-11T20:00:00Z",
        provider="CoinGecko",
        freshness_status="realtime",
    )
    with patch("app.tools.crypto.service.CryptoDataService.get_quote", return_value=mock_btc):
        resp = client.post("/chat", json={"query": "What is Bitcoin price?"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["domain_detected"] == "CRYPTO"
        assert data["crypto_data"] is not None
        assert data["crypto_data"]["symbol"] == "BTC"
        assert "BTC" in data["answer"]
        assert "$" in data["answer"]
        assert "crypto_data" in data["grounding_sources"]


def test_single_intent_personal_finance_budget():
    """Verify deterministic 50/30/20 budgeting calculation via /orchestrator/ask."""
    resp = client.post("/orchestrator/ask", json={"query": "How should I budget my income of 50000 using 50/30/20?"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["domain_detected"] == "PERSONAL_FINANCE"
    assert "25,000" in data["answer"]
    assert "15,000" in data["answer"]
    assert "10,000" in data["answer"]
    assert "calc_tool" in data["grounding_sources"]


def test_single_intent_personal_finance_emergency_fund():
    """Verify deterministic emergency fund calculation via /chat."""
    resp = client.post("/chat", json={"query": "Calculate emergency fund target for monthly expenses of 30000"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["domain_detected"] == "PERSONAL_FINANCE"
    assert "180,000" in data["answer"]  # 6 months * 30000
    assert "calc_tool" in data["grounding_sources"]


# =====================================================================
# 3. Compound Queries & Archetype C Execution
# =====================================================================

def test_compound_archetype_c_concept_and_quote():
    """
    Verify Archetype C: Educational Concept + Live Market Quote.
    Query: 'What is an IPO and what is Reliance trading at?'
    Expected: Synthesizes SEBI RAG concept + deterministic market card.
    """
    mock_rag_answer = RAGAnswer(
        query="What is an IPO and what is Reliance trading at?",
        answer="An Initial Public Offering (IPO) is the process by which a private company offers shares to the public [1].",
        citations=[
            Citation(
                citation_id=1,
                chunk_id="chunk_ipo_001",
                doc_id="sebi_investor_education.pdf",
                title="SEBI Investor Guide",
                source="SEBI",
                authority_level="primary_regulator",
                page_numbers=[5],
                similarity_score=0.92,
            )
        ],
        grounding_status="fully_grounded",
        model_used="qwen2.5:7b-instruct",
    )

    with patch("app.rag.service.RAGService.generate_answer", return_value=mock_rag_answer):
        resp = client.post("/orchestrator/ask", json={"query": "What is an IPO and what is Reliance trading at?"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["domain_detected"] == "EQUITY"
        # Must contain citation
        assert len(data["citations"]) >= 1
        assert data["citations"][0]["citation_id"] == 1
        # Must contain market quote
        assert data["market_data"] is not None
        assert data["market_data"]["symbol"] == "RELIANCE"
        # Must contain both RAG and Live Market sources
        assert "sebi_rag" in data["grounding_sources"]
        assert "live_market_data" in data["grounding_sources"]
        # Response composer formatted both
        assert "IPO" in data["answer"]
        assert "RELIANCE" in data["answer"]


def test_compound_multi_company_comparative_quotes():
    """
    Verify comparative multi-company queries.
    Query: 'Compare Reliance and TCS price'
    Expected: Returns market data cards for both companies in market_data_list.
    """
    resp = client.post("/orchestrator/ask", json={"query": "Compare Reliance and TCS price"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["domain_detected"] == "EQUITY"
    assert len(data["market_data_list"]) >= 2
    symbols = {item["symbol"] for item in data["market_data_list"]}
    assert "RELIANCE" in symbols
    assert "TCS" in symbols
    assert "RELIANCE" in data["answer"]
    assert "TCS" in data["answer"]


def test_cross_domain_equity_and_personal_finance():
    """
    Verify cross-domain query: Equity Concept + Personal Finance Budget.
    Query: 'What is an IPO and how do I budget 50000 with 50/30/20?'
    """
    mock_rag_answer = RAGAnswer(
        query="What is an IPO and how do I budget 50000 with 50/30/20?",
        answer="An IPO is an Initial Public Offering where private companies issue public shares [1].",
        citations=[
            Citation(
                citation_id=1,
                chunk_id="chunk_ipo_002",
                doc_id="sebi_guide.pdf",
                title="SEBI Guide to Capital Markets",
                source="SEBI",
                authority_level="primary_regulator",
                page_numbers=[2],
                similarity_score=0.88,
            )
        ],
        grounding_status="fully_grounded",
        model_used="qwen2.5:7b-instruct",
    )

    with patch("app.rag.service.RAGService.generate_answer", return_value=mock_rag_answer):
        resp = client.post("/chat", json={"query": "What is an IPO and how do I budget 50000 with 50/30/20?"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["sub_tasks"]) >= 2
        # Verify both domains appear in subtasks
        subtask_domains = {t["domain"] for t in data["sub_tasks"]}
        assert "EQUITY" in subtask_domains
        assert "PERSONAL_FINANCE" in subtask_domains
        # Verify answer incorporates both educational explanations
        assert "IPO" in data["answer"]
        assert "25,000" in data["answer"]
        assert "15,000" in data["answer"]
        assert "10,000" in data["answer"]


def test_cross_domain_crypto_and_equity():
    """
    Verify cross-domain query: Crypto Quote + Equity Concept.
    Query: 'What is Bitcoin price and what is an ETF?'
    """
    mock_rag_answer = RAGAnswer(
        query="What is Bitcoin price and what is an ETF?",
        answer="An Exchange Traded Fund (ETF) is an investment fund traded on stock exchanges [1].",
        citations=[
            Citation(
                citation_id=1,
                chunk_id="chunk_etf_001",
                doc_id="sebi_etf_guide.pdf",
                title="SEBI Mutual Funds and ETFs",
                source="SEBI",
                authority_level="primary_regulator",
                page_numbers=[1],
                similarity_score=0.90,
            )
        ],
        grounding_status="fully_grounded",
        model_used="qwen2.5:7b-instruct",
    )

    from app.tools.crypto.models import CryptoQuote
    mock_btc = CryptoQuote(
        symbol="BTC",
        name="Bitcoin",
        price_usd=64250.0,
        price_inr=5350000.0,
        change_24h=2.45,
        market_timestamp="2026-09-11T20:00:00Z",
        retrieved_at="2026-09-11T20:00:00Z",
        provider="CoinGecko",
        freshness_status="realtime",
    )

    with patch("app.rag.service.RAGService.generate_answer", return_value=mock_rag_answer), \
         patch("app.tools.crypto.service.CryptoDataService.get_quote", return_value=mock_btc):
        resp = client.post("/orchestrator/ask", json={"query": "What is Bitcoin price and what is an ETF?"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["crypto_data"] is not None
        assert data["crypto_data"]["symbol"] == "BTC"
        assert len(data["citations"]) >= 1
        assert "BTC" in data["answer"]
        assert "ETF" in data["answer"]


# =====================================================================
# 4. Agent-Specific Dedicated Endpoints
# =====================================================================

def test_crypto_dedicated_endpoint_quote():
    """Verify POST /agents/crypto/ask returns valid quote structure."""
    from app.tools.crypto.models import CryptoQuote

    mock_eth = CryptoQuote(
        symbol="ETH",
        name="Ethereum",
        price_usd=3450.50,
        price_inr=285000.0,
        change_24h=1.85,
        market_timestamp="2026-09-11T20:00:00Z",
        retrieved_at="2026-09-11T20:00:00Z",
        provider="CoinGecko",
        freshness_status="realtime",
    )
    with patch("app.tools.crypto.service.CryptoDataService.get_quote", return_value=mock_eth):
        resp = client.post("/agents/crypto/ask", json={"query": "Current price of Ethereum"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["agent_name"] == "Crypto Tutor (Prof. Crypton)"
        assert data["grounding_status"] == "fully_grounded"
        assert data["crypto_data"]["symbol"] == "ETH"
        assert "ETH" in data["answer"]
        assert "crypto_data" in data["grounding_sources"]


def test_personal_finance_dedicated_endpoint_budget():
    """Verify POST /agents/personal-finance/ask returns valid budget calculation."""
    resp = client.post("/agents/personal-finance/ask", json={"query": "How to budget 60000 with 50/30/20"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["agent_name"] == "Personal Finance Tutor (Prof. Persona)"
    assert data["calc_data"]["needs"] == 30000.0
    assert data["calc_data"]["wants"] == 18000.0
    assert data["calc_data"]["savings"] == 12000.0
    assert "30,000" in data["answer"]
    assert "calc_tool" in data["grounding_sources"]


# =====================================================================
# 5. Phase 2/3 Backward Compatibility Regression
# =====================================================================

def test_legacy_equity_ask_backward_compatibility():
    """Verify POST /agents/equity/ask contract remains 100% backward compatible."""
    resp = client.post("/agents/equity/ask", json={"query": "What is Reliance trading at?"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["agent_name"] == "Equity Tutor"
    assert data["market_data"] is not None
    assert data["market_data"]["symbol"] == "RELIANCE"
    assert "RELIANCE" in data["answer"]
    assert "live_market_data" in data["grounding_sources"]


def test_scenario_b_reliance_quote_and_bitcoin_concept_e2e():
    """
    Scenario B: 'What is Reliance trading at and what is Bitcoin?'
    Verifies execution of BOTH Reliance quote and Bitcoin educational intent,
    and checks truthful 'partially_grounded' status.
    """
    mock_llm_text = "Bitcoin is a decentralized digital cryptocurrency created by Satoshi Nakamoto."
    with patch("app.agents.crypto.agent.CryptoAgent.ask") as mock_crypto:
        from app.agents.crypto.agent import CryptoAgentResult
        mock_crypto.return_value = CryptoAgentResult(
            query="what is Bitcoin?",
            answer=mock_llm_text,
            grounding_status="ungrounded",
            crypto_data=None,
            grounding_sources=[],
            agent_name="Crypto Tutor (Prof. Crypton)",
            disclaimer="",
            model_used="qwen2.5:7b-instruct",
            latency_ms=10.0,
        )

        resp = client.post("/orchestrator/ask", json={"query": "What is Reliance trading at and what is Bitcoin?"})
        assert resp.status_code == 200
        data = resp.json()

        # Both subtasks must be recorded
        assert len(data["sub_tasks"]) == 2
        sub_intents = {t["intent"] for t in data["sub_tasks"]}
        assert "quote" in sub_intents
        assert "educational_concept" in sub_intents

        # Reliance market quote was fetched
        assert len(data["market_data_list"]) >= 1
        assert any(q["symbol"] == "RELIANCE" for q in data["market_data_list"])

        # Truthful hybrid grounding status
        assert data["grounding_status"] == "partially_grounded"
        assert "live_market_data" in data["grounding_sources"]
        assert "Satoshi Nakamoto" in data["answer"]


def test_scenario_f_three_domain_compound_query_e2e():
    """
    Scenario F: 'What is an IPO, what is Bitcoin, and how does 50/30/20 budgeting work?'
    Verifies all 3 domains execute: Equity RAG, Crypto Education, and PF Education.
    """
    mock_rag_answer = RAGAnswer(
        query="What is an IPO",
        answer="An IPO is an Initial Public Offering [1].",
        citations=[
            Citation(
                citation_id=1,
                chunk_id="chunk_ipo_001",
                doc_id="sebi_guide.pdf",
                title="SEBI Capital Markets Guide",
                source="SEBI",
                authority_level="primary_regulator",
                page_numbers=[1],
                similarity_score=0.92,
            )
        ],
        grounding_status="fully_grounded",
        model_used="qwen2.5:7b-instruct",
    )

    with patch("app.rag.service.RAGService.generate_answer", return_value=mock_rag_answer):
        resp = client.post("/orchestrator/ask", json={
            "query": "What is an IPO, what is Bitcoin, and how does 50/30/20 budgeting work?"
        })
        assert resp.status_code == 200
        data = resp.json()

        # All 3 subtasks must be executed
        assert len(data["sub_tasks"]) == 3
        domains = {t["domain"] for t in data["sub_tasks"]}
        assert domains == {"EQUITY", "CRYPTO", "PERSONAL_FINANCE"}

        # Answer should contain elements of all three
        assert "IPO" in data["answer"]
        assert "sebi_rag" in data["grounding_sources"]
        # Hybrid status because of ungrounded crypto/PF educational alongside sebi_rag
        assert data["grounding_status"] == "partially_grounded"


def test_subtask_failure_metadata_recording_e2e():
    """
    Verify that when a subtask fails during orchestration, it is recorded
    with status='failed' in execution metadata rather than silently dropped.
    """
    with patch("app.tools.market.service.MarketDataService.get_quote", side_effect=Exception("Upstream Yahoo failure")):
        resp = client.post("/orchestrator/ask", json={
            "query": "What is Reliance trading at and what is Bitcoin?"
        })
        assert resp.status_code == 200
        data = resp.json()

        # Equity quote subtask must be present and marked 'failed'
        reliance_task = next((t for t in data["sub_tasks"] if t["domain"] == "EQUITY"), None)
        assert reliance_task is not None
        assert reliance_task["status"] == "failed"

