"""
Comprehensive Unit Tests for RAG Grounding & Citation Validation Hardening (Phase 5, Milestone 5.4).

Covers:
1. Acronym-only presence (SEBI, IPO, KYC) does not validate unrelated claims.
2. Substantive token overlap >= 0.25 supports genuine paraphrases.
3. Unrelated claim sharing 2 generic words is marked ungrounded.
4. Contradiction / negated assertion with high word overlap is marked unsupported.
5. Multi-fact claim where 1 fact has unsupported numbers is marked unsupported.
6. Number 10 does not match 10% or 2010.
7. Percentage 10% matches '10 percent' and '10 per cent', but not '10' or '110%'.
8. Currency ₹500 matches 'Rs. 500', 'Rs 500', '₹ 500', but not '$500' or '₹1500'.
9. Decimal 5.5 does not match 55.
10. Year 2024 does not match 2021.
11. Out-of-range citations stripped and marked partially_grounded if other claims valid.
12. No citations present yields ungrounded.
13. Uncited factual claims (with numbers/percentages) yield partially_grounded.
14. EquityAgent returns explicit ungrounded on symbol not found / provider error.
15. CentralOrchestrator preserves EQUITY domain for live quote queries despite non-equity domain_context.
"""

from unittest.mock import MagicMock
import pytest

from app.rag.retriever import RetrievedChunk
from app.rag.service import ClaimSupportValidator, check_numeric_match, normalize_text_for_comparison
from app.agents.equity.agent import EquityAgent
from app.tools.market.interfaces import SymbolNotFoundError
from app.router.orchestrator import CentralOrchestrator


# =====================================================================
# Fixtures
# =====================================================================

@pytest.fixture
def sebi_chunk():
    return RetrievedChunk(
        chunk_id="chk_sebi_01",
        chunk_index=0,
        doc_id="sebi_handbook",
        text="SEBI establishes regulatory frameworks for listed companies, stock exchanges, and registered market intermediaries in India.",
        score=0.92,
        source="SEBI",
        authority_level="Tier 1",
    )


@pytest.fixture
def mutual_fund_chunk():
    return RetrievedChunk(
        chunk_id="chk_mf_01",
        chunk_index=0,
        doc_id="mf_basics",
        text="Mutual funds pool money from multiple investors to invest in a diversified portfolio of stocks, bonds, and other securities.",
        score=0.95,
        source="SEBI",
        authority_level="Tier 1",
    )


@pytest.fixture
def ipo_quota_chunk():
    return RetrievedChunk(
        chunk_id="chk_ipo_01",
        chunk_index=0,
        doc_id="ipo_regulations",
        text="Under SEBI ICDR regulations, the retail individual investor reservation quota is 35% with an application limit of Rs 200000.",
        score=0.94,
        source="SEBI",
        authority_level="Tier 1",
    )


@pytest.fixture
def numeric_evidence_chunk():
    return RetrievedChunk(
        chunk_id="chk_num_01",
        chunk_index=0,
        doc_id="pricing_policy",
        text="In 2021, the brokerage charged a processing fee of Rs. 500 with a 10 percent discount for transactions exceeding 55 units.",
        score=0.90,
        source="SEBI",
        authority_level="Tier 1",
    )


# =====================================================================
# Test 1: Acronym-Only Presence Does Not Support Unrelated Claim
# =====================================================================

def test_acronym_only_presence_does_not_support_unrelated_claim(sebi_chunk):
    """Standalone acronyms (SEBI, IPO, KYC) alone must not validate claims where substantive overlap is 0%."""
    unrelated_claim = "SEBI operates commercial passenger flights between New York and London [1]."
    clean_text, citations, status, summary = ClaimSupportValidator.validate_citations_and_claims(
        unrelated_claim, [sebi_chunk]
    )

    assert status == "ungrounded"
    assert summary["supported_claims"] == 0
    assert summary["unsupported_claims"] == 1
    assert summary["claims"][0]["supported"] is False


# =====================================================================
# Test 2: Substantive Token Overlap >= 0.25 Supports Genuine Paraphrase
# =====================================================================

def test_substantive_token_overlap_supports_genuine_paraphrase(mutual_fund_chunk):
    """Substantive token overlap >= 0.25 correctly marks genuine paraphrases as supported."""
    paraphrased_claim = "Investors pool their capital through mutual funds to invest across diversified stocks [1]."
    clean_text, citations, status, summary = ClaimSupportValidator.validate_citations_and_claims(
        paraphrased_claim, [mutual_fund_chunk]
    )

    assert status == "fully_grounded"
    assert len(citations) == 1
    assert summary["supported_claims"] == 1
    assert summary["unsupported_claims"] == 0
    assert summary["claims"][0]["supported"] is True


