"""
Unit tests for the deterministic FastPathClassifier (app.router.classifier).
Verifies domain and intent classification across Equity, Crypto, Personal Finance,
as well as compound query identification and entity extraction.
"""

import time
import pytest
from app.router.classifier import FastPathClassifier, fast_path_classifier


@pytest.fixture
def classifier():
    return FastPathClassifier()


# =====================================================================
# 1. Equity Domain Classification
# =====================================================================
@pytest.mark.parametrize(
    "query,expected_intent,expected_entity",
    [
        ("What is the current price of Reliance?", "quote", "RELIANCE"),
        ("TCS share price on NSE", "quote", "TCS"),
        ("CMP of INFY", "quote", "INFY"),
        ("Nifty 50 today", "quote", "NIFTY 50"),
        ("Sensex value", "quote", "SENSEX"),
        ("How did Reliance perform over the past month?", "historical", "RELIANCE"),
        ("1mo trend for TCS", "historical", "TCS"),
        ("What are the fundamentals and market cap of HDFC Bank?", "overview", "HDFCBANK"),
        ("Tell me about Infosys sector and company profile", "overview", "INFY"),
    ],
)
def test_equity_single_intent_classification(
    classifier: FastPathClassifier, query: str, expected_intent: str, expected_entity: str
):
    res = classifier.classify(query)
    assert res.domain == "EQUITY"
    assert res.intent == expected_intent
    assert expected_entity in res.entities
    assert res.is_fast_path is True
    assert res.confidence >= 0.8


def test_equity_market_status_classification(classifier: FastPathClassifier):
    queries = [
        "Is the stock market open today?",
        "Is NSE closed for Holi?",
        "What are the NSE trading hours?",
        "When does the market open tomorrow?",
    ]
    for q in queries:
        res = classifier.classify(q)
        assert res.domain == "EQUITY"
        assert res.intent == "market_status"
        assert res.confidence >= 0.9


def test_equity_conceptual_rag_classification(classifier: FastPathClassifier):
    queries = [
        "What is an IPO?",
        "How do I lodge a complaint on SCORES?",
        "Explain the difference between buying and selling shares.",
        "What are corporate actions like bonus shares?",
    ]
    for q in queries:
        res = classifier.classify(q)
        assert res.domain == "EQUITY"
        assert res.intent == "educational_concept"


# =====================================================================
# 2. Crypto Domain Classification
# =====================================================================
@pytest.mark.parametrize(
    "query,expected_intent,expected_entity",
    [
        ("Current price of Bitcoin", "quote", "BTC"),
        ("What is BTC trading at?", "quote", "BTC"),
        ("Ethereum price today", "quote", "ETH"),
        ("Solana current price", "quote", "SOL"),
        ("What is blockchain?", "educational_concept", None),
        ("Explain decentralized finance (DeFi)", "educational_concept", None),
        ("How does tokenomics work?", "educational_concept", None),
        ("Why is crypto volatile?", "educational_concept", None),
    ],
)
def test_crypto_domain_classification(
    classifier: FastPathClassifier, query: str, expected_intent: str, expected_entity: str | None
):
    res = classifier.classify(query)
    assert res.domain == "CRYPTO"
    assert res.intent == expected_intent
    if expected_entity:
        assert expected_entity in res.entities


# =====================================================================
# 3. Personal Finance Domain Classification
# =====================================================================
@pytest.mark.parametrize(
    "query,expected_intent",
    [
        ("What is the 50/30/20 budgeting rule?", "educational_concept"),
        ("How do I build an emergency fund?", "educational_concept"),
        ("Explain compound interest and SIP", "educational_concept"),
        ("What affects my credit score?", "educational_concept"),
        ("If my monthly income is ₹50,000, how does 50/30/20 split?", "calculation"),
        ("Calculate 50/30/20 for 100000 salary", "calculation"),
    ],
)
def test_personal_finance_classification(
    classifier: FastPathClassifier, query: str, expected_intent: str
):
    res = classifier.classify(query)
    assert res.domain == "PERSONAL_FINANCE"
    assert res.intent == expected_intent


# =====================================================================
# 4. Compound / Multi-Intent Detection
# =====================================================================
@pytest.mark.parametrize(
    "query",
    [
        "What is an IPO and what is Reliance trading at?",
        "Compare Reliance and TCS price",
        "What is P/E and how should I plan my monthly budget?",
        "Tell me Bitcoin price and what is an ETF?",
    ],
)
def test_compound_query_detection(classifier: FastPathClassifier, query: str):
    res = classifier.classify(query)
    assert res.is_compound is True


# =====================================================================
# 5. Latency Benchmark (< 5ms)
# =====================================================================
def test_classifier_sub_millisecond_speed(classifier: FastPathClassifier):
    query = "What is the current price of Reliance Industries on NSE?"
    t0 = time.perf_counter()
    for _ in range(100):
        classifier.classify(query)
    elapsed_ms = (time.perf_counter() - t0) * 1000
    avg_latency = elapsed_ms / 100
    assert avg_latency < 5.0, f"Classifier was too slow: {avg_latency:.3f}ms per query"
