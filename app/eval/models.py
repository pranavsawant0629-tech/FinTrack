"""
Standardized Pydantic Evaluation Schemas for Finova AI Phase 7.
Defines EvalCase, EvalSuite, EvalMetricResult, EvalReport, BaselineSnapshot, and EvalSuiteResult.
"""

from __future__ import annotations

import time
from typing import Any, Literal
from pydantic import BaseModel, Field


class EvalCase(BaseModel):
    """
    Standardized schema for an individual evaluation test case.
    Compatible with all Phase 7 evaluation categories (routing, safety, RAG, tools, memory).
    """
    case_id: str = Field(..., description="Unique case identifier (e.g. ROUTE_001, SAFE_005)")
    category: str = Field(..., description="Evaluation category or sub-category")
    query: str | None = Field(default=None, description="Input query text if query-based")
    input_prompt: str | None = Field(default=None, description="Alternative alias for input prompt")
    input_data: dict[str, Any] = Field(
        default_factory=dict,
        description="Structured parameter inputs (for tools, math, or memory context)",
    )
    expected_domain: str | None = Field(default=None, description="Expected domain classification")
    expected_intent: str | None = Field(default=None, description="Expected intent classification")
    expected_outcome: str | None = Field(
        default=None,
        description="Expected macro outcome (e.g. 'pass', 'block', 'safe_fulfillment', 'refusal', 'ungrounded')",
    )
    expected_grounding_status: Literal["fully_grounded", "partially_grounded", "ungrounded"] | None = Field(
        default=None,
        description="Expected grounding status (must strictly be one of the 3 existing statuses)",
    )
    expected_output: Any | None = Field(
        default=None,
        description="Expected deterministic mathematical or tool outputs (dict, string, float, etc.)",
    )
    expected_math: dict[str, Any] | None = Field(
        default=None,
        description="Expected mathematical ground truth key-values",
    )
    required_tokens: list[str] = Field(
        default_factory=list,
        description="Tokens that must appear in the text output",
    )
    forbidden_tokens: list[str] = Field(
        default_factory=list,
        description="Tokens that must NOT appear in the text output",
    )
    expected_subtasks: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Expected decomposed subtask domains and intents for compound queries",
    )
    expected_chunks: list[str] = Field(
        default_factory=list,
        description="Expected chunk IDs or document identifiers for retrieval evaluation",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Descriptive tags (e.g. ['critical', 'boundary', 'offline'])",
    )
    description: str = Field(
        default="",
        description="Human-readable description of test case intent and rationale",
    )

    @property
    def prompt_text(self) -> str:
        """Returns the active prompt text whether stored in query or input_prompt."""
        return self.query or self.input_prompt or ""


class EvalSuite(BaseModel):
    """
    Container for a collection of evaluation cases in a specific domain.
    Matches JSON files under data/evals/.
    """
    suite_id: str = Field(..., description="Unique suite identifier (e.g. routing_single_intent)")
    name: str = Field(..., description="Human-readable suite title")
    category: str = Field(..., description="High-level category (routing, rag, safety, tools, memory)")
    description: str = Field(default="", description="Description of the test suite purpose")
    cases: list[EvalCase] = Field(default_factory=list, description="List of evaluation cases")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Suite-level metadata")


class EvalCaseResult(BaseModel):
    """Result of executing an individual evaluation case."""
    case_id: str
    status: Literal["PASS", "FAIL", "SKIP", "ERROR"]
    category: str = ""
    input_prompt: str = ""
    expected_output: Any | None = None
    actual_output: Any | None = None
    error_message: str | None = None
    message: str = ""
    latency_ms: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvalMetricResult(BaseModel):
    """Calculated metric outcome for an evaluation dimension."""
    metric_name: str = Field(..., description="Name of the metric (e.g. Routing Accuracy)")
    category: str = Field(default="", description="Category (e.g. routing, safety, math)")
    score: float = Field(..., description="Measured percentage or count")
    total_cases: int = Field(default=0, description="Total cases evaluated")
    passed_cases: int = Field(default=0, description="Passed cases count")
    failed_cases: int = Field(default=0, description="Failed cases count")
    skipped_cases: int = Field(default=0, description="Skipped cases count")
    error_cases: int = Field(default=0, description="Error cases count")
    threshold: float | None = Field(default=None, description="Required target threshold")
    passed: bool = Field(..., description="Whether score satisfies the threshold")
    details: dict[str, Any] = Field(default_factory=dict, description="Diagnostic breakdown")


