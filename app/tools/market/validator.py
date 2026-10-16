"""Deterministic Multi-Stage Market Data Validation Pipeline.

Enforces:
1. Schema conformity (Pydantic types)
2. Normalization (rounding, uppercase tickers, standard currencies)
3. Sanity checks (positive prices, high >= low, reasonable range)
4. Freshness classification (realtime, delayed, last_traded_close, stale_cached_fallback)
5. Provenance tracking (provider, timestamps, reference link)
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
from typing import Literal

from app.tools.market.clock import IST, MarketClock
from app.tools.market.interfaces import DataValidationError
from app.tools.market.models import (
    CompanyOverview,
    FreshnessStatusType,
    HistoricalPrices,
    MarketDataProvenance,
    MarketQuote,
)

logger = logging.getLogger(__name__)


class MarketDataValidator:
    """Multi-stage deterministic validation gate for live market data."""

    def __init__(self, clock: MarketClock | None = None) -> None:
        self.clock = clock or MarketClock()

    def evaluate_freshness(
        self,
        retrieved_at_iso: str,
        market_timestamp_iso: str | None = None,
        dt_now: datetime | None = None,
    ) -> FreshnessStatusType:
        """Determine data freshness based on market session state and data timestamp.
        
        Rules:
        - If market is currently CLOSED (night, weekend, holiday): freshness is 'last_traded_close'.
        - If market is currently OPEN:
          - If age <= 30 minutes from retrieved_at: 'delayed' (standard 15m delayed exchange feed).
          - If age > 30 minutes: 'stale_cached_fallback'.
        """
        now = dt_now or self.clock.get_ist_now()
        is_open = self.clock.is_market_open(now)

        if not is_open:
            return "last_traded_close"

        try:
            retrieved_dt = datetime.fromisoformat(retrieved_at_iso)
            if retrieved_dt.tzinfo is None:
                retrieved_dt = retrieved_dt.replace(tzinfo=timezone.utc)
            now_utc = now.astimezone(timezone.utc)
            age_seconds = (now_utc - retrieved_dt).total_seconds()
            if age_seconds <= 1800:  # 30 minutes
                return "delayed"
            return "stale_cached_fallback"
        except Exception:
            return "delayed"

    def validate_quote(self, quote: MarketQuote, dt_now: datetime | None = None) -> MarketQuote:
        """Perform comprehensive sanity and normalization checks on a MarketQuote.
        
        Raises:
            DataValidationError: If any sanity check fails.
        """
        # 1. Price Sanity Check
        if math.isnan(quote.price) or math.isinf(quote.price) or quote.price <= 0.0:
            raise DataValidationError(f"Invalid non-positive quote price: {quote.price} for {quote.symbol}")

        # 2. High / Low Sanity
        for bound_name, bound_val in [("high", quote.high), ("low", quote.low), ("open", quote.open), ("previous_close", quote.previous_close)]:
            if bound_val is not None and (math.isnan(bound_val) or math.isinf(bound_val)):
                raise DataValidationError(f"Invalid non-finite {bound_name}: {bound_val} for {quote.symbol}")

        if quote.high is not None and quote.low is not None:
            if quote.high < quote.low:
                raise DataValidationError(
                    f"Day high ({quote.high}) cannot be lower than day low ({quote.low}) for {quote.symbol}"
                )
        if quote.high is not None and round(quote.price, 2) > round(quote.high, 2):
            raise DataValidationError(
                f"Quote price ({quote.price}) cannot exceed day high ({quote.high}) for {quote.symbol}"
            )
        if quote.low is not None and round(quote.price, 2) < round(quote.low, 2):
            raise DataValidationError(
                f"Quote price ({quote.price}) cannot be lower than day low ({quote.low}) for {quote.symbol}"
            )

        # 3. Previous Close Sanity
        if quote.previous_close is not None and quote.previous_close <= 0.0:
            raise DataValidationError(
                f"Invalid non-positive previous close: {quote.previous_close} for {quote.symbol}"
            )

        # 4. Volume Sanity
        if quote.volume is not None and quote.volume < 0:
            raise DataValidationError(f"Volume cannot be negative: {quote.volume} for {quote.symbol}")

        # 5. Evaluate Freshness
        freshness = self.evaluate_freshness(quote.retrieved_at, quote.market_timestamp, dt_now=dt_now)

        # 6. Return Normalized Copy
        return MarketQuote(
            symbol=quote.symbol.strip().upper(),
            company_name=quote.company_name.strip(),
            exchange=quote.exchange,
            currency=quote.currency.strip().upper(),
            price=round(float(quote.price), 2),
            change=round(float(quote.change), 2),
            change_percent=round(float(quote.change_percent), 2),
            previous_close=round(float(quote.previous_close), 2) if quote.previous_close else None,
            open=round(float(quote.open), 2) if quote.open else None,
            high=round(float(quote.high), 2) if quote.high else None,
            low=round(float(quote.low), 2) if quote.low else None,
            volume=quote.volume,
            market_status=quote.market_status,
            market_timestamp=quote.market_timestamp,
            retrieved_at=quote.retrieved_at,
            provider=quote.provider,
            source_url=quote.source_url,
            freshness_status=freshness,
        )

    def validate_historical(self, hist: HistoricalPrices) -> HistoricalPrices:
        """Validate historical summary metrics.
        
        Raises:
            DataValidationError: If start/end prices or high/low bounds are nonsensical.
        """
        for field_name, field_val in [
            ("start_price", hist.start_price),
            ("end_price", hist.end_price),
            ("period_high", hist.period_high),
            ("period_low", hist.period_low),
            ("fifty_two_week_high", hist.fifty_two_week_high),
            ("fifty_two_week_low", hist.fifty_two_week_low),
        ]:
            if field_val is not None and (math.isnan(field_val) or math.isinf(field_val)):
                raise DataValidationError(f"Invalid non-finite historical {field_name}: {field_val} for {hist.symbol}")

        if hist.start_price <= 0.0 or hist.end_price <= 0.0:
            raise DataValidationError(f"Historical prices must be positive for {hist.symbol}")

        if hist.period_high < hist.period_low:
            raise DataValidationError(
                f"Period high ({hist.period_high}) cannot be lower than period low ({hist.period_low}) for {hist.symbol}"
            )

        if hist.fifty_two_week_high is not None and hist.fifty_two_week_low is not None:
            if hist.fifty_two_week_high < hist.fifty_two_week_low:
                raise DataValidationError(
                    f"52-week high ({hist.fifty_two_week_high}) cannot be lower than 52-week low ({hist.fifty_two_week_low})"
                )

        return hist

    def validate_overview(self, overview: CompanyOverview) -> CompanyOverview:
        """Validate company fundamental profile."""
        if not overview.symbol:
            raise DataValidationError("CompanyOverview symbol cannot be empty")

        for field_name, field_val in [
            ("market_cap", overview.market_cap),
            ("pe_ratio", overview.pe_ratio),
            ("fifty_two_week_high", overview.fifty_two_week_high),
            ("fifty_two_week_low", overview.fifty_two_week_low),
        ]:
            if field_val is not None and (math.isnan(field_val) or math.isinf(field_val)):
                raise DataValidationError(f"Invalid non-finite overview {field_name}: {field_val} for {overview.symbol}")

        if overview.market_cap is not None and overview.market_cap < 0:
            raise DataValidationError(f"Market cap cannot be negative: {overview.market_cap}")

        if overview.fifty_two_week_high is not None and overview.fifty_two_week_low is not None:
            if overview.fifty_two_week_high < overview.fifty_two_week_low:
                raise DataValidationError(
                    f"52-week high ({overview.fifty_two_week_high}) cannot be lower than 52-week low ({overview.fifty_two_week_low})"
                )

        return overview

    def create_provenance(self, quote: MarketQuote) -> MarketDataProvenance:
        """Convert a validated MarketQuote into a MarketDataProvenance record."""
        return MarketDataProvenance(
            symbol=quote.symbol,
            company_name=quote.company_name,
            exchange=quote.exchange,
            currency=quote.currency,
            price=quote.price,
            change=quote.change,
            change_percent=quote.change_percent,
            previous_close=quote.previous_close,
            open=quote.open,
            high=quote.high,
            low=quote.low,
            volume=quote.volume,
            market_status=quote.market_status,
            market_timestamp=quote.market_timestamp,
            retrieved_at=quote.retrieved_at,
            provider=quote.provider,
            source_url=quote.source_url,
            freshness_status=quote.freshness_status,
        )
