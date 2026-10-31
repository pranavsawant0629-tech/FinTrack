"""
Master Central Orchestrator for Finova AI.

Coordinates:
1. Global Safety Pre-Filtering (blocks advisory/speculative queries across all domains in <1ms)
2. Fast-Path Domain & Intent Classification (sub-millisecond deterministic routing)
3. Multi-Intent Decomposition (QueryDecomposer for compound & cross-domain inquiries)
4. Multi-Agent & Tool Execution (Equity Tutor, Crypto Tutor, Personal Finance Tutor, Market Tools, RAG)
5. Deterministic Response Composition (ResponseComposer with exact numerical output preservation)
6. Unified Telemetry and TradeWise Response Assembly
"""

from __future__ import annotations

import logging
import re
import time
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from app.agents.crypto.agent import CryptoAgent
    from app.agents.equity.agent import EquityAgent
    from app.agents.personal_finance.agent import PersonalFinanceAgent
from app.memory.service import MemoryService, memory_service
from app.rag.service import Citation, RAGService, rag_service
from app.router.classifier import FastPathClassifier, fast_path_classifier
from app.router.composer import ResponseComposer, response_composer
from app.router.context_resolver import ContextualQueryResolver, contextual_resolver
from app.router.decomposer import QueryDecomposer, query_decomposer
from app.router.models import (
    DEFAULT_DISCLAIMER,
    Domain,
    OrchestratorResponse,
    RoutingDecision,
    SubTaskExecutionMetadata,
)
from app.router.safety import GlobalSafetyGuardrail, global_safety_guardrail
from app.safety.validator import GLOBAL_REFUSAL_MESSAGE, secondary_safety_validator
from app.tools.crypto.models import CryptoQuote
from app.tools.crypto.service import CryptoDataService, crypto_data_service
from app.tools.market.models import CompanyOverview, HistoricalPrices, MarketDataProvenance, MarketQuote
from app.tools.market.service import MarketDataService

logger = logging.getLogger(__name__)


