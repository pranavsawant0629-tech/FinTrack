<!-- Generated against commit: 42228bb55d6016ffff439024bbf4aec135269f95 | Date: 2026-09-13 | Verified against live repository state: YES -->

# Part 31: Finova AI REST API Reference

This document provides a comprehensive reference for every HTTP REST endpoint exposed by Finova AI's FastAPI application (`app/main.py`). Every endpoint is documented with its HTTP method, URL path, request/response schemas, validation rules, error codes, ownership models, and persistence implications.

---

## 1. System Health & Infrastructure Endpoints

### 1.1 `GET /health`

- **METHOD**: `GET`
- **PATH**: `/health`
- **PURPOSE**: Infrastructure health probe and service heartbeat for process supervisors (`scripts/run_local.py`, container probes, monitoring agents).
- **REQUEST SCHEMA**: None (No request body or query parameters required).
- **VALIDATION**: None.
- **PROCESSING**: Reads `settings.app_env` and `settings.ollama_model` from `config/settings.py` and returns an immediate status payload.
- **RESPONSE SCHEMA**:
  ```json
  {
    "status": "ok",
    "env": "development",
    "ollama_model": "qwen2.5:7b-instruct"
  }
  ```
- **STATUS CODES**:
  - `200 OK`: System online and responding.
- **ERROR BEHAVIOR**: If the ASGI server cannot bind or event loop fails, connection is refused (`ECONNREFUSED`).
- **IDENTITY / OWNERSHIP MODEL**: Unauthenticated, public endpoint.
- **PERSISTENCE IMPACT**: None (Zero disk or database I/O).
- **AGENT / TOOL INTERACTION**: None.

---

### 1.2 `POST /test-llm`

- **METHOD**: `POST`
- **PATH**: `/test-llm`
- **PURPOSE**: Low-level diagnostic endpoint to verify direct connectivity and inference latency with the local Ollama LLM instance without activating RAG, safety, or agent routing.
- **REQUEST SCHEMA**:
  ```json
  {
    "message": "Hello, world!"
  }
  ```
- **VALIDATION**: Pydantic asserts `message` is a valid string.
- **PROCESSING**: Dispatches raw text string to `llm_client.chat(payload.message)`, which formats a single user message and calls Ollama's `/api/generate` endpoint.
- **RESPONSE SCHEMA**:
  ```json
  {
    "reply": "Hello! How can I assist you with your financial questions today?"
  }
  ```
- **STATUS CODES**:
  - `200 OK`: Inference succeeded.
  - `422 Unprocessable Entity`: Request body is malformed.
  - `500 Internal Server Error`: Ollama service is offline, unresponsive, or model is missing.
- **ERROR BEHAVIOR**: Catches connection errors to `127.0.0.1:11434` and raises HTTP 500.
- **IDENTITY / OWNERSHIP MODEL**: Ephemeral, unpartitioned diagnostic.
- **PERSISTENCE IMPACT**: None.
- **AGENT / TOOL INTERACTION**: Bypasses all agents and tools. Direct `OllamaClient` call.

---

### 1.3 `POST /rag/retrieve`

- **METHOD**: `POST`
- **PATH**: `/rag/retrieve`
- **PURPOSE**: Standalone semantic retrieval endpoint. Returns raw vector search results, similarity scores, and SEBI regulatory chunk metadata without invoking LLM generation.
- **REQUEST SCHEMA**:
  ```json
  {
    "query": "What are the disclosure rules for an IPO?",
    "top_k": 3,
    "score_threshold": 0.5,
    "topic": "equity",
    "authority_level": "statutory"
  }
  ```
- **VALIDATION**: `query` required (str). Optional `top_k` (int, default: 3), `score_threshold` (float, default: 0.5).
- **PROCESSING**:
  1. Invokes `rag_retriever.retrieve()`.
  2. Embeds `query` using FastEmbed ONNX runtime (`bge-small-en-v1.5`, 384 dimensions).
  3. Searches local file-backed Qdrant index (`data/qdrant_storage/`).
  4. Filters chunks by cosine similarity threshold.
