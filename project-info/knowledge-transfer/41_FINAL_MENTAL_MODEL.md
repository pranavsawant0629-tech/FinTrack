<!-- Generated against commit: 42228bb55d6016ffff439024bbf4aec135269f95 | Date: 2026-09-13 | Verified against live repository state: YES -->

# Part 41: The Unified Mental Model of Finova AI

This is the definitive architectural and conceptual synthesis of Finova AI. It unifies every phase, subsystem, algorithm, and invariant into a single coherent mental model.

---

## 1. The Core Mental Models

### The One-Sentence Mental Model
> **Finova AI is a local-first, offline financial intelligence system that pairs deterministic Python tools and grounded regulatory vector search with an open-weights 7B LLM, enforcing statutory non-advisory safety guardrails before any token is generated.**

### The 30-Second Mental Model
> Traditional financial AI fails because it sends private user data to cloud servers, hallucinates mathematical calculations, and risks severe legal liability by giving unauthorized stock tips.
> 
> Finova AI solves this by running entirely on the user's workstation. Queries enter through a React interface to a local FastAPI backend. Before any model is called, a sub-millisecond safety gate intercepts stock tips and prompt injections. A central router directs math and live price queries to deterministic Python tools that completely bypass the LLM. 
> 
> For conceptual questions, the system retrieves official SEBI regulatory documents from a local Qdrant vector database, prompts a local Qwen 2.5 7B model running via Ollama, deterministically verifies that every citation is grounded in real text, and persists clean conversation state to local SQLite databases. It is fast, private, mathematically exact, and regulatory-compliant by design.

---

## 2. The Complete Architectural Topology

Below is the verified end-to-end architectural flow of Finova AI. Every box and arrow represents an actual, verified component in this repository:

```
+-----------------------------------------------------------------------------------------+
|                                        THE USER                                         |
+--------------------------------------------+--------------------------------------------+
                                             |
                                             v
+-----------------------------------------------------------------------------------------+
|                            FRONTEND (React 19 + TypeScript)                             |
|               Marigold Field & Maroon-Espresso UI | Specialized Cards                   |
+--------------------------------------------+--------------------------------------------+
                                             |
                                             | HTTP REST (Port 8000)
                                             v
+-----------------------------------------------------------------------------------------+
|                               API LAYER (FastAPI / Uvicorn)                             |
|             /conversations/send | /chat | /memory | /agents/* | /rag/retrieve           |
+--------------------------------------------+--------------------------------------------+
                                             |
                                             v
+-----------------------------------------------------------------------------------------+
|                        IDENTITY & CONVERSATION SERVICE LAYER                            |
|             IDOR Verification | Conversation Ownership | Bounded Context                |
+--------------------------------------------+--------------------------------------------+
                                             |
                                             v
+-----------------------------------------------------------------------------------------+
|                     PRE-INFERENCE SAFETY GATE (Deterministic Regex)                     |
|           app/safety/validator.py (SecondarySafetyValidator) | Sub-1ms Rejection        |
+----------------------+-------------------------------------+----------------------------+
                       |                                     |
    [VIOLATION DETECTED]                                     | [QUERY VALIDATED SAFE]
                       |                                     v
                       |      +-----------------------------------------------------------+
                       |      |                      CENTRAL ROUTER                       |
                       |      |      app/router/central.py (Fast-Path Intent & Tickers)   |
                       |      +------------------------------+----------------------------+
                       |                                     |
                       |         +---------------------------+---------------------------+
                       |         |                           |                           |
                       |         v                           v                           v
                       |  [DETERMINISTIC TOOLS]      [HYBRID QUERY]            [RAG PIPELINE]
                       |  - Market Quote Service     DecompositionPlan         - FastEmbed (BGE)
                       |  - SIP/Compound Calc        (Sub-tasks split)         - Qdrant Local Store
                       |  - Options Payoff Engine                              - SEBI Regulatory Text
                       |         |                           |                           |
                       |         | [BYPASSES LLM]            |                           v
                       |         |                           |               [LOCAL FOUNDATION LLM]
                       |         |                           |               Ollama (127.0.0.1:11434)
                       |         |                           |               qwen2.5:7b-instruct
                       |         |                           |               temp: 0.1, max: 600 tokens
                       |         |                           |                           |
                       |         v                           v                           v
                       |      +-----------------------------------------------------------+
                       |      |               CITATION & GROUNDING VALIDATOR              |
                       |      |        app/rag/validator.py (Validates Chunk ID Sets)     |
                       |      +------------------------------+----------------------------+
                       |                                     |
                       v                                     v
+-----------------------------------------------------------------------------------------+
|                                  RESPONSE COMPOSITION                                   |
|              OrchestratorResponse | Structured Tool Payloads | Disclaimers              |
+--------------------------------------------+--------------------------------------------+
                                             |
                                             v
+-----------------------------------------------------------------------------------------+
|                                   PERSISTENCE LAYER                                     |
|           data/conversations.db (schema_version: 1) | data/memory.db (ACID Upsert)      |
+--------------------------------------------+--------------------------------------------+
                                             |
                                             | Serialized JSON Payload
                                             v
+-----------------------------------------------------------------------------------------+
|                                    FRONTEND RENDERING                                   |
|           MessageItem (Markdown) | QuoteCard | OptionsCard | SIPCard | QuizCard         |
+-----------------------------------------------------------------------------------------+
```

