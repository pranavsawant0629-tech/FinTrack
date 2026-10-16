"""
Deterministic safety guardrail for the Portfolio Tutor Agent.
Pre-filters queries to block personalized portfolio reallocation directives,
buy/sell rebalancing orders, and real trade execution attempts.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

PORTFOLIO_SAFETY_REFUSAL = (
    "Finova AI is an educational platform and cannot provide personalized portfolio rebalancing "
    "advice, buy/sell directives, or asset reallocation orders. All investments carry market risk, "
    "and Finova AI does not execute trades or manage accounts. I can, however, provide educational "
    "analysis of your simulated portfolio's diversification, calculate asset and sector allocations, "
    "or model 'what-if' market movement scenarios."
)


@dataclass(frozen=True)
class PortfolioSafetyResult:
    """Outcome of portfolio safety evaluation."""
    is_safe: bool
    refusal_reason: str | None = None
    refusal_message: str | None = None


class PortfolioSafetyGuardrail:
    """Evaluates whether a query requests actionable portfolio reallocation or trade execution."""

    ADVISORY_PATTERNS = [
        re.compile(
            r"\b(?:how\s+should\s+i|tell\s+me\s+how\s+to)\s+(?:rebalance|reallocate|restructure)\s+(?:my\s+)?portfolio\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\bshould\s+i\s+(?:sell|liquidate|trim|exit)\s+.*?\s+(?:to\s+buy|and\s+invest\s+in|for)\s+[a-zA-Z0-9&]+\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(?:(?:tell\s+me\s+)?(?:which|what))\s+(?:stocks?|shares?|holdings?|funds?)\s+(?:should\s+(?:i\s+)?|to\s+)?(?:sell|remove|drop|cut|trim|buy)(?:\s+from\s+my\s+portfolio)?\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(?:tell\s+me\s+)?what\s+(?:to\s+buy|should\s+i\s+buy)\s+with\s+my\s+cash\s*(?:balance)?\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(?:place|execute|submit)\s+(?:an?\s+)?(?:order|trade|transaction)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(?:buy|sell)\s+\d+\s+shares?\s+of\s+[a-zA-Z0-9&]+\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\bexecute\s+trade\s+for\s+my\s+portfolio\b",
            re.IGNORECASE,
        ),
    ]

    CONCEPTUAL_DEFINITIONS = [
        re.compile(r"^(?:what\s+is|what\s+are|define|explain|meaning\s+of)\s+(?:portfolio\s+)?(?:rebalancing|asset\s+allocation|diversification)\b", re.IGNORECASE),
    ]

    def evaluate(self, query: str) -> PortfolioSafetyResult:
        cleaned = query.strip()
        if not cleaned:
            return PortfolioSafetyResult(is_safe=True)

        for pattern in self.ADVISORY_PATTERNS:
            if pattern.search(cleaned):
                if self._is_conceptual_exception(cleaned):
                    continue
                return PortfolioSafetyResult(
                    is_safe=False,
                    refusal_reason="portfolio_advisory_intent",
                    refusal_message=PORTFOLIO_SAFETY_REFUSAL,
                )

        return PortfolioSafetyResult(is_safe=True)

    def _is_conceptual_exception(self, query: str) -> bool:
        # If the user specifically refers to personal portfolio rebalancing or personal buy/sell directives, never exempt
        if re.search(r"\b(?:my\s+portfolio|should\s+i|tell\s+me\s+which|tell\s+me\s+what|place\s+an?\s+order|execute)\b", query, re.IGNORECASE):
            return False
        return any(cp.search(query) for cp in self.CONCEPTUAL_DEFINITIONS)


portfolio_safety_guardrail = PortfolioSafetyGuardrail()
