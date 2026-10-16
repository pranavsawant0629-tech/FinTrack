import re
from typing import Any
from pydantic import BaseModel, Field

from config.settings import settings
from app.rag.embeddings import embedding_manager
from app.rag.vector_store import vector_store


class RetrievedChunk(BaseModel):
    chunk_id: str
    doc_id: str
    chunk_index: int
    text: str
    score: float
    source: str = "SEBI"
    authority_level: str = "Tier 1"
    country: str = "India"
    topic: str = ""
    asset_product: str = ""
    publication_update_date: str = ""
    retrieval_date: str = ""
    url: str = ""
    licensing_usage_status: str = "Official Public Educational Material"
    page_numbers: list[int] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RetrievalResponse(BaseModel):
    query: str
    total_results: int
    chunks: list[RetrievedChunk]


# Verified Indian Financial & Regulatory Terminology & Acronym Dictionary
INDIAN_FINANCIAL_ACRONYMS: dict[str, str] = {
    "SCORES": "SEBI Complaints Redress System",
    "ASBA": "Application Supported by Blocked Amount",
    "STCG": "Short Term Capital Gains",
    "LTCG": "Long Term Capital Gains",
    "TER": "Total Expense Ratio",
    "FPI": "Foreign Portfolio Investor",
    "FII": "Foreign Institutional Investor",
    "REIT": "Real Estate Investment Trust",
    "REITS": "Real Estate Investment Trusts",
    "INVIT": "Infrastructure Investment Trust",
    "INVITS": "Infrastructure Investment Trusts",
    "CKYC": "Central KYC Registry",
    "KYC": "Know Your Customer",
    "DEMAT": "Dematerialized Account",
    "IPO": "Initial Public Offering",
    "OFS": "Offer for Sale",
    "AMC": "Asset Management Company",
    "NAV": "Net Asset Value",
    "SIP": "Systematic Investment Plan",
    "STP": "Systematic Transfer Plan",
    "SWP": "Systematic Withdrawal Plan",
    "AUM": "Assets Under Management",
    "NISM": "National Institute of Securities Markets",
}


def normalize_query_for_retrieval(query: str) -> tuple[str, list[str], set[str]]:
    """
    Cleans query text, extracts key query terms, and resolves Indian regulatory acronyms.
    Returns:
        (dense_query, matched_acronyms, query_keywords)
    """
    cleaned = re.sub(r"[^\w\s\?\.\-]", " ", query.strip())
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    tokens = re.findall(r"\b[A-Za-z0-9]+\b", cleaned)
    matched_acronyms: list[str] = []
    expansions: list[str] = []

    stop_words = {
        "what", "is", "a", "an", "the", "how", "to", "in", "of", "and", "or", "for",
        "does", "do", "can", "tell", "me", "about", "explain", "why", "are", "by", "on"
    }

    query_keywords: set[str] = set()

    for tok in tokens:
        upper_tok = tok.upper()
        if upper_tok in INDIAN_FINANCIAL_ACRONYMS:
            matched_acronyms.append(upper_tok)
            expansions.append(f"{upper_tok} ({INDIAN_FINANCIAL_ACRONYMS[upper_tok]})")
        lower_tok = tok.lower()
        if lower_tok not in stop_words and len(lower_tok) >= 3:
            query_keywords.add(lower_tok)

    if expansions:
        # Augment dense embedding query representation with authoritative definition context
        dense_query = f"{cleaned} " + " ".join(expansions)
    else:
        dense_query = cleaned

    return dense_query, matched_acronyms, query_keywords


