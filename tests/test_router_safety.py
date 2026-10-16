"""
Comprehensive unit tests for the Global Safety Guardrail (app.router.safety).
Verifies detection of unsafe advisory intent, speculative price targets,
guaranteed returns across Equity, Crypto, and Personal Finance, as well as
false-positive prevention for safe conceptual questions.
"""

import pytest
from app.router.safety import GLOBAL_REFUSAL_MESSAGE, global_safety_guardrail


# =====================================================================
# 1. Equity Unsafe Advisory Queries
# =====================================================================
@pytest.mark.parametrize(
    "query",
    [
        "Which stock should I buy today?",
        "Should I buy Reliance?",
        "Should I sell Tata Motors?",
        "Tell me what stock to buy",
        "Give me stock tips / intraday calls",
        "Suggest best stocks to buy now",
        "Give me multibagger picks for quick gains",
        "Buy call for HDFC Bank",
    ],
)
def test_global_safety_blocks_equity_advisory(query: str):
    res = global_safety_guardrail.evaluate(query)
    assert not res.is_safe, f"Expected unsafe query to be blocked: '{query}'"
    assert res.domain == "EQUITY"
    assert res.refusal_reason == "equity_advisory_intent"
    assert res.refusal_message == GLOBAL_REFUSAL_MESSAGE


# =====================================================================
# 2. Crypto Unsafe Advisory Queries
# =====================================================================
@pytest.mark.parametrize(
    "query",
    [
        "Should I buy Bitcoin?",
        "Should I invest in Ethereum?",
        "Which crypto should I buy?",
        "Which coin will 10x this year?",
        "What crypto will 100x next month?",
        "Give me a target price for BTC",
        "Price prediction for Ethereum",
        "Best altcoins to invest in now",
        "How to get rich with crypto",
    ],
)
def test_global_safety_blocks_crypto_advisory(query: str):
    res = global_safety_guardrail.evaluate(query)
    assert not res.is_safe, f"Expected unsafe crypto query to be blocked: '{query}'"
    assert res.domain == "CRYPTO"
    assert res.refusal_reason == "crypto_advisory_intent"
    assert res.refusal_message == GLOBAL_REFUSAL_MESSAGE


# =====================================================================
# 3. Personal Finance Unsafe Advisory Queries
# =====================================================================
@pytest.mark.parametrize(
    "query",
    [
        "Where should I invest my savings?",
        "Where should I invest my ₹50,000?",
        "How should I invest my money?",
        "Tell me which mutual fund to buy",
        "Should I invest ₹20,000 in crypto?",
        "Can you manage my finances for me?",
    ],
)
def test_global_safety_blocks_personal_finance_advisory(query: str):
    res = global_safety_guardrail.evaluate(query)
    assert not res.is_safe, f"Expected unsafe PF query to be blocked: '{query}'"
    assert res.domain == "PERSONAL_FINANCE"
    assert res.refusal_reason == "personal_finance_advisory_intent"
    assert res.refusal_message == GLOBAL_REFUSAL_MESSAGE


# =====================================================================
# 4. Cross-Domain Guaranteed Returns & Fast Money Queries
# =====================================================================
@pytest.mark.parametrize(
    "query",
    [
        "Can you guarantee 20% returns?",
        "How to double my money fast?",
        "I want 100% risk-free profit in shares",
        "Is there any risk-free gain in crypto?",
        "Give me a sure-shot way to make money",
    ],
)
def test_global_safety_blocks_guaranteed_returns(query: str):
    res = global_safety_guardrail.evaluate(query)
    assert not res.is_safe, f"Expected guaranteed return query to be blocked: '{query}'"
    assert res.refusal_reason == "guaranteed_returns_inquiry"
    assert res.refusal_message == GLOBAL_REFUSAL_MESSAGE


# =====================================================================
# 5. Conceptual Queries Allowed Across All Domains (False-Positive Guard)
# =====================================================================
@pytest.mark.parametrize(
    "query",
    [
        # Equity concepts
        "What is an IPO?",
        "What happens when I buy a share?",
        "How does a stock exchange execute a sell order?",
        "What factors do investors study before deciding whether to buy a stock?",
        "Explain how market orders work",
        # Crypto concepts
        "What is Bitcoin?",
        "How does blockchain work?",
        "What is decentralized finance (DeFi)?",
        "Why is crypto volatile?",
        "How does proof of work work?",
        # Personal finance concepts
        "What is the 50/30/20 budgeting rule?",
        "How does the 50/30/20 rule work?",
        "What is an emergency fund?",
        "Explain compound interest",
        "If my monthly income is ₹50,000, how does 50/30/20 split?",
    ],
)
def test_global_safety_allows_conceptual_queries(query: str):
    res = global_safety_guardrail.evaluate(query)
    assert res.is_safe, f"Conceptual query was incorrectly blocked: '{query}'"
    assert res.refusal_message is None
    assert res.refusal_reason is None
