"""
Pydantic data schemas for Finova AI Market Data Layer.
Defines strict, deterministic contracts for quotes, historical summaries,
company profiles, market sessions, and provenance tracking.
"""

from typing import Literal
from pydantic import BaseModel, Field

MarketStatusType = Literal["pre_open", "regular_trading", "post_closing", "closed"]
FreshnessStatusType = Literal[
    "realtime",
    "delayed",
    "last_traded_close",
    "stale_cached_fallback",
    "unavailable",
]


class MarketQuote(BaseModel):
    """
    Standardized live or closing quote for an Indian equity or index.
    Validated and normalized across all providers.
    """
    symbol: str = Field(description="Canonical ticker symbol (e.g. 'RELIANCE', 'NIFTY 50')")
    company_name: str = Field(default="", description="Registered company or index name")
    exchange: Literal["NSE", "BSE"] = Field(default="NSE", description="Primary exchange")
    currency: str = Field(default="INR", description="Three-letter currency code")
    price: float = Field(description="Current or last traded price (INR)")
    change: float = Field(default=0.0, description="Absolute change from previous close")
    change_percent: float = Field(default=0.0, description="Percentage change from previous close")
    previous_close: float | None = Field(default=None, description="Previous session closing price")
    open: float | None = Field(default=None, description="Day opening price")
    high: float | None = Field(default=None, description="Day high price")
    low: float | None = Field(default=None, description="Day low price")
    volume: int | None = Field(default=None, description="Day trading volume in shares")
    fifty_two_week_high: float | None = Field(default=None, description="52-week high price")
    fifty_two_week_low: float | None = Field(default=None, description="52-week low price")
    market_status: MarketStatusType = Field(description="Active market session state")
    market_timestamp: str = Field(description="Timestamp of the price quote (ISO 8601 with timezone)")
    retrieved_at: str = Field(description="Timestamp when data was retrieved by Finova (ISO 8601)")
    provider: str = Field(description="Source provider name (e.g. 'Yahoo Finance')")
    source_url: str = Field(default="", description="Source URL or reference link")
    freshness_status: FreshnessStatusType = Field(
        default="delayed",
        description="Freshness level (realtime, delayed, last_traded_close, stale_cached_fallback)",
    )


class HistoricalPrices(BaseModel):
    """
    Deterministic summary of 1-month daily historical OHLCV data.
    Technical indicators are intentionally deferred.
    """
    symbol: str = Field(description="Canonical ticker symbol")
    period: str = Field(default="1mo", description="Historical period window")
    interval: str = Field(default="1d", description="Bar interval")
    start_date: str = Field(description="Start date of period (YYYY-MM-DD)")
    end_date: str = Field(description="End date of period (YYYY-MM-DD)")
    start_price: float = Field(description="First close in period")
    end_price: float = Field(description="Latest close in period")
    period_change: float = Field(description="Net price change over period")
    period_change_percent: float = Field(description="Percentage price change over period")
    period_high: float = Field(description="Highest price observed in period")
    period_low: float = Field(description="Lowest price observed in period")
    fifty_two_week_high: float | None = Field(default=None, description="52-week high price")
    fifty_two_week_low: float | None = Field(default=None, description="52-week low price")
    provider: str = Field(description="Source provider name")
    retrieved_at: str = Field(description="Timestamp when data was retrieved by Finova (ISO 8601)")


class CompanyOverview(BaseModel):
    """
    Basic corporate profile and fundamental overview for retail education.
    """
    symbol: str = Field(description="Canonical ticker symbol")
    company_name: str = Field(description="Registered corporate name")
    exchange: Literal["NSE", "BSE"] = Field(default="NSE", description="Primary exchange")
    currency: str = Field(default="INR", description="Reporting currency")
    sector: str = Field(default="", description="Industry sector")
    industry: str = Field(default="", description="Specific industry classification")
    market_cap: float | None = Field(default=None, description="Market capitalization (INR)")
    pe_ratio: float | None = Field(default=None, description="Trailing price-to-earnings ratio")
    fifty_two_week_high: float | None = Field(default=None, description="52-week high price")
    fifty_two_week_low: float | None = Field(default=None, description="52-week low price")
    summary: str = Field(default="", description="Brief educational summary of business operations")
    provider: str = Field(description="Source provider name")
    retrieved_at: str = Field(description="Timestamp when profile was retrieved (ISO 8601)")


class MarketStatus(BaseModel):
    """
    Current session status for Indian exchanges (NSE / BSE).
    Evaluated with respect to Indian Standard Time (IST, UTC+05:30) and exchange holidays.
    """
    exchange: Literal["NSE", "BSE"] = Field(default="NSE", description="Exchange code")
    is_open: bool = Field(description="True if regular continuous trading session is active")
    session_type: MarketStatusType = Field(description="Detailed session phase")
    current_time_ist: str = Field(description="Current time in IST (ISO 8601 format)")
    next_session_open_ist: str = Field(description="Next scheduled market open time in IST")
    holiday_name: str | None = Field(default=None, description="Name of holiday if exchange is closed")


class MarketDataProvenance(BaseModel):
    """
    Provenance metadata attached to EquityAgent responses when market data is utilized.
    Sits alongside SEBI regulatory citations in TradeWise responses.
    """
    symbol: str
    company_name: str = ""
    exchange: str = "NSE"
    currency: str = "INR"
    price: float
    change: float = 0.0
    change_percent: float = 0.0
    previous_close: float | None = None
    open: float | None = None
    high: float | None = None
    low: float | None = None
    volume: int | None = None
    market_status: MarketStatusType
    market_timestamp: str
    retrieved_at: str
    provider: str
    source_url: str = ""
    freshness_status: FreshnessStatusType = "delayed"
