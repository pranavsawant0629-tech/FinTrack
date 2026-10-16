"""
Deterministic Multi-Turn Context and Anaphoric Query Resolver for Finova AI.
Phase 3: Answer Quality, Routing & Multi-Turn Context.

Resolves conversational references (e.g. 'it', 'its', 'that stock', 'the previous answer', 'compare it with X')
strictly against available preceding conversation history without inventing missing tickers, dates, or user preferences.
Zero LLM calls, deterministic execution in sub-millisecond time (<0.5ms).
"""

from __future__ import annotations

import re
from typing import Any
from pydantic import BaseModel, Field

from app.tools.market.intent import EQUITY_ALIASES, INDEX_ALIASES
from app.router.classifier import CRYPTO_ALIASES

# Anaphoric reference patterns
PRONOUN_REFERENCE_PATTERNS = [
    re.compile(r"\b(?:what\s+about\s+its?|how\s+about\s+its?|what\s+is\s+its?|tell\s+me\s+about\s+its?)\b", re.IGNORECASE),
    re.compile(r"\b(?:compare\s+it\s+with|compare\s+that\s+with|versus\s+it|vs\.?\s+it)\b", re.IGNORECASE),
    re.compile(r"\b(?:that\s+stock|this\s+stock|the\s+stock|that\s+company|this\s+company|the\s+company|that\s+asset|this\s+asset|the\s+same\s+stock)\b", re.IGNORECASE),
    re.compile(r"\b(?:for\s+it|about\s+it|of\s+it|on\s+it|in\s+it|to\s+it|with\s+it)\b", re.IGNORECASE),
    re.compile(r"\b(?:is\s+it|does\s+it|can\s+it|will\s+it|why\s+is\s+it)\b", re.IGNORECASE),
    re.compile(r"\b(?:its?\s+(?:pe\s+ratio|p/e|market\s+cap|52\s*week\s*high|52\s*week\s*low|price|quote|fundamentals?|trend|performance|breakeven|strike))\b", re.IGNORECASE),
]

# Topic reference patterns (e.g. "What are the tax implications of that?", "How does it work?")
TOPIC_REFERENCE_PATTERNS = [
    re.compile(r"\b(?:of\s+that|for\s+that|about\s+that|tax\s+implications\s+of\s+that|rules\s+for\s+that)\b", re.IGNORECASE),
    re.compile(r"\b(?:how\s+does\s+it\s+work|what\s+is\s+the\s+process\s+for\s+it|eligibility\s+for\s+it)\b", re.IGNORECASE),
]


class ResolvedContext(BaseModel):
    """Structured resolution of multi-turn query context."""
    original_query: str
    resolved_query: str
    has_reference: bool = False
    resolved_entity: str | None = None
    resolved_topic: str | None = None
    resolved_domain: str | None = None
    confidence: float = 1.0
    reference_turn_index: int | None = None


