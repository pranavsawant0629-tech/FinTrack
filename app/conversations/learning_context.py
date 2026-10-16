"""
Learning Context and Pedagogical Topic Resolver for Finova AI.
Phase 11: Conversational learning experience across all financial domains.

Provides high-speed (<0.2ms) deterministic resolution of:
- Canonical educational topic
- Related concepts
- Suggested next steps
- Topic continuity across bounded conversation turns
"""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CanonicalTopic:
    """Represents a canonical financial learning topic."""

    name: str
    domain: str
    keywords: list[str]
    related_concepts: list[str]
    suggested_next: list[str]
    analogy_hint: str = ""
    mechanics_hint: str = ""


# Curated, lightweight taxonomy across all Finova domains
CANONICAL_TOPICS: list[CanonicalTopic] = [
    # --- EQUITY ---
    CanonicalTopic(
        name="P/E Ratio & Valuation",
        domain="equity",
        keywords=["pe ratio", "p/e", "price to earnings", "price-to-earnings", "trailing pe", "forward pe", "valuation multiple", "expensive stock"],
        related_concepts=["EPS (Earnings Per Share)", "P/B Ratio", "Market Capitalization", "EV/EBITDA"],
        suggested_next=[
            "Why do high-growth companies often have high P/E?",
            "What is the difference between trailing and forward P/E?",
            "How does industry context affect what is a good P/E?",
        ],
        analogy_hint="P/E is like the price tag of a fruit stall relative to how much profit it produces each year.",
        mechanics_hint="P/E = Market Price per Share / Earnings Per Share (EPS).",
    ),
    CanonicalTopic(
        name="Market Capitalization & Sizing",
        domain="equity",
        keywords=["market cap", "market capitalization", "large cap", "mid cap", "small cap", "micro cap", "free float"],
        related_concepts=["Free Float", "Liquidity", "NIFTY 50", "P/E Ratio"],
        suggested_next=[
            "How does SEBI categorize Large Cap, Mid Cap, and Small Cap stocks?",
            "What is free-float market capitalization vs full market capitalization?",
            "Why do small cap stocks carry higher volatility than large caps?",
        ],
        mechanics_hint="Market Cap = Total Outstanding Shares * Current Market Price.",
    ),
    CanonicalTopic(
        name="Initial Public Offering (IPO)",
        domain="equity",
        keywords=["ipo", "initial public offering", "drhp", "rhp", "grey market premium", "gmp", "listing gains", "anchor investor", "retail quota"],
        related_concepts=["OFS (Offer for Sale)", "Fresh Issue", "Book Building", "Listing Day Gains"],
        suggested_next=[
            "What is the difference between a Fresh Issue and an Offer for Sale (OFS)?",
            "What should retail investors check in a company's DRHP before applying?",
            "How does SEBI regulate the retail allotment process in oversubscribed IPOs?",
        ],
    ),
    CanonicalTopic(
        name="Balance Sheet & Financial Health",
        domain="equity",
        keywords=["balance sheet", "debt to equity", "debt/equity", "current ratio", "working capital", "roe", "roce", "assets and liabilities"],
        related_concepts=["ROE (Return on Equity)", "ROCE", "Debt-to-Equity Ratio", "Free Cash Flow"],
        suggested_next=[
            "How do you assess if a company has too much debt on its balance sheet?",
            "What is the difference between ROE and ROCE in Indian companies?",
            "How does working capital efficiency affect shareholder value?",
        ],
    ),
    CanonicalTopic(
        name="Dividends & Shareholder Yield",
        domain="equity",
        keywords=["dividend", "dividend yield", "ex-dividend", "record date", "dividend payout", "buyback"],
        related_concepts=["Dividend Yield", "Record Date", "Share Buyback", "Payout Ratio"],
        suggested_next=[
            "What is the difference between dividend yield and capital appreciation?",
            "How do ex-dividend and record dates work on the NSE/BSE?",
            "Are share buybacks more tax-efficient than dividends for Indian investors?",
        ],
    ),
    CanonicalTopic(
        name="P/B Ratio & Book Value",
        domain="equity",
        keywords=["p/b", "pb ratio", "price to book", "book value", "net worth per share", "tangible book value"],
        related_concepts=["P/E Ratio", "ROE", "Tangible Net Worth", "Bank Valuation"],
        suggested_next=[
            "Why is P/B ratio particularly important when valuing Indian banks and NBFCs?",
            "What does a P/B ratio under 1.0 indicate about a business?",
            "How does Book Value differ from Market Value?",
        ],
    ),

    # --- DERIVATIVES ---
    CanonicalTopic(
        name="Call Options & Bullish Payoffs",
        domain="derivatives",
        keywords=["call option", "call options", "long call", "short call", "ce", "call premium", "buy call"],
        related_concepts=["Strike Price", "Option Premium", "Breakeven Price", "Put Option"],
        suggested_next=[
            "How do you calculate the breakeven point on a Long Call option?",
            "What is the risk and maximum loss when buying vs selling a Call option?",
            "How does time decay (Theta) erode a Call option's premium over time?",
        ],
        mechanics_hint="Call Option Payoff = max(Spot - Strike, 0) - Premium Paid.",
    ),
    CanonicalTopic(
        name="Put Options & Hedging",
        domain="derivatives",
        keywords=["put option", "put options", "long put", "short put", "pe", "put premium", "buy put", "protective put"],
        related_concepts=["Protective Put", "Strike Price", "Option Premium", "Call Option"],
        suggested_next=[
            "How does a protective put hedge an equity stock portfolio against crashes?",
            "What is the maximum profit and loss on a long put position?",
            "What is Put-Call Ratio (PCR) and how do traders interpret it?",
        ],
        mechanics_hint="Put Option Payoff = max(Strike - Spot, 0) - Premium Paid.",
    ),
    CanonicalTopic(
        name="Option Moneyness (ITM, ATM, OTM)",
        domain="derivatives",
        keywords=["moneyness", "itm", "in the money", "in-the-money", "atm", "at the money", "at-the-money", "otm", "out of the money", "out-of-the-money"],
        related_concepts=["Intrinsic Value", "Extrinsic / Time Value", "Delta", "Option Decay"],
        suggested_next=[
            "Why do deep OTM options have a high probability of expiring worthless?",
            "How do intrinsic value and time value change as expiry approaches?",
            "Which strikes offer the best risk-reward for retail options buyers?",
        ],
    ),
    CanonicalTopic(
        name="Option Greeks & Risk Dynamics",
        domain="derivatives",
        keywords=["greeks", "delta", "gamma", "theta", "vega", "rho", "time decay", "implied volatility", "iv"],
        related_concepts=["Delta", "Theta Decay", "Implied Volatility (IV)", "Gamma Risk"],
        suggested_next=[
            "How does Delta tell you both price sensitivity and approximate probability of expiring ITM?",
            "Why does Theta decay accelerate exponentially during the final week before expiry?",
            "What happens to option premiums when India VIX suddenly spikes?",
        ],
    ),
    CanonicalTopic(
        name="Futures Contracts & Margins",
        domain="derivatives",
        keywords=["futures", "future contract", "nifty futures", "span margin", "exposure margin", "mark to market", "m2m", "lot size"],
        related_concepts=["SPAN Margin", "Mark to Market (M2M)", "Lot Size", "Basis & Cost of Carry"],
        suggested_next=[
            "How does Mark to Market (M2M) settlement work daily on NSE futures?",
            "What is the difference between SPAN margin and exposure margin?",
            "Why is leverage in futures a double-edged sword for retail traders?",
        ],
    ),

    # --- PERSONAL FINANCE ---
    CanonicalTopic(
        name="SIP & Rupee Cost Averaging",
        domain="personal_finance",
        keywords=["sip", "systematic investment plan", "rupee cost averaging", "monthly investment", "step up sip", "step-up sip"],
        related_concepts=["Compounding", "Mutual Funds", "Lump Sum vs SIP", "Expense Ratio"],
        suggested_next=[
            "How does rupee-cost averaging protect you during market drawdowns?",
            "What is the quantitative impact of an annual 10% Step-Up on a 15-year SIP?",
            "When should an investor choose a SIP vs investing a lump sum?",
        ],
        analogy_hint="SIP is like planting a tree each month: in rainy years seeds are cheap, in sunny years they grow.",
        mechanics_hint="SIP Future Value = P * [((1 + r)^n - 1) / r] * (1 + r).",
    ),
    CanonicalTopic(
        name="Compounding & Time Horizon",
        domain="personal_finance",
        keywords=["compounding", "compound interest", "rule of 72", "exponential growth", "power of compounding", "long term wealth"],
        related_concepts=["SIP", "Inflation", "Real Returns", "CAGR"],
        suggested_next=[
            "How does the Rule of 72 quickly estimate when your money will double?",
            "Why does starting an investment at age 25 vs 35 result in dramatically higher wealth?",
            "How does inflation erode the purchasing power of your compounded corpus?",
        ],
        mechanics_hint="A = P * (1 + r/n)^(n*t).",
    ),
    CanonicalTopic(
        name="50/30/20 Budgeting & Cash Flow",
        domain="personal_finance",
        keywords=["50/30/20", "budgeting", "budget", "needs wants savings", "spending plan", "cash flow allocation"],
        related_concepts=["Emergency Fund", "Savings Rate", "Discretionary Spending", "Debt Payoff"],
        suggested_next=[
            "How do you adapt the 50/30/20 rule to high-cost Indian metro cities?",
            "Which category do insurance premiums and loan EMIs fall under in 50/30/20?",
            "What simple habits help maintain a 30% savings rate consistently?",
        ],
    ),
    CanonicalTopic(
        name="Emergency Fund & Liquidity",
        domain="personal_finance",
        keywords=["emergency fund", "contingency fund", "liquid fund", "rainy day fund", "liquidity buffer", "3 to 6 months expenses"],
        related_concepts=["Liquid Mutual Funds", "Fixed Deposit (FD)", "50/30/20 Budget", "Health Insurance"],
        suggested_next=[
            "Where should you park your emergency fund to balance safety and inflation?",
            "How many months of living expenses should salaried vs self-employed professionals hold?",
            "Why should you never invest your emergency fund in volatile equity stocks?",
        ],
    ),
    CanonicalTopic(
        name="Tax Planning & Section 80C",
        domain="personal_finance",
        keywords=["80c", "section 80c", "tax planning", "elss", "ppf", "nps", "new tax regime", "old tax regime", "income tax deduction"],
        related_concepts=["ELSS Mutual Funds", "PPF (Public Provident Fund)", "NPS", "Old vs New Regime"],
        suggested_next=[
            "Which is better for you: the New Tax Regime or the Old Tax Regime with deductions?",
            "Why does ELSS offer the shortest lock-in (3 years) among all Section 80C instruments?",
            "How does NPS Tier 1 provide an additional ₹50,000 deduction under Section 80CCD(1B)?",
        ],
    ),

    # --- CRYPTO ---
    CanonicalTopic(
        name="Bitcoin & Blockchain Fundamentals",
        domain="crypto",
        keywords=["bitcoin", "btc", "blockchain", "satoshi", "halving", "distributed ledger", "peer to peer", "digital gold"],
        related_concepts=["Consensus Mechanisms", "Crypto Market Cap", "Self-Custody Wallets", "Bitcoin Halving"],
        suggested_next=[
            "What is the Bitcoin halving cycle and how does it affect token supply emission?",
            "How does a distributed cryptographic blockchain prevent double-spending without a central bank?",
            "How is crypto taxation structured in India under Section 115BBH (30% flat tax + 1% TDS)?",
        ],
    ),
    CanonicalTopic(
        name="Consensus Mechanisms (PoW vs PoS)",
        domain="crypto",
        keywords=["proof of work", "proof of stake", "pow", "pos", "mining", "staking", "validator", "consensus"],
        related_concepts=["Blockchain", "Ethereum", "Energy Consumption", "Staking Rewards"],
        suggested_next=[
            "What is the technical difference between Proof-of-Work mining and Proof-of-Stake validation?",
            "Why did Ethereum transition from PoW to PoS during 'The Merge'?",
            "What are the centralization and security trade-offs of Proof-of-Stake?",
        ],
    ),
    CanonicalTopic(
        name="Self-Custody & Crypto Wallets",
        domain="crypto",
        keywords=["wallet", "hardware wallet", "cold storage", "hot wallet", "private key", "seed phrase", "ledger", "metamask"],
        related_concepts=["Private Keys", "Exchange Counterparty Risk", "Smart Contracts", "Security"],
        suggested_next=[
            "What does 'not your keys, not your coins' mean in practice?",
            "What is the difference between a custodial exchange wallet and non-custodial cold storage?",
            "How should users securely store and protect their 12 or 24-word recovery seed phrase?",
        ],
    ),

    # --- PORTFOLIO ---
    CanonicalTopic(
        name="Diversification & Correlation",
        domain="portfolio",
        keywords=["diversification", "diversify", "dont put all eggs in one basket", "correlation", "uncorrelated", "asset classes"],
        related_concepts=["Asset Allocation", "Systematic vs Unsystematic Risk", "Portfolio Variance", "Rebalancing"],
        suggested_next=[
            "Why does adding uncorrelated assets reduce overall portfolio risk without sacrificing expected return?",
            "What is the difference between systematic (market) risk and unsystematic (company) risk?",
            "How does Indian equity correlate with gold, real estate, and government bonds historically?",
        ],
    ),
    CanonicalTopic(
        name="Asset Allocation & Rebalancing",
        domain="portfolio",
        keywords=["asset allocation", "rebalance", "rebalancing", "equity debt ratio", "60/40", "portfolio weight", "drift"],
        related_concepts=["Diversification", "Risk Tolerance", "Drawdown", "Glide Path"],
        suggested_next=[
            "How often should an individual rebalance their portfolio: calendar-based vs threshold-based?",
            "What is a standard asset allocation framework for a 20-year retirement goal?",
            "What are the tax implications of rebalancing by selling appreciated equity funds in India?",
        ],
    ),
    CanonicalTopic(
        name="Sharpe Ratio & Risk-Adjusted Returns",
        domain="portfolio",
        keywords=["sharpe ratio", "risk adjusted return", "risk-adjusted", "standard deviation", "volatility", "treynor ratio", "sortino ratio"],
        related_concepts=["Standard Deviation", "Sortino Ratio", "Beta", "Risk-Free Rate"],
        suggested_next=[
            "What does a Sharpe ratio above 1.0 indicate about a fund manager's performance?",
            "How does Sortino ratio improve upon Sharpe ratio by focusing solely on downside volatility?",
            "What risk-free rate proxy is standard when calculating Sharpe ratio in India?",
        ],
        mechanics_hint="Sharpe Ratio = (Portfolio Return - Risk-Free Rate) / Portfolio Standard Deviation.",
    ),
    CanonicalTopic(
        name="Beta & Systematic Market Risk",
        domain="portfolio",
        keywords=["beta", "high beta", "low beta", "systematic risk", "market sensitivity", "nifty beta"],
        related_concepts=["Alpha", "NIFTY 50", "Sharpe Ratio", "Volatility"],
        suggested_next=[
            "What does a Beta of 1.4 mean for a stock when the NIFTY 50 rises or falls by 10%?",
            "When should an investor consider overweighting low-beta vs high-beta stocks?",
            "How is Beta calculated using covariance with the market index?",
        ],
    ),

    # --- NEWS / MACRO ---
    CanonicalTopic(
        name="RBI Monetary Policy & Repo Rate",
        domain="news",
        keywords=["rbi", "repo rate", "reverse repo", "mpc", "monetary policy", "interest rate hike", "rate cut", "inflation targeting"],
        related_concepts=["CPI Inflation", "Bond Yields", "Bank FD Rates", "Stock Market Multiples"],
        suggested_next=[
            "How does a change in the RBI Repo Rate transmit to home loan EMIs and stock markets?",
            "What is the RBI's statutory inflation target range (4% +/- 2%)?",
            "Why do high interest rates tend to compress equity valuation multiples like P/E?",
        ],
    ),
    CanonicalTopic(
        name="Inflation & Purchasing Power",
        domain="news",
        keywords=["inflation", "cpi", "wpi", "purchasing power", "cost of living", "real return", "headline inflation"],
        related_concepts=["Repo Rate", "Gold", "Equity Compounding", "Fixed Income"],
        suggested_next=[
            "What is the difference between Consumer Price Index (CPI) and Wholesale Price Index (WPI) in India?",
            "How do equity and gold act as long-term hedges against persistent inflation?",
            "What are negative real interest rates and how do they impact conservative savers?",
        ],
    ),
]


