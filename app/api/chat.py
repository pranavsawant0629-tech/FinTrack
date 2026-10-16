"""
FastAPI router for the Central Orchestrator.
Exposes POST /orchestrator/ask and POST /chat returning unified TradeWise responses.
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.router.models import OrchestratorResponse
from app.router.orchestrator import central_orchestrator

router = APIRouter()


class OrchestratorQueryRequest(BaseModel):
    """Unified query request payload for Finova AI."""
    query: str
    user_id: str | None = Field(
        default=None,
        description="TradeWise application-level user identity for persistent personalization",
    )
    conversation_history: list[dict[str, str]] = Field(
        default_factory=list,
        description="Prior conversation turns for forward context compatibility",
    )
    top_k: int | None = None
    score_threshold: float | None = None


@router.post("/orchestrator/ask", response_model=OrchestratorResponse)
@router.post("/chat", response_model=OrchestratorResponse)
def ask_orchestrator(payload: OrchestratorQueryRequest) -> OrchestratorResponse:
    """
    Main entrypoint for Finova AI multi-agent orchestration.
    Performs global safety filtering, intent routing, multi-intent decomposition,
    and returns a unified TradeWise response.
    """
    return central_orchestrator.ask(
        query=payload.query,
        user_id=payload.user_id,
        conversation_history=payload.conversation_history,
        top_k=payload.top_k,
        score_threshold=payload.score_threshold,
    )
