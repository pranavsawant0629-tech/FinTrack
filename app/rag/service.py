"""
RAG Orchestration Service for Finova AI (Phase 2).
Coordinates semantic retrieval with LLM answer generation, enforcing similarity threshold
evaluation, query normalization, citation extraction, invalid reference stripping,
claim-support validation, and honest abstention.
"""

import logging
import re
from typing import Literal, Any
from pydantic import BaseModel, Field

from config.settings import settings
from app.rag.retriever import RAGRetriever, rag_retriever, RetrievedChunk
from app.llm.llm_client import LLMClient, llm_client
from app.agents.equity.prompts import (
    EQUITY_TUTOR_SYSTEM_PROMPT,
    UNGROUNDED_TOPIC_MESSAGE,
    build_equity_prompt,
)

logger = logging.getLogger(__name__)

# Common English and query stopwords for deterministic claim token analysis
COMMON_STOPWORDS = {
    "the", "is", "are", "and", "in", "of", "to", "a", "an", "for", "on", "with",
    "as", "by", "at", "be", "this", "that", "it", "from", "or", "you", "your",
    "can", "should", "will", "would", "which", "what", "how", "has", "have", "had",
    "there", "their", "they", "our", "all", "also", "then", "into", "more", "other"
}


class Citation(BaseModel):
    """Authoritative citation mapped strictly to verified knowledge chunk."""
    citation_id: int
    chunk_id: str
    doc_id: str
    title: str
    source: str = "SEBI"
    authority_level: str = "Tier 1"
    url: str = ""
    page_numbers: list[int] = Field(default_factory=list)
    similarity_score: float


class RAGAnswer(BaseModel):
    """Structured response from the RAG service."""
    query: str
    answer: str
    grounding_status: Literal["fully_grounded", "partially_grounded", "ungrounded"]
    citations: list[Citation] = Field(default_factory=list)
    retrieved_chunks: list[RetrievedChunk] = Field(default_factory=list)
    model_used: str = ""
    claim_support_summary: dict[str, Any] = Field(default_factory=dict)