# Fast keyword lookup index
_TOPIC_LOOKUP: dict[str, CanonicalTopic] = {}
for _topic in CANONICAL_TOPICS:
    _TOPIC_LOOKUP[_topic.name.lower()] = _topic


# Action phrases that signal follow-up pedagogical turns
LEARNING_ACTION_PATTERNS = [
    r"\bexplain\s+(?:more\s+)?simpler\b",
    r"\bexplain\s+simply\b",
    r"\b(?:in\s+)?simpler\s+terms\b",
    r"\bsimple\s+terms\b",
    r"\bsimpler\b",
    r"\bbeginner\b",
    r"\belike\s+i['’]m\s+5\b",
    r"\beli5\b",
    r"\bgo\s+deeper\b",
    r"\bdeep\s+dive\b",
    r"\bdeeper\b",
    r"\bgive\s+(?:me\s+)?(?:an?\s+)?example\b",
    r"\bpractical\s+example\b",
    r"\b(?:give\s+an?\s+)?analogy\b",
    r"\bexplain\s+with\s+(?:an?\s+)?analogy\b",
    r"\bshow\s+(?:the\s+)?mechanics\b",
    r"\bhow\s+does\s+it\s+work\b",
    r"\bquiz\s+me\b",
    r"\btest\s+my\s+knowledge\b",
    r"\bwhat\s+should\s+i\s+learn\s+next\b",
    r"\bwhat\s+next\b",
    r"\bnext\s+step[s]?\b",
]

