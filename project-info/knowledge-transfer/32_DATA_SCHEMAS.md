<!-- Generated against commit: 42228bb55d6016ffff439024bbf4aec135269f95 | Date: 2026-09-13 | Verified against live repository state: YES -->

# Part 32: Core Data Contracts & Pydantic Schemas

Finova AI enforces strict runtime typing and structural validation using Pydantic v2 and immutable Python dataclasses. This document serves as the authoritative data schema reference, covering every primary model, field-level constraints, serialization behaviors, and architectural roles.

---

## 1. Multi-Agent Orchestrator Schemas (`app/router/models.py`)

### 1.1 `OrchestratorResponse`
The master, unified response payload emitted by `CentralOrchestrator` to frontend clients and integration partners.

| Field Name | Type | Required | Meaning & Constraints | Example | Purpose & Usage |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `query` | `str` | Yes | Verbatim user query evaluated. | `"What is P/E ratio?"` | Echoes query for UI thread alignment. |
| `answer` | `str` | Yes | Generated educational response or structured refusal. | `"The Price-to-Earnings ratio..."` | Primary markdown answer rendered to user. |
| `grounding_status` | `Literal["fully_grounded", "partially_grounded", "ungrounded"]` | Yes | Verification status of RAG and tool citations. | `"fully_grounded"` | Renders green/amber/gray trust badge in UI. |
| `citations` | `list[Citation]` | Yes | Verified regulatory source citations. | `[{ "chunk_id": "...", ... }]` | Rendered in `CitationsAccordion.tsx`. |
| `market_data` | `MarketDataProvenance \| None` | No | Verified live market quote payload. | `{ "symbol": "RELIANCE.NS", ... }` | Renders `QuoteCard.tsx` ticker card. |
| `market_data_list` | `list[MarketDataProvenance]` | Yes (Default: `[]`) | Multi-entity quotes for comparative queries. | `[{ "symbol": "TCS.NS" }, ...]` | Renders comparative stock table. |
| `crypto_data` | `dict[str, Any] \| None` | No | Cryptocurrency price and provenance data. | `{ "symbol": "BTC", "price_usd": 68500 }` | Renders `CryptoCard.tsx`. |
| `derivatives_data` | `dict[str, Any] \| None` | No | Option payoff schedules, Greeks, breakevens. | `{ "strike_price": 2500, ... }` | Renders interactive options payoff charts. |
| `portfolio_data` | `dict[str, Any] \| None` | No | Simulated portfolio metrics & stress tests. | `{ "sharpe_ratio": 1.42, ... }` | Renders portfolio analytics cards. |
| `news_data` | `list[dict[str, Any]] \| None` | No | Curated regulatory circulars. | `[{ "headline": "SEBI amends..." }]` | Renders regulatory news feed. |
| `quiz_data` | `dict[str, Any] \| None` | No | Interactive quiz question and options. | `{ "question": "...", "options": [...] }`| Renders interactive `QuizCard.tsx`. |
| `onboarding_data` | `list[dict[str, Any]] \| None` | No | System capability tours and FAQ cards. | `[{ "feature": "Options Calculator" }]` | Renders onboarding walkthroughs. |
| `grounding_sources` | `list[str]` | Yes (Default: `[]`) | Source identifiers (`sebi_rag`, `live_market_data`). | `["sebi_rag"]` | Signals provenance types. |
| `domain_detected` | `Domain` | Yes | Classified domain (`EQUITY`, `CRYPTO`, etc.). | `"EQUITY"` | Domain badge styling. |
| `sub_tasks` | `list[SubTaskExecutionMetadata]` | Yes (Default: `[]`) | Telemetry for decomposed sub-queries. | `[{ "task_id": "t1", ... }]` | Internal diagnostic tracking. |
| `agent_name` | `str` | Yes | Name of domain agent handling turn. | `"Equity Agent"` | Displayed as message author. |
| `disclaimer` | `str` | Yes | Statutory educational disclaimer. | `"Disclaimer: Finova AI is..."` | Legal non-advisory compliance. |
| `model_used` | `str` | Yes | Identifier of inference engine. | `"qwen2.5:7b-instruct"` | System auditability. |
| `latency_ms` | `float` | Yes | Total end-to-end execution latency. | `1240.5` | Performance monitoring. |
| `topic` | `str \| None` | No | Resolved educational concept topic. | `"valuation_metrics"` | Topic continuity tracking. |
| `related_concepts`| `list[str]` | Yes (Default: `[]`) | Suggested adjacent financial concepts. | `["P/B ratio", "EPS"]` | Renders exploration chips. |
| `suggested_next` | `list[str]` | Yes (Default: `[]`) | Pedagogical follow-up questions. | `["How is EPS calculated?"]` | Renders quick-reply suggestion chips. |

---

## 2. Persistent Conversation Schemas (`app/conversations/models.py`)

### 2.1 `AssistantMessageMetadata`
Lightweight, versioned schema (`schema_version: 1`) persisted in the `metadata` JSON column of `data/conversations.db`. Explicitly excludes redundant text (`query`, `answer`, `disclaimer`) to eliminate database bloat.

```python
class AssistantMessageMetadata(BaseModel):
    schema_version: int = 1
    grounding_status: str | None = None
    citations: list[dict[str, Any]] = Field(default_factory=list)
    market_data: dict[str, Any] | None = None
    market_data_list: list[dict[str, Any]] = Field(default_factory=list)
    crypto_data: dict[str, Any] | None = None
    derivatives_data: dict[str, Any] | None = None
    portfolio_data: dict[str, Any] | None = None
    news_data: list[dict[str, Any]] | None = None
    quiz_data: dict[str, Any] | None = None
    onboarding_data: list[dict[str, Any]] | None = None
    grounding_sources: list[str] = Field(default_factory=list)
    domain_detected: str | None = None
    sub_tasks: list[dict[str, Any]] = Field(default_factory=list)
    agent_name: str | None = None
    model_used: str | None = None
    latency_ms: float | None = None
    topic: str | None = None
    related_concepts: list[str] = Field(default_factory=list)
    suggested_next: list[str] = Field(default_factory=list)
```

