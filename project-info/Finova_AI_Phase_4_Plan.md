# FINOVA AI — PHASE 4 ARCHITECTURAL & IMPLEMENTATION PLAN

**Phase Title:** Multi-Domain Query Routing, Multi-Intent Decomposition, Crypto & Personal Finance Agents  
**Status:** REVISED & REFINED (Awaiting User Approval to Begin Stage 4A)  
**Target Hardware:** Windows 11 | Python 3.13.15 | NVIDIA RTX 4050 Laptop GPU (6 GB VRAM) | 16 GB System RAM  
**Cost Target:** ₹0 Infrastructure / Local-First Open Source Stack  
**Verification Baseline:** 117 / 117 tests passing in Phases 0–3  

---

## 1. Executive Summary

Finova AI has successfully established its foundation across three locked phases:
- **Phase 0 (Foundation):** FastAPI backend, local Ollama client (`qwen2.5:7b-instruct`), configuration infrastructure, health/test endpoints.
- **Phase 1 (Authoritative RAG Core):** Official SEBI educational document parsing, chunking, FastEmbed embeddings (`BAAI/bge-small-en-v1.5`), embedded Qdrant vector storage, and deterministic retrieval with provenance citations (`/rag/retrieve`).
- **Phase 2 (Equity Tutor Agent):** Deterministic safety/advisory guardrail, SEBI-grounded educational answer generation, citation validation, out-of-corpus LLM bypass, and standardized TradeWise JSON response contracts (`POST /agents/equity/ask`).
- **Phase 3 (Deterministic Market Data Layer):** Market data models, IST market clock, holiday calendar, primary Yahoo Finance provider, secondary Twelve Data fallback, in-memory caching with dynamic session-aware TTLs, stale-data failover, multi-stage validation, and regex-based market intent classification. Phase 3 is locked and verified with 117 passing automated tests.

**Phase 4 Goal:**  
Transform Finova AI from an Equity-focused prototype into a complete multi-domain educational platform by implementing:
1. **Central Router & Orchestrator:** Global safety pre-filtering, fast-path classification, and domain dispatch.
2. **Multi-Intent Decomposition:** Structuring compound and cross-domain inquiries into isolated sub-tasks.
3. **Response Composition:** Combining multi-source outputs where numerical outputs originate from validated deterministic tools and are not modified by the response composer.
4. **Crypto Agent:** Educational tutoring on blockchain, Bitcoin, Ethereum, tokenomics, DeFi, and crypto volatility, with live data accessed strictly through a replaceable `BaseCryptoProvider` abstraction.
5. **Personal Finance Agent:** Educational tutoring on budgeting, saving, debt, and emergency planning powered by unit-tested, deterministic financial calculation tools.

---

## 2. Current Architecture Assessment

### 2.1 Existing Execution Flow
```text
User Query
    │
    ▼
[EquityAgent.ask()] (app/agents/equity/agent.py)
    │
    ├── Step 1: EquitySafetyGuardrail.evaluate()
    │           └── If unsafe: Return refusal (LLM & RAG bypassed)
    │
    ├── Step 2: MarketIntentClassifier.classify() (app/tools/market/intent.py)
    │           ├── Market Status: MarketDataService.get_market_status() -> Return deterministic text
    │           ├── Quote / Historical / Overview: MarketDataService -> Return deterministic text
    │           └── If Hybrid: Returns quote text + static note "ask me separately about [concept]"
    │
    └── Step 3: RAGService.generate_answer() (Fallback for non-market queries)
                ├── Qdrant retrieval (score_threshold >= 0.65)
                ├── If 0 chunks: Return UNGROUNDED_TOPIC_MESSAGE (LLM bypassed)
                └── If chunks: Prompt assembly -> LLM chat -> Citation verification -> Return
```

### 2.2 Critical Gaps to Address
1. **Single-Domain Coupling:** Routing is hardcoded inside `EquityAgent`. `app/router/` is an empty directory.
2. **Hybrid Query Drop-off:** Compound queries return market data but drop the educational branch.
3. **Absence of Crypto & Personal Finance Agents:** No tutors exist for digital assets or personal financial planning.
4. **Scattered Safety Logic:** Domain-specific safety rules lack a unified global enforcement layer.

---

## 3. Phase 4 Architecture & Orchestration Flow

