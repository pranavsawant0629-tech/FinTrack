"""
Deterministic Rule-Guided Query Decomposer for Finova AI.

Splits multi-intent, compound, and comparative queries into isolated, structured
sub-tasks without LLM latency. Handles:
1. Conceptual + Market data queries (e.g. "What is an IPO and what is Reliance trading at?")
2. Cross-domain queries (e.g. "What is P/E and how should I budget my income?")
3. Multi-entity comparative queries (e.g. "Compare Reliance and TCS price")
4. Single-intent passthrough queries (preserves atomic query structure)
"""

from __future__ import annotations

import re
from app.router.classifier import FastPathClassifier, fast_path_classifier
from app.router.models import DecompositionPlan, SubTask

# Split boundaries: compound coordinators, clause dividers, and punctuation
CONJUNCTION_SPLIT_REGEX = re.compile(
    r"\s*(?:"
    r"\band\s+also\b|"
    r"\bas\s+well\s+as\b|"
    r"\balong\s+with\b|"
    r"\bwhile\s+also\b|"
    r",\s*and\b|"
    r"\b\?\s*and\b|"
    r"\b\?\s*|"
    r";\s*|"
    r"\band(?=\s+(?:what|how|why|tell|show|give|is|can|calculate|explain|does|do)\b)|"
    r",\s*(?=(?:what|how|why|tell|show|give|is|can|calculate|explain)\b)|"
    r",\s*(?=(?:[A-Za-z0-9&]+\s+(?:price|quote|cmp))\b)|"
    r",\s*(?=\b(?:calculate|sip|50/30/20|budget)\b)"
    r")\s*",
    re.IGNORECASE,
)

# Comparative trigger pattern (e.g. "Compare X and Y", "Price of X and Y")
COMPARATIVE_PATTERN = re.compile(
    r"\b(?:compare|comparison|versus|vs\.?|difference\s+between|differences\s+between|distinguish\s+between)\b",
    re.IGNORECASE,
)

# Educational comparative concepts that must remain atomic single-intent
EDUCATIONAL_COMPARISON_PATTERN = re.compile(
    r"\b(?:difference\s+between|differences\s+between|distinguish\s+between|"
    r"compare\s+(?:the\s+difference|and\s+contrast|growth\s+and\s+value|primary\s+and\s+secondary|equity\s+and\s+debt)|"
    r"pros\s+and\s+cons|advantages\s+and\s+disadvantages|"
    r"between\s+[a-z\s]+\s+and\s+[a-z\s]+)\b",
    re.IGNORECASE,
)


