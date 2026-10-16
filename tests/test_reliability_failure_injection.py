"""Stage 7G: Reliability, Failure Injection & Performance Benchmark Tests.

Validates:
1. LLM / Ollama connection outage degradation (zero crash, ungrounded fallback, truthful message).
2. Qdrant / Vector DB retrieval failure degradation (graceful ungrounded fallback).
3. Market data provider outage (graceful fallthrough, zero hallucinated market prices).
4. Deterministic fast-path pipeline latency (<15ms per end-to-end routing/validation cycle).
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock
import pytest

from app.agents.equity.agent import EquityAgent
from app.rag.retriever import RAGRetriever, RetrievedChunk
from app.rag.service import RAGService
from app.router.classifier import fast_path_classifier
from app.router.decomposer import query_decomposer
from app.router.safety import GlobalSafetyGuardrail
from app.tools.calc.compounding import calculate_compound_interest
from app.tools.market.interfaces import SymbolNotFoundError


class TestReliabilityFailureInjection:
    """Stage 7G: Failure injection simulations and performance benchmarks."""

    # =========================================================================
    # 1. LLM / Ollama Outage Simulation
    # =========================================================================
    def test_llm_outage_graceful_degradation(self):
        """When Ollama throws ConnectionError, RAGService must degrade gracefully without crashing."""
        mock_retriever = MagicMock(spec=RAGRetriever)
        mock_retriever.retrieve.return_value = MagicMock(
            chunks=[
                RetrievedChunk(
                    chunk_id="chunk_1",
                    chunk_index=1,
                    doc_id="SEBI_LODR",
                    text="Corporate governance norms apply to listed entities.",
                    score=0.88,
                    metadata={"title": "SEBI LODR Regulations"},
                )
            ]
        )

        mock_llm = MagicMock()
        mock_llm.model = "qwen2.5:7b-instruct"
        mock_llm.chat.side_effect = ConnectionError("Failed to establish a new connection: [Errno 111] Connection refused")

        rag = RAGService(retriever=mock_retriever, llm=mock_llm)
        result = rag.generate_answer(query="What are SEBI LODR corporate governance rules?")

        assert result is not None
        assert result.grounding_status == "ungrounded"
        assert result.citations == []
        assert "experiencing service disruption" in result.answer

    # =========================================================================
    # 2. Vector DB / Qdrant Outage Simulation
    # =========================================================================
    def test_vector_db_outage_graceful_degradation(self):
        """When Qdrant fails, RAGService must degrade to ungrounded fallback without crashing."""
        mock_retriever = MagicMock(spec=RAGRetriever)
        mock_retriever.retrieve.side_effect = TimeoutError("Qdrant connection timed out after 5.0s")

        mock_llm = MagicMock()
        mock_llm.model = "qwen2.5:7b-instruct"

        rag = RAGService(retriever=mock_retriever, llm=mock_llm)
        result = rag.generate_answer(query="What is an IPO?")

        assert result is not None
        assert result.grounding_status == "ungrounded"
        assert result.citations == []
        assert len(result.retrieved_chunks) == 0

    # =========================================================================
    # 3. Market Data Provider Outage Simulation
    # =========================================================================
    def test_market_data_outage_safe_fallthrough(self):
        """When live market data service fails, EquityAgent must not fabricate numbers."""
        mock_market_service = MagicMock()
        mock_market_service.get_quote.side_effect = SymbolNotFoundError("Provider connection timeout")

        mock_rag = MagicMock(spec=RAGService)
        mock_rag.generate_answer.return_value = MagicMock(
            answer="SEBI regulations govern equity trading on Indian exchanges.",
            grounding_status="fully_grounded",
            citations=[],
            model_used="qwen2.5:7b-instruct",
        )

        agent = EquityAgent(market_service=mock_market_service, rag=mock_rag)
        result = agent.ask(query="What is the price of UNKNOWN_TICKER?")

        assert result is not None
        # Market data should be None (never fabricated)
        assert result.market_data is None

    # =========================================================================
    # 4. Pipeline Latency Performance Benchmark (<15ms per cycle)
    # =========================================================================
    def test_deterministic_pipeline_latency(self):
        """Verify safety + classification + decomposition + calculation runs in <15ms."""
        guardrail = GlobalSafetyGuardrail()
        query = "What is an IPO and what is Reliance trading at?"

        latencies = []
        for _ in range(50):
            t0 = time.perf_counter()
            # 1. Safety check
            safety_res = guardrail.evaluate(query)
            # 2. Fast-path classification
            class_res = fast_path_classifier.classify(query)
            # 3. Query decomposition
            decomp_res = query_decomposer.decompose(query)
            # 4. Deterministic calculation
            calc_res = calculate_compound_interest(100000, 10.0, 5)

            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            latencies.append(elapsed_ms)

        avg_latency = sum(latencies) / len(latencies)
        assert avg_latency < 15.0, f"Pipeline average latency exceeded 15ms: {avg_latency:.2f}ms"
