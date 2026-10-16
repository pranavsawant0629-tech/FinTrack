"""
FastAPI router for the Derivatives Tutor Agent.
Exposes POST /agents/derivatives/ask and POST /agents/derivatives/calculate.
"""

from __future__ import annotations

from typing import Any
from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.agents.derivatives.agent import DerivativesAgent, DerivativesAgentResult
from app.tools.derivatives.payoff import calculate_futures_pnl, calculate_option_payoff

router = APIRouter()
_derivatives_agent = DerivativesAgent()


class DerivativesQueryRequest(BaseModel):
    query: str
    user_id: str | None = None
    conversation_history: list[dict[str, str]] = Field(default_factory=list)


class OptionCalculateRequest(BaseModel):
    contract_type: str = Field(description="'call', 'put', or 'futures'")
    position: str = Field(default="long", description="'long' or 'short'")
    strike_price: float = Field(default=0.0)
    premium: float = Field(default=0.0)
    spot_price: float | None = None
    lot_size: int = 1


@router.post("/ask", response_model=DerivativesAgentResult)
def ask_derivatives(payload: DerivativesQueryRequest) -> DerivativesAgentResult:
    """Query the Derivatives & F&O Tutor agent."""
    return _derivatives_agent.ask(
        query=payload.query,
        conversation_history=payload.conversation_history,
        user_id=payload.user_id,
    )


@router.post("/calculate")
def calculate_derivatives(payload: OptionCalculateRequest) -> dict[str, Any]:
    """Execute deterministic derivatives payoff and profit/loss calculation."""
    c_type = payload.contract_type.lower()
    if c_type in ("call", "put"):
        res = calculate_option_payoff(
            option_type=c_type,
            position=payload.position,
            strike_price=payload.strike_price,
            premium=payload.premium,
        )
        return res.model_dump()
    elif c_type in ("future", "futures"):
        entry = payload.spot_price or payload.strike_price
        res_f = calculate_futures_pnl(
            position=payload.position,
            entry_price=entry,
            lot_size=payload.lot_size,
        )
        return res_f.model_dump()
    else:
        return {"error": f"Unsupported contract type: {payload.contract_type}"}
