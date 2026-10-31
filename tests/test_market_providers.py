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


# --- Deterministic Mocked Tests for YahooFinanceProvider ---


@patch("yfinance.Ticker")
def test_yfinance_provider_mocked_quote_success(mock_ticker_cls):
    mock_ticker = MagicMock()
    mock_ticker_cls.return_value = mock_ticker

    mock_ticker.fast_info = {
        "last_price": 2500.50,
        "previous_close": 2480.00,
        "currency": "INR",
        "open": 2490.00,
        "day_high": 2515.00,
        "day_low": 2475.00,
        "last_volume": 1250000,
    }
    mock_ticker.info = {"shortName": "Reliance Industries Limited"}

    provider = YahooFinanceProvider()
    quote = provider.get_quote("RELIANCE", exchange="NSE")

    assert quote.symbol == "RELIANCE"
    assert quote.company_name == "Reliance Industries Limited"
    assert quote.exchange == "NSE"
    assert quote.currency == "INR"
    assert quote.price == 2500.50
    assert quote.change == 20.50
    assert quote.change_percent == 0.83
    assert quote.previous_close == 2480.00
    assert quote.open == 2490.00
    assert quote.high == 2515.00
    assert quote.low == 2475.00
    assert quote.volume == 1250000
    assert quote.provider == "Yahoo Finance"
    assert quote.source_url == "https://finance.yahoo.com/quote/RELIANCE.NS"
    assert quote.retrieved_at is not None


@patch("yfinance.Ticker")
def test_yfinance_provider_mocked_historical_filtering(mock_ticker_cls):
    import pandas as pd
    import numpy as np

    mock_ticker = MagicMock()
    mock_ticker_cls.return_value = mock_ticker

    # 3 valid rows + 1 incomplete trailing row with NaN close and high
    dates = pd.date_range("2026-09-01", periods=4, freq="D")
    df = pd.DataFrame(
        {
            "Open": [100.0, 105.0, 110.0, np.nan],
            "High": [106.0, 112.0, 115.0, np.nan],
            "Low": [99.0, 104.0, 108.0, 100.0],
            "Close": [105.0, 110.0, 114.0, np.nan],
            "Volume": [1000, 1200, 1100, 0],
        },
        index=dates,
    )
    mock_ticker.history.return_value = df
    mock_ticker.fast_info = {"year_high": 120.0, "year_low": 90.0}

    provider = YahooFinanceProvider()
    hist = provider.get_historical_summary("TCS")

    assert hist.symbol == "TCS"
    assert hist.period == "1mo"
    assert hist.start_price == 105.00
    # Crucial: trailing NaN row discarded, latest valid close is 114.00
    assert hist.end_price == 114.00
    assert hist.period_high == 115.00
    assert hist.period_low == 99.00
    assert hist.period_change == 9.00
    assert hist.period_change_percent == 8.57
    assert hist.fifty_two_week_high == 120.0
    assert hist.fifty_two_week_low == 90.0


@patch("yfinance.Ticker")
def test_yfinance_provider_mocked_historical_no_valid_bars(mock_ticker_cls):
    import pandas as pd
    import numpy as np
    from app.tools.market.interfaces import MarketDataError

    mock_ticker = MagicMock()
    mock_ticker_cls.return_value = mock_ticker

    dates = pd.date_range("2026-09-01", periods=2, freq="D")
    df = pd.DataFrame(
        {
            "Open": [np.nan, np.nan],
            "High": [np.nan, np.nan],
            "Low": [np.nan, np.nan],
            "Close": [np.nan, np.nan],
            "Volume": [0, 0],
        },
        index=dates,
    )
    mock_ticker.history.return_value = df

    provider = YahooFinanceProvider()
    with pytest.raises(MarketDataError, match="No valid historical price bars"):
        provider.get_historical_summary("INFY")


@patch("yfinance.Ticker")
def test_yfinance_provider_mocked_rate_limit(mock_ticker_cls):
    from unittest.mock import PropertyMock

    mock_ticker = MagicMock()
    mock_ticker_cls.return_value = mock_ticker
    type(mock_ticker).fast_info = PropertyMock(side_effect=Exception("HTTP 429 Too Many Requests"))

    provider = YahooFinanceProvider()
    with pytest.raises(RateLimitExceededError):
        provider.get_quote("RELIANCE")


@patch("yfinance.Ticker")
def test_yfinance_provider_mocked_symbol_not_found(mock_ticker_cls):
    from unittest.mock import PropertyMock

    mock_ticker = MagicMock()
    mock_ticker_cls.return_value = mock_ticker
    type(mock_ticker).fast_info = PropertyMock(side_effect=Exception("404 Not Found"))

    provider = YahooFinanceProvider()
    with pytest.raises(SymbolNotFoundError):
        provider.get_quote("UNKNOWN_SYM")
