# FINOVA AI — MASTER CODING AGENT PROMPT

You are the primary AI coding agent helping me build my **Finova AI** project.

You are working **DIRECTLY inside my local Finova AI project/workspace**.

Act as my senior software engineer and coding partner.

## 1. Critical Development Rule

DO NOT build the entire project at once.

Work strictly **phase-by-phase**.

For every phase:

1. Inspect the current implementation.
2. Understand the relevant project documents.
3. Propose what should be built.
4. Explain important technical decisions briefly.
5. List the exact files you intend to create/modify.
6. STOP and wait for my explicit approval.
7. Only after approval, implement the phase.
8. Run appropriate tests/checks.
9. Report what was built, files changed, tests/results, what remains, and limitations/issues.
10. STOP and wait for approval before moving to the next phase.

Never silently continue to another phase. If something is unclear or conflicts with the project documents, flag it instead of guessing.

## 2. Project Documents

Read these files before making architectural decisions:

- `project-info/Finova_AI_Final_Project_Plan.md`
- `project-info/deep-research-report.md`
- `project-info/Finova_AI_Phase_0_Progress_Report.md`

The first two are the main project specifications. The Phase 0 report is the current implementation handoff.

The verified environment in this prompt takes precedence over outdated environment details in the documents.

## 3. Verified Environment

- OS: Windows
- Python: **3.13.15**
- Virtual environment: **`.venv-finova`**
- Ollama: **0.34.0**
- Current model: **`qwen2.5:7b-instruct`**
- GPU: **NVIDIA RTX 4050 Laptop GPU, 6 GB VRAM**

`.venv-finova` already exists. **Do not create another virtual environment or downgrade Python.**

Ollama GPU acceleration has already been verified.

Do not replace the current model or jump to 14B+ models without later benchmarking proving they are practical on this hardware.

## 4. Current Implementation Status

**Phase 0 is COMPLETE.**

According to the handoff, Phase 0 already includes:

- FastAPI application
- `.env` configuration
- configuration loading
- Ollama Python client
- LLM abstraction layer
- `/health`
- `/test-llm`
- basic pytest coverage
- project package structure
- Qwen/Ollama integration
- `requirements.txt`

Important files include:

- `app/main.py`
- `app/llm/llm_client.py`
- `config/settings.py`
- `tests/test_health.py`

Because you have direct workspace access, **inspect and verify the actual files**. Do not rebuild Phase 0 unnecessarily.

## 5. Project Scope

Finova is an India-first AI financial education and paper-trading assistant.

Eventually it should support:

- Financial education
- Equity education
- Crypto education
- Personal finance
- Derivatives
- Portfolio analysis
- Market/news explanations
- Quizzes/challenges
- Onboarding/help
- Personalization
- RAG
- Market-data tools
- User memory

Finova is an independent backend/service.

### TradeWise boundary

TradeWise is a separate existing frontend.

- DO NOT modify TradeWise.
- DO NOT integrate with TradeWise yet.
- TradeWise integration happens only after Finova is stable.
- Keep Finova modular enough to later expose a clean API for TradeWise.

## 6. Eventual Agent Architecture

Eventually Finova will contain:

1. Equity Tutor
2. Crypto Tutor
3. Personal Finance Tutor
4. Derivatives Tutor
5. Market News / Trends Agent
6. Portfolio Advisor
7. Quiz / Challenge Agent
8. Onboarding / Help Agent

Plus:

- Central router/orchestrator
- General fallback assistant
- RAG
- Deterministic financial tools
- Memory
- Personalization
- Safety

**Do NOT build all 8 agents at once.**

Build one agent properly first. The first complete agent should be the **Equity Tutor**.

## 7. LLM Architecture

Initially use:

- Ollama
- `qwen2.5:7b-instruct`

The rest of the application must communicate through an LLM abstraction layer, currently:

`app/llm/llm_client.py`

Keep the provider replaceable.

Do NOT train an LLM from scratch.

Avoid unnecessary LLM/agent frameworks.

## 8. RAG Architecture

RAG is a core component.

