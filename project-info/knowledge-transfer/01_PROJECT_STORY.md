<!-- Generated against commit: 42228bb55d6016ffff439024bbf4aec135269f95 | Date: 2026-09-13 | Verified against live repository state: YES -->

# Finova AI — Master Project Bible: Complete Knowledge Transfer & Code Atlas
**Volume 01: Project Story From Day Zero (Phases 0 through 13)**  
**Target Release**: Phase 13 Release Candidate (`d64eb5f1b932231a8b72c3d3f59bd5378e880118`)  
**Commit Baseline**: `42228bb55d6016ffff439024bbf4aec135269f95`  
**Classification**: Engineering History & Architectural Evolution

---

## 1. Day Zero: Problem Statement & Original Vision

### 1.1 The Problem Finova AI Was Built to Solve
[FACT] Generative Artificial Intelligence presents an acute failure mode in finance: **stochastic hallucination**. When large language models (LLMs) are queried on financial concepts, they frequently:
1. **Invent Numerical Arithmetic**: Probabilistic token prediction models fail at multi-period compounding calculations, Black-Scholes partial differential equations, and portfolio risk weighting.
2. **Fabricate Live Market Numbers**: Models invent plausible-sounding current prices, market sessions, and historical percentage changes.
3. **Hallucinate Regulatory Rules**: Models synthesize fictional legal procedures for stock transfers, IPO allotments, and grievance mechanisms that contradict SEBI, RBI, or exchange regulations.
4. **Violate Fiduciary Boundaries**: Generic chatbots freely dispense speculative buy/sell recommendations, portfolio allocation tips, and promises of guaranteed returns, violating financial advisory laws (e.g., SEBI Investment Advisers Regulations, 2013).

[FACT] The original goal of Finova AI was to build an **India-first, local-first, educational financial intelligence system** that completely solves these failure modes by engineering a deterministic system *around* an LLM:
- **LLM for Natural Language & Pedagogy**: Explaining complex terms simply.
- **Deterministic Code for Mathematics**: Executing SIP, budgeting, options payoffs, and risk metrics in pure, unit-tested Python.
- **Authoritative RAG for Knowledge**: Grounding all factual claims in primary regulatory publications from SEBI and NISM.
- **Deterministic Guardrails for Safety**: Intercepting prompt injections, advisory bypasses, and guaranteed return claims with sub-millisecond regex filters *before* token generation.
- **Local-First Zero-Cloud Execution**: Running on consumer hardware at ₹0 operational cost.

### 1.2 Relationship to TradeWise & Separation Boundaries
[FACT] Finova AI was conceived alongside an existing web application called **TradeWise**. Early project planning recognized a critical software engineering trap: coupling backend development to an evolving frontend causes unstable API churn.

[FACT] A core project rule was established:
> **TradeWise Separation Invariant**: TradeWise must NOT be modified or integrated with until the Finova AI backend is 100% stable, fully tested, and hardened (scheduled for Phase 9, later deferred to post-Phase 13). Finova AI was to be developed as an independent, standalone product.

---

## 2. Chronological Phase Timeline & Evolution

The development of Finova AI progressed through 14 formal architectural phases:

```text
Phase 0: Foundation & Environment (Commit 9507118)
   │
   ▼
Phase 1: Authoritative RAG Core & Qdrant (Commits cc532f9, 23351b7, 1aaefd1)
   │
   ▼
Phase 2: Equity Tutor Agent & TradeWise API (Commits d6c31b0, 674840e, bb2432e)
   │
   ▼
Phase 3: Deterministic Market Data Layer (Commits 2eb440b to bcc1e42)
   │
   ▼
Phase 4: Central Router, Crypto & Personal Finance Agents (Commit 70d4982)
   │
   ▼
Phase 5: User Memory & Personalization (Commit dc9de9a)
   │
   ▼
Phase 6: Specialized Agents Suite (Commit 3142c87)
   │
   ▼
Phase 7: Hardening, Evaluation & 72-Case Benchmark (Commit c97e6df)
   │
   ▼
Phase 8: Standalone UI & Marigold Field Redesign (Commits 864df7d, c6f0dc9, 1f24cf3)
   │
   ▼
Persistence Interlude: SQLite Conversation Store & Real History (Commits 3b87bdd, 6e7bde2)
   │
   ▼
Phase 9: Consumer Profile, Settings & Privacy (Commit e063300)
   │
   ▼
Phase 10: Tutor Sections & Immutable Conversation Domains (Commit 92cae10)
   │
   ▼
Phase 11: Conversational Learning UX, Actions & Quizzes (Commit 460d8ab)
   │
   ▼
Phase 12: Product Polish, Theme Consistency & Reliability (Commit 3054ca2)
   │
   ▼
Phase 13: End-to-End QA & Release Readiness (Commit d64eb5f)
   │
   ▼
Packaging: GitHub Repository Packaging & Documentation (Commit 42228bb)
```

