"""
Safety guardrail for the Crypto Tutor Agent.
Delegates to the centralized CryptoSafetyRules in app.router.safety.
"""

from __future__ import annotations

from app.router.safety import GLOBAL_REFUSAL_MESSAGE, CryptoSafetyRules, GuaranteedReturnsRules, GlobalSafetyResult


class CryptoSafetyGuardrail:
    """Deterministic safety guardrail for the Crypto Agent."""

    def evaluate(self, query: str) -> GlobalSafetyResult:
        cleaned = query.strip()
        if not cleaned:
            return GlobalSafetyResult(is_safe=True)

        if GuaranteedReturnsRules.is_unsafe(cleaned):
            return GlobalSafetyResult(
                is_safe=False,
                refusal_reason="guaranteed_returns_inquiry",
                refusal_message=GLOBAL_REFUSAL_MESSAGE,
                domain="CRYPTO",
            )

        if CryptoSafetyRules.is_unsafe(cleaned):
            return GlobalSafetyResult(
                is_safe=False,
                refusal_reason="crypto_advisory_intent",
                refusal_message=GLOBAL_REFUSAL_MESSAGE,
                domain="CRYPTO",
            )

        return GlobalSafetyResult(is_safe=True)


crypto_safety_guardrail = CryptoSafetyGuardrail()
