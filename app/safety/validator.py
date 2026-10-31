"""
Secondary Deterministic Safety & Adversarial Injection Validator for Finova AI (Phase 7).

Provides secondary structural, regex, and pattern-based safety validation:
1. Catches advanced advisory bypasses: roleplay RIA, fictional framing, guaranteed returns, 100x moonshots.
2. Detects direct and indirect prompt injection, system prompt overrides, delimiter collisions, and jailbreak modes.
3. Completely deterministic: Zero LLM calls, zero embeddings, zero network access, sub-millisecond execution.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import ClassVar

logger = logging.getLogger(__name__)

GLOBAL_REFUSAL_MESSAGE = (
    "Finova AI is an educational platform and cannot provide personalized financial advice, "
    "buy/sell recommendations, portfolio allocation calls, or speculative price targets. "
    "Under financial regulations, guaranteed returns do not exist, and all securities and digital assets "
    "carry market risk. I can, however, provide educational explanations of market mechanisms, "
    "valuation metrics, budgeting frameworks, or fundamental concepts."
)

INJECTION_REFUSAL_MESSAGE = (
    "Finova AI detected instructions attempting to alter system behavior, override safety guardrails, "
    "or manipulate prompt context. As a secure educational system, these instructions are rejected. "
    "How can I assist you with financial education or market concepts today?"
)


@dataclass(frozen=True)
class SafetyValidationResult:
    """Outcome of secondary deterministic safety & prompt injection validation."""
    is_safe: bool
    is_injection: bool = False
    violation_type: str | None = None
    refusal_message: str | None = None
    sanitized_text: str = ""


class SecondarySafetyValidator:
    """Deterministic structural and regex validator for financial advisory bypasses and prompt injections."""

    # 1. Advanced Advisory Bypasses & Guaranteed Returns Patterns
    ROLEPLAY_ADVISORY_PATTERNS: ClassVar[list[re.Pattern[str]]] = [
        re.compile(
            r"\b(?:pretend|act\s+as|roleplay|simulate|imagine)\s+(?:you\s+are|being)?\s*(?:a|an)?\s*"
            r"(?:sebi\s+(?:registered\s+)?(?:investment\s+advis[oe]r|ria|advisor)?|sebi\s+registered|investment\s+advis[oe]r|financial\s+plann?er|portfolio\s+manag(?:er|ement)|broker|trader|ria)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(?:in\s+a\s+fictional|hypothetical(?:ly)?|thought\s+experiment|for\s+educational\s+purposes\s+only)\s*,?\s*"
            r"(?:(?:which|what|tell\s+me)\s+(?:stock|share|crypto|coin|option)?\s*(?:to|should\s+i)?\s*(?:buy|sell|trade|invest\s+in)|should\s+i\s+(?:buy|sell|trade|invest\s+in))\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(?:tell\s+me\s+how\s+to|how\s+should\s+i)\s+allocate\s+(?:my\s+exact|my)\s+(?:\d+|all)\s*(?:lakh|cr|crore|thousand|inr|rs)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(?:buy|sell|dump|liquidate)\s+(?:all\s+)?my\s+[A-Za-z0-9&]+\b",
            re.IGNORECASE,
        ),
    ]

    GUARANTEED_RETURN_PATTERNS: ClassVar[list[re.Pattern[str]]] = [
        re.compile(
            r"\b(?:100%|guarantee[ds]?|risk[- ]free|sure[- ]shot|riskless|zero[- ]risk|assured)\s+"
            r"(?:(?:100%|guarantee[ds]?|risk[- ]free|sure[- ]shot|riskless|zero[- ]risk|assured)\s+)*"
            r"(?:returns?|profits?|investments?|gains?|money|calls?|stocks?|trades?|yields?)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(?:investment|stock|fund|option)\s+that\s+guarantees?\s+\d+%\s*returns?\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(?:double\s+my\s+money\s+in\s+\d+\s*(?:days?|weeks?|months?)\s*(?:without\s+any?\s+risk|guaranteed)?|which\s+(?:stock|share|crypto|coin)s?\s+will\s+(?:double|triple)|stock\s+will\s+double)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\bsure\s+shot\s+option\s+calls?\s+for\s+tomorrow\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\bwhich\s+(?:crypto|coin|token|crypto\s+coin)\s+(?:will|to|should\s+i)?\s*\d+x\b",
            re.IGNORECASE,
        ),
    ]

    # Direct Unsafe Financial Advisory & Stock Tips Patterns
    DIRECT_ADVISORY_PATTERNS: ClassVar[list[re.Pattern[str]]] = [
        re.compile(
            r"\b(?:which|what)\s+(?:stock|share|company|equity|script|option|call|put|ce|pe|crypto|coin|token)s?\s+"
            r"(?:should|shall|can|must|to)?\s*(?:i|we)?\s*(?:to\s+)?(?:buy|sell|invest\s+in|pick|purchase|trade)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\bshould\s+(?:i|we)\s+(?:buy|sell|invest\s+in|hold|trade)\s+"
            r"(?:ce\s+or\s+pe|pe\s+or\s+ce|calls?\s+or\s+puts?|puts?\s+or\s+calls?|[a-zA-Z0-9&]+)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(?:tell\s+me|give\s+me|suggest|recommend|advise\s+me\s+on)\s+"
            r"(?:what|which|a)?\s*(?:stock|share|call|put|option|ce|pe|crypto|coin|equity|script)s?\s+to\s+(?:buy|sell|invest\s+in|trade)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(?:give\s+me|suggest|recommend|need|provide)\s+(?:some\s+)?"
            r"(?:(?:intraday|stock|equity|hot|multibagger)\s+)*(?:tips?|calls?|picks?|stocks?\s+to\s+buy)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(?:best|top)\s+(?:stocks?|shares?|cryptos?|coins?|options?)\s+to\s+(?:buy|invest\s+in)\s+"
            r"(?:today|now|tomorrow|this\s+week|this\s+month|for\s+(?:quick|fast)\s+(?:profit|gains?))\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(?:where|how)\s+(?:should|to)\s+(?:i\s+)?(?:invest|put|allocate)\s+(?:my\s+)?(?:money|savings|bonus|portfolio|\u20b9?\d+[\d,]*)\b",
            re.IGNORECASE,
        ),
    ]

    # 2. Direct & Indirect Prompt Injection Patterns
    PROMPT_INJECTION_PATTERNS: ClassVar[list[re.Pattern[str]]] = [
        re.compile(
            r"\b(?:ignore|disregard|forget|override|bypass|cancel)\s+(?:all\s+)?(?:(?:previous|prior|above|existing|system|safety)\s+)*(?:instructions?|directives?|rules?|prompts?|constraints?|guidelines?)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(?:system\s+override|admin\s+override)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"---+\s*(?:START|END)?\s*(?:SYSTEM\s+)?(?:SYSTEM|PROMPT|INSTRUCTIONS?|CONTEXT)\s*---+",
            re.IGNORECASE,
        ),
        re.compile(
            r"(?:<<SYS>>|<\|im_start\|>|<\|system\|>|\[SYSTEM\]|\[INST\]|\[INJECTION)",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(?:now\s+you\s+are\s+in\s+(?:developer|debug)(?:\s+debug)?\s+mode|enable\s+dan\s+mode|jailbreak\s+mode|unrestricted\s+mode)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(?:output|print|reveal|display|leak)\s+(?:your|the)\s+(?:system\s+prompt|initial\s+instructions?|hidden\s+prompt(?:\s+instructions?)?)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r";\s*(?:DROP\s+TABLE|DELETE\s+FROM|UPDATE\s+\w+\s+SET|INSERT\s+INTO)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"<!--\s*\[?(?:SYSTEM(?:\s+INSTRUCTION)?|INSTRUCTION|OVERRIDE|INJECTION):?.*-->",
            re.IGNORECASE,
        ),
    ]

    @classmethod
    def validate(cls, text: str) -> SafetyValidationResult:
        """
        Validate text against financial safety bypasses and prompt injection attacks.
        Fails closed on any unexpected exception or malformed input.
        """
        try:
            if text is None or not isinstance(text, str):
                logger.warning("SecondarySafetyValidator received non-string input: %s", type(text))
                return SafetyValidationResult(
                    is_safe=False,
                    is_injection=False,
                    violation_type="malformed_input",
                    refusal_message=GLOBAL_REFUSAL_MESSAGE,
                    sanitized_text="",
                )

            # Sanitize null bytes and bounding string to prevent ReDoS / memory exhaustion
            cleaned = text.replace("\x00", "").strip()
            if len(cleaned) > 50000:
                cleaned = cleaned[:50000]

            if not cleaned:
                return SafetyValidationResult(is_safe=True, sanitized_text=cleaned)

            # 1. Check for prompt injection attacks
            for pattern in cls.PROMPT_INJECTION_PATTERNS:
                if pattern.search(cleaned):
                    return SafetyValidationResult(
                        is_safe=False,
                        is_injection=True,
                        violation_type="prompt_injection",
                        refusal_message=INJECTION_REFUSAL_MESSAGE,
                        sanitized_text=cleaned,
                    )

            # 2. Check for roleplay or hypothetical advisory bypasses
            for pattern in cls.ROLEPLAY_ADVISORY_PATTERNS:
                if pattern.search(cleaned):
                    return SafetyValidationResult(
                        is_safe=False,
                        is_injection=False,
                        violation_type="advisory_bypass",
                        refusal_message=GLOBAL_REFUSAL_MESSAGE,
                        sanitized_text=cleaned,
                    )

            # 3. Check for guaranteed returns & moonshot speculation promises
            for pattern in cls.GUARANTEED_RETURN_PATTERNS:
                if pattern.search(cleaned):
                    return SafetyValidationResult(
                        is_safe=False,
                        is_injection=False,
                        violation_type="guaranteed_returns",
                        refusal_message=GLOBAL_REFUSAL_MESSAGE,
                        sanitized_text=cleaned,
                    )

            # 4. Check for direct financial advisory & stock tips
            for pattern in cls.DIRECT_ADVISORY_PATTERNS:
                if pattern.search(cleaned):
                    return SafetyValidationResult(
                        is_safe=False,
                        is_injection=False,
                        violation_type="advisory",
                        refusal_message=GLOBAL_REFUSAL_MESSAGE,
                        sanitized_text=cleaned,
                    )

            return SafetyValidationResult(is_safe=True, sanitized_text=cleaned)

        except Exception as exc:
            logger.critical("SecondarySafetyValidator failed unexpectedly: %s", exc, exc_info=True)
            return SafetyValidationResult(
                is_safe=False,
                is_injection=False,
                violation_type="validator_internal_fault",
                refusal_message=GLOBAL_REFUSAL_MESSAGE,
                sanitized_text="",
            )


secondary_safety_validator = SecondarySafetyValidator()