---

## 3. Phase-by-Phase Deep Dive

---

### Phase 0 — Environment Setup & Baseline Skeleton
- **Commit**: `9507118` (*chore: baseline Phase 0*)
- **Objective**: Establish the local Python virtual environment, verify local Ollama GPU execution, configure FastAPI application factory, and create `/health` test verification.
- **Starting State**: Empty repository with initialized Git.
- **Files Created**:
  - `config/settings.py`: Pydantic `Settings` class loading `.env`.
  - `app/llm/llm_client.py`: Abstraction client wrapping `ollama.Client`.
  - `app/main.py`: Initial FastAPI app with `/health` and `/test-llm`.
  - `tests/test_health.py`: Pytest case for `/health`.
  - `.env.example`, `.env`, `requirements.txt`.
- **Concepts Introduced**: Decoupled LLM client wrapper, Pydantic settings management, local GGUF model execution.
- **Implementation**:
  [FACT] Verified environment: Windows 11, Python 3.13.15, NVIDIA RTX 4050 Laptop GPU (6GB VRAM), Ollama v0.34.0 running `qwen2.5:7b-instruct`.
- **Important Decisions**:
  - *No `pydantic-settings`*: Used plain `pydantic.BaseModel` + `python-dotenv` to eliminate an unnecessary sub-dependency.
  - *LLMClient Abstraction*: App code must never import `ollama` directly; all calls go through `LLMClient`.
- **Alternatives Considered & Rejected**:
  - *OpenAI / Cloud APIs [REJECTED]*: Violates ₹0 cost target and local-first privacy requirement.
  - *LangChain / LlamaIndex [REJECTED]*: Excessive dependency bloat and breaking upstream API changes.
- **Bugs & Debugging**:
  - *Symptom*: Initial session assumed `ollama` Python package was pre-installed in `.venv-finova`.
  - *Discovery*: `pip list` inspection revealed missing package.
  - *Fix*: Added `ollama` and `httpx` to `requirements.txt` and installed cleanly.
- **Tests & Verification**: 1 passed (`test_health_returns_ok`). Server responded on `127.0.0.1:8000`.
- **Why Locked**: Verified the GPU inference and web server baseline before building RAG. Later phases depended on `Settings` and `LLMClient`.

---

### Phase 1 — Authoritative RAG Core & Qdrant Vector Storage
- **Commits**: `cc532f9`, `23351b7`, `1aaefd1`
- **Objective**: Build a vector retrieval pipeline using official SEBI/NISM investor education PDFs, benchmark embedding models, and configure embedded Qdrant vector storage.
- **Starting State**: Working FastAPI and Ollama client; zero knowledge retrieval.
- **Files Created**:
  - `app/rag/document_parser.py`: PDF parsing via `pypdf` with page extraction.
  - `app/rag/chunking.py`: `TextChunker` (600 characters, 100 overlap).
  - `app/rag/embeddings.py`: FastEmbed ONNX wrapper (`EmbeddingManager`).
  - `app/rag/vector_store.py`: Qdrant client in embedded disk mode.
  - `app/rag/retriever.py`: `RAGRetriever` executing similarity search.
  - `scripts/ingest_docs.py`: Document downloader and ingestion pipeline.
  - `scripts/benchmark_embeddings.py`: Head-to-head benchmark harness.
  - `data/manifest.json`: Manifest of 10 official SEBI/NISM documents.
- **Concepts Introduced**: Dense vector embeddings, HNSW indexing, chunk overlap, cosine similarity thresholding, PDF text extraction safeguards.
- **Implementation & Embedding Benchmark**:
  [FACT] Head-to-head benchmark run on 8 Indian finance questions:
  - **`BAAI/bge-small-en-v1.5`**: 384 dimensions, **5.00ms average latency**, 5.37ms P95 latency, 75.0% topic match, top-1 similarity 0.7782.
  - **`intfloat/e5-small-v2`**: 384 dimensions, **84.00ms average latency**, 85.87ms P95 latency, 75.0% topic match, top-1 similarity 0.8802.
  [FACT] BGE-small was chosen because it was **16.8x faster** with identical retrieval accuracy on CPU/ONNX.
