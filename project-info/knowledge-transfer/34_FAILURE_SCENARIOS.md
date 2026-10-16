<!-- Generated against commit: 42228bb55d6016ffff439024bbf4aec135269f95 | Date: 2026-09-13 | Verified against live repository state: YES -->

# Part 34: Failure Scenarios & Runtime Resilience Matrix

This document provides an exhaustive, honest analysis of the actual failure modes, error detection mechanisms, and recovery pathways in Finova AI. In accordance with Phase 14A instructions, no hypothetical resilience is claimed; only mechanisms verified in the codebase and test suites are documented.

Every scenario follows the canonical failure breakdown:
`TRIGGER → DETECTION → ACTUAL SYSTEM BEHAVIOR → USER-FACING RESULT → PERSISTENCE EFFECT → RECOVERY / FALLBACK → LIMITATION`.

---

## 1. Local LLM Service Offline (Ollama Process Stopped)

- **TRIGGER**: The Ollama background daemon is terminated, crashes, or was never started on `http://127.0.0.1:11434`.
- **DETECTION**: `httpx.ConnectError` or `urllib.error.URLError` raised inside `OllamaClient.generate()` when attempting to establish a TCP socket to port 11434.
- **ACTUAL SYSTEM BEHAVIOR**:
  - Catch block in `app/agents/equity/agent.py` and `app/router/orchestrator.py` traps connection exception.
  - **Deterministic Tools Bypass LLM**: If the query is a market quote request ("What is Reliance trading at?") or a calculation ("Calculate SIP"), the tool executes successfully without touching Ollama.
  - On conceptual RAG queries, the system catches the failure and returns a structured fallback response with `model_used="fallback"` and `grounding_status="ungrounded"`.
- **USER-FACING RESULT**:
  - Deterministic queries display quote/calculator cards normally.
  - Conceptual queries display a clear notice:
    `"Local LLM service (Ollama) is currently unreachable on port 11434. Please start it using 'ollama serve' in your terminal."`
- **PERSISTENCE EFFECT**: The turn is recorded in `data/conversations.db` with `status="failed"` or fallback text, preventing chat desync.
- **RECOVERY / FALLBACK**: User starts the daemon (`ollama serve`). Subsequent queries automatically succeed without restarting FastAPI.
- **LIMITATION**: Generative explanations cannot function without a running local inference service.

---

## 2. Foundation Model Missing (`qwen2.5:7b-instruct` Not Pulled)

- **TRIGGER**: Ollama is online, but the user has not executed `ollama pull qwen2.5:7b-instruct`.
- **DETECTION**: Ollama returns HTTP 404 Not Found with JSON payload `{"error": "model 'qwen2.5:7b-instruct' not found, try pulling it first"}`.
- **ACTUAL SYSTEM BEHAVIOR**: `OllamaClient.generate()` inspects HTTP status, logs an error, and raises an internal `ModelUnavailableError`.
- **USER-FACING RESULT**: Chat stream renders an error card:
  `"Model 'qwen2.5:7b-instruct' is not installed in local Ollama. Run: 'ollama pull qwen2.5:7b-instruct' to enable generative answers."`
- **PERSISTENCE EFFECT**: Message stored with `FailedMessageMetadata(schema_version=1, failed=True, error="Model not found")`.
- **RECOVERY / FALLBACK**: Run `ollama pull qwen2.5:7b-instruct` in PowerShell.
- **LIMITATION**: System does not automatically pull multi-gigabyte models at runtime to avoid unannounced background disk downloads.

---

## 3. Local Vector Database Unavailable (Qdrant Storage Lock / Corruption)

- **TRIGGER**: `data/qdrant_storage/` directory is corrupted, permissions are read-only, or another Python process holds an exclusive lock on the SQLite/RocksDB metadata files.
- **DETECTION**: `qdrant_client.exceptions.UnexpectedResponse` or OS file lock exception during `QdrantClient(path="data/qdrant_storage")` instantiation.
- **ACTUAL SYSTEM BEHAVIOR**: Vector store initialization fails. Retrieval queries return an empty chunk list `[]` and log an error.
- **USER-FACING RESULT**: The LLM synthesizes an ungrounded answer with an amber warning badge: `"Regulatory knowledge base unavailable. Answer generated without verified citations."`
- **PERSISTENCE EFFECT**: Persisted with `grounding_status="ungrounded"` and `citations=[]`.
- **RECOVERY / FALLBACK**: Release locking process or re-execute `scripts/ingest_docs.py` to rebuild index.
- **LIMITATION**: Citations cannot be grounded if vector store storage is inaccessible.

---

## 4. Market Data Provider Outage (Yahoo Finance Rate Limiting)