class ContextualQueryResolver:
    """
    Deterministic resolver for follow-up questions relying on earlier turns.
    Extracts entities and topics strictly from preceding conversation history.
    """

    @classmethod
    def _extract_entities_from_text(cls, text: str) -> list[str]:
        """Extract recognized equity and crypto entities from text."""
        upper = text.upper()
        found: list[str] = []

        # 1. Equity Indices
        for alias, canonical in sorted(INDEX_ALIASES.items(), key=lambda x: -len(x[0])):
            if re.search(rf"\b{re.escape(alias)}\b", upper):
                if canonical not in found:
                    found.append(canonical)

        # 2. Equities
        for alias, canonical in sorted(EQUITY_ALIASES.items(), key=lambda x: -len(x[0])):
            if re.search(rf"\b{re.escape(alias)}\b", upper):
                if canonical not in found:
                    found.append(canonical)

        # 3. Crypto
        for alias, canonical in sorted(CRYPTO_ALIASES.items(), key=lambda x: -len(x[0])):
            if re.search(rf"\b{re.escape(alias)}\b", upper):
                if canonical not in found:
                    found.append(canonical)

        return found

    @classmethod
    def _extract_topic_from_text(cls, text: str) -> str | None:
        """Extract prominent financial educational topic from text if present."""
        lower = text.lower()
        topic_patterns = [
            ("Initial Public Offering", ["ipo", "initial public offering"]),
            ("Mutual Funds & SIP", ["mutual fund", "sip", "systematic investment plan"]),
            ("Exchange Traded Funds", ["etf", "exchange traded fund"]),
            ("SCORES & Investor Grievance", ["scores", "grievance", "complaint"]),
            ("Real Estate Investment Trusts", ["reit", "real estate investment trust"]),
            ("Infrastructure Investment Trusts", ["invit", "infrastructure investment trust"]),
            ("Demat & Account Opening", ["demat", "ckyc", "trading account"]),
            ("Options & Derivatives", ["call option", "put option", "option", "futures", "f&o", "derivative"]),
            ("Budgeting & Personal Finance", ["50/30/20", "emergency fund", "budget", "cibil"]),
        ]
        for topic_name, keywords in topic_patterns:
            if any(re.search(rf"\b{re.escape(kw)}\b", lower) for kw in keywords):
                return topic_name
        return None

    @classmethod
    def resolve_context(
        cls,
        query: str,
        conversation_history: list[dict[str, str]] | None = None,
    ) -> ResolvedContext:
        """
        Inspects query for anaphoric pronouns or references and resolves them
        against preceding conversation turns without inventing facts.
        """
        trimmed = query.strip()
        if not trimmed:
            return ResolvedContext(original_query=query, resolved_query=query)

        # If no conversation history is provided, return original query cleanly
        if not conversation_history:
            return ResolvedContext(original_query=trimmed, resolved_query=trimmed)

        # 1. Check if the current query has self-contained entities already
        current_entities = cls._extract_entities_from_text(trimmed)

        # 2. Detect if anaphoric pronoun reference exists
        has_pronoun = any(bool(p.search(trimmed)) for p in PRONOUN_REFERENCE_PATTERNS)
        has_topic_ref = any(bool(p.search(trimmed)) for p in TOPIC_REFERENCE_PATTERNS)

        # Check for isolated short pronouns: e.g. "What is its price?", "Explain it", "Compare with TCS"
        has_short_pronoun = bool(re.search(r"\b(?:it|its|that|this)\b", trimmed, re.IGNORECASE))
        has_missing_entity_comparison = bool(re.search(r"\b(?:compare\s+(?:with|to)|vs\.?|versus)\s+([A-Za-z0-9&]+)\b", trimmed, re.IGNORECASE)) and len(current_entities) == 1

        is_anaphoric = has_pronoun or has_topic_ref or (has_short_pronoun and not current_entities) or has_missing_entity_comparison

        if not is_anaphoric:
            return ResolvedContext(
                original_query=trimmed,
                resolved_query=trimmed,
                has_reference=False,
                resolved_entity=current_entities[0] if current_entities else None,
            )

        # 3. Scan preceding conversation history in reverse order (most recent turn first)
        antecedent_entity: str | None = None
        antecedent_topic: str | None = None
        reference_turn_idx: int | None = None

        for idx, turn in enumerate(reversed(conversation_history)):
            content = turn.get("content", "")
            turn_entities = cls._extract_entities_from_text(content)
            if turn_entities and not antecedent_entity:
                antecedent_entity = turn_entities[0]
                reference_turn_idx = len(conversation_history) - 1 - idx

            turn_topic = cls._extract_topic_from_text(content)
            if turn_topic and not antecedent_topic:
                antecedent_topic = turn_topic

            if antecedent_entity and antecedent_topic:
                break

        # 4. If no antecedent could be verified from history, cleanly leave query unchanged
        if not antecedent_entity and not antecedent_topic:
            return ResolvedContext(
                original_query=trimmed,
                resolved_query=trimmed,
                has_reference=True,
                resolved_entity=None,
                resolved_topic=None,
                confidence=0.5,
            )

        # 5. Deterministically construct resolved query
        resolved_q = trimmed

        if antecedent_entity:
            # Handle "Compare it with X" or "Compare with X"
            if re.search(r"\bcompare\s+(?:it\s+with|that\s+with|with)\s+([A-Za-z0-9&]+)\b", resolved_q, re.IGNORECASE):
                resolved_q = re.sub(
                    r"\bcompare\s+(?:it\s+with|that\s+with|with)\s+([A-Za-z0-9&]+)\b",
                    rf"Compare {antecedent_entity} and \1",
                    resolved_q,
                    flags=re.IGNORECASE,
                )
            # Handle "What about its PE / price / 52 week high"
            elif re.search(r"\b(?:what\s+about|how\s+about|what\s+is)\s+its?\s+([A-Za-z0-9\s/]+)\b", resolved_q, re.IGNORECASE):
                resolved_q = re.sub(
                    r"\b(?:what\s+about|how\s+about|what\s+is)\s+its?\s+([A-Za-z0-9\s/]+)\b",
                    rf"What is the \1 of {antecedent_entity}",
                    resolved_q,
                    flags=re.IGNORECASE,
                )
            # Replace references like "that stock", "this stock", "the company", "that asset"
            elif re.search(r"\b(?:that\s+stock|this\s+stock|the\s+stock|that\s+company|this\s+company|the\s+company|that\s+asset)\b", resolved_q, re.IGNORECASE):
                resolved_q = re.sub(
                    r"\b(?:that\s+stock|this\s+stock|the\s+stock|that\s+company|this\s+company|the\s+company|that\s+asset)\b",
                    antecedent_entity,
                    resolved_q,
                    flags=re.IGNORECASE,
                )
            # General "it" replacement when no entity was present
            elif not current_entities and re.search(r"\b(?:it|its)\b", resolved_q, re.IGNORECASE):
                resolved_q = re.sub(r"\bits\b", f"{antecedent_entity}'s", resolved_q, flags=re.IGNORECASE)
                resolved_q = re.sub(r"\bit\b", antecedent_entity, resolved_q, flags=re.IGNORECASE)

        elif antecedent_topic:
            # Replace topic pronouns (e.g. "What are the tax implications of that?")
            if re.search(r"\b(?:of\s+that|for\s+that|about\s+that)\b", resolved_q, re.IGNORECASE):
                resolved_q = re.sub(
                    r"\b(?:of\s+that|for\s+that|about\s+that)\b",
                    f"for {antecedent_topic}",
                    resolved_q,
                    flags=re.IGNORECASE,
                )
            elif re.search(r"\bit\b", resolved_q, re.IGNORECASE):
                resolved_q = re.sub(r"\bit\b", antecedent_topic, resolved_q, flags=re.IGNORECASE)

        return ResolvedContext(
            original_query=trimmed,
            resolved_query=resolved_q,
            has_reference=True,
            resolved_entity=antecedent_entity,
            resolved_topic=antecedent_topic,
            reference_turn_index=reference_turn_idx,
            confidence=0.95,
        )


contextual_resolver = ContextualQueryResolver()
