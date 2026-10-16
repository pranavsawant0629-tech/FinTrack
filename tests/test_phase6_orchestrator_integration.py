"""
Integration tests for Phase 6 Orchestrator and Router integration.
Verifies fast-path classification, single-intent dispatch, compound multi-domain execution,
global safety pre-filtering, and memory personalization across all 8 specialized domains.
"""

from unittest.mock import MagicMock
import pytest

from app.router.classifier import FastPathClassifier
from app.router.models import OrchestratorResponse
from app.router.orchestrator import CentralOrchestrator


@pytest.fixture
def orchestrator():
    # Central orchestrator with default services and test-safe mocks where appropriate
    orch = CentralOrchestrator()
    return orch


class TestPhase6ClassifierRouting:
    """Test fast-path classification for the new Phase 6 specialized domains."""

    def test_classifies_derivatives(self):
        clf = FastPathClassifier()
        res = clf.classify("What is the payoff for Nifty 24500 Call?")
        assert res.domain == "DERIVATIVES"

    def test_classifies_portfolio(self):
        clf = FastPathClassifier()
        res = clf.classify("What is my portfolio value and asset allocation?")
        assert res.domain == "PORTFOLIO"

    def test_classifies_news(self):
        clf = FastPathClassifier()
        res = clf.classify("What is the latest market news for TCS?")
        assert res.domain == "NEWS"

    def test_classifies_quiz(self):
        clf = FastPathClassifier()
        res = clf.classify("Quiz me on derivatives")
        assert res.domain == "QUIZ"

    def test_classifies_onboarding(self):
        clf = FastPathClassifier()
        res = clf.classify("What can Finova AI do?")
        assert res.domain == "ONBOARDING"


class TestPhase6OrchestratorDispatch:
    """Test full central orchestrator dispatch to new specialized agents."""

    def test_derivatives_dispatch(self, orchestrator):
        res = orchestrator.ask("Explain option Greeks Delta and Gamma")
        assert isinstance(res, OrchestratorResponse)
        assert res.domain_detected == "DERIVATIVES"
        assert res.grounding_status in ("fully_grounded", "partially_grounded")
        assert "Delta" in res.answer or "Gamma" in res.answer
        assert len(res.sub_tasks) == 1
        assert res.sub_tasks[0].domain == "DERIVATIVES"

    def test_portfolio_dispatch(self, orchestrator):
        res = orchestrator.ask("What is my portfolio value?", user_id="user_test_p6")
        assert isinstance(res, OrchestratorResponse)
        assert res.domain_detected == "PORTFOLIO"
        assert res.portfolio_data is not None
        assert "₹" in res.answer
        assert res.sub_tasks[0].domain == "PORTFOLIO"

    def test_news_dispatch(self, orchestrator):
        # Using a mock provider for deterministic news in integration test
        from app.tools.news.providers.mock import MockNewsProvider
        from app.tools.news.service import NewsService
        from app.agents.news.agent import NewsAgent
        mock_news_svc = NewsService(providers=[MockNewsProvider(seed_demo=True)], allow_mock=True)
        orchestrator._news_agent = NewsAgent(service=mock_news_svc)

        res = orchestrator.ask("What is the latest news for TCS?")
        assert isinstance(res, OrchestratorResponse)
        assert res.domain_detected == "NEWS"
        assert res.news_data is not None
        assert len(res.news_data) > 0
        assert "TCS" in res.news_data[0]["title"]

    def test_quiz_dispatch(self, orchestrator):
        res = orchestrator.ask("Quiz me on personal finance")
        assert isinstance(res, OrchestratorResponse)
        assert res.domain_detected == "QUIZ"
        assert "Finova Knowledge Challenge" in res.answer
        assert res.quiz_data is not None

    def test_onboarding_dispatch(self, orchestrator):
        res = orchestrator.ask("What can Finova AI do?")
        assert isinstance(res, OrchestratorResponse)
        assert res.domain_detected == "ONBOARDING"
        assert "Welcome to Finova AI" in res.answer
        assert res.onboarding_data is not None
        assert len(res.onboarding_data) == 8

    def test_global_safety_blocks_derivatives_option_tips(self, orchestrator):
        res = orchestrator.ask("Give me sure shot option buying calls for tomorrow")
        assert res.grounding_status == "ungrounded"
        assert res.domain_detected in ("DERIVATIVES", "GENERAL", "EQUITY")
        assert "cannot provide" in res.answer and ("tips" in res.answer or "advice" in res.answer)

    def test_global_safety_blocks_portfolio_rebalancing(self, orchestrator):
        res = orchestrator.ask("How should I rebalance my portfolio?")
        assert res.grounding_status == "ungrounded"
        assert "cannot provide" in res.answer

    def test_compound_query_across_domains(self, orchestrator):
        from app.tools.news.providers.mock import MockNewsProvider
        from app.tools.news.service import NewsService
        from app.agents.news.agent import NewsAgent
        mock_news_svc = NewsService(providers=[MockNewsProvider(seed_demo=True)], allow_mock=True)
        orchestrator._news_agent = NewsAgent(service=mock_news_svc)

        res = orchestrator.ask("What is the latest news for TCS and also what is an equity IPO?")
        assert isinstance(res, OrchestratorResponse)
        # Should execute both tasks
        assert len(res.sub_tasks) >= 2
        domains = [st.domain for st in res.sub_tasks]
        assert "NEWS" in domains
        assert "EQUITY" in domains
