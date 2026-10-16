<!-- Generated against commit: 42228bb55d6016ffff439024bbf4aec135269f95 | Date: 2026-09-13 | Verified against live repository state: YES -->

# Part 37: Complete Finova AI Engineering Curriculum

This curriculum is an engineering roadmap designed to take you from a foundational understanding of web development and Python to complete architectural mastery, operational ownership, and independent stewardship of the Finova AI codebase.

Unlike generic computer science tutorials, every topic in this curriculum is directly anchored to specific files, classes, models, and tests within this repository.

---

## Level 1 — Foundations: Core Language & Toolchain

### 1.1 Python Type Hints & Static Typing
- **WHAT**: Type annotations using Python's `typing` module (`Literal`, `Union`, `Optional`, `Callable`, `TypeVar`, `ClassVar`).
- **WHY FINOVA NEEDS IT**: The multi-agent router, Pydantic schemas, and memory validator rely on compile-time and runtime type checking to eliminate runtime `TypeError` exceptions across 50 test suites.
- **WHERE IT EXISTS**: Throughout `app/router/models.py`, `app/safety/validator.py`, and `app/tools/market/models.py`.
- **WHAT YOU SHOULD UNDERSTAND**: How `Literal["call", "put"]` restricts strings to exact enums, and how Python 3.10+ union syntax (`X | None`) replaces `Optional[X]`.
- **PREREQUISITES**: Basic Python syntax.
- **COMMON CONFUSIONS**: Confusing static typing hints (which Python ignores at runtime by default) with runtime validation enforced by Pydantic.
- **PRACTICE TASK**: Inspect `app/tools/derivatives/models.py` lines 12–15; identify how `OptionType` and `OptionPosition` are typed.
- **YOU UNDERSTAND THIS WHEN**: You can write a new Pydantic schema using strict `Literal` tags and understand why an invalid string raises a `ValidationError`.

---

### 1.2 Pydantic v2 Data Modeling & Validation
- **WHAT**: Python's industry-standard data validation library based on Python type annotations.
- **WHY FINOVA NEEDS IT**: Enforces strict schema conformity on all inbound HTTP requests, internal tool outputs, and outbound API payloads.
- **WHERE IT EXISTS**: `app/router/models.py`, `app/conversations/models.py`, `app/tools/market/models.py`.
- **WHAT YOU SHOULD UNDERSTAND**: How `BaseModel`, `Field(description=..., ge=..., le=...)`, and `@field_validator` work; difference between `.model_dump()` and `.model_dump_json()`.
- **PREREQUISITES**: Python classes, type hints.
- **COMMON CONFUSIONS**: Believing Pydantic mutates data silently; Pydantic coerces types if possible (e.g. `"123"` to `123`) unless strict mode is enabled.
- **PRACTICE TASK**: Read `app/conversations/models.py` lines 98–162 to see how `AssistantMessageMetadata` filters response fields.
- **YOU UNDERSTAND THIS WHEN**: You can explain why `extract_assistant_metadata()` strips `query` and `answer` before persisting to SQLite.

---

### 1.3 FastAPI & ASGI Request Lifecycle
- **WHAT**: Modern, high-performance Python web framework for building REST APIs using ASGI (Asynchronous Server Gateway Interface).
- **WHY FINOVA NEEDS IT**: Exposes modular REST endpoints with automatic OpenAPI documentation (`/docs`), type coercion, and error handling.
- **WHERE IT EXISTS**: `app/main.py`, `app/api/*.py`.
- **WHAT YOU SHOULD UNDERSTAND**: How routers are mounted via `app.include_router(prefix=..., tags=...)`, how query parameters (`Query(...)`) differ from request bodies (`BaseModel`), and how FastAPI handles synchronous vs asynchronous route functions.
- **PREREQUISITES**: HTTP protocol, Python decorators.
- **COMMON CONFUSIONS**: Believing all FastAPI route functions must be declared `async def`. In Finova, synchronous route handlers (`def health():`) run in Uvicorn's threadpool to prevent blocking the event loop during heavy CPU tasks (ONNX embeddings and regex matching).
- **PRACTICE TASK**: Inspect `app/main.py` lines 20–45 and trace how 12 routers are aggregated.
- **YOU UNDERSTAND THIS WHEN**: You can create a new route in `app/api/` that accepts a validated Pydantic model and returns a typed response.

---