class ClaimSupportValidator:
    """
    Deterministic claim-support validation layer.
    Verifies that citations point to actual retrieved evidence and checks
    lexical co-occurrence of factual terms, acronyms, and key claim content
    against the referenced chunks.
    Note: This is a deterministic factual co-occurrence and citation-integrity
    safeguard, not a deep natural language inference (NLI) model.
    """

    @classmethod
    def validate_citations_and_claims(
        cls,
        raw_text: str,
        chunks: list[RetrievedChunk],
    ) -> tuple[str, list[Citation], Literal["fully_grounded", "partially_grounded", "ungrounded"], dict[str, Any]]:
        num_chunks = len(chunks)
        if num_chunks == 0:
            return raw_text.strip(), [], "ungrounded", {"reason": "no_retrieved_evidence"}

        # 1. Discover all citation markers [N]
        found_markers = re.findall(r"\[(\d+)\]", raw_text)
        cleaned_text = raw_text

        valid_indices: set[int] = set()
        invalid_indices: set[int] = set()

        for m_str in set(found_markers):
            idx = int(m_str)
            if 1 <= idx <= num_chunks:
                valid_indices.add(idx)
            else:
                invalid_indices.add(idx)
                # Strip out-of-range / hallucinated citation markers
                cleaned_text = re.sub(rf"\[{idx}\]", "", cleaned_text)

        if not valid_indices:
            return cleaned_text.strip(), [], "ungrounded", {
                "reason": "no_valid_citations",
                "invalid_markers_stripped": list(invalid_indices),
            }

        # 2. Extract and inspect individual claim sentences containing citations
        # Normalize list markers (e.g. "1. ", "2. ") so they do not trigger false sentence breaks
        norm_text = re.sub(r"(^|\n)\s*(\d+)\.\s+", r"\1\2_NUMDOT_ ", cleaned_text)
        raw_sentences = re.split(r"(?<=[.!?])\s+", norm_text)
        sentences = [s.replace("_NUMDOT_", ".") for s in raw_sentences]
        claim_evaluations: list[dict[str, Any]] = []

        supported_count = 0
        total_cited_sentences = 0

        for sentence in sentences:
            sentence_clean = sentence.strip()
            if not sentence_clean:
                continue

            sent_markers = [int(m) for m in re.findall(r"\[(\d+)\]", sentence_clean) if int(m) in valid_indices]
            if not sent_markers:
                continue

            total_cited_sentences += 1

            # Strip citation markers and list numbering from sentence text so indices are not confused for numerical assertions
            sentence_text_only = re.sub(r"\[\d+\]", "", sentence_clean).strip()
            sentence_text_only = re.sub(r"(?:^|\n)\s*\d+[\.\)]\s*", " ", sentence_text_only).strip()

            # Extract content words from sentence
            words = re.findall(r"\b[A-Za-z0-9%₹\-]+\b", sentence_text_only.lower())
            content_words = [w for w in words if len(w) >= 3 and w not in COMMON_STOPWORDS]

            # Extract key factual anchors (numbers, percentages, uppercase acronyms)
            factual_anchors = re.findall(r"\b(?:\d+%?|[A-Z]{2,})\b", sentence_text_only)

            sentence_is_supported = False
            matched_evidence_chunks: list[int] = []

            for cit_idx in sent_markers:
                chunk = chunks[cit_idx - 1]
                chunk_text_lower = chunk.text.lower()
                chunk_text_upper = chunk.text.upper()

                # Calculate content word overlap
                matched_words = [w for w in content_words if w in chunk_text_lower]
                overlap_ratio = len(matched_words) / max(1, len(content_words))

                # Separate numeric/percentage factual assertions from acronyms (ignoring standalone step/list numbers and single-digit ordinals)
                numeric_anchors = [
                    a for a in factual_anchors
                    if re.search(r"\d", a)
                    and not re.search(rf"\bstep\s+{a}\b", sentence_text_only, re.I)
                    and not re.match(r"^[0-9]$", a)
                ]
                
                # Check acronym/term anchors (direct match or expansion match)
                from app.rag.retriever import INDIAN_FINANCIAL_ACRONYMS
                matched_anchors = []
                for a in factual_anchors:
                    a_up = a.upper()
                    if a_up in chunk_text_upper:
                        matched_anchors.append(a)
                    elif a_up in INDIAN_FINANCIAL_ACRONYMS and INDIAN_FINANCIAL_ACRONYMS[a_up].upper() in chunk_text_upper:
                        matched_anchors.append(a)

                # Corroboration rules:
                # 1. If explicit numbers/percentages are asserted (e.g. 900%, 10%), they must appear in evidence
                if numeric_anchors:
                    has_numeric_support = any(num in chunk.text for num in numeric_anchors)
                    if not has_numeric_support:
                        sentence_is_supported = False
                        continue

                # 2. Corroboration via content word overlap and semantic anchors
                if overlap_ratio >= 0.20 or matched_anchors or (len(content_words) <= 2 and overlap_ratio > 0.0):
                    sentence_is_supported = True
                    matched_evidence_chunks.append(cit_idx)

            if sentence_is_supported:
                supported_count += 1

            claim_evaluations.append({
                "sentence": sentence_clean[:120],
                "cited_indices": sent_markers,
                "supported": sentence_is_supported,
                "matched_chunks": matched_evidence_chunks,
            })

        # 3. Assemble validated Citation objects
        citations: list[Citation] = []
        for idx in sorted(valid_indices):
            chunk = chunks[idx - 1]
            title = chunk.metadata.get("title") or chunk.doc_id
            citations.append(
                Citation(
                    citation_id=idx,
                    chunk_id=chunk.chunk_id,
                    doc_id=chunk.doc_id,
                    title=title,
                    source=chunk.source,
                    authority_level=chunk.authority_level,
                    url=chunk.url,
                    page_numbers=chunk.page_numbers,
                    similarity_score=round(chunk.score, 4),
                )
            )

        # 4. Resolve overall Grounding Status
        # Check if the generated answer contains explicit partial/abstention markers
        lower_ans = cleaned_text.lower()
        has_abstention_indicator = (
            "note:" in lower_ans
            or "ask me separately" in lower_ans
            or "not covered in the verified" in lower_ans
            or "does not contain" in lower_ans
            or "insufficient evidence" in lower_ans
        )

        # Check for substantive uncited sentences with factual assertions (numbers, percentages, specific entities)
        has_uncited_factual_claims = False
        for sentence in sentences:
            sentence_clean = sentence.strip()
            # Strip leading list number if present
            sentence_body = re.sub(r"^\s*\d+[\.\)]\s*", "", sentence_clean).strip()
            # Ignore empty sentences, short headings, list indices, or short transitional phrases
            if not sentence_body or len(sentence_body) < 15:
                continue
            has_markers = bool(re.findall(r"\[\d+\]", sentence_clean))
            if not has_markers:
                # Check if this uncited sentence asserts specific numbers or percentages
                has_nums = bool(re.findall(r"\b(?:\d+%?|₹\d+)\b", sentence_body))
                # Exclude purely conversational / disclaimer / concluding / step intro sentences
                is_boilerplate = any(b in sentence_clean.lower() for b in [
                    "ask me", "let me know", "disclaimer", "note:", "feel free", "hope this helps", "in summary", "follow these steps", "here are the steps", "here is how", "these steps will help"
                ])
                if has_nums and not is_boilerplate:
                    # Also ignore step numbers like "step 1", "step 2"
                    non_step_nums = [n for n in re.findall(r"\b(?:\d+%?|₹\d+)\b", sentence_body) if not re.search(rf"\bstep\s+{n}\b", sentence_body, re.I)]
                    if non_step_nums:
                        has_uncited_factual_claims = True
                        break

        if total_cited_sentences == 0:
            status: Literal["fully_grounded", "partially_grounded", "ungrounded"] = "ungrounded"
        elif supported_count == total_cited_sentences:
            if has_abstention_indicator or has_uncited_factual_claims or len(invalid_indices) > 0:
                status = "partially_grounded"
            else:
                status = "fully_grounded"
        elif supported_count > 0:
            status = "partially_grounded"
        else:
            status = "ungrounded"

        summary = {
            "total_cited_claims": total_cited_sentences,
            "supported_claims": supported_count,
            "unsupported_claims": total_cited_sentences - supported_count,
            "invalid_markers_stripped": list(invalid_indices),
            "claims": claim_evaluations,
            "has_uncited_factual_claims": has_uncited_factual_claims,
        }

        return cleaned_text.strip(), citations, status, summary


