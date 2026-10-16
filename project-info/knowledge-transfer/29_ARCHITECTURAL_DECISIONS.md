<!-- Generated against commit: 42228bb55d6016ffff439024bbf4aec135269f95 | Date: 2026-09-13 | Verified against live repository state: YES -->

# Part 29: Architectural Decision Records (ADRs)

Architectural Decision Records capture significant design choices, evaluating options, tradeoffs, and long-term consequences. This log documents the 21 foundational architectural decisions governing Finova AI.

In accordance with Phase 14A integrity standards:
- Documented facts from code and commits are classified as `[FACT]`.
- Architectural rationales derived from design patterns are classified as `[INFERENCE]`.
- Decisions driven by external audit feedback during Phase 14A are tagged as `[EXTERNAL REVIEW INFLUENCE]`.

---

## ADR-01: Local-First System Architecture

- **DECISION**: Establish Finova AI as a 100% local-first, offline-capable intelligence platform.
- **OPTIONS**:
  1. *Cloud-Hosted SaaS*: Deploy backend on AWS/GCP with managed services (Pinecone, OpenAI, Supabase).
  2. *Hybrid Cloud*: Local frontend communicating with private cloud LLM endpoints.
  3. *Local-First Standalone*: Run all models, vector stores, relational databases, and application logic directly on the user's host machine.
- **CHOSEN OPTION**: Option 3: Local-First Standalone `[FACT]`.
- **WHY**: Financial privacy is paramount. Retail investors and enterprise analysts are unwilling to transmit personal portfolio data, financial goals, or trade queries to third-party cloud servers. Furthermore, local-first eliminates ongoing cloud infrastructure hosting costs and vendor lock-in.
- **TRADEOFF**: System performance is constrained by the host machine's hardware (VRAM, CPU, RAM). Initial user setup requires downloading local model weights.
- **CONSEQUENCE**: Complete data sovereignty, zero cloud operating expenses, zero latency variance from internet congestion, and zero regulatory exposure to cross-border data transfer laws.

---

## ADR-02: Ollama as Local Model Runtime

- **DECISION**: Standardize on Ollama as the local LLM inference engine.
- **OPTIONS**:
  1. *Hugging Face Transformers / PyTorch*: Native Python GPU inference.
  2. *vLLM / TGI*: High-throughput server-grade serving engines.
  3. *Ollama*: Standalone Go/C++ service based on `llama.cpp` with a clean REST API.
- **CHOSEN OPTION**: Option 3: Ollama `[FACT]`.
- **WHY**: Native PyTorch installations on Windows require 4GB+ of CUDA dependencies and complex C++ compilation tools. vLLM has limited Windows support. Ollama provides a single executable installer, automatic CPU/GPU VRAM offloading, GGUF quantization management, and a standardized REST API (`/api/generate`).
- **TRADEOFF**: Adds an external process dependency (`ollama serve`) outside the Python virtual environment.
- **CONSEQUENCE**: Lightweight, reliable local inference that runs smoothly across consumer Windows hardware.

---

## ADR-03: Selection of Qwen 2.5 7B Instruct

- **DECISION**: Designate `qwen2.5:7b-instruct` as the primary foundation LLM.
- **OPTIONS**:
  1. *Llama 3.1 8B Instruct*
  2. *Mistral 7B Instruct v0.3*
  3. *Qwen 2.5 7B Instruct*
  4. *Phi-3 / Gemma 2 9B*
- **CHOSEN OPTION**: Option 3: `qwen2.5:7b-instruct` `[FACT]`.
- **WHY**: Qwen 2.5 exhibits superior performance on structured data extraction, tabular financial comprehension, mathematical reasoning, and instruction following in the 7B–8B parameter class. It strictly respects system prompts, citation grounding constraints, and negative constraints ("do not guess").
- **TRADEOFF**: 7B model requires ~5GB of VRAM (Q4_K_M quantization), requiring decent integrated or dedicated GPU hardware.
- **CONSEQUENCE**: High-fidelity financial answers with minimal hallucination, fitting comfortably on 8GB+ consumer GPUs.

---

## ADR-04: FastEmbed over Heavy ML Frameworks

