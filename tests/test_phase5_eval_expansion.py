"""
tests/test_phase5_eval_expansion.py

Verification tests for Phase 5 Evaluation Suite Expansion, Dual Baseline,
Extended Financial Math evaluation, and Adversarial Safety evaluation suites.
"""

import json
from pathlib import Path
import pytest

from app.eval.models import (
    HISTORICAL_BASELINE_SNAPSHOT,
    PHASE_5_BASELINE_SNAPSHOT,
    BaselineSnapshot,
    Phase5BaselineSnapshot,
    EvalSuite,
    EvalCase,
)
from scripts.eval_runner import EvalRunner


BASE_DIR = Path(__file__).resolve().parent.parent


def test_historical_baseline_snapshot_frozen():
    """Verify HISTORICAL_BASELINE_SNAPSHOT is immutable and preserves Phase 6 baseline exactly."""
    assert HISTORICAL_BASELINE_SNAPSHOT.phase == "Phase 6 Locked"
    assert HISTORICAL_BASELINE_SNAPSHOT.phase_6_passed == 378
    assert HISTORICAL_BASELINE_SNAPSHOT.phase_6_skipped == 1
    assert HISTORICAL_BASELINE_SNAPSHOT.phase_6_failed == 0
    assert HISTORICAL_BASELINE_SNAPSHOT.phase_6_total == 379
    assert HISTORICAL_BASELINE_SNAPSHOT.status == "locked_baseline"
    assert "test_yfinance_provider_get_historical_summary" in HISTORICAL_BASELINE_SNAPSHOT.skipped_test_id


def test_phase_5_baseline_snapshot_distinct():
    """Verify PHASE_5_BASELINE_SNAPSHOT is distinct and correctly configured."""
    assert isinstance(PHASE_5_BASELINE_SNAPSHOT, Phase5BaselineSnapshot)
    assert PHASE_5_BASELINE_SNAPSHOT.phase == "Phase 5 Baseline"
    assert PHASE_5_BASELINE_SNAPSHOT.status == "phase_5_verified"
    # Ensure it is not identical to historical snapshot
    assert PHASE_5_BASELINE_SNAPSHOT.phase != HISTORICAL_BASELINE_SNAPSHOT.phase
    assert "tools" in PHASE_5_BASELINE_SNAPSHOT.category_metrics
    assert "safety" in PHASE_5_BASELINE_SNAPSHOT.category_metrics
    assert "rag" in PHASE_5_BASELINE_SNAPSHOT.category_metrics
    assert "routing" in PHASE_5_BASELINE_SNAPSHOT.category_metrics
    assert "memory" in PHASE_5_BASELINE_SNAPSHOT.category_metrics


def test_extended_finance_math_suite_schema_and_count():
    """Verify data/evals/tools/extended_finance_math.json has exactly 25 valid cases."""
    path = BASE_DIR / "data" / "evals" / "tools" / "extended_finance_math.json"
    assert path.is_file(), f"Missing {path}"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    suite = EvalSuite.model_validate(data)
    assert suite.suite_id == "tools_extended_finance_math"
    assert suite.category == "tools"
    assert len(suite.cases) == 25

    categories = {c.category for c in suite.cases}
    assert "cagr" in categories
    assert "real_return" in categories
    assert "rule_of_72" in categories
    assert "sharpe_ratio" in categories
    assert "sortino_ratio" in categories
    assert "indian_number" in categories


def test_adversarial_safety_suite_schema_and_count():
    """Verify data/evals/safety/adversarial_expansion.json has at least 20 (25) valid cases."""
    path = BASE_DIR / "data" / "evals" / "safety" / "adversarial_expansion.json"
    assert path.is_file(), f"Missing {path}"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    suite = EvalSuite.model_validate(data)
    assert suite.suite_id == "safety_adversarial_expansion"
    assert suite.category == "safety"
    assert len(suite.cases) >= 20
    assert len(suite.cases) == 25

    # Check that positive controls exist and are tagged
    pos_controls = [c for c in suite.cases if "positive_control" in c.tags]
    assert len(pos_controls) >= 4
    for pc in pos_controls:
        assert pc.expected_outcome == "safe_fulfillment"


def test_eval_runner_executes_extended_finance_math_cleanly():
    """Verify EvalRunner executes the extended finance math suite with 100% pass rate."""
    runner = EvalRunner(mode="offline", eval_dir=str(BASE_DIR / "data" / "evals"))
    report = runner.run_all(suite_filter="tools_extended_finance_math")

    assert report.total_suites == 1
    assert report.total_cases == 25
    assert report.passed_cases == 25
    assert report.failed_cases == 0
    assert report.overall_accuracy == 1.0


def test_eval_runner_executes_adversarial_safety_cleanly():
    """Verify EvalRunner executes the adversarial safety suite with 100% pass rate."""
    runner = EvalRunner(mode="offline", eval_dir=str(BASE_DIR / "data" / "evals"))
    report = runner.run_all(suite_filter="safety_adversarial_expansion")

    assert report.total_suites == 1
    assert report.total_cases == 25
    assert report.passed_cases == 25
    assert report.failed_cases == 0
    assert report.overall_accuracy == 1.0


def test_rag_ooc_002_expected_outcome_preserved():
    """Verify data/evals/rag/out_of_corpus_eval.json preserves RAG_OOC_002 expected outcome as ungrounded."""
    path = BASE_DIR / "data" / "evals" / "rag" / "out_of_corpus_eval.json"
    assert path.is_file(), f"Missing {path}"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    cases = data.get("cases", [])
    ooc_002 = next((c for c in cases if c.get("case_id") == "RAG_OOC_002"), None)
    assert ooc_002 is not None, "RAG_OOC_002 not found in out_of_corpus_eval.json"
    assert ooc_002.get("expected_outcome") == "ungrounded"
