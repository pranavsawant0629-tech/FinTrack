"""Equity Agent (Equity Tutor) for Finova AI.

Coordinates:
1. Deterministic safety evaluation (no stock tips, no personalized advice, no return guarantees)
2. Fast-path market data routing (quotes, 1mo historical performance, company profiles, session status)
3. Grounded SEBI RAG synthesis and citation verification
4. Standardized TradeWise JSON response contracts
"""

from __future__ import annotations

import logging
import time
from typing import Any, Literal
from pydantic import BaseModel, Field

from app.agents.equity.prompts import EQUITY_TUTOR_SYSTEM_PROMPT
from app.agents.equity.safety import EquitySafetyGuardrail, equity_safety_guardrail
from app.rag.service import Citation, RAGService, rag_service
from app.tools.market.intent import MarketIntentClassifier
from app.tools.market.interfaces import SymbolNotFoundError
from app.tools.market.models import MarketDataProvenance
from app.tools.market.service import MarketDataService
from app.tools.market.validator import MarketDataValidator

logger = logging.getLogger(__name__)

EQUITY_DISCLAIMER = (
    "Disclaimer: Finova AI is an educational platform and not a SEBI-registered investment adviser. "
    "This information is for educational purposes only and does not constitute financial advice."
)


class EquityAgentResult(BaseModel):
    """TradeWise-ready response from the Equity Agent."""
    query: str
    answer: str
    grounding_status: Literal["fully_grounded", "partially_grounded", "ungrounded"]
    citations: list[Citation] = Field(default_factory=list)
    market_data: MarketDataProvenance | None = None
    grounding_sources: list[Literal["sebi_rag", "live_market_data"]] = Field(default_factory=list)
    agent_name: str = "Equity Tutor"
    disclaimer: str = EQUITY_DISCLAIMER
    model_used: str = ""
    latency_ms: float = 0.0


