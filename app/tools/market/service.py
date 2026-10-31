"""Market Data Service Orchestrator for Indian Equities (NSE / BSE).

Orchestrates:
1. Cache lookup (fresh hit)
2. Primary provider query (Yahoo Finance)
3. Secondary provider failover (Twelve Data, if configured)
4. Multi-stage validation and normalization (MarketDataValidator)
5. Stale-data fallback retrieval upon provider transient outage
"""

from __future__ import annotations

import logging
from typing import Literal

from app.tools.market.cache import MarketDataCache
from app.tools.market.clock import MarketClock
from app.tools.market.interfaces import (
    BaseMarketDataProvider,
    MarketDataError,
    ProviderUnavailableError,
    RateLimitExceededError,
    SymbolNotFoundError,
)
from app.tools.market.models import (
    CompanyOverview,
    HistoricalPrices,
    MarketQuote,
    MarketStatus,
)
from app.tools.market.providers.twelve_data_provider import TwelveDataProvider
from app.tools.market.providers.yfinance_provider import YahooFinanceProvider
from app.tools.market.validator import MarketDataValidator

logger = logging.getLogger(__name__)


class MarketDataService:
    """Unified service for fetching live quotes, historical data, and fundamentals."""

    def __init__(
        self,
        primary_provider: BaseMarketDataProvider | None = None,
        secondary_provider: BaseMarketDataProvider | None = None,
        cache: MarketDataCache | None = None,
        validator: MarketDataValidator | None = None,
        clock: MarketClock | None = None,
    ) -> None:
        self.clock = clock or MarketClock()
        self.primary_provider = primary_provider or YahooFinanceProvider(clock=self.clock)
        self.secondary_provider = secondary_provider or TwelveDataProvider(clock=self.clock)
        self.cache = cache or MarketDataCache(clock=self.clock)
        self.validator = validator or MarketDataValidator(clock=self.clock)

    def get_market_status(self) -> MarketStatus:
        """Evaluate the current market session status in IST."""
        return self.clock.get_market_status()

    def get_quote(self, symbol: str, exchange: Literal["NSE", "BSE"] = "NSE") -> MarketQuote:
        """Fetch a standardized, validated market quote with caching and fallback.
        
        Workflow:
        1. Check fresh cache
        2. Query primary provider -> validate -> cache -> return
        3. If primary fails with ProviderUnavailable/RateLimit:
           - Try secondary provider (if available) -> validate -> cache -> return
           - Fall back to stale cached entry if available
           - Otherwise re-raise typed exception
        """
        clean_symbol = symbol.strip().upper()

        # 1. Check fresh cache
        cached_quote, is_stale = self.cache.get_quote(clean_symbol, exchange, allow_stale=False)
        if cached_quote is not None and not is_stale:
            return cached_quote

        # 2. Query primary provider
        last_exception: Exception | None = None
        try:
            raw_quote = self.primary_provider.get_quote(clean_symbol, exchange=exchange)
            validated = self.validator.validate_quote(raw_quote)
            self.cache.set_quote(clean_symbol, exchange, validated)
            return validated
        except SymbolNotFoundError:
            # Re-raise symbol not found directly (no failover needed for invalid symbol)
            raise
        except (ProviderUnavailableError, RateLimitExceededError, MarketDataError) as exc:
            logger.warning(
                "Primary provider %s failed for %s:%s: %s",
                self.primary_provider.name,
                exchange,
                clean_symbol,
                exc,
            )
            last_exception = exc

        # 3. Failover to secondary provider if available
        if self.secondary_provider and self.secondary_provider.is_available:
            try:
                logger.info("Attempting secondary provider %s for %s", self.secondary_provider.name, clean_symbol)
                raw_quote = self.secondary_provider.get_quote(clean_symbol, exchange=exchange)
                validated = self.validator.validate_quote(raw_quote)
                self.cache.set_quote(clean_symbol, exchange, validated)
                return validated
            except SymbolNotFoundError:
                raise
            except Exception as sec_exc:
                logger.warning(
                    "Secondary provider %s also failed for %s: %s",
                    self.secondary_provider.name,
                    clean_symbol,
                    sec_exc,
                )
                last_exception = sec_exc

        # 4. Fall back to stale cache if available
        stale_quote, is_stale = self.cache.get_quote(clean_symbol, exchange, allow_stale=True)
        if stale_quote is not None:
            logger.warning(
                "Serving stale cached quote for %s due to provider outage: %s",
                clean_symbol,
                last_exception,
            )
            if stale_quote.freshness_status != "stale_cached_fallback":
                stale_quote = stale_quote.model_copy(update={"freshness_status": "stale_cached_fallback"})
            return stale_quote

        # 5. Re-raise if no cache and all providers failed
        if last_exception:
            raise last_exception
        raise ProviderUnavailableError(f"No market data providers available to resolve '{symbol}'")

    def get_historical_summary(
        self, symbol: str, exchange: Literal["NSE", "BSE"] = "NSE"
    ) -> HistoricalPrices:
        """Fetch 1-month daily historical summary with caching and failover."""
        clean_symbol = symbol.strip().upper()

        # 1. Check cache
        cached_hist, is_stale = self.cache.get_historical(clean_symbol, exchange, allow_stale=False)
        if cached_hist is not None and not is_stale:
            return cached_hist

        # 2. Query primary provider
        last_exception: Exception | None = None
        try:
            raw_hist = self.primary_provider.get_historical_summary(
                clean_symbol, period="1mo", interval="1d", exchange=exchange
            )
            validated = self.validator.validate_historical(raw_hist)
            self.cache.set_historical(clean_symbol, exchange, validated)
            return validated
        except SymbolNotFoundError:
            raise
        except (ProviderUnavailableError, RateLimitExceededError, MarketDataError) as exc:
            logger.warning("Primary provider historical query failed for %s: %s", clean_symbol, exc)
            last_exception = exc

        # 3. Failover to secondary provider
        if self.secondary_provider and self.secondary_provider.is_available:
            try:
                raw_hist = self.secondary_provider.get_historical_summary(
                    clean_symbol, period="1mo", interval="1d", exchange=exchange
                )
                validated = self.validator.validate_historical(raw_hist)
                self.cache.set_historical(clean_symbol, exchange, validated)
                return validated
            except SymbolNotFoundError:
                raise
            except Exception as sec_exc:
                logger.warning("Secondary provider historical query failed for %s: %s", clean_symbol, sec_exc)
                last_exception = sec_exc

        # 4. Fall back to stale cache
        stale_hist, _ = self.cache.get_historical(clean_symbol, exchange, allow_stale=True)
        if stale_hist is not None:
            logger.warning("Serving stale historical summary for %s", clean_symbol)
            return stale_hist

        if last_exception:
            raise last_exception
        raise ProviderUnavailableError(f"Failed to fetch historical summary for '{symbol}'")

    def get_company_overview(
        self, symbol: str, exchange: Literal["NSE", "BSE"] = "NSE"
    ) -> CompanyOverview:
        """Fetch corporate fundamental profile with 24-hour caching and failover."""
        clean_symbol = symbol.strip().upper()

        cached_ov, is_stale = self.cache.get_overview(clean_symbol, exchange, allow_stale=False)
        if cached_ov is not None and not is_stale:
            return cached_ov

        last_exception: Exception | None = None
        try:
            raw_ov = self.primary_provider.get_company_overview(clean_symbol, exchange=exchange)
            validated = self.validator.validate_overview(raw_ov)
            self.cache.set_overview(clean_symbol, exchange, validated)
            return validated
        except SymbolNotFoundError:
            raise
        except (ProviderUnavailableError, RateLimitExceededError, MarketDataError) as exc:
            logger.warning("Primary provider overview query failed for %s: %s", clean_symbol, exc)
            last_exception = exc

        if self.secondary_provider and self.secondary_provider.is_available:
            try:
                raw_ov = self.secondary_provider.get_company_overview(clean_symbol, exchange=exchange)
                validated = self.validator.validate_overview(raw_ov)
                self.cache.set_overview(clean_symbol, exchange, validated)
                return validated
            except SymbolNotFoundError:
                raise
            except Exception as sec_exc:
                logger.warning("Secondary provider overview query failed for %s: %s", clean_symbol, sec_exc)
                last_exception = sec_exc

        stale_ov, _ = self.cache.get_overview(clean_symbol, exchange, allow_stale=True)
        if stale_ov is not None:
            logger.warning("Serving stale company overview for %s", clean_symbol)
            return stale_ov

        if last_exception:
            raise last_exception
        raise ProviderUnavailableError(f"Failed to fetch company overview for '{symbol}'")
