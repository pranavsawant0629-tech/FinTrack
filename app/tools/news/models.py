"""
Data models for the Market News Tool.
Defines structured schemas for articles, query results, and freshness states.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class NewsSourceType(str, Enum):
    MARKET = "market"
    REGULATORY = "regulatory"
    MACRO = "macro"
    EDUCATIONAL = "educational"


class NewsFreshness(str, Enum):
    REALTIME = "realtime"
    DELAYED = "delayed"
    STALE_CACHE = "stale_cache"
    OFFLINE_FIXTURE = "offline_fixture"


@dataclass(frozen=True)
class NewsArticle:
    """Individual structured news article."""
    id: str
    title: str
    summary: str
    url: str
    source: str
    source_type: NewsSourceType
    published_at: str
    symbol: str | None = None
    freshness: NewsFreshness = NewsFreshness.REALTIME

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "summary": self.summary,
            "url": self.url,
            "source": self.source,
            "source_type": self.source_type.value,
            "published_at": self.published_at,
            "symbol": self.symbol,
            "freshness": self.freshness.value,
        }


@dataclass(frozen=True)
class NewsSearchResult:
    """Result of a news search or fetch query."""
    query: str
    articles: list[NewsArticle]
    freshness: NewsFreshness
    provider: str
    is_live: bool
    retrieved_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    symbol: str | None = None
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "symbol": self.symbol,
            "articles": [a.to_dict() for a in self.articles],
            "freshness": self.freshness.value,
            "provider": self.provider,
            "is_live": self.is_live,
            "retrieved_at": self.retrieved_at,
            "error_message": self.error_message,
        }