```text
                                  User Query
                                       │
                                       ▼
                     ┌───────────────────────────────────┐
                     │      1. Global Safety Filter      │  (<1ms Regex Pre-Filter)
                     └─────────────────┬─────────────────┘
                                       │
                       [Passes Safety] │ [Violates Safety] ──► Immediate Refusal
                                       ▼
                     ┌───────────────────────────────────┐
                     │   2. Central Router / Classifier  │
                     └─────────┬───────────────────┬─────┘
                               │                   │
                [Single-Intent]│                   │[Multi-Intent / Compound]
                               ▼                   ▼
                     ┌──────────────────┐ ┌───────────────────────────────────┐
                     │ Fast-Path Router │ │ 3. Query Decomposer               │
                     └─────────┬────────┘ │ - Intent Segmentation             │
                               │          │ - Entity Extraction               │
                               │          └─────────────────┬─────────────────┘
                               │                            │
                               ▼                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 4. Execution Layer                                     │
│  ┌───────────────────────┬───────────────────────────────┬──────────────────────────┐  │
│  │     Equity Agent      │         Crypto Agent          │  Personal Finance Agent  │  │
│  │  - SEBI RAG Service   │  - Blockchain/Crypto Pedagogy │  - Budgeting Pedagogy    │  │
│  │  - NSE/BSE Tools      │  - Crypto Safety Filter       │  - Personal Finance Safe │  │
│  │  - Valuation / Status │  - BaseCryptoProvider Tool    │  - Deterministic Math    │  │
│  └───────────┬───────────┴───────────────┬───────────────┴──────────────┬───────────┘  │
└──────────────┼───────────────────────────┼──────────────────────────────┼──────────────┘
               │                           │                              │
               └───────────────────────────┼──────────────────────────────┘
                                           ▼
                     ┌───────────────────────────────────┐
                     │     5. Response Composer          │
                     │  - Numerical Output Preservation  │
                     │  - Authoritative Citations        │
                     │  - Markdown Layout & Disclaimers  │
                     └─────────────────────┬─────────────┘
                                           │
                                           ▼
                     ┌───────────────────────────────────┐
                     │  Unified Response Contract (JSON) │
                     └───────────────────────────────────┘
```

---

## 4. Unified Safety Architecture

### 4.1 Global Safety Layer Design
Safety operates as a single global filter (`app/router/safety.py`) with domain-specific rule modules underneath it:
- **Global Entrypoint:** `GlobalSafetyGuardrail.evaluate(query: str) -> GlobalSafetyResult`
- Runs **before** any agent dispatch, tool execution, or LLM invocation.
- Ensures no contradictory safety decisions between agents.

### 4.2 Domain-Specific Rule Modules
1. **Equity Safety Rules (`EquitySafetyRules`):**
   - Blocks: personalized stock recommendations, buy/sell directives on specific tickers, price targets, guaranteed returns.
   - Allows: conceptual questions regarding market mechanisms, order types, settlement, and valuation metrics.
2. **Crypto Safety Rules (`CryptoSafetyRules`):**
   - Blocks: "Should I buy Bitcoin?", "Which coin will 10x?", speculative price targets, token buy/sell calls, guaranteed staking yields.
   - Allows: educational questions on blockchain consensus, smart contracts, tokenomics, DeFi mechanisms, and crypto volatility risks.
3. **Personal Finance Safety Rules (`PersonalFinanceRules`):**
   - Blocks: personalized asset allocation directives ("Where should I invest my ₹50,000?"), binding tax advice, specific insurance product recommendations.
   - Allows: general budgeting frameworks (e.g., 50/30/20), emergency fund guidelines, debt payoff strategies (snowball vs. avalanche), and savings definitions.

---

## 5. Query Routing & Multi-Intent Decomposition Strategy

### 5.1 Hierarchical Routing Strategy
- **Stage 1: Global Safety Check (< 1ms):** Immediate refusal for advisory/speculative queries.
- **Stage 2: Deterministic Fast-Path Classifier (< 1ms):**
  - Uses high-confidence regex patterns and canonical symbol tables to detect single-domain, single-intent queries.
  - Domains: `EQUITY`, `CRYPTO`, `PERSONAL_FINANCE`, `GENERAL`.
  - Dispatches directly to the target agent without LLM overhead.
- **Stage 3: Rule-Guided Query Decomposer:**
  - Segments compound queries across conjunctions (`and`, `also`, `as well as`).
  - Isolates multi-intent and cross-domain inquiries (e.g., *"What is P/E ratio and how should I budget my salary?"* ➔ Equity RAG sub-task + Personal Finance sub-task).
  - Handles multi-entity equity and crypto inquiries (e.g., *"Compare Reliance and TCS price"* or *"What are BTC and ETH trading at?"*).

---

## 6. Response Composition & Numerical Output Integrity

