<!-- Generated against commit: 42228bb55d6016ffff439024bbf4aec135269f95 | Date: 2026-09-13 | Verified against live repository state: YES -->

# Finova AI — Master Project Bible: Complete Knowledge Transfer & Code Atlas
**Volume 06: FastAPI Backend Architecture & Endpoint Reference**  
**Target Release**: Phase 13 Release Candidate (`d64eb5f1b932231a8b72c3d3f59bd5378e880118`)  
**Commit Baseline**: `42228bb55d6016ffff439024bbf4aec135269f95`  
**Classification**: Web API Engineering & HTTP Contract Specification

---

## 1. FastAPI Architecture from the Ground Up

### 1.1 What is FastAPI?
[FACT] **FastAPI** is a modern, high-performance web framework for building REST APIs with Python 3.10+. In Finova AI, FastAPI serves as the gateway layer that:
1. Validates incoming HTTP JSON payloads against typed Pydantic models.
2. Directs requests to the central multi-agent orchestrator or dedicated agent routers.
3. Automatically generates interactive OpenAPI/Swagger documentation at `http://127.0.0.1:8000/docs`.
4. Enforces Cross-Origin Resource Sharing (CORS) security rules for the React frontend.

### 1.2 Uvicorn: The ASGI Server
[FACT] FastAPI does not listen on network sockets directly; it is an ASGI (Asynchronous Server Gateway Interface) application. **Uvicorn** is the lightning-fast web server that executes FastAPI.
- In Finova AI, Uvicorn binds to `127.0.0.1:8000`.
- In development, Uvicorn runs with `--reload`, watching filesystem changes in `app/` and reloading automatically.

### 1.3 CORS Middleware Configuration
[FACT] Browsers enforce the Same-Origin Policy. When the React frontend on `http://localhost:5173` makes a fetch request to `http://127.0.0.1:8000`, the browser blocks it unless the backend explicitly emits CORS headers.

