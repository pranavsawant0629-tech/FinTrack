"""
Deterministic Fast-Path Intent & Domain Classifier.

Evaluates incoming user queries in sub-millisecond time (<1ms) without LLM calls.
Identifies target financial domains (EQUITY, CRYPTO, PERSONAL_FINANCE, GENERAL),
extracts canonical entities, and flags single- vs. multi-intent compound queries.
"""

from __future__ import annotations

import re
from app.router.models import Domain, IntentType, RoutingDecision
from app.tools.market.intent import EQUITY_ALIASES, INDEX_ALIASES

# Prominent Crypto Assets (Name/Alias -> Canonical Ticker)
CRYPTO_ALIASES: dict[str, str] = {
    "BITCOIN": "BTC",
    "BTC": "BTC",
    "ETHEREUM": "ETH",
    "ETHER": "ETH",
    "ETH": "ETH",
    "SOLANA": "SOL",
    "SOL": "SOL",
    "TETHER": "USDT",
    "USDT": "USDT",
    "DOGECOIN": "DOGE",
    "DOGE": "DOGE",
    "RIPPLE": "XRP",
    "XRP": "XRP",
    "CARDANO": "ADA",
    "ADA": "ADA",
    "BINANCE COIN": "BNB",
    "BNB": "BNB",
}

# Domain Trigger Patterns
CRYPTO_CONCEPT_PATTERN = re.compile(
    r"\b(crypto|cryptocurrency|blockchain|defi|decentralized\s+finance|web3|tokenomics|smart\s+contracts?|"
    r"crypto\s+wallet|proof\s+of\s+work|proof\s+of\s+stake|mining|halving|altcoins?|nft|nfts)\b",
    re.IGNORECASE,
)

CRYPTO_PRICE_PATTERN = re.compile(
    r"\b(crypto\s+price|coin\s+price|btc\s+price|bitcoin\s+price|eth\s+price|ethereum\s+price|"
    r"crypto\s+quote|crypto\s+market)\b",
    re.IGNORECASE,
)

PERSONAL_FINANCE_PATTERN = re.compile(
    r"\b(budget|budgeting|50/30/20|emergency\s+fund|savings?|credit\s+score|cibil|debt|loan|"
    r"financial\s+plan|financial\s+planning|compound\s+interest|sip|systematic\s+investment\s+plan|"
    r"monthly\s+income|monthly\s+expense|expense\s+tracker|frugal)\b",
    re.IGNORECASE,
)

# Phase 6 Specialized Domain Patterns
DERIVATIVES_PATTERN = re.compile(
    r"\b(derivative|derivatives|f&o|futures|options?|call\s+option|put\s+option|strike\s+price|"
    r"in\s+the\s+money|out\s+of\s+the\s+money|itm|otm|atm|option\s+greeks?|delta|gamma|theta|vega|rho|"
    r"payoff|breakeven|nifty\s+\d+\s+(?:ce|pe|call|put)|sebi\s+study\s+on\s+f&o|prof\.?\s*derivo)\b",
    re.IGNORECASE,
)

PORTFOLIO_PATTERN = re.compile(
    r"\b(portfolio|my\s+portfolio|portfolio\s+value|current\s+holdings|asset\s+allocation|"
    r"sector\s+allocation|diversification|unsystematic\s+risk|systematic\s+risk|"
    r"what\s+if\s+(?:nifty|[a-zA-Z0-9&]+)\s+(?:falls?|drops?|rises?|gains?))\b",
    re.IGNORECASE,
)

NEWS_PATTERN = re.compile(
    r"\b(news|latest\s+news|market\s+news|sebi\s+circulars?|rbi\s+announcements?|mpc\s+meeting|"
    r"press\s+release|corporate\s+announcements?)\b",
    re.IGNORECASE,
)

