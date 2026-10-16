"""
Mock news provider for offline testing and deterministic unit testing.
STRICT INVARIANT: This provider is ONLY for testing, deterministic test fixtures,
or explicitly configured offline demonstration mode. It is NEVER used as a silent
fallback during live user queries.
"""

from __future__ import annotations

from app.tools.news.interfaces import BaseNewsProvider
from app.tools.news.models import NewsArticle, NewsFreshness, NewsSourceType


class MockNewsProvider(BaseNewsProvider):
    """Deterministic mock news provider for unit and integration testing."""

    def __init__(self, seed_demo: bool = True) -> None:
        self._articles: list[NewsArticle] = []
        if seed_demo:
            self._seed_default_articles()

    @property
    def name(self) -> str:
        return "mock_news"

    def _seed_default_articles(self) -> None:
        self._articles = [
            NewsArticle(
                id="mock_tcs_1",
                title="TCS announces ₹15,000 crore share buyback at ₹4,150 per share",
                summary="Tata Consultancy Services approved a cash tender buyback representing 1.1% of paid-up equity.",
                url="https://finova.mock/news/tcs-buyback",
                source="Mock Financial News",
                source_type=NewsSourceType.MARKET,
                published_at="2026-09-10T10:00:00Z",
                symbol="TCS.NS",
                freshness=NewsFreshness.OFFLINE_FIXTURE,
            ),
            NewsArticle(
                id="mock_reliance_1",
                title="Reliance Industries increases capex in renewable green hydrogen infrastructure",
                summary="RIL targets 20 GW clean energy capacity across Gujarat plants by 2028.",
                url="https://finova.mock/news/reliance-clean-energy",
                source="Mock Financial News",
                source_type=NewsSourceType.MARKET,
                published_at="2026-09-11T09:30:00Z",
                symbol="RELIANCE.NS",
                freshness=NewsFreshness.OFFLINE_FIXTURE,
            ),
            NewsArticle(
                id="mock_sebi_1",
                title="SEBI issues circular tightening derivative eligibility criteria for index contracts",
                summary="Minimum contract size for equity index options revised to curb excessive retail speculation.",
                url="https://finova.mock/news/sebi-fo-circular",
                source="SEBI Gazette (Fixture)",
                source_type=NewsSourceType.REGULATORY,
                published_at="2026-09-11T12:00:00Z",
                symbol=None,
                freshness=NewsFreshness.OFFLINE_FIXTURE,
            ),
            NewsArticle(
                id="mock_rbi_1",
                title="RBI Monetary Policy Committee maintains repo rate at 6.50% citing food inflation vigilance",
                summary="Governor notes headline inflation path remains subject to climate and geopolitical risks.",
                url="https://finova.mock/news/rbi-mpc-decision",
                source="RBI Press (Fixture)",
                source_type=NewsSourceType.MACRO,
                published_at="2026-09-10T14:30:00Z",
                symbol=None,
                freshness=NewsFreshness.OFFLINE_FIXTURE,
            ),
        ]

    def add_article(self, article: NewsArticle) -> None:
        self._articles.insert(0, article)

    def fetch_ticker_news(self, symbol: str, limit: int = 5) -> list[NewsArticle]:
        clean = symbol.upper().replace(".NS", "").replace(".BO", "")
        matched = [a for a in self._articles if a.symbol and clean in a.symbol.upper()]
        if not matched:
            matched = [a for a in self._articles if clean in a.title.upper()]
        return matched[:limit]

    def fetch_macro_news(self, limit: int = 5) -> list[NewsArticle]:
        matched = [a for a in self._articles if a.source_type in (NewsSourceType.REGULATORY, NewsSourceType.MACRO)]
        return (matched or self._articles)[:limit]

    def is_healthy(self) -> bool:
        return True