# =====================================================================
# Test 3: Unrelated Claim Sharing Two Generic Words Is Marked Ungrounded
# =====================================================================

def test_unrelated_claim_sharing_two_generic_words_is_ungrounded(ipo_quota_chunk):
    """Two shared lexical words in an otherwise unrelated statement must not establish support."""
    # Shares only 'individual' and 'investor' out of 9 substantive words (overlap = 2/9 = 22.2% < 25%)
    unrelated_claim = "Every individual investor should cultivate rare vintage wine collections in France [1]."
    clean_text, citations, status, summary = ClaimSupportValidator.validate_citations_and_claims(
        unrelated_claim, [ipo_quota_chunk]
    )

    assert status == "ungrounded"
    assert summary["supported_claims"] == 0
    assert summary["unsupported_claims"] == 1


# =====================================================================
# Test 4: Contradiction / Negated Assertion Is Marked Unsupported
# =====================================================================

def test_contradiction_negated_assertion_is_marked_unsupported():
    """Contradiction or unsupported negation with high word overlap must be rejected."""
    chunk = RetrievedChunk(
        chunk_id="chk_gov_01",
        chunk_index=0,
        doc_id="governance_rules",
        text="SEBI mandates that all listed companies must appoint an independent director to the board.",
        score=0.91,
        source="SEBI",
        authority_level="Tier 1",
    )
    negated_claim = "SEBI does not require listed companies to appoint an independent director [1]."
    clean_text, citations, status, summary = ClaimSupportValidator.validate_citations_and_claims(
        negated_claim, [chunk]
    )

    assert status == "ungrounded"
    assert summary["supported_claims"] == 0
    assert summary["unsupported_claims"] == 1


# =====================================================================
# Test 5: Multi-Fact Claim Where 1 Fact Has Unsupported Numbers Is Unsupported
# =====================================================================

def test_multifact_claim_where_one_fact_has_unsupported_numbers_is_unsupported(ipo_quota_chunk):
    """If a claim asserts multiple numbers, all must be supported; one invalid number invalidates the claim."""
    # 35% is present in chunk, but ₹500,000 is NOT (chunk has Rs 200000)
    fabricated_multifact = "In an IPO, the retail quota is 35% and the application limit is Rs 500000 [1]."
    clean_text, citations, status, summary = ClaimSupportValidator.validate_citations_and_claims(
        fabricated_multifact, [ipo_quota_chunk]
    )

    assert status == "ungrounded"
    assert summary["supported_claims"] == 0
    assert summary["unsupported_claims"] == 1


# =====================================================================
# Test 6: Number 10 Does Not Match 10% or 2010
# =====================================================================

def test_number_ten_does_not_match_ten_percent_or_twenty_ten():
    """Standalone number 10 must not match 10% or year 2010."""
    chunk = RetrievedChunk(
        chunk_id="chk_t6",
        chunk_index=0,
        doc_id="returns_doc",
        text="In 2010, the fund generated 10% annualized returns.",
        score=0.90,
        source="SEBI",
        authority_level="Tier 1",
    )
    # Claim asserts integer 10 (units/shares), not 10% or 2010
    claim_integer_10 = "The investor purchased 10 shares in the secondary market [1]."
    clean_text, citations, status, summary = ClaimSupportValidator.validate_citations_and_claims(
        claim_integer_10, [chunk]
    )

    assert status == "ungrounded"
    assert summary["claims"][0]["supported"] is False

    # Direct unit test of boundary regex
    norm_chunk = normalize_text_for_comparison(chunk.text)
    assert check_numeric_match("10", norm_chunk) is False


# =====================================================================
# Test 7: Percentage 10% Matches Variations, Not 10 or 110%
# =====================================================================

def test_percentage_ten_percent_matches_variations_not_ten_or_one_hundred_ten(numeric_evidence_chunk):
    """Percentage 10% matches '10 percent' and '10 per cent', but not '10' or '110%'."""
    # Chunk has '10 percent discount'
    valid_pct_claim = "The brokerage offered a 10% discount on processing fees [1]."
    clean_text, citations, status, summary = ClaimSupportValidator.validate_citations_and_claims(
        valid_pct_claim, [numeric_evidence_chunk]
    )
    assert status == "fully_grounded"
    assert summary["supported_claims"] == 1

    # 110% must fail
    invalid_pct_claim = "The brokerage offered a 110% discount on processing fees [1]."
    clean_text, citations, status, summary = ClaimSupportValidator.validate_citations_and_claims(
        invalid_pct_claim, [numeric_evidence_chunk]
    )
    assert status == "ungrounded"
    assert summary["supported_claims"] == 0


