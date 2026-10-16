"""
Derivatives Tutor Agent for Finova AI (Prof. Derivo).

Coordinates:
1. Deterministic safety evaluation (blocks options tips, expiry gambling, strike recommendations)
2. Deterministic mathematical calculation tools (call/put payoffs, breakevens, futures P&L)
3. Option Greeks pedagogical catalog
4. Tier 1 SEBI RAG retrieval for authoritative derivatives regulatory rules
5. Pedagogical synthesis adapted to learner personalization profile
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any, Literal
from pydantic import BaseModel, Field

from app.agents.derivatives.prompts import DERIVATIVES_DISCLAIMER, DERIVATIVES_TUTOR_SYSTEM_PROMPT
from app.agents.derivatives.safety import DerivativesSafetyGuardrail, derivatives_safety_guardrail
from app.llm.llm_client import LLMClient, llm_client
from app.memory.models import PersonalizationProfile, build_personalization_instruction
from app.rag.service import Citation, RAGService, rag_service
from app.tools.derivatives.greeks import get_all_greeks, get_greek_info
from app.tools.derivatives.payoff import calculate_futures_pnl, calculate_option_payoff

logger = logging.getLogger(__name__)


class DerivativesAgentResult(BaseModel):
    """Unified response contract for the Derivatives Tutor Agent."""
    query: str
    answer: str
    grounding_status: Literal["fully_grounded", "partially_grounded", "ungrounded"]
    citations: list[Citation] = Field(default_factory=list)
    derivatives_data: dict[str, Any] | None = None
    grounding_sources: list[str] = Field(default_factory=list)
    agent_name: str = "Derivatives Tutor (Prof. Derivo)"
    disclaimer: str = DERIVATIVES_DISCLAIMER
    model_used: str = ""
    latency_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()


class DerivativesAgent:
    """Specialized tutor agent for futures, options, and derivatives education."""

    def __init__(
        self,
        safety: DerivativesSafetyGuardrail | None = None,
        rag: RAGService | None = None,
        llm: LLMClient | None = None,
    ) -> None:
        self.safety = safety or derivatives_safety_guardrail
        self.rag = rag or rag_service
        self.llm = llm or llm_client

    def _extract_option_params(self, text: str) -> tuple[str | None, str | None, float | None, float | None]:
        """
        Extract (option_type, position, strike_price, premium) deterministically from text.
        Returns None for missing elements.
        """
        cleaned = text.replace(",", "")

        # Option Type
        opt_type: str | None = None
        if re.search(r"\b(call|ce)\b", cleaned, re.IGNORECASE):
            opt_type = "call"
        elif re.search(r"\b(put|pe)\b", cleaned, re.IGNORECASE):
            opt_type = "put"

        # Position (default to long if not specified)
        position: str | None = None
        if re.search(r"\b(short|sell|sold|writing|written|writer)\b", cleaned, re.IGNORECASE):
            position = "short"
        elif re.search(r"\b(long|buy|bought|buyer|purchased?)\b", cleaned, re.IGNORECASE):
            position = "long"
        elif opt_type is not None:
            position = "long"

        # Strike Price
        strike: float | None = None
        strike_match = re.search(r"(?:strike|strike\s+price|k)\s*(?:of|is|at)?\s*[:=]?\s*(?:₹|\brs\.?\s*)?(\d+(?:\.\d+)?)", cleaned, re.IGNORECASE)
        if strike_match:
            strike = float(strike_match.group(1))
        else:
            # Pattern like "24000 call" or "25000 CE"
            ticker_strike = re.search(r"\b(\d{4,6})\s*(?:call|put|ce|pe)\b", cleaned, re.IGNORECASE)
            if ticker_strike:
                strike = float(ticker_strike.group(1))

        # Premium
        premium: float | None = None
        prem_match = re.search(r"(?:premium|prem|cost|price)\s*(?:of|is|at)?\s*[:=]?\s*(?:₹|\brs\.?\s*)?(\d+(?:\.\d+)?)", cleaned, re.IGNORECASE)
        if prem_match:
            premium = float(prem_match.group(1))
        else:
            paying_match = re.search(r"(?:paying|paid|at)\s+(?:₹|\brs\.?\s*)?(\d+(?:\.\d+)?)\s*(?:premium)?\b", cleaned, re.IGNORECASE)
            if paying_match:
                val = float(paying_match.group(1))
                if strike is None or val != strike:
                    premium = val

        return opt_type, position, strike, premium

    def _extract_futures_params(self, text: str) -> tuple[str | None, float | None, int | None]:
        """Extract (position, entry_price, lot_size) deterministically."""
        cleaned = text.replace(",", "")
        position = "short" if re.search(r"\b(short|sell|sold)\b", cleaned, re.IGNORECASE) else "long"

        entry: float | None = None
        entry_match = re.search(r"(?:entry|price|bought\s+at|sold\s+at|at)\s*(?:₹|\brs\.?\s*)?(\d+(?:\.\d+)?)", cleaned, re.IGNORECASE)
        if entry_match:
            entry = float(entry_match.group(1))

        lot_size: int | None = None
        lot_match = re.search(r"(?:lot\s+size|lot|multiplier|quantity|qty)\s*(?:of|is)?\s*[:=]?\s*(\d+)", cleaned, re.IGNORECASE)
        if lot_match:
            lot_size = int(lot_match.group(1))

        return position, entry, lot_size

    def ask(
        self,
        query: str,
        conversation_history: list[dict[str, str]] | None = None,
        personalization: PersonalizationProfile | None = None,
        user_id: str | None = None,
    ) -> DerivativesAgentResult:
        """Execute the Derivatives Tutor pipeline."""
        t0 = time.perf_counter()

        # Step 1: Safety Evaluation (<1ms)
        safety_res = self.safety.evaluate(query)
        if not safety_res.is_safe:
            latency = round((time.perf_counter() - t0) * 1000, 2)
            return DerivativesAgentResult(
                query=query,
                answer=safety_res.refusal_message or "",
                grounding_status="ungrounded",
                citations=[],
                derivatives_data=None,
                grounding_sources=[],
                agent_name="Derivatives Tutor (Prof. Derivo)",
                disclaimer=DERIVATIVES_DISCLAIMER,
                model_used="deterministic_guardrail",
                latency_ms=latency,
            )

        q_lower = query.lower()
        has_calc_intent = any(w in q_lower for w in ["payoff", "pnl", "profit", "breakeven", "loss", "calculate"])

        # Step 2: Deterministic Calculation Tool Dispatch
        if has_calc_intent:
            if "future" in q_lower:
                pos, entry, lot = self._extract_futures_params(query)
                if entry is not None and lot is not None:
                    try:
                        fut_res = calculate_futures_pnl(pos or "long", entry, lot)
                        data_dict = fut_res.model_dump()
                        latency = round((time.perf_counter() - t0) * 1000, 2)
                        answer = (
                            f"### 📈 Futures Contract P&L Analysis ({fut_res.position.title()} Position)\n"
                            f"- **Entry Price (F₀):** ₹{fut_res.entry_price:,.2f}\n"
                            f"- **Contract Lot Size:** {fut_res.lot_size:,} units\n"
                            f"- **Breakeven Price:** ₹{fut_res.breakeven_price:,.2f}\n\n"
                            f"**Payoff Schedule Across Exit Prices:**\n"
                            f"| Exit Price (₹) | P&L per Unit (₹) | Total P&L (₹) |\n"
                            f"| :--- | :--- | :--- |\n"
                        )
                        for pt in fut_res.payoff_table:
                            sign = "+" if pt.total_pnl > 0 else ""
                            answer += f"| ₹{pt.exit_price:,.2f} | {sign}₹{pt.pnl_per_unit:,.2f} | **{sign}₹{pt.total_pnl:,.2f}** |\n"

                        return DerivativesAgentResult(
                            query=query,
                            answer=answer,
                            grounding_status="fully_grounded",
                            citations=[],
                            derivatives_data=data_dict,
                            grounding_sources=["derivatives_tool"],
                            agent_name="Derivatives Tutor (Prof. Derivo)",
                            disclaimer=DERIVATIVES_DISCLAIMER,
                            model_used="deterministic_derivatives_tool",
                            latency_ms=latency,
                        )
                    except ValueError as e:
                        logger.warning("Futures calculation error: %s", e)

            # Option calculation attempt
            opt_type, position, strike, premium = self._extract_option_params(query)
            if opt_type and strike is not None and premium is not None:
                try:
                    payoff_res = calculate_option_payoff(opt_type, position or "long", strike, premium)
                    data_dict = payoff_res.model_dump()
                    latency = round((time.perf_counter() - t0) * 1000, 2)

                    max_profit_str = f"₹{payoff_res.max_profit:,.2f}" if isinstance(payoff_res.max_profit, (int, float)) else str(payoff_res.max_profit)
                    max_loss_str = f"₹{payoff_res.max_loss:,.2f}" if isinstance(payoff_res.max_loss, (int, float)) else str(payoff_res.max_loss)

                    answer = (
                        f"### 🎯 Option Payoff Analysis: **{payoff_res.position.title()} {payoff_res.option_type.upper()}**\n"
                        f"- **Strike Price (K):** ₹{payoff_res.strike_price:,.2f}\n"
                        f"- **Premium Paid/Received:** ₹{payoff_res.premium:,.2f}\n"
                        f"- **Breakeven Price at Expiration:** **₹{payoff_res.breakeven_price:,.2f}**\n"
                        f"- **Maximum Potential Profit:** {max_profit_str}\n"
                        f"- **Maximum Potential Loss:** {max_loss_str}\n\n"
                        f"**Payoff Schedule at Expiration:**\n"
                        f"| Spot Price at Expiry (₹) | Gross Payoff (₹) | Net P&L (₹) |\n"
                        f"| :--- | :--- | :--- |\n"
                    )
                    for pt in payoff_res.payoff_table:
                        sign = "+" if pt.pnl > 0 else ""
                        status_bold = f"**{sign}₹{pt.pnl:,.2f}**"
                        answer += f"| ₹{pt.spot_price:,.2f} | ₹{pt.payoff:,.2f} | {status_bold} |\n"

                    return DerivativesAgentResult(
                        query=query,
                        answer=answer,
                        grounding_status="fully_grounded",
                        citations=[],
                        derivatives_data=data_dict,
                        grounding_sources=["derivatives_tool"],
                        agent_name="Derivatives Tutor (Prof. Derivo)",
                        disclaimer=DERIVATIVES_DISCLAIMER,
                        model_used="deterministic_derivatives_tool",
                        latency_ms=latency,
                    )
                except ValueError as e:
                    logger.warning("Option payoff calculation error: %s", e)

            # If user explicitly asked for calculation but required parameters are missing
            if any(w in q_lower for w in ["calculate", "payoff", "breakeven"]):
                latency = round((time.perf_counter() - t0) * 1000, 2)
                missing = []
                if not opt_type:
                    missing.append("Option Type (Call or Put)")
                if strike is None:
                    missing.append("Strike Price (e.g. ₹24,000)")
                if premium is None:
                    missing.append("Premium Paid/Received (e.g. ₹150)")

                prompt_msg = (
                    "To calculate your exact deterministic option payoff and breakeven, please supply the following missing parameters:\n"
                    + "\n".join(f"- **{m}**" for m in missing)
                    + "\n\n*Example:* `Calculate payoff for a Long Call with strike 25000 and premium 120`"
                )
                return DerivativesAgentResult(
                    query=query,
                    answer=prompt_msg,
                    grounding_status="ungrounded",
                    citations=[],
                    derivatives_data=None,
                    grounding_sources=["derivatives_tool"],
                    agent_name="Derivatives Tutor (Prof. Derivo)",
                    disclaimer=DERIVATIVES_DISCLAIMER,
                    model_used="deterministic_parameter_prompt",
                    latency_ms=latency,
                )

        # Step 3: Option Greeks Query Dispatch
        greek_match = None
        for g_name in ["delta", "gamma", "theta", "vega", "rho"]:
            if re.search(rf"\b{g_name}\b", q_lower):
                greek_match = g_name
                break

        if greek_match:
            g_info = get_greek_info(greek_match)
            if g_info:
                data_dict = {"greek": g_info.model_dump()}
                # Synthesize educational explanation with LLM
                pers_instruction = build_personalization_instruction(personalization)
                prompt = (
                    f"{DERIVATIVES_TUTOR_SYSTEM_PROMPT}\n{pers_instruction}\n\n"
                    f"Learner Query: {query}\n\n"
                    f"Authoritative Greek Definition:\n"
                    f"- Name: {g_info.name} ({g_info.symbol})\n"
                    f"- Definition: {g_info.definition}\n"
                    f"- Normal Bound: {g_info.range_or_bound}\n"
                    f"- Primary Driver: {g_info.primary_driver}\n"
                    f"- Practical Example: {g_info.pedagogical_example}\n\n"
                    f"Explain this Greek clearly to the learner, highlighting how it affects option pricing."
                )
                try:
                    llm_reply = self.llm.chat(prompt)
                except Exception as exc:
                    logger.warning("LLM generation failed for Greek: %s", exc)
                    llm_reply = (
                        f"### 📐 Option Greek: **{g_info.name} ({g_info.symbol})**\n\n"
                        f"- **Definition:** {g_info.definition}\n"
                        f"- **Typical Range:** {g_info.range_or_bound}\n"
                        f"- **Primary Driver:** {g_info.primary_driver}\n\n"
                        f"**Practical Example:**\n{g_info.pedagogical_example}"
                    )

                latency = round((time.perf_counter() - t0) * 1000, 2)
                return DerivativesAgentResult(
                    query=query,
                    answer=llm_reply,
                    grounding_status="fully_grounded",
                    citations=[],
                    derivatives_data=data_dict,
                    grounding_sources=["derivatives_tool"],
                    agent_name="Derivatives Tutor (Prof. Derivo)",
                    disclaimer=DERIVATIVES_DISCLAIMER,
                    model_used=getattr(self.llm, "model_name", "ollama"),
                    latency_ms=latency,
                )

        # Step 4: Tier 1 SEBI RAG Retrieval for Conceptual & Regulatory Inquiries
        sys_prompt = DERIVATIVES_TUTOR_SYSTEM_PROMPT
        if personalization:
            inst = build_personalization_instruction(personalization)
            if inst:
                sys_prompt = DERIVATIVES_TUTOR_SYSTEM_PROMPT + inst

        try:
            rag_ans = self.rag.generate_answer(
                query=query,
                system_prompt=sys_prompt,
            )
            answer = rag_ans.answer
            citations = rag_ans.citations
            grounding_status = rag_ans.grounding_status
            model_used = rag_ans.model_used
        except Exception as exc:
            logger.error("RAG generation error: %s", exc)
            answer = "Finova AI Derivatives Tutor is temporarily unable to generate an explanation. Please try again shortly."
            citations = []
            grounding_status = "ungrounded"
            model_used = "error_fallback"

        latency = round((time.perf_counter() - t0) * 1000, 2)
        sources: list[str] = ["sebi_rag"] if grounding_status == "fully_grounded" else []
        return DerivativesAgentResult(
            query=query,
            answer=answer,
            grounding_status=grounding_status,
            citations=citations,
            derivatives_data=None,
            grounding_sources=sources,
            agent_name="Derivatives Tutor (Prof. Derivo)",
            disclaimer=DERIVATIVES_DISCLAIMER,
            model_used=model_used,
            latency_ms=latency,
        )


derivatives_agent = DerivativesAgent()
