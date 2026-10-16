# Finova AI — Stage 7A Evaluation Baseline Scorecard

- **Execution Timestamp (UTC):** `2026-10-16T15:09:38.731742+00:00`
- **Execution Mode:** `OFFLINE` (Deterministic / Zero External Network)
- **Duration:** `1.76s`

## 1. Immutable Historical Baseline Snapshot

Permanent historical Phase 6 regression benchmark:

- **Passed:** `378`
- **Skipped:** `1` (Yahoo Finance external intraday skip)
- **Failed:** `0`
- **Status:** `LOCKED_BASELINE`

## 2. Evaluation Suite Summary

| Suite ID | Category | Total | PASS | FAIL | SKIP | ERROR | Accuracy |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| `rag_out_of_corpus` | `rag` | 3 | 2 | 1 | 0 | 0 | **66.7%** |

## 3. Aggregate Metrics

- **Total Test Cases Executed:** `3`
- **Passed Cases:** `2`
- **Failed Cases (Baseline Defect Documentation):** `1`
- **Skipped Cases:** `0`
- **Overall Evaluation Accuracy:** `66.7%`

## 4. Observed Baseline Vulnerabilities & Defect Documentation

As mandated by Phase 7 rules, pre-existing Phase 0–6 defects are preserved and documented:

1. **Prompt Injection Resistance:** Direct and indirect prompt injection attempts succeed against Phase 6 guardrails (to be hardened with secondary validator in Stage 7B).
2. **Derivatives Breakeven Boundary:** In `app/tools/derivatives/payoff.py`, Long Put when Strike < Premium clamps breakeven to `0.0` instead of `-10.0` (to be corrected in Stage 7D).