class EquityAgent:
    """Main Equity Agent coordinator for Finova AI."""

    def __init__(
        self,
        safety: EquitySafetyGuardrail | None = None,
        rag: RAGService | None = None,
        market_service: MarketDataService | None = None,
        intent_classifier: MarketIntentClassifier | None = None,
        validator: MarketDataValidator | None = None,
    ):
        self.safety = safety or equity_safety_guardrail
        self.rag_service = rag or rag_service
        self.market_service = market_service or MarketDataService()
        self.intent_classifier = intent_classifier or MarketIntentClassifier()
        self.validator = validator or MarketDataValidator()

    def ask(
        self,
        query: str,
        conversation_history: list[dict[str, str]] | None = None,
        top_k: int | None = None,
        score_threshold: float | None = None,
        personalization: Any | None = None,
    ) -> EquityAgentResult:
        """Execute the Equity Agent pipeline with deterministic safety, market tools, and SEBI RAG."""
        t0 = time.perf_counter()

        # Step 1: Safety & Advisory Guardrail Check
        safety_result = self.safety.evaluate(query)
        if not safety_result.is_safe:
            latency = round((time.perf_counter() - t0) * 1000, 2)
            model_name = str(getattr(self.rag_service.llm, "model", "qwen2.5:7b-instruct"))
            return EquityAgentResult(
                query=query,
                answer=safety_result.refusal_message or "",
                grounding_status="ungrounded",
                citations=[],
                market_data=None,
                grounding_sources=[],
                agent_name="Equity Tutor",
                disclaimer=EQUITY_DISCLAIMER,
                model_used=model_name,
                latency_ms=latency,
            )

        # Step 2: Market Intent Classification
        intent_res = self.intent_classifier.classify(query)

        # 2A. Market Status Intent
        if intent_res.intent == "market_status":
            status = self.market_service.get_market_status()
            session_label = status.session_type.replace("_", " ").title()
            holiday_info = f" Closed for {status.holiday_name}." if status.holiday_name else ""
            status_text = (
                f"The Indian stock market ({status.exchange}) is currently "
                f"{'OPEN' if status.is_open else 'CLOSED'} ({session_label} session).{holiday_info}\n\n"
                f"• Regular Trading Hours: 09:15 AM to 03:30 PM IST (Monday to Friday)\n"
                f"• Pre-Open Session: 09:00 AM to 09:15 AM IST\n"
                f"• Post-Closing Session: 03:30 PM to 04:00 PM IST\n"
                f"• Next Scheduled Market Open: {status.next_session_open_ist}"
            )
            latency = round((time.perf_counter() - t0) * 1000, 2)
            return EquityAgentResult(
                query=query,
                answer=status_text,
                grounding_status="fully_grounded",
                citations=[],
                market_data=None,
                grounding_sources=["live_market_data"],
                agent_name="Equity Tutor",
                disclaimer=EQUITY_DISCLAIMER,
                model_used="deterministic_tools",
                latency_ms=latency,
            )

        # 2B. Live Quote Intent
        if intent_res.intent == "quote" and intent_res.symbol:
            try:
                quote = self.market_service.get_quote(intent_res.symbol, exchange=intent_res.exchange)
                provenance = self.validator.create_provenance(quote)
                
                sign = "+" if quote.change > 0 else ""
                quote_text = (
                    f"**{quote.company_name or quote.symbol} ({quote.symbol})** on {quote.exchange}:\n\n"
                    f"• **Current / Last Traded Price:** ₹{quote.price:,.2f} ({sign}{quote.change:,.2f}, {sign}{quote.change_percent:.2f}%)\n"
                )
                if quote.previous_close:
                    quote_text += f"• **Previous Close:** ₹{quote.previous_close:,.2f}\n"
                if quote.high and quote.low:
                    quote_text += f"• **Day Range:** ₹{quote.low:,.2f} - ₹{quote.high:,.2f}\n"
                if quote.volume:
                    quote_text += f"• **Volume:** {quote.volume:,}\n"
                quote_text += f"• **Market Session:** {quote.market_status.replace('_', ' ').title()}\n"
                quote_text += f"• **Data Freshness:** {quote.freshness_status.replace('_', ' ').title()} (as of {quote.market_timestamp})\n"
                quote_text += f"• **Source Provider:** {quote.provider}"
                if intent_res.is_hybrid:
                    concept_phrase = f"what {intent_res.detected_concept} is" if intent_res.detected_concept else "the concept you asked about"
                    quote_text += (
                        f"\n\n> **Note:** I've shown you the current market data — "
                        f"ask me separately about {concept_phrase} for a full explanation."
                    )

                latency = round((time.perf_counter() - t0) * 1000, 2)
                return EquityAgentResult(
                    query=query,
                    answer=quote_text,
                    grounding_status="fully_grounded",
                    citations=[],
                    market_data=provenance,
                    grounding_sources=["live_market_data"],
                    agent_name="Equity Tutor",
                    disclaimer=EQUITY_DISCLAIMER,
                    model_used="deterministic_tools",
                    latency_ms=latency,
                )
            except SymbolNotFoundError:
                pass
            except Exception as exc:
                logger.warning("Market quote retrieval failed for %s: %s", intent_res.symbol, exc)

        # 2C. Historical Performance Intent
        if intent_res.intent == "historical" and intent_res.symbol:
            try:
                hist = self.market_service.get_historical_summary(intent_res.symbol, exchange=intent_res.exchange)
                sign = "+" if hist.period_change > 0 else ""
                hist_text = (
                    f"**{hist.symbol} — 1-Month Historical Performance ({hist.start_date} to {hist.end_date})**:\n\n"
                    f"• **Starting Price:** ₹{hist.start_price:,.2f}\n"
                    f"• **Ending Price:** ₹{hist.end_price:,.2f}\n"
                    f"• **1-Month Net Change:** {sign}₹{hist.period_change:,.2f} ({sign}{hist.period_change_percent:.2f}%)\n"
                    f"• **1-Month High:** ₹{hist.period_high:,.2f}\n"
                    f"• **1-Month Low:** ₹{hist.period_low:,.2f}\n"
                )
                if hist.fifty_two_week_high and hist.fifty_two_week_low:
                    hist_text += f"• **52-Week Range:** ₹{hist.fifty_two_week_low:,.2f} - ₹{hist.fifty_two_week_high:,.2f}\n"
                hist_text += f"• **Data Provider:** {hist.provider}"
                if intent_res.is_hybrid:
                    concept_phrase = f"what {intent_res.detected_concept} is" if intent_res.detected_concept else "the concept you asked about"
                    hist_text += (
                        f"\n\n> **Note:** I've shown you the historical performance data — "
                        f"ask me separately about {concept_phrase} for a full explanation."
                    )

                latency = round((time.perf_counter() - t0) * 1000, 2)
                return EquityAgentResult(
                    query=query,
                    answer=hist_text,
                    grounding_status="fully_grounded",
                    citations=[],
                    market_data=None,
                    grounding_sources=["live_market_data"],
                    agent_name="Equity Tutor",
                    disclaimer=EQUITY_DISCLAIMER,
                    model_used="deterministic_tools",
                    latency_ms=latency,
                )
            except SymbolNotFoundError:
                pass
            except Exception as exc:
                logger.warning("Historical data retrieval failed for %s: %s", intent_res.symbol, exc)

        # 2D. Overview / Fundamentals Intent
        if intent_res.intent == "overview" and intent_res.symbol:
            try:
                ov = self.market_service.get_company_overview(intent_res.symbol, exchange=intent_res.exchange)
                ov_text = f"**{ov.company_name} ({ov.symbol})**:\n\n"
                if ov.sector or ov.industry:
                    ov_text += f"• **Sector / Industry:** {ov.sector} | {ov.industry}\n"
                if ov.market_cap:
                    ov_text += f"• **Market Capitalization:** ₹{ov.market_cap:,.0f}\n"
                if ov.pe_ratio:
                    ov_text += f"• **P/E Ratio:** {ov.pe_ratio:.2f}\n"
                if ov.fifty_two_week_high and ov.fifty_two_week_low:
                    ov_text += f"• **52-Week Range:** ₹{ov.fifty_two_week_low:,.2f} - ₹{ov.fifty_two_week_high:,.2f}\n"
                if ov.summary:
                    ov_text += f"\n**Business Summary:**\n{ov.summary[:400]}..."
                if intent_res.is_hybrid:
                    concept_phrase = f"what {intent_res.detected_concept} is" if intent_res.detected_concept else "the concept you asked about"
                    ov_text += (
                        f"\n\n> **Note:** I've shown you the company fundamentals — "
                        f"ask me separately about {concept_phrase} for a full explanation."
                    )

                latency = round((time.perf_counter() - t0) * 1000, 2)
                return EquityAgentResult(
                    query=query,
                    answer=ov_text,
                    grounding_status="fully_grounded",
                    citations=[],
                    market_data=None,
                    grounding_sources=["live_market_data"],
                    agent_name="Equity Tutor",
                    disclaimer=EQUITY_DISCLAIMER,
                    model_used="deterministic_tools",
                    latency_ms=latency,
                )
            except SymbolNotFoundError:
                pass
            except Exception as exc:
                logger.warning("Company overview retrieval failed for %s: %s", intent_res.symbol, exc)

        # Step 3: SEBI RAG Execution (For conceptual, educational, regulatory, or unmapped queries)
        sys_prompt = EQUITY_TUTOR_SYSTEM_PROMPT
        if personalization:
            from app.memory.models import build_personalization_instruction
            inst = build_personalization_instruction(personalization)
            if inst:
                sys_prompt = EQUITY_TUTOR_SYSTEM_PROMPT + inst

        rag_ans = self.rag_service.generate_answer(
            query=query,
            top_k=top_k,
            score_threshold=score_threshold,
            system_prompt=sys_prompt,
            conversation_history=conversation_history,
        )

        latency = round((time.perf_counter() - t0) * 1000, 2)
        sources: list[Literal["sebi_rag", "live_market_data"]] = (
            ["sebi_rag"] if rag_ans.grounding_status in ("fully_grounded", "partially_grounded") else []
        )
        return EquityAgentResult(
            query=query,
            answer=rag_ans.answer,
            grounding_status=rag_ans.grounding_status,
            citations=rag_ans.citations,
            market_data=None,
            grounding_sources=sources,
            agent_name="Equity Tutor",
            disclaimer=EQUITY_DISCLAIMER,
            model_used=rag_ans.model_used,
            latency_ms=latency,
        )


equity_agent = EquityAgent()
