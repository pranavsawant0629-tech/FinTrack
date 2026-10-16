"""
Safety guardrail for the Personal Finance Tutor Agent.
Delegates to centralized PersonalFinanceSafetyRules in app.router.safety.
"""

from __future__ import annotations

from app.router.safety import (
    GLOBAL_REFUSAL_MESSAGE,
    GlobalSafetyResult,
    GuaranteedReturnsRules,
    PersonalFinanceSafetyRules,
)


class PersonalFinanceSafetyGuardrail:
    """Deterministic safety guardrail for the Personal Finance Agent."""

    def evaluate(self, query: str) -> GlobalSafetyResult:
        cleaned = query.strip()
        if not cleaned:
            return GlobalSafetyResult(is_safe=True)

        if GuaranteedReturnsRules.is_unsafe(cleaned):
            return GlobalSafetyResult(
                is_safe=False,
                refusal_reason="guaranteed_returns_inquiry",
                refusal_message=GLOBAL_REFUSAL_MESSAGE,
                domain="PERSONAL_FINANCE",
            )

        if PersonalFinanceSafetyRules.is_unsafe(cleaned):
            return GlobalSafetyResult(
                is_safe=False,
                refusal_reason="personal_finance_advisory_intent",
                refusal_message=GLOBAL_REFUSAL_MESSAGE,
                domain="PERSONAL_FINANCE",
            )

        return GlobalSafetyResult(is_safe=True)


personal_finance_safety_guardrail = PersonalFinanceSafetyGuardrail()
