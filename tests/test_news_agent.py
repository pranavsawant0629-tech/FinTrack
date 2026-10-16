"""
Tests for the Market News Agent.
Verifies safety guardrail pre-filtering, rumor/tips blocking,
truthful error responses, and educational news formatting.
"""

from unittest.mock import MagicMock
import pytest

from app.agents.news.agent import NewsAgent, NewsAgentResult
from app.agents.news.prompts import NEWS_DISCLAIMER
from app.agents.news.safety import NewsSafetyGuardrail
from app.tools.news.providers.mock import MockNewsProvider
from app.tools.news.service import NewsService


class TestNewsSafety:
    """Test safety rules blocking rumor speculation and news-based tips."""

    def test_blocks_news_trading_tips_and_rumors(self):
        guardrail = NewsSafetyGuardrail()
        unsafe_queries = [
            "What stocks should I buy based on the news?",
            "Which shares to buy after the news?",
            "Give me hot news stocks to buy",
            "Any news based tips for today?",
            "Tell me insider trading tips",
            "Is the unverified rumor about TCS crash true?",
            "Will Reliance double after this news?",
        ]
        for q in unsafe_queries:
            res = guardrail.evaluate(q)
            assert not res.is_safe, f"Expected unsafe for: {q}"
            assert res.refusal_reason == "news_speculation_or_tips"
            assert "We do not provide trading recommendations based on news" in (res.refusal_message or "")

    def test_allows_factual_and_conceptual_inquiries(self):
        guardrail = NewsSafetyGuardrail()
        safe_queries = [
            "What is the latest news for TCS?",
            "Show recent SEBI circulars",
            "What did RBI announce in the latest MPC meeting?",
            "What is insider trading?",
            "Explain how share buybacks work",
        ]
        for q in safe_queries:
            res = guardrail.evaluate(q)
            assert res.is_safe, f"Expected safe for: {q}"


class TestNewsAgentExecution:
    """Test NewsAgent execution pipeline."""

    @pytest.fixture
    def mock_service(self):
        return NewsService(providers=[MockNewsProvider(seed_demo=True)], allow_mock=True)

    @pytest.fixture
    def agent(self, mock_service):
        return NewsAgent(service=mock_service)

    def test_safety_refusal_returns_unadvisory_response(self, agent):
        res = agent.ask("What stocks should I buy based on the news?")
        assert isinstance(res, NewsAgentResult)
        assert res.grounding_status == "ungrounded"
        assert "We do not provide trading recommendations based on news" in res.answer
        assert res.disclaimer == NEWS_DISCLAIMER
        assert len(res.articles) == 0

    def test_ticker_news_retrieval(self, agent):
        res = agent.ask("What is the latest news for TCS?")
        assert res.grounding_status == "fully_grounded"
        assert len(res.articles) > 0
        assert "TCS" in res.articles[0]["title"]
        assert "Retrieved Financial & Regulatory Headlines" in res.answer
        assert res.disclaimer == NEWS_DISCLAIMER

    def test_macro_news_retrieval(self, agent):
        res = agent.ask("What are the latest regulatory announcements from SEBI and RBI?")
        assert res.grounding_status == "fully_grounded"
        assert len(res.articles) > 0
        assert any("SEBI" in a["source"] or "RBI" in a["source"] for a in res.articles)

    def test_truthful_failure_when_no_news_available(self):
        empty_service = MagicMock()
        from app.tools.news.models import NewsFreshness, NewsSearchResult
        empty_service.get_ticker_news.return_value = NewsSearchResult(
            query="news for UNKNOWN",
            symbol="UNKNOWN",
            articles=[],
            freshness=NewsFreshness.REALTIME,
            provider="none",
            is_live=True,
            error_message="No verified recent news could be retrieved for UNKNOWN at this time.",
        )
        agent = NewsAgent(service=empty_service)

        res = agent.ask("News on UNKNOWN stock")
        assert res.grounding_status == "ungrounded"
        assert len(res.articles) == 0
        assert "No verified recent news could be retrieved for UNKNOWN" in res.answer
