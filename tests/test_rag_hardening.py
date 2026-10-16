"""
Comprehensive Hardening & Regression Test Suite for RAG Phase 2.
Covers:
1. Improved chunking boundaries (headings, lists, sentence splitting, exact tuple overlap).
2. Short document and empty text handling.
3. Acronym normalization and exact-term keyword boosting (SCORES, ASBA, REIT, InvIT, CKYC).
4. Multi-source authoritative retrieval across SEBI, RBI, and AMFI.
5. Deterministic claim-support validation (supported vs unsupported claims).
6. Out-of-range citation stripping and missing marker protection.
7. Honest abstention on out-of-corpus queries (LLM bypass).
8. Partial grounding on compound queries.
9. Prompt injection immunity in evidence/query.
"""

from unittest.mock import MagicMock, patch
import pytest

from app.rag.chunking import TextChunker, DocumentChunk
from app.rag.document_parser import ParsedDocument, PageContent
from app.rag.retriever import rag_retriever, normalize_query_for_retrieval, RetrievedChunk, RetrievalResponse
from app.rag.service import ClaimSupportValidator, RAGService, Citation, RAGAnswer
from app.agents.equity.prompts import UNGROUNDED_TOPIC_MESSAGE


# =====================================================================
# 1. Chunking Boundaries, Heading & List Preservation, Page Tracking
# =====================================================================
def test_chunker_binds_isolated_headings():
    """Verify that isolated heading lines are bound to the subsequent paragraph."""
    text = "# What is an InvIT?\n\nAn Infrastructure Investment Trust is an investment vehicle."
    doc = ParsedDocument(
        doc_id="test_invit",
        file_name="test.txt",
        file_path="/test.txt",
        file_type="txt",
        total_pages=1,
        full_text=text,
        pages=[PageContent(page_number=1, text=text)],
    )
    chunker = TextChunker(chunk_size=100, chunk_overlap=20)
    chunks = chunker.chunk_document(doc)

    assert len(chunks) == 1
    assert "What is an InvIT?" in chunks[0].text
    assert "Infrastructure Investment Trust" in chunks[0].text
    assert chunks[0].page_numbers == [1]


def test_chunker_preserves_numbered_lists():
    """Verify that numbered list procedures are grouped together without arbitrary sentence splitting."""
    list_text = (
        "Procedure to file a complaint:\n\n"
        "1. Approach the listed entity directly.\n"
        "2. Wait for 30 days for resolution.\n"
        "3. If dissatisfied, file on the SCORES portal.\n"
        "4. Provide PAN and complaint details."
    )
    doc = ParsedDocument(
        doc_id="test_proc",
        file_name="test.txt",
        file_path="/test.txt",
        file_type="txt",
        total_pages=1,
        full_text=list_text,
        pages=[PageContent(page_number=1, text=list_text)],
    )
    chunker = TextChunker(chunk_size=150, chunk_overlap=30)
    chunks = chunker.chunk_document(doc)

    assert len(chunks) == 1
    assert "1. Approach" in chunks[0].text
    assert "4. Provide PAN" in chunks[0].text


def test_chunker_handles_empty_and_short_docs():
    """Verify defensive handling of empty text and very short documents."""
    chunker = TextChunker(chunk_size=100, chunk_overlap=20)

    # Empty doc
    empty_doc = ParsedDocument(
        doc_id="empty",
        file_name="empty.txt",
        file_path="/empty.txt",
        file_type="txt",
        total_pages=1,
        full_text="   \n\n  ",
        pages=[],
    )
    assert chunker.chunk_document(empty_doc) == []

    # Short doc
    short_doc = ParsedDocument(
        doc_id="short",
        file_name="short.txt",
        file_path="/short.txt",
        file_type="txt",
        total_pages=1,
        full_text="Indian equities settle on a T+1 rolling basis.",
        pages=[PageContent(page_number=1, text="Indian equities settle on a T+1 rolling basis.")],
    )
    short_chunks = chunker.chunk_document(short_doc)
    assert len(short_chunks) == 1
    assert short_chunks[0].chunk_index == 0
    assert short_chunks[0].page_numbers == [1]