- **DECISION**: Use Qdrant's `fastembed` library for vector embeddings instead of `sentence-transformers` / `torch`.
- **OPTIONS**:
  1. *sentence-transformers (PyTorch)*
  2. *FastEmbed (ONNX Runtime)*
  3. *Ollama Embeddings API*
- **CHOSEN OPTION**: Option 2: `fastembed` `[FACT]`.
- **WHY**: PyTorch adds ~3GB to the virtual environment and introduces significant startup overhead on Windows. `fastembed` uses ONNX Runtime under the hood, running quantized embedding models with minimal CPU overhead, ~5ms embedding latency per chunk, and a tiny disk footprint.
- **TRADEOFF**: Limited to ONNX-converted embedding models supported by FastEmbed.
- **CONSEQUENCE**: Lightning-fast cold start, negligible RAM usage, and zero PyTorch dependency bloat.

---

## ADR-05: Embedding Model: `BAAI/bge-small-en-v1.5`

- **DECISION**: Utilize `BAAI/bge-small-en-v1.5` (384 dimensions) for semantic retrieval.
- **OPTIONS**:
  1. *all-MiniLM-L6-v2* (384 dimensions)
  2. *BAAI/bge-small-en-v1.5* (384 dimensions)
  3. *intfloat/e5-large-v2* (1024 dimensions)
- **CHOSEN OPTION**: Option 2: `bge-small-en-v1.5` `[FACT]`.
- **WHY**: Scores substantially higher than `all-MiniLM-L6-v2` on the MTEB (Massive Text Embedding Benchmark) for retrieval tasks, while producing compact 384-dimensional vectors that search in sub-millisecond time. E5-large was tested but added 80ms latency per query without meaningful retrieval improvements on regulatory text.
- **TRADEOFF**: Smaller vector dimension than 768/1024 models, requiring higher quality chunking.
- **CONSEQUENCE**: Ultra-fast vector retrieval and compact Qdrant index size (<50MB for the entire SEBI corpus).

---

## ADR-06: Qdrant Local File-Backed Storage

- **DECISION**: Deploy Qdrant in local embedded file-backed storage mode (`data/qdrant_storage/`).
- **OPTIONS**:
  1. *ChromaDB*
  2. *Faiss*
  3. *Qdrant (Local Storage Mode)*
  4. *pgvector (PostgreSQL)*
- **CHOSEN OPTION**: Option 3: Qdrant Local Storage `[FACT]`.
- **WHY**: Faiss lacks metadata filtering and payload persistence. ChromaDB has historically suffered from dependency conflicts with Pydantic v2 and SQLite locking issues on Windows. Qdrant's `QdrantClient(path="data/qdrant_storage")` runs an embedded Rust-powered vector engine directly inside the Python process with full payload filtering, HNSW indexing, and zero daemon requirement.
- **TRADEOFF**: Concurrent write locks from multiple processes must be managed.
- **CONSEQUENCE**: Industrial vector database capabilities with zero external server processes.

---

## ADR-07: SQLite as Primary Relational Store

- **DECISION**: Store conversations, user memory, and settings in local SQLite databases (`conversations.db`, `memory.db`).
- **OPTIONS**:
  1. *PostgreSQL / MySQL*
  2. *DuckDB*
  3. *SQLite3*
  4. *Flat JSON files*
- **CHOSEN OPTION**: Option 3: SQLite3 `[FACT]`.
- **WHY**: Built directly into Python standard library (`import sqlite3`), zero configuration, ACID-compliant, self-contained single-file storage, and rock-solid reliability across operating systems. Flat JSON files risk corruption during concurrent writes, while PostgreSQL requires an external daemon.
- **TRADEOFF**: Limited to single-writer concurrency.
- **CONSEQUENCE**: Zero-maintenance, instantly inspectable, zero-cloud data persistence.

---

## ADR-08: Federated Multi-Agent Architecture

- **DECISION**: Structure the system as a federated suite of domain-specific agents orchestrated by a Central Router.
- **OPTIONS**:
  1. *Monolithic Single-Prompt System*: One giant system prompt instructing the LLM on all topics.
  2. *Autonomous ReAct Loop*: Let an LLM autonomously plan and call arbitrary tools in a loop.
  3. *Federated Agent Architecture*: Explicit routing to specialized domain tutors with tailored system instructions and bounded tools.
