"""
Portfolio Tutor Agent for Finova AI.

Coordinates:
1. Deterministic safety evaluation (blocks rebalancing directives and trade execution)
2. Deterministic portfolio accounting metrics (cost basis vs market value vs cash)
3. Deterministic 'what-if' market movement simulations
4. Pedagogical portfolio management explanations adapted to learner profile
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any, Literal
from pydantic import BaseModel, Field

from app.agents.portfolio.prompts import PORTFOLIO_DISCLAIMER, PORTFOLIO_TUTOR_SYSTEM_PROMPT
from app.agents.portfolio.safety import PortfolioSafetyGuardrail, portfolio_safety_guardrail
from app.llm.llm_client import LLMClient, llm_client
from app.memory.models import PersonalizationProfile, build_personalization_instruction
from app.tools.portfolio.models import PortfolioData, PortfolioMetrics, WhatIfSimulationResult
from app.tools.portfolio.providers.mock import create_demo_portfolio
from app.tools.portfolio.service import PortfolioService, portfolio_service

logger = logging.getLogger(__name__)


class PortfolioAgentResult(BaseModel):
    """Standardized response contract for the Portfolio Tutor Agent."""
    query: str
    answer: str
    grounding_status: Literal["fully_grounded", "partially_grounded", "ungrounded"]
    portfolio_data: dict[str, Any] | None = None
    grounding_sources: list[str] = Field(default_factory=list)
    agent_name: str = "Portfolio Tutor"
    disclaimer: str = PORTFOLIO_DISCLAIMER
    model_used: str = ""
    latency_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()


class PortfolioAgent:
    """Specialized tutor agent for simulated portfolio analysis and diversification education."""

    def __init__(
        self,
        safety: PortfolioSafetyGuardrail | None = None,
        service: PortfolioService | None = None,
        llm: LLMClient | None = None,
    ) -> None:
        self.safety = safety or portfolio_safety_guardrail
        self.service = service or portfolio_service
        self.llm = llm or llm_client

    def _extract_what_if_params(self, text: str) -> tuple[str | None, float | None, bool]:
        """
        Extract target asset, percentage change, and broad-market flag from what-if query.
        Returns (target_symbol, change_pct, is_broad_market).
        """
        cleaned = text.replace(",", "")
        pct_match = re.search(r"(-?\d+(?:\.\d+)?)\s*%", cleaned)
        if not pct_match:
            # Check for words like "5 percent"
            pct_match = re.search(r"(-?\d+(?:\.\d+)?)\s*percent\b", cleaned, re.IGNORECASE)

        if not pct_match:
            return None, None, False

        val = float(pct_match.group(1))

        # Check directional indicator (falls, drops, crashes, negative sign)
        is_negative = bool(re.search(r"\b(falls?|drops?|crashes?|down|loses?|decreases?)\b", cleaned, re.IGNORECASE))
        if is_negative and val > 0:
            val = -val

        is_broad = bool(re.search(r"\b(nifty|market|sensex|index|all\s+stocks)\b", cleaned, re.IGNORECASE))

        symbol: str | None = None
        if not is_broad:
            from app.tools.market.intent import EQUITY_ALIASES
            upper = cleaned.upper()
            for alias, canonical in sorted(EQUITY_ALIASES.items(), key=lambda x: -len(x[0])):
                if re.search(rf"\b{re.escape(alias)}\b", upper):
                    symbol = canonical
                    break

        return symbol, val, is_broad

    def ask(
        self,
        query: str,
        user_id: str | None = None,
        conversation_history: list[dict[str, str]] | None = None,
        personalization: PersonalizationProfile | None = None,
    ) -> PortfolioAgentResult:
        """Execute the Portfolio Tutor pipeline."""
        t0 = time.perf_counter()

        # Step 1: Safety Check (<1ms)
        safety_res = self.safety.evaluate(query)
        if not safety_res.is_safe:
            latency = round((time.perf_counter() - t0) * 1000, 2)
            return PortfolioAgentResult(
                query=query,
                answer=safety_res.refusal_message or "",
                grounding_status="ungrounded",
                portfolio_data=None,
                grounding_sources=[],
                agent_name="Portfolio Tutor",
                disclaimer=PORTFOLIO_DISCLAIMER,
                model_used="deterministic_guardrail",
                latency_ms=latency,
            )

        # Step 2: Fetch Portfolio (User isolated; fallback to demo portfolio if not found)
        effective_user_id = user_id or "demo_user"
        portfolio = self.service.get_portfolio(effective_user_id)
        if portfolio is None:
            # Provide educational demo portfolio if user has no saved portfolio
            portfolio = create_demo_portfolio(effective_user_id)

        # Step 3: Check for 'What-If' Simulation Inquiry
        target_sym, change_pct, is_broad = self._extract_what_if_params(query)
        if change_pct is not None:
            sim_res: WhatIfSimulationResult = self.service.simulate_what_if(
                portfolio=portfolio,
                target_symbol=target_sym,
                change_pct=change_pct,
                broad_market=is_broad,
            )
            data_dict = sim_res.model_dump()
            sign = "+" if sim_res.portfolio_delta_value > 0 else ""
            answer = (
                f"### 🧪 Simulated Portfolio Stress Test\n"
                f"**Scenario:** {sim_res.scenario_description}\n\n"
                f"- **Original Portfolio Value:** ₹{sim_res.original_portfolio_value:,.2f}\n"
                f"- **Simulated Portfolio Value:** ₹{sim_res.simulated_portfolio_value:,.2f}\n"
                f"- **Projected Portfolio Impact:** **{sign}₹{sim_res.portfolio_delta_value:,.2f} ({sign}{sim_res.portfolio_delta_pct:.2f}%)**\n\n"
            )
            if sim_res.impacted_holdings:
                answer += (
                    f"**Impacted Holdings:**\n"
                    f"| Holding | Original Price | Simulated Price | Value Impact |\n"
                    f"| :--- | :--- | :--- | :--- |\n"
                )
                for h_imp in sim_res.impacted_holdings:
                    h_sign = "+" if h_imp.value_delta > 0 else ""
                    answer += f"| **{h_imp.symbol}** | ₹{h_imp.original_price:,.2f} | ₹{h_imp.simulated_price:,.2f} | {h_sign}₹{h_imp.value_delta:,.2f} |\n"

            latency = round((time.perf_counter() - t0) * 1000, 2)
            return PortfolioAgentResult(
                query=query,
                answer=answer,
                grounding_status="fully_grounded",
                portfolio_data=data_dict,
                grounding_sources=["portfolio_tool"],
                agent_name="Portfolio Tutor",
                disclaimer=PORTFOLIO_DISCLAIMER,
                model_used="deterministic_portfolio_tool",
                latency_ms=latency,
            )

        # Step 4: Deterministic Portfolio Valuation & Analytics
        metrics: PortfolioMetrics = self.service.calculate_metrics(portfolio)
        data_dict = {
            "portfolio": portfolio.model_dump(),
            "metrics": metrics.model_dump(),
        }

        sign = "+" if metrics.unrealized_pnl > 0 else ""
        lines = [
            f"### 📊 Simulated Portfolio Analysis ({effective_user_id})\n",
            f"- **Total Portfolio Value:** **₹{metrics.total_portfolio_value:,.2f}**",
            f"- **Securities Market Value:** ₹{metrics.securities_market_value:,.2f}",
            f"- **Securities Cost Basis:** ₹{metrics.securities_cost_basis:,.2f}",
            f"- **Cash Balance (Liquidity):** ₹{metrics.cash_balance:,.2f}",
            f"- **Unrealized Gain / Loss:** **{sign}₹{metrics.unrealized_pnl:,.2f} ({sign}{metrics.unrealized_pnl_pct:.2f}%)**",
            f"- **Diversification Assessment:** {metrics.diversification_assessment}\n",
            "**Asset Allocation Breakdown:**",
        ]
        for asset, alloc_pct in sorted(metrics.asset_allocation.items(), key=lambda x: -x[1]):
            lines.append(f"- **{asset.replace('_', ' ').title()}:** {alloc_pct:.1f}%")

        if metrics.sector_allocation:
            lines.append("\n**Securities Sector Allocation:**")
            for sector, sec_pct in sorted(metrics.sector_allocation.items(), key=lambda x: -x[1]):
                lines.append(f"- **{sector}:** {sec_pct:.1f}%")

        if portfolio.holdings:
            lines.append("\n**Active Holdings:**")
            lines.append("| Symbol | Qty | Avg Price | Current Price | Market Value | P&L |")
            lines.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
            for h in portfolio.holdings:
                h_sign = "+" if h.unrealized_pnl > 0 else ""
                lines.append(
                    f"| **{h.symbol}** | {h.quantity} | ₹{h.average_buy_price:,.2f} | "
                    f"₹{h.current_price:,.2f} | ₹{h.market_value:,.2f} | {h_sign}₹{h.unrealized_pnl:,.2f} ({h_sign}{h.unrealized_pnl_pct:.1f}%) |"
                )

        answer = "\n".join(lines)
        latency = round((time.perf_counter() - t0) * 1000, 2)
        return PortfolioAgentResult(
            query=query,
            answer=answer,
            grounding_status="fully_grounded",
            portfolio_data=data_dict,
            grounding_sources=["portfolio_tool"],
            agent_name="Portfolio Tutor",
            disclaimer=PORTFOLIO_DISCLAIMER,
            model_used="deterministic_portfolio_tool",
            latency_ms=latency,
        )


portfolio_agent = PortfolioAgent()