- **Important Decisions**:
  - *Embedded Qdrant*: Used local disk storage (`data/qdrant_storage/`) instead of requiring Docker.
  - *FastEmbed over Sentence-Transformers*: Eliminated heavy PyTorch dependencies (saving ~2 GB disk space).
  - *Official-Only Manifest*: Restrained ingestion strictly to official SEBI PDFs (`data/raw/`).
- **Bugs & Debugging**:
  - *Bug 1: PDF Font Corruption*: The SEBI SCORES brochure (`igrbrochure.pdf`) extracted garbled characters due to custom font encodings.
  - *Fix (`1aaefd1`)*: Added a text-corruption safeguard in `DocumentParser` that flags high ratios of unprintable characters and re-downloaded a clean copy of the brochure.
- **Tests & Verification**: `test_rag.py` passed 7 tests. Qdrant indexed 283 chunks across 10 official PDFs.
- **Why Locked**: Established the ground truth retrieval engine. Phase 2 directly depended on `rag_retriever`.

---

### Phase 2 — Equity Tutor Agent & Grounded Chat API
- **Commits**: `d6c31b0`, `674840e`, `bb2432e`
- **Objective**: Implement the first complete domain tutor agent (Equity), incorporating deterministic safety, SEBI-grounded RAG answers, citation integrity, and standardized JSON responses.
- **Starting State**: RAG retrieval available; no agents, no safety guardrails.
- **Files Created**:
  - `app/agents/equity/agent.py`: `EquityAgent` coordinating safety, RAG, and LLM.
  - `app/agents/equity/safety.py`: Regex-based `EquitySafetyGuardrail`.
  - `app/agents/equity/prompts.py`: System prompt templates.
  - `app/rag/service.py`: `RAGService` generating answers and extracting citations.
  - `app/api/equity.py`: REST endpoint `POST /agents/equity/ask`.
  - `tests/test_equity_agent.py`: 26 automated unit tests.
- **Concepts Introduced**: Pre-LLM safety refusal, citation verification, out-of-corpus fallback, structured JSON API contracts.
- **Implementation**:
  [FACT] Query execution pipeline:
  `Query -> Safety Check -> RAG Retrieval (threshold 0.65) -> Out-of-Corpus Check -> Prompt Assembly -> LLM Chat -> Citation Validator -> Response`.
- **Important Decisions**:
  - *Out-of-Corpus Fallback*: If retrieval scores are $< 0.65$, LLM is **completely bypassed** and a deterministic refusal is returned: *"I do not have authoritative information on this topic in my official investor education knowledge base..."*
  - *Token Cap*: System generation was capped at `num_predict=600` via Ollama options to prevent verbose, rambling answers.
- **Bugs & Debugging**:
  - *Bug 1: Overly Broad Safety Filter*: Initially blocked legitimate educational timing questions (e.g., *"When is the right time in life to start investing?"*) because "time" matched trading signals.
  - *Fix (`674840e`)*: Refined regular expressions to target market-timing speculation rather than lifecycle investing concepts.
- **Tests & Verification**: 26 passed tests covering SEBI grounding, citation validation, and advisory refusals. Total repo tests: 33.
- **Why Locked**: Established the architectural blueprint for all subsequent domain agents.

---

### Phase 3 — Deterministic Market Data Layer
- **Commits**: `2eb440b` through `bcc1e42` (9 granular commits)
- **Objective**: Build a deterministic market data layer for Indian equities (NSE/BSE) featuring live quotes, market session clocks, holiday calendars, TTL caching, stale fallback, and data validation.
- **Starting State**: Equity Agent answered conceptual questions via RAG; could not provide live quotes.
- **Files Created**:
  - `app/tools/market/models.py`: `StockQuote`, `MarketStatus`, provider models.
  - `app/tools/market/clock.py`: `NSEMarketClock` with official 2026 holiday calendar.
  - `app/tools/market/providers/yfinance_provider.py`: Primary Yahoo Finance adapter.
  - `app/tools/market/providers/twelve_data_provider.py`: Secondary fallback adapter.
  - `app/tools/market/validator.py`: Sanity bounds validator (`MarketDataValidator`).
  - `app/tools/market/cache.py`: In-memory TTL cache with stale fallback.
  - `app/tools/market/service.py`: `MarketDataService` orchestrating providers.
  - `app/tools/market/intent.py`: Regex-based fast-path intent classifier.
  - `data/market/nse_holidays.json`: Curated 2026 NSE exchange holiday schedule.
  - 8 test files in `tests/`.