- **RESPONSE SCHEMA** (`RetrievalResponse`):
  ```json
  {
    "query": "What are the disclosure rules for an IPO?",
    "chunks": [
      {
        "chunk_id": "sebi_eq_chunk_042",
        "doc_id": "sebi_icdr_regulations",
        "title": "SEBI Issue of Capital and Disclosure Requirements",
        "content": "An issuer making an initial public offer shall ensure that...",
        "similarity_score": 0.842,
        "page_number": 14,
        "authority_level": "statutory"
      }
    ],
    "total_retrieved": 1
  }
  ```
- **STATUS CODES**:
  - `200 OK`: Retrieval executed.
  - `422 Unprocessable Entity`: Invalid parameters.
- **ERROR BEHAVIOR**: Returns empty `chunks` list if similarity scores fall below threshold.
- **IDENTITY / OWNERSHIP MODEL**: Public read-only retrieval.
- **PERSISTENCE IMPACT**: None.
- **AGENT / TOOL INTERACTION**: FastEmbed + Qdrant Vector Store only.

---

## 2. Central Multi-Agent Orchestration Endpoints

### 2.1 `POST /orchestrator/ask` and `POST /chat`

- **METHOD**: `POST`
- **PATH**: `/orchestrator/ask` (alias: `/chat`)
- **PURPOSE**: Primary multi-agent conversational intelligence gateway. Executes global safety filtering, intent classification, multi-intent decomposition, specialized agent routing, RAG retrieval, citation verification, and response synthesis.
- **REQUEST SCHEMA** (`OrchestratorQueryRequest`):
  ```json
  {
    "query": "What is P/E ratio and what is Reliance trading at?",
    "user_id": "user_42",
    "conversation_history": [
      {"role": "user", "content": "I am interested in large cap stocks."}
    ],
    "top_k": 3,
    "score_threshold": 0.5
  }
  ```
- **VALIDATION**:
  - `query`: Required non-empty string.
  - `user_id`: Optional string identifying the user partition for memory recall.
  - `conversation_history`: Optional list of role/content dictionaries.
- **PROCESSING**:
  1. **Pre-Inference Safety Gate**: `SecondarySafetyValidator.validate()` intercepts investment advice, speculative tips, or prompt injections. If violated, halts immediately and returns refusal.
  2. **Fast-Path & Intent Routing**: `CentralRouter.route()` classifies query domain (`EQUITY`, `CRYPTO`, `DERIVATIVES`, etc.) and intent.
  3. **Compound Decomposition**: If query contains multiple intents, `DecompositionPlan` generates sub-tasks.
  4. **Agent Execution**: Dispatches to target domain agents (e.g. `EquityAgent`, `MarketDataService`).
  5. **Grounding & Citation Check**: `validate_citations()` verifies all citations against retrieved chunks.
- **RESPONSE SCHEMA** (`OrchestratorResponse`):
  ```json
  {
    "query": "What is P/E ratio and what is Reliance trading at?",
    "answer": "The Price-to-Earnings (P/E) ratio measures a company's current share price relative to its per-share earnings...",
    "grounding_status": "fully_grounded",
    "citations": [
      {
        "chunk_id": "sebi_eq_chunk_018",
        "doc_id": "sebi_investor_education",
        "title": "SEBI Equity Valuation Guide",
        "source": "sebi_rag"
      }
    ],
    "market_data": {
      "symbol": "RELIANCE.NS",
      "company_name": "Reliance Industries Limited",
      "price": 2985.40,
      "change": 18.20,
      "change_percent": 0.61,
      "currency": "INR",
      "exchange": "NSE",
      "freshness_status": "delayed"
    },
    "market_data_list": [],
    "crypto_data": null,
    "derivatives_data": null,
    "portfolio_data": null,
    "news_data": null,
    "quiz_data": null,
    "onboarding_data": null,
    "grounding_sources": ["sebi_rag", "live_market_data"],
    "domain_detected": "EQUITY",
    "sub_tasks": [],
    "agent_name": "Equity Agent",
    "disclaimer": "Disclaimer: Finova AI is an educational platform...",
    "model_used": "qwen2.5:7b-instruct",
    "latency_ms": 1420.5,
    "topic": "valuation_metrics",
    "related_concepts": ["P/B ratio", "Dividend Yield", "EPS"],
    "suggested_next": ["How is EPS calculated?", "What is a good P/E ratio for IT stocks?"]
  }
  ```
