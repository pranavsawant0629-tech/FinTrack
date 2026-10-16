"""
Deterministic Safety & Advisory Guardrail for the Equity Agent.

Enforces strict SEBI regulatory compliance by blocking personalized investment advice,
buy/sell recommendations, stock tips, and guaranteed return inquiries BEFORE invoking
retrieval or LLM generation. Distinguishes between dangerous advisory intent and legitimate
conceptual or educational queries about securities markets.

================================================================================
KNOWN LIMITATIONS (Phase 2 v1 Architectural Tradeoff):
================================================================================
The regex-based safety filter is deterministic, high-throughput, and auditable, but as
a pattern-matching pre-filter it may fail to detect:
1. Rephrased advice requests (e.g. "I have ₹50,000, where should it go?")
2. Indirect or contextual advice requests (e.g. "Which firm has better dividend growth?")
3. Multilingual or non-English advice requests (e.g. Hindi, Hinglish phrasing)

This is an accepted Phase 2 v1 architectural tradeoff. Advanced semantic safety
classification, LLM-based safety judges, and multi-turn intent tracking are deferred
to Phase 7 (Safety Hardening & Production Polish).
================================================================================
"""

import re
from dataclasses import dataclass

SAFETY_REFUSAL_MESSAGE = (
    "Finova AI is an educational platform and cannot provide personalized stock recommendations, "
    "buy/sell calls, or financial advice. Under SEBI regulations, guaranteed returns do not exist in "
    "securities markets, and all equity investments carry market risk. I can, however, explain how equity "
    "markets operate, how fundamental valuation metrics (such as P/E ratio, debt-to-equity, and cash flows) "
    "are analyzed, or how orders are executed on stock exchanges."
)


@dataclass(frozen=True)
class SafetyCheckResult:
    """Outcome of safety guardrail evaluation."""
    is_safe: bool
    refusal_reason: str | None = None
    refusal_message: str | None = None


class EquitySafetyGuardrail:
    """
    Deterministic regex-based guardrail for the Equity Agent.
    Evaluates queries for advisory intent, stock tips, and guaranteed return claims.
    """

    # Unsafe Patterns: Direct personalized buy/sell directives on specific companies/tickers
    _PERSONALIZED_BUY_SELL_PATTERNS = [
        re.compile(
            r"\b(?:which|what)\s+(?:stock|share|company|equity|script)s?\s+"
            r"(?:should|shall|can|must|to)\s+(?:i|we)\s+(?:buy|sell|invest\s+in|pick|purchase|trade)\b",
            re.IGNORECASE,
        ),
        # Matches 'should I buy/sell/hold <ticker/stock>' while excluding generic asset/instrument classes
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
    ]

    # Unsafe Patterns: Guaranteed returns and unrealistic wealth generation
    _GUARANTEED_RETURNS_PATTERNS = [
        re.compile(
            r"\b(?:guarantee(?:d|ing)?|promise|promising|assure)\s+(?:(?:an?|any|me|\d+%?)\s+)*(?:returns?|profit|gain|money)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(?:guarantee(?:d)?|risk-?free|100%|sure-?shot|zero-?risk)\s+(?:returns?|profit|gain|money)\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(?:double|triple)\s+my\s+money\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b\d+%\s+(?:guaranteed?|sure|risk-?free|fixed)\s*(?:returns?|profit|gain)?\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\bhow\s+to\s+(?:make|get)\s+(?:quick|fast|easy)\s+money\s+"
            r"(?:in|from)\s+(?:stocks?|trading|shares?|equity)\b",
            re.IGNORECASE,
        ),
    ]

    # Conceptual Framing Patterns: Distinguishes educational questions from advice
    _CONCEPTUAL_FRAMING_PATTERNS = [
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
        re.compile(
            r"\bex-dividend\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\bbook\s+closure\b",
            re.IGNORECASE,
        ),
        re.compile(
            r"\bsettlement\s+cycle\b",
            re.IGNORECASE,
        ),
    ]

    def evaluate(self, query: str) -> SafetyCheckResult:
        """
        Evaluate a user query for safety and regulatory compliance.

        Returns:
            SafetyCheckResult indicating whether the query is safe to process.
        """
        cleaned_query = query.strip()
        if not cleaned_query:
            return SafetyCheckResult(is_safe=True)

        # 1. Check for guaranteed returns / get-rich-quick (unconditionally unsafe)
        for pattern in self._GUARANTEED_RETURNS_PATTERNS:
            if pattern.search(cleaned_query):
                return SafetyCheckResult(
                    is_safe=False,
                    refusal_reason="guaranteed_returns_inquiry",
                    refusal_message=SAFETY_REFUSAL_MESSAGE,
                )

        # 2. Check personalized buy/sell directives
        for pattern in self._PERSONALIZED_BUY_SELL_PATTERNS:
            if pattern.search(cleaned_query):
                # Check if it's a false positive conceptual query
                if self._is_conceptual_exception(cleaned_query):
                    continue
                return SafetyCheckResult(
                    is_safe=False,
                    refusal_reason="personalized_advisory_intent",
                    refusal_message=SAFETY_REFUSAL_MESSAGE,
                )

        return SafetyCheckResult(is_safe=True)

    def _is_conceptual_exception(self, query: str) -> bool:
        """
        Detects if a query containing 'buy' or 'sell' is strictly conceptual/educational.
        e.g. "What factors do investors study before deciding whether to buy a stock?",
             "should I buy shares before the dividend record date?",
             "should I hold my mutual funds during a market dip?"
        """
        # If it explicitly asks "Which stock should I buy" or "What stock should I buy", NEVER an exception
        if re.search(r"\b(?:which|what)\s+(?:stock|share|company)s?\s+(?:should|shall|can|must)\s+i\b", query, re.IGNORECASE):
            return False

        # If it asks "Tell me what stock to buy", NEVER an exception
        if re.search(r"\b(?:tell|suggest|recommend)\s+.*to\s+(?:buy|sell)\b", query, re.IGNORECASE):
            return False

        # If it explicitly asks "Should I buy/sell/hold <specific company/ticker>", NEVER an exception
        specific_stock_match = re.search(
            r"\bshould\s+(?:i|we)\s+(?:buy|sell|invest\s+in|hold|trade)\s+"
            r"(?!shares?\b|stocks?\b|equities\b|mutual\s+funds?\b|my\s+(?:mutual\s+funds?|portfolio|shares?|stocks?|units?|holdings?)\b|units?\b|etfs?\b|securities\b)"
            r"([A-Za-z0-9&]+)",
            query,
            re.IGNORECASE,
        )
        if specific_stock_match:
            return False

        # Check for conceptual phrasing
        for pattern in self._CONCEPTUAL_FRAMING_PATTERNS:
            if pattern.search(query):
                return True

        return False


equity_safety_guardrail = EquitySafetyGuardrail()
