"""
YFinance news provider for real-time market and company news.
"""

from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import Any
import yfinance as yf

from app.tools.news.interfaces import BaseNewsProvider
from app.tools.news.models import NewsArticle, NewsFreshness, NewsSourceType

logger = logging.getLogger(__name__)


class YFinanceNewsProvider(BaseNewsProvider):
    """Fetches market news using yfinance for Indian and global equities."""

    def __init__(self, default_suffix: str = ".NS") -> None:
        self._default_suffix = default_suffix

    @property
    def name(self) -> str:
        return "yfinance"

    def _normalize_symbol(self, symbol: str) -> str:
        clean = symbol.strip().upper()
        if "." not in clean and not clean.startswith("^"):
            return f"{clean}{self._default_suffix}"
        return clean

    def fetch_ticker_news(self, symbol: str, limit: int = 5) -> list[NewsArticle]:
        norm_symbol = self._normalize_symbol(symbol)
        try:
            ticker = yf.Ticker(norm_symbol)
            raw_news = ticker.news
            if not raw_news:
                return []
            return self._parse_articles(raw_news, symbol=norm_symbol, limit=limit)
        except Exception as exc:
            logger.warning("Failed to fetch yfinance news for %s: %s", norm_symbol, exc)
            return []

    def fetch_macro_news(self, limit: int = 5) -> list[NewsArticle]:
        """Fetch general Indian market news via Nifty 50 ticker (^NSEI)."""
        return self.fetch_ticker_news("^NSEI", limit=limit)

    def is_healthy(self) -> bool:
        try:
            t = yf.Ticker("^NSEI")
            return bool(t.ticker)
        except Exception:
            return False

    def _parse_articles(self, raw_items: list[dict[str, Any]], symbol: str, limit: int) -> list[NewsArticle]:
        articles: list[NewsArticle] = []
        for idx, item in enumerate(raw_items[:limit]):
            try:
                # Handle both new yfinance schema (item.get('content')) and legacy flat schema
                raw_content = item.get("content")
                content: dict[str, Any] = raw_content if isinstance(raw_content, dict) else item
                
                title = content.get("title") or item.get("title") or "Market Update"
                summary = content.get("summary") or content.get("description") or item.get("summary") or ""
                url = ""
                canon = content.get("canonicalUrl")
                if isinstance(canon, dict):
                    url = canon.get("url", "")
                elif "link" in item:
                    url = item.get("link", "")
                elif "url" in content:
                    url = content.get("url", "")

                publisher = "Yahoo Finance"
                prov = content.get("provider")
                if isinstance(prov, dict):
                    publisher = prov.get("displayName", "Yahoo Finance")
                elif "publisher" in item:
                    publisher = item.get("publisher", "Yahoo Finance")

                pub_time = item.get("providerPublishTime") or content.get("pubDate")
                if isinstance(pub_time, (int, float)):
                    published_at = datetime.fromtimestamp(pub_time, tz=timezone.utc).isoformat()
                elif isinstance(pub_time, str):
                    from app.tools.news.providers.rss_provider import normalize_rss_pub_date
                    published_at = normalize_rss_pub_date(pub_time)
                else:
                    published_at = ""

                article_id = str(item.get("uuid") or content.get("id") or f"{symbol}_{idx}")

                articles.append(
                    NewsArticle(
                        id=article_id,
                        title=str(title).strip(),
                        summary=str(summary).strip() if summary else str(title).strip(),
                        url=str(url),
                        source=str(publisher),
                        source_type=NewsSourceType.MARKET,
                        published_at=published_at,
                        symbol=symbol,
                        freshness=NewsFreshness.REALTIME,
                    )
                )
            except Exception as e:
                logger.debug("Error parsing article item %s: %s", idx, e)
                continue
        return articles