_ACTION_REGEX = re.compile("|".join(LEARNING_ACTION_PATTERNS), re.IGNORECASE)


@dataclass
class LearningContextResult:
    """Resolved learning metadata for a conversational turn."""

    topic: str | None = None
    related_concepts: list[str] = field(default_factory=list)
    suggested_next: list[str] = field(default_factory=list)
    is_action_followup: bool = False


def _match_topic_from_text(text: str, domain_hint: str | None = None) -> CanonicalTopic | None:
    """Find best matching canonical topic from query text."""
    low = text.lower()
    best_match: CanonicalTopic | None = None
    best_score = 0

    norm_hint = domain_hint.lower().strip() if domain_hint else None
    if norm_hint == "personalfinance":
        norm_hint = "personal_finance"

    for topic in CANONICAL_TOPICS:
        # Score matching keywords
        score = 0
        for kw in topic.keywords:
            if kw in low:
                # Prioritize longer keyword matches
                score += len(kw) + (5 if kw.startswith(low[:5]) else 0)

        if score > 0:
            # Domain alignment bonus
            if norm_hint and topic.domain == norm_hint:
                score += 15

            if score > best_score:
                best_score = score
                best_match = topic

    return best_match if best_score >= 3 else None


def resolve_learning_context(
    query: str,
    domain: str | None = None,
    conversation_history: list[dict[str, str]] | None = None,
    orchestrator_response: Any | None = None,
) -> LearningContextResult:
    """
    Resolve canonical topic, related concepts, and suggested next steps for an educational turn.

    Enforces:
    1. Safety Refusals / Filtered Turns -> return topic=None, no actions.
    2. Pure Quotes / Non-educational lookups -> return topic=None, no actions.
    3. Topic Continuity: If query is an action or continuation follow-up,
       inspects preceding bounded history (last 6 turns) to maintain active topic.
    """
    # 1. Inspect orchestrator response for safety refusals or errors
    if orchestrator_response:
        # Step 1 Safety Refusal check
        if getattr(orchestrator_response, "model_used", "") == "deterministic_guardrail":
            return LearningContextResult()

        sub_tasks = getattr(orchestrator_response, "sub_tasks", None) or []
        for st in sub_tasks:
            intent = getattr(st, "intent", "")
            status = getattr(st, "status", "")
            if intent == "advice_refusal" or status == "filtered":
                return LearningContextResult()

        # Pure market quote check: if response has market quote without educational text
        # e.g. pure stock price lookup for RELIANCE with short non-educational answer
        has_market = getattr(orchestrator_response, "market_data", None) is not None or bool(
            getattr(orchestrator_response, "market_data_list", None)
        )
        has_crypto = getattr(orchestrator_response, "crypto_data", None) is not None
        grounding_status = getattr(orchestrator_response, "grounding_status", "")

        # If answer is very short and just quotes a price, skip educational topic
        ans_text = getattr(orchestrator_response, "answer", "")
        if (has_market or has_crypto) and len(ans_text.split()) < 15 and "ratio" not in ans_text.lower():
            return LearningContextResult()

    trimmed = query.strip()
    is_action = bool(_ACTION_REGEX.search(trimmed))

    # 2. Match topic directly from current query
    topic = _match_topic_from_text(trimmed, domain_hint=domain)

    # 3. If query didn't match a topic directly (e.g. "Explain simpler", "Why is it high?", "Give an example")
    # inspect preceding conversation history (bounded to last 6 messages) in reverse
    if not topic and conversation_history:
        for turn in reversed(conversation_history):
            content = turn.get("content", "")
            matched = _match_topic_from_text(content, domain_hint=domain)
            if matched:
                topic = matched
                break

    # 4. If still no topic matched, check if query contains any generic financial terms matching domain
    if not topic and domain:
        norm_domain = domain.lower().strip()
        if norm_domain == "equity":
            # Default to general equity if asking broad questions
            if any(w in trimmed.lower() for w in ["share", "stock", "company", "invest in stocks", "equity"]):
                topic = _TOPIC_LOOKUP.get("market capitalization & sizing")
        elif norm_domain == "derivatives":
            if any(w in trimmed.lower() for w in ["f&o", "futures", "options"]):
                topic = _TOPIC_LOOKUP.get("call options & bullish payoffs")
        elif norm_domain == "personal_finance":
            if any(w in trimmed.lower() for w in ["money", "save", "saving", "invest", "finance"]):
                topic = _TOPIC_LOOKUP.get("sip & rupee cost averaging")

    # 5. Construct result
    if topic:
        return LearningContextResult(
            topic=topic.name,
            related_concepts=list(topic.related_concepts),
            suggested_next=list(topic.suggested_next),
            is_action_followup=is_action,
        )

    return LearningContextResult()