class BaselineSnapshot(BaseModel):
    """
    Immutable representation of the locked Phase 6 verification baseline.
    378 passed / 1 skipped / 0 failed.
    """
    phase: str = "Phase 6 Locked"
    phase_6_passed: int = 378
    phase_6_skipped: int = 1
    phase_6_failed: int = 0
    phase_6_total: int = 379
    status: str = "locked_baseline"
    skipped_test_id: str = (
        "tests/test_market_providers.py::test_yfinance_provider_get_historical_summary"
    )
    skipped_reason: str = (
        "Yahoo Finance returned an incomplete intraday bar with NaN close price / ProviderUnavailableError"
    )
    full_pyright_errors: int = 2
    pyright_baseline_file: str = "app/rag/embeddings.py"
    pyright_baseline_details: str = (
        "FastEmbed Generator type annotation missing type arguments and generator value iteration"
    )


HISTORICAL_BASELINE_SNAPSHOT = BaselineSnapshot()


class Phase5BaselineSnapshot(BaseModel):
    """
    Dedicated Phase 5 evaluation and verification baseline snapshot.
    Rigorously distinguishes:
    - Deterministic offline unit tests
    - Evaluation benchmark cases across categories
    - Optional live Ollama integration tests
    """
    phase: str = "Phase 5 Baseline"
    status: str = "phase_5_verified"
    timestamp: str = "2026-10-31T07:45:00Z"

    # Deterministic offline unit tests
    unit_tests_total: int = 717
    unit_tests_passed: int = 702
    unit_tests_failed: int = 15
    unit_tests_skipped: int = 0
    unit_tests_pass_rate: float = 0.9791

    # Evaluation benchmark cases (across all data/evals suites)
    eval_benchmark_total: int = 152
    eval_benchmark_passed: int = 147
    eval_benchmark_failed: int = 5
    eval_benchmark_skipped: int = 0
    eval_benchmark_pass_rate: float = 0.9671

    # Evaluation category metrics
    category_metrics: dict[str, dict[str, Any]] = Field(default_factory=dict)

    # Optional live Ollama integration tests
    live_ollama_status: str = "optional_live_integration"
    live_ollama_tests_total: int = 0
    live_ollama_tests_passed: int = 0
    live_ollama_tests_failed: int = 0
    live_ollama_tests_skipped: int = 0
    live_ollama_note: str = (
        "Live Ollama inference is optional and kept strictly separate from offline deterministic verification."
    )


PHASE_5_BASELINE_SNAPSHOT = Phase5BaselineSnapshot(
    category_metrics={
        "tools": {"total": 41, "passed": 41, "failed": 0, "accuracy": 1.0},
        "safety": {"total": 38, "passed": 38, "failed": 0, "accuracy": 1.0},
        "memory": {"total": 9, "passed": 9, "failed": 0, "accuracy": 1.0},
        "routing": {"total": 40, "passed": 36, "failed": 4, "accuracy": 0.90},
        "rag": {"total": 24, "passed": 23, "failed": 1, "accuracy": 0.9583},
    }
)


class EvalSuiteResult(BaseModel):
    """Execution results and metrics for an entire evaluation suite."""
    suite_id: str
    category: str
    total_cases: int = 0
    passed_cases: int = 0
    failed_cases: int = 0
    skipped_cases: int = 0
    error_cases: int = 0
    accuracy: float = 0.0
    metric_results: list[EvalMetricResult] = Field(default_factory=list)
    case_results: list[EvalCaseResult] = Field(default_factory=list)


class EvalReport(BaseModel):
    """
    Comprehensive structured report generated by eval_runner.py.
    """
    report_id: str = Field(default_factory=lambda: f"eval_report_{int(time.time())}")
    timestamp: str
    mode: Literal["offline", "online"]
    total_suites: int = 0
    total_cases: int = 0
    passed_cases: int = 0
    failed_cases: int = 0
    skipped_cases: int = 0
    error_cases: int = 0
    overall_accuracy: float = 0.0
    duration_seconds: float = 0.0
    baseline_snapshot: BaselineSnapshot = Field(default_factory=BaselineSnapshot)
    phase_5_baseline: Phase5BaselineSnapshot = Field(default_factory=lambda: PHASE_5_BASELINE_SNAPSHOT)
    suite_results: list[EvalSuiteResult] = Field(default_factory=list)
    overall_metrics: list[EvalMetricResult] = Field(default_factory=list)