### 6.1 Strict Numerical Output Integrity Guarantee
- **Core Principle:** Numerical outputs originate from validated deterministic tools and are not modified by the response composer.
- The LLM is **never** used to re-synthesize or paraphrase numerical values returned by deterministic tools or calculation engines.
- The Response Composer (`app/router/composer.py`) performs deterministic string formatting:
  - Formats live/delayed equity quotes into structured markdown tables/cards.
  - Formats crypto prices and 24h metrics directly from tool data models.
  - Formats personal finance calculation outputs directly from calculation results.
  - Attaches verified SEBI RAG citations `[1]`, `[2]` strictly to their respective educational passages.
  - Appends appropriate regulatory disclaimers.

---

## 7. Crypto Agent & Authoritative Source Strategy

### 7.1 Architecture & Replaceable Provider
- `CryptoAgent` coordinates educational explanations and market queries.
- **Strict Provider Decoupling:** Live crypto prices are fetched through a clean interface:
  ```python
  class BaseCryptoProvider(ABC):
      @abstractmethod
      def get_quote(self, symbol: str) -> CryptoQuote: ...
      @abstractmethod
      def is_available(self) -> bool: ...
  ```
- `CoinGeckoProvider` implements `BaseCryptoProvider` using the public free API via `httpx` (no API key required).
- `CryptoDataService` manages caching, rate limiting, and provider failover.
- **The `CryptoAgent` depends exclusively on `CryptoDataService` and `BaseCryptoProvider`**, ensuring the provider can be swapped at any time without touching agent logic.

### 7.2 Crypto RAG: Authoritative Sources & Staged Limitation
- **Prohibited Sources:** Unverified crypto blogs, anonymous forums, speculative news sites (e.g., CoinDesk, Cointelegraph, Reddit) are **strictly prohibited** as authoritative RAG sources.
- **Authoritative Crypto Sources Identified:**
  - **Tier 1 (Global & Central Bank Authorities):** Bank for International Settlements (BIS), Financial Stability Board (FSB), International Monetary Fund (IMF), Reserve Bank of India (RBI Working Group Reports and Public Cautionary Notices).
  - **Tier 2/3 (Global Securities Regulators):** SEC Investor Bulletins on Digital Assets, CFTC Customer Advisories, IOSCO Policy Recommendations for Crypto and Digital Asset Markets.
- **Explicit Phase 4 Staged Limitation:**
  - In Phase 4, the Qdrant vector store contains only the official SEBI equity corpus.
  - **Crypto RAG is explicitly marked as a staged limitation:** Finova will **not** fabricate citations or pretend the SEBI corpus covers crypto facts.
  - For Phase 4, conceptual crypto questions are answered via structured pedagogical prompts (Prof. Crypton) with clear risk disclosures. Any RAG query routed to the vector store for crypto will return an explicit `ungrounded` notice rather than an unverified answer. Ingestion of a dedicated Tier 1 crypto regulatory corpus is scheduled as a formal prerequisite for full Crypto RAG grounding in Phase 7.

---

## 8. Personal Finance Agent & Deterministic Calculators

### 8.1 Scope & Architecture
- `PersonalFinanceAgent` (Prof. Persona) provides educational tutoring on budgeting, saving, debt reduction, and financial planning principles.
- Calculations are performed **exclusively** by unit-tested, deterministic Python mathematical tools in `app/tools/calc/`. The LLM never computes or alters financial calculations.

### 8.2 Explicit Mathematical Formulas & Assumptions

#### 1. 50/30/20 Budgeting Calculator (`budget.py`)
- **Assumptions:** Input is monthly net (post-tax) income $I > 0$.
- **Formulas:**
  - $\text{Needs} = \text{round}(0.50 \times I, 2)$ (Essential expenses: housing, utilities, groceries, transportation).
  - $\text{Wants} = \text{round}(0.30 \times I, 2)$ (Discretionary: dining out, entertainment, subscriptions).
  - $\text{Savings \& Debt Repayment} = \text{round}(0.20 \times I, 2)$ (Emergency fund, investments, extra debt payments).

#### 2. Compound Interest Calculator (`compounding.py`)
- **Assumptions:** Principal $P > 0$, annual nominal interest rate $r > 0$ (as decimal, e.g. 0.08 for 8%), compounding frequency $n \ge 1$ times per year (1=annual, 4=quarterly, 12=monthly), time $t > 0$ in years.
- **Formulas:**
  - $\text{Maturity Amount } A = \text{round}\left(P \times \left(1 + \frac{r}{n}\right)^{n \times t}, 2\right)$
  - $\text{Total Interest Earned } I_{\text{total}} = \text{round}(A - P, 2)$

