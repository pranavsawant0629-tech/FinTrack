"""
Unified Global Safety & Advisory Guardrail for Finova AI.

Enforces financial safety across all supported domains:
1. Equity: Blocks stock tips, buy/sell directives, and price targets.
2. Crypto: Blocks speculative coin recommendations, 10x promises, and price predictions.
3. Personal Finance: Blocks personalized asset allocation advice and guaranteed return claims.

Operates as a single global pre-filter before query routing, agent dispatch,
or LLM generation. Distinguishes between dangerous advisory intent and legitimate
conceptual/educational questions.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.router.models import Domain

GLOBAL_REFUSAL_MESSAGE = (
    "Finova AI is an educational platform and cannot provide personalized financial advice, "
    "buy/sell recommendations, portfolio allocation calls, or speculative price targets. "
    "Under financial regulations, guaranteed returns do not exist, and all securities and digital assets "
    "carry market risk. I can, however, provide educational explanations of market mechanisms, "
    "valuation metrics, budgeting frameworks, or fundamental concepts."
)


@dataclass(frozen=True)
class GlobalSafetyResult:
    """Outcome of global safety guardrail evaluation."""
    is_safe: bool
    refusal_reason: str | None = None
    refusal_message: str | None = None
    domain: Domain | None = None


class EquitySafetyRules:
    """Deterministic patterns detecting unsafe equity advice and stock tips."""

    BUY_SELL_PATTERNS = [
        re.compile(
            r"\b(?:which|what)\s+(?:stock|share|company|equity|script)s?\s+"
            r"(?:should|shall|can|must|to)\s+(?:i|we)\s+(?:buy|sell|invest\s+in|pick|purchase|trade)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\bshould\s+(?:i|we)\s+(?:buy|sell|invest\s+in|hold|trade)\s+"
            r"(?!shares?\b|stocks?\b|equities\b|mutual\s+funds?\b|my\s+(?:mutual\s+funds?|portfolio|shares?|stocks?|units?|holdings?)\b|units?\b|etfs?\b|securities\b)"
            r"([A-Za-z0-9&]+(?:\s+(?:shares?|stocks?|ltd|limited))?)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(?:tell\s+me|give\s+me|suggest|recommend|advise\s+me\s+on)\s+"
            r"(?:what|which|a)?\s*(?:stock|share|call|equity|script)s?\s+to\s+(?:buy|sell|invest\s+in|trade)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(?:give\s+me|suggest|recommend|need|provide)\s+(?:some\s+)?"
            r"(?:stock\s+tips?|intraday\s+calls?|hot\s+stocks?|multibagger\s+picks?|best\s+stocks?\s+to\s+buy)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(?:best|top)\s+(?:stocks?|shares?)\s+to\s+(?:buy|invest\s+in)\s+"
            r"(?:today|now|tomorrow|this\s+week|this\s+month|for\s+(?:quick|fast)\s+(?:profit|gains?))\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(?:buy|sell)\s+call\s+for\s+[a-zA-Z0-9&]+\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(?:buy|sell|dump|liquidate)\s+(?:all\s+)?my\s+[a-zA-Z0-9&]+\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\bput\s+(?:all\s+|everything\s+)?(?:in|into)\s+(?:bitcoin|btc|crypto|stocks?|shares?|[a-zA-Z0-9&]+)\b",
            re.IGNORECASE,
        ),
    ]

    CONCEPTUAL_PATTERNS = [
        re.compile(
            r"^(?:what|how|why|explain|define|describe)\s+"
            r"(?:is|are|does|do|happens|mean|can\s+an\s+investor)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(?:difference\s+between|process\s+of|mechanism\s+of|factors\s+(?:to|that|investors)|"
            r"concept\s+of|meaning\s+of|how\s+does\s+(?:a\s+)?(?:stock\s+exchange|order|settlement|trade))\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\bdeciding\s+whether\s+to\s+(?:buy|sell)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\bwhen\s+(?:an?\s+)?(?:investor|one|i)\s+buys?\s+(?:a\s+)?(?:share|stock)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(?:dividend\s+)?record\s+date\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(?:market\s+)?(?:dip|crash|correction|volatility|downturn)\b",
            re.IGNORECASE,
        ),
    ]

    @classmethod
    def is_unsafe(cls, text: str) -> bool:
        for pattern in cls.BUY_SELL_PATTERNS:
            if pattern.search(text):
                # Check for explicit conceptual exception
                if cls._is_conceptual_exception(text):
                    continue
                return True
        return False

    @classmethod
    def _is_conceptual_exception(cls, query: str) -> bool:
        if re.search(r"\b(?:which|what)\s+(?:stock|share|company)s?\s+(?:should|shall|can|must)\s+i\b", query, re.IGNORECASE):
            return False
        if re.search(r"\b(?:tell|suggest|recommend)\s+.*to\s+(?:buy|sell)\b", query, re.IGNORECASE):
            return False
        specific_stock_match = re.search(
            r"\bshould\s+(?:i|we)\s+(?:buy|sell|invest\s+in|hold|trade)\s+"
            r"(?!shares?\b|stocks?\b|equities\b|mutual\s+funds?\b|my\s+(?:mutual\s+funds?|portfolio|shares?|stocks?|units?|holdings?)\b|units?\b|etfs?\b|securities\b)"
            r"([A-Za-z0-9&]+)",
            query,
            re.IGNORECASE,
        )
        if specific_stock_match:
            return False
        for pattern in cls.CONCEPTUAL_PATTERNS:
            if pattern.search(query):
                return True
        return False


class CryptoSafetyRules:
    """Deterministic patterns detecting unsafe crypto advice, speculation, and 10x promises."""

    CRYPTO_ADVISORY_PATTERNS = [
        re.compile(
            r"\bshould\s+(?:i|we)\s+(?:buy|sell|invest\s+in|hold|trade)\s+(?:bitcoin|btc|ethereum|eth|crypto|solana|sol|doge|altcoins?)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(?:which|what)\s+(?:meme\s+)?(?:crypto|coin|token|altcoin)s?\s+(?:should|shall|can|must|to)?\s*(?:i|we)?\s*(?:to\s+)?(?:buy|invest\s+in|trade|pick)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(?:(?:give\s+me|suggest|recommend|need|provide)\s+)?(?:a\s+)?(?:target\s+price|price\s+prediction|price\s+target)\s+(?:for|of)\s+(?:bitcoin|btc|ethereum|eth|crypto|[a-z0-9]+)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(?:which|what)\s+(?:meme\s+)?(?:crypto|coin|token)\s+will\s+(?:10x|100x|moon|explode|pump)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(?:buy|invest\s+in|pick)\s+.*(?:for\s+)?(?:10x|100x)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(?:best|top)\s+(?:crypto|coins?|tokens?|altcoins?)\s+to\s+(?:buy|invest\s+in)\s+(?:today|now|2026|this\s+year)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\bhow\s+to\s+get\s+rich\s+(?:with|from|in)\s+crypto\b",
            re.IGNORECASE,
        ),
    ]

    CONCEPTUAL_CRYPTO_PATTERNS = [
        re.compile(r"^(?:what|how|why|explain|define|describe)\s+(?:is|are|does|do)\s+(?:bitcoin|ethereum|crypto|blockchain|defi|tokenomics|web3|smart\s+contracts?)\b", re.IGNORECASE),
        re.compile(r"\bwhy\s+is\s+crypto\s+(?:so\s+)?volatile\b", re.IGNORECASE),
        re.compile(r"\bhow\s+does\s+(?:a\s+)?(?:blockchain|crypto\s+wallet|proof\s+of\s+work|proof\s+of\s+stake)\s+work\b", re.IGNORECASE),
    ]

    @classmethod
    def is_unsafe(cls, text: str) -> bool:
        for pattern in cls.CRYPTO_ADVISORY_PATTERNS:
            if pattern.search(text):
                # Check for explicit conceptual exception
                for cp in cls.CONCEPTUAL_CRYPTO_PATTERNS:
                    if cp.search(text):
                        return False
                return True
        return False


class PersonalFinanceSafetyRules:
    """Deterministic patterns detecting personalized asset allocation advice and guaranteed financial promises."""

    PF_ADVISORY_PATTERNS = [
        re.compile(
            r"\b(?:where|how)\s+(?:should|to)\s+(?:i\s+)?(?:invest|put|allocate)\s+(?:my\s+)?(?:money|savings|bonus|portfolio|\u20b9?\d+[\d,]*)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(?:tell\s+me\s+)?(?:how\s+to\s+)?allocate\s+(?:my\s+)?(?:exact\s+)?(?:\u20b9?\d+[\d,]*\s*)?(?:lakh|crore|k)?\s*portfolio\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(?:tell\s+me\s+)?which\s+(?:stocks?|shares?|funds?|mutual\s+funds?)\s+to\s+(?:put|invest)\s+.*(?:savings|money)\s+into\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\bshould\s+i\s+invest\s+(?:\u20b9?\d+[\d,]*\s+)?in\s+[a-zA-Z0-9\s&]+\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\btell\s+me\s+which\s+(?:mutual\s+fund|scheme|policy)\s+to\s+(?:buy|invest\s+in)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\bcan\s+you\s+manage\s+my\s+(?:money|finances|portfolio|salary)\b",
            re.IGNORECASE,
        ),
    ]

    CONCEPTUAL_PF_PATTERNS = [
        re.compile(r"^(?:what|how|explain|define)\s+(?:is|does|are)\s+(?:the\s+)?(?:50/30/20|budgeting|emergency\s+fund|credit\s+score|compound\s+interest|sip)\b", re.IGNORECASE),
        re.compile(r"\bhow\s+does\s+(?:the\s+)?50/30/20\s+rule\s+work\b", re.IGNORECASE),
        re.compile(r"\bif\s+(?:my\s+)?(?:monthly\s+)?income\s+is\s+.*how\s+does\s+50/30/20\s+split\b", re.IGNORECASE),
    ]

    @classmethod
    def is_unsafe(cls, text: str) -> bool:
        for pattern in cls.PF_ADVISORY_PATTERNS:
            if pattern.search(text):
                for cp in cls.CONCEPTUAL_PF_PATTERNS:
                    if cp.search(text):
                        return False
                return True
        return False


class GuaranteedReturnsRules:
    """Cross-domain patterns detecting promises of risk-free gains or guaranteed wealth."""

    PATTERNS = [
        re.compile(
            r"\b(?:guarantee(?:d|ing)?|promise|promising|assure)\s+(?:(?:an?|any|me|\d+%?)\s+)*(?:returns?|profit|gain|money)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(?:guarantee(?:d)?|risk-?free|100%|sure-?shot|zero-?risk)\s+(?:(?:an?|any|the|way\s+to\s+(?:make|get)\s+)?)*(?:returns?|profit|gain|money|wealth)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(?:(?:double|triple)\s+my\s+money|which\s+(?:stock|share|crypto|coin)s?\s+will\s+(?:double|triple)|stock\s+will\s+double)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b\d+%\s+(?:guaranteed?|sure|risk-?free|fixed)\s*(?:returns?|profit|gain)?\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\bhow\s+to\s+(?:make|get)\s+(?:quick|fast|easy)\s+money\b",
            re.IGNORECASE,
        ),
    ]

    @classmethod
    def is_unsafe(cls, text: str) -> bool:
        return any(p.search(text) for p in cls.PATTERNS)


class GlobalSafetyGuardrail:
    """Unified safety layer evaluating all queries before routing or tool execution."""

    def evaluate(self, query: str) -> GlobalSafetyResult:
        cleaned = query.strip()
        if not cleaned:
            return GlobalSafetyResult(is_safe=True)

        detected_domain: Domain = "GENERAL"
        lower_query = cleaned.lower()
        if any(w in lower_query for w in ["stock", "share", "equity", "nifty", "sensex", "reliance", "tcs"]):
            detected_domain = "EQUITY"
        elif any(w in lower_query for w in ["crypto", "coin", "token", "bitcoin", "btc", "ethereum", "eth", "altcoin"]):
            detected_domain = "CRYPTO"
        elif any(w in lower_query for w in ["portfolio", "savings", "budget", "salary", "expense", "emergency fund"]):
            detected_domain = "PERSONAL_FINANCE"

        # 1. Unconditionally check for guaranteed returns / get-rich-quick claims
        if GuaranteedReturnsRules.is_unsafe(cleaned):
            return GlobalSafetyResult(
                is_safe=False,
                refusal_reason="guaranteed_returns_inquiry",
                refusal_message=GLOBAL_REFUSAL_MESSAGE,
                domain=detected_domain,
            )

        # 2. Check Crypto advisory intent
        if CryptoSafetyRules.is_unsafe(cleaned):
            return GlobalSafetyResult(
                is_safe=False,
                refusal_reason="crypto_advisory_intent",
                refusal_message=GLOBAL_REFUSAL_MESSAGE,
                domain="CRYPTO",
            )

        # 3. Check Equity advisory intent
        if EquitySafetyRules.is_unsafe(cleaned):
            return GlobalSafetyResult(
                is_safe=False,
                refusal_reason="equity_advisory_intent",
                refusal_message=GLOBAL_REFUSAL_MESSAGE,
                domain="EQUITY",
            )

        # 4. Check Personal Finance advisory intent
        if PersonalFinanceSafetyRules.is_unsafe(cleaned):
            return GlobalSafetyResult(
                is_safe=False,
                refusal_reason="personal_finance_advisory_intent",
                refusal_message=GLOBAL_REFUSAL_MESSAGE,
                domain="PERSONAL_FINANCE",
            )

        # 5. Check Derivatives advisory / option tip intent
        from app.agents.derivatives.safety import derivatives_safety_guardrail
        deriv_res = derivatives_safety_guardrail.evaluate(cleaned)
        if not deriv_res.is_safe:
            return GlobalSafetyResult(
                is_safe=False,
                refusal_reason=deriv_res.refusal_reason or "derivatives_advisory_intent",
                refusal_message=deriv_res.refusal_message or GLOBAL_REFUSAL_MESSAGE,
                domain="DERIVATIVES",
            )

        # 6. Check Portfolio rebalancing / directive intent
        from app.agents.portfolio.safety import portfolio_safety_guardrail
        port_res = portfolio_safety_guardrail.evaluate(cleaned)
        if not port_res.is_safe:
            return GlobalSafetyResult(
                is_safe=False,
                refusal_reason=port_res.refusal_reason or "portfolio_advisory_intent",
                refusal_message=port_res.refusal_message or GLOBAL_REFUSAL_MESSAGE,
                domain="PORTFOLIO",
            )

        # 7. Check News trading tips / rumor intent
        from app.agents.news.safety import news_safety_guardrail
        news_res = news_safety_guardrail.evaluate(cleaned)
        if not news_res.is_safe:
            return GlobalSafetyResult(
                is_safe=False,
                refusal_reason=news_res.refusal_reason or "news_advisory_intent",
                refusal_message=news_res.refusal_message or GLOBAL_REFUSAL_MESSAGE,
                domain="NEWS",
            )

        # 8. Check Secondary Safety Validator (Stage 7B: Adversarial & Prompt Injection)
        from app.safety.validator import secondary_safety_validator
        sec_res = secondary_safety_validator.validate(cleaned)
        if not sec_res.is_safe:
            return GlobalSafetyResult(
                is_safe=False,
                refusal_reason=sec_res.violation_type or "secondary_safety_violation",
                refusal_message=sec_res.refusal_message or GLOBAL_REFUSAL_MESSAGE,
                domain=None,
            )

        return GlobalSafetyResult(is_safe=True)


global_safety_guardrail = GlobalSafetyGuardrail()
