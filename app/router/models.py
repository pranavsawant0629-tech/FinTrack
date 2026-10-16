"""
Data contracts and Pydantic schemas for the Finova AI Central Router & Orchestrator.
Defines domain types, intent classifications, sub-tasks, routing decisions,
and the unified multi-agent response contract.
"""

from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field

from app.rag.service import Citation
from app.tools.market.models import MarketDataProvenance

# Core Domain Definitions (8 specialized domains + GENERAL fallback)
Domain = Literal[
    "EQUITY",
    "CRYPTO",
    "PERSONAL_FINANCE",
    "DERIVATIVES",
    "PORTFOLIO",
    "NEWS",
    "QUIZ",
    "ONBOARDING",
    "GENERAL",
]

# Granular Intent Definitions across all domains
IntentType = Literal[
    "quote",
    "historical",
    "overview",
    "market_status",
    "educational_concept",
    "calculation",
    "compound",
    "advice_refusal",
    "unknown",
]

DEFAULT_DISCLAIMER = (
    "Disclaimer: Finova AI is an educational platform and not a registered investment adviser. "
    "This information is for educational purposes only and does not constitute financial advice."
)


class SubTask(BaseModel):
    """Represents a single atomic sub-task decomposed from a query."""
    task_id: str = Field(description="Unique identifier for the sub-task (e.g. 'task_1')")
    domain: Domain = Field(description="Target financial domain for this sub-task")
    intent: IntentType = Field(description="Granular intent for this sub-task")
    query_slice: str = Field(description="Segment of user query mapped to this sub-task")
    target_entity: str | None = Field(default=None, description="Extracted entity (e.g. ticker, coin, or metric)")
    status: Literal["pending", "success", "fallback", "filtered", "error", "failed"] = Field(
        default="pending",
        description="Execution lifecycle status",
    )


class DecompositionPlan(BaseModel):
    """Structured decomposition plan for single- or multi-intent queries."""
    original_query: str = Field(description="Raw user query text")
    is_compound: bool = Field(default=False, description="True if query contains multiple distinct intents")
    sub_tasks: list[SubTask] = Field(default_factory=list, description="Ordered list of sub-tasks to execute")


class RoutingDecision(BaseModel):
    """Output of the fast-path or semantic classifier."""
    query: str = Field(description="Query evaluated")
    domain: Domain = Field(description="Primary classified domain")
    intent: IntentType = Field(description="Primary classified intent")
    is_fast_path: bool = Field(default=True, description="True if classified without LLM inference")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Routing confidence score")
    entities: list[str] = Field(default_factory=list, description="Extracted symbols, tickers, or asset names")
    is_compound: bool = Field(default=False, description="True if query contains compound indicators")
    reason: str = Field(default="", description="Diagnostic rationale for the routing decision")


class SubTaskExecutionMetadata(BaseModel):
    """Execution telemetry for individual decomposed sub-tasks."""
    task_id: str
    domain: str
    intent: str
    target: str | None = None
    status: Literal["success", "fallback", "filtered", "error", "failed"]
    latency_ms: float = 0.0


class OrchestratorResponse(BaseModel):
    """TradeWise-ready unified response schema for the Finova Orchestrator."""
    query: str
    resolved_query: str | None = Field(default=None, description="Contextually resolved query for follow-up turns")
    answer: str
    grounding_status: Literal["fully_grounded", "partially_grounded", "ungrounded"]
    citations: list[Citation] = Field(default_factory=list)
    market_data: MarketDataProvenance | None = None
    market_data_list: list[MarketDataProvenance] = Field(
        default_factory=list,
        description="Supports multiple companies in comparative queries",
    )
    crypto_data: dict[str, Any] | None = Field(
        default=None,
        description="Cryptocurrency price and market provenance data",
    )
    derivatives_data: dict[str, Any] | None = Field(
        default=None,
        description="Options and derivatives payoff and Greeks data",
    )
    portfolio_data: dict[str, Any] | None = Field(
        default=None,
        description="Simulated portfolio analytics and what-if stress test data",
    )
    news_data: list[dict[str, Any]] | None = Field(
        default=None,
        description="Verified financial and regulatory news articles",
    )
    quiz_data: dict[str, Any] | None = Field(
        default=None,
        description="Quiz questions presentation or evaluation payload",
    )
    onboarding_data: list[dict[str, Any]] | None = Field(
        default=None,
        description="System capabilities and FAQ entries",
    )
    grounding_sources: list[str] = Field(
        default_factory=list,
        description="Grounding source identifiers",
    )
    domain_detected: Domain
    sub_tasks: list[SubTaskExecutionMetadata] = Field(default_factory=list)
    agent_name: str = "Finova Orchestrator"
    disclaimer: str = DEFAULT_DISCLAIMER
    model_used: str = ""
    latency_ms: float = 0.0
    topic: str | None = Field(default=None, description="Resolved educational topic name")
    related_concepts: list[str] = Field(default_factory=list, description="Related concept chips")
    suggested_next: list[str] = Field(default_factory=list, description="Pedagogical next inquiry suggestions")