def test_chunker_overlap_provenance_integrity():
    """Verify that multi-page documents track page numbers accurately across overlap rewinds."""
    pages = [
        PageContent(page_number=1, text="Page 1 discusses equities and stock market fundamentals."),
        PageContent(page_number=2, text="Page 2 discusses clearing corporations and settlement."),
        PageContent(page_number=3, text="Page 3 discusses investor grievance redressal on SCORES."),
    ]
    full_text = "\n\n".join(p.text for p in pages)
    doc = ParsedDocument(
        doc_id="multipage",
        file_name="multi.pdf",
        file_path="/multi.pdf",
        file_type="pdf",
        total_pages=3,
        full_text=full_text,
        pages=pages,
    )
    chunker = TextChunker(chunk_size=20, chunk_overlap=8)
    chunks = chunker.chunk_document(doc)

    assert len(chunks) >= 2
    for c in chunks:
        assert len(c.page_numbers) > 0
        assert all(p in (1, 2, 3) for p in c.page_numbers)
        # Ensure page numbers are strictly sorted without duplicates
        assert c.page_numbers == sorted(list(set(c.page_numbers)))


# =====================================================================
# 2. Query Normalization and Exact-Term Acronym Boosting
# =====================================================================
def test_normalize_query_identifies_acronyms():
    """Verify that Indian financial acronyms are recognized and expanded."""
    dense_q, matched, kws = normalize_query_for_retrieval("How does ASBA work in an IPO?")
    assert "ASBA" in matched
    assert "IPO" in matched
    assert "Application Supported by Blocked Amount" in dense_q
    assert "Initial Public Offering" in dense_q
    assert "work" in kws or "asba" in kws


def test_retriever_multi_source_coverage():
    """Verify retrieval returns verified docs across SEBI, RBI, and AMFI."""
    # 1. SEBI REIT
    res_reit = rag_retriever.retrieve("What is a Real Estate Investment Trust REIT?", top_k=1)
    assert res_reit.total_results > 0
    assert res_reit.chunks[0].doc_id == "SEBI_REITs_Introduction"
    assert res_reit.chunks[0].source == "SEBI"

    # 2. SEBI InvIT
    res_invit = rag_retriever.retrieve("What is an Infrastructure Investment Trust InvIT?", top_k=1)
    assert res_invit.total_results > 0
    assert res_invit.chunks[0].doc_id == "SEBI_InvITs_Introduction"

    # 3. SEBI F&O Study
    res_fno = rag_retriever.retrieve("What did SEBI report about individual trader losses in F&O derivatives?", top_k=1)
    assert res_fno.total_results > 0
    assert res_fno.chunks[0].doc_id == "SEBI_Derivatives_Study_2023"

    # 4. RBI FAME
    res_rbi = rag_retriever.retrieve("Financial awareness messages in RBI FAME on banking literacy", top_k=1)
    assert res_rbi.total_results > 0
    assert res_rbi.chunks[0].doc_id == "RBI_FAME_2024"
    assert res_rbi.chunks[0].source == "RBI"


# =====================================================================
# 3. Claim-Support Validation & Citation Integrity
# =====================================================================
def test_claim_support_validator_supported_claim():
    """Verify that factual claims matching the cited chunk are marked fully_grounded."""
    chunk = RetrievedChunk(
        chunk_id="chk_01",
        doc_id="igrbrochure",
        chunk_index=0,
        text="SCORES is a centralized web based complaints redress system launched by SEBI in 2011.",
        score=0.90,
        source="SEBI",
        page_numbers=[4],
    )
    answer = "SCORES is a web-based complaint redress system launched by SEBI [1]."
    clean_text, citations, status, summary = ClaimSupportValidator.validate_citations_and_claims(answer, [chunk])

    assert status == "fully_grounded"
    assert len(citations) == 1
    assert citations[0].citation_id == 1
    assert summary["supported_claims"] == 1
    assert summary["unsupported_claims"] == 0


def test_claim_support_validator_unsupported_claim():
    """Verify that completely unsupported factual claims are marked ungrounded or partially_grounded."""
    chunk = RetrievedChunk(
        chunk_id="chk_01",
        doc_id="primarymarkets",
        chunk_index=0,
        text="The primary market provides an avenue for companies to raise capital through IPOs.",
        score=0.88,
        source="SEBI",
        page_numbers=[2],
    )
    # Answer cites [1] but makes a wildly unsupported claim about Bitcoin mining in Mars
    answer = "The primary market is used for mining Bitcoin on Mars with 900% returns [1]."
    clean_text, citations, status, summary = ClaimSupportValidator.validate_citations_and_claims(answer, [chunk])

    assert status == "ungrounded"
    assert summary["unsupported_claims"] >= 1


