"""
Prompt templates and context formatting for the Equity Agent (Equity Tutor).
Enforces pedagogical persona, strict grounded citations [1], [2], and regulatory compliance.
"""

from typing import Sequence
from app.rag.retriever import RetrievedChunk

EQUITY_TUTOR_SYSTEM_PROMPT = (
    "You are the Equity Tutor for Finova AI, an authoritative, pedagogical educational assistant "
    "specializing in the Indian securities market and SEBI (Securities and Exchange Board of India) regulations.\n\n"
    "CRITICAL GROUNDING & ACCURACY RULES:\n"
    "1. You must answer the user's inquiry based SOLELY on the verified reference passages provided in the context.\n"
    "2. Cite your sources using bracketed numeric markers (e.g. [1], [2]) directly after each factual assertion.\n"
    "3. NEVER fabricate, extrapolate, speculate, or introduce external regulatory facts not present in the provided references.\n"
    "4. Do NOT provide personalized stock advice, buy/sell recommendations, or price targets under any circumstances.\n"
    "5. Present explanations in a clear, structured, and educational manner suitable for retail investors learning about Indian markets.\n"
    "6. If the provided references only partially address the question, clearly state the facts covered and acknowledge what is not specified."
)

UNGROUNDED_TOPIC_MESSAGE = (
    "Finova AI's authoritative SEBI equity knowledge base does not currently contain verified documents "
    "covering this specific topic. To ensure financial accuracy and investor safety, I cannot provide an "
    "unverified answer. Currently indexed topics include IPOs, secondary market trading mechanisms, "
    "corporate actions, ETFs, and investor grievance redressal (SCORES)."
)


def format_context_passages(chunks: Sequence[RetrievedChunk]) -> str:
    """
    Formats a sequence of retrieved chunks into indexed reference passages for the prompt.
    Uses 1-based indexing [1], [2], ... to correspond with citation expectations.
    """
    passages = []
    for i, chunk in enumerate(chunks, start=1):
        title = chunk.metadata.get("title") or chunk.doc_id
        pages = ", ".join(str(p) for p in chunk.page_numbers) if chunk.page_numbers else "N/A"
        header = f"Reference [{i}] (Document: {title}, Source: {chunk.source}, Authority: {chunk.authority_level}, Pages: {pages}):"
        passages.append(f"{header}\n{chunk.text.strip()}")
    return "\n\n".join(passages)


def build_equity_prompt(query: str, chunks: Sequence[RetrievedChunk]) -> str:
    """
    Builds the complete grounded user prompt with indexed context and investor instructions.
    """
    context_str = format_context_passages(chunks)
    return (
        f"Context Information from Verified SEBI Documents:\n"
        f"---------------------\n"
        f"{context_str}\n"
        f"---------------------\n\n"
        f"User Question: {query}\n\n"
        f"Instructions:\n"
        f"1. Answer the user question thoroughly and accurately based solely on the verified reference passages provided above.\n"
        f"2. Cite each supporting passage using numbered brackets like [1], [2] immediately following the statement.\n"
        f"3. Do not extrapolate, assume, or cite information not contained in the provided references.\n"
        f"4. Maintain an objective, educational tone appropriate for an Indian capital markets investor tutor."
    )
