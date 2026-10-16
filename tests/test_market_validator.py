"""Unit tests for MarketDataValidator."""

from datetime import datetime, timedelta, timezone
import pytest

from app.tools.market.clock import IST, MarketClock
from app.tools.market.interfaces import DataValidationError
from app.tools.market.models import (
    CompanyOverview,
    HistoricalPrices,
    MarketDataProvenance,
    MarketQuote,
)
from app.tools.market.validator import MarketDataValidator


@pytest.fixture
def validator():
    return MarketDataValidator()


def test_validate_quote_success(validator: MarketDataValidator):
    raw_quote = MarketQuote(
        symbol=" reliance ",
        company_name=" Reliance Industries Ltd ",
        exchange="NSE",
        currency="inr",
        price=2985.4049,
        change=15.201,
        change_percent=0.512,
        previous_close=2970.20,
        open=2975.00,
        high=2990.00,
        low=2965.00,
        volume=3500000,
        market_status="regular_trading",
        market_timestamp="2026-09-11T14:30:00+05:30",
        retrieved_at=datetime.now(timezone.utc).isoformat(),
        provider="Yahoo Finance",
    )

    validated = validator.validate_quote(raw_quote)
    assert validated.symbol == "RELIANCE"
    assert validated.company_name == "Reliance Industries Ltd"
    assert validated.currency == "INR"
    assert validated.price == 2985.40
    assert validated.change == 15.20
    assert validated.change_percent == 0.51


def test_validate_quote_negative_or_zero_price(validator: MarketDataValidator):
    zero_quote = MarketQuote(
        symbol="TCS",
        price=0.0,
        market_status="regular_trading",
        market_timestamp="2026-09-11T14:30:00+05:30",
        retrieved_at="2026-09-11T14:31:00+05:30",
        provider="Yahoo Finance",
    )
    with pytest.raises(DataValidationError, match="Invalid non-positive quote price"):
        validator.validate_quote(zero_quote)

    negative_quote = MarketQuote(
        symbol="TCS",
        price=-50.0,
        market_status="regular_trading",
        market_timestamp="2026-09-11T14:30:00+05:30",
        retrieved_at="2026-09-11T14:31:00+05:30",
        provider="Yahoo Finance",
    )
    with pytest.raises(DataValidationError, match="Invalid non-positive quote price"):
        validator.validate_quote(negative_quote)


def test_validate_quote_invalid_high_low(validator: MarketDataValidator):
    inverted_quote = MarketQuote(
        symbol="INFY",
        price=1800.0,
        high=1750.0,  # High lower than low!
        low=1850.0,
        market_status="regular_trading",
        market_timestamp="2026-09-11T14:30:00+05:30",
        retrieved_at="2026-09-11T14:31:00+05:30",
        provider="Yahoo Finance",
    )
    with pytest.raises(DataValidationError, match="cannot be lower than day low"):
        validator.validate_quote(inverted_quote)


def test_validate_quote_price_outside_high_low_bounds(validator: MarketDataValidator):
    # Price exceeding day high
    high_exceeded_quote = MarketQuote(
        symbol="TCS",
        price=4100.0,
        high=4000.0,
        low=3900.0,
        market_status="regular_trading",
        market_timestamp="2026-09-11T14:30:00+05:30",
        retrieved_at="2026-09-11T14:31:00+05:30",
        provider="Yahoo Finance",
    )
    with pytest.raises(DataValidationError, match="cannot exceed day high"):
        validator.validate_quote(high_exceeded_quote)

    # Price below day low
    low_breached_quote = MarketQuote(
        symbol="TCS",
        price=3850.0,
        high=4000.0,
        low=3900.0,
        market_status="regular_trading",
        market_timestamp="2026-09-11T14:30:00+05:30",
        retrieved_at="2026-09-11T14:31:00+05:30",
        provider="Yahoo Finance",
    )
    with pytest.raises(DataValidationError, match="cannot be lower than day low"):
        validator.validate_quote(low_breached_quote)



def test_validate_quote_negative_volume(validator: MarketDataValidator):
    bad_volume_quote = MarketQuote(
        symbol="HDFCBANK",
        price=1650.0,
        volume=-100,
        market_status="regular_trading",
        market_timestamp="2026-09-11T14:30:00+05:30",
        retrieved_at="2026-09-11T14:31:00+05:30",
        provider="Yahoo Finance",
    )
    with pytest.raises(DataValidationError, match="Volume cannot be negative"):
        validator.validate_quote(bad_volume_quote)