### 2.2 `Conversation` & `Message`
Relational entity schemas mirroring the SQLite database tables.

```python
class Conversation(BaseModel):
    conversation_id: str = Field(description="UUID4 primary key")
    user_id: str = Field(description="Owner user partition key")
    title: str = Field(description="Human-readable conversation title")
    domain: str = Field(default="general", description="Immutable domain binding")
    created_at: str = Field(description="ISO 8601 UTC creation timestamp")
    updated_at: str = Field(description="ISO 8601 UTC last modified timestamp")

class Message(BaseModel):
    message_id: str = Field(description="UUID4 primary key")
    conversation_id: str = Field(description="Foreign key to conversations")
    role: Literal["user", "assistant"] = Field(description="Turn speaker")
    content: str = Field(description="Plaintext / Markdown message body")
    status: Literal["complete", "failed"] = Field(default="complete")
    metadata: dict[str, Any] = Field(default_factory=dict, description="JSON metadata")
    created_at: str = Field(description="ISO 8601 UTC creation timestamp")
```

---

## 3. User Memory & Personalization Schemas (`app/memory/models.py`)

### 3.1 `MemoryRecord`
Atomic unit of validated user profile state stored in `data/memory.db`.

```python
class MemoryRecord(BaseModel):
    memory_id: str = Field(description="UUID4 unique memory identifier")
    user_id: str = Field(description="Application-level user identifier")
    memory_type: MemoryType = Field(description="Category (USER_PREFERENCE, LEARNING_LEVEL, etc.)")
    key: str = Field(description="Attribute key, e.g. 'investment_experience'")
    value: Any = Field(description="Validated scalar or JSON value")
    source: Literal["explicit_user_statement", "system_default"] = Field(
        default="explicit_user_statement",
        description="Origin provenance; strictly non-speculative",
    )
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    created_at: str = Field(description="ISO 8601 UTC creation timestamp")
    updated_at: str = Field(description="ISO 8601 UTC last update timestamp")
    expires_at: str | None = Field(default=None, description="Optional TTL expiration")
```

### 3.2 `PersonalizationProfile`
Dynamically assembled pedagogical persona injected into agent prompts.

```python
class PersonalizationProfile(BaseModel):
    user_id: str | None = None
    learning_level: Literal["beginner", "intermediate", "advanced"] | None = None
    learning_goals: list[str] = Field(default_factory=list)
    interests: list[str] = Field(default_factory=list)
    risk_tolerance: Literal["conservative", "moderate", "aggressive"] | None = None
    preferred_analogy_domain: str | None = None
    preferences: dict[str, str] = Field(default_factory=dict)
```

---

## 4. Market Data & Derivatives Tool Schemas

### 4.1 `MarketQuote` (`app/tools/market/models.py`)
Normalized, verified equity quote model.

| Field | Type | Required | Meaning | Validation Rules |
| :--- | :--- | :--- | :--- | :--- |
| `symbol` | `str` | Yes | Ticker symbol | Uppercase, stripped, `.NS` or `.BO` suffix |
| `company_name` | `str` | Yes | Clean registered company name | Stripped string |
| `exchange` | `str` | Yes | Exchange code | Canonical `"NSE"` or `"BSE"` |
| `currency` | `str` | Yes | Currency code | Standard `"INR"` |
| `price` | `float` | Yes | Current / Last Traded Price | Must be strictly positive ($> 0.0$), rounded to 2 decimals |
| `change` | `float` | Yes | Absolute price change from prev close | Rounded to 2 decimals |
| `change_percent`| `float` | Yes | Percentage change | Rounded to 2 decimals |
| `previous_close`| `float \| None` | No | Prior trading day close | Must be $> 0.0$ if present |
| `open` | `float \| None` | No | Day opening price | Must be $> 0.0$ if present |
| `high` | `float \| None` | No | Day high price | Must satisfy: $\text{high} \ge \text{low}$ |
| `low` | `float \| None` | No | Day low price | Must satisfy: $\text{low} \le \text{high}$ |
| `volume` | `int \| None` | No | Shares traded | Must be $\ge 0$ |
| `freshness_status`| `FreshnessStatusType`| Yes | Realtime, delayed, last close, stale | Evaluated via `MarketClock` against IST exchange hours |

### 4.2 `OptionPayoffResult` (`app/tools/derivatives/models.py`)
Deterministic output of options contract payoff schedules.

```python
class OptionPayoffResult(BaseModel):
    option_type: Literal["call", "put"]
    position: Literal["long", "short"]
    strike_price: float
    premium: float
    breakeven_price: float
    has_feasible_breakeven: bool = True
    max_profit: float | str  # Number or "Unlimited"
    max_loss: float | str    # Number or "Unlimited"
    payoff_table: list[OptionPayoffPoint] = Field(default_factory=list)
```

---

## 5. RAG & Citation Schemas (`app/rag/service.py`)

### 5.1 `Citation`
```python
class Citation(BaseModel):
    chunk_id: str = Field(description="Deterministic chunk identifier, e.g. 'sebi_eq_014'")
    doc_id: str = Field(description="Source document identifier")
    title: str = Field(description="Document title, e.g. 'SEBI Investor Education Booklet'")
    source: str = Field(description="Source repository provenance ('sebi_rag')")
    page_number: int | None = Field(default=None, description="Physical page in source PDF")
    authority_level: str = Field(default="statutory", description="Regulatory authority level")
```