### 1.4 SQLite3, WAL Mode, and ACID Transactions
- **WHAT**: Embedded, serverless, relational database engine compiled directly into Python.
- **WHY FINOVA NEEDS IT**: Stores persistent conversations (`data/conversations.db`) and user memory preferences (`data/memory.db`) with zero external daemon configuration.
- **WHERE IT EXISTS**: `app/conversations/store.py`, `app/memory/store.py`.
- **WHAT YOU SHOULD UNDERSTAND**: Parameterized queries (`?` placeholders) to prevent SQL injection, Write-Ahead Logging (`PRAGMA journal_mode=WAL;`), and SQLite foreign key constraints.
- **PREREQUISITES**: Basic SQL (SELECT, INSERT, UPDATE, DELETE).
- **COMMON CONFUSIONS**: Assuming SQLite cannot handle concurrent reads and writes; WAL mode allows infinite concurrent readers alongside a single active writer.
- **PRACTICE TASK**: Inspect `app/conversations/store.py` lines 20–55 and identify how SQLite tables and indexes are initialized.
- **YOU UNDERSTAND THIS WHEN**: You can explain why `sqlite3.connect()` is configured with `timeout=5.0` to handle lock contention.

---

### 1.5 React 19, TypeScript, and Vite Dev Server
- **WHAT**: Modern frontend architecture combining React functional components, TypeScript static typing, and Vite's lightning-fast ES module bundler.
- **WHY FINOVA NEEDS IT**: Powers the high-performance "Marigold Field & Maroon-Espresso" user interface with real-time markdown streaming, interactive cards, and zero build latency.
- **WHERE IT EXISTS**: `frontend/src/`, `frontend/vite.config.ts`, `frontend/package.json`.
- **WHAT YOU SHOULD UNDERSTAND**: Component composition, hooks (`useState`, `useEffect`, `useCallback`, `useMemo`), Vite proxy configuration (`vite.config.ts` forwarding `/api` to port 8000), and TypeScript interface definitions.
- **PREREQUISITES**: Basic JavaScript, HTML, CSS.
- **COMMON CONFUSIONS**: Confusing Vite's local dev server (`npm run dev` with HMR) with the production Rollup bundle (`npm run build`).
- **PRACTICE TASK**: Inspect `frontend/vite.config.ts` to see how `/api` is proxied to `http://127.0.0.1:8000`.
- **YOU UNDERSTAND THIS WHEN**: You can create a new React card component in `frontend/src/components/cards/` that renders typed JSON props from the backend.

---

## Level 2 — Finova Core Architecture

### 2.1 Multi-Agent Orchestration & Central Routing
- **WHAT**: The central decision engine (`CentralRouter` & `CentralOrchestrator`) that classifies user queries and delegates execution to specialized tutors.
- **WHY FINOVA NEEDS IT**: Eliminates monolithic LLM confusion by routing options questions to derivatives specialists, stock quotes to deterministic market tools, and budgeting queries to personal finance calculators.
- **WHERE IT EXISTS**: `app/router/central.py`, `app/router/orchestrator.py`, `app/router/models.py`.
- **WHAT YOU SHOULD UNDERSTAND**: Fast-path intent matching, multi-intent query decomposition (`DecompositionPlan`), and domain classification.
- **PREREQUISITES**: Level 1 (Python, FastAPI, Pydantic).
- **COMMON CONFUSIONS**: Thinking routing always calls an LLM. In Finova, >90% of routing is fast-path regex and keyword matching running in <1ms.
- **PRACTICE TASK**: Trace how `app/router/central.py` classifies `"What is Reliance trading at?"` as a fast-path market intent.
- **YOU UNDERSTAND THIS WHEN**: You can trace any query from `central_orchestrator.ask()` to its target agent.

---

### 2.2 Deterministic Financial Tools vs. Generative Math
- **WHAT**: Pure Python mathematical functions executing financial formulas with zero LLM involvement.
- **WHY FINOVA NEEDS IT**: LLMs hallucinate numbers and make compounding errors. SIPs, compounding growth, and options payoffs must be mathematically provable.
- **WHERE IT EXISTS**: `app/tools/calc/compounding.py`, `app/tools/derivatives/payoff.py`.
- **WHAT YOU SHOULD UNDERSTAND**: The annuity due SIP formula $M = P \times [\frac{(1+i)^k - 1}{i}] \times (1+i)$, Black-Scholes Greek definitions, and discrete payoff tables.
- **PREREQUISITES**: High-school algebra, compound interest concepts.
- **COMMON CONFUSIONS**: Assuming the LLM calculates the numbers and Python formats them. In Finova, Python does 100% of the math; the LLM merely writes surrounding explanatory prose or is bypassed entirely.
- **PRACTICE TASK**: Run `tests/test_calculator.py` and inspect why ₹10,000/month for 10 years at 12% yields exactly ₹23,23,391.
- **YOU UNDERSTAND THIS WHEN**: You can add a new deterministic calculation (e.g. PPF or loan EMI) without touching the LLM.

