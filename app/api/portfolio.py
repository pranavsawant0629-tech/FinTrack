"""
FastAPI router for the Portfolio Tutor Agent.
Exposes GET /agents/portfolio, POST /agents/portfolio/whatif, and POST /agents/portfolio/ask.
"""

from __future__ import annotations

from typing import Any
from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.agents.portfolio.agent import PortfolioAgent, PortfolioAgentResult
from app.tools.portfolio.providers.mock import create_demo_portfolio
from app.tools.portfolio.service import portfolio_service

router = APIRouter()
_portfolio_agent = PortfolioAgent(service=portfolio_service)


class PortfolioQueryRequest(BaseModel):
    query: str
    user_id: str | None = None
    conversation_history: list[dict[str, str]] = Field(default_factory=list)


class WhatIfRequest(BaseModel):
    user_id: str = "demo_user"
    symbol: str = "TCS"
    percentage_change: float = -10.0


@router.get("/")
def get_portfolio(user_id: str = "demo_user") -> dict[str, Any]:
    """Retrieve portfolio metrics and allocation for user_id."""
    p = portfolio_service.get_portfolio(user_id) or create_demo_portfolio(user_id)
    metrics = portfolio_service.calculate_metrics(p)
    return {
        "portfolio": p.model_dump(),
        "metrics": metrics.model_dump(),
    }


@router.post("/whatif")
def simulate_whatif(payload: WhatIfRequest) -> dict[str, Any]:
    """Simulate asset price shock on user portfolio."""
    p = portfolio_service.get_portfolio(payload.user_id) or create_demo_portfolio(payload.user_id)
    res = portfolio_service.simulate_what_if(
        portfolio=p,
        target_symbol=payload.symbol,
        change_pct=payload.percentage_change,
    )
    return res.model_dump()


@router.post("/ask")
def ask_portfolio(payload: PortfolioQueryRequest) -> dict[str, Any]:
    """Query the Portfolio Analytics & Stress Testing agent."""
    res = _portfolio_agent.ask(query=payload.query, user_id=payload.user_id)
    return res.to_dict()