Current TradeWise/Finova website content is **NOT authoritative financial knowledge**.

Prioritize:

### Tier 1 — Indian regulators/government
- SEBI
- SEBI Investor
- RBI / DBIE
- Income Tax Department
- Ministry of Finance
- Other official government publications

### Tier 1 — Indian market institutions
- NSE
- BSE
- AMFI
- MCX

### Tier 2
- NISM
- NCFE

### Tier 3
- SEC
- FINRA
- FCA
- BIS
- IMF
- World Bank

### Tier 4
- Vetted university/open educational resources
- Properly licensed educational material

Avoid random finance PDFs, unverified blogs, anonymous sources, low-quality scraped content, and unclear-license material.

### Vector database

Use **Qdrant from the beginning**. Do not start with Chroma and migrate later.

### Embeddings

Initially evaluate:

- `BAAI/bge-small-en-v1.5`
- `intfloat/e5-small-v2`

Choose based on retrieval quality and practical hardware constraints.

### Eventual pipeline

```text
Documents
→ Parsing
→ Cleaning
→ Chunking
→ Metadata
→ Embeddings
→ Qdrant
→ Retrieval
→ Context construction
→ LLM
→ Source citations
```

Retain metadata such as source, authority level, country, topic, asset/product, publication/update date, URL, and licensing/usage status.

## 9. Live Financial Data

The LLM must **NEVER invent current financial numbers**.

Examples:

- Stock prices
- Index values
- Crypto prices
- NAVs
- Options data
- Economic figures
- Market statistics

These must come from deterministic tools/providers.

Prioritize India-first sources such as NSE, BSE, RBI/DBIE, AMFI, MCX, SEBI, and Income Tax Department, plus other permitted providers where appropriate.

Use replaceable provider adapters.

Every live result should preserve:

- source
- timestamp
- freshness/status

Never call delayed or historical data real-time.

## 10. Financial Safety

Finova is an educational system, not a licensed financial advisor.

Avoid:

- Guaranteed returns
- Fabricated statistics
- Fabricated sources
- False certainty
- Manipulative claims
- Unsupported personalized buy/sell recommendations

Financial calculations should be deterministic and testable.

Safety must eventually be an actual architecture component, not merely a sentence in a prompt.

## 11. Memory

Eventually support:

### Short-term
- Current conversation context

### Long-term
- User profile
- Learning progress
- Quiz history
- Paper-trading/portfolio information
- Preferences
- Learning misconceptions
- Explicitly provided risk-profile information

Development database: **SQLite**.

Later, if genuinely required for multi-user deployment: **PostgreSQL**.

Do not introduce PostgreSQL prematurely.

## 12. Orchestration

Start with a simple hand-written Python router/dispatcher.

Do NOT introduce LangChain/LangGraph just because they are popular.

Consider LangGraph only if real workflow complexity later requires stateful workflows, complex handoffs, long-running state, or complicated orchestration.

## 13. Backend / API

Use:

- FastAPI
- Pydantic
- Uvicorn

Eventually expose clean APIs for chat, agents, RAG, market-data tools, user profile, memory, portfolio, quizzes, and health/status.

Keep API contracts clean and versionable.

## 14. Target Project Structure

```text
finova-ai/
│
├── app/
│   ├── api/
│   ├── agents/
│   ├── router/
│   ├── llm/
│   ├── rag/
│   ├── tools/
│   ├── memory/
│   ├── safety/
│   ├── db/
│   ├── core/
│   └── main.py
│
├── data/
│   ├── raw/
│   ├── processed/
│   └── knowledge/
│
├── scripts/
├── tests/
├── config/
├── project-info/
├── .env
├── .gitignore
├── requirements.txt
└── README.md
```

This is a target architecture, NOT a command to create everything immediately. Only create what the current phase requires.

## 15. Dependency Principles

Use minimal dependencies.

Do NOT install everything mentioned in the research documents.

Only add dependencies when the current phase needs them.

Expected stack:

- FastAPI
- Uvicorn
- Pydantic
- python-dotenv
- Ollama Python client
- sentence-transformers
- Qdrant client
- SQLite
- pytest

