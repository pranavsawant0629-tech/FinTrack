"""
Unit tests for Phase 3A: Market Data Models & Provider Interface.
Validates Pydantic contracts, required fields, literal enums, and ABC enforcement.
"""

import pytest
from pydantic import ValidationError

from app.tools.market.models import (
    MarketQuote,
    HistoricalPrices,
    CompanyOverview,
    MarketStatus,
    MarketDataProvenance,
)
from app.tools.market.interfaces import (
    BaseMarketDataProvider,
    MarketDataError,
    SymbolNotFoundError,
    ProviderUnavailableError,
    RateLimitExceededError,
    DataValidationError,
)


def test_market_quote_valid_instantiation():
    quote = MarketQuote(
        symbol="RELIANCE",
        company_name="Reliance Industries Limited",
        exchange="NSE",
        currency="INR",
        price=2985.40,
        change=14.20,
        change_percent=0.48,
        previous_close=2971.20,
        open=2975.00,
        high=2998.50,
        low=2965.00,
        volume=4821300,
        fifty_two_week_high=3217.90,
        fifty_two_week_low=2220.30,
        market_status="regular_trading",
        market_timestamp="2026-09-11T14:30:00+05:30",
        retrieved_at="2026-09-11T14:31:00+05:30",
        provider="Yahoo Finance",
        source_url="https://finance.yahoo.com/quote/RELIANCE.NS",
        freshness_status="delayed",
    )
    assert quote.symbol == "RELIANCE"
    assert quote.exchange == "NSE"
    assert quote.price == 2985.40
    assert quote.currency == "INR"
    assert quote.market_status == "regular_trading"
    assert quote.volume == 4821300


def test_market_quote_validation_missing_required():
    with pytest.raises(ValidationError):
        # Missing price and symbol
        MarketQuote(  # type: ignore[call-arg]
            exchange="NSE",
            market_status="regular_trading",
            market_timestamp="2026-09-11T14:30:00+05:30",
            retrieved_at="2026-09-11T14:31:00+05:30",
            provider="Yahoo Finance",
        )


def test_market_quote_invalid_exchange_literal():
    with pytest.raises(ValidationError):
        MarketQuote(
            symbol="RELIANCE",
            exchange="NASDAQ",  # type: ignore[arg-type]  # Invalid for Indian equities
            price=2985.40,
            market_status="regular_trading",
            market_timestamp="2026-09-11T14:30:00+05:30",
            retrieved_at="2026-09-11T14:31:00+05:30",
            provider="Yahoo Finance",
        )


def test_historical_prices_model():
    hist = HistoricalPrices(
        symbol="TCS",
        period="1mo",
        interval="1d",
        start_date="2026-08-11",
        end_date="2026-09-11",
        start_price=4100.00,
        end_price=4250.00,
        period_change=150.00,
        period_change_percent=3.66,
        period_high=4300.00,
        period_low=4050.00,
        fifty_two_week_high=4500.00,
        fifty_two_week_low=3400.00,
        provider="Yahoo Finance",
        retrieved_at="2026-09-11T17:00:00+05:30",
    )
    assert hist.symbol == "TCS"
    assert hist.period == "1mo"
    assert hist.period_change == 150.00
    assert hist.period_high == 4300.00


def test_company_overview_model():
    overview = CompanyOverview(
        symbol="INFY",
        company_name="Infosys Limited",
        exchange="NSE",
        currency="INR",
        sector="Technology",
        industry="Information Technology Services",
        market_cap=650000000000.0,
        pe_ratio=28.5,
        fifty_two_week_high=1950.00,
        fifty_two_week_low=1350.00,
        summary="Leading provider of digital services and consulting.",
        provider="Yahoo Finance",
        retrieved_at="2026-09-11T17:00:00+05:30",
    )
    assert overview.symbol == "INFY"
    assert overview.sector == "Technology"
    assert overview.pe_ratio == 28.5


def test_market_status_model():
    status = MarketStatus(
        exchange="NSE",
        is_open=False,
        session_type="closed",
        current_time_ist="2026-09-11T18:00:00+05:30",
        next_session_open_ist="2026-09-14T09:15:00+05:30",
        holiday_name=None,
    )
    assert status.exchange == "NSE"
    assert status.is_open is False
    assert status.session_type == "closed"


def test_market_data_provenance_model():
    prov = MarketDataProvenance(
        symbol="RELIANCE",
        company_name="Reliance Industries Limited",
        exchange="NSE",
        currency="INR",
        price=2985.40,
        change=14.20,
        change_percent=0.48,
        market_status="closed",
        market_timestamp="2026-09-11T15:30:00+05:30",
        retrieved_at="2026-09-11T17:15:00+05:30",
        provider="Yahoo Finance",
        freshness_status="last_traded_close",
    )
    data = prov.model_dump()
    assert data["symbol"] == "RELIANCE"
    assert data["freshness_status"] == "last_traded_close"
    assert data["price"] == 2985.40


def test_abstract_provider_cannot_be_instantiated():
    class IncompleteProvider(BaseMarketDataProvider):
        pass

    with pytest.raises(TypeError):
        IncompleteProvider()  # type: ignore[abstract]


def test_concrete_provider_implementation():
    class MockProvider(BaseMarketDataProvider):
        @property
        def name(self) -> str:
            return "MockProvider"

        @property
        def is_available(self) -> bool:
            return True

        def get_quote(self, symbol: str, exchange: str = "NSE") -> MarketQuote:
            return MarketQuote(
                symbol=symbol,
                exchange="NSE",
                price=100.0,
                market_status="regular_trading",
                market_timestamp="2026-09-11T12:00:00+05:30",
                retrieved_at="2026-09-11T12:00:01+05:30",
                provider=self.name,
            )

        def get_historical_summary(
            self, symbol: str, period: str = "1mo", interval: str = "1d", exchange: str = "NSE"
        ) -> HistoricalPrices:
            return HistoricalPrices(
                symbol=symbol,
                period=period,
                interval=interval,
                start_date="2026-08-11",
                end_date="2026-09-11",
                start_price=90.0,
                end_price=100.0,
                period_change=10.0,
                period_change_percent=11.11,
                period_high=105.0,
                period_low=88.0,
                provider=self.name,
                retrieved_at="2026-09-11T12:00:01+05:30",
            )

        def get_company_overview(self, symbol: str, exchange: str = "NSE") -> CompanyOverview:
            return CompanyOverview(
                symbol=symbol,
                company_name=f"{symbol} Corp",
                exchange="NSE",
                provider=self.name,
                retrieved_at="2026-09-11T12:00:01+05:30",
            )

    provider = MockProvider()
    assert provider.name == "MockProvider"
    assert provider.is_available is True
    quote = provider.get_quote("SBIN")
    assert quote.symbol == "SBIN"
    assert quote.price == 100.0


def test_domain_exceptions_hierarchy():
    assert issubclass(SymbolNotFoundError, MarketDataError)
    assert issubclass(ProviderUnavailableError, MarketDataError)
    assert issubclass(RateLimitExceededError, MarketDataError)
    assert issubclass(DataValidationError, MarketDataError)
