# Finova AI — Intelligent Financial Education & Analysis Assistant

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![React 19](https://img.shields.io/badge/react-19-61dafb.svg)](https://react.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.1.0-009688.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Finova AI is a local-first, multi-agent financial intelligence and educational assistant. Built to provide reliable, verifiable financial learning, Finova AI combines an instruction-tuned local LLM with deterministic calculation engines, authoritative regulatory grounding (SEBI/NISM investor education), live market data feeds, and rigorous safety guardrails.

---

## 1. Overview

Finova AI addresses the critical problem of hallucinations and ungrounded advice in financial AI. Rather than relying on a general-purpose conversational LLM to invent formulas or quote unverified stock figures, Finova AI implements a modular architecture:
- **Central Multi-Agent Orchestrator**: Classifies and decomposes user queries across specialized financial domains.
- **Deterministic Tool Layer**: Executes exact mathematical formulas for compounding, options payoffs, Black-Scholes Greeks, budget allocations, and portfolio analytics in pure Python code.
- **Authoritative RAG Retrieval**: Grounds educational responses in official publications from the Securities and Exchange Board of India (SEBI) and the National Institute of Securities Markets (NISM), returning transparent source citations and page provenance.
- **Local-First Privacy & Identity**: Stores chat history and learner progress in local SQLite databases, completely isolated on the user's machine with built-in PII validation and privacy controls.

---

## 2. Purpose

The purpose of Finova AI is to empower learners to understand Indian and global financial concepts safely and accurately. It acts as an interactive personal tutor that teaches:
- How securities and market mechanisms work (primary vs. secondary markets, clearing, settlement).
- How personal financial planning tools function (SIP compounding, emergency funds, debt management).
- How derivatives and risk management operate (hedging, options spreads, Greek sensitivities).
- How to interpret live market information without succumbing to speculative hype or emotional trading.

---

## 3. Main Capabilities

- **Multi-Intent Query Decomposition**: Seamlessly breaks down complex, multi-part questions (e.g., *"What is the current price of TCS and how should I calculate an emergency fund?"*) into distinct domain subtasks, aggregates results, and presents a cohesive answer.
- **Deterministic Financial Calculators**: Guaranteed numerical precision for SIP compounding, 50-30-20 budgeting, emergency funds, and derivatives payoffs without LLM arithmetic errors.
- **Options & Derivatives Payoff Modeling**: Interactive payoff tables, breakeven calculations, maximum profit/loss metrics, and Black-Scholes Greeks calculations for call and put options.
- **Live & Cached Indian Market Data**: Real-time quotes for NSE/BSE equities with session awareness (market open/closed), trading clock validation, and freshness timestamps.
- **Cryptocurrency Market Analytics**: Dual-currency (INR and USD) market quotes and 24-hour metrics powered by public CoinGecko feeds.
- **Authoritative RAG Grounding**: Semantic vector search across official regulatory investor education PDFs with verifiable citation cards (source, authority level, publication date, URL).
- **Interactive Adaptive Quizzes**: Generates topic-tailored financial education questions with instant client-side grading and detailed pedagogical explanations.
- **Simulated Portfolio Stress Testing**: Evaluates simulated equity and mutual fund holdings under hypothetical market drops (e.g., a 10% NIFTY drawdown) with holding-level impact breakdowns.
- **Learner Identity & Privacy Controls**: Stores user preferences and learning modules locally; enforces strict PII rejection (PAN, Aadhaar, phone numbers, bank details) and provides a one-click memory purge.
- **Deterministic Safety Guardrails**: Sub-millisecond regex and pattern matching to intercept registered investment adviser (RIA) impersonation attempts, guaranteed-return promises, and prompt injection attacks.

---

## 4. Available Tutor & Domain Sections

Finova AI provides 9 dedicated tutor contexts with domain-isolated chat histories:

| Section | Domain Tag | Scope & Capabilities |
| :--- | :--- | :--- |
| **General Chat** | `ALL` | Central multi-agent orchestrator handling compound queries, cross-domain comparisons, and general financial literacy. |
| **Equity Tutor** | `EQUITY` | Indian stock market mechanisms (NSE/BSE), live price quotes, fundamental valuation metrics, and corporate actions (dividends, splits, bonuses). |
| **Derivatives Tutor** | `DERIVATIVES` | Futures and options (F&O) mechanics, Bull/Bear spreads, interactive payoff tables, breakeven analysis, and Black-Scholes Greeks. |
| **Personal Finance** | `PERSONAL_FINANCE` | Systematic Investment Plans (SIP), compound wealth accumulation, emergency fund sizing, and 50-30-20 budget frameworks. |
| **Crypto Tutor** | `CRYPTO` | Blockchain fundamentals, major digital assets (BTC, ETH, SOL), CoinGecko INR/USD market quotes, and structural risk factors. |
| **Portfolio Tutor** | `PORTFOLIO` | Simulated portfolio allocation, diversification analysis, asset concentration, and what-if market stress simulations. |
| **Market News** | `NEWS` | Aggregated market headlines, macro economic trends, and regulatory updates with verified source timestamps. |
| **Quiz & Challenge** | `QUIZ` | Interactive financial literacy quizzes covering key investor concepts with instant scoring and explanation feedback. |
| **System Guide** | `ONBOARDING` | Platform architecture overview, available capabilities, sample queries, and navigation walkthroughs. |

---

## 5. High-Level Architecture

```text
┌────────────────────────────────────────────────────────────────────────┐
│               Frontend Presentation (React 19 + TypeScript)            │
│  Interactive Cards (Quotes, Payoffs, Portfolios, Quizzes, Citations)  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTP REST / JSON
┌───────────────────────────────────▼────────────────────────────────────┐
│                    FastAPI Central Gateway (Port 8000)                 │
│         CORS Middleware • Health Checks • Domain Routers               │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
           ┌────────────────────────┼────────────────────────┐
           ▼                        ▼                        ▼
┌───────────────────────┐┌───────────────────────┐┌──────────────────────┐
│ Deterministic Safety  ││ Multi-Agent Router    ││ SQLite Persistence   │
│ & Injection Validator ││ Classifier/Decomposer ││ conversations.db     │
│ (Regex / Structural)  ││ Task Composer         ││ memory.db            │
└───────────────────────┘└──────────┬────────────┘└──────────────────────┘
                                    │
    ┌────────────────┬──────────────┼───────────────┬────────────────┐
    ▼                ▼              ▼               ▼                ▼
┌──────────────┐┌──────────────┐┌──────────────┐┌──────────────┐┌─────────┐
│ Equity Agent ││ Derivatives  ││ Personal Fin.││ Crypto/News  ││ Quiz /  │
│ (NSE/BSE)    ││ (Payoffs/BS) ││ (SIP/Budget) ││ (CoinGecko)  ││ Onboard │
└──────┬───────┘└──────┬───────┘└──────┬───────┘└──────┬───────┘└────┬────┘
       │               │               │               │             │
       └───────────────┴───────┬───────┴───────────────┴─────────────┘
                               │
                ┌──────────────┴──────────────┐
                ▼                             ▼
   ┌──────────────────────────┐  ┌───────────────────────────┐
   │ Qdrant Vector Store      │  │ Ollama Local Runtime      │
   │ (FastEmbed BGE-small)    │  │ qwen2.5:7b-instruct       │
   │ SEBI/NISM Documents      │  │ Port 11434                │
   └──────────────────────────┘  └───────────────────────────┘
```

---

## 6. Technology Stack

- **Backend Framework**: Python 3.10+ (tested on Python 3.13), FastAPI, Uvicorn, Pydantic v2
- **Persistence**: Python standard library `sqlite3` (thread-safe, zero external setup)
- **Local LLM Runtime**: [Ollama](https://ollama.com) running `qwen2.5:7b-instruct`
- **Vector Search & RAG**: Qdrant Client (embedded local disk mode), FastEmbed (`BAAI/bge-small-en-v1.5`), PyPDF
- **Frontend Framework**: React 19, TypeScript 5.9+, Vite 8, Tailwind CSS v4, Lucide React, React Markdown
- **Market Data Adapters**: yfinance, CoinGecko public API, RSS news feeds
- **Testing & Quality**: Pytest, AnyIO, Starlette TestClient, Oxlint

---

## 7. Local Prerequisites

Before running Finova AI locally, ensure your environment has:

1. **Python**: Version 3.10 or higher (Python 3.11–3.13 recommended).
2. **Node.js & npm**: Node.js 18+ and npm 9+.
3. **Ollama**: Download and install from [ollama.com](https://ollama.com).
4. **Ollama Model**:
   ```bash
   ollama run qwen2.5:7b-instruct
   ```

---

## 8. Installation & Setup

### Step 1: Clone the Repository
```bash
git clone https://github.com/pranavsawant0629-tech/finova-ai.git
cd finova-ai
```

### Step 2: Set Up Python Virtual Environment
```powershell
# Windows PowerShell
python -m venv .venv-finova
.venv-finova\Scripts\Activate.ps1

# Linux / macOS
python3 -m venv .venv-finova
source .venv-finova/bin/activate
```

### Step 3: Install Backend Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables
```bash
# Copy the example environment file
cp .env.example .env
```

### Step 5: Install Frontend Dependencies
```bash
cd frontend
npm install
cd ..
```

### Step 6: (Optional) Ingest Official Knowledge Documents
To populate the embedded Qdrant vector database with official SEBI/NISM educational materials:
```bash
.venv-finova\Scripts\python scripts/ingest_docs.py
```

---

## 9. Exact Commands to Run the Application

### Option A: Unified Local Runner (Recommended)

From the project root directory, run:

```powershell
# Windows PowerShell
.venv-finova\Scripts\python scripts/run_local.py

# Linux / macOS
.venv-finova/bin/python scripts/run_local.py
```

The runner automatically:
1. Verifies that Ollama is active on port `11434`.
2. Starts the FastAPI backend on port `8000`.
3. Verifies frontend dependencies and starts the Vite development server.
4. Provides a direct link to open the web interface.

### Option B: Manual Startup (Separate Terminals)

**Terminal 1 — Backend**:
```powershell
.venv-finova\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

**Terminal 2 — Frontend**:
```powershell
cd frontend
npm run dev
```

Open your browser and navigate to `http://localhost:5173`.

---

## 10. Service Ports & Endpoints

| Service | Address | Description |
| :--- | :--- | :--- |
| **Frontend Web App** | `http://localhost:5173` | Vite development server (React 19 UI) |
| **Backend REST API** | `http://127.0.0.1:8000` | FastAPI server with CORS enabled |
| **Interactive API Docs**| `http://127.0.0.1:8000/docs` | Swagger UI for endpoint testing |
| **Ollama Local LLM** | `http://127.0.0.1:11434` | Local model inference server |

---

## 11. Testing & Validation

The project includes an extensive test suite verifying mathematical correctness, routing accuracy, privacy hardening, and safety bounds:

### Backend Automated Test Suite
```powershell
.venv-finova\Scripts\python.exe -m pytest
```
*Expected: 525 passed, 0 failures.*

### Frontend Production Build
```powershell
cd frontend
npm run build
```
*Expected: TypeScript typecheck passes and Vite produces optimized production assets.*

### Frontend Linting
```powershell
cd frontend
npm run lint
```
*Expected: Oxlint runs across 27+ files with 0 errors and 0 warnings.*

---

## 12. Project Structure

```text
finova-ai/
├── app/                        # FastAPI application source
│   ├── agents/                 # Domain agents (equity, crypto, derivatives, etc.)
│   ├── api/                    # REST routes and controllers
│   ├── conversations/          # Conversation sessions, store & title generator
│   ├── core/                   # Telemetry, metrics and system logging
│   ├── eval/                   # Evaluation harnesses and benchmark models
│   ├── llm/                    # Ollama LLM client integration
│   ├── memory/                 # SQLite user memory engine & privacy filters
│   ├── rag/                    # Parsing, chunking, embeddings & vector store
│   ├── router/                 # Query classification, decomposition, composer
│   ├── safety/                 # Deterministic safety & injection guardrails
│   ├── tools/                  # Deterministic math, options, quotes, portfolios
│   └── main.py                 # FastAPI application root & middleware setup
├── config/                     # Configuration and environment loaders
├── data/                       # Grounding knowledge & evaluation datasets
│   ├── evals/                  # Benchmark JSON suites for RAG, safety & routing
│   ├── market/                 # Market schedules and holiday calendars
│   ├── quiz/                   # Curated educational quiz bank
│   ├── raw/                    # Official SEBI investor educational PDFs
│   └── manifest.json           # Document ingestion manifest
├── docs/                       # Local trial guides and operational docs
├── frontend/                   # React 19 + TypeScript + Vite application
│   ├── public/                 # Favicons and SVG asset symbols
│   ├── src/
│   │   ├── api/                # API client and TypeScript contracts
│   │   ├── components/         # Reusable UI cards, chat layout, sidebar
│   │   ├── hooks/              # Custom React hooks (useChat, useIdentity, useTheme)
│   │   ├── index.css           # Tailwind CSS v4 design system
│   │   └── main.tsx            # Application DOM mount
│   ├── package.json            # Frontend package manifest
│   └── vite.config.ts          # Vite build configuration
├── project-info/               # Project plans, architectural designs and reports
├── reports/                    # Benchmark scorecards and evaluation outputs
├── scripts/                    # Ingestion pipeline, benchmark & local runner
├── tests/                      # 525 automated pytest unit and integration tests
├── .env.example                # Template environment variables
├── .gitignore                  # Git ignore rules for runtime artifacts & secrets
├── requirements.txt            # Python dependencies
└── README.md                   # Project documentation
```

---

## 13. Persistence & Memory Architecture

Finova AI adheres to a strict local-first data isolation model:
- **Zero Cloud Leakage**: All conversations and user memories are stored strictly on the local machine in standard SQLite databases (`data/conversations.db` and `data/memory.db`).
- **Domain-Bound Conversations**: Chat sessions are assigned to specific learning domains with deterministic, clean titles generated from the opening prompt without consuming LLM tokens.
- **Privacy Hardening**: Extracted user memories (experience level, risk profile, learning preferences) are passed through an automated privacy validator. Any attempt to record Personally Identifiable Information (PAN cards, Aadhaar numbers, email addresses, phone numbers, or bank accounts) is unconditionally rejected.
- **User Control & Deletion**: Users can review active memories in the Profile modal and perform an instant, deterministic wipe ("Clear Memory") that deletes records from the database.

---

## 14. RAG & Grounding Behavior

- **Authoritative Ingestion**: Knowledge is ingested directly from primary regulatory publications (SEBI and NISM investor booklets) covering equities, mutual funds, derivatives, and investor protections.
- **Dense Vector Retrieval**: Documents are parsed into clean text chunks, embedded via FastEmbed (`BAAI/bge-small-en-v1.5`), and indexed into an embedded Qdrant vector collection.
- **Provenance & Citations**: Responses derived from the knowledge store provide exact citation cards showing the official publisher, document title, authority level (Tier 1), publication date, and page numbers.
- **Out-of-Corpus Fallback**: When an inquiry falls outside the indexed regulatory corpus or below the similarity threshold (`0.65`), Finova AI explicitly states the lack of authoritative regulatory grounding rather than inventing unsourced rules or claims.

---

## 15. Safety & Educational Disclaimer

> **IMPORTANT NOTICE**
> 
> Finova AI is strictly an **educational and analytical platform** designed to teach financial concepts, market mechanisms, and mathematical modeling.
> 
> - **Not Financial Advice**: Finova AI is **not** a SEBI-registered Investment Adviser (RIA), Research Analyst (RA), portfolio manager, broker, or tax consultant. No content, calculation, or output produced by Finova AI constitutes personalized investment advice, buy/sell recommendations, portfolio allocation calls, or endorsements of specific securities or digital assets.
> - **No Guaranteed Returns**: Under financial regulations and fundamental economic laws, guaranteed returns do not exist. All financial markets, equities, derivatives, mutual funds, and digital assets carry market risk, including the potential loss of principal.
> - **Independent Consultation**: Users should always conduct their own independent research and consult certified, registered financial professionals before making real-world financial commitments or investment decisions.

---

## 16. Local-First Limitations

- **Hardware Performance**: Response generation speed is dependent on host CPU/GPU capabilities. Running `qwen2.5:7b-instruct` locally typically requires 2 to 15 seconds per turn.
- **Offline / Sandbox Market Data**: In environments without an active internet connection or external API access, live market feeds fall back to deterministic mock providers and cached session data.
- **Simulated Execution**: All portfolio modifications, stress tests, and trading mechanisms are simulated educational sandbox environments. Finova AI does not connect to live brokerages, exchange trading engines, or bank accounts.

---

## 17. Status of TradeWise Integration

**TradeWise integration is NOT included in this release.**

Finova AI is packaged as an independent, fully self-contained product (Phase 13 release status). While future roadmap specifications contemplate external platform integration with TradeWise, no TradeWise API connectors, shared authentication tokens, or remote dependencies are included or activated in this repository.

---

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