---

### 2.3 Secondary Safety & Regulatory Guardrails
- **WHAT**: Pre-inference deterministic regex and structural safety validator.
- **WHY FINOVA NEEDS IT**: Under SEBI regulations, unauthorized AI platforms cannot provide stock recommendations, price targets, or portfolio allocation advice.
- **WHERE IT EXISTS**: `app/safety/validator.py`, `app/router/safety.py`.
- **WHAT YOU SHOULD UNDERSTAND**: Structural pattern matching, roleplay evasion detection, guaranteed return filtering, and sub-millisecond execution.
- **PREREQUISITES**: Regular expressions (`re` module).
- **COMMON CONFUSIONS**: Assuming safety guardrails run *after* the LLM generates text. Finova intercepts unsafe queries *before* the LLM is invoked, saving 100% of GPU compute.
- **PRACTICE TASK**: Inspect `ROLEPLAY_ADVISORY_PATTERNS` in `app/safety/validator.py` lines 45–65.
- **YOU UNDERSTAND THIS WHEN**: You can write a regex that intercepts a new adversarial advisory bypass and verify it via `tests/test_red_team_safety.py`.

---

## Level 3 — AI, RAG, & Local LLM Systems

### 3.1 Vector Embeddings & FastEmbed
- **WHAT**: Generating dense 384-dimensional semantic vector representations of financial text using `BAAI/bge-small-en-v1.5` running on ONNX Runtime.
- **WHY FINOVA NEEDS IT**: Enables semantic search across SEBI regulatory booklets without cloud dependencies or heavy PyTorch overhead.
- **WHERE IT EXISTS**: `app/rag/embeddings.py`, `app/rag/retriever.py`.
- **WHAT YOU SHOULD UNDERSTAND**: Cosine similarity dot products, vector dimensions, and ONNX Runtime CPU SIMD acceleration.
- **PREREQUISITES**: Vector dot products, linear algebra basics.
- **COMMON CONFUSIONS**: Believing embedding models "understand" text. They project semantic relationships into high-dimensional geometric space where related concepts cluster together.
- **PRACTICE TASK**: Inspect `app/rag/embeddings.py` to see how `FastEmbed` is initialized with `bge-small-en-v1.5`.
- **YOU UNDERSTAND THIS WHEN**: You can explain why a 384-dimension model was chosen over a 1024-dimension model for local desktop execution.

---

### 3.2 Qdrant Local Vector Database
- **WHAT**: High-performance, Rust-backed vector search engine running in embedded local storage mode (`data/qdrant_storage/`).
- **WHY FINOVA NEEDS IT**: Provides HNSW indexing, payload metadata filtering, and sub-10ms similarity search without requiring a Docker container or cloud service.
- **WHERE IT EXISTS**: `app/rag/vector_store.py`, `scripts/ingest_docs.py`.
- **WHAT YOU SHOULD UNDERSTAND**: Qdrant collections, payloads, HNSW graph indexing, and score thresholds.
- **PREREQUISITES**: Level 1 (File paths, storage).
- **COMMON CONFUSIONS**: Expecting Qdrant to run on a network port like `6333`. In Finova, it runs in embedded mode directly accessing disk files.
- **PRACTICE TASK**: Inspect `scripts/ingest_docs.py` to see how PDFs are parsed, chunked, and upserted into Qdrant.
- **YOU UNDERSTAND THIS WHEN**: You can inspect collection stats and query the vector store directly using Python.

---