- **Concepts Introduced**: Provider abstraction, temporal session awareness (IST UTC+05:30), dynamic TTL (15s live vs 12h closed), data provenance validation.
- **Implementation**:
  [FACT] The market clock checks current IST against trading hours (09:15–15:30) and holidays. Quotes validate that `low <= price <= high` and `price > 0`.
- **Important Decisions**:
  - *No Live LLM Quotes*: Numbers originate exclusively from providers; LLM is strictly prohibited from quoting stock prices.
  - *Dynamic TTL*: Live market cache expires in 15 seconds; after-hours cache expires in 12 hours.
- **Bugs & Debugging**:
  - *Bug 1: Inverted High/Low Bounds Check*: Initial validator check did not enforce strict high/low bounds on incoming third-party quotes.
  - *Fix (`bcc1e42`)*: [UNKNOWN — External Review Discovery] Enforced strict sanity validation in `MarketDataValidator` and flagged unserved concepts in hybrid queries.
- **Tests & Verification**: 84 new unit tests added. Total repository tests passed: 117.
- **Why Locked**: Provided bulletproof market quote infrastructure before expanding into multi-agent routing.

---

### Phase 4 — Central Router, Crypto & Personal Finance Agents
- **Commit**: `70d4982` (*feat(phase-4): Central Router, Crypto Agent, and Personal Finance Tutor*)
- **Objective**: Introduce a Central Orchestrator with query decomposition, add the Crypto Agent with CoinGecko data, and add the Personal Finance Agent with deterministic calculators.
- **Starting State**: Single-agent Equity system; all other domains unrouted.
- **Files Created**:
  - `app/router/classifier.py`: Fast-path domain intent classifier.
  - `app/router/decomposer.py`: Multi-intent query decomposer.
  - `app/router/composer.py`: Multi-subtask response composer.
  - `app/router/orchestrator.py`: `CentralOrchestrator` entrypoint.
  - `app/router/safety.py`: Global pre-routing safety filter.
  - `app/agents/crypto/`: `CryptoAgent`, prompts, safety.
  - `app/tools/crypto/`: `CoinGeckoProvider`, `CryptoService`.
  - `app/agents/personal_finance/`: `PersonalFinanceAgent`, prompts, safety.
  - `app/tools/calc/`: `compounding.py` (SIP), `budget.py` (50/30/20), `emergency_fund.py`.
  - `app/api/chat.py`: REST endpoint `POST /chat`.
- **Concepts Introduced**: Query decomposition, orthogonal subtasks, deterministic financial calculation tools, multi-agent orchestration.
- **Implementation**:
  [FACT] Compound query handling:
  `"What is Reliance price and how does an emergency fund work?"`
  -> Decomposed into:
  1. Subtask 1: `EQUITY` (`What is Reliance price`)
  2. Subtask 2: `PERSONAL_FINANCE` (`how does an emergency fund work`)
  -> Executed in parallel/sequence -> Composed with numerical tool outputs intact.
- **Important Decisions**:
  - *Hand-written Python Decomposer*: Used deterministic regex splitting on conjunctions (`and`, `also`, `as well as`) instead of an LLM routing agent, reducing router latency to $<1\text{ms}$.
  - *Crypto RAG Deferred*: Crypto queries use prompt pedagogy and CoinGecko quotes; vector RAG was deferred.
- **Bugs & Debugging**:
  - *Bug 1: SIP Calculator Wiring Gap*: Early draft did not wire the compounding calculator output directly into the agent response payload.
  - *Fix*: [UNKNOWN — External Review Discovery] Structured the agent response to always return the full calculator metadata object alongside text.
- **Tests & Verification**: 88 new tests added. Total repository tests passed: 205.
- **Why Locked**: Established multi-agent routing. Phase 5 and Phase 6 depended on the Central Router.

---