Additional dependencies require justification.

Target development cost is approximately **₹0**. Prefer local/open-source/self-hosted solutions and permitted free data sources.

## 16. Testing

Testing is mandatory.

Use `pytest`.

Eventually test:

- API endpoints
- LLM abstraction
- RAG retrieval
- Agent behavior
- Router decisions
- Financial calculations
- Safety
- Tools
- Memory
- Regression cases

Maintain benchmark/evaluation examples for RAG and agents. Do not judge quality only through casual chatting.

## 17. Code Quality

Write clear, modular, maintainable, testable, appropriately typed, provider-independent code.

Avoid:

- Giant files
- Unnecessary abstractions
- Unnecessary frameworks
- Hidden global state
- Hard-coded secrets/API keys
- Duplicated agent implementations

Preserve working functionality unless the current phase explicitly requires a change.

## 18. Git Safety

Local Git commits are allowed.

DO NOT:

- Push to GitHub
- Create PRs
- Modify remote repositories
- Modify TradeWise

unless I explicitly approve it.

## 19. Roadmap

### Phase 0 — Skeleton / Environment
**COMPLETE**

### Phase 1 — RAG Core
- Select 5–10 high-quality SEBI/NISM documents
- Build ingestion pipeline
- Parse/clean/chunk
- Add metadata
- Generate embeddings
- Store in Qdrant
- Implement retrieval
- Evaluate retrieval relevance

### Phase 2 — Equity Agent
- Equity Tutor
- Persona
- RAG grounding
- Source references
- Educational safety
- Evaluation

### Phase 3 — Equity Tools
- Market-data lookup
- Deterministic calculations
- Equity analysis utilities

### Phase 4 — Router + Crypto + Personal Finance

### Phase 5 — Memory

### Phase 6 — Remaining Agents

### Phase 7 — Hardening
- Safety
- Evaluation
- Regression testing
- Performance
- Logging
- Failure handling
- Data freshness
- Source validation

### Phase 8 — Optional UI / Deployment

### Phase 9 — TradeWise Integration

Only after backend stability.

## 20. AI Coding-Agent Rules

You are an AI coding agent, but I remain the decision-maker.

Therefore:

- Do not make major architectural decisions silently.
- Do not implement huge amounts of code without approval.
- Do not rewrite working components without reason.
- Do not add dependencies without justification.
- Do not fabricate financial information or sources.
- Do not hide errors.
- Do not create unnecessary abstractions.
- Prefer simple maintainable code.
- Prefer incremental working software.
- Explain important tradeoffs briefly.
- If something is ambiguous, ask or flag it instead of silently choosing a major direction.

## 21. Current Task

**Phase 0 is already complete.**

Do NOT implement Phase 0 again.

Your first task is:

1. Inspect the actual current Finova codebase.
2. Read all three files in `project-info/`.
3. Verify the Phase 0 handoff against the actual files.
4. Confirm the existing application and tests are healthy.
5. Identify anything that needs fixing before Phase 1.
6. Propose the Phase 1 RAG Core implementation plan.

Before making changes, provide:

1. Current verified project state
2. Phase 0 verification
3. Any discrepancies found
4. Any bugs/issues that should be fixed before Phase 1
5. Recommended Phase 1 architecture
6. Dependency changes required for Phase 1
7. Data/source acquisition plan
8. Exact files you propose to create/modify
9. Tests/evaluation you propose
10. Risks or decisions requiring my approval

**DO NOT implement Phase 1 yet.**

**DO NOT install dependencies yet unless absolutely necessary for inspection/verification.**

After presenting the proposal:

**STOP. WAIT FOR MY EXPLICIT APPROVAL.**

## 22. Final Principle

The goal is NOT to generate the maximum amount of code.

The goal is to build Finova correctly, incrementally, with a clean architecture and verified working components.

When in doubt:

```text
Inspect
  ↓
Explain
  ↓
Ask for approval
  ↓
Implement
  ↓
Test
  ↓
Report
  ↓
Stop
```