---

## 3. Deep Layer-by-Layer Breakdown

### Layer 1: Client & Presentation (`frontend/src/`)
- **Technology**: React 19, TypeScript, Vite.
- **Role**: Renders an aesthetic, high-trust financial desktop interface. It parses markdown with LaTeX math formatting, renders citations inside expandable accordions, displays real-time interactive financial cards (Quote, SIP, Payoff, Quiz), and provides continuous pedagogical exploration chips.
- **Key Invariant**: The frontend is strictly a presentation layer. It performs zero business math and zero security filtering. All validation is enforced server-side.

### Layer 2: API Gateway (`app/main.py`, `app/api/`)
- **Technology**: FastAPI, Uvicorn, ASGI.
- **Role**: Exposes 12 modular routers. Handles HTTP serialization, CORS middleware, request schema validation, and health checks.
- **Key Invariant**: Synchronous handlers run in Uvicorn's worker threadpool to prevent blocking the event loop during heavy ONNX vector calculations.

### Layer 3: Conversation & Identity Lifecycle (`app/conversations/`)
- **Technology**: SQLite3, WAL mode.
- **Role**: Enforces server-side user ownership (`verify_ownership()`), prevents IDOR vulnerabilities, generates conversation titles, bounds multi-turn context (last 6 messages), and maintains ACID transactional message records.
- **Key Invariant**: Domain immutability. Once a conversation is created with a domain (e.g. `DERIVATIVES`), all subsequent turns stay with that specialist tutor.

### Layer 4: Deterministic Safety Gate (`app/safety/validator.py`)
- **Technology**: Pre-compiled Python regular expressions (`re`).
- **Role**: The guardian of the system. Intercepts specific investment advice, timing queries, guaranteed return claims, roleplay advisor impersonation, and prompt injection attacks.
- **Key Invariant**: Zero LLM calls, zero network calls, sub-millisecond latency (<1ms). Intercepts *before* routing or model generation.

### Layer 5: Central Router & Decomposer (`app/router/`)
- **Technology**: Python intent classification engine.
- **Role**: Dispatches queries to one of 8 domain agents (`EQUITY`, `CRYPTO`, `DERIVATIVES`, `PERSONAL_FINANCE`, `PORTFOLIO`, `NEWS`, `QUIZ`, `ONBOARDING`) or decomposes hybrid queries into parallel sub-tasks.
- **Key Invariant**: Fast-path short-circuiting. If a query is exclusively a ticker quote or calculation, it routes straight to tools without calling an LLM.

### Layer 6: Subsystem Execution Layer
- **Deterministic Tools (`app/tools/`)**: Pure Python compiled mathematics. Calculates annuity due SIPs, compound interest schedules, options payoff matrices, Black-Scholes Greeks, and live market quotes. Zero hallucination risk.
- **Semantic RAG (`app/rag/`)**: FastEmbed (`bge-small-en-v1.5`) encodes queries into 384-dimensional vectors; Qdrant searches local embedded disk storage (`data/qdrant_storage/`) for official SEBI regulatory chunks.
- **Foundation LLM (`app/llm/client.py`)**: Local Ollama daemon running `qwen2.5:7b-instruct` under temperature `0.1` and `num_predict: 600`. Synthesizes grounded natural language explanations.

