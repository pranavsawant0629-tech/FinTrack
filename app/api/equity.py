"""
FastAPI router for the Equity Agent.
Exposes POST /agents/equity/ask returning standardized TradeWise responses.
"""

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.agents.equity.agent import equity_agent
from app.rag.service import Citation
from app.tools.market.models import MarketDataProvenance

router = APIRouter()


class EquityQueryRequest(BaseModel):
    """
    Request payload for the Equity Agent.

    Note on conversation_history:
    Accepted by the Phase 2 request schema for forward API contract compatibility,
    but currently unused by Phase 2 single-turn agent logic. Full multi-turn
    conversational memory and context tracking are intentionally deferred to Phase 5.
    """
    query: str
    conversation_history: list[dict[str, str]] = Field(
        default_factory=list,
        description="Prior conversation turns. Accepted in Phase 2 for contract stability; unused until Phase 5 memory.",
    )
    top_k: int | None = None
    score_threshold: float | None = None


class EquityQueryResponse(BaseModel):
    """TradeWise-ready response contract for the Equity Agent."""
    query: str
    answer: str
    grounding_status: str
    citations: list[Citation] = Field(default_factory=list)
    market_data: MarketDataProvenance | None = None
    grounding_sources: list[Literal["sebi_rag", "live_market_data"]] = Field(default_factory=list)
    agent_name: str
    disclaimer: str
    model_used: str
    latency_ms: float


@router.post("/ask", response_model=EquityQueryResponse)
def ask_equity_agent(payload: EquityQueryRequest):
    """
    Endpoint for querying the Equity Tutor agent.
    Performs safety pre-filtering, grounded SEBI RAG retrieval, citation verification,
    and returns TradeWise-compliant response metadata.
    """
    result = equity_agent.ask(
        query=payload.query,
        conversation_history=payload.conversation_history,
        top_k=payload.top_k,
        score_threshold=payload.score_threshold,
    )
    return EquityQueryResponse(
        query=result.query,
        answer=result.answer,
        grounding_status=result.grounding_status,
        citations=result.citations,
        market_data=result.market_data,
        grounding_sources=result.grounding_sources,
        agent_name=result.agent_name,
        disclaimer=result.disclaimer,
        model_used=result.model_used,
        latency_ms=result.latency_ms,
    )
