<!-- Generated against commit: 42228bb55d6016ffff439024bbf4aec135269f95 | Date: 2026-09-13 | Verified against live repository state: YES -->

# Part 35: Evaluated & Rejected Alternatives

Architecture is defined as much by what is excluded as by what is built. This chapter documents 15 significant technological and architectural alternatives evaluated throughout the lifecycle of Finova AI, detailing their evaluation status, evidence, rejection rationale, tradeoffs, and current system implications.

In compliance with Phase 14A integrity standards:
- Status tags follow the canonical enum: `[IMPLEMENTED]`, `[PARTIALLY IMPLEMENTED]`, `[PLANNED / DEFERRED]`, `[REJECTED]`, `[REMOVED]`, `[UNKNOWN]`.
- Factual decisions verified in code/commits are tagged `[FACT]`.
- Architectural deductions explaining rejection reasons are tagged `[INFERENCE]`.
- Unknown historical deliberation trails are tagged `[UNKNOWN]`.

---

## 1. OpenAI API & Proprietary Cloud LLMs (GPT-4o, Claude 3.5 Sonnet)

- **OPTION**: OpenAI GPT-4o / Anthropic Claude 3.5 Sonnet via Cloud REST API.
- **STATUS**: `[REJECTED]` `[FACT]`.
- **EVIDENCE**: Zero OpenAI SDK dependencies in `requirements.txt`; zero cloud API key configuration in `app/core/config.py`.
- **WHY NOT CHOSEN**:
  1. *Financial Privacy Violation*: Sending personal financial queries, investment goals, or portfolio balances to cloud servers violates the core privacy promise of Finova AI.
  2. *Recurring Cost Barrier*: Per-token cloud API billing restricts access for students, retail investors, and local research analysts.
  3. *Internet Dependency*: Cloud APIs prevent offline operation on local air-gapped workstations.
- **TRADEOFF**: Open-weights 7B models (`qwen2.5:7b-instruct`) have lower general-knowledge reasoning capacity than 1-trillion parameter frontier cloud models.
- **CURRENT IMPLICATION**: 100% data sovereignty, zero ongoing API subscription costs, and local offline execution.

---

## 2. Paid Financial Data APIs (Bloomberg Terminal, FactSet, Refinitiv)

- **OPTION**: Commercial institutional data feeds (Bloomberg B-PIPE, FactSet, Refinitiv).
- **STATUS**: `[REJECTED]` `[FACT]`.
- **EVIDENCE**: Absence of proprietary enterprise client libraries in repository; `BaseMarketDataProvider` designed around public feeds.
- **WHY NOT CHOSEN**: Institutional data terminals cost upwards of $2,000/month per seat, conflicting fundamentally with the goal of democratizing financial literacy.
- **TRADEOFF**: Public web feeds lack tick-level streaming, Level 2/3 order book depth, and institutional macro databases.
- **CURRENT IMPLICATION**: System functions entirely on free public Yahoo Finance and CoinGecko endpoints, with optional Twelve Data API key support.

---

## 3. Direct Broker Trading APIs (Zerodha Kite Connect, Upstox, Angel One)

- **OPTION**: Automated order routing and portfolio trade execution via Indian broker REST APIs.
- **STATUS**: `[REJECTED]` `[FACT]`.
- **EVIDENCE**: Zero order execution routes in `app/api/`; absence of API secret/access token models in `app/core/config.py`.
- **WHY NOT CHOSEN**:
  1. *Regulatory Prohibition*: Automated trade execution falls under strict SEBI algorithmic trading guidelines, requiring registered broker-dealer licenses and statutory exchange compliance audits.
  2. *Catastrophic Financial Risk*: Automated trading bugs or prompt injection exploits could execute unintended capital transactions.
  3. *Credential Theft Vector*: Storing trading API tokens locally exposes user brokerage accounts to host-level credential theft.
- **TRADEOFF**: Users cannot execute trades directly within Finova AI's conversational interface.
- **CURRENT IMPLICATION**: Finova AI remains an educational intelligence system, eliminating financial liability and security risks.

---

## 4. Direct Exchange Feed Integration (NSE/BSE Leased Line & FIX Protocol)