### Layer 7: Grounding & Citation Validation (`app/rag/validator.py`)
- **Technology**: Set intersection and tag matching.
- **Role**: Inspects LLM generated text. Extracts citation tags (e.g. `[SEBI-EQ-01]`) and asserts that they match the exact chunk IDs returned by Qdrant. Purges hallucinated citations and sets `grounding_status`.

### Layer 8: Versioned Persistence (`conversations.db`, `memory.db`)
- **Technology**: Parameterized SQLite transactions.
- **Role**: Records messages with clean `schema_version: 1` assistant metadata (storing cards and citations while omitting redundant answer text) and updates user learner profiles with PII protection.

---

## 4. The Request Lifecycle Across 12 Canonical Scenarios

| Scenario | Safety Gate | Router Target | Subsystem Path | LLM Invoked? | Persistence Effect | User Result |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1. General Education** | Passes | `GENERAL` | System prompt + Ollama | Yes | Stored with `schema_version: 1` | Markdown explanation |
| **2. Equity RAG Query** | Passes | `EQUITY` | FastEmbed -> Qdrant -> Ollama | Yes | Stored with verified citations | Markdown + Citation Accordion |
| **3. Live Market Quote** | Passes | Fast-Path | `MarketDataService` -> Yahoo Finance | **NO (0 tokens)** | Stored with `market_data` dict | Interactive `QuoteCard` |
| **4. Hybrid Query** | Passes | Decomposer | RAG (Concept) + Tool (Quote) | Yes (Concept only)| Stored with text + quote card | Markdown text + `QuoteCard` |
| **5. Derivatives Payoff** | Passes | `DERIVATIVES`| `calculate_option_payoff()` | **NO (Math)** | Stored with `derivatives_data` | Payoff chart + SEBI 9/10 risk warning |
| **6. SIP Calculation** | Passes | `PERSONAL_FINANCE`| `calculate_sip()` annuity due | **NO (Math)** | Stored with `calculator_data` | Interactive `SIPCalculatorCard` |
| **7. Crypto Quote** | Passes | `CRYPTO` | `CoinGeckoProvider` (TTL cache) | Optional | Stored with `crypto_data` | Interactive `CryptoCard` |
| **8. Financial Quiz** | Passes | `QUIZ` | Qdrant RAG -> Quiz generator | Yes | Stored with `quiz_data` | Interactive clickable `QuizCard` |
| **9. Persisted Continuation**| Passes | Immutable Domain| Loads last 6 turns -> Ollama | Yes | Appends turn to conversation | Cohesive multi-turn answer |
| **10. Memory Extraction** | Passes | Background Hook | Regex extractor -> PII validator -> SQLite| Optional | Updates `user_memory` row | Profile updated toast |
| **11. Provider Failure** | Passes | Market / Crypto | Catches error -> Stale cache / Error | No | Stored with error metadata | "Data temporarily unavailable" |
| **12. Prompt Injection** | **REJECTED** | **BYPASSED** | Pipeline aborted in <1ms | **NO (0 tokens)** | Stored with `safety_blocked=True`| Canonical safety refusal card |

---

## 5. Data Lineage: What is Authoritative, Derived, Cached, and Generated

```
[AUTHORITATIVE TRUTH] 
  - Official SEBI Regulatory PDFs (Ingested offline via scripts/ingest_docs.py)
  - Compiled Python Mathematical Formulas (Annuity due, Black-Scholes Greeks)
  - 2026 NSE Official Holiday Calendar & IST Market Clock
  - Explicit User Declarations ("I am a beginner")

[DERIVED STATE]
  - 384-dimensional FastEmbed ONNX vector embeddings
  - Qdrant HNSW vector index points and cosine similarity scores
  - Aggregated Personalization Profile (assembled from unexpired user memories)

[CACHED STATE]
  - In-memory Market Data TTL Cache (60s expiration, thread-safe lock)
  - In-memory CoinGecko Crypto Cache (60s expiration)
  - Stale fallback market quotes (used strictly during network outages)

[GENERATED / SYNTHETIC]
  - Qwen 2.5 7B natural language explanatory prose
  - Conversational topic suggestions and pedagogical follow-up chips
```