class CentralOrchestrator:
    """Master orchestrator managing safety, routing, execution, and unified response formatting."""

    def __init__(
        self,
        safety: GlobalSafetyGuardrail | None = None,
        classifier: FastPathClassifier | None = None,
        decomposer: QueryDecomposer | None = None,
        composer: ResponseComposer | None = None,
        equity: Any | None = None,
        crypto: Any | None = None,
        personal_finance: Any | None = None,
        market_service: MarketDataService | None = None,
        crypto_service: CryptoDataService | None = None,
        rag: RAGService | None = None,
        memory: MemoryService | None = None,
        context_resolver: ContextualQueryResolver | None = None,
    ) -> None:
        self.safety = safety or global_safety_guardrail
        self.classifier = classifier or fast_path_classifier
        self.decomposer = decomposer or query_decomposer
        self.composer = composer or response_composer
        self.context_resolver = context_resolver or contextual_resolver

        self._equity_agent = equity
        self._crypto_agent = crypto
        self._personal_finance_agent = personal_finance
        self._derivatives_agent = None
        self._portfolio_agent = None
        self._news_agent = None
        self._quiz_agent = None
        self._onboarding_agent = None

        self.market_service = market_service or MarketDataService()
        self.crypto_service = crypto_service or crypto_data_service
        self.rag_service = rag or rag_service
        self.memory_service = memory or memory_service

    @property
    def equity_agent(self) -> Any:
        if self._equity_agent is None:
            from app.agents.equity.agent import equity_agent
            self._equity_agent = equity_agent
        return self._equity_agent

    @property
    def crypto_agent(self) -> Any:
        if self._crypto_agent is None:
            from app.agents.crypto.agent import crypto_agent
            self._crypto_agent = crypto_agent
        return self._crypto_agent

    @property
    def personal_finance_agent(self) -> Any:
        if self._personal_finance_agent is None:
            from app.agents.personal_finance.agent import personal_finance_agent
            self._personal_finance_agent = personal_finance_agent
        return self._personal_finance_agent

    @property
    def derivatives_agent(self) -> Any:
        if self._derivatives_agent is None:
            from app.agents.derivatives.agent import DerivativesAgent
            self._derivatives_agent = DerivativesAgent(rag=self.rag_service)
        return self._derivatives_agent

    @property
    def portfolio_agent(self) -> Any:
        if self._portfolio_agent is None:
            from app.agents.portfolio.agent import PortfolioAgent
            self._portfolio_agent = PortfolioAgent()
        return self._portfolio_agent

    @property
    def news_agent(self) -> Any:
        if self._news_agent is None:
            from app.agents.news.agent import NewsAgent
            self._news_agent = NewsAgent()
        return self._news_agent

    @property
    def quiz_agent(self) -> Any:
        if self._quiz_agent is None:
            from app.agents.quiz.agent import QuizAgent
            self._quiz_agent = QuizAgent(memory_service=self.memory_service)
        return self._quiz_agent

    @property
    def onboarding_agent(self) -> Any:
        if self._onboarding_agent is None:
            from app.agents.onboarding.agent import OnboardingAgent
            self._onboarding_agent = OnboardingAgent()
        return self._onboarding_agent

    def ask(
        self,
        query: str,
        user_id: str | None = None,
        conversation_history: list[dict[str, str]] | None = None,
        top_k: int | None = None,
        score_threshold: float | None = None,
        domain_context: str | Domain | None = None,
    ) -> OrchestratorResponse:
        """Execute the central orchestration pipeline."""
        t0 = time.perf_counter()

        # Step 0A: Universal Input Sanitization & Central Safety Pre-Filter (<0.5ms)
        sec_safety = secondary_safety_validator.validate(query)
        if not sec_safety.is_safe:
            latency = round((time.perf_counter() - t0) * 1000, 2)
            sub_meta = SubTaskExecutionMetadata(
                task_id="task_1",
                domain="GENERAL",
                intent="advice_refusal",
                status="filtered",
                latency_ms=latency,
            )
            return OrchestratorResponse(
                query=query if isinstance(query, str) else "",
                resolved_query=None,
                answer=sec_safety.refusal_message or GLOBAL_REFUSAL_MESSAGE,
                grounding_status="ungrounded",
                citations=[],
                market_data=None,
                market_data_list=[],
                crypto_data=None,
                grounding_sources=[],
                domain_detected="GENERAL",
                sub_tasks=[sub_meta],
                agent_name="Finova Orchestrator",
                disclaimer=DEFAULT_DISCLAIMER,
                model_used="deterministic_guardrail",
                latency_ms=latency,
            )
        # Enforce sanitized input across router pipeline
        query = sec_safety.sanitized_text

        # Step 0: Multi-Turn Context and Anaphora Resolution (<0.5ms)
        resolved_ctx = self.context_resolver.resolve_context(
            query=query,
            conversation_history=conversation_history,
        )
        effective_query = resolved_ctx.resolved_query if resolved_ctx.has_reference else query
        resolved_query_attr = resolved_ctx.resolved_query if resolved_ctx.has_reference else None

        if resolved_ctx.has_reference:
            sec_effective = secondary_safety_validator.validate(effective_query)
            if not sec_effective.is_safe:
                latency = round((time.perf_counter() - t0) * 1000, 2)
                sub_meta = SubTaskExecutionMetadata(
                    task_id="task_1",
                    domain="GENERAL",
                    intent="advice_refusal",
                    status="filtered",
                    latency_ms=latency,
                )
                return OrchestratorResponse(
                    query=query,
                    resolved_query=resolved_query_attr,
                    answer=sec_effective.refusal_message or GLOBAL_REFUSAL_MESSAGE,
                    grounding_status="ungrounded",
                    citations=[],
                    market_data=None,
                    market_data_list=[],
                    crypto_data=None,
                    grounding_sources=[],
                    domain_detected="GENERAL",
                    sub_tasks=[sub_meta],
                    agent_name="Finova Orchestrator",
                    disclaimer=DEFAULT_DISCLAIMER,
                    model_used="deterministic_guardrail",
                    latency_ms=latency,
                )
            effective_query = sec_effective.sanitized_text

        # Step 1: Global Safety Pre-Filtering (<1ms)
        safety_res = self.safety.evaluate(effective_query)
        if not safety_res.is_safe:
            # Explicit invariant: Unsafe queries return refusal immediately.
            # No memory candidates are ever extracted or stored for unsafe queries.
            latency = round((time.perf_counter() - t0) * 1000, 2)
            filtered_domain: Domain = safety_res.domain or "GENERAL"
            sub_meta = SubTaskExecutionMetadata(
                task_id="task_1",
                domain=filtered_domain,
                intent="advice_refusal",
                status="filtered",
                latency_ms=latency,
            )
            return OrchestratorResponse(
                query=query,
                resolved_query=resolved_query_attr,
                answer=safety_res.refusal_message or "",
                grounding_status="ungrounded",
                citations=[],
                market_data=None,
                market_data_list=[],
                crypto_data=None,
                grounding_sources=[],
                domain_detected=filtered_domain,
                sub_tasks=[sub_meta],
                agent_name="Finova Orchestrator",
                disclaimer=DEFAULT_DISCLAIMER,
                model_used="deterministic_guardrail",
                latency_ms=latency,
            )

        if effective_query != query:
            safety_res_orig = self.safety.evaluate(query)
            if not safety_res_orig.is_safe:
                latency = round((time.perf_counter() - t0) * 1000, 2)
                filtered_domain = safety_res_orig.domain or "GENERAL"
                sub_meta = SubTaskExecutionMetadata(
                    task_id="task_1",
                    domain=filtered_domain,
                    intent="advice_refusal",
                    status="filtered",
                    latency_ms=latency,
                )
                return OrchestratorResponse(
                    query=query,
                    resolved_query=resolved_query_attr,
                    answer=safety_res_orig.refusal_message or "",
                    grounding_status="ungrounded",
                    citations=[],
                    market_data=None,
                    market_data_list=[],
                    crypto_data=None,
                    grounding_sources=[],
                    domain_detected=filtered_domain,
                    sub_tasks=[sub_meta],
                    agent_name="Finova Orchestrator",
                    disclaimer=DEFAULT_DISCLAIMER,
                    model_used="deterministic_guardrail",
                    latency_ms=latency,
                )

        # Step 2: Contextual Memory Retrieval (if user_id is provided)
        profile = None
        if user_id:
            try:
                profile = self.memory_service.retrieve_profile(user_id=user_id, current_query=effective_query)
            except Exception as exc:
                logger.warning("Memory profile retrieval failed gracefully: %s", exc)
                profile = None

        # Check for explicit current-query level overrides
        effective_profile = profile
        q_lower = effective_query.lower()
        override_level = None
        if any(w in q_lower for w in ["beginner", "simple terms", "like i'm 5", "eli5", "new to", "explain simpler", "simpler", "simple"]):
            override_level = "beginner"
        elif any(w in q_lower for w in ["advanced", "in-depth", "deep dive", "expert", "detailed technical", "go deeper", "deeper", "mechanics"]):
            override_level = "advanced"
        elif any(w in q_lower for w in ["intermediate", "moderate"]):
            override_level = "intermediate"

        if profile and override_level and override_level != profile.learning_level:
            effective_profile = profile.model_copy(update={"learning_level": override_level})
        elif not profile and override_level:
            from app.memory.models import PersonalizationProfile
            effective_profile = PersonalizationProfile(
                user_id=user_id or "anonymous",
                learning_level=override_level,
            )

        # Step 3: Intent & Domain Classification (<1ms)
        decision: RoutingDecision = self.classifier.classify(effective_query)

        # Tutor section bias: If an explicit non-general domain context is provided,
        # route directly to that tutor rather than cross-domain decomposition.
        normalized_domain_ctx: Domain | None = None
        if domain_context:
            clean_ctx = str(domain_context).strip().upper()
            if clean_ctx in (
                "EQUITY",
                "CRYPTO",
                "PERSONAL_FINANCE",
                "DERIVATIVES",
                "PORTFOLIO",
                "NEWS",
                "QUIZ",
                "ONBOARDING",
                "GENERAL",
            ):
                normalized_domain_ctx = clean_ctx  # type: ignore

        # Check for quiz actions or answer submissions inside tutor sections
        is_quiz_query = (
            any(w in q_lower for w in ["quiz me", "test me", "take a quiz", "test my knowledge", "quiz on"])
            or bool(re.search(r"\b[a-zA-Z0-9_]+\s*[:=]\s*[A-Da-d]\b", effective_query))
            or bool(re.search(r"\b(?:answer|option|choice)\s*[:]?\s*[A-Da-d]\s*for\b", effective_query, re.IGNORECASE))
        )

        if is_quiz_query:
            decision = RoutingDecision(
                query=effective_query,
                domain="QUIZ",
                intent="educational_concept",
                is_compound=False,
                entities=decision.entities,
            )
        elif normalized_domain_ctx and normalized_domain_ctx != "GENERAL":
            decision = RoutingDecision(
                query=effective_query,
                domain=normalized_domain_ctx,
                intent=decision.intent,
                is_compound=False,
                entities=decision.entities,
            )

        # Step 4: Multi-Intent / Compound Query Execution
        response: OrchestratorResponse | None = None
        if decision.is_compound:
            plan = self.decomposer.decompose(effective_query)
            if plan.is_compound and len(plan.sub_tasks) > 1:
                response = self._execute_compound_plan(
                    query=query,
                    plan=plan,
                    top_k=top_k,
                    score_threshold=score_threshold,
                    t0=t0,
                    personalization=effective_profile,
                    resolved_query=resolved_query_attr,
                    conversation_history=conversation_history,
                )

        # Step 5: Single-Intent Fast-Path Execution (if not handled by compound planner)
        if response is None:
            # 5A. Equity Domain Dispatch
            if decision.domain == "EQUITY":
                equity_res = self.equity_agent.ask(
                    query=effective_query,
                    conversation_history=conversation_history,
                    top_k=top_k,
                    score_threshold=score_threshold,
                    personalization=effective_profile,
                )
                latency = round((time.perf_counter() - t0) * 1000, 2)
                sub_meta = SubTaskExecutionMetadata(
                    task_id="task_1",
                    domain="EQUITY",
                    intent=decision.intent,
                    target=decision.entities[0] if decision.entities else None,
                    status="success",
                    latency_ms=equity_res.latency_ms,
                )
                response = OrchestratorResponse(
                    query=query,
                    resolved_query=resolved_query_attr,
                    answer=equity_res.answer,
                    grounding_status=equity_res.grounding_status,
                    citations=equity_res.citations,
                    market_data=equity_res.market_data,
                    market_data_list=[equity_res.market_data] if equity_res.market_data else [],
                    crypto_data=None,
                    grounding_sources=equity_res.grounding_sources,
                    domain_detected="EQUITY",
                    sub_tasks=[sub_meta],
                    agent_name=equity_res.agent_name,
                    disclaimer=equity_res.disclaimer,
                    model_used=equity_res.model_used,
                    latency_ms=latency,
                )

            # 5B. Crypto Domain Dispatch
            elif decision.domain == "CRYPTO":
                crypto_res = self.crypto_agent.ask(
                    query=effective_query,
                    conversation_history=conversation_history,
                    personalization=effective_profile,
                )
                latency = round((time.perf_counter() - t0) * 1000, 2)
                sub_meta = SubTaskExecutionMetadata(
                    task_id="task_1",
                    domain="CRYPTO",
                    intent=decision.intent,
                    target=decision.entities[0] if decision.entities else None,
                    status="success",
                    latency_ms=crypto_res.latency_ms,
                )
                response = OrchestratorResponse(
                    query=query,
                    resolved_query=resolved_query_attr,
                    answer=crypto_res.answer,
                    grounding_status=crypto_res.grounding_status,
                    citations=[],
                    market_data=None,
                    market_data_list=[],
                    crypto_data=crypto_res.crypto_data,
                    grounding_sources=crypto_res.grounding_sources,
                    domain_detected="CRYPTO",
                    sub_tasks=[sub_meta],
                    agent_name=crypto_res.agent_name,
                    disclaimer=crypto_res.disclaimer,
                    model_used=crypto_res.model_used,
                    latency_ms=latency,
                )

            # 5C. Personal Finance Domain Dispatch
            elif decision.domain == "PERSONAL_FINANCE":
                pf_res = self.personal_finance_agent.ask(
                    query=effective_query,
                    conversation_history=conversation_history,
                    personalization=effective_profile,
                )
                latency = round((time.perf_counter() - t0) * 1000, 2)
                sub_meta = SubTaskExecutionMetadata(
                    task_id="task_1",
                    domain="PERSONAL_FINANCE",
                    intent=decision.intent,
                    status="success",
                    latency_ms=pf_res.latency_ms,
                )
                response = self.composer.compose(
                    query=query,
                    resolved_query=resolved_query_attr,
                    educational_text=pf_res.answer if not pf_res.calc_data else None,
                    calc_data=pf_res.calc_data,
                    domain_detected="PERSONAL_FINANCE",
                    sub_tasks=[sub_meta],
                    disclaimer=pf_res.disclaimer,
                    model_used=pf_res.model_used,
                    latency_ms=latency,
                )

            # 5D. Derivatives Domain Dispatch
            elif decision.domain == "DERIVATIVES":
                deriv_res = self.derivatives_agent.ask(
                    query=effective_query,
                    user_id=user_id,
                    conversation_history=conversation_history,
                    personalization=effective_profile,
                )
                latency = round((time.perf_counter() - t0) * 1000, 2)
                sub_meta = SubTaskExecutionMetadata(
                    task_id="task_1",
                    domain="DERIVATIVES",
                    intent=decision.intent,
                    status="success",
                    latency_ms=latency,
                )
                response = OrchestratorResponse(
                    query=query,
                    resolved_query=resolved_query_attr,
                    answer=deriv_res.answer,
                    grounding_status=deriv_res.grounding_status,
                    citations=[],
                    market_data=None,
                    market_data_list=[],
                    crypto_data=None,
                    derivatives_data=deriv_res.derivatives_data,
                    grounding_sources=deriv_res.grounding_sources,
                    domain_detected="DERIVATIVES",
                    sub_tasks=[sub_meta],
                    agent_name=deriv_res.agent_name,
                    disclaimer=deriv_res.disclaimer,
                    model_used=deriv_res.model_used,
                    latency_ms=latency,
                )

            # 5E. Portfolio Domain Dispatch
            elif decision.domain == "PORTFOLIO":
                port_res = self.portfolio_agent.ask(
                    query=effective_query,
                    user_id=user_id,
                    conversation_history=conversation_history,
                    personalization=effective_profile,
                )
                latency = round((time.perf_counter() - t0) * 1000, 2)
                sub_meta = SubTaskExecutionMetadata(
                    task_id="task_1",
                    domain="PORTFOLIO",
                    intent=decision.intent,
                    status="success",
                    latency_ms=latency,
                )
                response = OrchestratorResponse(
                    query=query,
                    resolved_query=resolved_query_attr,
                    answer=port_res.answer,
                    grounding_status=port_res.grounding_status,
                    citations=[],
                    market_data=None,
                    market_data_list=[],
                    crypto_data=None,
                    portfolio_data=port_res.portfolio_data,
                    grounding_sources=port_res.grounding_sources,
                    domain_detected="PORTFOLIO",
                    sub_tasks=[sub_meta],
                    agent_name="Portfolio Tutor",
                    disclaimer=port_res.disclaimer,
                    model_used="deterministic_tools",
                    latency_ms=latency,
                )

            # 5F. News Domain Dispatch
            elif decision.domain == "NEWS":
                news_res = self.news_agent.ask(
                    query=effective_query,
                    user_id=user_id,
                )
                latency = round((time.perf_counter() - t0) * 1000, 2)
                sub_meta = SubTaskExecutionMetadata(
                    task_id="task_1",
                    domain="NEWS",
                    intent=decision.intent,
                    status="success",
                    latency_ms=latency,
                )
                response = OrchestratorResponse(
                    query=query,
                    resolved_query=resolved_query_attr,
                    answer=news_res.answer,
                    grounding_status=news_res.grounding_status,
                    citations=[],
                    market_data=None,
                    market_data_list=[],
                    crypto_data=None,
                    news_data=news_res.articles,
                    grounding_sources=news_res.grounding_sources,
                    domain_detected="NEWS",
                    sub_tasks=[sub_meta],
                    agent_name="Market News Agent",
                    disclaimer=news_res.disclaimer,
                    model_used="news_service",
                    latency_ms=latency,
                )

            # 5G. Quiz Domain Dispatch
            elif decision.domain == "QUIZ":
                quiz_res = self.quiz_agent.ask(
                    query=effective_query,
                    user_id=user_id,
                )
                latency = round((time.perf_counter() - t0) * 1000, 2)
                sub_meta = SubTaskExecutionMetadata(
                    task_id="task_1",
                    domain="QUIZ",
                    intent=decision.intent,
                    status="success",
                    latency_ms=latency,
                )
                domain_to_report = normalized_domain_ctx or "QUIZ"
                agent_display_name = (
                    f"{normalized_domain_ctx.title().replace('_', ' ')} Tutor (Quiz)"
                    if (normalized_domain_ctx and normalized_domain_ctx not in ("GENERAL", "QUIZ"))
                    else "Quiz Tutor"
                )
                response = OrchestratorResponse(
                    query=query,
                    resolved_query=resolved_query_attr,
                    answer=quiz_res.answer,
                    grounding_status=quiz_res.grounding_status,
                    citations=[],
                    market_data=None,
                    market_data_list=[],
                    crypto_data=None,
                    quiz_data=quiz_res.evaluation or ({"questions": quiz_res.questions} if quiz_res.questions else None),
                    grounding_sources=quiz_res.grounding_sources,
                    domain_detected=domain_to_report,
                    sub_tasks=[sub_meta],
                    agent_name=agent_display_name,
                    disclaimer=quiz_res.disclaimer,
                    model_used="deterministic_grading",
                    latency_ms=latency,
                )

            # 5H. Onboarding Domain Dispatch
            elif decision.domain == "ONBOARDING":
                onboard_res = self.onboarding_agent.ask(
                    query=effective_query,
                    user_id=user_id,
                )
                latency = round((time.perf_counter() - t0) * 1000, 2)
                sub_meta = SubTaskExecutionMetadata(
                    task_id="task_1",
                    domain="ONBOARDING",
                    intent=decision.intent,
                    status="success",
                    latency_ms=latency,
                )
                response = OrchestratorResponse(
                    query=query,
                    resolved_query=resolved_query_attr,
                    answer=onboard_res.answer,
                    grounding_status=onboard_res.grounding_status,
                    citations=[],
                    market_data=None,
                    market_data_list=[],
                    crypto_data=None,
                    onboarding_data=onboard_res.capabilities or onboard_res.faqs,
                    grounding_sources=onboard_res.grounding_sources,
                    domain_detected="ONBOARDING",
                    sub_tasks=[sub_meta],
                    agent_name="System Guide",
                    disclaimer=onboard_res.disclaimer,
                    model_used="system_catalog",
                    latency_ms=latency,
                )

            # 5I. General Fallback
            else:
                equity_res = self.equity_agent.ask(
                    query=effective_query,
                    conversation_history=conversation_history,
                    top_k=top_k,
                    score_threshold=score_threshold,
                    personalization=effective_profile,
                )
                latency = round((time.perf_counter() - t0) * 1000, 2)
                sub_meta = SubTaskExecutionMetadata(
                    task_id="task_1",
                    domain="GENERAL",
                    intent=decision.intent,
                    status="success",
                    latency_ms=equity_res.latency_ms,
                )
                response = OrchestratorResponse(
                    query=query,
                    resolved_query=resolved_query_attr,
                    answer=equity_res.answer,
                    grounding_status=equity_res.grounding_status,
                    citations=equity_res.citations,
                    market_data=equity_res.market_data,
                    market_data_list=[equity_res.market_data] if equity_res.market_data else [],
                    crypto_data=None,
                    grounding_sources=equity_res.grounding_sources,
                    domain_detected="GENERAL",
                    sub_tasks=[sub_meta],
                    agent_name="Finova Orchestrator",
                    disclaimer=equity_res.disclaimer,
                    model_used=equity_res.model_used,
                    latency_ms=latency,
                )

        # Step 6: Synchronous & Fault-Tolerant Candidate Extraction & Persistence
        if user_id:
            try:
                self.memory_service.process_and_save_candidates(user_id=user_id, query=effective_query)
            except Exception as exc:
                logger.warning("Memory candidate processing failed gracefully: %s", exc)

        # Step 7: Resolve Pedagogical Learning Context & Topic Continuity (Phase 11)
        if response:
            try:
                from app.conversations.learning_context import resolve_learning_context

                target_domain = normalized_domain_ctx or str(response.domain_detected)
                ctx_res = resolve_learning_context(
                    query=effective_query,
                    domain=target_domain,
                    conversation_history=conversation_history,
                    orchestrator_response=response,
                )
                response.topic = ctx_res.topic
                response.related_concepts = ctx_res.related_concepts
                response.suggested_next = ctx_res.suggested_next
            except Exception as exc:
                logger.warning("Failed to resolve learning context: %s", exc)

        return response

    def _execute_compound_plan(
        self,
        query: str,
        plan: Any,
        top_k: int | None,
        score_threshold: float | None,
        t0: float,
        personalization: Any | None = None,
        resolved_query: str | None = None,
        conversation_history: list[dict[str, str]] | None = None,
    ) -> OrchestratorResponse:
        """Execute a decomposed multi-intent plan and compose the results."""
        educational_texts: list[str] = []
        all_citations: list[Citation] = []
        market_quotes: list[MarketQuote | MarketDataProvenance] = []
        historical_data: HistoricalPrices | None = None
        overview_data: CompanyOverview | None = None
        crypto_data: dict[str, Any] | None = None
        calc_data: dict[str, Any] | None = None
        derivatives_data: dict[str, Any] | None = None
        portfolio_data: dict[str, Any] | None = None
        news_data: list[dict[str, Any]] | None = None
        sub_metas: list[SubTaskExecutionMetadata] = []
        is_causal = any("why" in t.query_slice.lower() and "fall" in t.query_slice.lower() for t in plan.sub_tasks)

        for task in plan.sub_tasks:
            t_sub = time.perf_counter()
            # 1. Equity Domain Sub-Tasks
            if task.domain == "EQUITY":
                if task.intent == "quote" and task.target_entity:
                    try:
                        quote = self.market_service.get_quote(task.target_entity)
                        market_quotes.append(quote)
                        sub_metas.append(
                            SubTaskExecutionMetadata(
                                task_id=task.task_id,
                                domain="EQUITY",
                                intent="quote",
                                target=task.target_entity,
                                status="success",
                                latency_ms=round((time.perf_counter() - t_sub) * 1000, 2),
                            )
                        )
                    except Exception as exc:
                        logger.warning("Quote fetch failed for %s: %s", task.target_entity, exc)
                        sub_metas.append(
                            SubTaskExecutionMetadata(
                                task_id=task.task_id,
                                domain="EQUITY",
                                intent="quote",
                                target=task.target_entity,
                                status="failed",
                                latency_ms=round((time.perf_counter() - t_sub) * 1000, 2),
                            )
                        )
                elif task.intent == "historical" and task.target_entity:
                    try:
                        historical_data = self.market_service.get_historical_summary(task.target_entity)
                        sub_metas.append(
                            SubTaskExecutionMetadata(
                                task_id=task.task_id,
                                domain="EQUITY",
                                intent="historical",
                                target=task.target_entity,
                                status="success",
                                latency_ms=round((time.perf_counter() - t_sub) * 1000, 2),
                            )
                        )
                    except Exception as exc:
                        logger.warning("Historical fetch failed for %s: %s", task.target_entity, exc)
                        sub_metas.append(
                            SubTaskExecutionMetadata(
                                task_id=task.task_id,
                                domain="EQUITY",
                                intent="historical",
                                target=task.target_entity,
                                status="failed",
                                latency_ms=round((time.perf_counter() - t_sub) * 1000, 2),
                            )
                        )
                elif task.intent == "overview" and task.target_entity:
                    try:
                        overview_data = self.market_service.get_company_overview(task.target_entity)
                        sub_metas.append(
                            SubTaskExecutionMetadata(
                                task_id=task.task_id,
                                domain="EQUITY",
                                intent="overview",
                                target=task.target_entity,
                                status="success",
                                latency_ms=round((time.perf_counter() - t_sub) * 1000, 2),
                            )
                        )
                    except Exception as exc:
                        logger.warning("Overview fetch failed for %s: %s", task.target_entity, exc)
                        sub_metas.append(
                            SubTaskExecutionMetadata(
                                task_id=task.task_id,
                                domain="EQUITY",
                                intent="overview",
                                target=task.target_entity,
                                status="failed",
                                latency_ms=round((time.perf_counter() - t_sub) * 1000, 2),
                            )
                        )
                else:
                    # Conceptual Educational RAG query
                    try:
                        sys_prompt = None
                        if personalization:
                            from app.agents.equity.prompts import EQUITY_TUTOR_SYSTEM_PROMPT
                            from app.memory.models import build_personalization_instruction
                            inst = build_personalization_instruction(personalization)
                            if inst:
                                sys_prompt = EQUITY_TUTOR_SYSTEM_PROMPT + inst
                        rag_ans = self.rag_service.generate_answer(
                            query=task.query_slice,
                            top_k=top_k,
                            score_threshold=score_threshold,
                            system_prompt=sys_prompt,
                            conversation_history=conversation_history,
                        )
                        educational_texts.append(rag_ans.answer)
                        all_citations.extend(rag_ans.citations)
                        sub_metas.append(
                            SubTaskExecutionMetadata(
                                task_id=task.task_id,
                                domain="EQUITY",
                                intent="educational_concept",
                                status="success",
                                latency_ms=round((time.perf_counter() - t_sub) * 1000, 2),
                            )
                        )
                    except Exception as exc:
                        logger.warning("RAG query failed for %s: %s", task.query_slice, exc)
                        sub_metas.append(
                            SubTaskExecutionMetadata(
                                task_id=task.task_id,
                                domain="EQUITY",
                                intent="educational_concept",
                                status="failed",
                                latency_ms=round((time.perf_counter() - t_sub) * 1000, 2),
                            )
                        )

            # 2. Crypto Domain Sub-Tasks
            elif task.domain == "CRYPTO":
                if task.intent == "quote" and task.target_entity:
                    try:
                        c_quote = self.crypto_service.get_quote(task.target_entity)
                        prov = self.crypto_service.create_provenance(c_quote)
                        crypto_data = prov.model_dump()
                        sub_metas.append(
                            SubTaskExecutionMetadata(
                                task_id=task.task_id,
                                domain="CRYPTO",
                                intent="quote",
                                target=task.target_entity,
                                status="success",
                                latency_ms=round((time.perf_counter() - t_sub) * 1000, 2),
                            )
                        )
                    except Exception as exc:
                        logger.warning("Crypto quote fetch failed for %s: %s", task.target_entity, exc)
                        sub_metas.append(
                            SubTaskExecutionMetadata(
                                task_id=task.task_id,
                                domain="CRYPTO",
                                intent="quote",
                                target=task.target_entity,
                                status="failed",
                                latency_ms=round((time.perf_counter() - t_sub) * 1000, 2),
                            )
                        )
                else:
                    try:
                        c_res = self.crypto_agent.ask(task.query_slice, personalization=personalization)
                        educational_texts.append(c_res.answer)
                        sub_metas.append(
                            SubTaskExecutionMetadata(
                                task_id=task.task_id,
                                domain="CRYPTO",
                                intent=task.intent,
                                status="success",
                                latency_ms=round((time.perf_counter() - t_sub) * 1000, 2),
                            )
                        )
                    except Exception as exc:
                        logger.warning("Crypto ask failed for %s: %s", task.query_slice, exc)
                        sub_metas.append(
                            SubTaskExecutionMetadata(
                                task_id=task.task_id,
                                domain="CRYPTO",
                                intent=task.intent,
                                status="failed",
                                latency_ms=round((time.perf_counter() - t_sub) * 1000, 2),
                            )
                        )

            # 3. Personal Finance Domain Sub-Tasks
            elif task.domain == "PERSONAL_FINANCE":
                try:
                    pf_res = self.personal_finance_agent.ask(task.query_slice, personalization=personalization)
                    if pf_res.calc_data:
                        calc_data = pf_res.calc_data
                    else:
                        educational_texts.append(pf_res.answer)
                    sub_metas.append(
                        SubTaskExecutionMetadata(
                            task_id=task.task_id,
                            domain="PERSONAL_FINANCE",
                            intent=task.intent,
                            status="success",
                            latency_ms=round((time.perf_counter() - t_sub) * 1000, 2),
                        )
                    )
                except Exception as exc:
                    logger.warning("Personal finance ask failed for %s: %s", task.query_slice, exc)
                    sub_metas.append(
                        SubTaskExecutionMetadata(
                            task_id=task.task_id,
                            domain="PERSONAL_FINANCE",
                            intent=task.intent,
                            status="failed",
                            latency_ms=round((time.perf_counter() - t_sub) * 1000, 2),
                        )
                    )

            # 4. Derivatives Domain Sub-Tasks
            elif task.domain == "DERIVATIVES":
                try:
                    d_res = self.derivatives_agent.ask(task.query_slice, personalization=personalization)
                    if d_res.derivatives_data:
                        derivatives_data = d_res.derivatives_data
                    educational_texts.append(d_res.answer)
                    sub_metas.append(
                        SubTaskExecutionMetadata(
                            task_id=task.task_id,
                            domain="DERIVATIVES",
                            intent=task.intent,
                            status="success",
                            latency_ms=round((time.perf_counter() - t_sub) * 1000, 2),
                        )
                    )
                except Exception as exc:
                    logger.warning("Derivatives ask failed for %s: %s", task.query_slice, exc)
                    sub_metas.append(
                        SubTaskExecutionMetadata(
                            task_id=task.task_id,
                            domain="DERIVATIVES",
                            intent=task.intent,
                            status="failed",
                            latency_ms=round((time.perf_counter() - t_sub) * 1000, 2),
                        )
                    )

            # 5. Portfolio Domain Sub-Tasks
            elif task.domain == "PORTFOLIO":
                try:
                    p_res = self.portfolio_agent.ask(task.query_slice, personalization=personalization)
                    if p_res.portfolio_data:
                        portfolio_data = p_res.portfolio_data
                    educational_texts.append(p_res.answer)
                    sub_metas.append(
                        SubTaskExecutionMetadata(
                            task_id=task.task_id,
                            domain="PORTFOLIO",
                            intent=task.intent,
                            status="success",
                            latency_ms=round((time.perf_counter() - t_sub) * 1000, 2),
                        )
                    )
                except Exception as exc:
                    logger.warning("Portfolio ask failed for %s: %s", task.query_slice, exc)
                    sub_metas.append(
                        SubTaskExecutionMetadata(
                            task_id=task.task_id,
                            domain="PORTFOLIO",
                            intent=task.intent,
                            status="failed",
                            latency_ms=round((time.perf_counter() - t_sub) * 1000, 2),
                        )
                    )

            # 6. News Domain Sub-Tasks
            elif task.domain == "NEWS":
                try:
                    n_res = self.news_agent.ask(task.query_slice)
                    if n_res.articles:
                        news_data = n_res.articles
                    educational_texts.append(n_res.answer)
                    sub_metas.append(
                        SubTaskExecutionMetadata(
                            task_id=task.task_id,
                            domain="NEWS",
                            intent=task.intent,
                            status="success",
                            latency_ms=round((time.perf_counter() - t_sub) * 1000, 2),
                        )
                    )
                except Exception as exc:
                    logger.warning("News ask failed for %s: %s", task.query_slice, exc)
                    sub_metas.append(
                        SubTaskExecutionMetadata(
                            task_id=task.task_id,
                            domain="NEWS",
                            intent=task.intent,
                            status="failed",
                            latency_ms=round((time.perf_counter() - t_sub) * 1000, 2),
                        )
                    )

            # 7. Quiz Domain Sub-Tasks
            elif task.domain == "QUIZ":
                try:
                    q_res = self.quiz_agent.ask(task.query_slice)
                    educational_texts.append(q_res.answer)
                    sub_metas.append(
                        SubTaskExecutionMetadata(
                            task_id=task.task_id,
                            domain="QUIZ",
                            intent=task.intent,
                            status="success",
                            latency_ms=round((time.perf_counter() - t_sub) * 1000, 2),
                        )
                    )
                except Exception as exc:
                    logger.warning("Quiz ask failed for %s: %s", task.query_slice, exc)
                    sub_metas.append(
                        SubTaskExecutionMetadata(
                            task_id=task.task_id,
                            domain="QUIZ",
                            intent=task.intent,
                            status="failed",
                            latency_ms=round((time.perf_counter() - t_sub) * 1000, 2),
                        )
                    )

            # 8. Onboarding Domain Sub-Tasks
            elif task.domain == "ONBOARDING":
                try:
                    o_res = self.onboarding_agent.ask(task.query_slice)
                    educational_texts.append(o_res.answer)
                    sub_metas.append(
                        SubTaskExecutionMetadata(
                            task_id=task.task_id,
                            domain="ONBOARDING",
                            intent=task.intent,
                            status="success",
                            latency_ms=round((time.perf_counter() - t_sub) * 1000, 2),
                        )
                    )
                except Exception as exc:
                    logger.warning("Onboarding ask failed for %s: %s", task.query_slice, exc)
                    sub_metas.append(
                        SubTaskExecutionMetadata(
                            task_id=task.task_id,
                            domain="ONBOARDING",
                            intent=task.intent,
                            status="failed",
                            latency_ms=round((time.perf_counter() - t_sub) * 1000, 2),
                        )
                    )

        combined_edu = "\n\n".join(educational_texts) if educational_texts else None
        latency = round((time.perf_counter() - t0) * 1000, 2)

        distinct_domains = {t.domain for t in plan.sub_tasks}
        compound_domain: Domain = (
            "GENERAL" if len(distinct_domains) > 1 else (list(distinct_domains)[0] if distinct_domains else "GENERAL")
        )

        return self.composer.compose(
            query=query,
            resolved_query=resolved_query,
            educational_text=combined_edu,
            citations=all_citations,
            market_quotes=market_quotes,
            historical_data=historical_data,
            overview_data=overview_data,
            crypto_data=crypto_data,
            calc_data=calc_data,
            derivatives_data=derivatives_data,
            portfolio_data=portfolio_data,
            news_data=news_data,
            is_causal_query=is_causal,
            domain_detected=compound_domain,
            sub_tasks=sub_metas,
            latency_ms=latency,
        )


central_orchestrator = CentralOrchestrator()
