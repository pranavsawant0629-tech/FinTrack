"""
Data models and Pydantic schemas for simulated portfolio analysis.
Enforces rigorous accounting distinguishing invested capital (cost basis) from cash liquidity.
"""

from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field


AssetType = Literal["equity", "etf", "mutual_fund", "crypto", "cash"]


class Holding(BaseModel):
    """Represents a single asset holding in a simulated portfolio."""
    symbol: str = Field(description="Ticker or asset symbol (e.g. TCS, RELIANCE, NIFTYBEES)")
    asset_type: AssetType = Field(default="equity", description="Classification of asset")
    quantity: float = Field(gt=0, description="Number of units/shares held")
    average_buy_price: float = Field(ge=0, description="Volume-weighted average purchase price per share")
    current_price: float = Field(ge=0, description="Latest market price per share")
    sector: str = Field(default="General", description="Industry sector (e.g. Technology, Energy, Banking)")
    currency: str = Field(default="INR", description="Currency denomination")

    @property
    def cost_basis(self) -> float:
        """Total capital invested to acquire this holding."""
        return round(self.quantity * self.average_buy_price, 2)

    @property
    def market_value(self) -> float:
        """Current market valuation of this holding."""
        return round(self.quantity * self.current_price, 2)

    @property
    def unrealized_pnl(self) -> float:
        """Unrealized gain or loss in currency units."""
        return round(self.market_value - self.cost_basis, 2)

    @property
    def unrealized_pnl_pct(self) -> float:
        """Unrealized return percentage relative to cost basis."""
        if self.cost_basis <= 0:
            return 0.0
        return round((self.unrealized_pnl / self.cost_basis) * 100, 2)


class PortfolioData(BaseModel):
    """Complete simulated user portfolio state."""
    user_id: str = Field(description="Owner user partition ID")
    cash_balance: float = Field(default=0.0, ge=0, description="Uninvested liquid cash balance")
    currency: str = Field(default="INR", description="Base portfolio currency denomination")
    holdings: list[Holding] = Field(default_factory=list, description="Active asset positions")
    updated_at: str = Field(default="", description="ISO 8601 update timestamp")


class PortfolioMetrics(BaseModel):
    """Deterministic financial analytics for a portfolio."""
    currency: str = Field(default="INR", description="Portfolio base currency")
    securities_cost_basis: float = Field(description="Total capital invested in securities (excludes cash)")
    securities_market_value: float = Field(description="Total current market value of securities")
    cash_balance: float = Field(description="Liquid uninvested cash balance")
    total_portfolio_value: float = Field(description="Securities market value + cash balance")
    unrealized_pnl: float = Field(description="Absolute unrealized gain/loss on securities")
    unrealized_pnl_pct: float = Field(description="Percentage return on invested securities capital")
    asset_allocation: dict[str, float] = Field(description="Percentage allocation by asset type (sums to 100%)")
    sector_allocation: dict[str, float] = Field(description="Percentage allocation by sector across securities")
    top_holding_symbol: str = Field(description="Symbol of largest position by market value")
    top_holding_concentration_pct: float = Field(description="Share of total portfolio value in top holding")
    diversification_assessment: str = Field(description="Educational risk commentary based on concentration")


class WhatIfHoldingImpact(BaseModel):
    """Simulated price shock outcome for an individual holding."""
    symbol: str
    original_price: float
    simulated_price: float
    price_change_pct: float
    value_delta: float


class WhatIfSimulationResult(BaseModel):
    """Outcome of a deterministic 'what-if' portfolio stress test."""
    scenario_description: str
    original_portfolio_value: float
    simulated_portfolio_value: float
    portfolio_delta_value: float
    portfolio_delta_pct: float
    impacted_holdings: list[WhatIfHoldingImpact] = Field(default_factory=list)