class RAGService:
    """
    Orchestration service combining retrieval and LLM inference.
    Enforces strict grounding: if retrieval confidence is below threshold,
    bypasses the LLM completely to prevent hallucination.
    """

    def __init__(
        self,
        retriever: RAGRetriever | None = None,
        llm: LLMClient | None = None,
        default_temperature: float = 0.1,
    ):
        self.retriever = retriever or rag_retriever
        self.llm = llm or llm_client
        self.default_temperature = default_temperature

    def generate_answer(
        self,
        query: str,
        top_k: int | None = None,
        score_threshold: float | None = None,
        temperature: float | None = None,
        system_prompt: str | None = None,
        conversation_history: list[dict[str, str]] | None = None,
    ) -> RAGAnswer:
        """
        Execute grounded RAG workflow:
        1. Retrieve candidate chunks with similarity score >= threshold.
        2. If 0 chunks qualify, return ungrounded deterministic fallback (bypass LLM).
        3. If chunks qualify, assemble prompt and generate response via LLM at temperature=0.1.
        4. Validate citation markers against retrieved chunks, rejecting invalid citations.
        5. Evaluate claim support deterministically.
        """
        k = top_k or settings.rag_top_k
        thresh = score_threshold if score_threshold is not None else settings.rag_similarity_threshold
        temp = temperature if temperature is not None else self.default_temperature

        model_name = str(getattr(self.llm, "model", "qwen2.5:7b-instruct"))

        # 1. Retrieval
        try:
            retrieval_res = self.retriever.retrieve(query=query, top_k=k, score_threshold=thresh)
            qualifying_chunks = retrieval_res.chunks
        except Exception as exc:
            logger.error("RAG retrieval failed: %s", exc)
            return RAGAnswer(
                query=query,
                answer=UNGROUNDED_TOPIC_MESSAGE,
                grounding_status="ungrounded",
                citations=[],
                retrieved_chunks=[],
                model_used=model_name,
            )

        # 2. Strict LLM-Bypass for Low Confidence / Out-of-Corpus Queries
        if not qualifying_chunks:
            return RAGAnswer(
                query=query,
                answer=UNGROUNDED_TOPIC_MESSAGE,
                grounding_status="ungrounded",
                citations=[],
                retrieved_chunks=[],
                model_used=model_name,
            )

        # 3. Grounded LLM Generation with multi-turn conversational support
        user_prompt = build_equity_prompt(query, qualifying_chunks)
        history_msgs: list[dict[str, str]] | None = None
        if conversation_history:
            history_msgs = [
                {"role": turn.get("role", "user"), "content": turn.get("content", "")}
                for turn in conversation_history[-4:]
                if turn.get("content") and turn.get("role") in ("user", "assistant")
            ]

        try:
            raw_answer = self.llm.chat(
                message=user_prompt,
                messages=history_msgs,
                system=system_prompt or EQUITY_TUTOR_SYSTEM_PROMPT,
                temperature=temp,
            )
        except Exception as exc:
            logger.error("LLM inference failed: %s", exc)
            return RAGAnswer(
                query=query,
                answer="Finova AI is currently experiencing service disruption connecting to the inference engine. Please try again shortly.",
                grounding_status="ungrounded",
                citations=[],
                retrieved_chunks=qualifying_chunks,
                model_used=model_name,
            )

        # 4. Citation Extraction and Claim-Support Validation
        validated_answer, citations, grounding_status, claim_summary = (
            ClaimSupportValidator.validate_citations_and_claims(raw_answer, qualifying_chunks)
        )

        return RAGAnswer(
            query=query,
            answer=validated_answer,
            grounding_status=grounding_status,
            citations=citations,
            retrieved_chunks=qualifying_chunks,
            model_used=model_name,
            claim_support_summary=claim_summary,
        )


rag_service = RAGService()
