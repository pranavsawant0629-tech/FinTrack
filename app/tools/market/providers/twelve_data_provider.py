"""Twelve Data Market Data Provider (Optional Secondary Fallback).

Implements BaseMarketDataProvider for Indian equities.
Requires TWELVE_DATA_API_KEY environment variable. If unconfigured,
is_available evaluates to False without impeding normal system operation.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Literal

import httpx

from app.tools.market.clock import IST, MarketClock
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
)

logger = logging.getLogger(__name__)


class TwelveDataProvider(BaseMarketDataProvider):
    """Optional Twelve Data provider fallback."""

    def __init__(self, api_key: str | None = None, clock: MarketClock | None = None) -> None:
        self.api_key = api_key or os.getenv("TWELVE_DATA_API_KEY")
        self.clock = clock or MarketClock()
        self.base_url = "https://api.twelvedata.com"

    @property
    def name(self) -> str:
        return "Twelve Data"

    @property
    def is_available(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    def _ensure_available(self) -> None:
        if not self.is_available:
            raise ProviderUnavailableError(
                "Twelve Data provider is unavailable: TWELVE_DATA_API_KEY is not configured."
            )

    def get_quote(
        self, symbol: str, exchange: Literal["NSE", "BSE"] = "NSE"
    ) -> MarketQuote:
        self._ensure_available()
        clean_symbol = symbol.strip().upper()
        clean_exchange: Literal["NSE", "BSE"] = "BSE" if exchange.upper() == "BSE" else "NSE"

        url = f"{self.base_url}/quote"
        params = {
            "symbol": clean_symbol,
            "exchange": clean_exchange,
            "apikey": self.api_key,
        }

        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(url, params=params)
        except Exception as exc:
            raise ProviderUnavailableError(f"Twelve Data connection failed: {exc}") from exc

        if resp.status_code == 429:
            raise RateLimitExceededError("Twelve Data API rate limit reached.")
        if resp.status_code != 200:
            raise ProviderUnavailableError(f"Twelve Data HTTP error: {resp.status_code}")

        data = resp.json()
        if data.get("status") == "error" or "code" in data:
            code = data.get("code")
            msg = data.get("message", "")
            if code == 404 or "not found" in msg.lower():
                raise SymbolNotFoundError(f"Symbol '{symbol}' not found on {exchange}: {msg}")
            if code == 429:
                raise RateLimitExceededError(f"Twelve Data rate limit: {msg}")
            raise MarketDataError(f"Twelve Data error: {msg}")

        try:
            price = float(data["close"])
            prev_close = float(data.get("previous_close", price))
            change = float(data.get("change", round(price - prev_close, 2)))
            change_pct = float(data.get("percent_change", 0.0))
            open_price = float(data["open"]) if data.get("open") else None
            high = float(data["high"]) if data.get("high") else None
            low = float(data["low"]) if data.get("low") else None
            vol = int(data["volume"]) if data.get("volume") else None
        except (KeyError, ValueError) as exc:
            raise MarketDataError(f"Malformed quote response from Twelve Data: {exc}") from exc

        now_ist = datetime.now(IST)
        session_type = self.clock.get_session(now_ist)

        return MarketQuote(
            symbol=clean_symbol,
            company_name=data.get("name", clean_symbol),
            exchange=clean_exchange,
            currency=data.get("currency", "INR"),
            price=price,
            change=change,
            change_percent=change_pct,
            previous_close=prev_close,
            open=open_price,
            high=high,
            low=low,
            volume=vol,
            market_status=session_type,
            market_timestamp=now_ist.isoformat(),
            retrieved_at=datetime.now(timezone.utc).isoformat(),
            provider=self.name,
            source_url="https://twelvedata.com",
        )

    def get_historical_summary(
        self,
        symbol: str,
        period: str = "1mo",
        interval: str = "1d",
        exchange: Literal["NSE", "BSE"] = "NSE",
    ) -> HistoricalPrices:
        self._ensure_available()
        clean_symbol = symbol.strip().upper()
        clean_exchange: Literal["NSE", "BSE"] = "BSE" if exchange.upper() == "BSE" else "NSE"

        url = f"{self.base_url}/time_series"
        # 1 month ~ 22 trading days
        params = {
            "symbol": clean_symbol,
            "exchange": clean_exchange,
            "interval": "1day",
            "outputsize": 30,
            "apikey": self.api_key,
        }

        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(url, params=params)
        except Exception as exc:
            raise ProviderUnavailableError(f"Twelve Data connection failed: {exc}") from exc

        data = resp.json()
        values = data.get("values", [])
        if not values:
            raise SymbolNotFoundError(f"No historical data found for '{symbol}'")

        ordered = list(reversed(values))  # chronological order
        start_date = ordered[0]["datetime"][:10]
        end_date = ordered[-1]["datetime"][:10]
        start_price = float(ordered[0]["close"])
        end_price = float(ordered[-1]["close"])
        period_change = round(end_price - start_price, 2)
        period_change_percent = round((period_change / start_price) * 100, 2) if start_price else 0.0
        period_high = max(float(r["high"]) for r in ordered)
        period_low = min(float(r["low"]) for r in ordered)

        return HistoricalPrices(
            symbol=clean_symbol,
            period="1mo",
            interval="1d",
            start_date=start_date,
            end_date=end_date,
            start_price=start_price,
            end_price=end_price,
            period_change=period_change,
            period_change_percent=period_change_percent,
            period_high=period_high,
            period_low=period_low,
            provider=self.name,
            retrieved_at=datetime.now(timezone.utc).isoformat(),
        )

    def get_company_overview(
        self, symbol: str, exchange: Literal["NSE", "BSE"] = "NSE"
    ) -> CompanyOverview:
        self._ensure_available()
        clean_symbol = symbol.strip().upper()
        clean_exchange: Literal["NSE", "BSE"] = "BSE" if exchange.upper() == "BSE" else "NSE"

        url = f"{self.base_url}/profile"
        params = {
            "symbol": clean_symbol,
            "exchange": clean_exchange,
            "apikey": self.api_key,
        }

        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(url, params=params)
        except Exception as exc:
            raise ProviderUnavailableError(f"Twelve Data profile request failed: {exc}") from exc

        data = resp.json()
        return CompanyOverview(
            symbol=clean_symbol,
            company_name=data.get("name", clean_symbol),
            exchange=clean_exchange,
            currency="INR",
            sector=data.get("sector", ""),
            industry=data.get("industry", ""),
            summary=data.get("description", ""),
            provider=self.name,
            retrieved_at=datetime.now(timezone.utc).isoformat(),
        )
