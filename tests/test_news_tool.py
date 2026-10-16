"""
Tests for the Market News Tool and Providers.
Verifies strict truthfulness, caching TTL semantics, freshness labeling,
and the strict invariant that live queries never fall back silently to mock news.
"""

import time
from unittest.mock import MagicMock
import pytest

from app.tools.news.models import NewsArticle, NewsFreshness, NewsSearchResult, NewsSourceType
from app.tools.news.providers.mock import MockNewsProvider
from app.tools.news.service import NewsService


class TestNewsProviders:
    """Test individual providers."""

    def test_mock_provider_seeded_articles(self):
        prov = MockNewsProvider(seed_demo=True)
        assert prov.name == "mock_news"
        assert prov.is_healthy() is True

        tcs_news = prov.fetch_ticker_news("TCS.NS")
        assert len(tcs_news) > 0
        assert "TCS" in tcs_news[0].title
        assert tcs_news[0].freshness == NewsFreshness.OFFLINE_FIXTURE

        macro_news = prov.fetch_macro_news()
        assert len(macro_news) > 0
        assert any(a.source_type in (NewsSourceType.REGULATORY, NewsSourceType.MACRO) for a in macro_news)


class TestNewsService:
    """Test NewsService caching, routing, and truthfulness guarantees."""

    def test_mock_mode_explicitly_labeled(self):
        service = NewsService(allow_mock=True)
        res = service.get_ticker_news("TCS")
        assert res.freshness == NewsFreshness.OFFLINE_FIXTURE
        assert not res.is_live
        assert len(res.articles) > 0

    def test_live_mode_never_silently_falls_back_to_mock(self):
        # Create a mock failing provider in live mode (allow_mock=False)
        failing_provider = MagicMock()
        failing_provider.name = "failing_live_feed"
        failing_provider.fetch_ticker_news.side_effect = RuntimeError("Network down")
        failing_provider.fetch_macro_news.side_effect = RuntimeError("Network down")

        service = NewsService(providers=[failing_provider], allow_mock=False)

        res = service.get_ticker_news("RELIANCE")
        # Invariant: Must report truthful error/empty, NEVER mock news!
        assert len(res.articles) == 0
        assert res.error_message is not None
        assert "No verified recent news could be retrieved" in res.error_message

    def test_in_memory_caching_and_stale_semantics(self):
        # Provider that returns articles once
        provider = MagicMock()
        provider.name = "test_live"
        sample_art = NewsArticle(
            id="test_1",
            title="RBI Test Notification",
            summary="Testing cache TTL",
            url="https://test.rbi.org",
            source="RBI",
            source_type=NewsSourceType.MACRO,
            published_at="2026-09-12T00:00:00Z",
            freshness=NewsFreshness.REALTIME,
        )
        provider.fetch_macro_news.return_value = [sample_art]

        # Service with 1-second TTL, 5-second stale TTL
        service = NewsService(
            providers=[provider],
            ttl_seconds=1,
            stale_ttl_seconds=5,
            allow_mock=False,
        )

        # 1. First fetch -> Live query
        res1 = service.get_macro_news()
        assert res1.freshness == NewsFreshness.REALTIME
        assert provider.fetch_macro_news.call_count == 1

        # 2. Second fetch immediately -> Served from fresh cache
        res2 = service.get_macro_news()
        assert res2.freshness == NewsFreshness.REALTIME
        assert "cached" in res2.provider
        assert provider.fetch_macro_news.call_count == 1  # No extra call!

        # 3. Simulate passage of time past fresh TTL (1s) and provider failure
        time.sleep(1.1)
        provider.fetch_macro_news.side_effect = RuntimeError("Feed offline")

        res3 = service.get_macro_news()
        # Should be served as truthful STALE cache!
        assert res3.freshness == NewsFreshness.STALE_CACHE
        assert "stale_cache" in res3.provider
        assert len(res3.articles) == 1
