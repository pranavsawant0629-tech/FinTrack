"""
Abstract interfaces for news providers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.tools.news.models import NewsArticle


class BaseNewsProvider(ABC):
    """Abstract base class for all market news and regulatory feed providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the news provider."""
        ...

    @abstractmethod
    def fetch_ticker_news(self, symbol: str, limit: int = 5) -> list[NewsArticle]:
        """Fetch latest news for a given equity ticker symbol."""
        ...

    @abstractmethod
    def fetch_macro_news(self, limit: int = 5) -> list[NewsArticle]:
        """Fetch latest macro/regulatory market news."""
        ...

    @abstractmethod
    def is_healthy(self) -> bool:
        """Check whether provider endpoint or source is reachable."""
        ...