QUIZ_PATTERN = re.compile(
    r"\b(quiz|quiz\s+me|test\s+my\s+knowledge|challenge\s+me|knowledge\s+test|financial\s+quiz|"
    r"answer\s*[:=]\s*[A-D]|[a-zA-Z0-9_]+\s*[:=]\s*[A-D])\b",
    re.IGNORECASE,
)

ONBOARDING_PATTERN = re.compile(
    r"\b(what\s+can\s+(?:you|finova(?:\s+ai)?)\s+do|capabilities|help|how\s+to\s+use\s+finova|"
    r"delete\s+my\s+memory|forget\s+me|clear\s+memory|privacy\s+policy|"
    r"sebi\s+registered\s+advisor|orientation)\b",
    re.IGNORECASE,
)

# Indian Equity Market Patterns
MARKET_STATUS_PATTERN = re.compile(
    r"\b(market\s+open|market\s+closed|trading\s+hours|holidays?|is\s+nse\s+open|is\s+nse\s+closed|"
    r"is\s+bse\s+open|is\s+bse\s+closed|market\s+status|next\s+trading\s+session)\b",
    re.IGNORECASE,
)

QUOTE_PATTERN = re.compile(
    r"\b(price|quote|cmp|current\s+price|share\s+price|stock\s+price|trading\s+at|how\s+much\s+is|"
    r"value\s+of|rate\s+of|today['’]?s\s+price)\b",
    re.IGNORECASE,
)

HISTORICAL_PATTERN = re.compile(
    r"\b(historical|past\s+month|last\s+month|1mo|performance|trend|return|monthly\s+chart|past\s+30\s+days)\b",
    re.IGNORECASE,
)

OVERVIEW_PATTERN = re.compile(
    r"\b(fundamentals?|market\s+cap|pe\s+ratio|sector|industry|company\s+profile|overview\s+of|"
    r"about\s+the\s+company|business\s+model|52\s*week\s*high)\b",
    re.IGNORECASE,
)

EQUITY_CONCEPT_PATTERN = re.compile(
    r"\b(ipo|ipos|fpo|sebi|scores|demat|trading\s+account|bonus\s+shares?|stock\s+split|dividend|"
    r"settlement\s+cycle|t\+1|stock\s+exchange|nse|bse|equity\s+market|circuit\s+breaker|etf|etfs|mutual\s+funds?|"
    r"index\s+funds?|shares?|stocks?|equit(?:y|ies)|securities|p/e(?:\s+ratio)?|pe\s+ratio)\b",
    re.IGNORECASE,
)

# Compound / Multi-Intent Coordination Patterns
COMPOUND_CONJUNCTIONS_PATTERN = re.compile(
    r"\b(and\s+also|and\s+what\s+is|and\s+how\s+much|and\s+tell\s+me|as\s+well\s+as|along\s+with|while\s+also)\b|"
    r"\b(?:and|also|while)\s+(?:what|how|why|tell|show|give|is|can)\b",
    re.IGNORECASE,
)