- **STATUS CODES**:
  - `200 OK`: Request processed successfully.
  - `422 Unprocessable Entity`: Validation failure on input schema.
  - `500 Internal Server Error`: Unhandled internal exception.
- **ERROR BEHAVIOR**: Returns graceful structured refusal on safety violation; returns fallback ungrounded response on LLM failure.
- **IDENTITY / OWNERSHIP MODEL**: Stateless turn execution. Reads memory if `user_id` is supplied.
- **PERSISTENCE IMPACT**: Reads user memory from `data/memory.db`. Does NOT persist turn messages directly (message persistence is handled by `/conversations/send`).
- **AGENT / TOOL INTERACTION**: Orchestrates all agents, RAG pipelines, market data tools, and Ollama LLM.

---

## 3. Persistent Conversation Management Endpoints

### 3.1 `POST /conversations`

- **METHOD**: `POST`
- **PATH**: `/conversations`
- **PURPOSE**: Creates a new persistent conversation thread.
- **REQUEST SCHEMA** (`CreateConversationRequest`):
  ```json
  {
    "user_id": "default_user",
    "title": "Options Trading Basics",
    "domain": "DERIVATIVES"
  }
  ```
- **VALIDATION**: `user_id` required. `domain` defaults to `"general"`.
- **PROCESSING**: Generates UUID4 `conversation_id`, sets created/updated UTC timestamps, and executes parameterized SQLite `INSERT` into `conversations` table in `data/conversations.db`.
- **RESPONSE SCHEMA** (`Conversation`):
  ```json
  {
    "conversation_id": "c7a8b9d0-1234-5678-9abc-def012345678",
    "user_id": "default_user",
    "title": "Options Trading Basics",
    "domain": "DERIVATIVES",
    "created_at": "2026-09-13T12:00:00Z",
    "updated_at": "2026-09-13T12:00:00Z"
  }
  ```
- **STATUS CODES**: `201 Created`.
- **PERSISTENCE IMPACT**: Inserts 1 row into `conversations` table.

---

### 3.2 `GET /conversations`

- **METHOD**: `GET`
- **PATH**: `/conversations?user_id={user_id}&domain={domain}`
- **PURPOSE**: Lists all conversations owned by a user, ordered by `updated_at` descending.
- **REQUEST SCHEMA**: Query parameters: `user_id` (str, required), `domain` (str, optional).
- **VALIDATION**: Rejects empty `user_id` with 400 Bad Request.
- **RESPONSE SCHEMA**: `list[ConversationSummary]`:
  ```json
  [
    {
      "conversation_id": "c7a8b9d0-1234-5678-9abc-def012345678",
      "user_id": "default_user",
      "title": "Options Trading Basics",
      "domain": "DERIVATIVES",
      "message_count": 4,
      "last_message_preview": "A call option gives the buyer the right...",
      "created_at": "2026-09-13T12:00:00Z",
      "updated_at": "2026-09-13T12:05:00Z"
    }
  ]
  ```
- **STATUS CODES**: `200 OK`, `400 Bad Request`.
- **IDENTITY / OWNERSHIP MODEL**: Strict user isolation. Only returns records where `user_id = :user_id`.

---

### 3.3 `GET /conversations/{conversation_id}`