### 3.3 Grounding, Citation Integrity, & Hallucination Defense
- **WHAT**: Deterministic verification cross-referencing generated citation markers against retrieved chunk IDs.
- **WHY FINOVA NEEDS IT**: Guarantees that every legal or regulatory claim cites real, retrieved SEBI documentation.
- **WHERE IT EXISTS**: `app/rag/validator.py`, `app/rag/service.py`.
- **WHAT YOU SHOULD UNDERSTAND**: Chunk ID extraction, set intersection verification, and grounding status transitions (`fully_grounded`, `partially_grounded`, `ungrounded`).
- **PREREQUISITES**: Sets, string parsing.
- **COMMON CONFUSIONS**: Assuming the LLM "knows" when it is hallucinating. Citation validation must be enforced externally by code.
- **PRACTICE TASK**: Run `tests/test_rag.py` and inspect how hallucinated citation tags are purged.
- **YOU UNDERSTAND THIS WHEN**: You can explain what happens when an LLM cites `[SEBI-FAKE-01]`.

---

### 3.4 Local Inference with Ollama & Qwen 2.5 7B
- **WHAT**: Quantized local LLM execution via Ollama (`qwen2.5:7b-instruct`).
- **WHY FINOVA NEEDS IT**: Synthesizes natural language educational explanations completely offline on consumer hardware.
- **WHERE IT EXISTS**: `app/llm/client.py`, `app/llm/llm_client.py`.
- **WHAT YOU SHOULD UNDERSTAND**: HTTP REST interaction with `http://127.0.0.1:11434/api/generate`, `temperature=0.1`, and token bounding via `num_predict=600`.
- **PREREQUISITES**: HTTP clients, JSON.
- **COMMON CONFUSIONS**: Believing Ollama is an AI model. Ollama is a C++/Go *runtime* that runs quantized GGUF model weights.
- **PRACTICE TASK**: Test Ollama generation using `curl.exe -s http://127.0.0.1:11434/api/generate -d '{"model":"qwen2.5:7b-instruct","prompt":"Hi"}'`.
- **YOU UNDERSTAND THIS WHEN**: You can explain why `num_predict: 600` prevents latency spikes and memory runaway.

---

## Level 4 — Financial Intelligence & Market Systems

### 4.1 Market Data Architecture & Clock Invariants
- **WHAT**: Multi-provider market data orchestration with caching, failover, validation, and official exchange clock schedules.
- **WHY FINOVA NEEDS IT**: Ingests, normalizes, and validates stock quotes from Yahoo Finance and Twelve Data while adhering strictly to Indian Standard Time (IST) trading sessions.
- **WHERE IT EXISTS**: `app/tools/market/clock.py`, `app/tools/market/validator.py`, `app/tools/market/service.py`.
- **WHAT YOU SHOULD UNDERSTAND**: IST exchange hours (09:15–15:30 IST), official NSE holiday calendar for 2026, and data freshness states (`realtime`, `delayed`, `last_traded_close`, `stale_cached_fallback`).
- **PREREQUISITES**: Python `datetime`, `zoneinfo`.
- **COMMON CONFUSIONS**: Labeling data fetched on Sunday as "delayed". On Sunday, the market is closed, so the data is `last_traded_close`.
- **PRACTICE TASK**: Inspect `app/tools/market/clock.py` lines 30–80 to see how 2026 NSE holidays are hardcoded.
- **YOU UNDERSTAND THIS WHEN**: You can explain how `MarketDataValidator` determines whether a quote is delayed or closed.

---

### 4.2 Cryptocurrency & Offline Resilience
- **WHAT**: Free public CoinGecko data integration with strict production offline isolation.
- **WHY FINOVA NEEDS IT**: Provides live crypto prices (BTC, ETH, SOL) without paid API keys while preventing sandbox fallback data from leaking into production.
- **WHERE IT EXISTS**: `app/tools/crypto/service.py`, `app/tools/crypto/providers/coingecko_provider.py`.
- **WHAT YOU SHOULD UNDERSTAND**: In-memory TTL caching (60s), provider interfaces (`BaseCryptoProvider`), and `allow_offline_fallback=False` production isolation.
- **PREREQUISITES**: Level 1 (Classes, interfaces).
- **COMMON CONFUSIONS**: Believing unit tests use live CoinGecko APIs. Unit tests run hermetically using mock providers or explicit fallback flags.
- **PRACTICE TASK**: Inspect `app/tools/crypto/providers/coingecko_provider.py` line 47 and verify the default parameter for `allow_offline_fallback`.
- **YOU UNDERSTAND THIS WHEN**: You can explain why silent fallback data is dangerous in financial software.

---

## Level 5 — Production Engineering & System Hardening