### Phase 5 — User Memory & Personalization
- **Commit**: `dc9de9a` (*feat(memory): complete Phase 5 memory and personalization*)
- **Objective**: Implement thread-safe local memory storage in SQLite, extract user learning profiles, enforce PII rejection, and personalize responses.
- **Starting State**: Stateless chat turns; no memory of learner preferences across turns.
- **Files Created**:
  - `app/memory/models.py`: `MemoryRecord`, `PersonalizationProfile`.
  - `app/memory/store.py`: `SQLiteMemoryStore` managing `data/memory.db`.
  - `app/memory/extractor.py`: Deterministic and LLM memory extractor.
  - `app/memory/validator.py`: PII filter rejecting PAN, Aadhaar, and bank accounts.
  - `app/memory/service.py`: `MemoryService` managing memory lifecycle.
  - `app/api/memory.py`: REST endpoints for memory inspection and deletion.
  - 6 test files in `tests/`.
- **Concepts Introduced**: Long-term vs short-term memory separation, PII scrubbing, user-isolated storage, memory purge capability.
- **Implementation**:
  [FACT] When a user says *"I am a complete beginner"*, memory records `(user_id, 'learning_level', 'beginner')`. Subsequent prompts inject: `[Learner Profile: beginner]`.
- **Important Decisions**:
  - *Separate SQLite Database*: Stored memory in `data/memory.db` rather than polluting vectors in Qdrant.
  - *Strict PII Rejection*: If an extraction contains a 10-character PAN pattern (`[A-Z]{5}[0-9]{4}[A-Z]`) or 12-digit Aadhaar, it is rejected immediately.
- **Bugs & Debugging**:
  - *Bug 1: Memory Extraction False Positives*: LLM extractor occasionally classified hypothetical financial numbers in prompts as user net worth.
  - *Fix*: Added deterministic pattern pre-validation in `app/memory/validator.py`.
- **Tests & Verification**: 44 new tests added. Total repository tests passed: 249.
- **Why Locked**: Provided learner continuity while protecting user privacy.

---

### Phase 6 — Remaining Specialized Agents Suite
- **Commit**: `3142c87` (*feat(phase-6): complete remaining specialized agents*)
- **Objective**: Build the 5 remaining specialized agents: Derivatives, Portfolio, Market News, Quiz, and Onboarding.
- **Starting State**: Equity, Crypto, Personal Finance agents operational; other domains fell back to general chat.
- **Files Created**:
  - `app/agents/derivatives/`: `DerivativesAgent`, Black-Scholes Greeks, options payoff engine.
  - `app/tools/derivatives/payoff.py`: Interactive payoff generator for Long/Short Call/Put and spreads.
  - `app/tools/derivatives/greeks.py`: Black-Scholes Greek calculation engine ($\Delta, \Gamma, \Theta, \text{Vega}, \rho$).
  - `app/agents/portfolio/`: `PortfolioAgent`, simulated portfolio stress-testing tool.
  - `app/tools/portfolio/service.py`: Diversification and drawdown calculator.
  - `app/agents/news/`: `NewsAgent` with RSS and yfinance news feeds.
  - `app/agents/quiz/`: `QuizAgent` with educational question bank (`data/quiz/questions.json`).
  - `app/agents/onboarding/`: `OnboardingAgent` for system guides and capabilities.
  - Corresponding routers in `app/api/`.
- **Concepts Introduced**: F&O payoff curves, Black-Scholes formulas, simulated portfolio stress testing, interactive quizzes.
- **Implementation**:
  [FACT] Derivatives payoff computes an array of 21 spot price points around strike price, returning max profit, max loss, and breakeven.
- **Important Decisions**:
  - *Deterministic Payoffs*: Payoff matrices are calculated via numpy/math, not the LLM.
  - *Simulated Portfolio Baseline*: Built with `"demo_user"` default portfolio to enable stress-test trials without user entry.
- **Bugs & Debugging**:
  - *Bug 1: Long Put Breakeven Clamping*: Initial draft clamped Long Put breakeven ($K - P$) to 0 when $P > K$.
  - *Fix*: Flagged for Phase 7 hardening.
- **Tests & Verification**: 129 new unit and integration tests added. Total repository tests passed: 378 (1 skipped).
- **Why Locked**: Completed all 8 domain agent capabilities planned in the master roadmap.

---

