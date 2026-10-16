"""
Unit tests for ResponseComposer (app.router.composer).
Verifies strict numerical output preservation, citation preservation,
multi-source composition, and causal market dynamics explanations.
"""

import pytest
from app.rag.service import Citation
from app.router.composer import CAUSAL_MARKET_EXPLAINER, ResponseComposer, response_composer
from app.tools.market.models import MarketQuote


@pytest.fixture
def composer():
    return ResponseComposer()


@pytest.fixture
def sample_quote():
    return MarketQuote(
        symbol="RELIANCE",
        company_name="Reliance Industries Limited",
        exchange="NSE",
        currency="INR",
        price=2985.40,
        change=15.20,
        change_percent=0.51,
        previous_close=2970.20,
        open=2975.00,
        high=2990.00,
        low=2965.00,
        volume=3500000,
        market_status="regular_trading",
        market_timestamp="2026-09-11T14:30:00+05:30",
        retrieved_at="2026-09-11T14:30:05+05:30",
        provider="Yahoo Finance",
        freshness_status="delayed",
    )


@pytest.fixture
def sample_citation():
    return Citation(
        citation_id=1,
        chunk_id="chunk_101",
        doc_id="sebi_ipo_guide",
        title="SEBI Guide to Initial Public Offerings",
        source="SEBI",
        authority_level="Tier 1",
        url="https://investor.sebi.gov.in/pdf/ipo.pdf",
        page_numbers=[3, 4],
        similarity_score=0.89,
    )


def test_numerical_output_preservation(composer: ResponseComposer, sample_quote: MarketQuote):
    """Verifies that numerical outputs originate from validated deterministic tools and are not modified."""
    card = composer.format_quote_card(sample_quote)
    assert "₹2,985.40" in card
    assert "+15.20" in card
    assert "+0.51%" in card
    assert "₹2,970.20" in card
    assert "₹2,965.00 - ₹2,990.00" in card
    assert "3,500,000 shares" in card
    assert "Yahoo Finance" in card


def test_hybrid_rag_and_quote_composition(
    composer: ResponseComposer, sample_quote: MarketQuote, sample_citation: Citation
):
    """Verifies composition of conceptual RAG answer with live market quote."""
    query = "What is an IPO and what is Reliance trading at?"
    educational_text = (
        "An Initial Public Offering (IPO) is when an unlisted company makes either a fresh issue "
        "of securities or an offer for sale of its existing securities to the public for the first time [1]."
    )

    resp = composer.compose(
        query=query,
        educational_text=educational_text,
        citations=[sample_citation],
        market_quotes=[sample_quote],
        domain_detected="EQUITY",
    )

    assert resp.grounding_status == "fully_grounded"
    assert "sebi_rag" in resp.grounding_sources
    assert "live_market_data" in resp.grounding_sources
    assert len(resp.citations) == 1
    assert resp.citations[0].doc_id == "sebi_ipo_guide"
    assert resp.market_data is not None
    assert resp.market_data.price == 2985.40

    # Ensure both sections exist in answer
    assert "Initial Public Offering (IPO)" in resp.answer
    assert "₹2,985.40" in resp.answer


def test_causal_market_explainer_attachment(composer: ResponseComposer, sample_quote: MarketQuote):
    """Verifies non-speculative market dynamics explainer for causal queries."""
    resp = composer.compose(
        query="Why did Reliance fall today?",
        market_quotes=[sample_quote],
        is_causal_query=True,
        domain_detected="EQUITY",
    )
    assert CAUSAL_MARKET_EXPLAINER in resp.answer
    assert "Stock prices fluctuate throughout trading sessions" in resp.answer
    assert "Finova AI does not speculate on intraday market rumors" in resp.answer


def test_crypto_card_formatting(composer: ResponseComposer):
    crypto_data = {
        "symbol": "BTC",
        "name": "Bitcoin",
        "price_usd": 68500.25,
        "price_inr": 5750000.0,
        "change_24h": 2.45,
        "provider": "CoinGecko",
        "freshness_status": "live",
        "retrieved_at": "2026-09-11T14:30:00Z",
    }
    card = composer.format_crypto_card(crypto_data)
    assert "$68,500.25" in card
    assert "+2.45%" in card
    assert "₹5,750,000.00" in card
    assert "CoinGecko" in card


def test_personal_finance_calculation_formatting(composer: ResponseComposer):
    calc_data = {
        "type": "budget_50_30_20",
        "title": "50/30/20 Budget Breakdown",
        "income": 60000.0,
        "needs": 30000.0,
        "wants": 18000.0,
        "savings": 12000.0,
    }
    card = composer.format_finance_calc_card(calc_data)
    assert "₹60,000.00" in card
    assert "₹30,000.00" in card
    assert "₹18,000.00" in card
    assert "₹12,000.00" in card
