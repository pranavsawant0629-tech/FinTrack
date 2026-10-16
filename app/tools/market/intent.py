"""Deterministic Fast-Path Intent and Ticker Symbol Classifier.

Detects market data queries (quotes, historical performance, fundamentals,
market status) in sub-millisecond time without LLM calls.
Extracts canonical Indian equity tickers and indices for deterministic fetching.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

IntentType = Literal["quote", "historical", "overview", "market_status", "none"]


@dataclass
class MarketIntentResult:
    """Classification result from MarketIntentClassifier."""
    intent: IntentType
    symbol: str | None = None
    exchange: Literal["NSE", "BSE"] = "NSE"
    confidence: float = 0.0
    is_hybrid: bool = False
    detected_concept: str | None = None


# Prominent Indian equities mapping (Common name / alias -> Canonical Ticker)
EQUITY_ALIASES: dict[str, str] = {
    "RELIANCE": "RELIANCE",
    "RELIANCE INDUSTRIES": "RELIANCE",
    "RIL": "RELIANCE",
    "TCS": "TCS",
    "TATA CONSULTANCY SERVICES": "TCS",
    "INFOSYS": "INFY",
    "INFY": "INFY",
    "HDFC": "HDFCBANK",
    "HDFC BANK": "HDFCBANK",
    "HDFCBANK": "HDFCBANK",
    "ICICI": "ICICIBANK",
    "ICICI BANK": "ICICIBANK",
    "ICICIBANK": "ICICIBANK",
    "SBI": "SBIN",
    "STATE BANK OF INDIA": "SBIN",
    "SBIN": "SBIN",
    "BHARTI AIRTEL": "BHARTIARTL",
    "AIRTEL": "BHARTIARTL",
    "BHARTIARTL": "BHARTIARTL",
    "ITC": "ITC",
    "KOTAK": "KOTAKBANK",
    "KOTAK BANK": "KOTAKBANK",
    "KOTAKBANK": "KOTAKBANK",
    "L&T": "LT",
    "LARSEN": "LT",
    "LT": "LT",
    "TATA MOTORS": "TATAMOTORS",
    "TATAMOTORS": "TATAMOTORS",
    "WIPRO": "WIPRO",
    "HCL TECH": "HCLTECH",
    "HCLTECH": "HCLTECH",
    "ASIAN PAINTS": "ASIANPAINT",
    "ASIANPAINT": "ASIANPAINT",
    "MARUTI": "MARUTI",
    "MARUTI SUZUKI": "MARUTI",
    "SUN PHARMA": "SUNPHARMA",
    "SUNPHARMA": "SUNPHARMA",
    "BAJAJ FINANCE": "BAJFINANCE",
    "BAJFINANCE": "BAJFINANCE",
    "TITAN": "TITAN",
    "AXIS BANK": "AXISBANK",
    "AXISBANK": "AXISBANK",
    "NTPC": "NTPC",
    "ONGC": "ONGC",
    "TATA STEEL": "TATASTEEL",
    "TATASTEEL": "TATASTEEL",
    "NIFTYBEES": "NIFTYBEES",
    "NIFTY BEES": "NIFTYBEES",
}

# Major Indices
INDEX_ALIASES: dict[str, str] = {
    "NIFTY": "NIFTY 50",
    "NIFTY 50": "NIFTY 50",
    "NIFTY50": "NIFTY 50",
    "NIFTY BANK": "BANKNIFTY",
    "BANK NIFTY": "BANKNIFTY",
    "BANKNIFTY": "BANKNIFTY",
    "SENSEX": "SENSEX",
    "BSE SENSEX": "SENSEX",
}

# Regex intent trigger patterns
MARKET_STATUS_PATTERN = re.compile(
    r"\b(market\s+open|market\s+closed|trading\s+hours|holidays?|is\s+nse\s+open|is\s+nse\s+closed|nse\s+closed|is\s+bse\s+open|is\s+bse\s+closed|bse\s+closed|market\s+status|when\s+does\s+market\s+open|next\s+trading\s+session)\b",
    re.IGNORECASE,
)

QUOTE_PATTERN = re.compile(
    r"\b(price|quote|cmp|current\s+price|share\s+price|stock\s+price|trading\s+at|how\s+much\s+is|value\s+of|rate\s+of|today['’]?s\s+price)\b",
    re.IGNORECASE,
)

HISTORICAL_PATTERN = re.compile(
    r"\b(historical|past\s+month|last\s+month|1mo|performance|trend|return|monthly\s+chart|past\s+30\s+days|how\s+did\s+.*perform)\b",
    re.IGNORECASE,
)

OVERVIEW_PATTERN = re.compile(
    r"\b(fundamentals?|market\s+cap|pe\s+ratio|sector|industry|company\s+profile|overview\s+of|about\s+the\s+company|business\s+model|52\s*week\s*high)\b",
    re.IGNORECASE,
)

# Hybrid conceptual query indicator (e.g. "What is an IPO and what is Reliance trading at?")
HYBRID_CONCEPT_PATTERN = re.compile(
    r"\b(?:what\s+is\s+(?:an?\s+)?|what\s+are\s+|explain\s+|define\s+|meaning\s+of\s+|how\s+do(?:es)?\s+)"
    r"(?!(?:the\s+)?(?:current\s+)?(?:price|quote|cmp|stock|share\s+price|market(?:\s+cap)?|trading|performance|return|fundamentals?|pe(?:\s+ratio)?|52))\b"
    r"([a-zA-Z0-9\s]{2,35}?)"
    r"(?:\b\s*(?:and|also|while|with|\?|\.|$))",
    re.IGNORECASE,
)


class MarketIntentClassifier:
    """Fast-path deterministic classifier for live market queries."""

    def _extract_exchange(self, query: str) -> Literal["NSE", "BSE"]:
        """Detect explicit mention of BSE, otherwise default to NSE."""
        upper = query.upper()
        if re.search(r"\b(BSE|BOMBAY\s+STOCK\s+EXCHANGE)\b", upper):
            return "BSE"
        return "NSE"

    def _extract_symbol(self, query: str) -> tuple[str | None, Literal["NSE", "BSE"] | None]:
        """Extract index or equity symbol from user query."""
        upper = query.upper()

        # 1. Check indices first
        for alias, canonical in sorted(INDEX_ALIASES.items(), key=lambda x: -len(x[0])):
            pattern = rf"\b{re.escape(alias)}\b"
            if re.search(pattern, upper):
                exch: Literal["NSE", "BSE"] = "BSE" if canonical == "SENSEX" else "NSE"
                return canonical, exch

        # 2. Check known equity aliases (longest first)
        for alias, canonical in sorted(EQUITY_ALIASES.items(), key=lambda x: -len(x[0])):
            pattern = rf"\b{re.escape(alias)}\b"
            if re.search(pattern, upper):
                return canonical, None

        # 3. Check for general standalone uppercase ticker symbols (2 to 10 letters)
        # e.g., "price of BEL", "quote for ZOMATO"
        words = re.findall(r"\b[A-Z]{2,10}\b", upper)
        common_english_words = {
            "WHAT", "HOW", "WHY", "WHEN", "WHERE", "WHO", "CAN", "YOU", "TELL",
            "GIVE", "SHOW", "FIND", "SHARE", "STOCK", "PRICE", "QUOTE", "TODAY",
            "MARKET", "OPEN", "CLOSE", "HOURS", "DATE", "NSE", "BSE", "INDIA",
            "LAST", "MONTH", "PAST", "DAYS", "ABOUT", "WITH", "FROM", "FOR",
            "THE", "AND", "ARE", "HAS", "HAD", "HAVE", "WAS", "WERE", "WILL",
            "IS", "IT", "IN", "ON", "AT", "TO", "OF", "BY", "AN", "AS", "DO",
            "SO", "OR", "IF", "MY", "ME", "WE", "HE", "BE", "UP", "NO", "GO",
            "NOT", "BUT", "ALL", "ANY", "NEW", "NOW", "ONE", "OUT", "GET", "SEE",
            "LIKE", "ALSO", "SOME", "MORE", "THEN", "THEM", "THAN", "THAT", "THIS",
            "ETF", "ETFS", "IPO", "IPOS", "FPO", "FPOS", "OFS", "NAV", "CMP", "PE",
        }
        for w in words:
            if w not in common_english_words:
                return w, None

        return None, None

    def classify(self, query: str) -> MarketIntentResult:
        """Classify user query into market intent and extract target symbol.
        
        Evaluated entirely with regex in < 1ms without LLM latency.
        """
        trimmed = query.strip()
        if not trimmed:
            return MarketIntentResult(intent="none", confidence=0.0)

        # 1. Market Status Query
        if MARKET_STATUS_PATTERN.search(trimmed):
            exchange = self._extract_exchange(trimmed)
            return MarketIntentResult(intent="market_status", exchange=exchange, confidence=0.95)

        # 2. Extract potential symbol
        symbol, forced_exch = self._extract_symbol(trimmed)
        exchange = forced_exch or self._extract_exchange(trimmed)

        # If no symbol found, it cannot be a quote/historical/overview query
        if not symbol:
            return MarketIntentResult(intent="none", confidence=0.0)

        # Detect potential hybrid multi-part intent
        hybrid_m = HYBRID_CONCEPT_PATTERN.search(trimmed)
        is_hybrid = hybrid_m is not None
        detected_concept = hybrid_m.group(1).strip() if hybrid_m else None

        # 3. Historical Intent
        if HISTORICAL_PATTERN.search(trimmed):
            return MarketIntentResult(
                intent="historical",
                symbol=symbol,
                exchange=exchange,
                confidence=0.90,
                is_hybrid=is_hybrid,
                detected_concept=detected_concept,
            )

        # 4. Overview / Fundamentals Intent
        if OVERVIEW_PATTERN.search(trimmed):
            return MarketIntentResult(
                intent="overview",
                symbol=symbol,
                exchange=exchange,
                confidence=0.90,
                is_hybrid=is_hybrid,
                detected_concept=detected_concept,
            )

        # 5. Quote Intent (Explicit trigger or symbol mentioned with price/status context)
        if QUOTE_PATTERN.search(trimmed) or trimmed.upper() in INDEX_ALIASES or trimmed.upper() in EQUITY_ALIASES:
            return MarketIntentResult(
                intent="quote",
                symbol=symbol,
                exchange=exchange,
                confidence=0.95,
                is_hybrid=is_hybrid,
                detected_concept=detected_concept,
            )

        # If symbol was clearly extracted (e.g. "Reliance" or "TCS") alongside generic query
        # default to quote intent if confidence is reasonable
        if symbol in EQUITY_ALIASES.values() or symbol in INDEX_ALIASES.values():
            return MarketIntentResult(
                intent="quote",
                symbol=symbol,
                exchange=exchange,
                confidence=0.75,
                is_hybrid=is_hybrid,
                detected_concept=detected_concept,
            )

        return MarketIntentResult(intent="none", confidence=0.0)