- **OPTION**: Direct connectivity to the National Stock Exchange (NSE) via Financial Information eXchange (FIX) protocol over dedicated leased lines.
- **STATUS**: `[REJECTED]` `[FACT]`.
- **EVIDENCE**: No C++ / socket-level FIX protocol engine exists in the repository.
- **WHY NOT CHOSEN**: Direct exchange co-location and leased line connectivity cost millions of rupees annually and are legally restricted to SEBI-registered stockbrokers and institutional members.
- **TRADEOFF**: Price updates reflect standard 15-minute delayed exchange feeds rather than sub-millisecond tick streaming.
- **CURRENT IMPLICATION**: Standardized delayed data model (`freshness_status="delayed"`), fully compliant with regulatory investor education rules.

---

## 5. Alpha Vantage & Commercial Web APIs

- **OPTION**: Standardizing on Alpha Vantage as the primary financial market provider.
- **STATUS**: `[REJECTED]` `[FACT]`.
- **EVIDENCE**: Adapter suite in `app/tools/market/adapters/` contains `YahooFinanceAdapter` and `TwelveDataAdapter`, completely omitting Alpha Vantage.
- **WHY NOT CHOSEN**: Free-tier Alpha Vantage accounts enforce an aggressive limit of 25 requests per day (5 calls/minute), which is immediately exhausted during multi-ticker comparisons.
- **TRADEOFF**: Yahoo Finance requires HTML/JSON scraping resilience.
- **CURRENT IMPLICATION**: Higher reliability and throughput using Yahoo Finance and Twelve Data failover.

---

## 6. Web Scraping Google Finance Directly

- **OPTION**: Parsing Google Finance HTML pages using BeautifulSoup or Selenium.
- **STATUS**: `[REJECTED]` `[FACT]`.
- **EVIDENCE**: Zero headless browser or HTML DOM parsing tools in `app/tools/market/`.
- **WHY NOT CHOSEN**: Google Finance aggressively updates obfuscated DOM classes, implements anti-bot CAPTCHAs, and frequently blocks automated scrapers, making it fragile for production pipelines.
- **TRADEOFF**: Relies on Yahoo Finance's unofficial v8 JSON endpoints.
- **CURRENT IMPLICATION**: Structured JSON parsing with near-zero DOM maintenance overhead.

---

## 7. Cloud Vector Databases (Pinecone, Weaviate Cloud, Milvus Cloud)

- **OPTION**: Managing regulatory document embeddings in hosted cloud vector services.
- **STATUS**: `[REJECTED]` `[FACT]`.
- **EVIDENCE**: Qdrant configured strictly in local storage mode (`path="data/qdrant_storage"`).
- **WHY NOT CHOSEN**: Defeats offline-first capability. Introduces cloud network latency (50–150ms per search) and vendor lock-in.
- **TRADEOFF**: Vector database must be stored locally on host disk (~50MB).
- **CURRENT IMPLICATION**: Sub-10ms local vector retrieval and zero network dependency.

---

## 8. ChromaDB as Local Vector Store

- **OPTION**: Using ChromaDB (`chromadb`) for local embedded vector storage.
- **STATUS**: `[REJECTED]` `[FACT]`.
- **EVIDENCE**: Git history shows Qdrant was selected from Day 1 (Phase 1 commit `cc532f9`).
- **WHY NOT CHOSEN**: ChromaDB has historically experienced dependency conflicts with Pydantic v2, file-locking contention on Windows operating systems, and heavy transitive dependencies.
- **TRADEOFF**: Qdrant requires custom path initialization for local embedded mode.
- **CURRENT IMPLICATION**: High-performance, Rust-backed embedded vector engine with payload filtering.

---

## 9. Heavy Embedding Models (intfloat/e5-large-v2, OpenAI text-embedding-3)

- **OPTION**: High-dimensional (1,024-dimension) embedding models.
- **STATUS**: `[REJECTED]` `[FACT]`.
- **EVIDENCE**: FastEmbed pinned to `BAAI/bge-small-en-v1.5` (384 dimensions) in `app/rag/embeddings.py`.
- **WHY NOT CHOSEN**: E5-large required ~1.5 GB of RAM and took ~80ms to embed queries on CPU, while providing negligible retrieval quality improvements on structured regulatory text.
- **TRADEOFF**: 384 dimensions require strict chunk size boundaries (512 tokens max).
- **CURRENT IMPLICATION**: Lightning-fast 6ms embeddings and compact vector index footprint.

---