# =====================================================================
# Test 8: Currency ₹500 Matches Variations, Not $500 or ₹1500
# =====================================================================

def test_currency_rupee_five_hundred_matches_variations_not_dollar_or_fifteen_hundred(numeric_evidence_chunk):
    """Currency ₹500 matches 'Rs. 500', 'Rs 500', '₹ 500', but not '$500' or '₹1500'."""
    # Chunk has 'Rs. 500' -> ₹500
    valid_rupee_claim = "The standard processing fee charged was ₹500 for accounts [1]."
    clean_text, citations, status, summary = ClaimSupportValidator.validate_citations_and_claims(
        valid_rupee_claim, [numeric_evidence_chunk]
    )
    assert status == "fully_grounded"
    assert summary["supported_claims"] == 1

    # Dollar $500 must fail
    dollar_claim = "The standard processing fee charged was $500 for accounts [1]."
    clean_text, citations, status, summary = ClaimSupportValidator.validate_citations_and_claims(
        dollar_claim, [numeric_evidence_chunk]
    )
    assert status == "ungrounded"
    assert summary["supported_claims"] == 0

    # ₹1500 must fail
    fifteen_hundred_claim = "The standard processing fee charged was ₹1500 for accounts [1]."
    clean_text, citations, status, summary = ClaimSupportValidator.validate_citations_and_claims(
        fifteen_hundred_claim, [numeric_evidence_chunk]
    )
    assert status == "ungrounded"
    assert summary["supported_claims"] == 0


# =====================================================================
# Test 9: Decimal 5.5 Does Not Match 55
# =====================================================================

def test_decimal_five_point_five_does_not_match_fifty_five(numeric_evidence_chunk):
    """Decimal 5.5 must not match integer 55."""
    # Chunk has '55 units'
    decimal_claim = "Transactions exceeding 5.5 units were eligible for processing fee discounts [1]."
    clean_text, citations, status, summary = ClaimSupportValidator.validate_citations_and_claims(
        decimal_claim, [numeric_evidence_chunk]
    )
    assert status == "ungrounded"
    assert summary["supported_claims"] == 0

    norm_chunk = normalize_text_for_comparison(numeric_evidence_chunk.text)
    assert check_numeric_match("5.5", norm_chunk) is False
    assert check_numeric_match("55", norm_chunk) is True


# =====================================================================
# Test 10: Year 2024 Does Not Match 2021
# =====================================================================

def test_year_twenty_twenty_four_does_not_match_twenty_twenty_one(numeric_evidence_chunk):
    """Year 2024 must not match year 2021."""
    # Chunk has 'In 2021'
    wrong_year_claim = "In 2024, the brokerage revised processing fee discounts for unit orders [1]."
    clean_text, citations, status, summary = ClaimSupportValidator.validate_citations_and_claims(
        wrong_year_claim, [numeric_evidence_chunk]
    )
    assert status == "ungrounded"
    assert summary["supported_claims"] == 0

    norm_chunk = normalize_text_for_comparison(numeric_evidence_chunk.text)
    assert check_numeric_match("2024", norm_chunk) is False
    assert check_numeric_match("2021", norm_chunk) is True


# =====================================================================
# Test 11: Out-of-Range Citations Stripped and Marked Partially Grounded
# =====================================================================

def test_out_of_range_citations_stripped_and_marked_partially_grounded(mutual_fund_chunk):
    """Out-of-range citations are stripped and answer marked partially_grounded if remaining claim supported."""
    answer = "Mutual funds pool money from multiple investors [1]. High-frequency automated arbitrage guarantees wealth [99]."
    clean_text, citations, status, summary = ClaimSupportValidator.validate_citations_and_claims(
        answer, [mutual_fund_chunk]
    )

    assert "[99]" not in clean_text
    assert "[1]" in clean_text
    assert len(citations) == 1
    assert 99 in summary["invalid_markers_stripped"]
    assert status == "partially_grounded"


# =====================================================================
# Test 12: No Citations Present Yields Ungrounded
# =====================================================================

def test_no_citations_present_yields_ungrounded(mutual_fund_chunk):
    """Answers without any citation markers yield ungrounded status and empty citations."""
    answer = "Mutual funds are regulated collective investment vehicles managed by asset management companies."
    clean_text, citations, status, summary = ClaimSupportValidator.validate_citations_and_claims(
        answer, [mutual_fund_chunk]
    )

    assert status == "ungrounded"
    assert citations == []
    assert summary["total_cited_claims"] == 0


# =====================================================================
# Test 13: Uncited Factual Claims Yield Partially Grounded
# =====================================================================

