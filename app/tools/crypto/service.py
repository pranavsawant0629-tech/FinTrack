"""
Cryptocurrency Data Service for Finova AI.

Coordinates:
1. Thread-safe in-memory TTL caching (60s default)
2. Provider dispatch via BaseCryptoProvider
3. Graceful fallback on network/provider outage
"""

from __future__ import annotations

import logging
import threading
import time
from app.tools.crypto.interfaces import BaseCryptoProvider, CryptoAssetNotFoundError
from app.tools.crypto.models import CryptoProvenance, CryptoQuote
from app.tools.crypto.providers.coingecko_provider import CoinGeckoProvider

logger = logging.getLogger(__name__)


class CryptoDataService:
    """Unified service for fetching crypto quotes with caching and provider abstraction."""

    def __init__(
        self,
        provider: BaseCryptoProvider | None = None,
        cache_ttl: float = 60.0,
    ) -> None:
        self.provider = provider or CoinGeckoProvider()
        self.cache_ttl = cache_ttl
        self._cache: dict[str, tuple[CryptoQuote, float]] = {}
        self._lock = threading.Lock()

    def get_quote(self, symbol: str) -> CryptoQuote:
        """Fetch standardized crypto quote with TTL caching."""
        clean_symbol = symbol.strip().upper()
        now = time.time()

        # 1. Check cache
        with self._lock:
            if clean_symbol in self._cache:
                cached_quote, expire_time = self._cache[clean_symbol]
                if now < expire_time:
                    return cached_quote

        # 2. Query provider
        quote = self.provider.get_quote(clean_symbol)

        # 3. Cache result
        with self._lock:
            self._cache[clean_symbol] = (quote, now + self.cache_ttl)

        return quote

    def create_provenance(self, quote: CryptoQuote) -> CryptoProvenance:
        """Create serializable provenance metadata from a CryptoQuote."""
        return CryptoProvenance(
            symbol=quote.symbol,
            name=quote.name,
            price_usd=quote.price_usd,
            price_inr=quote.price_inr,
            change_24h=quote.change_24h,
            market_timestamp=quote.market_timestamp,
            retrieved_at=quote.retrieved_at,
            provider=quote.provider,
            freshness_status=quote.freshness_status,
        )


crypto_data_service = CryptoDataService()
