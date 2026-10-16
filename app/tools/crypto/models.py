"""
Data schemas for the Finova AI Cryptocurrency Layer.
Defines standardized models for crypto quotes and provenance tracking.
"""

from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field

CryptoFreshnessType = Literal["realtime", "delayed", "cached_fallback", "unavailable"]


class CryptoQuote(BaseModel):
    """Standardized crypto quote normalized across providers."""
    symbol: str = Field(description="Canonical ticker symbol (e.g. 'BTC', 'ETH')")
    name: str = Field(default="", description="Asset name (e.g. 'Bitcoin', 'Ethereum')")
    price_usd: float = Field(description="Current price in USD")
    price_inr: float | None = Field(default=None, description="Current price in INR")
    change_24h: float = Field(default=0.0, description="Percentage change in the last 24 hours")
    market_cap_usd: float | None = Field(default=None, description="Market capitalization in USD")
    volume_24h_usd: float | None = Field(default=None, description="24-hour trading volume in USD")
    high_24h_usd: float | None = Field(default=None, description="24-hour high price in USD")
    low_24h_usd: float | None = Field(default=None, description="24-hour low price in USD")
    market_timestamp: str = Field(description="Timestamp of the quote data (ISO 8601)")
    retrieved_at: str = Field(description="Timestamp when data was retrieved by Finova (ISO 8601)")
    provider: str = Field(default="CoinGecko", description="Source provider name")
    freshness_status: CryptoFreshnessType = Field(default="realtime", description="Data freshness level")


class CryptoProvenance(BaseModel):
    """Provenance metadata attached to agent responses for crypto data."""
    symbol: str
    name: str = ""
    price_usd: float
    price_inr: float | None = None
    change_24h: float = 0.0
    market_timestamp: str
    retrieved_at: str
    provider: str
    freshness_status: CryptoFreshnessType = "realtime"