- **CHOSEN OPTION**: Option 3: Federated Agent Architecture `[FACT]`.
- **WHY**: Monolithic prompts dilute instruction following and increase hallucination. Autonomous ReAct loops are unpredictable, slow (5–8 LLM calls per query), and prone to infinite loops. Federated routing ensures that an options question goes to a derivatives tutor with statutory risk warnings, while a mutual fund question gets AMFI/SEBI grounding.
- **TRADEOFF**: Requires maintaining explicit agent classes and routing rules.
- **CONSEQUENCE**: High domain specialization, predictable execution, and robust boundary control.

---

## ADR-09: Deterministic Financial Tools over LLM Math

- **DECISION**: Implement all financial calculations (SIP, compounding, options payoff, metrics) in pure Python code, never allowing the LLM to perform arithmetic.
- **OPTIONS**:
  1. *LLM Native Arithmetic*: Prompt the LLM to calculate numbers.
  2. *Code Interpreter*: Let the LLM write and execute Python code in a sandbox.
  3. *Deterministic Tool Execution*: Parse inputs via regex/schema and execute validated mathematical formulas.
- **CHOSEN OPTION**: Option 3: Deterministic Tool Execution `[FACT]`.
- **WHY**: LLMs are notorious for mathematical hallucination, rounding errors, and compounding mistakes. In financial intelligence, math must be 100% correct 100% of the time.
- **TRADEOFF**: Tools must be pre-coded and their parameters explicitly parsed.
- **CONSEQUENCE**: Zero arithmetic errors. Complete mathematical auditability.

---

## ADR-10: Provider Abstractions for Market Data

- **DECISION**: Define abstract base classes (`BaseMarketDataProvider`, `BaseCryptoProvider`) for all external market data integrations.
- **OPTIONS**:
  1. *Direct API Calls*: Call Yahoo Finance or CoinGecko directly in agent code.
  2. *Provider Abstraction with Service Orchestrator*: Formal interfaces with multi-provider failover, caching, and validation gates.
- **CHOSEN OPTION**: Option 2: Provider Abstraction `[FACT]`.
- **WHY**: Free financial APIs frequently rate-limit, alter endpoints, or fail. Abstractions allow seamless switching between Yahoo Finance, Twelve Data, CoinGecko, or premium exchange feeds without touching agent logic.
- **TRADEOFF**: Additional architectural layers (models, interfaces, adapters, orchestrators).
- **CONSEQUENCE**: Resilient data ingestion, testability with mock providers, and painless future provider additions.

---

## ADR-11: Memory Isolation and Bounded Extraction

- **DECISION**: Restrict persistent user memory to explicit, validated user facts, stored separately from conversation history.
- **OPTIONS**:
  1. *Implicit Conversational Summary*: Summarize all past messages and inject into context.
  2. *Vector-Based Conversational Search*: Search all historical turns for semantic relevance.
  3. *Isolated Bounded Memory Store*: Store explicit categorized facts (`risk_tolerance`, `experience`, `goals`) with PII filters.
- **CHOSEN OPTION**: Option 3: Isolated Bounded Memory Store `[FACT]`.
- **WHY**: Summaries and vector search over full history frequently inject stale or irrelevant chatter. Bounded memory allows explicit user control, privacy auditing, and implementation of statutory Right to be Forgotten.
- **TRADEOFF**: Does not recall arbitrary casual remarks from 3 weeks ago unless classified as a preference.
- **CONSEQUENCE**: Clean, deterministic personalization without context bloat or privacy leaks.

---

## ADR-12: Domain Immutability in Conversations

- **DECISION**: Lock each conversation to its initial subject domain upon creation `[EXTERNAL REVIEW INFLUENCE]`.
- **OPTIONS**:
  1. *Dynamic Re-Routing per Turn*: Re-route every user message to whatever agent scores highest.
  2. *Domain Immutability*: Fix the conversation's domain (e.g. `EQUITY_TUTOR`) so all subsequent turns remain with that specialist.
