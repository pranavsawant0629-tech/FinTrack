"""
FastAPI router for the Market News Agent.
Exposes GET /agents/news/ticker/{symbol}, GET /agents/news/macro, and POST /agents/news/ask.
"""

from __future__ import annotations

from typing import Any
from fastapi import APIRouter
from pydantic import BaseModel

from app.agents.news.agent import NewsAgent
from app.tools.news.service import NewsService

router = APIRouter()
_news_service = NewsService()
_news_agent = NewsAgent(service=_news_service)


class NewsQueryRequest(BaseModel):
    query: str
    user_id: str | None = None


@router.get("/ticker/{symbol}")
def get_ticker_news(symbol: str, limit: int = 5) -> dict[str, Any]:
    """Retrieve verified live news for an Indian equity ticker symbol."""
    res = _news_service.get_ticker_news(symbol, limit=limit)
    return res.to_dict()


@router.get("/macro")
def get_macro_news(limit: int = 5) -> dict[str, Any]:
    """Retrieve verified regulatory announcements from SEBI & RBI."""
    res = _news_service.get_macro_news(limit=limit)
    return res.to_dict()


@router.post("/ask")
def ask_news(payload: NewsQueryRequest) -> dict[str, Any]:
    """Query the Market News & Regulatory Intelligence agent."""
    res = _news_agent.ask(query=payload.query, user_id=payload.user_id)
    return res.to_dict()
