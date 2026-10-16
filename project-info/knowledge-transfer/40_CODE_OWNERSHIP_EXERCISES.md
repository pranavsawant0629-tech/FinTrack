<!-- Generated against commit: 42228bb55d6016ffff439024bbf4aec135269f95 | Date: 2026-09-13 | Verified against live repository state: YES -->

# Part 40: Code Ownership & Practical Maintenance Exercises

To truly own a codebase, an engineer must move beyond reading documentation to diagnosing defects, navigating call stacks, adding verified features, and defending architectural invariants.

This guide provides structured, hands-on maintenance exercises categorized from beginner orientation to advanced system evolution. **Every exercise uses real paths, real classes, and real tests in this repository.**

---

## Level 1 — Repository Navigation & Orientation

### Exercise 1.1: Locate the Master Execution Entrypoint
- **OBJECTIVE**: Identify how the backend and frontend are orchestrated on local Windows environments.
- **FILES TO INSPECT**: `scripts/run_local.py`, `app/main.py`, `frontend/vite.config.ts`.
- **CONCEPTS REQUIRED**: Process supervision, subprocess spawning, port topology.
- **TASK**: Trace lines 55–100 of `scripts/run_local.py`. Determine what happens if the backend is already running on port 8000 when the script is executed.
- **INVARIANTS**: The script must never spawn duplicate Uvicorn instances on port 8000.
- **TESTS TO RUN**: Run `.venv-finova\Scripts\python.exe scripts/run_local.py` in a terminal.
- **EXPECTED RESULT**: It detects status 200 on `/health` and logs: `[BACKEND] [OK] Backend is already running on http://127.0.0.1:8000.`
- **HINTS**: Look at `check_backend_running()` in `scripts/run_local.py`.

---

### Exercise 1.2: Locate the Safety Guardrail Interceptor
- **OBJECTIVE**: Find where user prompts are intercepted before reaching the LLM or router.
- **FILES TO INSPECT**: `app/safety/validator.py`, `app/router/orchestrator.py`.
- **CONCEPTS REQUIRED**: Pre-inference safety filtering, regular expressions.
- **TASK**: Locate `SecondarySafetyValidator.validate()`. Identify the regex pattern that intercepts the query `"Tell me which stock to buy tomorrow"`.
- **INVARIANTS**: Safety validation must execute in <1ms without network calls.
- **TESTS TO RUN**: `.venv-finova\Scripts\pytest.exe tests/test_red_team_safety.py -v`.
- **EXPECTED RESULT**: All 30+ adversarial jailbreak tests pass with 100% rejection.

---

## Level 2 — Small Enhancements & Unit Testing

### Exercise 2.1: Add a Deterministic Fixed Deposit (FD) Calculator
- **OBJECTIVE**: Implement a deterministic mathematical calculator for bank Fixed Deposits without touching the LLM.
- **FILES TO INSPECT**: `app/tools/calc/compounding.py`, `tests/test_calculator.py`.
- **CONCEPTS REQUIRED**: Compound interest formula $A = P(1 + r/n)^{nt}$, input validation.
- **TASK**:
  1. Define `calculate_fd(principal: float, annual_rate_pct: float, tenure_years: float, compounding_frequency: int = 4)` in `app/tools/calc/compounding.py`.
  2. Validate $P > 0, r > 0, t > 0$.
  3. Write a unit test asserting that ₹1,00,000 at 7.5% quarterly compounding for 5 years yields ₹1,44,994.80.
- **INVARIANTS**: Zero LLM arithmetic; strictly deterministic float calculation.
- **TESTS TO RUN**: `.venv-finova\Scripts\pytest.exe tests/test_calculator.py`.
- **WHAT COULD GO WRONG**: Floating point rounding discrepancies; ensure outputs are rounded using `round(..., 2)`.

---

### Exercise 2.2: Add an Indian PII Validation Pattern for Driving Licenses
- **OBJECTIVE**: Extend PII scanning to reject Indian Driving License numbers in persistent memory.
- **FILES TO INSPECT**: `app/memory/validator.py`, `tests/test_memory.py`.
- **CONCEPTS REQUIRED**: Regex patterns for Indian state-issued driving licenses (`^[A-Z]{2}[0-9]{2}[0-9]{11}$`).
- **TASK**: Add the driving license regex to `MemoryValidator.PII_PATTERNS`.
- **INVARIANTS**: Rejects matching input before any write to `data/memory.db`.
- **TESTS TO RUN**: `.venv-finova\Scripts\pytest.exe tests/test_memory.py`.
- **EXPECTED RESULT**: Memory requests containing driving licenses raise `MemoryValidationError`.

---

## Level 3 — Read-Only Debugging & Root Cause Analysis