#### 3. Systematic Investment Plan (SIP) Calculator (`compounding.py`)
- **Assumptions:** Monthly installment $P > 0$ invested at the beginning of each period (annuity due), annual expected return rate $r > 0$, investment duration $t > 0$ years.
- **Formulas:**
  - Periodic monthly rate $i = \frac{r}{12}$
  - Total number of monthly contributions $k = t \times 12$
  - Future Value $M = \text{round}\left(P \times \left[ \frac{(1 + i)^k - 1}{i} \right] \times (1 + i), 2\right)$
  - Total Principal Invested $P_{\text{total}} = P \times k$
  - Estimated Wealth Gain = $\text{round}(M - P_{\text{total}}, 2)$

#### 4. Emergency Fund Adequacy Calculator (`emergency_fund.py`)
- **Assumptions:** Monthly essential living expenses $E > 0$, current liquid savings $S \ge 0$, target months $m$ (default 6 months; typical range 3–12 months).
- **Formulas:**
  - Target Emergency Fund $T = \text{round}(E \times m, 2)$
  - Funding Gap = $\text{round}(\max(0, T - S), 2)$
  - Months of Coverage Currently Available = $\text{round}\left(\frac{S}{E}, 1\right)$

---

## 9. Response Contract & Backward Compatibility

### 9.1 Guaranteed Compatibility
- The existing response contract (`EquityQueryResponse` at `POST /agents/equity/ask`) is **100% preserved**. Existing client integrations and tests continue to receive identical fields.
- Phase 3 market-data infrastructure (`app/tools/market/`) remains locked and unchanged.

### 9.2 Unified Orchestrator Response Schema
```python
class SubTaskExecutionMetadata(BaseModel):
    task_id: str
    domain: Literal["EQUITY", "CRYPTO", "PERSONAL_FINANCE", "GENERAL"]
    intent: str
    target: str | None = None
    status: Literal["success", "fallback", "filtered", "error"]
    latency_ms: float

class OrchestratorResponse(BaseModel):
    query: str
    answer: str
    grounding_status: Literal["fully_grounded", "partially_grounded", "ungrounded"]
    citations: list[Citation] = Field(default_factory=list)
    market_data: MarketDataProvenance | None = None
    market_data_list: list[MarketDataProvenance] = Field(default_factory=list)
    crypto_data: CryptoProvenance | None = None
    grounding_sources: list[Literal["sebi_rag", "live_market_data", "crypto_data", "calc_tool"]] = Field(default_factory=list)
    domain_detected: str
    sub_tasks: list[SubTaskExecutionMetadata] = Field(default_factory=list)
    agent_name: str = "Finova Orchestrator"
    disclaimer: str = (
        "Disclaimer: Finova AI is an educational platform and not a registered investment adviser. "
        "Content is for educational purposes only and does not constitute financial advice."
    )
    model_used: str = "qwen2.5:7b-instruct"
    latency_ms: float
```

---

## 10. Implementation Stages (Strict Staging Workflow)

Execution proceeds **strictly stage-by-stage**. At the conclusion of each stage, automated tests are executed, a report is generated, and work **STOPS for explicit user approval** before continuing.

```text
4A ──► Test & Report ──► [STOP / Approval]
 │
4B ──► Test & Report ──► [STOP / Approval]
 │
4C ──► Test & Report ──► [STOP / Approval]
 │
4D ──► Test & Report ──► [STOP / Approval]
 │
4E ──► Test & Report ──► [STOP / Approval]
 │
4F ──► Full Regression & Verification Report
```

### Stage 4A: Central Router / Orchestrator Foundation
- **Objective:** Create domain models, unified global safety filter, fast-path classifier, and basic orchestrator dispatch.
- **Files to Create:**
  - `app/router/models.py`
  - `app/router/safety.py` (Unified global safety encompassing Equity, Crypto, Personal Finance rules)
  - `app/router/classifier.py`
  - `app/router/orchestrator.py`
  - `app/router/__init__.py`
  - `tests/test_router_models.py`
  - `tests/test_router_safety.py`
  - `tests/test_router_classifier.py`
- **Verification:** Unit tests for models, safety rules, and classification accuracy.
- **Exit Action:** STOP and report.

### Stage 4B: Multi-Intent Decomposition
- **Objective:** Implement compound query parsing, clause boundary detection, and entity extraction.
- **Files to Create:**
  - `app/router/decomposer.py`
  - `tests/test_router_decomposer.py`
- **Verification:** Decomposition accuracy on multi-intent, cross-domain, and multi-entity queries.
- **Exit Action:** STOP and report.

