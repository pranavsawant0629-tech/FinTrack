"""
Tests for the Derivatives Tutor Agent (Prof. Derivo).
Verifies safety guardrail pre-filtering, parameter extraction, deterministic tool
dispatch, Greeks explanations, RAG grounding, and personalization.
"""

from unittest.mock import MagicMock
import pytest

from app.agents.derivatives.agent import DerivativesAgent, DerivativesAgentResult
from app.agents.derivatives.prompts import DERIVATIVES_DISCLAIMER
from app.agents.derivatives.safety import DerivativesSafetyGuardrail
from app.memory.models import PersonalizationProfile
from app.rag.service import Citation, RAGAnswer


@pytest.fixture
def mock_llm():
    llm = MagicMock()
    llm.model_name = "mock_qwen"
    llm.chat.return_value = "Educational explanation of derivatives concepts by Prof. Derivo."
    return llm


@pytest.fixture
def mock_rag():
    rag = MagicMock()
    citation = Citation(
        citation_id=1,
        chunk_id="chunk_deriv_1",
        doc_id="Module_on_Derivative_Segment",
        title="Module on Derivative Segment",
        source="SEBI",
        authority_level="Tier 1",
        url="https://investor.sebi.gov.in",
        page_numbers=[1],
        similarity_score=0.88,
    )
    rag.generate_answer.return_value = RAGAnswer(
        query="What is a call option?",
        answer="A call option gives the buyer the right, but not the obligation, to buy an underlying asset.",
        grounding_status="fully_grounded",
        citations=[citation],
        retrieved_chunks=[],
        model_used="mock_rag_model",
    )
    return rag


@pytest.fixture
def agent(mock_llm, mock_rag):
    return DerivativesAgent(rag=mock_rag, llm=mock_llm)


class TestDerivativesSafety:
    """Test deterministic safety guardrail rules for options and futures."""

    def test_blocks_options_recommendations(self):
        guardrail = DerivativesSafetyGuardrail()
        unsafe_queries = [
            "Which call option should I buy for tomorrow's expiry?",
            "Should I buy Nifty 24500 CE?",
            "Give me some option tips for today",
            "Best strike to buy for weekly expiry",
            "Suggest a hero zero option call for today",
            "How to 10x money with options trading?",
            "Buy call for Reliance 3000",
        ]
        for q in unsafe_queries:
            res = guardrail.evaluate(q)
            assert not res.is_safe, f"Expected unsafe for: {q}"
            assert res.refusal_reason == "derivatives_advisory_intent"
            assert "over 90% of individual F&O traders lose money" in (res.refusal_message or "")

    def test_allows_conceptual_derivatives_inquiries(self):
        guardrail = DerivativesSafetyGuardrail()
        safe_queries = [
            "What is a call option?",
            "How does a put option work?",
            "Explain the difference between futures and options",
            "What is moneyness in options?",
            "How does delta affect an option price?",
            "Why do 9 out of 10 traders lose money in F&O?",
            "Calculate payoff for a Call option with strike 25000 and premium 150",
            "What is the breakeven for strike 24000 and premium 200?",
        ]
        for q in safe_queries:
            res = guardrail.evaluate(q)
            assert res.is_safe, f"Expected safe for: {q}"


class TestDerivativesAgentExecution:
    """Test DerivativesAgent pipeline execution."""

    def test_safety_refusal_returns_unadvisory_response(self, agent):
        res = agent.ask("Which call option should I buy for expiry?")
        assert isinstance(res, DerivativesAgentResult)
        assert res.grounding_status == "ungrounded"
        assert "over 90% of individual F&O traders lose money" in res.answer
        assert res.disclaimer == DERIVATIVES_DISCLAIMER
        assert res.derivatives_data is None

    def test_deterministic_option_payoff_calculation(self, agent):
        query = "Calculate payoff for a Long Call option with strike 25000 and premium 150"
        res = agent.ask(query)
        assert res.grounding_status == "fully_grounded"
        assert "derivatives_tool" in res.grounding_sources
        assert res.derivatives_data is not None
        assert res.derivatives_data["strike_price"] == 25000.0
        assert res.derivatives_data["premium"] == 150.0
        assert res.derivatives_data["breakeven_price"] == 25150.0
        assert "Option Payoff Analysis" in res.answer
        assert "₹25,150.00" in res.answer

    def test_deterministic_put_payoff_calculation(self, agent):
        query = "What is the payoff for strike 24000 Put with premium 200?"
        res = agent.ask(query)
        assert res.derivatives_data is not None
        assert res.derivatives_data["option_type"] == "put"
        assert res.derivatives_data["strike_price"] == 24000.0
        assert res.derivatives_data["premium"] == 200.0
        assert res.derivatives_data["breakeven_price"] == 23800.0

    def test_deterministic_futures_pnl_calculation(self, agent):
        query = "Calculate futures pnl bought at 24000 with lot size 25"
        res = agent.ask(query)
        assert res.derivatives_data is not None
        assert res.derivatives_data["entry_price"] == 24000.0
        assert res.derivatives_data["lot_size"] == 25
        assert "Futures Contract P&L Analysis" in res.answer

    def test_missing_calculation_parameters_prompts_user(self, agent):
        query = "Please calculate my call option payoff"
        res = agent.ask(query)
        assert res.derivatives_data is None
        assert "missing parameters" in res.answer.lower()
        assert "Strike Price" in res.answer
        assert "Premium" in res.answer

    def test_greeks_educational_query(self, agent, mock_llm):
        mock_llm.chat.return_value = "Delta measures the expected change in option price."
        query = "What is Delta in options trading?"
        res = agent.ask(query)
        assert res.derivatives_data is not None
        assert "greek" in res.derivatives_data
        assert res.derivatives_data["greek"]["name"] == "Delta"
        assert res.grounding_status == "fully_grounded"

    def test_conceptual_inquiry_with_rag_citations(self, agent, mock_rag):
        query = "What is a call option according to SEBI?"
        res = agent.ask(query)
        assert len(res.citations) == 1
        assert res.citations[0].doc_id == "Module_on_Derivative_Segment"
        assert "sebi_rag" in res.grounding_sources
        assert res.grounding_status == "fully_grounded"

    def test_personalization_injection(self, agent, mock_rag):
        profile = PersonalizationProfile(
            user_id="user_123",
            learning_level="beginner",
            learning_goals=["options_basics"],
        )
        agent.ask("What is an option strike price?", personalization=profile)
        called_prompt = mock_rag.generate_answer.call_args[1]["system_prompt"]
        assert "Beginner level" in called_prompt
        assert "options_basics" in called_prompt