### Phase 7 — Hardening, Evaluation & 72-Case Benchmark
- **Commit**: `c97e6df` (*feat(phase-7): harden, evaluate, and lock Finova AI*)
- **Objective**: Perform comprehensive hardening across safety, retrieval grounding, math boundaries, router disambiguation, privacy, and failure resilience. Establish an automated evaluation runner and 72-case benchmark scorecard.
- **Starting State**: All features functional; vulnerabilities in prompt injection and mathematical edge cases remained.
- **Files Created**:
  - `app/safety/validator.py`: `SecondarySafetyValidator` with regex patterns for RIA roleplay and prompt injection.
  - `app/core/telemetry.py`: Telemetry recorder with PII sanitization.
  - `scripts/eval_runner.py`: Offline benchmark evaluation harness.
  - `data/evals/`: 16 JSON evaluation suites (72 test cases).
  - `reports/phase7_benchmark_scorecard.md`: Verified benchmark report.
  - `tests/test_red_team_safety.py`, `tests/test_reliability_failure_injection.py`, etc.
- **Concepts Introduced**: Secondary deterministic safety layer, evaluation scorecards, adversarial red-teaming, polysemic router disambiguation.
- **Implementation & Scorecard Results**:
  [FACT] The 72-case benchmark achieved **100.0% accuracy** (72/72 passed) across 5 categories:
  - Safety & Adversarial: 14/14 passed (100%)
  - RAG Grounding & Citations: 9/9 passed (100%)
  - Deterministic Tools: 20/20 passed (100%)
  - Router & Multi-Agent: 25/25 passed (100%)
  - Memory & Privacy: 4/4 passed (100%)
- **Bugs Caught & Fixed**:
  - *Defect 1: Prompt Injections Succeeded*: Indirect injection via simulated news passed Phase 6 guardrails. Fixed with `SecondarySafetyValidator`.
  - *Defect 2: Long Put Breakeven Clamping*: Fixed `Strike - Premium` to allow unclamped mathematical breakeven; positions with $P > K$ return `has_feasible_breakeven=False`.
  - *Defect 3: Polysemic Term Confusion*: Words like "delta" routed ambiguously. Fixed with token-isolated regex in `app/router/classifier.py`.
- **Tests & Verification**: 73 new tests added. Total repository tests passed: 451.
- **Why Locked**: Proved system robustness under adversarial conditions.

---

### Phase 8 — Standalone UI & Marigold Field Redesign
- **Commits**: `864df7d`, `c6f0dc9`, `1f24cf3`
- **Objective**: Build a standalone React 19 + TypeScript + Vite frontend. Redesign from an early developer dashboard into a consumer-grade product using the "Marigold Field" palette.
- **Starting State**: Backend complete; no graphical user interface existed in the repository.
- **Files Created**:
  - `frontend/`: Complete React 19 + TypeScript + Tailwind CSS v4 project.
  - `frontend/src/App.tsx`: Central application layout.
  - `frontend/src/components/layout/`: `Header.tsx`, `Sidebar.tsx`.
  - `frontend/src/components/chat/`: `MessageList.tsx`, `MessageItem.tsx`, `ChatInput.tsx`, `LoadingBubble.tsx`.
  - `frontend/src/components/cards/`: `MarketQuoteCard.tsx`, `PayoffTableCard.tsx`, `PortfolioCard.tsx`, `QuizCard.tsx`, `CryptoCard.tsx`, `NewsCard.tsx`, `CitationCard.tsx`.
  - `frontend/src/hooks/`: `useChat.ts`, `useIdentity.ts`, `useTheme.ts`.
- **Concepts Introduced**: Micro-card rendering, dark/warm theme toggle, honest elapsed-time feedback, localStorage learner identity.
- **Important Decisions**:
  - *Vite + Tailwind v4*: High build performance with Oxlint verification.
  - *No Fake Progress Bars*: Used an honest elapsed-time counter (`~2-15s`) instead of simulated progress steps.
- **Bugs & Debugging**:
  - *Bug 1: Regulatory Claims in Frontend Copy*: Early UI copy claimed "SEBI Compliant" which violated regulatory advertising guidelines.
  - *Fix (`1f24cf3`)*: [UNKNOWN — External Review Discovery] Stripped all universal regulatory compliance claims and clarified educational disclaimer.
- **Tests & Verification**: Frontend build succeeded; Oxlint passed with 0 errors. Total backend tests: 451.
- **Why Locked**: Established the visual product identity.

---

