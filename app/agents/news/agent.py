"""
Market News Agent for Finova AI.
Coordinates verified news retrieval, enforces safety, and formats summaries with source
provenance and freshness labels, adhering to the invariant that LLMs are not the source of truth
for live market news data.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
import re
from typing import Any

from app.agents.news.prompts import NEWS_DISCLAIMER, NEWS_SYSTEM_PROMPT
from app.agents.news.safety import NewsSafetyGuardrail, news_safety_guardrail
from app.tools.news.models import NewsFreshness, NewsSearchResult
from app.tools.news.service import NewsService

logger = logging.getLogger(__name__)

KNOWN_INDIAN_TICKERS = {
    "TCS": "TCS.NS",
    "RELIANCE": "RELIANCE.NS",
    "INFY": "INFY.NS",
    "INFOSYS": "INFY.NS",
    "HDFCBANK": "HDFCBANK.NS",
    "ICICIBANK": "ICICIBANK.NS",
    "SBIN": "SBIN.NS",
    "SBI": "SBIN.NS",
    "TATAMOTORS": "TATAMOTORS.NS",
    "ITC": "ITC.NS",
    "WIPRO": "WIPRO.NS",
    "NIFTY": "^NSEI",
    "SENSEX": "^BSESN",
}


@dataclass(frozen=True)
class NewsAgentResult:
    """Standardized response from the Market News Agent."""
    query: str
    answer: str
    articles: list[dict[str, Any]]
    freshness: str
    grounding_status: str
    grounding_sources: list[str]
    disclaimer: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "answer": self.answer,
            "articles": self.articles,
            "freshness": self.freshness,
            "grounding_status": self.grounding_status,
            "grounding_sources": self.grounding_sources,
            "disclaimer": self.disclaimer,
        }


class NewsAgent:
    """Agent specialized in financial news summarization and regulatory announcements."""

    def __init__(
        self,
        service: NewsService | None = None,
        llm: Any = None,
        guardrail: NewsSafetyGuardrail | None = None,
    ) -> None:
        self._service = service or NewsService()
        self._llm = llm
        self._guardrail = guardrail or news_safety_guardrail

    def _extract_symbol(self, query: str) -> str | None:
        tokens = re.findall(r"\b[A-Za-z0-9&^.]+\b", query.upper())
        for token in tokens:
            if token in KNOWN_INDIAN_TICKERS:
                return KNOWN_INDIAN_TICKERS[token]
            if token.endswith(".NS") or token.endswith(".BO") or token.startswith("^"):
                return token

        match = re.search(r"\b(?:news\s+(?:on|for|about)|for)\s+([A-Za-z0-9]+)\b", query, re.IGNORECASE)
        if match:
            cand = match.group(1).upper()
            if cand not in {"THE", "LATEST", "RECENT", "TODAY", "MARKET", "STOCK", "STOCKS", "SEBI", "RBI"}:
                return cand
        return None

    def ask(self, query: str, user_id: str | None = None) -> NewsAgentResult:
        """Process user news inquiry."""
        # 1. Safety Guardrail
        safety_eval = self._guardrail.evaluate(query)
        if not safety_eval.is_safe:
            return NewsAgentResult(
                query=query,
                answer=safety_eval.refusal_message or "This request cannot be fulfilled.",
                articles=[],
                freshness="unspecified",
                grounding_status="ungrounded",
                grounding_sources=["safety_guardrail"],
                disclaimer=NEWS_DISCLAIMER,
            )

        # 2. Extract entity or default to macro/regulatory news
        symbol = self._extract_symbol(query)
        if symbol:
            search_res = self._service.get_ticker_news(symbol, limit=4)
        else:
            search_res = self._service.get_macro_news(limit=4)

        # 3. Handle no articles / failure truthfully
        if not search_res.articles:
            msg = search_res.error_message or f"No recent verified news available for query: '{query}'."
            return NewsAgentResult(
                query=query,
                answer=f"{msg}\n\n{NEWS_DISCLAIMER}",
                articles=[],
                freshness=search_res.freshness.value,
                grounding_status="ungrounded",
                grounding_sources=["news_service"],
                disclaimer=NEWS_DISCLAIMER,
            )

        # 4. Synthesize educational summary
        answer = self._format_news_summary(query, search_res)

        return NewsAgentResult(
            query=query,
            answer=answer,
            articles=[a.to_dict() for a in search_res.articles],
            freshness=search_res.freshness.value,
            grounding_status="fully_grounded",
            grounding_sources=["news_service", search_res.provider],
            disclaimer=NEWS_DISCLAIMER,
        )

    def _format_news_summary(self, query: str, res: NewsSearchResult) -> str:
        lines: list[str] = [
            f"### Retrieved Financial & Regulatory Headlines",
            f"**Freshness Status:** `{res.freshness.value.upper()}` | **Source Provider:** `{res.provider}`\n",
        ]

        for idx, art in enumerate(res.articles, start=1):
            lines.append(f"#### {idx}. {art.title}")
            lines.append(f"- **Source:** {art.source} ({art.source_type.value})")
            lines.append(f"- **Published:** {art.published_at if art.published_at else 'Unknown'}")
            if art.summary:
                lines.append(f"- **Summary:** {art.summary}")
            if art.url and not art.url.startswith("https://finova.mock"):
                lines.append(f"- **Read More:** [Source Link]({art.url})")
            lines.append("")

        lines.append(f"*{NEWS_DISCLAIMER}*")
        return "\n".join(lines)
