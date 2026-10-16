"""
Unit and Integration Tests for Finova AI Phase 7 Evaluation Harness (Stage 7A).
Validates evaluation schemas, dataset integrity, runner execution, and immutable historical baseline.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.eval.models import (
    HISTORICAL_BASELINE_SNAPSHOT,
    BaselineSnapshot,
    EvalCase,
    EvalCaseResult,
    EvalMetricResult,
    EvalReport,
    EvalSuite,
    EvalSuiteResult,
)
from scripts.eval_runner import EvalRunner, generate_markdown_scorecard

BASE_DIR = Path(__file__).resolve().parent.parent
EVAL_DIR = BASE_DIR / "data" / "evals"


def test_eval_models_schema_validation() -> None:
    """Verify standard Pydantic models instantiate and serialize cleanly."""
    case = EvalCase(
        case_id="TEST_001",
        category="routing",
        query="What is the price of TCS?",
        expected_domain="EQUITY",
        expected_intent="quote",
        expected_outcome="pass",
        tags=["unit_test", "offline"],
    )
    assert case.case_id == "TEST_001"
    assert case.prompt_text == "What is the price of TCS?"

    suite = EvalSuite(
        suite_id="test_suite",
        name="Test Suite",
        category="routing",
        cases=[case],
    )
    assert suite.suite_id == "test_suite"
    assert len(suite.cases) == 1

    metric = EvalMetricResult(
        metric_name="test_accuracy",
        category="routing",
        score=1.0,
        total_cases=1,
        passed_cases=1,
        passed=True,
    )
    assert metric.passed is True

    suite_res = EvalSuiteResult(
        suite_id="test_suite",
        category="routing",
        total_cases=1,
        passed_cases=1,
        accuracy=1.0,
        metric_results=[metric],
    )
    assert suite_res.accuracy == 1.0

    report = EvalReport(
        timestamp="2026-09-12T00:00:00Z",
        mode="offline",
        total_suites=1,
        total_cases=1,
        passed_cases=1,
        overall_accuracy=1.0,
        baseline_snapshot=HISTORICAL_BASELINE_SNAPSHOT,
        suite_results=[suite_res],
        overall_metrics=[metric],
    )
    dumped = report.model_dump_json()
    assert "eval_report" in dumped
    assert "378" in dumped


def test_immutable_historical_baseline_snapshot() -> None:
    """Verify permanent Phase 6 historical baseline is strictly 378 passed / 1 skipped / 0 failed."""
    snapshot = HISTORICAL_BASELINE_SNAPSHOT
    assert snapshot.phase_6_passed == 378
    assert snapshot.phase_6_skipped == 1
    assert snapshot.phase_6_failed == 0
    assert snapshot.phase_6_total == 379
    assert snapshot.status == "locked_baseline"
    assert "test_yfinance_provider_get_historical_summary" in snapshot.skipped_test_id
    assert snapshot.full_pyright_errors == 2


def test_all_eval_dataset_json_files_are_valid() -> None:
    """Ensure all JSON datasets under data/evals parse into valid EvalSuite instances."""
    assert EVAL_DIR.exists(), f"Evals dir missing: {EVAL_DIR}"

    json_files = list(EVAL_DIR.rglob("*.json"))
    assert len(json_files) >= 15, f"Expected at least 15 eval datasets, found {len(json_files)}"

    categories_found: set[str] = set()
    total_cases = 0

    for fpath in json_files:
        raw_text = fpath.read_text(encoding="utf-8")
        # Validate valid JSON
        data = json.loads(raw_text)
        assert "suite_id" in data, f"Missing suite_id in {fpath}"
        assert "cases" in data, f"Missing cases in {fpath}"

        # Validate Pydantic schema
        suite = EvalSuite.model_validate_json(raw_text)
        assert len(suite.cases) > 0, f"Suite {suite.suite_id} has 0 cases in {fpath}"
        categories_found.add(suite.category.lower())
        total_cases += len(suite.cases)

    # Verify all 5 core evaluation categories are present
    assert "routing" in categories_found
    assert "rag" in categories_found
    assert "safety" in categories_found
    assert "tools" in categories_found
    assert "memory" in categories_found
    assert total_cases >= 70, f"Expected >= 70 total cases across datasets, got {total_cases}"


def test_eval_runner_offline_mode_execution() -> None:
    """Verify EvalRunner executes deterministically offline without network calls."""
    runner = EvalRunner(mode="offline", eval_dir=EVAL_DIR)
    report = runner.run_all()

    assert report.mode == "offline"
    assert report.total_suites >= 15
    assert report.total_cases >= 70
    assert report.error_cases == 0, f"Evaluation runner produced {report.error_cases} unhandled errors"
    assert report.baseline_snapshot.phase_6_passed == 378
    assert report.overall_accuracy > 0.70  # Baseline accuracy expected around ~83% prior to Stage 7B-7J hardening


def test_eval_runner_suite_filter() -> None:
    """Verify EvalRunner can filter and execute an individual suite."""
    runner = EvalRunner(mode="offline", eval_dir=EVAL_DIR)
    report = runner.run_all(suite_filter="routing_ambiguous")

    assert report.total_suites == 1
    assert report.suite_results[0].suite_id == "routing_ambiguous"
    assert report.total_cases == 6
    assert report.passed_cases == 6
    assert report.suite_results[0].accuracy == 1.0


def test_generate_markdown_scorecard() -> None:
    """Verify markdown scorecard generation contains all essential summary sections."""
    runner = EvalRunner(mode="offline", eval_dir=EVAL_DIR)
    report = runner.run_all(suite_filter="routing_ambiguous")
    scorecard = generate_markdown_scorecard(report)

    assert "# Finova AI — Stage 7A Evaluation Baseline Scorecard" in scorecard
    assert "378" in scorecard
    assert "routing_ambiguous" in scorecard
    assert "100.0%" in scorecard