### Persistence Interlude — SQLite Conversation History & Audit Fixes
- **Commits**: `3b87bdd`, `6e7bde2`
- **Objective**: Implement permanent conversation history in SQLite (`data/conversations.db`), enabling multi-turn thread reloading, title generation, and clean metadata persistence.
- **Starting State**: Chat conversations were ephemeral in browser memory; reloading the page lost all history.
- **Files Created**:
  - `app/conversations/models.py`: `Conversation`, `Message`, metadata schemas.
  - `app/conversations/store.py`: `SQLiteConversationStore` managing `data/conversations.db`.
  - `app/conversations/service.py`: `ConversationService` coordinating session lifecycle.
  - `app/api/conversations.py`: REST endpoints for listing, fetching, deleting, and renaming threads.
  - `tests/test_conversation_store.py`, `tests/test_conversations_api.py`.
- **Concepts Introduced**: Deterministic conversation title generation without LLM tokens, bounded message history loading, clean metadata persistence.
- **Important Decisions**:
  - *Separate DB*: Maintained strict separation between `data/conversations.db` and `data/memory.db`.
  - *Clean Metadata Schema (`6e7bde2`)*: [UNKNOWN — External Review Discovery] Discovered that blindly saving the entire `OrchestratorResponse` to the database created bloated, brittle records. Replaced with `AssistantMessageMetadata` (`schema_version=1`).
- **Tests & Verification**: 16 new tests added. Total repository tests passed: 467.

---

### Phase 9 — Consumer Profile, Learning Personalization & Settings
- **Commit**: `e063300` (*feat(phase-9): implement consumer profile, learning personalization, and settings*)
- **Objective**: Build a profile and settings management modal in the frontend, wire it to backend memory endpoints, and enforce client-side PII rejection.
- **Starting State**: Backend memory APIs existed; no interactive user interface existed for learners to inspect or delete their data.
- **Files Created**:
  - `frontend/src/components/memory/ProfileModal.tsx`: Interactive modal for learner profile and settings.
  - `tests/test_phase9_profile_settings.py`: API validation suite.
- **Concepts Introduced**: Self-service memory auditing, instant memory wipe, client-side identity persistence (`useIdentity`).
- **Implementation**: Learners click their top-header badge to view active memory keys (experience level, risk tolerance) and can click "Clear Memory" for an immediate purge.
- **Tests & Verification**: 8 new tests added. Total repository tests passed: 475.

---

### Phase 10 — Tutor & Subject Sections with Immutable Conversation Domains
- **Commit**: `92cae10` (*feat(phase10): implement tutor & subject sections with immutable conversation domain*)
- **Objective**: Partition chat interactions into 9 distinct subject sections in the sidebar, enforcing domain immutability so a thread started in "Equity Tutor" cannot be hijacked by other domains.
- **Starting State**: All chat sessions operated under general routing; sidebar lacked subject grouping.
- **Files Created / Modified**:
  - `frontend/src/components/layout/Sidebar.tsx`: Subject section navigation with domain tags.
  - `app/conversations/models.py`: Added `domain` field to `Conversation`.
  - `app/router/orchestrator.py`: Enforced `domain_context` override in dispatch.
  - `tests/test_phase10_tutor_sections.py`: Verification suite.
- **Concepts Introduced**: Domain immutability, subject-isolated chat sessions, context-aware prompt templates.
- **Implementation**:
  [FACT] If a thread is tagged `domain="derivatives"`, the central router dispatches queries directly to `DerivativesAgent` without re-classifying to another domain.
- **Tests & Verification**: 7 new tests added. Total repository tests passed: 482.

---

### Phase 11 — Conversational Learning UX, Actions & Quizzes
- **Commit**: `460d8ab` (*feat(phase11): implement learning and tutor conversational UX with topic continuity, learning actions, and quiz integration*)
- **Objective**: Enhance pedagogical flow by adding learning action chips (e.g., *"Take a Quiz on this topic"*, *"Explain with an Example"*), related concept chips, and inline quiz challenges.
- **Starting State**: Chat turns ended with text; users had to manually invent follow-up prompts.
- **Files Created / Modified**:
  - `frontend/src/components/chat/LearningActions.tsx`: Action button bar below assistant answers.
  - `frontend/src/components/chat/RelatedConcepts.tsx`: Concept navigation chips.
  - `app/conversations/learning_context.py`: Learning action generator.
  - `tests/test_phase11_learning_ux.py`: Integration test suite.
- **Concepts Introduced**: Topic continuity, interactive pedagogical scaffolding, dynamic follow-up synthesis.
- **Tests & Verification**: 16 new tests added. Total repository tests passed: 498.