class QueryDecomposer:
    """Decomposes user queries into independent executable sub-tasks."""

    def __init__(self, classifier: FastPathClassifier | None = None) -> None:
        self.classifier = classifier or fast_path_classifier

    def decompose(self, query: str) -> DecompositionPlan:
        """Decompose a query into a structured DecompositionPlan."""
        trimmed = query.strip()
        if not trimmed:
            return DecompositionPlan(original_query=query, is_compound=False, sub_tasks=[])

        # 1. First classify the query as a whole
        full_decision = self.classifier.classify(trimmed)

        # 2. Check for educational comparative queries that must NOT be split into sub-tasks
        has_educational_interrogative = bool(re.search(
            r"\b(?:what\s+is|what\s+are|explain|how\s+does|how\s+do|define|how\s+should|calculate|pros\s+and\s+cons|difference\s+between|differences\s+between|distinguish\s+between)\b",
            trimmed,
            re.IGNORECASE,
        ))
        is_comparative_concept = bool(EDUCATIONAL_COMPARISON_PATTERN.search(trimmed))

        if is_comparative_concept and (len(full_decision.entities) == 0 or full_decision.intent == "educational_concept"):
            target_entity = full_decision.entities[0] if full_decision.entities else None
            return DecompositionPlan(
                original_query=trimmed,
                is_compound=False,
                sub_tasks=[
                    SubTask(
                        task_id="task_1",
                        domain=full_decision.domain,
                        intent="educational_concept",
                        query_slice=trimmed,
                        target_entity=target_entity,
                        status="pending",
                    )
                ],
            )

        # 3. Check for explicit comparative queries for market quotes (e.g. "Compare Reliance and TCS price", "Compare BTC and ETH")
        is_explicit_comparison = bool(COMPARATIVE_PATTERN.search(trimmed)) and len(full_decision.entities) > 1 and not has_educational_interrogative
        is_pure_multi_quote = (
            len(full_decision.entities) > 1
            and bool(re.search(r"\b(?:prices?|quotes?|cmps?|trading\s+at)\b", trimmed, re.IGNORECASE))
            and not has_educational_interrogative
        )

        if (is_explicit_comparison or is_pure_multi_quote) and len(full_decision.entities) > 1:
            sub_tasks: list[SubTask] = []
            for idx, entity in enumerate(full_decision.entities, start=1):
                domain = "CRYPTO" if entity in ("BTC", "ETH", "SOL", "USDT", "DOGE", "XRP", "ADA", "BNB") else "EQUITY"
                sub_tasks.append(
                    SubTask(
                        task_id=f"task_{idx}",
                        domain=domain,
                        intent="quote",
                        query_slice=f"Price quote for {entity}",
                        target_entity=entity,
                        status="pending",
                    )
                )
            return DecompositionPlan(
                original_query=trimmed,
                is_compound=True,
                sub_tasks=sub_tasks,
            )

        # 4. Attempt Syntactic Clause Splitting on Conjunctions / Punctuation
        raw_clauses = [c.strip() for c in CONJUNCTION_SPLIT_REGEX.split(trimmed) if len(c.strip()) > 2]

        if len(raw_clauses) >= 2:
            decomposed_tasks: list[SubTask] = []
            seen_intents: set[tuple[str, str, str | None]] = set()

            for idx, clause in enumerate(raw_clauses, start=1):
                # Clean up any leftover punctuation or leading conjunction words
                cleaned_clause = re.sub(r"^(?:and|also|while|then|tell\s+me|what\s+about)\s+", "", clause, flags=re.IGNORECASE).strip()
                if not cleaned_clause or len(cleaned_clause.split()) < 2:
                    continue

                clause_decision = self.classifier.classify(cleaned_clause)
                target_entity = clause_decision.entities[0] if clause_decision.entities else None
                key = (clause_decision.domain, clause_decision.intent, target_entity)

                # Avoid duplicate identical sub-tasks
                if key not in seen_intents:
                    seen_intents.add(key)
                    decomposed_tasks.append(
                        SubTask(
                            task_id=f"task_{len(decomposed_tasks) + 1}",
                            domain=clause_decision.domain,
                            intent=clause_decision.intent,
                            query_slice=cleaned_clause,
                            target_entity=target_entity,
                            status="pending",
                        )
                    )

            if len(decomposed_tasks) >= 2:
                return DecompositionPlan(
                    original_query=trimmed,
                    is_compound=True,
                    sub_tasks=decomposed_tasks,
                )

        # 5. If query is not flagged as compound or splitting produced single intent
        if not full_decision.is_compound:
            target_entity = full_decision.entities[0] if full_decision.entities else None
            single_task = SubTask(
                task_id="task_1",
                domain=full_decision.domain,
                intent=full_decision.intent,
                query_slice=trimmed,
                target_entity=target_entity,
                status="pending",
            )
            return DecompositionPlan(
                original_query=trimmed,
                is_compound=False,
                sub_tasks=[single_task],
            )

        # 6. Fallback for compound queries that couldn't be cleanly divided
        if len(full_decision.entities) > 1:
            sub_tasks = []
            for idx, entity in enumerate(full_decision.entities, start=1):
                domain = "CRYPTO" if entity in ("BTC", "ETH", "SOL", "USDT", "DOGE", "XRP", "ADA", "BNB") else "EQUITY"
                sub_tasks.append(
                    SubTask(
                        task_id=f"task_{idx}",
                        domain=domain,
                        intent="quote",
                        query_slice=f"Price quote for {entity}",
                        target_entity=entity,
                        status="pending",
                    )
                )
            return DecompositionPlan(
                original_query=trimmed,
                is_compound=True,
                sub_tasks=sub_tasks,
            )

        # 7. Fallback if splitting did not isolate distinct sub-tasks
        target_entity = full_decision.entities[0] if full_decision.entities else None
        return DecompositionPlan(
            original_query=trimmed,
            is_compound=False,
            sub_tasks=[
                SubTask(
                    task_id="task_1",
                    domain=full_decision.domain,
                    intent=full_decision.intent,
                    query_slice=trimmed,
                    target_entity=target_entity,
                    status="pending",
                )
            ],
        )


query_decomposer = QueryDecomposer()
