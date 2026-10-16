"""
Market News Service.
Coordinates live financial and regulatory news providers, manages in-memory caching
with freshness tracking, and enforces strict truthfulness (zero fabricated news).
"""

from __future__ import annotations

from datetime import datetime, timezone
import logging
import time
from typing import Any

from app.tools.news.interfaces import BaseNewsProvider
from app.tools.news.models import NewsArticle, NewsFreshness, NewsSearchResult
from app.tools.news.providers.mock import MockNewsProvider
from app.tools.news.providers.rss_provider import PublicRSSNewsProvider
from app.tools.news.providers.yfinance_provider import YFinanceNewsProvider

logger = logging.getLogger(__name__)


class NewsService:
    """Service providing verified news summaries with freshness guarantees."""

    def __init__(
        self,
        providers: list[BaseNewsProvider] | None = None,
        ttl_seconds: int = 300,
        stale_ttl_seconds: int = 1800,
        allow_mock: bool = False,
    ) -> None:
        self._allow_mock = allow_mock
        self._ttl_seconds = ttl_seconds
        self._stale_ttl_seconds = stale_ttl_seconds
        self._cache: dict[str, tuple[float, list[NewsArticle], str]] = {}  # key -> (timestamp, articles, provider)

        if providers is not None:
            self._providers = providers
        else:
            if allow_mock:
                self._providers = [MockNewsProvider()]
            else:
                self._providers = [
                    YFinanceNewsProvider(),
                    PublicRSSNewsProvider(),
                ]

    def get_ticker_news(self, symbol: str, limit: int = 5) -> NewsSearchResult:
        """Retrieve verified news for a given equity ticker symbol."""
        clean_symbol = symbol.strip().upper()
        cache_key = f"ticker:{clean_symbol}"

        # 1. Check active fresh cache
        cached = self._get_cached_articles(cache_key, check_stale=False)
        if cached:
            articles, provider, freshness = cached
            return NewsSearchResult(
                query=f"news for {clean_symbol}",
                symbol=clean_symbol,
                articles=articles[:limit],
                freshness=freshness,
                provider=f"{provider}_cached",
                is_live=not self._allow_mock,
            )

        # 2. Query live providers
        for provider in self._providers:
            try:
                articles = provider.fetch_ticker_news(clean_symbol, limit=limit)
                if articles:
                    self._cache[cache_key] = (time.time(), articles, provider.name)
                    freshness = NewsFreshness.OFFLINE_FIXTURE if isinstance(provider, MockNewsProvider) else NewsFreshness.REALTIME
                    return NewsSearchResult(
                        query=f"news for {clean_symbol}",
                        symbol=clean_symbol,
                        articles=articles,
                        freshness=freshness,
                        provider=provider.name,
                        is_live=not isinstance(provider, MockNewsProvider),
                    )
            except Exception as exc:
                logger.warning("Provider %s failed fetching news for %s: %s", provider.name, clean_symbol, exc)

        # 3. If live query failed, check if stale cache can be served truthfully
        stale = self._get_cached_articles(cache_key, check_stale=True)
        if stale:
            articles, provider, freshness = stale
            return NewsSearchResult(
                query=f"news for {clean_symbol}",
                symbol=clean_symbol,
                articles=articles[:limit],
                freshness=NewsFreshness.STALE_CACHE,
                provider=f"{provider}_stale_cache",
                is_live=False,
            )

        # 4. Truthful failure — NEVER silently substitute mock news
        return NewsSearchResult(
            query=f"news for {clean_symbol}",
            symbol=clean_symbol,
            articles=[],
            freshness=NewsFreshness.REALTIME,
            provider="none",
            is_live=not self._allow_mock,
            error_message=f"No verified recent news could be retrieved for {clean_symbol} at this time.",
        )

    def get_macro_news(self, limit: int = 5) -> NewsSearchResult:
        """Retrieve macro-economic and SEBI/RBI regulatory news."""
        cache_key = "macro_news"

        # 1. Check active fresh cache
        cached = self._get_cached_articles(cache_key, check_stale=False)
        if cached:
            articles, provider, freshness = cached
            return NewsSearchResult(
                query="macro and regulatory news",
                symbol=None,
                articles=articles[:limit],
                freshness=freshness,
                provider=f"{provider}_cached",
                is_live=not self._allow_mock,
            )

        # 2. Query providers
        aggregated_articles: list[NewsArticle] = []
        reporting_providers: list[str] = []

        for provider in self._providers:
            try:
                arts = provider.fetch_macro_news(limit=limit)
                if arts:
                    aggregated_articles.extend(arts)
                    reporting_providers.append(provider.name)
            except Exception as exc:
                logger.warning("Provider %s failed fetching macro news: %s", provider.name, exc)

        if aggregated_articles:
            # Sort newest first if possible
            self._cache[cache_key] = (time.time(), aggregated_articles, ",".join(reporting_providers))
            is_fixture = any(isinstance(p, MockNewsProvider) for p in self._providers)
            freshness = NewsFreshness.OFFLINE_FIXTURE if is_fixture else NewsFreshness.REALTIME
            return NewsSearchResult(
                query="macro and regulatory news",
                symbol=None,
                articles=aggregated_articles[:limit],
                freshness=freshness,
                provider=",".join(reporting_providers),
                is_live=not is_fixture,
            )

        # 3. Check stale cache
        stale = self._get_cached_articles(cache_key, check_stale=True)
        if stale:
            articles, provider, freshness = stale
            return NewsSearchResult(
                query="macro and regulatory news",
                symbol=None,
                articles=articles[:limit],
                freshness=NewsFreshness.STALE_CACHE,
                provider=f"{provider}_stale_cache",
                is_live=False,
            )

        # 4. Truthful failure
        return NewsSearchResult(
            query="macro and regulatory news",
            symbol=None,
            articles=[],
            freshness=NewsFreshness.REALTIME,
            provider="none",
            is_live=not self._allow_mock,
            error_message="No verified regulatory or macro news could be retrieved at this time.",
        )

    def _get_cached_articles(
        self, key: str, check_stale: bool
    ) -> tuple[list[NewsArticle], str, NewsFreshness] | None:
        if key not in self._cache:
            return None
        timestamp, articles, provider = self._cache[key]
        age = time.time() - timestamp

        if not check_stale:
            if age <= self._ttl_seconds:
                return articles, provider, NewsFreshness.REALTIME
            return None
        else:
            if age <= self._stale_ttl_seconds:
                return articles, provider, NewsFreshness.STALE_CACHE
            return None