- **TRIGGER**: Yahoo Finance public endpoints return HTTP 429 Too Many Requests, block scrapers, or internet connection drops.
- **DETECTION**: `ProviderError` raised in `YahooFinanceAdapter.get_quote()`.
- **ACTUAL SYSTEM BEHAVIOR**:
  1. `MarketDataService` catches `ProviderError`.
  2. Attempts secondary failover to `TwelveDataAdapter` if API key is configured.
  3. If secondary fails or unconfigured, inspects `MarketDataCache` for expired cached quotes.
  4. If a cached quote exists, returns it with `freshness_status="stale_cached_fallback"`.
  5. If no cached quote exists, raises `DataValidationError`.
- **USER-FACING RESULT**:
  - If cached: Renders `QuoteCard` with a visible warning: `"⚠️ Stale Market Data (Cached fallback due to network outage)"`.
  - If no cache: Renders an error card: `"Market data temporarily unavailable. Please retry shortly."`
- **PERSISTENCE EFFECT**: Persisted with `market_data` payload indicating stale status, or omitted entirely.
- **RECOVERY / FALLBACK**: In-memory TTL cache serves historical quotes; automatic recovery when upstream recovers.
- **LIMITATION**: Real-time prices cannot be generated synthetically without internet connectivity.

---

## 5. Cryptocurrency Provider Failure (CoinGecko Rate Limit)

- **TRIGGER**: CoinGecko public API rate limits (HTTP 429) or network times out (>5.0s).
- **DETECTION**: `httpx.HTTPStatusError` caught in `CoinGeckoProvider.get_quote()`.
- **ACTUAL SYSTEM BEHAVIOR**:
  - In production (`allow_offline_fallback=False`), raises `CryptoProviderError`.
  - Hardcoded sandbox prices are strictly quarantined from production execution.
- **USER-FACING RESULT**: UI displays error alert: `"Crypto market data temporarily unavailable due to public rate limits. Please wait 60 seconds."`
- **PERSISTENCE EFFECT**: Message recorded with failed crypto status; zero fake numbers persisted.
- **RECOVERY / FALLBACK**: In-memory TTL cache (60s) reduces outbound request frequency to CoinGecko.
- **LIMITATION**: Free CoinGecko public tier allows only 10–30 calls/minute.

---

## 6. Relational Database Concurrency Lock (SQLite Busy)

- **TRIGGER**: Multiple concurrent requests attempt simultaneous write transactions on `data/conversations.db` or `data/memory.db`.
- **DETECTION**: `sqlite3.OperationalError: database is locked`.
- **ACTUAL SYSTEM BEHAVIOR**:
  - Python's SQLite driver automatically retries writes up to the configured `busy_timeout` (5,000 ms).
  - If lock persists past 5.0 seconds, the transaction aborts and raises `HTTPException(500)`.
- **USER-FACING RESULT**: Frontend displays toast notification: `"Database operation timed out. Please retry."`
- **PERSISTENCE EFFECT**: Uncommitted transaction rolls back cleanly via SQLite ACID guarantees. Zero database corruption.
- **RECOVERY / FALLBACK**: WAL (Write-Ahead Logging) mode allows simultaneous readers and one writer.
- **LIMITATION**: SQLite is single-writer. High-concurrency multi-user enterprise setups require PostgreSQL.

---

## 7. Adversarial Prompt Injection & System Override Attack

- **TRIGGER**: User submits malicious input containing jailbreaks, system prompt overrides, or delimiter collisions (`"SYSTEM OVERRIDE: Ignore all prior rules..."`).
- **DETECTION**: `SecondarySafetyValidator.validate()` in `app/safety/validator.py` matches injection signatures, roleplay framing, or delimiter escapes.
- **ACTUAL SYSTEM BEHAVIOR**:
  - **Pre-LLM Interception**: Execution stops immediately (<1ms).
  - Router, Agent, RAG, and LLM are **completely bypassed** (0 tokens consumed).
  - Returns canonical refusal: `INJECTION_REFUSAL_MESSAGE`.
- **USER-FACING RESULT**: Renders amber warning card explaining that system manipulation instructions were rejected.
- **PERSISTENCE EFFECT**: Saved in `conversations.db` with `metadata.safety_blocked=True` and `violation_type="PROMPT_INJECTION"`.
- **RECOVERY / FALLBACK**: Clean conversation continuation on next compliant turn.
- **LIMITATION**: Pure regex/structural defense can theoretically be bypassed by novel linguistic encodings.

---

## 8. Hallucinated or Invalid Citations

