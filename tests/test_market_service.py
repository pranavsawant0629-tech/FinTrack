"""Unit tests for MarketDataService orchestrator (caching, failover, validation, stale fallback)."""

from datetime import datetime, timezone
from unittest.mock import MagicMock
import pytest

from app.tools.market.cache import MarketDataCache
from app.tools.market.clock import MarketClock
from app.tools.market.interfaces import (
    BaseMarketDataProvider,
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
from app.tools.market.service import MarketDataService
from app.tools.market.validator import MarketDataValidator


@pytest.fixture
def mock_clock():
    return MarketClock()


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
        previous_close=2970.20,
        open=2975.00,
        high=2990.00,
        low=2965.00,
        volume=3500000,
        market_status="regular_trading",
        market_timestamp="2026-09-11T14:30:00+05:30",
        retrieved_at=datetime.now(timezone.utc).isoformat(),
        provider="Yahoo Finance",
        freshness_status="delayed",
    )


def test_service_quote_retrieval_and_caching(mock_clock, sample_quote):
    mock_primary = MagicMock(spec=BaseMarketDataProvider)
    mock_primary.name = "MockPrimary"
    mock_primary.is_available = True
    mock_primary.get_quote.return_value = sample_quote

    cache = MarketDataCache(clock=mock_clock)
    validator = MarketDataValidator(clock=mock_clock)
    service = MarketDataService(
        primary_provider=mock_primary,
        cache=cache,
        validator=validator,
        clock=mock_clock,
    )

    # 1. First call queries provider
    quote1 = service.get_quote("RELIANCE")
    assert quote1.symbol == "RELIANCE"
    assert quote1.price == 2985.40
    assert mock_primary.get_quote.call_count == 1

    # 2. Second call hits cache (provider not called again)
    quote2 = service.get_quote("RELIANCE")
    assert quote2.symbol == "RELIANCE"
    assert mock_primary.get_quote.call_count == 1


def test_service_failover_to_secondary_provider(mock_clock, sample_quote):
    mock_primary = MagicMock(spec=BaseMarketDataProvider)
    mock_primary.name = "MockPrimary"
    mock_primary.is_available = True
    mock_primary.get_quote.side_effect = RateLimitExceededError("Rate limit hit")

    mock_secondary = MagicMock(spec=BaseMarketDataProvider)
    mock_secondary.name = "Twelve Data"
    mock_secondary.is_available = True
    secondary_quote = sample_quote.model_copy(update={"provider": "Twelve Data"})
    mock_secondary.get_quote.return_value = secondary_quote

    cache = MarketDataCache(clock=mock_clock)
    validator = MarketDataValidator(clock=mock_clock)
    service = MarketDataService(
        primary_provider=mock_primary,
        secondary_provider=mock_secondary,
        cache=cache,
        validator=validator,
        clock=mock_clock,
    )

    quote = service.get_quote("RELIANCE")
    assert quote.symbol == "RELIANCE"
    assert quote.provider == "Twelve Data"
    assert mock_primary.get_quote.call_count == 1
    assert mock_secondary.get_quote.call_count == 1


def test_service_stale_cache_fallback_on_total_outage(mock_clock, sample_quote):
    mock_primary = MagicMock(spec=BaseMarketDataProvider)
    mock_primary.name = "MockPrimary"
    mock_primary.is_available = True
    mock_primary.get_quote.side_effect = ProviderUnavailableError("Network timeout")

    mock_secondary = MagicMock(spec=BaseMarketDataProvider)
    mock_secondary.is_available = False

    cache = MarketDataCache(clock=mock_clock)
    # Pre-populate cache with an expired entry
    cache.set_quote("RELIANCE", "NSE", sample_quote, ttl_seconds=-1.0)

    validator = MarketDataValidator(clock=mock_clock)
    service = MarketDataService(
        primary_provider=mock_primary,
        secondary_provider=mock_secondary,
        cache=cache,
        validator=validator,
        clock=mock_clock,
    )

    quote = service.get_quote("RELIANCE")
    assert quote.symbol == "RELIANCE"
    assert quote.freshness_status == "stale_cached_fallback"


def test_service_symbol_not_found_propagates_directly(mock_clock):
    mock_primary = MagicMock(spec=BaseMarketDataProvider)
    mock_primary.name = "MockPrimary"
    mock_primary.is_available = True
    mock_primary.get_quote.side_effect = SymbolNotFoundError("Symbol 'XYZ' not found")

    mock_secondary = MagicMock(spec=BaseMarketDataProvider)
    mock_secondary.is_available = True

    service = MarketDataService(
        primary_provider=mock_primary,
        secondary_provider=mock_secondary,
        clock=mock_clock,
    )

    with pytest.raises(SymbolNotFoundError):
        service.get_quote("XYZ")

    # Secondary provider must NOT be attempted if symbol simply doesn't exist
    assert mock_secondary.get_quote.call_count == 0


def test_service_get_market_status(mock_clock):
    service = MarketDataService(clock=mock_clock)
    status = service.get_market_status()
    assert isinstance(status, MarketStatus)
    assert status.exchange == "NSE"
    assert status.session_type in ("pre_open", "regular_trading", "post_closing", "closed")