class RAGRetriever:
    """
    RAG Retriever layer: performs semantic search over indexed Qdrant knowledge
    with exact-term boosting for Indian regulatory acronyms, chunk deduplication,
    and returns ranked raw chunks with full provenance and citation metadata.
    Does NOT invoke any LLM.
    """

    def __init__(self, top_k: int | None = None, score_threshold: float | None = None):
        self.top_k = top_k or settings.rag_top_k
        self.score_threshold = score_threshold if score_threshold is not None else settings.rag_similarity_threshold

    def retrieve(
        self,
        query: str,
        top_k: int | None = None,
        score_threshold: float | None = None,
        topic: str | None = None,
        authority_level: str | None = None,
    ) -> RetrievalResponse:
        """
        Executes query normalization, query embedding, similarity search in Qdrant,
        lexical/acronym exact-match boosting, and chunk deduplication.
        """
        k = top_k or self.top_k
        thresh = score_threshold if score_threshold is not None else self.score_threshold

        # 1. Normalize query and identify acronyms
        dense_query, matched_acronyms, query_keywords = normalize_query_for_retrieval(query)

        # 2. Embed search query
        query_vector = embedding_manager.embed_query(dense_query)

        # 3. Retrieve broader candidate set from Qdrant with candidate margin
        candidate_limit = max(k * 3, 10)
        candidate_thresh = max(0.40, thresh - 0.08)

        search_results = vector_store.search(
            query_vector=query_vector,
            limit=candidate_limit,
            score_threshold=candidate_thresh,
            topic=topic,
            authority_level=authority_level,
        )

        # 4. Lexical & Exact-Term Acronym Scoring Boost
        ranked_candidates = []
        for res in search_results:
            text_lower = res.text.lower()
            text_upper = res.text.upper()

            exact_boost = 0.0

            # Boost for exact Indian regulatory acronym match (e.g. SCORES, ASBA, REIT, TER, CKYC)
            for acr in matched_acronyms:
                if acr in text_upper:
                    exact_boost += 0.05
                    break

            # Boost for salient non-stopword query keywords
            matched_keywords = sum(1 for kw in query_keywords if kw in text_lower)
            if query_keywords:
                kw_ratio = matched_keywords / len(query_keywords)
                exact_boost += min(0.04, kw_ratio * 0.04)

            final_score = min(1.0, res.score + exact_boost)

            # Filter against true configured threshold
            if final_score >= thresh:
                ranked_candidates.append((final_score, res))

        # Sort by boosted score descending
        ranked_candidates.sort(key=lambda x: x[0], reverse=True)

        # 5. Deduplication of overlapping / near-duplicate chunks from same document
        deduped_results = []
        seen_texts: list[str] = []

        for score, res in ranked_candidates:
            is_duplicate = False
            res_words = set(res.text.lower().split())

            for prev_text in seen_texts:
                prev_words = set(prev_text.lower().split())
                if not prev_words or not res_words:
                    continue
                intersection = len(res_words & prev_words)
                union = len(res_words | prev_words)
                jaccard = intersection / max(1, union)
                if jaccard > 0.65:
                    is_duplicate = True
                    break

            if not is_duplicate:
                deduped_results.append((score, res))
                seen_texts.append(res.text)

            if len(deduped_results) >= k:
                break

        # 6. Format chunks with rich metadata and provenance
        chunks: list[RetrievedChunk] = []
        for score, res in deduped_results:
            meta = res.metadata
            chunk = RetrievedChunk(
                chunk_id=res.chunk_id,
                doc_id=res.doc_id,
                chunk_index=meta.get("chunk_index", 0),
                text=res.text,
                score=round(score, 4),
                source=meta.get("source", "SEBI"),
                authority_level=meta.get("authority_level", "Tier 1"),
                country=meta.get("country", "India"),
                topic=meta.get("topic", ""),
                asset_product=meta.get("asset_product", ""),
                publication_update_date=meta.get("publication_update_date", ""),
                retrieval_date=meta.get("retrieval_date", ""),
                url=meta.get("url", ""),
                licensing_usage_status=meta.get("licensing_usage_status", "Official Public Educational Material"),
                page_numbers=res.page_numbers,
                metadata=meta,
            )
            chunks.append(chunk)

        return RetrievalResponse(
            query=query,
            total_results=len(chunks),
            chunks=chunks,
        )


rag_retriever = RAGRetriever()