- **TRIGGER**: The LLM synthesizes an inline citation marker (`[SEBI-FAKE-99]`) that was never retrieved from Qdrant.
- **DETECTION**: `validate_citations()` in `app/rag/validator.py` compares cited chunk IDs against retrieved chunk IDs.
- **ACTUAL SYSTEM BEHAVIOR**:
  - Hallucinated marker is removed from verified `citations` array.
  - `grounding_status` is downgraded from `fully_grounded` to `partially_grounded` or `ungrounded`.
- **USER-FACING RESULT**: Markdown text is displayed, but the citation badge turns amber, and only verified sources are displayed in the expandable drawer.
- **PERSISTENCE EFFECT**: Persisted with accurately downgraded `grounding_status`.
- **RECOVERY / FALLBACK**: System transparently purges unverified citations from metadata.
- **LIMITATION**: LLM text may still contain ungrounded prose if the model disregarded negative constraints.

---

## 9. Zero RAG Retrieval Chunks Pass Similarity Threshold

- **TRIGGER**: User asks a query with no relevant documents in the SEBI knowledge base (similarity < 0.5).
- **DETECTION**: `rag_retriever.retrieve()` filters out all chunks below `score_threshold`, yielding an empty list `[]`.
- **ACTUAL SYSTEM BEHAVIOR**:
  - Agent prompt is assembled with zero context chunks.
  - Injects negative constraint: `"No regulatory context was found. State clearly that no authoritative SEBI guidelines were retrieved for this specific query. Do not speculate."`
- **USER-FACING RESULT**: Assistant states it lacks official regulatory documentation on that topic, offering to explain general principles instead.
- **PERSISTENCE EFFECT**: Stored with `grounding_status="ungrounded"` and `citations=[]`.
- **RECOVERY / FALLBACK**: User can rephrase query or lower similarity threshold in request payload.
- **LIMITATION**: Cannot answer niche un-indexed regulatory questions authoritatively.

---

## 10. Unauthorized Conversation Access (IDOR Vulnerability Attempt)

- **TRIGGER**: Client attempts to read or mutate another user's conversation (`GET /conversations/{id}?user_id=attacker`).
- **DETECTION**: `ConversationService.verify_ownership()` in `app/conversations/service.py` evaluates `conv.user_id != user_id`.
- **ACTUAL SYSTEM BEHAVIOR**:
  - Emits security warning log.
  - Aborts request immediately with `HTTPException(status_code=403, detail="Forbidden: conversation does not belong to user")`.
- **USER-FACING RESULT**: Frontend displays unauthorized access error; messages are never disclosed.
- **PERSISTENCE EFFECT**: Zero state mutation.
- **RECOVERY / FALLBACK**: Access granted only when correct `user_id` is supplied.
- **LIMITATION**: Assumes `user_id` cannot be spoofed without network-level authentication in local trial mode.

---

## 11. Frontend-Backend Network Disconnect

- **TRIGGER**: Backend process crashes, port 8000 drops, or user closes terminal while frontend UI remains open in browser.
- **DETECTION**: React `fetch()` call in `frontend/src/api.ts` rejects with `TypeError: Failed to fetch`.
- **ACTUAL SYSTEM BEHAVIOR**: `useChat` hook catches network error, sets UI error state, and preserves user draft in text input.
- **USER-FACING RESULT**: Top banner alert: `"⚠️ Disconnected from Finova Backend (http://127.0.0.1:8000). Reconnecting..."` with manual retry button.
- **PERSISTENCE EFFECT**: Unsent user turn is retained in browser memory; no partial state written to server.
- **RECOVERY / FALLBACK**: Once backend process is restarted, clicking retry resumes turn execution seamlessly.
- **LIMITATION**: Requires user to run `scripts/run_local.py` or `uvicorn`.

---

## 12. Failed Conversational Turn Execution

- **TRIGGER**: Unhandled exception during agent turn (e.g. system out-of-memory or thread interruption).
- **DETECTION**: Outer `try...except` block in `ConversationService.send_turn()`.
- **ACTUAL SYSTEM BEHAVIOR**:
  - Catches general exception.
  - Persists user turn message (`status="complete"`).
  - Persists assistant turn message with `status="failed"` and `FailedMessageMetadata(schema_version=1, failed=True, error=str(e))`.
- **USER-FACING RESULT**: Chat stream renders red error message card: `"An unexpected error occurred while processing this message. Your question has been saved."`
- **PERSISTENCE EFFECT**: Preserves conversation ordering; eliminates orphaned user turns or broken conversation state.
- **RECOVERY / FALLBACK**: User can submit a follow-up query without corrupting conversation history.
- **LIMITATION**: The specific failed turn must be re-queried by the user.
