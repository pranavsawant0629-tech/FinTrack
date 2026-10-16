"""
Tests for the Portfolio Tutor Agent.
Verifies safety guardrail pre-filtering, deterministic portfolio analytics,
what-if stress testing, user isolation, and educational framing.
"""

from unittest.mock import MagicMock
import pytest

from app.agents.portfolio.agent import PortfolioAgent, PortfolioAgentResult
from app.agents.portfolio.prompts import PORTFOLIO_DISCLAIMER
from app.agents.portfolio.safety import PortfolioSafetyGuardrail
from app.tools.portfolio.models import Holding, PortfolioData
from app.tools.portfolio.providers.mock import MockPortfolioProvider
from app.tools.portfolio.service import PortfolioService


@pytest.fixture
def mock_service():
    provider = MockPortfolioProvider(seed_demo=False)
    # Seed a known test portfolio
    p = PortfolioData(
        user_id="user_test",
        cash_balance=10000.0,
        holdings=[
            Holding(symbol="TCS", quantity=10.0, average_buy_price=3500.0, current_price=4000.0, sector="Technology"),
            Holding(symbol="RELIANCE", quantity=20.0, average_buy_price=2500.0, current_price=2700.0, sector="Energy"),
        ],
    )
    provider.save_portfolio(p)
    return PortfolioService(provider=provider)


@pytest.fixture
def agent(mock_service):
    llm = MagicMock()
    return PortfolioAgent(service=mock_service, llm=llm)


class TestPortfolioSafety:
    """Test safety rules blocking rebalancing advice and trade execution."""

    def test_blocks_rebalancing_directives(self):
        guardrail = PortfolioSafetyGuardrail()
        unsafe_queries = [
            "How should I rebalance my portfolio?",
            "Should I sell TCS to buy Reliance?",
            "Tell me which stocks to sell from my portfolio",
            "What to buy with my cash balance?",
            "Place an order to buy 50 shares of TCS",
            "Sell 10 shares of Reliance",
            "Execute trade for my portfolio",
        ]
        for q in unsafe_queries:
            res = guardrail.evaluate(q)
            assert not res.is_safe, f"Expected unsafe for: {q}"
            assert res.refusal_reason == "portfolio_advisory_intent"
            assert "cannot provide personalized portfolio rebalancing advice" in (res.refusal_message or "")

    def test_allows_educational_portfolio_inquiries(self):
        guardrail = PortfolioSafetyGuardrail()
        safe_queries = [
            "What is my portfolio value?",
            "How diversified is my portfolio?",
            "Show my current holdings",
            "What is my asset allocation?",
            "What if TCS falls 10%?",
            "What if Nifty drops 5%?",
            "Explain portfolio diversification",
            "What is the difference between systematic and unsystematic risk?",
        ]
        for q in safe_queries:
            res = guardrail.evaluate(q)
            assert res.is_safe, f"Expected safe for: {q}"


class TestPortfolioAgentExecution:
    """Test PortfolioAgent execution pipeline."""

    def test_safety_refusal_returns_unadvisory_response(self, agent):
        res = agent.ask("How should I rebalance my portfolio?", user_id="user_test")
        assert isinstance(res, PortfolioAgentResult)
        assert res.grounding_status == "ungrounded"
        assert "cannot provide personalized portfolio rebalancing advice" in res.answer
        assert res.disclaimer == PORTFOLIO_DISCLAIMER
        assert res.portfolio_data is None

    def test_portfolio_analytics_exact_math(self, agent):
        res = agent.ask("What is my portfolio value?", user_id="user_test")
        assert res.grounding_status == "fully_grounded"
        assert "portfolio_tool" in res.grounding_sources
        assert res.portfolio_data is not None

        metrics = res.portfolio_data["metrics"]
        assert metrics["total_portfolio_value"] == 104000.0  # 40k + 54k + 10k cash
        assert metrics["securities_cost_basis"] == 85000.0  # 35k + 50k
        assert metrics["cash_balance"] == 10000.0
        assert metrics["unrealized_pnl"] == 9000.0

        assert "Total Portfolio Value" in res.answer
        assert "₹104,000.00" in res.answer
        assert "₹85,000.00" in res.answer

    def test_what_if_scenario_execution(self, agent):
        res = agent.ask("What if TCS falls 10%?", user_id="user_test")
        assert res.grounding_status == "fully_grounded"
        assert "portfolio_tool" in res.grounding_sources
        assert res.portfolio_data is not None

        # TCS: 40k -> 36k (delta -4k)
        # Total portfolio: 104k -> 100k (delta -4k)
        assert res.portfolio_data["original_portfolio_value"] == 104000.0
        assert res.portfolio_data["simulated_portfolio_value"] == 100000.0
        assert res.portfolio_data["portfolio_delta_value"] == -4000.0
        assert "Simulated Portfolio Stress Test" in res.answer
        assert "₹100,000.00" in res.answer

    def test_missing_portfolio_provides_demo_educational_view(self, agent):
        res = agent.ask("What is my portfolio value?", user_id="unknown_new_user")
        assert res.grounding_status == "fully_grounded"
        assert res.portfolio_data is not None
        # Should provide standard demo holdings
        holdings = res.portfolio_data["portfolio"]["holdings"]
        assert len(holdings) > 0