In [app/main.py:22-32](file:///c:/Users/prana/OneDrive/Desktop/finova-ai/app/main.py):
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```
*Why this matters*: Without this middleware, every frontend API call fails with a browser `CORS policy: No 'Access-Control-Allow-Origin' header is present` error.

---

## 2. Exhaustive API Endpoint Catalog

---

### Endpoint 1: Central Orchestration Gateway (`POST /chat`)

- **METHOD**: `POST`
- **PATH**: `/chat`
- **LOCATION**: [app/api/chat.py](file:///c:/Users/prana/OneDrive/Desktop/finova-ai/app/api/chat.py)
- **PURPOSE**: The primary conversational entrypoint for the user interface. Coordinates safety checks, multi-intent decomposition, specialized agent execution, and response composition.

#### Request Schema: `ChatRequest`
```json
{
  "message": "What is the live price of TCS and how does an emergency fund work?",
  "conversation_id": "c1a2b3c4-0000-0000-0000-000000000001",
  "user_id": "u9z8y7x6-0000-0000-0000-000000000001",
  "domain_context": "general"
}
```

#### Validation Invariants:
- `message`: Required non-empty string.
- `conversation_id`: Optional UUID string; if omitted, backend generates a new session.
- `user_id`: Optional persistent learner UUID string.
- `domain_context`: Optional subject section lock (`general`, `equity`, `derivatives`, etc.).

#### Processing Lifecycle:
1. Passes message to `SecondarySafetyValidator`. If unsafe, returns immediate 200 OK with refusal text and `citations=[]`.
2. Inspects `domain_context`. If locked to a subject section, bypasses classifier and dispatches directly.
3. If `general`, evaluates `IntentClassifier` and `QueryDecomposer`.
4. Executes subtasks across specialized domain agents.
5. Invokes `ResponseComposer` to aggregate text, quote objects, and payoffs.
6. Persists user prompt and assistant reply to `data/conversations.db`.
7. Triggers asynchronous memory extraction for `data/memory.db`.

#### Response Schema: `OrchestratorResponse` (Status 200 OK)
```json
{
  "conversation_id": "c1a2b3c4-0000-0000-0000-000000000001",
  "routing_intent": "COMPOUND",
  "primary_agent": "CentralOrchestrator",
  "response_text": "### Tata Consultancy Services (TCS)\nLive market price is ₹3,842.50...\n\n### Emergency Fund Planning\nAn emergency fund should cover 3 to 6 months of essential living expenses...",
  "grounding_status": "partially_grounded",
  "citations": [],
  "market_quotes": [
    {
      "symbol": "TCS.NS",
      "price": 3842.50,
      "change_percent_24h": 1.15,
      "market_status": "CLOSED",
      "is_stale": false
    }
  ],
  "payoff_table": null,
  "quiz": null,
  "subtasks": [
    {"task_id": "task_1", "domain": "EQUITY"},
    {"task_id": "task_2", "domain": "PERSONAL_FINANCE"}
  ]
}
```

#### Error Handling:
- Request validation error $\rightarrow$ `422 Unprocessable Entity`.
- Subsystem timeout or unhandled crash $\rightarrow$ Graceful fallback message with status 200 OK to prevent client disconnection.

#### Call Chain:
`Client -> POST /chat -> chat_router -> orchestrator.handle_query() -> safety_validator.validate() -> classifier.classify() -> decomposer.decompose() -> agent.ask() -> composer.compose() -> conversation_service.save_turn() -> Client`

---

### Endpoint 2: System Health Check (`GET /health`)

- **METHOD**: `GET`
- **PATH**: `/health`
- **LOCATION**: [app/main.py:47-53](file:///c:/Users/prana/OneDrive/Desktop/finova-ai/app/main.py)
- **PURPOSE**: Lightweight diagnostic endpoint used by local runners and monitoring scripts to verify backend uptime.
- **INPUT**: None.
- **VALIDATION**: None.
- **PROCESSING**: Inspects `settings.app_env` and `settings.ollama_model`.
- **OUTPUT**: `{"status": "ok", "env": "development", "ollama_model": "qwen2.5:7b-instruct"}`
- **STATUS CODE**: `200 OK`.
- **CALL CHAIN**: `Client -> GET /health -> health() -> Client`

---

### Endpoint 3: Direct Knowledge Retrieval (`POST /rag/retrieve`)

- **METHOD**: `POST`
- **PATH**: `/rag/retrieve`
- **LOCATION**: [app/main.py:74-86](file:///c:/Users/prana/OneDrive/Desktop/finova-ai/app/main.py)
- **PURPOSE**: Diagnostic and evaluation endpoint returning raw retrieved Qdrant knowledge chunks, scores, and page provenance **without invoking any LLM**.

#### Request Schema: `RetrieveRequest`
```json
{
  "query": "What are the rules for an IPO allotment?",
  "top_k": 4,
  "score_threshold": 0.65,
  "topic": null,
  "authority_level": null
}
```

#### Response Schema: `RetrievalResponse` (Status 200 OK)
```json
{
  "query": "What are the rules for an IPO allotment?",
  "total_results": 2,
  "chunks": [
    {
      "chunk_id": "pt_9182",
      "doc_id": "primarymarkets.pdf",
      "chunk_index": 14,
      "text": "The basis of allotment in an IPO is finalized by the issuer in consultation with the stock exchange...",
      "score": 0.8124,
      "source": "SEBI",
      "authority_level": "Tier 1",
      "page_numbers": [12, 13],
      "url": "https://investor.sebi.gov.in"
    }
  ]
}
```
- **CALL CHAIN**: `Client -> POST /rag/retrieve -> rag_retriever.retrieve() -> vector_store.search() -> Client`

---

### Endpoint 4: List User Conversations (`GET /conversations`)

- **METHOD**: `GET`
- **PATH**: `/conversations`
- **LOCATION**: [app/api/conversations.py](file:///c:/Users/prana/OneDrive/Desktop/finova-ai/app/api/conversations.py)
- **PURPOSE**: Returns all active conversation threads belonging to the authenticated learner, sorted by last updated timestamp.
- **QUERY PARAMS**: `user_id: str` (Required query parameter).
- **IDOR INVARIANT**: A user can only list threads matching their `user_id`. Empty or missing `user_id` returns an empty array.
- **OUTPUT**:
```json
[
  {
    "conversation_id": "c1a2b3c4-0000-0000-0000-000000000001",
    "user_id": "u9z8y7x6-0000-0000-0000-000000000001",
    "title": "TCS Price & Emergency Fund",
    "domain": "general",
    "created_at": "2026-09-13T08:00:00Z",
    "updated_at": "2026-09-13T08:02:15Z"
  }
]
```

---

### Endpoint 5: Fetch Single Thread History (`GET /conversations/{conversation_id}`)

- **METHOD**: `GET`
- **PATH**: `/conversations/{conversation_id}`
- **LOCATION**: [app/api/conversations.py](file:///c:/Users/prana/OneDrive/Desktop/finova-ai/app/api/conversations.py)
- **PURPOSE**: Loads full message history and metadata for a specific conversation session.
- **QUERY PARAMS**: `user_id: str` (Required for ownership verification).
- **IDOR DEFENSE**: Returns `404 Not Found` if the conversation does not exist or if `user_id` does not match the database record.
- **OUTPUT**:
```json
{
  "conversation_id": "c1a2b3c4-0000-0000-0000-000000000001",
  "title": "TCS Price & Emergency Fund",
  "domain": "general",
  "messages": [
    {
      "message_id": "m1",
      "role": "user",
      "content": "What is the live price of TCS?",
      "created_at": "2026-09-13T08:00:00Z"
    },
    {
      "message_id": "m2",
      "role": "assistant",
      "content": "Live price of TCS is ₹3,842.50.",
      "created_at": "2026-09-13T08:00:03Z",
      "metadata": {
        "schema_version": 1,
        "routing_intent": "EQUITY",
        "market_quotes": [{"symbol": "TCS.NS", "price": 3842.50}]
      }
    }
  ]
}
```

---

### Endpoint 6: Delete Conversation Thread (`DELETE /conversations/{conversation_id}`)

- **METHOD**: `DELETE`
- **PATH**: `/conversations/{conversation_id}`
- **PURPOSE**: Hard-deletes a conversation thread and its associated message rows from SQLite.
- **STATUS CODE**: `200 OK` with `{"status": "deleted"}`.

---

### Endpoint 7: Inspect User Memories (`GET /memory`)

- **METHOD**: `GET`
- **PATH**: `/memory`
- **LOCATION**: [app/api/memory.py](file:///c:/Users/prana/OneDrive/Desktop/finova-ai/app/api/memory.py)
- **PURPOSE**: Powers the Profile & Settings modal, allowing users to audit all persistent memories recorded about them.
- **QUERY PARAMS**: `user_id: str` (Required).
- **OUTPUT**:
```json
{
  "user_id": "u9z8y7x6-0000-0000-0000-000000000001",
  "learning_level": "beginner",
  "risk_profile": "conservative",
  "preferences": {"prefers_examples": "true"},
  "total_memories": 2
}
```

---

### Endpoint 8: Hard Purge User Memories (`DELETE /memory`)

- **METHOD**: `DELETE`
- **PATH**: `/memory`
- **LOCATION**: [app/api/memory.py](file:///c:/Users/prana/OneDrive/Desktop/finova-ai/app/api/memory.py)
- **PURPOSE**: Executes a complete privacy reset ("Clear Memory"), deleting all rows for the given `user_id` from `data/memory.db`.
- **STATUS CODE**: `200 OK` with `{"status": "cleared", "deleted_count": 2}`.

---

### Endpoints 9–16: Direct Domain Endpoints (`POST /agents/{domain}/ask`)

- **PATHS**:
  - `POST /agents/equity/ask`
  - `POST /agents/crypto/ask`
  - `POST /agents/personal-finance/ask`
  - `POST /agents/derivatives/ask`
  - `POST /agents/portfolio/ask`
  - `POST /agents/news/ask`
  - `POST /agents/quiz/ask`
  - `POST /agents/onboarding/ask`
- **PURPOSE**: Direct, un-orchestrated access to specific domain agents. Bypasses general classification and query decomposition, sending prompts straight to that domain's tools and prompts.
- **COMMON REQUEST BODY**:
```json
{
  "message": "Explain a Bull Call Spread",
  "conversation_id": "optional-uuid",
  "user_id": "optional-uuid"
}
```
- **STATUS CODE**: `200 OK`.