---

## 6. Trust Boundaries

```
[UNTRUSTED ZONE]
  - Raw user input text (May contain prompt injections, jailbreaks, PII, SQL injection)
  - External public web APIs (Yahoo Finance, CoinGecko: May rate-limit, fail, or return bad prices)
  - LLM generated output (May hallucinate citations, numbers, or ungrounded claims)

[TRUSTED ENCLAVE]
  - Secondary Safety Validator (Regex and structural pattern gate)
  - Deterministic Financial Calculators (Pure compiled Python math)
  - Market Data Validator (Sanity, bounds, and freshness verification gate)
  - Citation Integrity Validator (Set-intersection verification against Qdrant)
  - SQLite Database Drivers (Parameterized SQL queries preventing injection)
```

---

## 7. The Architecture Invariants (Rules That Must Never Be Broken)

1. **The Deterministic Math Invariant**: Never allow the LLM to perform mathematical calculations. All financial math must execute in verified Python code.
2. **The Pre-Inference Safety Invariant**: Never evaluate regulatory safety *after* model generation. Intercept unsafe prompts before a single token reaches the LLM.
3. **The Grounding Verification Invariant**: Never trust LLM citation tags. Validate all citations against chunk IDs returned by Qdrant.
4. **The Local-First Sovereignty Invariant**: Never transmit user financial queries, memory, or history to third-party cloud servers.
5. **The Non-Advisory Invariant**: Never provide specific stock recommendations, buy/sell calls, price targets, or portfolio allocation advice.
6. **The Domain Immutability Invariant**: Never dynamically switch the domain agent of an existing conversation thread mid-stream.
7. **The Parameterized SQL Invariant**: Never construct SQL queries using string formatting or concatenation.
8. **The Explicit Memory Invariant**: Never use probabilistic LLM extraction to write to persistent user memory.
9. **The Offline Isolation Invariant**: Never allow sandbox fallback data to silently masquerade as live market prices in production.
10. **The Token Bound Invariant**: Never invoke local LLMs without `num_predict: 600` and low temperature (`0.1`).

---

## 8. Why Each Major Technology Exists

- **Python 3.13**: Rich ecosystem for financial math, data validation, and AI libraries.
- **FastAPI**: Type-safe REST API routing with automatic OpenAPI docs and high throughput.
- **Pydantic v2**: High-performance Rust-backed data validation and schema enforcement.
- **SQLite3**: Zero-maintenance, ACID-compliant, self-contained relational storage in a single file.
- **Qdrant**: Embedded Rust-powered vector database with HNSW indexing and metadata filtering.
- **FastEmbed**: ONNX Runtime vector embeddings avoiding 3GB of PyTorch overhead.
- **BAAI/bge-small-en-v1.5**: 384-dimensional dense semantic vectors with ultra-fast 6ms CPU embedding.
- **Ollama**: Standalone runtime for GGUF quantized models with automatic GPU VRAM offloading.
- **Qwen 2.5 7B Instruct**: Best-in-class open-weights model for structured data and instruction following.
- **React 19 & TypeScript**: Responsive, type-safe frontend UI with instant hot module replacement.
- **Vite**: Sub-second dev server HMR and 413ms production bundle compilation.
- **yfinance**: Free public market data adapter for Indian equities (NSE/BSE).
- **CoinGecko**: Public cryptocurrency quotes with zero paid API requirements.
- **Pytest**: Automated testing harness locking 525 passed tests across 50 test files.
- **Git**: Append-only cryptographic DAG tracking 33 verified development commits.

---

## 9. The Phase-by-Phase Evolution (Phase 0 to Phase 13)

