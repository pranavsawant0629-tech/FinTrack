"""Unit and provider integration tests for Yahoo Finance and Twelve Data providers."""

import math
from unittest.mock import MagicMock, patch
import pytest

from app.tools.market.interfaces import (
    ProviderUnavailableError,
    RateLimitExceededError,
    SymbolNotFoundError,
)
from app.tools.market.models import CompanyOverview, HistoricalPrices, MarketQuote
from app.tools.market.providers.twelve_data_provider import TwelveDataProvider
from app.tools.market.providers.yfinance_provider import (
    YahooFinanceProvider,
    normalize_indian_symbol,
)


def test_symbol_normalization():
    # Plain ticker defaults to NSE .NS
    yf_sym, base, exch = normalize_indian_symbol("RELIANCE")
    assert yf_sym == "RELIANCE.NS"
    assert base == "RELIANCE"
    assert exch == "NSE"

    # Explicit .NS suffix
    yf_sym, base, exch = normalize_indian_symbol("TCS.NS")
    assert yf_sym == "TCS.NS"
    assert base == "TCS"
    assert exch == "NSE"

    # BSE requested
    yf_sym, base, exch = normalize_indian_symbol("INFY", exchange="BSE")
    assert yf_sym == "INFY.BO"
    assert base == "INFY"
    assert exch == "BSE"

    # Indices
    yf_sym, base, exch = normalize_indian_symbol("NIFTY 50")
    assert yf_sym == "^NSEI"
    assert exch == "NSE"

    yf_sym, base, exch = normalize_indian_symbol("SENSEX")
    assert yf_sym == "^BSESN"
    assert exch == "BSE"


def test_yfinance_provider_get_quote_live_or_mocked():
    provider = YahooFinanceProvider()
    assert provider.name == "Yahoo Finance"
    assert provider.is_available is True

    # Test live query against a blue-chip Indian stock
    try:
        quote = provider.get_quote("RELIANCE")
        assert isinstance(quote, MarketQuote)
        assert quote.symbol == "RELIANCE"
        assert quote.exchange == "NSE"
        assert quote.currency == "INR"
        assert quote.price > 0.0
        assert quote.provider == "Yahoo Finance"
        assert quote.market_status in ("pre_open", "regular_trading", "post_closing", "closed")
    except ProviderUnavailableError:
        pytest.skip("External Yahoo Finance network connectivity unavailable")


def test_yfinance_provider_get_historical_summary():
    provider = YahooFinanceProvider()

    try:
        hist = provider.get_historical_summary("RELIANCE")
        assert isinstance(hist, HistoricalPrices)
        assert hist.symbol == "RELIANCE"
        assert hist.period == "1mo"
        assert hist.interval == "1d"
        assert hist.start_price > 0
        if math.isnan(hist.end_price):
            pytest.skip("Yahoo Finance returned an incomplete intraday bar with NaN close price")
        assert hist.end_price > 0
        assert hist.period_high >= hist.period_low
        assert hist.provider == "Yahoo Finance"
        # Verify strict absence of technical indicators
        data_keys = set(hist.model_dump().keys())
        assert "rsi" not in data_keys
        assert "macd" not in data_keys
        assert "sma" not in data_keys
    except ProviderUnavailableError:
        pytest.skip("External Yahoo Finance network connectivity unavailable")


def test_yfinance_provider_symbol_not_found():
    provider = YahooFinanceProvider()
    with pytest.raises(SymbolNotFoundError):
        provider.get_quote("NON_EXISTENT_TICKER_XYZ_9999")


def test_twelve_data_unconfigured_availability():
    # Without API key, provider reports unavailable and rejects operations gracefully
    provider = TwelveDataProvider(api_key=None)
    assert provider.is_available is False

    with pytest.raises(ProviderUnavailableError, match="not configured"):
        provider.get_quote("RELIANCE")

    with pytest.raises(ProviderUnavailableError, match="not configured"):
        provider.get_historical_summary("RELIANCE")

    with pytest.raises(ProviderUnavailableError, match="not configured"):
        provider.get_company_overview("RELIANCE")


@patch("httpx.Client.get")
def test_twelve_data_mocked_quote_success(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "symbol": "RELIANCE",
        "name": "Reliance Industries Limited",
        "exchange": "NSE",
        "currency": "INR",
        "close": "1250.50",
        "previous_close": "1240.00",
        "change": "10.50",
        "percent_change": "0.85",
        "open": "1242.00",
        "high": "1255.00",
        "low": "1238.00",
        "volume": "5400000",
    }
    mock_get.return_value = mock_resp

    provider = TwelveDataProvider(api_key="dummy_test_key")
    assert provider.is_available is True

    quote = provider.get_quote("RELIANCE")
    assert quote.symbol == "RELIANCE"
    assert quote.price == 1250.50
    assert quote.change == 10.50
    assert quote.change_percent == 0.85
    assert quote.provider == "Twelve Data"


@patch("httpx.Client.get")
def test_twelve_data_rate_limit_handling(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 429
    mock_get.return_value = mock_resp

    provider = TwelveDataProvider(api_key="dummy_test_key")
    with pytest.raises(RateLimitExceededError):
        provider.get_quote("RELIANCE")


@patch("httpx.Client.get")
def test_twelve_data_symbol_not_found(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "status": "error",
        "code": 404,
        "message": "symbol not found",
    }
    mock_get.return_value = mock_resp

    provider = TwelveDataProvider(api_key="dummy_test_key")
    with pytest.raises(SymbolNotFoundError):
        provider.get_quote("INVALID_TICKER")
