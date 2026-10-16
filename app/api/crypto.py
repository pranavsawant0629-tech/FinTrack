"""
FastAPI router for the Crypto Agent.
Exposes POST /agents/crypto/ask returning standardized TradeWise crypto responses.
"""

from typing import Any, Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.agents.crypto.agent import crypto_agent

router = APIRouter()


class CryptoQueryRequest(BaseModel):
    """Request payload for the Crypto Agent."""
    query: str
    conversation_history: list[dict[str, str]] = Field(
        default_factory=list,
        description="Prior conversation turns for forward context compatibility",
    )


class CryptoQueryResponse(BaseModel):
    """TradeWise-ready response contract for the Crypto Agent."""
    query: str
    answer: str
    grounding_status: str
    crypto_data: dict[str, Any] | None = None
    grounding_sources: list[Literal["sebi_rag", "live_market_data", "crypto_data", "calc_tool"]] = Field(
        default_factory=list
    )
    agent_name: str
    disclaimer: str
    model_used: str
    latency_ms: float


@router.post("/ask", response_model=CryptoQueryResponse)
def ask_crypto_agent(payload: CryptoQueryRequest) -> CryptoQueryResponse:
    """
    Endpoint for querying the Crypto Tutor agent.
    Performs safety checks, cryptocurrency data fetching, and conceptual explanations.
    """
    res = crypto_agent.ask(
        query=payload.query,
        conversation_history=payload.conversation_history,
    )
    return CryptoQueryResponse(
        query=res.query,
        answer=res.answer,
        grounding_status=res.grounding_status,
        crypto_data=res.crypto_data,
        grounding_sources=res.grounding_sources,
        agent_name=res.agent_name,
        disclaimer=res.disclaimer,
        model_used=res.model_used,
        latency_ms=res.latency_ms,
    )