- **Phase 0 (`9507118`)**: Workspace genesis, Python environment, directory scaffolding.
- **Phase 1 (`cc532f9`, `23351b7`, `1aaefd1`)**: RAG core, FastEmbed, Qdrant, and PDF font glyph repair.
- **Phase 2 (`d6c31b0`, `674840e`)**: Equity Tutor, basic safety filtering, TradeWise API contract, 600 token cap.
- **Phase 3 (`2eb440b` to `bcc1e42`)**: Complete market tools pipeline (Step 3A–3H), IST clock, validators, TTL cache, ticker classifiers.
- **Phase 4 (`70d4982`)**: Central Router, Crypto Agent, Personal Finance Agent.
- **Phase 5 (`dc9de9a`)**: Memory service, SQLite `user_memory`, PII validation, Right to be Forgotten.
- **Phase 6 (`3142c87`)**: Specialized agents suite (Derivatives, Mutual Funds, Fixed Income, Tax, ESG).
- **Phase 7 (`c97e6df`)**: System hardening, `SecondarySafetyValidator`, red-team evaluation harness, 72/72 lock.
- **Phase 8 (`864df7d`, `c6f0dc9`, `1f24cf3`)**: Standalone UI, Marigold Field & Maroon-Espresso redesign, compliance copy purge.
- **Phase 9 (`3b87bdd`, `6e7bde2`, `e063300`)**: Persistent conversations (`conversations.db`), `schema_version: 1` metadata fix, user profile modal.
- **Phase 10 (`92cae10`)**: Tutor & subject sections with immutable conversation domain routing.
- **Phase 11 (`460d8ab`)**: Conversational learning UX, topic continuity, interactive quiz generation, learning actions.
- **Phase 12 (`3054ca2`)**: Theme consistency, card polish, and reliability enhancements.
- **Phase 13 (`d64eb5f`)**: Final end-to-end QA, safety red-team lock (525 passed tests), release gate.
- **Release Packaging (`42228bb`)**: Public GitHub release packaging, comprehensive `README.md`, and `.gitignore` lock.

---

## 10. The Biggest Engineering Lessons

1. **Never Let an LLM Do Arithmetic**: Deterministic Python code executes in microseconds with zero errors. LLMs are for language synthesis, not mathematical computation.
2. **Safety Must Precede Inference**: Post-generation filtering wastes user time and GPU compute. Sub-millisecond pre-inference regex interception is 100x more efficient.
3. **Data Schemas Must Be Versioned Immediately**: Committing raw API dumps into databases causes bloat and desync. Always version persistence models (`schema_version: 1`).
4. **Offline Isolation Is Paramount**: Fallback test fixtures must never be allowed to leak silently into production paths during network outages.
5. **Character Encoding on Windows Matters**: Never deploy console tools on Windows without handling CP1252 character map collisions.

---

## 11. If You Forget Everything: How to Reconstruct Finova from Scratch

If you lose this documentation, you can rediscover the entire system from the repository in 5 commands:
1. **Find Entrypoint**: Open `scripts/run_local.py` -> Read lines 45–112 to understand process orchestration.
2. **Find API Routes**: Open `app/main.py` -> Read lines 34–45 to see all mounted routers.
3. **Find the Safety Gate**: Open `app/safety/validator.py` -> Read lines 40–120 to see all intercepted patterns.
4. **Find the Router**: Open `app/router/central.py` -> Read `route()` to see how queries are classified.
5. **Run the Tests**: Execute `.venv-finova\Scripts\pytest.exe -v` -> Read test names to see every expected behavior.

---

## 12. The "I Own This Project" Final Checklist

- [x] I understand why Finova runs 100% locally and why cloud APIs were rejected.
- [x] I can explain why SIP math uses an annuity due formula and where it lives in code.
- [x] I know why `schema_version: 1` was created and what bug it fixed.
- [x] I can trace a prompt injection attack from user input to sub-millisecond rejection.
- [x] I can explain how FastEmbed and Qdrant perform local vector retrieval in ~10ms.
- [x] I can explain why conversation domains are immutable.
- [x] I know how Indian PII is detected and rejected before touching the database.
- [x] I know how to run all 525 tests and verify that the repository is clean.
- [x] I know how to launch the complete system with one command: `.venv-finova\Scripts\python scripts/run_local.py`.