### Exercise 3.1: Read-Only Debugging — The Stale CoinGecko Price Mystery
- **OBJECTIVE**: Diagnose why unit tests pass while a production client reports seeing identical Bitcoin prices across 48 hours during an internet outage.
- **FILES TO INSPECT**: `app/tools/crypto/providers/coingecko_provider.py` (lines 30–50).
- **SCENARIO**: An engineer changed `allow_offline_fallback = True` as a default in `CoinGeckoProvider.__init__`.
- **TASK**: Explain why this change creates a critical factual grounding failure in production.
- **HINT**: Look at `FALLBACK_PRICES` dictionary.
- **ROOT CAUSE DIAGNOSIS**: If `allow_offline_fallback=True`, any network timeout or rate limit causes the provider to return static historical prices ($68,500.00 for BTC) without throwing an error, silently misleading users.

---

### Exercise 3.2: Read-Only Debugging — The SQLite Database Lock Timeout
- **OBJECTIVE**: Identify why a high-throughput load test throws `sqlite3.OperationalError: database is locked`.
- **FILES TO INSPECT**: `app/conversations/store.py` (lines 30–50).
- **TASK**: Inspect `init_db()` and connection creation. Determine whether WAL mode is active and what the connection timeout is set to.
- **ROOT CAUSE DIAGNOSIS**: If connections are opened without `PRAGMA journal_mode=WAL;` and `timeout=5.0`, concurrent write operations fail immediately rather than waiting for preceding transactions to commit.

---

## Level 4 — Feature Extensions & Schema Evolution

### Exercise 4.1: Extend Assistant Metadata with a New Tool Payload
- **OBJECTIVE**: Safely add a new field `tax_data: dict[str, Any] | None` to the assistant persistence schema.
- **FILES TO INSPECT**: `app/conversations/models.py`.
- **CONCEPTS REQUIRED**: Pydantic v2 schema evolution, backward compatibility.
- **TASK**:
  1. Add `tax_data: dict[str, Any] | None = None` to `AssistantMessageMetadata`.
  2. Update `extract_assistant_metadata()` to copy `tax_data` from `OrchestratorResponse`.
  3. Ensure `schema_version` remains `1` or increments safely.
- **INVARIANTS**: Must NOT break deserialization of historical messages stored in `data/conversations.db`.
- **TESTS TO RUN**: `.venv-finova\Scripts\pytest.exe tests/test_conversations.py`.

---

### Exercise 4.2: Add a Fast-Path Routing Alias for Gold & Silver
- **OBJECTIVE**: Enable instant market routing for sovereign gold bonds and commodity ETFs.
- **FILES TO INSPECT**: `app/tools/market/intent.py`, `app/router/central.py`.
- **TASK**: Add alias mappings `"gold"` -> `"GOLDBEES.NS"` and `"silver"` -> `"SILVERBEES.NS"` into the ticker classifier dictionary.
- **TESTS TO RUN**: `.venv-finova\Scripts\pytest.exe tests/test_market_tools.py`.
- **EXPECTED RESULT**: Queries like "What is gold trading at?" bypass the LLM and fetch `GOLDBEES.NS` quotes in <200ms.

---

## Level 5 — Advanced Architectural Evolution

### Exercise 5.1: Replace Yahoo Finance with a Statutory Exchange Feed
- **OBJECTIVE**: Design and implement a new market data provider conforming to `BaseMarketDataProvider`.
- **FILES TO INSPECT**: `app/tools/market/interfaces.py`, `app/tools/market/service.py`.
- **CONCEPTS REQUIRED**: Adapter pattern, error handling, normalization.
- **TASK**: Create `BSEDirectAdapter(BaseMarketDataProvider)` implementing `get_quote(symbol)`.
- **INVARIANTS**: Must emit standardized `MarketQuote` models; must pass all `MarketDataValidator` sanity and bounds checks.
- **TESTS TO RUN**: `.venv-finova\Scripts\pytest.exe tests/test_market_validator.py`.

---

## 6. Code Ownership Graduation Test

Before considering yourself an independent code owner of Finova AI, you should be able to execute and defend these 5 milestones without consulting assistance:

1. **The Zero-LLM Test**: Explain why executing a stock quote or SIP calculation consumes exactly zero LLM tokens and trace the code path in <2 minutes.
2. **The Ingestion Audit**: Re-ingest an official SEBI PDF into Qdrant using `scripts/ingest_docs.py`, verify font glyph repair, and inspect the resulting collection points.
3. **The Red-Team Lock**: Add a new adversarial prompt injection pattern to `app/safety/validator.py`, add a test case to `tests/test_red_team_safety.py`, and achieve a 100% pass rate.
4. **The Database Migration Defense**: Explain why SQLite assistant messages must use `schema_version: 1` and how you would migrate columns without losing chat history.
5. **The Clean Release Gate**: Run `git status`, `npm run build`, `npm run lint`, and `pytest`, verifying that all 525 tests pass and zero uncommitted files contaminate the repository.
