"""
Unit tests for Router models and schemas (app.router.models).
Validates schema initialization, defaults, field types, and serialization.
"""

import pytest
from app.router.models import (
    DEFAULT_DISCLAIMER,
    DecompositionPlan,
    OrchestratorResponse,
    RoutingDecision,
    SubTask,
    SubTaskExecutionMetadata,
)
from app.tools.market.models import MarketDataProvenance


def test_subtask_initialization():
    task = SubTask(
        task_id="task_1",
        domain="EQUITY",
        intent="quote",
        query_slice="what is Reliance trading at",
        target_entity="RELIANCE",
    )
    assert task.task_id == "task_1"
    assert task.domain == "EQUITY"
    assert task.intent == "quote"
    assert task.target_entity == "RELIANCE"
    assert task.status == "pending"


def test_decomposition_plan_defaults():
    plan = DecompositionPlan(original_query="What is an IPO?")
    assert plan.original_query == "What is an IPO?"
    assert plan.is_compound is False
    assert plan.sub_tasks == []


def test_routing_decision_serialization():
    decision = RoutingDecision(
        query="Current price of BTC",
        domain="CRYPTO",
        intent="quote",
        is_fast_path=True,
        confidence=0.95,
        entities=["BTC"],
        is_compound=False,
        reason="Matched crypto asset price pattern",
    )
    data = decision.model_dump()
    assert data["domain"] == "CRYPTO"
    assert data["intent"] == "quote"
    assert data["entities"] == ["BTC"]
    assert data["confidence"] == 0.95


def test_orchestrator_response_contract():
    provenance = MarketDataProvenance(
        symbol="TCS",
        company_name="Tata Consultancy Services Ltd",
        exchange="NSE",
        currency="INR",
        price=4200.50,
        change=25.50,
        change_percent=0.61,
        market_status="regular_trading",
        market_timestamp="2026-09-11T14:30:00+05:30",
        retrieved_at="2026-09-11T14:30:05+05:30",
        provider="Yahoo Finance",
        freshness_status="delayed",
    )
    sub_meta = SubTaskExecutionMetadata(
        task_id="task_1",
        domain="EQUITY",
        intent="quote",
        target="TCS",
        status="success",
        latency_ms=12.5,
    )
    resp = OrchestratorResponse(
        query="TCS price",
        answer="TCS is trading at ₹4,200.50",
        grounding_status="fully_grounded",
        citations=[],
        market_data=provenance,
        market_data_list=[provenance],
        grounding_sources=["live_market_data"],
        domain_detected="EQUITY",
        sub_tasks=[sub_meta],
        agent_name="Equity Tutor",
        disclaimer=DEFAULT_DISCLAIMER,
        model_used="deterministic_tools",
        latency_ms=15.0,
    )
    assert resp.grounding_status == "fully_grounded"
    assert resp.domain_detected == "EQUITY"
    assert resp.market_data is not None
    assert resp.market_data.symbol == "TCS"
    assert len(resp.market_data_list) == 1
    assert resp.sub_tasks[0].status == "success"
