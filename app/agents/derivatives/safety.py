"""
Deterministic safety guardrail for the Derivatives Tutor Agent (Prof. Derivo).
Pre-filters incoming queries to reject options trading tips, strike recommendations,
and speculative expiry gambling requests in <1ms.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

DERIVATIVES_SAFETY_REFUSAL = (
    "Finova AI is an educational platform and cannot provide options trading tips, strike "
    "recommendations, expiry calls, or speculative derivative strategies. Trading in equity "
    "derivatives involves significant financial risk; according to SEBI, over 90% of individual "
    "F&O traders lose money. I can, however, provide educational explanations of how options work, "
    "the mathematics of call/put payoffs, option Greeks (Delta, Theta, Vega), or SEBI regulatory frameworks."
)


@dataclass(frozen=True)
class DerivativesSafetyResult:
    """Outcome of derivatives safety guardrail evaluation."""
    is_safe: bool
    refusal_reason: str | None = None
    refusal_message: str | None = None


class DerivativesSafetyGuardrail:
    """Evaluates whether a query requests actionable derivatives trading tips."""

    ADVISORY_PATTERNS = [
        re.compile(
            r"\b(?:which|what)\s+(?:(?:call|put|strike)\s+)?(?:call|put|option|strike|contract)s?\s+"
            r"(?:should|shall|can|must|to)\s+(?:i|we)\s+(?:buy|sell|trade|pick|enter)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\bshould\s+(?:i|we)\s+(?:buy|sell|trade|hold)\s+(?:a\s+)?(?:[a-z0-9&]+\s+){0,3}(?:call|put|ce|pe|option|future|futures|options)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(?:give\s+me|suggest|recommend|need|provide)\s+.*?\b"
            r"(?:option\s+tips?|options?\s+(?:buying\s+|selling\s+)?calls?|f&o\s+calls?|expiry\s+calls?|hero\s*(?:or|\/)?\s*zero|intraday\s+options?|jackpot\s+calls?|[a-z0-9&]+\s+(?:call|put|ce|pe))\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\bhero\s*(?:or|\/)?\s*zero\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(?:best|top)\s+(?:(?:call|put|option|strike|contract|straddle)\s+){1,2}to\s+(?:buy|sell|trade|pick)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(?:tell\s+me\s+)?which\s+strike\s+(?:is\s+best|should\s+i\s+buy|to\s+trade)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(?:buy|sell)\s+(?:ce|pe|call|put)\s+for\s+[a-zA-Z0-9&]+\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\bhow\s+to\s+(?:double|triple|10x)\s+money\s+(?:in|with)\s+(?:options|f&o|futures)\b",
            re.IGNORECASE,
        ),
    ]

    CONCEPTUAL_PATTERNS = [
        re.compile(r"^(?:what|how|why|explain|define|describe)\s+(?:is|are|does|do|mean)\s+(?:a\s+)?(?:call|put|option|strike|premium|moneyness|delta|gamma|theta|vega|rho|futures?|hedging)\b", re.IGNORECASE),
        re.compile(r"\b(?:difference\s+between|concept\s+of|mechanism\s+of|meaning\s+of|payoff\s+(?:of|for)|breakeven\s+(?:of|for))\b", re.IGNORECASE),
        re.compile(r"\bwhy\s+do\s+(?:9|nine|\d+)\s+(?:out\s+of\s+10\s+)?traders\s+lose\b", re.IGNORECASE),
        re.compile(r"\bhow\s+does\s+(?:delta|theta|gamma|vega|time\s+decay|strike\s+price)\s+work\b", re.IGNORECASE),
        re.compile(r"\b(?:calculate|what\s+is\s+the)\s+(?:payoff|pnl|profit|breakeven)\b", re.IGNORECASE),
    ]

    def evaluate(self, query: str) -> DerivativesSafetyResult:
        cleaned = query.strip()
        if not cleaned:
            return DerivativesSafetyResult(is_safe=True)

        for pattern in self.ADVISORY_PATTERNS:
            if pattern.search(cleaned):
                # Check for explicit conceptual override
                if self._is_conceptual_exception(cleaned):
                    continue
                return DerivativesSafetyResult(
                    is_safe=False,
                    refusal_reason="derivatives_advisory_intent",
                    refusal_message=DERIVATIVES_SAFETY_REFUSAL,
                )

        return DerivativesSafetyResult(is_safe=True)

    def _is_conceptual_exception(self, query: str) -> bool:
        # If user explicitly asks for advice/tips, it is not an exception
        if re.search(r"\b(?:which|what)\s+(?:(?:call|put|strike)\s+)?(?:strike|call|put|option)\s+should\s+i\s+(?:buy|sell|trade)\b", query, re.IGNORECASE):
            return False
        if re.search(r"\b(?:give\s+me|suggest|recommend)\s+.*(?:tips?|calls?|picks?)\b", query, re.IGNORECASE):
            return False
        return any(cp.search(query) for cp in self.CONCEPTUAL_PATTERNS)


derivatives_safety_guardrail = DerivativesSafetyGuardrail()
