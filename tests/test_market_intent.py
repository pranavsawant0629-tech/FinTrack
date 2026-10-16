"""Unit tests for deterministic MarketIntentClassifier."""

import pytest

from app.tools.market.intent import MarketIntentClassifier, MarketIntentResult


@pytest.fixture
def classifier():
    return MarketIntentClassifier()


@pytest.mark.parametrize(
    "query,expected_symbol,expected_exchange",
    [
        ("What is the current price of Reliance?", "RELIANCE", "NSE"),
        ("Quote for TCS on BSE", "TCS", "BSE"),
        ("Nifty 50 today", "NIFTY 50", "NSE"),
        ("Sensex current price", "SENSEX", "BSE"),
        ("CMP of INFY", "INFY", "NSE"),
        ("What is the stock price of HDFC Bank?", "HDFCBANK", "NSE"),
        ("State Bank of India share price", "SBIN", "NSE"),
    ],
)
def test_quote_intent_classification(
    classifier: MarketIntentClassifier, query: str, expected_symbol: str, expected_exchange: str
):
    res = classifier.classify(query)
    assert res.intent == "quote"
    assert res.symbol == expected_symbol
    assert res.exchange == expected_exchange
    assert res.confidence > 0.7


@pytest.mark.parametrize(
    "query,expected_symbol",
    [
        ("How did Reliance perform over the past month?", "RELIANCE"),
        ("1mo trend for TCS", "TCS"),
        ("Tata Motors monthly performance", "TATAMOTORS"),
        ("Infosys return over last month", "INFY"),
    ],
)
def test_historical_intent_classification(
    classifier: MarketIntentClassifier, query: str, expected_symbol: str
):
    res = classifier.classify(query)
    assert res.intent == "historical"
    assert res.symbol == expected_symbol
    assert res.confidence >= 0.8


@pytest.mark.parametrize(
    "query,expected_symbol",
    [
        ("What are the fundamentals and market cap of HDFC Bank?", "HDFCBANK"),
        ("Tell me about Infosys sector and company profile", "INFY"),
        ("What is the PE ratio of Reliance Industries?", "RELIANCE"),
    ],
)
def test_overview_intent_classification(
    classifier: MarketIntentClassifier, query: str, expected_symbol: str
):
    res = classifier.classify(query)
    assert res.intent == "overview"
    assert res.symbol == expected_symbol
    assert res.confidence >= 0.8


@pytest.mark.parametrize(
    "query",
    [
        "Is the stock market open today?",
        "Is NSE closed for Holi?",
        "What are the NSE trading hours?",
        "When does the market open tomorrow?",
        "Is today a trading holiday?",
    ],
)
def test_market_status_intent_classification(classifier: MarketIntentClassifier, query: str):
    res = classifier.classify(query)
    assert res.intent == "market_status"
    assert res.confidence >= 0.9


@pytest.mark.parametrize(
    "query",
    [
        "What is an IPO?",
        "How do I lodge a complaint on SCORES?",
        "Explain the difference between buying and selling shares.",
        "What are corporate actions like bonus shares?",
        "What does SEBI stand for?",
        "Can you explain equity risk?",
    ],
)
def test_non_market_conceptual_queries_route_to_none(
    classifier: MarketIntentClassifier, query: str
):
    res = classifier.classify(query)
    assert res.intent == "none"
    assert res.symbol is None


@pytest.mark.parametrize(
    "query,expected_symbol,expected_concept",
    [
        ("What is an IPO and what is Reliance trading at?", "RELIANCE", "IPO"),
        ("What is an ETF and what is NIFTYBEES trading at?", "NIFTYBEES", "ETF"),
        ("Explain bonus shares and tell me TCS price", "TCS", "bonus shares"),
    ],
)
def test_hybrid_query_intent_detection(
    classifier: MarketIntentClassifier, query: str, expected_symbol: str, expected_concept: str
):
    res = classifier.classify(query)
    assert res.intent == "quote"
    assert res.symbol == expected_symbol
    assert res.is_hybrid is True
    assert res.detected_concept == expected_concept