### 5.1 IDOR Protection & Conversation Ownership
- **WHAT**: Server-side verification guaranteeing users can only read, update, or delete conversations they own.
- **WHY FINOVA NEEDS IT**: Protects sensitive financial history from unauthorized access across user sessions.
- **WHERE IT EXISTS**: `app/conversations/service.py` (`verify_ownership()`).
- **WHAT YOU SHOULD UNDERSTAND**: Insecure Direct Object Reference vulnerabilities and HTTP 403 Forbidden enforcement.
- **PREREQUISITES**: Web security fundamentals.
- **COMMON CONFUSIONS**: Relying on frontend UI hiding for security. Security must be asserted server-side in Python.
- **PRACTICE TASK**: Inspect `tests/test_conversations.py` to see the automated IDOR test asserting HTTP 403.
- **YOU UNDERSTAND THIS WHEN**: You can explain how `verify_ownership()` blocks unauthorized cross-user queries.

---

### 5.2 Indian PII Protection & The Right to Be Forgotten
- **WHAT**: Deterministic regex scanning for Indian financial PII (PAN, Aadhaar, phone, email) and statutory data deletion APIs.
- **WHY FINOVA NEEDS IT**: Complies with the Indian Digital Personal Data Protection (DPDP) Act, 2023.
- **WHERE IT EXISTS**: `app/memory/validator.py`, `app/api/memory.py`.
- **WHAT YOU SHOULD UNDERSTAND**: Regex patterns for PAN (`[A-Z]{5}[0-9]{4}[A-Z]`) and Aadhaar (`\d{4}\s?\d{4}\s?\d{4}`), and `DELETE /memory` cascading deletion.
- **PREREQUISITES**: Regular expressions.
- **COMMON CONFUSIONS**: Scrubbing PII after database insertion. PII must be rejected *before* database commit.
- **PRACTICE TASK**: Run `tests/test_memory.py` and inspect how PII attempts raise `MemoryValidationError`.
- **YOU UNDERSTAND THIS WHEN**: You can explain how Finova fulfills statutory Right to be Forgotten requests.

---

### 5.3 Test Suite Architecture & Benchmark Locking
- **WHAT**: Industrial test automation suite containing 525 passed unit, integration, and red-team tests across 50 test files.
- **WHY FINOVA NEEDS IT**: Prevents regressions across safety filters, financial math, RAG retrieval, and conversation persistence.
- **WHERE IT EXISTS**: `tests/`, `tests/test_red_team_safety.py`, `tests/test_eval_harness.py`.
- **WHAT YOU SHOULD UNDERSTAND**: Pytest fixtures, mock patching (`unittest.mock`), parametrized testing, and evaluation metrics.
- **PREREQUISITES**: Pytest.
- **COMMON CONFUSIONS**: Writing tests that call live external APIs. Production tests must be 100% hermetic and reproducible offline.
- **PRACTICE TASK**: Run `.venv-finova\Scripts\pytest.exe tests/test_red_team_safety.py -v`.
- **YOU UNDERSTAND THIS WHEN**: You can add a new feature alongside comprehensive unit and failure tests that pass on local Windows environments.

---

## 6. Recommended Learning Sequence

To study and master this repository in the most efficient, dependency-aware order:

```
Step 1: Environment & Toolchain
  Read Part 25 (Local Environment) -> Inspect scripts/run_local.py -> Run pytest

Step 2: Core Data Contracts & Storage
  Read Part 32 (Data Schemas) -> Inspect app/router/models.py -> Inspect SQLite stores

Step 3: Deterministic Tools & Market Systems
  Read Part 14 & Part 16 -> Inspect app/tools/calc/ and app/tools/market/

Step 4: Safety & Regulatory Defense
  Read Part 20 & Part 21 -> Inspect app/safety/validator.py -> Run test_red_team_safety.py

Step 5: Semantic RAG & Qdrant
  Read Part 09 & Part 11 -> Inspect app/rag/ -> Inspect scripts/ingest_docs.py

Step 6: Central Multi-Agent Orchestrator
  Read Part 12 & Part 13 -> Inspect app/router/central.py and orchestrator.py

Step 7: Persistent Conversations & Memory
  Read Part 18 & Part 19 -> Inspect app/conversations/ and app/memory/

Step 8: Frontend UI & Visualization
  Read Part 07 & Part 24 -> Inspect frontend/src/ -> Run npm run build & lint

Step 9: End-to-End Traces & Failure Modes
  Read Part 30 (Query Traces) and Part 34 (Failure Scenarios) -> Trace all 10 queries

Step 10: Complete Code Ownership
  Complete Part 40 (Code Ownership Exercises) -> Pass the Graduation Test
```