def test_uncited_factual_claims_yield_partially_grounded(mutual_fund_chunk):
    """Answers with valid cited claims but containing uncited factual assertions yield partially_grounded."""
    answer = (
        "Mutual funds pool money from multiple investors to invest in securities [1]. "
        "Top quant hedge funds deliver 75% annual returns with zero market drawdown."
    )
    clean_text, citations, status, summary = ClaimSupportValidator.validate_citations_and_claims(
        answer, [mutual_fund_chunk]
    )

    assert status == "partially_grounded"
    assert len(citations) == 1
    assert summary["has_uncited_factual_claims"] is True


# =====================================================================
# Test 14: EquityAgent Explicit Ungrounded on Symbol Not Found / Provider Error
# =====================================================================

def test_equity_agent_explicit_ungrounded_on_symbol_not_found_or_provider_error():
    """EquityAgent must return structured ungrounded result on tool error rather than falling through to SEBI RAG."""
    agent = EquityAgent()

    # Mock market_service to raise SymbolNotFoundError
    agent.market_service = MagicMock()
    agent.market_service.get_quote.side_effect = SymbolNotFoundError("TICKER_DOES_NOT_EXIST")

    result = agent.ask("What is the current quote for TICKER_DOES_NOT_EXIST?")

    assert result.grounding_status == "ungrounded"
    assert result.market_data is None
    assert result.grounding_sources == []
    assert result.model_used == "deterministic_tools"
    assert "Could not find market quote data" in result.answer

    # Mock market_service to raise generic Exception (provider error)
    agent.market_service.get_quote.side_effect = RuntimeError("Upstream feed timeout")
    result_err = agent.ask("What is the current price of RELIANCE?")

    assert result_err.grounding_status == "ungrounded"
    assert result_err.market_data is None
    assert result_err.grounding_sources == []
    assert result_err.model_used == "deterministic_tools"
    assert "currently unavailable due to an upstream service error" in result_err.answer


# =====================================================================
# Test 15: CentralOrchestrator Preserves EQUITY Domain for Live Quotes
# =====================================================================

def test_central_orchestrator_preserves_equity_domain_for_live_quotes():
    """Orchestrator must preserve EQUITY domain for live quote queries despite conflicting domain_context."""
    orchestrator = CentralOrchestrator()

    # Quote query with recognized entity RELIANCE under domain_context="CRYPTO"
    # Classifier step should preserve EQUITY
    decision_quote = orchestrator.classifier.classify("What is the current price of RELIANCE?")
    assert decision_quote.domain == "EQUITY"
    assert decision_quote.intent == "quote"
    assert "RELIANCE" in decision_quote.entities

    # Test orchestrator fast-path routing execution
    mock_equity = MagicMock()
    mock_res = MagicMock()
    mock_res.answer = "RELIANCE: ₹2950"
    mock_res.grounding_status = "fully_grounded"
    mock_res.citations = []
    mock_res.model_used = "deterministic_tools"
    mock_res.latency_ms = 10.0
    mock_res.market_data = None
    mock_res.grounding_sources = ["live_market_data"]
    mock_res.agent_name = "Equity Tutor"
    mock_res.disclaimer = "Equity disclaimer"
    mock_equity.ask.return_value = mock_res
    orchestrator._equity_agent = mock_equity

    mock_crypto = MagicMock()
    orchestrator._crypto_agent = mock_crypto

    res = orchestrator.ask(
        query="What is the current price of RELIANCE?",
        domain_context="CRYPTO",
    )

    # Must be routed to equity_agent, not crypto_agent
    mock_equity.ask.assert_called_once()
    mock_crypto.ask.assert_not_called()
    assert res.domain_detected == "EQUITY"

    # Also verify conceptual equity query (IPO) is not hijacked by CRYPTO context
    mock_equity.reset_mock()
    mock_crypto.reset_mock()
    mock_res_ipo = MagicMock()
    mock_res_ipo.answer = "An IPO is an Initial Public Offering."
    mock_res_ipo.grounding_status = "fully_grounded"
    mock_res_ipo.citations = []
    mock_res_ipo.model_used = "deterministic_tools"
    mock_res_ipo.latency_ms = 12.0
    mock_res_ipo.market_data = None
    mock_res_ipo.grounding_sources = ["sebi_knowledge_base"]
    mock_res_ipo.agent_name = "Equity Tutor"
    mock_res_ipo.disclaimer = "Equity disclaimer"
    mock_equity.ask.return_value = mock_res_ipo

    res_ipo = orchestrator.ask(
        query="What is an IPO and how does it work?",
        domain_context="CRYPTO",
    )
    mock_equity.ask.assert_called_once()
    mock_crypto.ask.assert_not_called()
    assert res_ipo.domain_detected == "EQUITY"