- **METHOD**: `GET`
- **PATH**: `/conversations/{conversation_id}?user_id={user_id}`
- **PURPOSE**: Retrieves full conversation metadata and complete chronological message history.
- **VALIDATION**: Verifies conversation existence (404) and asserts `conversation.user_id == user_id` (403 Forbidden on IDOR violation).
- **RESPONSE SCHEMA** (`ConversationDetailResponse`):
  ```json
  {
    "conversation": { ... },
    "messages": [
      {
        "message_id": "m1-uuid",
        "conversation_id": "c7a8b9d0-...",
        "role": "user",
        "content": "What is a call option?",
        "status": "complete",
        "metadata": {},
        "created_at": "2026-09-13T12:01:00Z"
      },
      {
        "message_id": "m2-uuid",
        "conversation_id": "c7a8b9d0-...",
        "role": "assistant",
        "content": "A call option is a financial contract...",
        "status": "complete",
        "metadata": {
          "schema_version": 1,
          "grounding_status": "fully_grounded",
          "citations": [ ... ],
          "derivatives_data": { ... }
        },
        "created_at": "2026-09-13T12:01:03Z"
      }
    ]
  }
  ```
- **STATUS CODES**: `200 OK`, `403 Forbidden`, `404 Not Found`.

---

### 3.4 `POST /conversations/send`

- **METHOD**: `POST`
- **PATH**: `/conversations/send`
- **PURPOSE**: Master transactional turn execution endpoint. Auto-creates conversation if missing, persists user message, retrieves preceding bounded context (last 6 turns), executes multi-agent orchestrator, extracts and persists clean `schema_version: 1` assistant metadata, and updates conversation timestamps.
- **REQUEST SCHEMA** (`SendTurnRequest`):
  ```json
  {
    "user_id": "default_user",
    "conversation_id": "c7a8b9d0-...",
    "query": "How do interest rates affect call options?",
    "domain": "DERIVATIVES",
    "top_k": 3,
    "score_threshold": 0.5
  }
  ```
- **VALIDATION**: Asserts non-empty query. Verifies ownership if `conversation_id` is supplied.
- **PROCESSING**:
  1. If `conversation_id` is None, creates a new conversation with auto-generated title.
  2. Persists user turn message to SQLite (`status="complete"`).
  3. Fetches last 6 messages from SQLite for bounded context.
  4. Calls `CentralOrchestrator.ask()`.
  5. Extracts versioned metadata via `extract_assistant_metadata()`.
  6. Persists assistant message to SQLite (`status="complete"` or `"failed"` on error).
- **RESPONSE SCHEMA** (`SendTurnResponse`):
  ```json
  {
    "conversation_id": "c7a8b9d0-...",
    "user_message": { ... },
    "assistant_message": { ... },
    "orchestrator_response": { ... }
  }
  ```
- **STATUS CODES**: `200 OK`, `403 Forbidden`, `404 Not Found`.
- **PERSISTENCE IMPACT**: Atomically appends 2 rows to `messages` and updates `updated_at` on `conversations`.

---

### 3.5 `PATCH /conversations/{conversation_id}`

- **METHOD**: `PATCH`
- **PATH**: `/conversations/{conversation_id}`
- **PURPOSE**: Updates conversation title or metadata.
- **REQUEST SCHEMA** (`UpdateConversationRequest`):
  ```json
  {
    "user_id": "default_user",
    "title": "Renamed: Advanced Derivatives Strategies"
  }
  ```
- **STATUS CODES**: `200 OK`, `403 Forbidden`, `404 Not Found`.

---

### 3.6 `DELETE /conversations/{conversation_id}`

- **METHOD**: `DELETE`
- **PATH**: `/conversations/{conversation_id}?user_id={user_id}`
- **PURPOSE**: Deletes a specific conversation and cascades deletion to all contained messages.
- **STATUS CODES**: `200 OK`, `403 Forbidden`, `404 Not Found`.
- **PERSISTENCE IMPACT**: Executes `DELETE FROM messages WHERE conversation_id = ?` and `DELETE FROM conversations WHERE conversation_id = ?`.