class FastPathClassifier:
    """High-throughput deterministic classifier for query domain and intent."""

    def _extract_equity_symbols(self, query: str) -> list[str]:
        """Extract matched Indian equity tickers and index names."""
        upper = query.upper()
        found: list[str] = []

        # 1. Indices
        for alias, canonical in sorted(INDEX_ALIASES.items(), key=lambda x: -len(x[0])):
            if re.search(rf"\b{re.escape(alias)}\b", upper):
                if canonical not in found:
                    found.append(canonical)

        # 2. Known Equities
        for alias, canonical in sorted(EQUITY_ALIASES.items(), key=lambda x: -len(x[0])):
            if re.search(rf"\b{re.escape(alias)}\b", upper):
                if canonical not in found:
                    found.append(canonical)

        return found

    def _extract_crypto_symbols(self, query: str) -> list[str]:
        """Extract matched cryptocurrency tickers."""
        upper = query.upper()
        found: list[str] = []
        for alias, canonical in sorted(CRYPTO_ALIASES.items(), key=lambda x: -len(x[0])):
            if re.search(rf"\b{re.escape(alias)}\b", upper):
                if canonical not in found:
                    found.append(canonical)
        return found

    def classify(self, query: str) -> RoutingDecision:
        """Classify query domain and intent in <1ms without LLM latency."""
        trimmed = query.strip()
        if not trimmed:
            return RoutingDecision(
                query=query,
                domain="GENERAL",
                intent="unknown",
                confidence=0.0,
                reason="Empty query",
            )

        equity_symbols = self._extract_equity_symbols(trimmed)
        crypto_symbols = self._extract_crypto_symbols(trimmed)
        all_entities = equity_symbols + crypto_symbols

        is_compound = bool(COMPOUND_CONJUNCTIONS_PATTERN.search(trimmed))
        if len(equity_symbols) > 1 or (equity_symbols and crypto_symbols):
            is_compound = True

        # 1. Specialized Domains Fast-Path Checks
        # A. Quiz Intent
        if QUIZ_PATTERN.search(trimmed):
            return RoutingDecision(
                query=trimmed,
                domain="QUIZ",
                intent="educational_concept",
                confidence=0.95,
                entities=[],
                is_compound=is_compound,
                reason="Matched quiz or knowledge challenge pattern",
            )

        # B. Onboarding / Help Intent
        if ONBOARDING_PATTERN.search(trimmed):
            return RoutingDecision(
                query=trimmed,
                domain="ONBOARDING",
                intent="overview",
                confidence=0.95,
                entities=[],
                is_compound=is_compound,
                reason="Matched onboarding, capability overview, or privacy help pattern",
            )

        # C. Derivatives Intent
        if DERIVATIVES_PATTERN.search(trimmed):
            has_calc = bool(re.search(r"\b(payoff|breakeven|calculate|greeks?|delta|theta|gamma)\b", trimmed, re.IGNORECASE))
            return RoutingDecision(
                query=trimmed,
                domain="DERIVATIVES",
                intent="calculation" if has_calc else "educational_concept",
                confidence=0.95,
                entities=equity_symbols,
                is_compound=is_compound,
                reason="Matched options, futures, or derivatives educational pattern",
            )

        # D. Portfolio Intent
        if PORTFOLIO_PATTERN.search(trimmed):
            has_calc = bool(re.search(r"\b(value|allocation|what\s+if|holdings)\b", trimmed, re.IGNORECASE))
            return RoutingDecision(
                query=trimmed,
                domain="PORTFOLIO",
                intent="calculation" if has_calc else "overview",
                confidence=0.95,
                entities=equity_symbols,
                is_compound=is_compound,
                reason="Matched portfolio analytics or stress testing pattern",
            )

        # E. Market News Intent
        if NEWS_PATTERN.search(trimmed):
            return RoutingDecision(
                query=trimmed,
                domain="NEWS",
                intent="overview",
                confidence=0.95,
                entities=equity_symbols,
                is_compound=is_compound,
                reason="Matched financial news or regulatory announcement pattern",
            )

        # 2. Market Status Query (Equity)
        if MARKET_STATUS_PATTERN.search(trimmed):
            return RoutingDecision(
                query=trimmed,
                domain="EQUITY",
                intent="market_status",
                confidence=0.95,
                entities=equity_symbols,
                is_compound=is_compound,
                reason="Matched Indian stock market session/hours pattern",
            )

        # 3. Crypto Intent
        is_crypto_query = bool(crypto_symbols or CRYPTO_CONCEPT_PATTERN.search(trimmed) or CRYPTO_PRICE_PATTERN.search(trimmed))
        has_equity = bool(equity_symbols or EQUITY_CONCEPT_PATTERN.search(trimmed))
        if is_crypto_query and not has_equity and not PERSONAL_FINANCE_PATTERN.search(trimmed):
            if crypto_symbols and (QUOTE_PATTERN.search(trimmed) or CRYPTO_PRICE_PATTERN.search(trimmed)):
                return RoutingDecision(
                    query=trimmed,
                    domain="CRYPTO",
                    intent="quote",
                    confidence=0.95,
                    entities=crypto_symbols,
                    is_compound=is_compound,
                    reason="Matched crypto asset price/quote pattern",
                )
            return RoutingDecision(
                query=trimmed,
                domain="CRYPTO",
                intent="educational_concept",
                confidence=0.90,
                entities=crypto_symbols,
                is_compound=is_compound,
                reason="Matched cryptocurrency/blockchain educational concept",
            )

        # 4. Personal Finance Intent
        is_pf_query = bool(PERSONAL_FINANCE_PATTERN.search(trimmed))
        if is_pf_query and not has_equity and not crypto_symbols:
            is_pure_conceptual = bool(re.search(r"^(?:what\s+is|explain|define|how\s+does)\b", trimmed, re.IGNORECASE)) and not bool(re.search(r"\b(income\s+is|salary|split|\d{4,})\b", trimmed, re.IGNORECASE))
            has_calc_intent = bool(re.search(r"\b(calculate|split|formula\s+for|\b\d{4,}\b|salary|income\s+is)\b", trimmed, re.IGNORECASE)) and not is_pure_conceptual
            intent: IntentType = "calculation" if has_calc_intent else "educational_concept"
            return RoutingDecision(
                query=trimmed,
                domain="PERSONAL_FINANCE",
                intent=intent,
                confidence=0.90,
                entities=[],
                is_compound=is_compound,
                reason="Matched personal finance budgeting/calculation pattern",
            )

        # 5. Cross-Domain and Multi-Intent Compound Query Detection
        domain_matches: list[tuple[int, Domain]] = []
        for alias in EQUITY_ALIASES:
            m = re.search(rf"\b{re.escape(alias)}\b", trimmed, re.IGNORECASE)
            if m:
                domain_matches.append((m.start(), "EQUITY"))
        for alias in INDEX_ALIASES:
            m = re.search(rf"\b{re.escape(alias)}\b", trimmed, re.IGNORECASE)
            if m:
                domain_matches.append((m.start(), "EQUITY"))
        m_eq = EQUITY_CONCEPT_PATTERN.search(trimmed)
        if m_eq:
            domain_matches.append((m_eq.start(), "EQUITY"))

        for alias in CRYPTO_ALIASES:
            m = re.search(rf"\b{re.escape(alias)}\b", trimmed, re.IGNORECASE)
            if m:
                domain_matches.append((m.start(), "CRYPTO"))
        m_cr = CRYPTO_CONCEPT_PATTERN.search(trimmed) or CRYPTO_PRICE_PATTERN.search(trimmed)
        if m_cr:
            domain_matches.append((m_cr.start(), "CRYPTO"))

        m_pf = PERSONAL_FINANCE_PATTERN.search(trimmed)
        if m_pf:
            domain_matches.append((m_pf.start(), "PERSONAL_FINANCE"))

        m_der = DERIVATIVES_PATTERN.search(trimmed)
        if m_der:
            domain_matches.append((m_der.start(), "DERIVATIVES"))

        m_port = PORTFOLIO_PATTERN.search(trimmed)
        if m_port:
            domain_matches.append((m_port.start(), "PORTFOLIO"))

        m_news = NEWS_PATTERN.search(trimmed)
        if m_news:
            domain_matches.append((m_news.start(), "NEWS"))

        m_quiz = QUIZ_PATTERN.search(trimmed)
        if m_quiz:
            domain_matches.append((m_quiz.start(), "QUIZ"))

        m_onb = ONBOARDING_PATTERN.search(trimmed)
        if m_onb:
            domain_matches.append((m_onb.start(), "ONBOARDING"))

        domain_matches.sort(key=lambda x: x[0])
        unique_domains: list[Domain] = []
        for _, dom in domain_matches:
            if dom not in unique_domains:
                unique_domains.append(dom)

        if len(unique_domains) > 1:
            # Check if this is an educational comparison across financial concepts (e.g. equity and debt, mutual funds and fixed deposits)
            is_edu_comparison = bool(re.search(
                r"\b(?:difference\s+between|differences\s+between|distinguish\s+between|compare\s+(?:and\s+contrast|the\s+differences?)|pros\s+and\s+cons|advantages\s+and\s+disadvantages)\b",
                trimmed,
                re.IGNORECASE,
            ))
            if is_edu_comparison:
                primary_dom: Domain = unique_domains[0]
                return RoutingDecision(
                    query=trimmed,
                    domain=primary_dom,
                    intent="educational_concept",
                    confidence=0.90,
                    entities=all_entities,
                    is_compound=False,
                    reason="Matched comparative educational concept across financial terms",
                )
            primary_domain: Domain = unique_domains[0]
            return RoutingDecision(
                query=trimmed,
                domain=primary_domain,
                intent="compound",
                is_fast_path=False,
                confidence=0.85,
                entities=all_entities,
                is_compound=True,
                reason="Detected cross-domain query",
            )

        # 6. Same-Domain Multi-Intent (e.g. Archetype B: Quote + Concept)
        if is_compound and equity_symbols and EQUITY_CONCEPT_PATTERN.search(trimmed):
            return RoutingDecision(
                query=trimmed,
                domain="EQUITY",
                intent="compound",
                confidence=0.90,
                entities=equity_symbols,
                is_compound=True,
                reason="Matched compound equity quote and conceptual question",
            )

        # 7. Single-Intent Equity Patterns
        if equity_symbols:
            if HISTORICAL_PATTERN.search(trimmed):
                return RoutingDecision(
                    query=trimmed,
                    domain="EQUITY",
                    intent="historical",
                    confidence=0.90,
                    entities=equity_symbols,
                    is_compound=False,
                    reason="Matched 1-month historical equity performance pattern",
                )
            if OVERVIEW_PATTERN.search(trimmed):
                return RoutingDecision(
                    query=trimmed,
                    domain="EQUITY",
                    intent="overview",
                    confidence=0.90,
                    entities=equity_symbols,
                    is_compound=False,
                    reason="Matched company overview/fundamentals pattern",
                )

            # Check if the query is an educational question about equity concepts or indices
            has_edu_interrogative = bool(re.search(
                r"\b(?:what\s+is|what\s+are|explain|define|how\s+does|how\s+do|difference\s+between|differences\s+between|distinguish\s+between)\b",
                trimmed,
                re.IGNORECASE,
            ))
            has_quote_terms = bool(QUOTE_PATTERN.search(trimmed))

            if has_edu_interrogative and not has_quote_terms:
                return RoutingDecision(
                    query=trimmed,
                    domain="EQUITY",
                    intent="educational_concept",
                    confidence=0.90,
                    entities=equity_symbols,
                    is_compound=False,
                    reason="Matched educational concept inquiry regarding equity asset or benchmark index",
                )
            # Default to quote (preserving is_compound flag)
            return RoutingDecision(
                query=trimmed,
                domain="EQUITY",
                intent="quote",
                confidence=0.95 if has_quote_terms else 0.80,
                entities=equity_symbols,
                is_compound=is_compound,
                reason="Matched equity ticker quote request",
            )

        # 6. Conceptual Equity RAG Pattern
        if EQUITY_CONCEPT_PATTERN.search(trimmed):
            return RoutingDecision(
                query=trimmed,
                domain="EQUITY",
                intent="educational_concept",
                confidence=0.85,
                entities=[],
                is_compound=False,
                reason="Matched conceptual equity/regulatory query for SEBI RAG",
            )

        # 7. Fallback General
        return RoutingDecision(
            query=trimmed,
            domain="GENERAL",
            intent="educational_concept",
            confidence=0.60,
            entities=[],
            is_compound=False,
            reason="Unclassified generic financial query",
        )


fast_path_classifier = FastPathClassifier()
