"""
Deterministic safety guardrail for the Market News Agent.
Pre-filters queries to block trade recommendations based on news,
unverified rumor inquiries, and insider trading tips.
"""

from __future__ import annotations

from dataclasses import dataclass
import re

NEWS_SAFETY_REFUSAL = (
    "Finova AI provides factual news summaries and regulatory announcements for educational "
    "awareness only. We do not provide trading recommendations based on news events, speculate on "
    "unverified rumors, or provide price target predictions. For personalized financial advice, "
    "consult a SEBI-registered Investment Adviser."
)


@dataclass(frozen=True)
class NewsSafetyResult:
    """Outcome of news safety evaluation."""
    is_safe: bool
    refusal_reason: str | None = None
    refusal_message: str | None = None


class NewsSafetyGuardrail:
    """Evaluates whether a news query is safe and strictly educational."""

    UNSAFE_PATTERNS = [
        re.compile(
            r"\b(?:what|which)\s+(?:stocks?|shares?)\s+(?:should\s+i|to)\s+(?:buy|sell)\s+(?:based\s+on|after)\s+(?:the\s+)?news\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(?:hot\s+news\s+stocks?|news\s+based\s+tips?|trade\s+tomorrow'?s?\s+news)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(?:insider\s+trading\s+tips?|insider\s+leak|unverified\s+rumor|is\s+the\s+rumor\s+true)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\bwill\s+[a-zA-Z0-9&]+\s+(?:double|crash|skyrocket|hit\s+\d+)\s+after\s+(?:this|the)\s+news\b",
            re.IGNORECASE,
        ),
    ]

    CONCEPTUAL_DEFINITIONS = [
        re.compile(r"^(?:what\s+is|define|explain|meaning\s+of)\s+(?:insider\s+trading|market\s+news|corporate\s+announcements?|buybacks?)\b", re.IGNORECASE),
    ]

    def evaluate(self, query: str) -> NewsSafetyResult:
        # 1. Universal Secondary Safety & Input Sanitization
        try:
            from app.safety.validator import GLOBAL_REFUSAL_MESSAGE, secondary_safety_validator
            sec_res = secondary_safety_validator.validate(query)
            if not sec_res.is_safe:
                return NewsSafetyResult(
                    is_safe=False,
                    refusal_reason=sec_res.violation_type or "secondary_safety_violation",
                    refusal_message=sec_res.refusal_message or GLOBAL_REFUSAL_MESSAGE,
                )
            cleaned = sec_res.sanitized_text
        except Exception as exc:
            import logging
            logging.getLogger(__name__).critical("Universal safety validation failed in NewsSafetyGuardrail: %s", exc, exc_info=True)
            return NewsSafetyResult(
                is_safe=False,
                refusal_reason="validator_internal_fault",
                refusal_message=GLOBAL_REFUSAL_MESSAGE,
            )

        for pattern in self.UNSAFE_PATTERNS:
            if pattern.search(cleaned):
                if any(cp.search(cleaned) for cp in self.CONCEPTUAL_DEFINITIONS):
                    continue
                return NewsSafetyResult(
                    is_safe=False,
                    refusal_reason="news_speculation_or_tips",
                    refusal_message=NEWS_SAFETY_REFUSAL,
                )

        return NewsSafetyResult(is_safe=True)


news_safety_guardrail = NewsSafetyGuardrail()