---

### 3.7 `DELETE /conversations`

- **METHOD**: `DELETE`
- **PATH**: `/conversations?user_id={user_id}`
- **PURPOSE**: Clears all persistent conversations and messages belonging to a user (Right to be Forgotten).
- **RESPONSE SCHEMA**:
  ```json
  {
    "status": "cleared",
    "user_id": "default_user",
    "deleted_count": 14
  }
  ```
- **STATUS CODES**: `200 OK`, `400 Bad Request`.

---

## 4. User Memory & Personalization Endpoints

### 4.1 `GET /memory/profile`

- **METHOD**: `GET`
- **PATH**: `/memory/profile?user_id={user_id}`
- **PURPOSE**: Retrieves the active pedagogical learner profile assembled from unexpired SQLite memory facts.
- **RESPONSE SCHEMA** (`PersonalizationProfile`):
  ```json
  {
    "user_id": "default_user",
    "learning_level": "beginner",
    "learning_goals": ["equity_valuation", "mutual_funds"],
    "interests": ["large_cap", "index_funds"],
    "risk_tolerance": "moderate",
    "preferred_analogy_domain": "consumer",
    "preferences": {}
  }
  ```
- **STATUS CODES**: `200 OK`, `400 Bad Request`.

---

### 4.2 `POST /memory/profile`

- **METHOD**: `POST`
- **PATH**: `/memory/profile`
- **PURPOSE**: Explicitly updates a user's pedagogical preferences with PII validation.
- **REQUEST SCHEMA** (`UpdateProfileRequest`):
  ```json
  {
    "user_id": "default_user",
    "learning_level": "intermediate",
    "learning_goals": ["options_hedging"],
    "interests": ["derivatives"]
  }
  ```
- **VALIDATION**: Rejects Indian PII (Aadhaar, PAN, phone, email) with 422 Unprocessable Entity.
- **PERSISTENCE IMPACT**: Executes SQLite ACID upsert on `user_memory` table in `data/memory.db`.

---

### 4.3 `DELETE /memory`

- **METHOD**: `DELETE`
- **PATH**: `/memory?user_id={user_id}`
- **PURPOSE**: Statutory Right to be Forgotten. Permanently deletes all memory records and personalization facts for the user.
- **RESPONSE SCHEMA**:
  ```json
  {
    "status": "cleared",
    "user_id": "default_user",
    "deleted_count": 6
  }
  ```
- **STATUS CODES**: `200 OK`.

---

## 5. Specialized Domain Agent Endpoints

Each domain tutor exposes a direct query endpoint conforming to standardized request/response contracts:

| Endpoint Path | Domain Specialist | Core Subsystems Involved |
| :--- | :--- | :--- |
| `POST /agents/equity/ask` | Equity Tutor | SEBI Equity RAG, Market Data Service, Citation Validator |
| `POST /agents/crypto/ask` | Crypto Tutor | CoinGecko Provider, TTL Cache, Risk Disclosure Banner |
| `POST /agents/personal-finance/ask` | Personal Finance Tutor | Deterministic Calculators (SIP, Compounding, Budget) |
| `POST /agents/derivatives/ask` | Derivatives Tutor | SEBI F&O RAG, Options Payoff Tool, Compulsory Risk Warning |
| `POST /agents/portfolio/ask` | Portfolio Tutor | Deterministic Metrics (Sharpe, Diversification, Stress Testing) |
| `POST /agents/news/ask` | News Tutor | Curated Regulatory Circulars, SEBI Press Releases |
| `POST /agents/quiz/ask` | Quiz Agent | Interactive MCQ Generation, Grading Engine, Score Tracker |
| `POST /agents/onboarding/ask` | Onboarding Agent | Guided Walkthroughs, Capability Introspection |
