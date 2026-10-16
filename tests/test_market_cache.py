"""Unit tests for thread-safe MarketDataCache with session-aware TTL and stale fallback."""

import concurrent.futures
from datetime import datetime, timezone
import pytest

from app.tools.market.cache import MarketDataCache
from app.tools.market.clock import IST, MarketClock
from app.tools.market.models import CompanyOverview, HistoricalPrices, MarketQuote


@pytest.fixture
def cache():
    return MarketDataCache()


@pytest.fixture
def sample_quote():
    return MarketQuote(
        symbol="RELIANCE",
        company_name="Reliance Industries Limited",
        exchange="NSE",
        currency="INR",
        price=2985.40,
        change=15.20,
        change_percent=0.51,
        market_status="regular_trading",
        market_timestamp="2026-09-11T14:30:00+05:30",
        retrieved_at=datetime.now(timezone.utc).isoformat(),
        provider="Yahoo Finance",
        freshness_status="delayed",
    )


def test_cache_set_and_get_fresh(cache: MarketDataCache, sample_quote: MarketQuote):
    cache.set_quote("RELIANCE", "NSE", sample_quote, ttl_seconds=10.0)

    val, is_stale = cache.get_quote("RELIANCE", "NSE")
    assert is_stale is False
    assert val is not None
    assert val.symbol == "RELIANCE"
    assert val.price == 2985.40
    assert val.freshness_status == "delayed"


def test_cache_miss_on_expired(cache: MarketDataCache, sample_quote: MarketQuote):
    # Set with negative TTL so it is immediately expired
    cache.set_quote("RELIANCE", "NSE", sample_quote, ttl_seconds=-1.0)

    # Without allow_stale -> returns None
    val, is_stale = cache.get_quote("RELIANCE", "NSE", allow_stale=False)
    assert val is None
    assert is_stale is True


def test_cache_stale_fallback_retrieval(cache: MarketDataCache, sample_quote: MarketQuote):
    # Set with negative TTL so it is immediately expired
    cache.set_quote("RELIANCE", "NSE", sample_quote, ttl_seconds=-1.0)

    # With allow_stale -> returns value with freshness_status marked as stale_cached_fallback
    val, is_stale = cache.get_quote("RELIANCE", "NSE", allow_stale=True)
    assert val is not None
    assert is_stale is True
    assert val.symbol == "RELIANCE"
    assert val.freshness_status == "stale_cached_fallback"


def test_dynamic_ttl_calculation(cache: MarketDataCache):
    # During regular trading (Wednesday 2026-09-16 11:00 IST) -> 60 seconds
    dt_open = datetime(2026, 9, 16, 11, 0, tzinfo=IST)
    ttl_open = cache.calculate_quote_ttl(dt_open)
    assert ttl_open == 60.0

    # During night (Wednesday 2026-09-16 20:00 IST) -> until next open at 09:15 next day (~13.25 hrs, capped at 12h = 43200s)
    dt_night = datetime(2026, 9, 16, 20, 0, tzinfo=IST)
    ttl_night = cache.calculate_quote_ttl(dt_night)
    assert ttl_night > 3600.0


def test_cache_invalidation_and_clear(cache: MarketDataCache, sample_quote: MarketQuote):
    cache.set_quote("RELIANCE", "NSE", sample_quote, ttl_seconds=60.0)
    cache.set_quote("TCS", "NSE", sample_quote.model_copy(update={"symbol": "TCS"}), ttl_seconds=60.0)

    # Invalidate RELIANCE only
    cache.invalidate("quote:NSE:RELIANCE")
    val_rel, _ = cache.get_quote("RELIANCE", "NSE")
    val_tcs, _ = cache.get_quote("TCS", "NSE")
    assert val_rel is None
    assert val_tcs is not None

    # Clear all
    cache.clear()
    val_tcs_after, _ = cache.get_quote("TCS", "NSE")
    assert val_tcs_after is None


def test_cache_concurrent_thread_safety(cache: MarketDataCache, sample_quote: MarketQuote):
    def worker(worker_id: int):
        sym = f"SYM{worker_id % 10}"
        q = sample_quote.model_copy(update={"symbol": sym, "price": float(worker_id)})
        cache.set_quote(sym, "NSE", q, ttl_seconds=5.0)
        retrieved, _ = cache.get_quote(sym, "NSE")
        assert retrieved is not None
        assert retrieved.symbol == sym

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(worker, i) for i in range(50)]
        for f in concurrent.futures.as_completed(futures):
            f.result()  # Will raise if any thread failed


def test_historical_and_overview_caching(cache: MarketDataCache):
    hist = HistoricalPrices(
        symbol="TCS",
        period="1mo",
        interval="1d",
        start_date="2026-08-11",
        end_date="2026-09-11",
        start_price=4100.0,
        end_price=4250.0,
        period_change=150.0,
        period_change_percent=3.66,
        period_high=4300.0,
        period_low=4050.0,
        provider="Yahoo Finance",
        retrieved_at=datetime.now(timezone.utc).isoformat(),
    )
    cache.set_historical("TCS", "NSE", hist, ttl_seconds=3600.0)
    cached_hist, is_stale = cache.get_historical("TCS", "NSE")
    assert is_stale is False
    assert cached_hist is not None
    assert cached_hist.symbol == "TCS"
    assert cached_hist.period_change == 150.0

    overview = CompanyOverview(
        symbol="INFY",
        company_name="Infosys Ltd",
        exchange="NSE",
        currency="INR",
        sector="Technology",
        summary="IT services provider",
        provider="Yahoo Finance",
        retrieved_at=datetime.now(timezone.utc).isoformat(),
    )
    cache.set_overview("INFY", "NSE", overview, ttl_seconds=86400.0)
    cached_ov, is_stale_ov = cache.get_overview("INFY", "NSE")
    assert is_stale_ov is False
    assert cached_ov is not None
    assert cached_ov.symbol == "INFY"
    assert cached_ov.sector == "Technology"
