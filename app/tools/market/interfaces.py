"""
Abstract interfaces and domain exceptions for the Market Data Layer.
Ensures loose coupling: Finova AI core depends only on this interface,
not on specific external data vendor implementations.
"""

from abc import ABC, abstractmethod
from typing import Literal

from app.tools.market.models import MarketQuote, HistoricalPrices, CompanyOverview


class MarketDataError(Exception):
    """Base domain exception for all market data errors."""
    pass


class SymbolNotFoundError(MarketDataError):
    """Raised when a requested ticker/symbol cannot be found on the exchange."""
    pass


class ProviderUnavailableError(MarketDataError):
    """Raised when an external market data provider is unreachable or down."""
    pass


class RateLimitExceededError(MarketDataError):
    """Raised when an external market data provider rate limit is encountered."""
    pass


class DataValidationError(MarketDataError):
    """Raised when raw data received from a provider fails schema or sanity checks."""
    pass


class BaseMarketDataProvider(ABC):
    """
    Abstract interface for market data providers (e.g. Yahoo Finance, Twelve Data).
    All concrete providers must implement these methods.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable identifier of the provider."""
        pass

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Indicates if the provider is configured and available for live requests."""
        pass

    @abstractmethod
    def get_quote(self, symbol: str, exchange: Literal["NSE", "BSE"] = "NSE") -> MarketQuote:
        """
        Fetch the current or last traded quote for an Indian equity or index.

        Args:
            symbol: Ticker symbol (e.g. 'RELIANCE', 'TCS', 'NIFTY 50').
            exchange: Primary Indian exchange ('NSE' or 'BSE').

        Returns:
            MarketQuote with standardized and validated fields.

        Raises:
            SymbolNotFoundError: If the symbol cannot be found.
            ProviderUnavailableError: If the provider is unreachable.
            RateLimitExceededError: If the request was rate-limited.
            DataValidationError: If the response is malformed or invalid.
        """
        pass

    @abstractmethod
    def get_historical_summary(
        self,
        symbol: str,
        period: str = "1mo",
        interval: str = "1d",
        exchange: Literal["NSE", "BSE"] = "NSE",
    ) -> HistoricalPrices:
        """
        Fetch 1-month daily historical OHLCV summary for an equity or index.

        Args:
            symbol: Ticker symbol.
            period: Historical window (fixed to '1mo' for Phase 3).
            interval: Bar interval (fixed to '1d' for Phase 3).
            exchange: Primary Indian exchange ('NSE' or 'BSE').

        Returns:
            HistoricalPrices summary object.
        """
        pass

    @abstractmethod
    def get_company_overview(
        self,
        symbol: str,
        exchange: Literal["NSE", "BSE"] = "NSE",
    ) -> CompanyOverview:
        """
        Fetch corporate overview and key fundamental metrics for an equity.

        Args:
            symbol: Ticker symbol.
            exchange: Primary Indian exchange ('NSE' or 'BSE').

        Returns:
            CompanyOverview object.
        """
        pass
