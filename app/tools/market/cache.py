"""Thread-Safe In-Memory Market Data TTL Cache with Dynamic Expiration and Stale Fallback.

Provides:
- Short TTL (60s) during regular market trading hours
- Extended TTL (until next session open) when market is closed/weekend/holiday
- 1-hour TTL for historical 1-month summaries
- 24-hour TTL for fundamental company overviews
- Stale-data fallback retrieval upon provider transient outage/rate limit
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Generic, TypeVar

from app.tools.market.clock import MarketClock
from app.tools.market.models import CompanyOverview, HistoricalPrices, MarketQuote

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class CacheEntry(Generic[T]):
    """Container for cached item with expiration metadata."""
    value: T
    expires_at: float  # Unix timestamp
    created_at: float  # Unix timestamp


class MarketDataCache:
    """Thread-safe TTL cache with session-aware expiration and stale fallback."""

    def __init__(self, clock: MarketClock | None = None) -> None:
        self.clock = clock or MarketClock()
        self._lock = threading.Lock()
        self._store: dict[str, CacheEntry[Any]] = {}

    def _make_key(self, data_type: str, symbol: str, exchange: str = "NSE") -> str:
        return f"{data_type}:{exchange.upper()}:{symbol.upper()}"

    def get(self, key: str, allow_stale: bool = False) -> tuple[Any | None, bool]:
        """Retrieve a value by key.
        
        Returns:
            tuple[value | None, is_stale: bool]
        """
        now = time.time()
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None, False

            if now <= entry.expires_at:
                return entry.value, False

            # Expired
            if allow_stale:
                return entry.value, True
            return None, True

    def set(self, key: str, value: Any, ttl_seconds: float) -> None:
        """Store a value with specified TTL."""
        now = time.time()
        entry = CacheEntry(
            value=value,
            expires_at=now + ttl_seconds,
            created_at=now,
        )
        with self._lock:
            self._store[key] = entry

    def clear(self) -> None:
        """Clear all cached entries."""
        with self._lock:
            self._store.clear()

    def invalidate(self, key: str) -> None:
        """Remove a specific key."""
        with self._lock:
            self._store.pop(key, None)

    # --- Session-Aware Quote Helpers ---

    def calculate_quote_ttl(self, dt: datetime | None = None) -> float:
        """Calculate dynamic TTL for a quote.
        
        - 60 seconds if market is in regular trading session
        - Time until next market open (capped at 12 hours) if market is closed
        """
        now = dt or self.clock.get_ist_now()
        session = self.clock.get_session(now)

        if session == "regular_trading":
            return 60.0  # 1 minute

        # Market is closed, pre-open, or post-close
        next_open = self.clock.get_next_open(now)
        seconds_to_open = (next_open - now).total_seconds()
        if seconds_to_open > 0:
            return min(seconds_to_open, 43200.0)  # Max 12 hours
        return 60.0

    def get_quote(
        self, symbol: str, exchange: str = "NSE", allow_stale: bool = False
    ) -> tuple[MarketQuote | None, bool]:
        key = self._make_key("quote", symbol, exchange)
        val, is_stale = self.get(key, allow_stale=allow_stale)
        if isinstance(val, MarketQuote):
            if is_stale:
                # Mark as stale fallback
                val = val.model_copy(update={"freshness_status": "stale_cached_fallback"})
            return val, is_stale
        return None, is_stale

    def set_quote(
        self, symbol: str, exchange: str, quote: MarketQuote, ttl_seconds: float | None = None
    ) -> None:
        key = self._make_key("quote", symbol, exchange)
        ttl = ttl_seconds if ttl_seconds is not None else self.calculate_quote_ttl()
        self.set(key, quote, ttl)

    # --- Historical Prices Helpers ---

    def get_historical(
        self, symbol: str, exchange: str = "NSE", allow_stale: bool = False
    ) -> tuple[HistoricalPrices | None, bool]:
        key = self._make_key("historical", symbol, exchange)
        val, is_stale = self.get(key, allow_stale=allow_stale)
        if isinstance(val, HistoricalPrices):
            return val, is_stale
        return None, is_stale

    def set_historical(
        self, symbol: str, exchange: str, hist: HistoricalPrices, ttl_seconds: float = 3600.0
    ) -> None:
        """1-hour default TTL for 1-month daily historical summaries."""
        key = self._make_key("historical", symbol, exchange)
        self.set(key, hist, ttl_seconds)

    # --- Company Overview Helpers ---

    def get_overview(
        self, symbol: str, exchange: str = "NSE", allow_stale: bool = False
    ) -> tuple[CompanyOverview | None, bool]:
        key = self._make_key("overview", symbol, exchange)
        val, is_stale = self.get(key, allow_stale=allow_stale)
        if isinstance(val, CompanyOverview):
            return val, is_stale
        return None, is_stale

    def set_overview(
        self, symbol: str, exchange: str, overview: CompanyOverview, ttl_seconds: float = 86400.0
    ) -> None:
        """24-hour default TTL for company profiles/fundamentals."""
        key = self._make_key("overview", symbol, exchange)
        self.set(key, overview, ttl_seconds)
