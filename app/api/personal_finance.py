"""
FastAPI router for the Personal Finance Agent.
Exposes POST /agents/personal-finance/ask returning standardized TradeWise personal finance responses.
"""

from typing import Any, Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.agents.personal_finance.agent import personal_finance_agent

router = APIRouter()


class PersonalFinanceQueryRequest(BaseModel):
    """Request payload for the Personal Finance Agent."""
    query: str
    conversation_history: list[dict[str, str]] = Field(
        default_factory=list,
        description="Prior conversation turns for forward context compatibility",
    )


class PersonalFinanceQueryResponse(BaseModel):
    """TradeWise-ready response contract for the Personal Finance Agent."""
    query: str
    answer: str
    grounding_status: str
    calc_data: dict[str, Any] | None = None
    grounding_sources: list[Literal["sebi_rag", "live_market_data", "crypto_data", "calc_tool"]] = Field(
        default_factory=list
    )
    agent_name: str
    disclaimer: str
    model_used: str
    latency_ms: float


@router.post("/ask", response_model=PersonalFinanceQueryResponse)
def ask_personal_finance_agent(payload: PersonalFinanceQueryRequest) -> PersonalFinanceQueryResponse:
    """
    Endpoint for querying the Personal Finance Tutor agent.
    Performs safety checks, deterministic calculations, and budgeting explanations.
    """
    res = personal_finance_agent.ask(
        query=payload.query,
        conversation_history=payload.conversation_history,
    )
    return PersonalFinanceQueryResponse(
        query=res.query,
        answer=res.answer,
        grounding_status=res.grounding_status,
        calc_data=res.calc_data,
        grounding_sources=res.grounding_sources,
        agent_name=res.agent_name,
        disclaimer=res.disclaimer,
        model_used=res.model_used,
        latency_ms=res.latency_ms,
    )