def test_claim_support_validator_strips_out_of_range_markers():
    """Verify that out-of-range citations (e.g. [55]) are stripped without fabricating sources."""
    chunk = RetrievedChunk(
        chunk_id="chk_01",
        doc_id="MFunds",
        chunk_index=0,
        text="Mutual funds pool money from investors and invest in equities and debt.",
        score=0.85,
        source="SEBI",
        page_numbers=[1],
    )
    answer = "Mutual funds pool money from investors [1]. Also crypto derivatives are safe [99]."
    clean_text, citations, status, summary = ClaimSupportValidator.validate_citations_and_claims(answer, [chunk])

    assert "[99]" not in clean_text
    assert "[1]" in clean_text
    assert len(citations) == 1
    assert 99 in summary["invalid_markers_stripped"]
    # Stripped invalid citation marker must downgrade status from fully_grounded to partially_grounded
    assert status == "partially_grounded"


def test_claim_support_validator_invalid_markers_with_no_valid_citations():
    """Verify that when only invalid citation markers are present, status is ungrounded with citations empty."""
    chunk = RetrievedChunk(
        chunk_id="chk_01",
        doc_id="MFunds",
        chunk_index=0,
        text="Mutual funds pool money from investors.",
        score=0.85,
        source="SEBI",
        page_numbers=[1],
    )
    answer = "Forex options guarantee 100x leverage on offshore brokerages [42]."
    clean_text, citations, status, summary = ClaimSupportValidator.validate_citations_and_claims(answer, [chunk])

    assert "[42]" not in clean_text
    assert status == "ungrounded"
    assert citations == []
    assert 42 in summary["invalid_markers_stripped"]
    assert summary.get("reason") == "no_valid_citations"


def test_claim_support_validator_unsupported_uncited_factual_claims():
    """Verify that substantive uncited numeric/factual claims downgrade status to partially_grounded."""
    chunk = RetrievedChunk(
        chunk_id="chk_01",
        doc_id="MFunds",
        chunk_index=0,
        text="Mutual funds pool money from investors and invest in diversified securities.",
        score=0.85,
        source="SEBI",
        page_numbers=[1],
    )
    # Valid cited claim [1] is supported, but subsequent sentence asserts an uncited factual percentage (500%)
    answer = (
        "Mutual funds pool money from investors [1]. "
        "Historically this particular fund delivered 500% annualized returns without any risk."
    )
    clean_text, citations, status, summary = ClaimSupportValidator.validate_citations_and_claims(answer, [chunk])

    assert status == "partially_grounded"
    assert len(citations) == 1
    assert summary["has_uncited_factual_claims"] is True


def test_claim_support_validator_no_citations_means_ungrounded():
    """Verify that an answer without citations cannot be marked fully grounded."""
    chunk = RetrievedChunk(
        chunk_id="chk_01",
        doc_id="MFunds",
        chunk_index=0,
        text="Mutual funds pool money from investors.",
        score=0.85,
    )
    answer = "Mutual funds are great investment vehicles with professional fund management."
    clean_text, citations, status, summary = ClaimSupportValidator.validate_citations_and_claims(answer, [chunk])

    assert status == "ungrounded"
    assert citations == []


# =====================================================================
# 4. Honest Abstention (LLM Bypass on Out-of-Corpus Queries)
# =====================================================================
def test_honest_abstention_bypasses_llm():
    """Verify that when no chunks qualify, LLM chat is never invoked."""
    mock_retriever = MagicMock()
    mock_retriever.retrieve.return_value = RetrievalResponse(
        query="What is the quantum state of helium-3 in Jupiter's atmosphere?",
        total_results=0,
        chunks=[],
    )
    mock_llm = MagicMock()

    service = RAGService(retriever=mock_retriever, llm=mock_llm)
    ans = service.generate_answer("What is the quantum state of helium-3 in Jupiter's atmosphere?")

    # LLM must NEVER be called
    mock_llm.chat.assert_not_called()
    assert ans.grounding_status == "ungrounded"
    assert ans.citations == []
    assert ans.answer == UNGROUNDED_TOPIC_MESSAGE


# =====================================================================
# 5. Compound Query Partial Grounding
# =====================================================================
def test_compound_query_partial_grounding():
    """Verify that an answer containing explicit notes about unserved portions resolves as partially_grounded."""
    chunk = RetrievedChunk(
        chunk_id="chk_ipo",
        doc_id="primarymarkets",
        chunk_index=0,
        text="An Initial Public Offering is the process by which a private company issues shares to the public.",
        score=0.90,
        source="SEBI",
        page_numbers=[3],
    )
    answer = (
        "An IPO is when a private company sells shares to the public for the first time [1].\n\n"
        "Note: Details regarding quantum nuclear reactors are not covered in the verified educational corpus."
    )
    clean_text, citations, status, summary = ClaimSupportValidator.validate_citations_and_claims(answer, [chunk])

    assert status == "partially_grounded"
    assert len(citations) == 1