---

### Phase 12 — Product Polish, Theme Consistency & Reliability
- **Commit**: `3054ca2` (*feat(phase12): product polish, theme consistency, and reliability enhancements*)
- **Objective**: Refine visual design consistency across all card components, optimize dark/warm theme tokens, and add automated failure recovery.
- **Starting State**: Visual discrepancies between card borders; intermittent network reconnect issues.
- **Files Modified**:
  - `frontend/src/index.css`: Tailwind v4 theme variables (`--color-surface`, `--color-marigold`, `--color-teal`).
  - `frontend/src/components/cards/*`: Unified glassmorphism styling and border radiuses.
  - `frontend/src/api/client.ts`: Request retry interceptors with exponential backoff.
- **Concepts Introduced**: Unified design token system, frontend fault tolerance.
- **Tests & Verification**: All frontend components verified; backend tests maintained at 498.

---

### Phase 13 — End-to-End QA & Release Readiness
- **Commit**: `d64eb5f` (*feat(phase13): complete end-to-end QA and release readiness*)
- **Objective**: Execute exhaustive regression testing across all 8 specialized domains, run end-to-end multi-intent scenarios, resolve harmless deprecation warnings, and verify release gates.
- **Starting State**: Complete feature set; needed final release-readiness audit.
- **Files Modified**:
  - `app/router/safety.py`: Final safety pattern hardening.
  - `app/safety/validator.py`: Injection delimiter edge-case fix.
  - `tests/test_red_team_safety.py`: Final adversarial test cases added.
- **Verification Results**:
  [FACT] Backend test suite: **525 passed, 0 failed, 4 harmless deprecation warnings in 269.47s**.
  [FACT] Frontend: Build succeeded, Oxlint passed on 27 files with **0 errors and 0 warnings**.
- **Final State**: System declared **RELEASE READY**.

---

### Packaging — Final GitHub Release Packaging
- **Commit**: `42228bb` (*docs: complete public release packaging and documentation*)
- **Objective**: Prepare repository for public GitHub release, audit `.gitignore` against secret leaks, write comprehensive README.md covering all 17 required topics, and perform first authorized push to remote.
- **Files Modified / Created**:
  - `README.md`: Comprehensive 17-section documentation.
  - `.gitignore`: Added explicit exclusions for root `node_modules/` and build artifacts.
- **Final Result**: Pushed to `https://github.com/pranavsawant0629-tech/finova-ai.git` on branch `main`.

---

## 4. Summary of Deliberately Rejected & Postponed Approaches

| Feature / Technology | Planned or Evaluated In | Final Status | Authoritative Reason |
| :--- | :---: | :---: | :--- |
| **OpenAI / Anthropic Cloud APIs** | Phase 0 | **[REJECTED]** | Violates ₹0 operational cost goal and local-first privacy requirement. |
| **LangChain / LlamaIndex** | Phase 0 | **[REJECTED]** | Excessive dependency overhead, unneeded abstractions, frequent breaking changes. |
| **Docker Daemon for Qdrant** | Phase 1 | **[REJECTED]** | Embedded local disk storage (`data/qdrant_storage`) eliminated container runtime prerequisites. |
| **Sentence-Transformers (PyTorch)** | Phase 1 | **[REJECTED]** | FastEmbed ONNX runtime reduced disk footprint by ~2 GB and ran 16.8x faster. |
| **LLM-Based Numerical Calculations** | Phase 2, 3 | **[REJECTED]** | Language models hallucinate math; deterministic Python tools guarantee precision. |
| **Real Brokerage / Trading Execution** | Phase 6 | **[REJECTED]** | Finova AI is strictly educational; live order routing creates extreme regulatory risk. |
| **TradeWise Website RAG Ingestion** | Phase 1 | **[REJECTED]** | Website content is non-authoritative; grounding restricted strictly to SEBI/NISM. |
| **Crypto Vector RAG** | Phase 4 | **[DEFERRED]** | Deferred to subsequent phases; crypto relies on pedagogy and CoinGecko quotes. |
| **TradeWise Frontend Integration** | Phase 9 | **[DEFERRED]** | Intentionally postponed until after standalone release validation. |
| **User Authentication / Cloud Accounts** | Phase 5, 9 | **[REJECTED]** | Local SQLite storage and browser `localStorage` ensure zero cloud leakage. |
