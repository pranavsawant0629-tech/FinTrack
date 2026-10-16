"""
CoinGecko implementation of BaseCryptoProvider.
Uses free public CoinGecko endpoints without requiring paid API keys.
Includes offline fallback data for resilient development and hermetic testing.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
import httpx

from app.tools.crypto.interfaces import BaseCryptoProvider, CryptoAssetNotFoundError, CryptoProviderError
from app.tools.crypto.models import CryptoQuote

logger = logging.getLogger(__name__)

# Canonical Symbol -> CoinGecko API ID & Name
COINGECKO_ASSET_MAP: dict[str, tuple[str, str]] = {
    "BTC": ("bitcoin", "Bitcoin"),
    "ETH": ("ethereum", "Ethereum"),
    "SOL": ("solana", "Solana"),
    "USDT": ("tether", "Tether"),
    "DOGE": ("dogecoin", "Dogecoin"),
    "XRP": ("ripple", "XRP"),
    "ADA": ("cardano", "Cardano"),
    "BNB": ("binancecoin", "BNB"),
}

# Offline / Sandbox fallback values for tests and network isolation
FALLBACK_PRICES: dict[str, tuple[float, float, float]] = {
    # symbol: (usd_price, inr_price, change_24h)
    "BTC": (68500.0, 5750000.0, 2.15),
    "ETH": (3800.0, 319000.0, -0.85),
    "SOL": (175.0, 14700.0, 4.30),
    "USDT": (1.0, 84.0, 0.02),
    "DOGE": (0.15, 12.6, -1.20),
    "XRP": (0.58, 48.7, 1.10),
    "ADA": (0.45, 37.8, 0.50),
    "BNB": (590.0, 49560.0, 1.80),
}


class CoinGeckoProvider(BaseCryptoProvider):
    """Free CoinGecko public API provider with network timeout and offline resilience."""

    def __init__(self, timeout: float = 5.0, allow_offline_fallback: bool = False) -> None:
        self._timeout = timeout
        self._allow_offline_fallback = allow_offline_fallback
        self._client = httpx.Client(timeout=self._timeout)

    @property
    def name(self) -> str:
        return "CoinGecko"

    @property
    def is_available(self) -> bool:
        return True

    def get_quote(self, symbol: str) -> CryptoQuote:
        clean_symbol = symbol.strip().upper()
        if clean_symbol not in COINGECKO_ASSET_MAP:
            raise CryptoAssetNotFoundError(f"Unsupported crypto asset symbol: '{symbol}'")

        cg_id, asset_name = COINGECKO_ASSET_MAP[clean_symbol]
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {
            "ids": cg_id,
            "vs_currencies": "usd,inr",
            "include_24hr_change": "true",
        }

        try:
            resp = self._client.get(url, params=params)
            if resp.status_code == 200:
                data = resp.json()
                if cg_id in data:
                    item = data[cg_id]
                    price_usd = float(item.get("usd", 0.0))
                    price_inr = float(item.get("inr", 0.0)) if "inr" in item else None
                    change_24h = float(item.get("usd_24h_change", 0.0))
                    now_iso = datetime.now(timezone.utc).isoformat()
                    return CryptoQuote(
                        symbol=clean_symbol,
                        name=asset_name,
                        price_usd=price_usd,
                        price_inr=price_inr,
                        change_24h=round(change_24h, 2),
                        market_timestamp=now_iso,
                        retrieved_at=now_iso,
                        provider=self.name,
                        freshness_status="realtime",
                    )
        except Exception as exc:
            logger.warning("CoinGecko live API request failed for %s: %s", clean_symbol, exc)

        # Fallback to local sandbox pricing ONLY if explicitly enabled via test injection
        if self._allow_offline_fallback and clean_symbol in FALLBACK_PRICES:
            fb_usd, fb_inr, fb_chg = FALLBACK_PRICES[clean_symbol]
            # Use fixed historic sandbox timestamp; never disguise test data with datetime.now()
            sandbox_ts = "2024-01-01T00:00:00Z"
            return CryptoQuote(
                symbol=clean_symbol,
                name=asset_name,
                price_usd=fb_usd,
                price_inr=fb_inr,
                change_24h=fb_chg,
                market_timestamp=sandbox_ts,
                retrieved_at=sandbox_ts,
                provider="CoinGecko-Sandbox",
                freshness_status="cached_fallback",
            )

        raise CryptoProviderError(f"CoinGecko service unavailable or rate-limited for crypto symbol '{clean_symbol}'")