def test_freshness_evaluation_market_closed(validator: MarketDataValidator):
    # During weekend (Saturday 2026-09-12 11:00 IST), freshness must be 'last_traded_close'
    dt_closed = datetime(2026, 9, 12, 11, 0, tzinfo=IST)
    retrieved_at = datetime(2026, 9, 11, 15, 30, tzinfo=IST).isoformat()
    freshness = validator.evaluate_freshness(retrieved_at, dt_now=dt_closed)
    assert freshness == "last_traded_close"


def test_freshness_evaluation_market_open(validator: MarketDataValidator):
    # During trading hours (Wednesday 2026-09-16 11:00 IST)
    dt_open = datetime(2026, 9, 16, 11, 0, tzinfo=IST)

    # 1. Fresh quote fetched 5 minutes ago -> 'delayed'
    recent_iso = (dt_open - timedelta(minutes=5)).astimezone(timezone.utc).isoformat()
    fresh_status = validator.evaluate_freshness(recent_iso, dt_now=dt_open)
    assert fresh_status == "delayed"

    # 2. Old quote fetched 45 minutes ago -> 'stale_cached_fallback'
    stale_iso = (dt_open - timedelta(minutes=45)).astimezone(timezone.utc).isoformat()
    stale_status = validator.evaluate_freshness(stale_iso, dt_now=dt_open)
    assert stale_status == "stale_cached_fallback"


def test_historical_prices_validation(validator: MarketDataValidator):
    valid_hist = HistoricalPrices(
        symbol="RELIANCE",
        period="1mo",
        interval="1d",
        start_date="2026-08-11",
        end_date="2026-09-11",
        start_price=2900.0,
        end_price=2985.0,
        period_change=85.0,
        period_change_percent=2.93,
        period_high=3020.0,
        period_low=2880.0,
        fifty_two_week_high=3200.0,
        fifty_two_week_low=2400.0,
        provider="Yahoo Finance",
        retrieved_at=datetime.now(timezone.utc).isoformat(),
    )
    assert validator.validate_historical(valid_hist) == valid_hist

    # Inverted period high/low
    with pytest.raises(DataValidationError, match="Period high .* cannot be lower than period low"):
        bad_hist = valid_hist.model_copy(update={"period_high": 2700.0, "period_low": 2900.0})
        validator.validate_historical(bad_hist)

    # Non-positive start price
    with pytest.raises(DataValidationError, match="Historical prices must be positive"):
        bad_price_hist = valid_hist.model_copy(update={"start_price": -10.0})
        validator.validate_historical(bad_price_hist)


def test_company_overview_validation(validator: MarketDataValidator):
    valid_overview = CompanyOverview(
        symbol="TCS",
        company_name="Tata Consultancy Services Ltd",
        exchange="NSE",
        currency="INR",
        sector="Technology",
        industry="Information Technology Services",
        market_cap=15000000000000.0,
        pe_ratio=28.5,
        fifty_two_week_high=4500.0,
        fifty_two_week_low=3400.0,
        summary="Leading global IT services and consulting organization.",
        provider="Yahoo Finance",
        retrieved_at=datetime.now(timezone.utc).isoformat(),
    )
    assert validator.validate_overview(valid_overview) == valid_overview

    # Inverted 52-week metrics
    with pytest.raises(DataValidationError, match="52-week high .* cannot be lower than 52-week low"):
        bad_overview = valid_overview.model_copy(update={"fifty_two_week_high": 3000.0, "fifty_two_week_low": 4000.0})
        validator.validate_overview(bad_overview)


def test_create_provenance(validator: MarketDataValidator):
    quote = MarketQuote(
        symbol="RELIANCE",
        company_name="Reliance Industries Limited",
        exchange="NSE",
        currency="INR",
        price=2985.40,
        change=15.20,
        change_percent=0.51,
        previous_close=2970.20,
        open=2975.00,
        high=2990.00,
        low=2965.00,
        volume=3500000,
        market_status="regular_trading",
        market_timestamp="2026-09-11T14:30:00+05:30",
        retrieved_at="2026-09-11T14:31:00+05:30",
        provider="Yahoo Finance",
        freshness_status="delayed",
    )

    prov = validator.create_provenance(quote)
    assert isinstance(prov, MarketDataProvenance)
    assert prov.symbol == "RELIANCE"
    assert prov.price == 2985.40
    assert prov.provider == "Yahoo Finance"
    assert prov.freshness_status == "delayed"
