"""
FastAPI router for the Onboarding & System Help Agent.
Exposes GET /agents/onboarding/capabilities, GET /agents/onboarding/faqs, and POST /agents/onboarding/ask.
"""

from __future__ import annotations

from typing import Any
from fastapi import APIRouter
from pydantic import BaseModel

from app.agents.onboarding.agent import OnboardingAgent
from app.tools.onboarding.repository import onboarding_repository

router = APIRouter()
_onboarding_agent = OnboardingAgent(repository=onboarding_repository)


class OnboardingQueryRequest(BaseModel):
    query: str
    user_id: str | None = None


@router.get("/capabilities")
def get_capabilities() -> list[dict[str, Any]]:
    """Enumerate all 8 specialized capabilities of Finova AI."""
    caps = onboarding_repository.get_all_capabilities()
    return [c.to_dict() for c in caps]


@router.get("/faqs")
def get_faqs(category: str | None = None) -> list[dict[str, Any]]:
    """Retrieve system, privacy, and memory management FAQs."""
    faqs = onboarding_repository.get_faqs(category=category)
    return [f.to_dict() for f in faqs]


@router.post("/ask")
def ask_onboarding(payload: OnboardingQueryRequest) -> dict[str, Any]:
    """Query the System Guide & Onboarding Agent."""
    res = _onboarding_agent.ask(query=payload.query, user_id=payload.user_id)
    return res.to_dict()