### Stage 4C: Response Composition
- **Objective:** Build deterministic markdown assembler that guarantees numerical output integrity and preserves citations.
- **Files to Create:**
  - `app/router/composer.py`
  - `tests/test_router_composer.py`
- **Verification:** Number preservation tests, citation preservation tests, layout tests.
- **Exit Action:** STOP and report.

### Stage 4D: Crypto Agent & Replaceable Provider
- **Objective:** Build Crypto Tutor agent, pedagogical prompts, crypto safety guardrail, and `BaseCryptoProvider` with `CoinGeckoProvider`.
- **Files to Create:**
  - `app/agents/crypto/agent.py`
  - `app/agents/crypto/prompts.py`
  - `app/agents/crypto/safety.py`
  - `app/tools/crypto/models.py`
  - `app/tools/crypto/interfaces.py` (`BaseCryptoProvider`)
  - `app/tools/crypto/service.py`
  - `app/tools/crypto/providers/coingecko_provider.py`
  - `tests/test_crypto_agent.py`
  - `tests/test_crypto_safety.py`
  - `tests/test_crypto_tools.py`
- **Verification:** Educational response tests, provider abstraction tests, safety refusal tests.
- **Exit Action:** STOP and report.

### Stage 4E: Personal Finance Agent & Deterministic Calculators
- **Objective:** Build Personal Finance Tutor agent, prompts, safety rules, and deterministic calculation tools.
- **Files to Create:**
  - `app/agents/personal_finance/agent.py`
  - `app/agents/personal_finance/prompts.py`
  - `app/agents/personal_finance/safety.py`
  - `app/tools/calc/budget.py` (50/30/20 formula)
  - `app/tools/calc/compounding.py` (Compound interest & SIP formulas)
  - `app/tools/calc/emergency_fund.py` (Emergency fund formula)
  - `tests/test_personal_finance_agent.py`
  - `tests/test_finance_calc.py`
- **Verification:** Mathematical precision tests, budgeting tests, financial advice safety tests.
- **Exit Action:** STOP and report.

### Stage 4F: API Integration, Equity Alignment & Full Regression
- **Objective:** Mount API endpoints (`/orchestrator/ask`, `/chat`, `/agents/crypto/ask`, `/agents/personal-finance/ask`), wrap `EquityAgent` through orchestrator with backward compatibility, and execute full regression.
- **Files to Create/Modify:**
  - `NEW` `app/api/chat.py`
  - `NEW` `app/api/crypto.py`
  - `NEW` `app/api/personal_finance.py`
  - `MODIFY` `app/api/equity.py`
  - `MODIFY` `app/agents/equity/agent.py`
  - `MODIFY` `app/agents/equity/safety.py`
  - `MODIFY` `app/main.py`
  - `NEW` `tests/test_orchestrator_e2e.py`
  - `MODIFY` `tests/test_equity_agent.py`
- **Verification:** All 117 previous tests pass + all new Phase 4 tests pass.
- **Exit Action:** Deliver complete Phase 4 report.

---

## 11. Testing & Verification Matrix

| Area | Test File | Target Coverage |
| :--- | :--- | :--- |
| **Router Models** | `tests/test_router_models.py` | Pydantic schema validation, defaults, serialization |
| **Global Safety** | `tests/test_router_safety.py` | Equity tips, crypto 10x calls, personal finance advice, conceptual exceptions |
| **Classifier** | `tests/test_router_classifier.py` | Single-domain accuracy, fast-path bypass latency |
| **Decomposer** | `tests/test_router_decomposer.py` | Compound queries, cross-domain queries, entity extraction |
| **Composer** | `tests/test_router_composer.py` | Numerical preservation, citation mapping, layout |
| **Crypto Agent** | `tests/test_crypto_agent.py`, `test_crypto_safety.py`, `test_crypto_tools.py` | Concepts, quotes, safety refusals, provider failover |
| **Personal Finance** | `tests/test_personal_finance_agent.py`, `test_finance_calc.py` | 50/30/20 math, compounding math, SIP math, emergency fund math |
| **E2E Orchestration** | `tests/test_orchestrator_e2e.py` | Multi-agent workflows, API endpoint validation |
| **Regression** | Entire existing test suite | All 117 Phase 0–3 tests pass without regression |

---

## 12. Explicit Non-Goals for Phase 4
- ❌ No persistent SQLite user profile or multi-turn conversational memory (deferred to Phase 5).
- ❌ No portfolio simulation database or real trading APIs.
- ❌ No news sentiment analysis or live news scrapers (deferred to Phase 6).
- ❌ No UI / TradeWise React frontend changes.
- ❌ No new external pip packages or paid cloud services.
