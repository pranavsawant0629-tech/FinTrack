"""
Finova AI Market Data Tools Package.
Provides deterministic interfaces and models for market data providers (NSE/BSE).
"""

from app.tools.market.models import (
    MarketQuote,
    HistoricalPrices,
    CompanyOverview,
    MarketStatus,
    MarketDataProvenance,
    MarketStatusType,
    FreshnessStatusType,
)
from app.tools.market.clock import MarketClock
from app.tools.market.interfaces import (
    BaseMarketDataProvider,
    MarketDataError,
    SymbolNotFoundError,
    ProviderUnavailableError,
    RateLimitExceededError,
    DataValidationError,
)

from app.tools.market.cache import MarketDataCache
from app.tools.market.intent import MarketIntentClassifier, MarketIntentResult
from app.tools.market.providers import TwelveDataProvider, YahooFinanceProvider
from app.tools.market.service import MarketDataService
from app.tools.market.validator import MarketDataValidator

__all__ = [
    "MarketQuote",
    "HistoricalPrices",
    "CompanyOverview",
    "MarketStatus",
    "MarketDataProvenance",
    "MarketStatusType",
    "FreshnessStatusType",
    "BaseMarketDataProvider",
    "YahooFinanceProvider",
    "TwelveDataProvider",
    "MarketClock",
    "MarketDataValidator",
    "MarketDataCache",
    "MarketDataService",
    "MarketIntentClassifier",
    "MarketIntentResult",
    "MarketDataError",
    "SymbolNotFoundError",
    "ProviderUnavailableError",
    "RateLimitExceededError",
    "DataValidationError",
]