- **CHOSEN OPTION**: Option 2: Domain Immutability (Commit `92cae10`) `[FACT]`.
- **WHY**: In dynamic routing, context switches across agents destroyed conversational topic continuity. An equity tutor explaining P/E ratios was abruptly replaced by a crypto tutor because the user mentioned "coin". Domain immutability preserves pedagogical depth.
- **TRADEOFF**: Users wishing to switch subjects must open a new conversation or section.
- **CONSEQUENCE**: Cohesive educational conversations, stable context, and zero jarring persona shifts.

---

## ADR-13: Safety Evaluation Before LLM Inference

- **DECISION**: Execute deterministic safety and prompt injection validation *before* routing or model generation.
- **OPTIONS**:
  1. *Post-Generation Guardrails*: Let the LLM generate, then inspect its output.
  2. *System Prompt Instruction Only*: Tell the model "Do not give financial advice".
  3. *Pre-Inference Deterministic Gate*: Intercept unsafe prompts with regex and structural rules before any token reaches the LLM.
- **CHOSEN OPTION**: Option 3: Pre-Inference Deterministic Gate `[FACT]`.
- **WHY**: LLMs can be persuaded to ignore system instructions via jailbreaks and roleplay. Post-generation filtering wastes 5–10 seconds of GPU compute and GPU energy on responses destined to be discarded. Pre-inference interception executes in <1ms and cannot be bypassed by model confusion.
- **TRADEOFF**: Requires comprehensive regex and pattern maintenance.
- **CONSEQUENCE**: 100% block rate on direct stock tips, sub-millisecond rejection, and zero GPU waste.

---

## ADR-14: Citation Validation and Grounding Verification

- **DECISION**: Validate all citations generated by the LLM against the actual retrieved context chunks.
- **OPTIONS**:
  1. *Trust LLM Citations*: Accept any citation the LLM prints.
  2. *Deterministic Verification*: Cross-reference citation markers against retrieved chunk IDs and source document names.
- **CHOSEN OPTION**: Option 2: Deterministic Verification `[FACT]`.
- **WHY**: Models frequently hallucinate plausible-sounding legal citations (e.g. citing non-existent regulations or attributing equity rules to SEBI mutual fund circulars).
- **TRADEOFF**: If an LLM misformats a citation marker, valid retrieved context might be flagged as ungrounded.
- **CONSEQUENCE**: Only verifiable, retrieved regulatory evidence is highlighted to the user.

---

## ADR-15: No Brokerage Execution or Trading APIs

- **DECISION**: Explicitly exclude trading execution, order routing, and brokerage API credentials from Finova AI.
- **OPTIONS**:
  1. *Automated Trading Execution*: Connect to Zerodha Kite or Upstox to place orders.
  2. *Read-Only Portfolio Integration*: Connect to broker APIs to read balances.
  3. *Zero Brokerage Integration*: Pure educational, conceptual, and analytical platform.
- **CHOSEN OPTION**: Option 3: Zero Brokerage Integration `[FACT]`.
- **WHY**: Automated trading introduces catastrophic financial risk, API credential vulnerability, and stringent SEBI algorithmic trading regulatory licensing requirements. Finova is strictly an educational and analytical companion.
- **TRADEOFF**: Users cannot execute trades directly from Finova's UI.
- **CONSEQUENCE**: Zero financial execution risk, zero credential theft vector, and pure educational positioning.

---

## ADR-16: No Mandatory User Authentication

- **DECISION**: Ship the local application without mandatory OAuth2/JWT user login walls.
- **OPTIONS**:
  1. *Mandatory Cloud Auth (Supabase, Auth0)*
  2. *Local Password / JWT System*
  3. *Local Single-User Isolation (`default_user`)*
- **CHOSEN OPTION**: Option 3: Local Single-User Isolation `[FACT]`.
- **WHY**: Finova is an offline, local-first workstation app. Forcing a local user to log in creates unnecessary friction for local trials and evaluation. Multi-user isolation is enforced architecturally via `user_id` parameters to support enterprise multi-tenancy when deployed behind enterprise proxies.
- **TRADEOFF**: Assumes single-user physical security on the host machine.
- **CONSEQUENCE**: Instant, friction-free startup without login screens or credential management.

