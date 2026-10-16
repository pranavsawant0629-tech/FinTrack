"""
Personal Finance Tutor Agent for Finova AI (Prof. Persona).

Coordinates:
1. Deterministic safety evaluation (blocks personal portfolio allocation directives)
2. Deterministic mathematical calculation tools (50/30/20, compound interest, emergency fund)
3. Pedagogical financial planning and budgeting explanations
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any, Literal
from pydantic import BaseModel, Field

from app.agents.personal_finance.prompts import PF_DISCLAIMER, PF_TUTOR_SYSTEM_PROMPT
from app.agents.personal_finance.safety import PersonalFinanceSafetyGuardrail, personal_finance_safety_guardrail
from app.llm.llm_client import LLMClient, llm_client
from app.tools.calc.budget import calculate_50_30_20
from app.tools.calc.compounding import calculate_compound_interest, calculate_sip
from app.tools.calc.emergency_fund import calculate_emergency_fund

logger = logging.getLogger(__name__)


class PersonalFinanceAgentResult(BaseModel):
    """Response contract for the Personal Finance Tutor Agent."""
    query: str
    answer: str
    grounding_status: Literal["fully_grounded", "partially_grounded", "ungrounded"]
    calc_data: dict[str, Any] | None = None
    grounding_sources: list[Literal["sebi_rag", "live_market_data", "crypto_data", "calc_tool"]] = Field(
        default_factory=list
    )
    agent_name: str = "Personal Finance Tutor (Prof. Persona)"
    disclaimer: str = PF_DISCLAIMER
    model_used: str = ""
    latency_ms: float = 0.0


class PersonalFinanceAgent:
    """Specialized tutor agent for budgeting, saving, and financial planning."""

    def __init__(
        self,
        safety: PersonalFinanceSafetyGuardrail | None = None,
        llm: LLMClient | None = None,
    ) -> None:
        self.safety = safety or personal_finance_safety_guardrail
        self.llm = llm or llm_client

    def _extract_number(self, text: str) -> float | None:
        """Extract first prominent numerical value from query text."""
        cleaned = text.replace(",", "")
        matches = re.findall(r"(?:₹|\brs\.?\s*)?(\d+(?:\.\d+)?)", cleaned, re.IGNORECASE)
        for m in matches:
            val = float(m)
            # Skip rule numbers like 50, 30, 20
            if val not in (50.0, 30.0, 20.0, 503020.0):
                return val
        return None

    def _extract_compound_params(self, text: str) -> tuple[float | None, float | None, float | None]:
        """Extract (principal, rate_pct, tenure_years) deterministically."""
        cleaned = text.replace(",", "")

        rate: float | None = None
        rate_match = re.search(r"(-?\d+(?:\.\d+)?)\s*(?:%|\s*percent\b)", cleaned, re.IGNORECASE)
        if rate_match:
            rate = float(rate_match.group(1))

        tenure: float | None = None
        tenure_match = re.search(r"(-?\d+(?:\.\d+)?)\s*(?:years?|yrs?)\b", cleaned, re.IGNORECASE)
        if tenure_match:
            tenure = float(tenure_match.group(1))

        principal: float | None = None
        p_explicit = re.search(r"(?:principal|amount|sum|invested?|deposit)(?:\s+of)?\s*(?:₹|\brs\.?\s*)?(-?\d+(?:\.\d+)?)", cleaned, re.IGNORECASE)
        if p_explicit:
            principal = float(p_explicit.group(1))
        else:
            currency_match = re.search(r"(?:₹|\brs\.?\s*)(-?\d+(?:\.\d+)?)", cleaned, re.IGNORECASE)
            if currency_match:
                principal = float(currency_match.group(1))
            else:
                all_nums = re.findall(r"\b(-?\d+(?:\.\d+)?)\b", cleaned)
                for num_str in all_nums:
                    val = float(num_str)
                    if rate is not None and val == rate:
                        continue
                    if tenure is not None and val == tenure:
                        continue
                    if val >= 100 or val < 0:
                        principal = val
                        break

        return principal, rate, tenure

    def _extract_sip_params(self, text: str) -> tuple[float | None, float | None, float | None]:
        """Extract (monthly_investment, return_pct, tenure_years) deterministically."""
        cleaned = text.replace(",", "")

        rate: float | None = None
        rate_match = re.search(r"(-?\d+(?:\.\d+)?)\s*(?:%|\s*percent\b)", cleaned, re.IGNORECASE)
        if rate_match:
            rate = float(rate_match.group(1))

        tenure: float | None = None
        tenure_match = re.search(r"(-?\d+(?:\.\d+)?)\s*(?:years?|yrs?)\b", cleaned, re.IGNORECASE)
        if tenure_match:
            tenure = float(tenure_match.group(1))

        monthly: float | None = None
        m_explicit = re.search(r"(?:monthly|sip|installment|invest)(?:\s+of)?\s*(?:₹|\brs\.?\s*)?(-?\d+(?:\.\d+)?)", cleaned, re.IGNORECASE)
        if m_explicit:
            monthly = float(m_explicit.group(1))
        else:
            currency_match = re.search(r"(?:₹|\brs\.?\s*)(-?\d+(?:\.\d+)?)", cleaned, re.IGNORECASE)
            if currency_match:
                monthly = float(currency_match.group(1))
            else:
                all_nums = re.findall(r"\b(-?\d+(?:\.\d+)?)\b", cleaned)
                for num_str in all_nums:
                    val = float(num_str)
                    if rate is not None and val == rate:
                        continue
                    if tenure is not None and val == tenure:
                        continue
                    if val >= 100 or val < 0:
                        monthly = val
                        break

        return monthly, rate, tenure

    def ask(
        self,
        query: str,
        conversation_history: list[dict[str, str]] | None = None,
        personalization: Any | None = None,
    ) -> PersonalFinanceAgentResult:
        """Execute the Personal Finance Tutor pipeline."""
        t0 = time.perf_counter()

        # Step 1: Safety Check
        safety_res = self.safety.evaluate(query)
        if not safety_res.is_safe:
            latency = round((time.perf_counter() - t0) * 1000, 2)
            return PersonalFinanceAgentResult(
                query=query,
                answer=safety_res.refusal_message or "",
                grounding_status="ungrounded",
                calc_data=None,
                grounding_sources=[],
                agent_name="Personal Finance Tutor (Prof. Persona)",
                disclaimer=PF_DISCLAIMER,
                model_used="deterministic_guardrail",
                latency_ms=latency,
            )

        lower_query = query.lower()

        # Step 2: Deterministic Compound Interest Calculation
        if "compound interest" in lower_query or "compounding" in lower_query:
            has_calc_intent = any(w in lower_query for w in ["calculate", "formula for", "returns on", "how much will", "maturity", "%", "years"])
            is_pure_conceptual = query.strip().lower().startswith(("what is", "explain", "how does", "define")) and not has_calc_intent

            if not is_pure_conceptual:
                p, r, t = self._extract_compound_params(query)
                if p is None or r is None or t is None:
                    latency = round((time.perf_counter() - t0) * 1000, 2)
                    clarification = (
                        "### 🧮 Compound Interest Calculation Required Parameters:\n\n"
                        "To calculate compound interest deterministically, please provide all three required parameters:\n"
                        "1. **Principal Amount** (e.g. ₹1,00,000)\n"
                        "2. **Annual Interest Rate** (e.g. 10%)\n"
                        "3. **Investment Tenure** (e.g. 5 years)\n\n"
                        "*Example: 'Calculate compound interest on ₹1,00,000 at 10% for 5 years'*"
                    )
                    return PersonalFinanceAgentResult(
                        query=query,
                        answer=clarification,
                        grounding_status="ungrounded",
                        calc_data=None,
                        grounding_sources=[],
                        agent_name="Personal Finance Tutor (Prof. Persona)",
                        disclaimer=PF_DISCLAIMER,
                        model_used="deterministic_guardrail",
                        latency_ms=latency,
                    )

                if p <= 0 or r <= 0 or t <= 0:
                    latency = round((time.perf_counter() - t0) * 1000, 2)
                    return PersonalFinanceAgentResult(
                        query=query,
                        answer="Invalid input: Principal amount, annual interest rate, and tenure must all be positive numbers greater than zero.",
                        grounding_status="ungrounded",
                        calc_data=None,
                        grounding_sources=[],
                        agent_name="Personal Finance Tutor (Prof. Persona)",
                        disclaimer=PF_DISCLAIMER,
                        model_used="deterministic_guardrail",
                        latency_ms=latency,
                    )

                try:
                    calc = calculate_compound_interest(principal=p, annual_rate_pct=r, tenure_years=t)
                    ci_text = (
                        f"### 🧮 Compound Interest Calculation:\n\n"
                        f"- **Initial Principal:** ₹{p:,.2f}\n"
                        f"- **Annual Interest Rate:** {r:.2f}%\n"
                        f"- **Tenure:** {t:.1f} years\n"
                        f"- **Total Maturity Value:** ₹{calc['maturity_amount']:,.2f}\n"
                        f"- **Total Wealth Generated:** ₹{calc['interest_earned']:,.2f}\n\n"
                        f"*Note: Calculation is strictly deterministic using discrete annual compounding formula A = P(1 + r/n)^(nt).*"
                    )
                    latency = round((time.perf_counter() - t0) * 1000, 2)
                    return PersonalFinanceAgentResult(
                        query=query,
                        answer=ci_text,
                        grounding_status="fully_grounded",
                        calc_data=calc,
                        grounding_sources=["calc_tool"],
                        agent_name="Personal Finance Tutor (Prof. Persona)",
                        disclaimer=PF_DISCLAIMER,
                        model_used="deterministic_tools",
                        latency_ms=latency,
                    )
                except Exception as exc:
                    logger.warning("Compound interest calculation failed: %s", exc)

        # Step 3: Deterministic SIP Calculation
        if re.search(r"\b(?:sip|systematic\s+investment)\b", lower_query):
            has_calc_intent = any(w in lower_query for w in ["calculate", "returns", "future value", "investing", "yield", "accumulation", "%", "years", "monthly"])
            is_pure_conceptual = query.strip().lower().startswith(("what is", "explain", "how does", "define")) and not has_calc_intent

            if not is_pure_conceptual:
                m, r, t = self._extract_sip_params(query)
                if m is None or r is None or t is None:
                    latency = round((time.perf_counter() - t0) * 1000, 2)
                    clarification = (
                        "### 🧮 Systematic Investment Plan (SIP) Required Parameters:\n\n"
                        "To calculate SIP wealth accumulation deterministically, please provide all three required parameters:\n"
                        "1. **Monthly Investment Amount** (e.g. ₹5,000)\n"
                        "2. **Expected Annual Return Rate** (e.g. 12%)\n"
                        "3. **Investment Tenure** (e.g. 10 years)\n\n"
                        "*Example: 'Calculate SIP for ₹5,000 per month at 12% for 10 years'*"
                    )
                    return PersonalFinanceAgentResult(
                        query=query,
                        answer=clarification,
                        grounding_status="ungrounded",
                        calc_data=None,
                        grounding_sources=[],
                        agent_name="Personal Finance Tutor (Prof. Persona)",
                        disclaimer=PF_DISCLAIMER,
                        model_used="deterministic_guardrail",
                        latency_ms=latency,
                    )

                if m <= 0 or r <= 0 or t <= 0:
                    latency = round((time.perf_counter() - t0) * 1000, 2)
                    return PersonalFinanceAgentResult(
                        query=query,
                        answer="Invalid input: Monthly investment, expected annual return, and tenure must all be positive numbers greater than zero.",
                        grounding_status="ungrounded",
                        calc_data=None,
                        grounding_sources=[],
                        agent_name="Personal Finance Tutor (Prof. Persona)",
                        disclaimer=PF_DISCLAIMER,
                        model_used="deterministic_guardrail",
                        latency_ms=latency,
                    )

                try:
                    calc = calculate_sip(monthly_investment=m, annual_return_pct=r, tenure_years=t)
                    sip_text = (
                        f"### 🧮 Systematic Investment Plan (SIP) Calculation:\n\n"
                        f"- **Monthly Investment:** ₹{m:,.2f}\n"
                        f"- **Expected Annual Return:** {r:.2f}%\n"
                        f"- **Tenure:** {t:.1f} years\n"
                        f"- **Total Amount Invested:** ₹{calc['total_invested']:,.2f}\n"
                        f"- **Estimated Future Value:** ₹{calc['future_value']:,.2f}\n"
                        f"- **Estimated Wealth Gain:** ₹{calc['wealth_gain']:,.2f}\n\n"
                        f"*Note: Calculation is strictly deterministic using monthly annuity due formula M = P * [((1+i)^k - 1)/i] * (1+i).*"
                    )
                    latency = round((time.perf_counter() - t0) * 1000, 2)
                    return PersonalFinanceAgentResult(
                        query=query,
                        answer=sip_text,
                        grounding_status="fully_grounded",
                        calc_data=calc,
                        grounding_sources=["calc_tool"],
                        agent_name="Personal Finance Tutor (Prof. Persona)",
                        disclaimer=PF_DISCLAIMER,
                        model_used="deterministic_tools",
                        latency_ms=latency,
                    )
                except Exception as exc:
                    logger.warning("SIP calculation failed: %s", exc)

        # Step 4: Deterministic 50/30/20 Budgeting Calculation
        if "50/30/20" in lower_query or "budget" in lower_query or "split" in lower_query:
            income = self._extract_number(query)
            if income and income > 0:
                calc = calculate_50_30_20(income)
                breakdown_text = (
                    f"### 🧮 50/30/20 Budget Breakdown for Monthly Income of **₹{income:,.2f}**:\n\n"
                    f"- **Needs (50%):** ₹{calc['needs']:,.2f}\n"
                    f"  *Covers non-negotiable living essentials: rent/home loan, utilities, groceries, and basic transit.*\n"
                    f"- **Wants (30%):** ₹{calc['wants']:,.2f}\n"
                    f"  *Covers discretionary lifestyle spending: dining out, leisure, subscriptions, and entertainment.*\n"
                    f"- **Savings & Debt Repayment (20%):** ₹{calc['savings']:,.2f}\n"
                    f"  *Covers building an emergency fund, long-term investments, and prepaying high-interest debt.*\n\n"
                    f"*Note: Calculations are strictly deterministic based on Elizabeth Warren's 50/30/20 budgeting framework.*"
                )
                latency = round((time.perf_counter() - t0) * 1000, 2)
                return PersonalFinanceAgentResult(
                    query=query,
                    answer=breakdown_text,
                    grounding_status="fully_grounded",
                    calc_data=calc,
                    grounding_sources=["calc_tool"],
                    agent_name="Personal Finance Tutor (Prof. Persona)",
                    disclaimer=PF_DISCLAIMER,
                    model_used="deterministic_tools",
                    latency_ms=latency,
                )
            elif any(w in lower_query for w in ["calculate", "split my", "breakdown for", "split income"]):
                latency = round((time.perf_counter() - t0) * 1000, 2)
                clarification = (
                    "### 🧮 50/30/20 Budget Calculation Parameter Required:\n\n"
                    "To generate a deterministic 50/30/20 budget breakdown, please specify your monthly net income.\n"
                    "*Example: 'How should I budget an income of ₹60,000 using 50/30/20?'*"
                )
                return PersonalFinanceAgentResult(
                    query=query,
                    answer=clarification,
                    grounding_status="ungrounded",
                    calc_data=None,
                    grounding_sources=[],
                    agent_name="Personal Finance Tutor (Prof. Persona)",
                    disclaimer=PF_DISCLAIMER,
                    model_used="deterministic_guardrail",
                    latency_ms=latency,
                )

        # Step 5: Deterministic Emergency Fund Calculation
        if "emergency fund" in lower_query and any(w in lower_query for w in ["calculate", "target", "need", "for"]):
            expense = self._extract_number(query)
            if expense and expense > 0:
                calc = calculate_emergency_fund(monthly_expenses=expense)
                ef_text = (
                    f"### 🛡️ Emergency Fund Adequacy Target (Monthly Expenses: **₹{expense:,.2f}**):\n\n"
                    f"- **Recommended Reserve (6 Months):** ₹{calc['target_fund']:,.2f}\n"
                    f"- **Minimum Essential Reserve (3 Months):** ₹{expense * 3:,.2f}\n"
                    f"- **Conservative Reserve (12 Months):** ₹{expense * 12:,.2f}\n\n"
                    f"*Tip: Keep your emergency reserves in high-liquidity instruments like high-yield savings accounts or liquid mutual funds rather than volatile equity.*"
                )
                latency = round((time.perf_counter() - t0) * 1000, 2)
                return PersonalFinanceAgentResult(
                    query=query,
                    answer=ef_text,
                    grounding_status="fully_grounded",
                    calc_data=calc,
                    grounding_sources=["calc_tool"],
                    agent_name="Personal Finance Tutor (Prof. Persona)",
                    disclaimer=PF_DISCLAIMER,
                    model_used="deterministic_tools",
                    latency_ms=latency,
                )
            elif any(w in lower_query for w in ["calculate", "target for", "how much emergency fund"]):
                latency = round((time.perf_counter() - t0) * 1000, 2)
                clarification = (
                    "### 🛡️ Emergency Fund Calculation Parameter Required:\n\n"
                    "To calculate your emergency fund target deterministically, please specify your estimated monthly expenses.\n"
                    "*Example: 'Calculate emergency fund for monthly expenses of ₹30,000'*"
                )
                return PersonalFinanceAgentResult(
                    query=query,
                    answer=clarification,
                    grounding_status="ungrounded",
                    calc_data=None,
                    grounding_sources=[],
                    agent_name="Personal Finance Tutor (Prof. Persona)",
                    disclaimer=PF_DISCLAIMER,
                    model_used="deterministic_guardrail",
                    latency_ms=latency,
                )

        # Step 6: Pedagogical Conceptual Generation (Prof. Persona)
        model_name = str(getattr(self.llm, "model", "qwen2.5:7b-instruct"))
        sys_prompt = PF_TUTOR_SYSTEM_PROMPT
        if personalization:
            from app.memory.models import build_personalization_instruction
            inst = build_personalization_instruction(personalization)
            if inst:
                sys_prompt = PF_TUTOR_SYSTEM_PROMPT + inst

        try:
            explanation = self.llm.chat(
                message=query,
                system=sys_prompt,
                temperature=0.1,
            )
            latency = round((time.perf_counter() - t0) * 1000, 2)
            return PersonalFinanceAgentResult(
                query=query,
                answer=explanation.strip(),
                grounding_status="ungrounded",
                calc_data=None,
                grounding_sources=[],
                agent_name="Personal Finance Tutor (Prof. Persona)",
                disclaimer=PF_DISCLAIMER,
                model_used=model_name,
                latency_ms=latency,
            )
        except Exception as exc:
            logger.error("LLM inference error in PersonalFinanceAgent: %s", exc)
            fallback_text = (
                "Personal financial planning focuses on disciplined budgeting (such as the 50/30/20 rule), "
                "maintaining a 3–6 month emergency fund, minimizing high-interest debt, and investing systematically."
            )
            latency = round((time.perf_counter() - t0) * 1000, 2)
            return PersonalFinanceAgentResult(
                query=query,
                answer=fallback_text,
                grounding_status="ungrounded",
                calc_data=None,
                grounding_sources=[],
                agent_name="Personal Finance Tutor (Prof. Persona)",
                disclaimer=PF_DISCLAIMER,
                model_used="fallback",
                latency_ms=latency,
            )


personal_finance_agent = PersonalFinanceAgent()
