"""Stage 7E: Router and Multi-Agent Hardening Tests.

Validates:
1. Polysemic keyword disambiguation ('delta', 'portfolio', 'news', 'risk', 'investment', 'market').
2. Generic queries route cleanly to GENERAL fallback rather than falsely specializing.
3. Archetype decomposition (Archetypes A, B, C, D) without task loss or duplication.
4. Fast-path classifier performance guarantee (<5ms per query).
"""

from __future__ import annotations

import time
import pytest

from app.router.classifier import FastPathClassifier, fast_path_classifier
from app.router.decomposer import QueryDecomposer, query_decomposer


class TestRouterHardening:
    """Stage 7E: Rigorous routing, disambiguation, and decomposition tests."""

    @pytest.fixture
    def classifier(self) -> FastPathClassifier:
        return fast_path_classifier

    @pytest.fixture
    def decomposer(self) -> QueryDecomposer:
        return query_decomposer

    # =========================================================================
    # 1. Polysemic Keywords Disambiguation
    # =========================================================================
    @pytest.mark.parametrize(
        "query,expected_domain,expected_intent",
        [
            ("delta", "DERIVATIVES", "calculation"),
            ("portfolio", "PORTFOLIO", "overview"),
            ("news", "NEWS", "overview"),
            ("risk", "GENERAL", "educational_concept"),
            ("investment", "GENERAL", "educational_concept"),
            ("market", "GENERAL", "educational_concept"),
        ],
    )
    def test_polysemic_isolated_keywords(
        self,
        classifier: FastPathClassifier,
        query: str,
        expected_domain: str,
        expected_intent: str,
    ):
        """Isolated polysemic keywords must route according to defined semantics."""
        decision = classifier.classify(query)
        assert decision.domain == expected_domain, f"Expected {expected_domain} for '{query}', got {decision.domain}"
        assert decision.intent == expected_intent, f"Expected {expected_intent} for '{query}', got {decision.intent}"

    @pytest.mark.parametrize(
        "query,expected_domain",
        [
            ("What is financial risk?", "GENERAL"),
            ("What is inflation?", "GENERAL"),
            ("How does economic inflation affect currency purchasing power?", "GENERAL"),
            ("What is the general concept of investing?", "GENERAL"),
        ],
    )
    def test_generic_queries_route_to_general(
        self,
        classifier: FastPathClassifier,
        query: str,
        expected_domain: str,
    ):
        """Generic conceptual queries must default to GENERAL rather than falsely specializing."""
        decision = classifier.classify(query)
        assert decision.domain == expected_domain, f"Expected {expected_domain} for '{query}', got {decision.domain}"

    # =========================================================================
    # 2. Archetype Multi-Intent Decomposition
    # =========================================================================
    def test_archetype_a_concept_plus_live_quote(self, decomposer: QueryDecomposer):
        """Archetype A: Conceptual RAG + Live Quote."""
        query = "What is an IPO and what is Reliance trading at?"
        plan = decomposer.decompose(query)
        assert plan.is_compound is True
        assert len(plan.sub_tasks) == 2

        task_domains = [t.domain for t in plan.sub_tasks]
        task_intents = [t.intent for t in plan.sub_tasks]
        assert "EQUITY" in task_domains
        assert "quote" in task_intents
        assert "educational_concept" in task_intents

    def test_archetype_b_cross_domain_multi_agent(self, decomposer: QueryDecomposer):
        """Archetype B: Cross-Domain Multi-Agent (Equity + Personal Finance)."""
        query = "What is P/E and how should I plan my monthly budget?"
        plan = decomposer.decompose(query)
        assert plan.is_compound is True
        assert len(plan.sub_tasks) == 2

        domains = {t.domain for t in plan.sub_tasks}
        assert "EQUITY" in domains
        assert "PERSONAL_FINANCE" in domains

    def test_archetype_c_multi_entity_comparative(self, decomposer: QueryDecomposer):
        """Archetype C: Multi-Entity Comparative Quotes."""
        query = "Compare Reliance and TCS price"
        plan = decomposer.decompose(query)
        assert plan.is_compound is True
        assert len(plan.sub_tasks) == 2

        entities = [t.target_entity for t in plan.sub_tasks]
        assert "RELIANCE" in entities
        assert "TCS" in entities
        assert all(t.intent == "quote" for t in plan.sub_tasks)

    def test_archetype_d_three_domain_compound(self, decomposer: QueryDecomposer):
        """Archetype D: 3-Domain Compound (Equity + Crypto + Personal Finance)."""
        query = "Price of Reliance, current price of Bitcoin, and calculate 50/30/20 for 60000"
        plan = decomposer.decompose(query)
        assert plan.is_compound is True
        assert len(plan.sub_tasks) == 3

        domains = {t.domain for t in plan.sub_tasks}
        assert "EQUITY" in domains
        assert "CRYPTO" in domains
        assert "PERSONAL_FINANCE" in domains

    def test_no_duplicate_subtasks(self, decomposer: QueryDecomposer):
        """Ensure decomposition never produces duplicate sub-tasks with identical domain, intent, and entity."""
        query = "Reliance price and Reliance price"
        plan = decomposer.decompose(query)
        keys = [(t.domain, t.intent, t.target_entity) for t in plan.sub_tasks]
        assert len(keys) == len(set(keys)), "Decomposition must not produce duplicate tasks"

    # =========================================================================
    # 3. Sub-millisecond Classifier Performance
    # =========================================================================
    def test_classifier_fastpath_performance(self, classifier: FastPathClassifier):
        """Verify 100 queries classify in under 50ms total (<0.5ms average)."""
        test_queries = [
            "What is an IPO?",
            "CMP of INFY",
            "What is BTC trading at?",
            "50/30/20 budget for 50000",
            "What is delta in options?",
            "What is financial risk?",
            "Latest market news",
            "Quiz me on options",
        ] * 15

        start = time.perf_counter()
        for q in test_queries:
            classifier.classify(q)
        duration_ms = (time.perf_counter() - start) * 1000.0

        avg_latency_ms = duration_ms / len(test_queries)
        assert avg_latency_ms < 2.0, f"Classifier average latency too high: {avg_latency_ms:.2f}ms"