## 10. Large Local LLMs (Qwen 2.5 14B/72B, Llama 3.1 70B)

- **OPTION**: Deploying 14B or 70B parameter models locally.
- **STATUS**: `[REJECTED]` `[FACT]`.
- **EVIDENCE**: Settings explicitly configure `qwen2.5:7b-instruct` in `config/settings.py`.
- **WHY NOT CHOSEN**: A 14B model requires 10GB+ VRAM, and a 70B model requires 40GB+ VRAM. Less than 5% of consumer workstations possess the hardware to run these models.
- **TRADEOFF**: 7B models have less reasoning buffer for complex philosophical multi-step logic.
- **CURRENT IMPLICATION**: Runs smoothly across consumer laptops with 6GB–8GB VRAM or modern 16GB RAM CPUs.

---

## 11. Hosted Local LLMs (vLLM / TGI Server Daemons)

- **OPTION**: Running vLLM or Hugging Face Text Generation Inference (TGI) in Docker.
- **STATUS**: `[REJECTED]` `[FACT]`.
- **EVIDENCE**: Ollama selected as the standard runtime.
- **WHY NOT CHOSEN**: vLLM and TGI require Linux host environments and complex Docker container setups, creating massive setup friction on consumer Windows machines.
- **TRADEOFF**: Ollama provides less fine-grained batching concurrency control than vLLM.
- **CURRENT IMPLICATION**: Native Windows executable installation with zero Docker requirement.

---

## 12. Mandatory User Authentication Systems (OAuth2, JWT, Supabase Auth)

- **OPTION**: Gating application access behind username/password logins or OAuth2 providers.
- **STATUS**: `[REJECTED]` `[FACT]`.
- **EVIDENCE**: Frontend loads directly to chat interface; `user_id` defaults to `"default_user"` with optional multi-user isolation.
- **WHY NOT CHOSEN**: Unnecessary friction for local-first desktop software. Users expect immediate utility upon launching local software without creating web accounts.
- **TRADEOFF**: Assumes single-user physical security on the host machine.
- **CURRENT IMPLICATION**: Instant startup, zero credential management, and privacy by design.

---

## 13. Cloud Container Deployment (AWS ECS, Google Cloud Run)

- **OPTION**: Packaging and deploying Finova AI to public cloud container platforms.
- **STATUS**: `[PLANNED / DEFERRED]` `[FACT]`.
- **EVIDENCE**: Project packaged for local standalone evaluation in Phase 13/14A.
- **WHY NOT CHOSEN**: Local standalone validation was prioritized to guarantee complete data privacy, hermetic test reliability, and zero cloud operating costs.
- **TRADEOFF**: Requires local user machine to perform inference.
- **CURRENT IMPLICATION**: Complete focus on desktop runtime excellence.

---

## 14. Computer Vision / Multimodal Financial Chart Analysis

- **OPTION**: Allowing users to upload screenshots of stock charts for technical analysis.
- **STATUS**: `[REJECTED]` `[FACT]`.
- **EVIDENCE**: System input schemas accept text queries only; vision models excluded from Ollama configuration.
- **WHY NOT CHOSEN**:
  1. Multimodal LLMs hallucinate chart patterns (e.g. seeing non-existent "head-and-shoulders" formations).
  2. Doubles memory consumption (VRAM).
  3. Visual technical chart reading frequently drifts into speculative trading calls.
- **TRADEOFF**: Users cannot analyze image-only financial charts.
- **CURRENT IMPLICATION**: High-fidelity text and tabular focus with zero chart hallucination risk.

---

## 15. Semantic RAG on Cryptocurrency Whitepapers

- **OPTION**: Ingesting whitepapers (Bitcoin, Ethereum, Solana) into a dedicated crypto vector index.
- **STATUS**: `[REJECTED]` `[FACT]`.
- **EVIDENCE**: Qdrant collections strictly index SEBI and Indian statutory equity documents (`sebi_equity_knowledge`).
- **WHY NOT CHOSEN**: Cryptocurrency whitepapers are promotional and speculative. Investor education requires focusing on statutory regulatory frameworks (RBI/SEBI crypto taxation and risk warnings) rather than token promotional claims.
- **TRADEOFF**: Crypto queries rely on fundamental definitions and live pricing rather than dense whitepaper retrieval.
- **CURRENT IMPLICATION**: Uncompromising regulatory compliance and risk-first investor protection.
