"""
Data contracts and Pydantic models for the Derivatives calculation tools.
Defines contracts for option payoffs, futures P&L, and option Greeks.
"""

from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field, field_validator


OptionType = Literal["call", "put"]
OptionPosition = Literal["long", "short"]


class OptionPayoffPoint(BaseModel):
    """Single discrete spot price outcome in an option payoff schedule."""
    spot_price: float = Field(description="Underlying spot price at expiration")
    payoff: float = Field(description="Gross payoff at expiration before premium")
    pnl: float = Field(description="Net profit or loss after accounting for premium")


class OptionPayoffResult(BaseModel):
    """Deterministic output of an option payoff calculation."""
    option_type: OptionType = Field(description="'call' or 'put'")
    position: OptionPosition = Field(description="'long' or 'short'")
    strike_price: float = Field(description="Option strike price (K)")
    premium: float = Field(description="Option premium paid or received per unit")
    breakeven_price: float = Field(description="Exact underlying price where P&L is zero")
    has_feasible_breakeven: bool = Field(default=True, description="Whether a non-negative breakeven price exists")
    max_profit: float | str = Field(description="Maximum potential profit (or 'Unlimited')")
    max_loss: float | str = Field(description="Maximum potential loss (or 'Unlimited')")
    payoff_table: list[OptionPayoffPoint] = Field(
        default_factory=list,
        description="Discrete schedule of P&L values across spot prices",
    )


class FuturesPayoffPoint(BaseModel):
    """Single discrete exit price outcome in a futures P&L schedule."""
    exit_price: float = Field(description="Underlying price at exit / settlement")
    pnl_per_unit: float = Field(description="Net P&L per single underlying share/unit")
    total_pnl: float = Field(description="Total P&L across the contract lot size")


class FuturesPayoffResult(BaseModel):
    """Deterministic output of a futures contract P&L calculation."""
    position: Literal["long", "short"] = Field(description="'long' or 'short'")
    entry_price: float = Field(description="Futures contract entry price (F_0)")
    lot_size: int = Field(description="Contract lot size / multiplier")
    breakeven_price: float = Field(description="Exact price where net P&L is zero")
    payoff_table: list[FuturesPayoffPoint] = Field(
        default_factory=list,
        description="Discrete schedule of futures P&L values across exit prices",
    )


class GreeksInfo(BaseModel):
    """Pedagogical and analytical definition of an option Greek."""
    name: str = Field(description="Greek name (e.g. Delta, Gamma, Theta, Vega)")
    symbol: str = Field(description="Mathematical Greek letter symbol")
    definition: str = Field(description="Conceptual definition and meaning")
    range_or_bound: str = Field(description="Typical numerical range for calls and puts")
    primary_driver: str = Field(description="Market variable driving this Greek (Price, Time, Volatility)")
    pedagogical_example: str = Field(description="Intuitive real-world explanation for learners")