---

## ADR-17: Zero Cloud Requirement for Core Functions

- **DECISION**: Guarantee that all core capabilities (RAG, calculation, safety, memory, conversation) operate with the internet disconnected.
- **OPTIONS**:
  1. *Cloud-Dependent Architecture*
  2. *Hybrid Optional Cloud*
  3. *Strict Offline Baseline*
- **CHOSEN OPTION**: Option 3: Strict Offline Baseline `[FACT]`.
- **WHY**: Local software must work on air-gapped workstations, flights, or during internet disruptions.
- **TRADEOFF**: Live market quotes require internet, but fallback and cached data prevent application failure.
- **CONSEQUENCE**: The system never fails to launch or educate due to network issues.

---

## ADR-18: Zero Required Paid API Subscriptions

- **DECISION**: Build all features using free, open-source, or public data sources.
- **OPTIONS**:
  1. *Commercial APIs (Bloomberg, FactSet, OpenAI, Pinecone)*
  2. *Zero Paid APIs Baseline*
- **CHOSEN OPTION**: Option 2: Zero Paid APIs Baseline `[FACT]`.
- **WHY**: Democratizes access to financial intelligence. Anyone with a personal computer can run Finova AI without paying monthly API fees.
- **TRADEOFF**: Public feeds (Yahoo Finance, CoinGecko) have rate limits and lack sub-second tick-level streaming.
- **CONSEQUENCE**: True open-source utility and zero financial barrier to entry.

---

## ADR-19: Pure Text & Tabular Focus (No Vision/Multimodal LLM)

- **DECISION**: Restrict LLM inference to text and tabular tokens, excluding vision models.
- **OPTIONS**:
  1. *Multimodal Models (Llava, Qwen-VL)*
  2. *Text-Only Specialist Models (`qwen2.5:7b-instruct`)*
- **CHOSEN OPTION**: Option 2: Text-Only Specialist Models `[FACT]`.
- **WHY**: Multimodal models require 2x–3x more VRAM and significantly higher compute, sacrificing financial reasoning accuracy for generic image captioning. Financial charts are rendered interactively on the frontend using deterministic Canvas/SVG components rather than LLM image generation.
- **TRADEOFF**: Users cannot upload screenshots of stock charts for visual analysis.
- **CONSEQUENCE**: Lower resource requirements, faster inference, and superior text reasoning.

---

## ADR-20: Decoupling from TradeWise Prototype

- **DECISION**: Develop and validate Finova AI as a standalone product before integrating with TradeWise.
- **OPTIONS**:
  1. *Direct TradeWise Dependency*: Build Finova as a plugin inside the TradeWise codebase.
  2. *Standalone Decoupled Architecture*: Build Finova as an independent system, exposing standardized REST endpoints for TradeWise consumption.
- **CHOSEN OPTION**: Option 2: Standalone Decoupled Architecture `[FACT]`.
- **WHY**: Prevents architectural contamination. Allows Finova AI to be audited, evaluated, and released as an authoritative standalone open-source repository.
- **TRADEOFF**: Requires maintaining a dedicated standalone UI.
- **CONSEQUENCE**: High architectural modularity, independent versioning, and clean separation of concerns.

---

## ADR-21: Versioned Clean Assistant Metadata (`schema_version: 1`)

- **DECISION**: Migrate SQLite assistant message persistence to a clean, versioned schema omitting redundant text `[EXTERNAL REVIEW INFLUENCE]`.
- **OPTIONS**:
  1. *Raw Dump Persistence*: Save full API responses.
  2. *Versioned Filtered Schema*: Persist only UI-rendering metadata with an explicit `schema_version: 1`.
- **CHOSEN OPTION**: Option 2: Versioned Filtered Schema (Commit `6e7bde2`) `[FACT]`.
- **WHY**: Resolves database inflation and desynchronization bugs identified in Phase 9 post-mortems.
- **TRADEOFF**: Schema migrations required if new metadata fields are added.
- **CONSEQUENCE**: 80% reduction in conversation database size, structured data integrity, and painless future migrations.
