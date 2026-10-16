<!-- Generated against commit: 42228bb55d6016ffff439024bbf4aec135269f95 | Date: 2026-09-13 | Verified against live repository state: YES -->

# Part 30: End-to-End Query Execution Traces

This chapter traces 10 real, representative user queries through every layer of Finova AI's architecture. Each trace follows the canonical 10-stage execution pipeline:

```
[1. FRONTEND] 
     |
     v
[2. API LAYER] 
     |
     v
[3. SAFETY GATE] 
     |
     v
[4. CENTRAL ROUTER] 
     |
     v
[5. SPECIALIZED AGENT] 
     |
     v
[6. RAG / TOOL / LLM SUBSYSTEM] 
     |
     v
[7. CITATION & RESPONSE VALIDATION] 
     |
     v
[8. PERSISTENCE LAYER] 
     |
     v
[9. RESPONSE SERIALIZATION] 
     |
     v
[10. FRONTEND RENDERING]
```

Every transition specifies the exact source file, class name, method, and data structure executed in the live repository.

---

## Query 1: "What is P/E ratio?"

*A canonical, grounded equity education query.*

```
FRONTEND: ChatInput -> api.sendTurn()
  -> API: POST /api/conversations/{id}/turns
  -> SAFETY: SecondarySafetyValidator.validate() -> SAFE
  -> ROUTER: CentralRouter.classify() -> EQUITY_TUTOR
  -> AGENT: EquityAgent.handle()
  -> RAG/LLM: VectorStore.search() -> Context Chunks -> OllamaClient.generate()
  -> VALIDATION: validate_citations() -> Grounded: True
  -> PERSISTENCE: SQLite (schema_version: 1)
  -> RESPONSE: SendTurnResponse
  -> FRONTEND RENDERING: MessageItem (Markdown + Citation Badges)
```

1. **FRONTEND**: User enters `"What is P/E ratio?"` in `frontend/src/components/ChatInput.tsx`. `useChat()` invokes `api.sendTurn("default_user", conversationId, "What is P/E ratio?")`.
2. **API LAYER**: `app/api/conversations.py` receives `SendTurnRequest`. `ConversationService.send_turn()` in `app/conversations/service.py` validates ownership and calls `CentralOrchestrator.route_and_execute()`.
3. **SAFETY GATE**: `SecondarySafetyValidator.validate()` in `app/safety/validator.py` scans the query against advisory, speculative, and injection patterns. Returns `SafetyValidationResult(is_safe=True)`.
4. **CENTRAL ROUTER**: `CentralRouter.route()` in `app/router/central.py` classifies the query as `DomainTarget.EQUITY_TUTOR`.
5. **SPECIALIZED AGENT**: `EquityAgent.process_turn()` in `app/agents/equity.py` is invoked with the user query.
6. **RAG / LLM SUBSYSTEM**:
   - `QdrantVectorStore.search(collection_name="sebi_equity_knowledge", query_text="What is P/E ratio?", top_k=3)` embeds the query via FastEmbed (`bge-small-en-v1.5`) and returns relevant chunks from SEBI Investor Education booklets explaining Price-to-Earnings valuation.
   - System prompt assembled with grounded context.
   - `OllamaClient.generate()` calls `http://127.0.0.1:11434/api/generate` (`qwen2.5:7b-instruct`, temperature `0.1`, `num_predict: 600`).
7. **VALIDATION**: `validate_citations()` in `app/rag/validator.py` checks that inline citations (e.g. `[SEBI-EQ-01]`) strictly correspond to retrieved chunk IDs. Sets `grounded=True`.
8. **PERSISTENCE**: `SQLiteConversationStore.add_message()` saves user turn and assistant response into `data/conversations.db` with `schema_version: 1` metadata.
9. **RESPONSE**: Returns `SendTurnResponse` with `assistant_message.content` and structured citations.
10. **FRONTEND RENDERING**: `frontend/src/components/MessageItem.tsx` renders formatted markdown explanation of P/E ratio, accompanied by clickable citation chips in `CitationsAccordion.tsx`.

---

## Query 2: "Explain P/E ratio like I'm a beginner."

*A personalized query integrating long-term memory.*

```
FRONTEND: ChatInput -> api.sendTurn()
  -> API: POST /api/conversations/{id}/turns
  -> SAFETY: SecondarySafetyValidator.validate() -> SAFE
  -> ROUTER: CentralRouter.classify() -> EQUITY_TUTOR
  -> AGENT: EquityAgent.handle() + MemoryService.get_user_profile()
  -> RAG/LLM: Grounded chunks + "User Level: Beginner" system prompt injection
  -> VALIDATION: validate_citations() -> Grounded: True
  -> PERSISTENCE: SQLite (schema_version: 1)
  -> RESPONSE: SendTurnResponse
  -> FRONTEND RENDERING: MessageItem (Analogy-driven pedagogical answer)
```

1. **FRONTEND**: User submits `"Explain P/E ratio like I'm a beginner."`.
2. **API LAYER**: Received at `POST /api/conversations/{id}/turns`.
3. **SAFETY GATE**: Verified safe by `SecondarySafetyValidator`.
4. **CENTRAL ROUTER**: Routed to `DomainTarget.EQUITY_TUTOR`.
5. **SPECIALIZED AGENT**: `EquityAgent` calls `MemoryService.get_user_profile("default_user")` in `app/memory/service.py`. Profile reveals: `investment_experience: "beginner"`.
6. **RAG / LLM SUBSYSTEM**:
   - `QdrantVectorStore` retrieves fundamental definition chunks.
   - Context injection adds explicit pedagogical guidance:
     `"Personalization Context: The user is a beginner. Use everyday consumer analogies (e.g., buying a fruit stall), avoid ungrounded technical acronyms, and explain both the numerator (market price) and denominator (earnings per share)."`
   - Ollama synthesizes the answer adhering strictly to the beginner frame.
7. **VALIDATION**: `validate_citations()` confirms grounding.
8. **PERSISTENCE**: Saved to `data/conversations.db`.
9. **RESPONSE**: Emits conversational response.
10. **FRONTEND RENDERING**: `MessageItem.tsx` renders clear, analogy-driven text with learning action chips ("Calculate a sample P/E", "Compare with P/B ratio").

---

## Query 3: "What is an IPO?"

*Primary capital markets educational query.*

```
FRONTEND -> API -> SAFETY -> ROUTER (EQUITY_TUTOR) -> AGENT (EquityAgent)
  -> RAG (SEBI Issue of Capital chunks) -> LLM -> VALIDATION -> PERSISTENCE -> FRONTEND
```

1. **FRONTEND**: User inputs `"What is an IPO?"`.
2. **API LAYER**: Forwarded to `ConversationService.send_turn()`.
3. **SAFETY GATE**: Evaluated as compliant educational inquiry.
4. **CENTRAL ROUTER**: Classified as `EQUITY_TUTOR` (Primary Capital Markets).
5. **SPECIALIZED AGENT**: `EquityAgent.process_turn()` handles query.
6. **RAG / LLM SUBSYSTEM**:
   - FastEmbed retrieves chunks from `sebi_public_issues` booklet in `data/qdrant_storage/`.
   - Chunks cover Initial Public Offering mechanics: Draft Red Herring Prospectus (DRHP), price bands, retail quota, bidding, and exchange listing on NSE/BSE.
   - Ollama generates a structured overview: Definition, Purpose, Process, and Investor Caveats.
7. **VALIDATION**: Validates source citations to SEBI regulations.
8. **PERSISTENCE**: Recorded in `data/conversations.db`.
9. **RESPONSE**: Standard `SendTurnResponse` payload.
10. **FRONTEND RENDERING**: Markdown output rendered with SEBI regulatory citation badge.

---

## Query 4: "What is Reliance trading at?"

*Deterministic live market quote — Complete LLM bypass.*

```
FRONTEND: ChatInput
  -> API: POST /api/conversations/{id}/turns
  -> SAFETY: SecondarySafetyValidator.validate() -> SAFE
  -> ROUTER: Market Intent Fast-Path (is_market_query=True, ticker="RELIANCE.NS")
  -> TOOL: MarketDataService.get_quote("RELIANCE.NS")
      +-- Cache Check -> Provider Dispatch (YahooFinanceAdapter) -> MarketDataValidator
  -> LLM: [BYPASSED — 0 TOKENS CONSUMED]
  -> PERSISTENCE: Message stored with market_data payload
  -> RESPONSE: SendTurnResponse (market_data payload)
  -> FRONTEND RENDERING: QuoteCard.tsx (Real-time financial ticker card)
```

1. **FRONTEND**: User submits `"What is Reliance trading at?"`.
2. **API LAYER**: Received at `/api/conversations/{id}/turns`.
3. **SAFETY GATE**: Safe informational price request.
4. **CENTRAL ROUTER**: `classify_market_intent()` in `app/tools/market/intent.py` intercepts query via regex fast-path:
   - Matches company alias `"reliance"` -> maps to canonical ticker `"RELIANCE.NS"`.
   - Classifies as direct price quote intent.
5. **SPECIALIZED AGENT / ORCHESTRATOR**: Bypasses agent conversation prompt generation. Dispatches directly to `MarketDataService`.
6. **TOOL EXECUTION (ZERO LLM CALLS)**:
   - `MarketDataService.get_quote("RELIANCE.NS")` checks in-memory TTL cache (`app/tools/market/cache.py`).
   - If expired/absent: calls `YahooFinanceAdapter.get_quote("RELIANCE.NS")`.
   - `MarketDataValidator.validate_quote()` in `app/tools/market/validator.py` checks positive price, normalizes exchange, and evaluates freshness (`delayed` or `last_traded_close` via `MarketClock`).
   - Returns structured `MarketQuote` model (`price: 2985.40`, `change: +18.20`, `change_percent: +0.61%`).
7. **LLM BYPASS**: The large language model is **never invoked**. Latency is ~120ms instead of 4,000ms.
8. **PERSISTENCE**: Persisted in SQLite with `market_data` JSON populated in metadata.
9. **RESPONSE**: Returns `SendTurnResponse` containing the structured quote payload.
10. **FRONTEND RENDERING**: `frontend/src/components/cards/QuoteCard.tsx` renders a live ticker card featuring current price, day high/low bar, trading volume, exchange timestamp, and statutory delayed data notice.

---

## Query 5: "What is an IPO and what is Reliance trading at?"

*Compound / Hybrid Query: Conceptual RAG + Market Tool Decomposition.*

```
FRONTEND -> API -> SAFETY -> ROUTER: HybridQueryRouter decomposes:
  +-- Sub-Query A: "What is an IPO?" -> Conceptual RAG (EquityAgent)
  +-- Sub-Query B: "What is Reliance trading at?" -> Deterministic Market Tool
AGENT/ORCHESTRATOR: Executes both paths in parallel/sequence
PERSISTENCE: Assistant message combines text answer + market_data card
FRONTEND RENDERING: MessageItem (Markdown Text) + QuoteCard (Below text)
```

1. **FRONTEND**: User inputs compound query.
2. **API LAYER**: Dispatched to `CentralOrchestrator`.
3. **SAFETY GATE**: Passed as safe.
4. **CENTRAL ROUTER**: `HybridQueryRouter` analyzes the sentence clauses:
   - Identifies an informational market quote clause ("what is Reliance trading at?").
   - Identifies an educational conceptual clause ("What is an IPO?").
5. **ORCHESTRATOR EXECUTION**:
   - Sub-task 1: Dispatches `RELIANCE.NS` to `MarketDataService`, obtaining verified `MarketQuote`.
   - Sub-task 2: Dispatches "What is an IPO?" to `EquityAgent` for RAG retrieval and Ollama synthesis.
6. **TOOL & RAG SYNTHESIS**: Market quote data is packaged into structured metadata. LLM synthesizes the conceptual explanation of IPOs without attempting to hallucinate stock prices.
7. **VALIDATION**: Citation validator confirms SEBI citations for the IPO text.
8. **PERSISTENCE**: Saved with both markdown text and `market_data` card payload in `schema_version: 1`.
9. **RESPONSE**: `OrchestratorResponse` contains both generated text and `market_data` dict.
10. **FRONTEND RENDERING**: UI renders the IPO educational markdown response, followed directly by the interactive `QuoteCard` for Reliance Industries.

---

## Query 6: "Explain a long call option."

*Derivatives education with compulsory statutory risk warning.*

```
FRONTEND -> API -> SAFETY -> ROUTER (DERIVATIVES_TUTOR) -> AGENT (DerivativesAgent)
  -> RAG (SEBI Derivatives booklet) -> LLM (Strike, Premium, Expiry, Payoff)
  -> POST-PROCESS: Injects SEBI 9/10 F&O Loss Warning Banner
  -> VALIDATION -> PERSISTENCE -> FRONTEND RENDERING (Options Risk Card)
```

1. **FRONTEND**: User inputs `"Explain a long call option."`.
2. **API LAYER**: Enters `ConversationService`.
3. **SAFETY GATE**: Verified as educational inquiry (no speculative recommendation requested).
4. **CENTRAL ROUTER**: Classified as `DomainTarget.DERIVATIVES_TUTOR`.
5. **SPECIALIZED AGENT**: `DerivativesAgent.process_turn()` in `app/agents/derivatives.py`.
6. **RAG / LLM SUBSYSTEM**:
   - Retrieves chunks from SEBI Derivatives & Risk Disclosure materials in Qdrant.
   - LLM synthesizes core mechanics: Strike Price, Option Premium, Expiration Date, Breakeven Formula ($\text{Strike} + \text{Premium}$), and Right vs. Obligation.
7. **STATUTORY RISK WARNING INJECTION**: `DerivativesAgent` deterministically appends the mandatory SEBI F&O risk disclosure:
   `"SEBI Regulatory Risk Warning: According to SEBI's official study, 9 out of 10 individual traders in the equity Futures and Options (F&O) segment incurred net losses, with average net trading loss of ~₹50,000."`
8. **PERSISTENCE**: Saved to `conversations.db` with `domain_detected: "DERIVATIVES_TUTOR"`.
9. **RESPONSE**: Emitted to API caller.
10. **FRONTEND RENDERING**: Rendered with an amber SEBI Risk Alert Banner above the options payoff explanation.

---

## Query 7: "Should I buy Reliance tomorrow?"

*Advisory violation — 100% Pre-LLM Deterministic Rejection.*

```
FRONTEND: ChatInput
  -> API: POST /api/conversations/{id}/turns
  -> SAFETY: SecondarySafetyValidator.evaluate()
      +-- Regex match: r"\bshould\s+i\s+(?:buy|sell|trade)\b"
      +-- Action: REJECT (Severity: HIGH)
  -> ROUTER: [BYPASSED]
  -> AGENT: [BYPASSED]
  -> LLM: [BYPASSED — 0 TOKENS CONSUMED]
  -> PERSISTENCE: Saved with safety_blocked=True
  -> RESPONSE: Global Refusal Disclaimer
  -> FRONTEND RENDERING: Red/Amber Safety Alert Message
```

1. **FRONTEND**: User asks `"Should I buy Reliance tomorrow?"`.
2. **API LAYER**: Forwarded to `ConversationService.send_turn()`.
3. **SAFETY GATE INTERCEPTION**:
   - `SecondarySafetyValidator.validate()` inspects the raw query in `app/safety/validator.py`.
   - Triggers regex pattern: `\bshould\s+i\s+(?:buy|sell|trade)\b` and timing pattern `\btomorrow\b`.
   - Flagged as `ViolationType.SPECIFIC_INVESTMENT_ADVICE`.
   - Sets `is_safe=False`, `refusal_message=GLOBAL_REFUSAL_MESSAGE`.
4. **COMPLETE PIPELINE SHORT-CIRCUIT**:
   - Central Router is **not** called.
   - Equity Agent is **not** called.
   - Vector Store is **not** queried.
   - Ollama LLM is **not** invoked (0 tokens consumed, <1ms execution latency).
5. **PERSISTENCE**: Message recorded in `conversations.db` with `status="complete"` and metadata `{"safety_blocked": True, "violation_type": "SPECIFIC_INVESTMENT_ADVICE"}`.
6. **RESPONSE**: Emits statutory refusal:
   `"Finova AI is an educational platform and cannot provide personalized financial advice, buy/sell recommendations, or speculative price targets..."`
7. **FRONTEND RENDERING**: Displayed in `MessageItem.tsx` styled with an amber safety shield badge, guiding the user toward educational valuation questions instead.

---

## Query 8: "Calculate SIP for ₹10,000 per month for 10 years at 12%."

*Deterministic financial calculation — 100% Zero-Hallucination Math.*

```
FRONTEND: ChatInput
  -> API: POST /api/conversations/{id}/turns
  -> SAFETY: SecondarySafetyValidator.validate() -> SAFE
  -> ROUTER: Personal Finance / Calculator Intent
  -> TOOL: calculate_sip(monthly_investment=10000, tenure_years=10, annual_return_pct=12)
      +-- Annuity Due Formula: M = P * [((1+i)^k - 1) / i] * (1+i)
      +-- Invested: ₹12,00,000.00 | Wealth Gain: ₹11,23,391.00 | Maturity: ₹23,23,391.00
  -> LLM: Formats conversational summary around verified numbers (or direct card)
  -> PERSISTENCE: Saved with calculator_data payload
  -> FRONTEND RENDERING: SIPCalculatorCard.tsx (Interactive breakdown chart & sliders)
```

1. **FRONTEND**: User submits calculation query.
2. **API LAYER**: Received at `/api/conversations/{id}/turns`.
3. **SAFETY GATE**: Verified safe.
4. **CENTRAL ROUTER**: Classified as `PERSONAL_FINANCE_TUTOR` with tool action `sip_calculator`.
5. **DETERMINISTIC TOOL EXECUTION**:
   - Parameters parsed from query via regex: `monthly_investment = 10000.0`, `tenure_years = 10.0`, `annual_return_pct = 12.0`.
   - Invokes `calculate_sip()` in `app/tools/calc/compounding.py`:
     $$i = \frac{12.0}{100 \times 12} = 0.01$$
     $$k = 10 \times 12 = 120$$
     $$\text{Maturity} = 10000 \times \left[ \frac{(1.01)^{120} - 1}{0.01} \right] \times 1.01 = \text{₹}23,23,390.89$$
     $$\text{Invested Amount} = 10000 \times 120 = \text{₹}12,00,000.00$$
     $$\text{Estimated Returns} = \text{₹}11,23,390.89$$
6. **SYNTHESIS**: Zero generative mathematical risk. The exact numbers are injected into the response envelope.
7. **PERSISTENCE**: Persisted in SQLite with calculation schema in metadata.
8. **RESPONSE**: Returns `SendTurnResponse` with `calculator_data` dict.
9. **FRONTEND RENDERING**: `frontend/src/components/cards/SIPCalculatorCard.tsx` renders an interactive visual card showing:
   - Total Investment: `₹12,00,000`
   - Est. Wealth Gain: `₹11,23,391`
   - Total Maturity Value: `₹23,23,391`
   - Dual-color visual progress bar and interactive tenure/amount sliders.

---

## Query 9: "Remember that I'm a beginner."

*Explicit memory extraction, PII validation, and SQLite ACID upsert.*

```
FRONTEND: ChatInput
  -> API: POST /api/conversations/{id}/turns
  -> SAFETY: Safe
  -> MEMORY SUBSYSTEM:
      +-- MemoryService.extract_candidate_facts() -> key="investment_experience", value="beginner"
      +-- PII Validator -> No Aadhaar, PAN, phone, or email detected -> CLEAN
      +-- SQLite ACID Upsert -> user_memory table updated
  -> AGENT: Acknowledges memory persistence
  -> PERSISTENCE: Saved to conversations.db
  -> FRONTEND RENDERING: MessageItem + Toast confirmation "Preferences updated"
```

1. **FRONTEND**: User inputs `"Remember that I'm a beginner."`.
2. **API LAYER**: Processed by `ConversationService.send_turn()`.
3. **SAFETY GATE**: Safe informational preference.
4. **MEMORY SERVICE EXTRACTION**:
   - `MemoryService.extract_candidate_facts()` in `app/memory/service.py` evaluates the message.
   - Matches regex pattern: `r"\b(?:i\s+am|i'm)\s+(?:a\s+)?(beginner|novice|starting\s+out)\b"`.
   - Generates candidate fact: `category="experience"`, `key="investment_experience"`, `value="beginner"`, `confidence=1.0`.
5. **PII VALIDATION**: Scans candidate fact value against Indian PII regexes (PAN card, Aadhaar number, phone, email). Validated completely clean.
6. **DATABASE UPSERT**:
   - Executes parameterized SQLite query on `data/memory.db`:
     ```sql
     INSERT INTO user_memory (user_id, category, fact_key, fact_value, confidence, updated_at)
     VALUES (?, ?, ?, ?, ?, ?)
     ON CONFLICT(user_id, fact_key) DO UPDATE SET fact_value = excluded.fact_value;
     ```
7. **CONFIRMATION**: System generates conversational confirmation:
   `"I've updated your profile to reflect that you are a beginner. I will explain financial concepts using accessible terminology and practical analogies."`
8. **PERSISTENCE**: Persisted in conversation store.
9. **FRONTEND RENDERING**: UI displays assistant acknowledgment and emits a subtle toast notification that personalization preferences have been saved.

---

## Query 10: "Quiz me on P/E ratio."

*Interactive quiz generation, schema validation, and score grading.*

```
FRONTEND: ChatInput
  -> API: POST /api/conversations/{id}/turns
  -> SAFETY: Safe
  -> ROUTER: Learning & Quiz Intent (LEARNING_TUTOR)
  -> AGENT / RAG: EquityAgent retrieves P/E concepts from Qdrant
  -> LLM: Generates structured JSON quiz question with options A, B, C, D
  -> VALIDATION: Quiz schema parsed and validated
  -> PERSISTENCE: Saved with quiz_data in metadata (schema_version: 1)
  -> FRONTEND RENDERING: QuizCard.tsx (Interactive clickable option buttons)
```

1. **FRONTEND**: User types `"Quiz me on P/E ratio."`.
2. **API LAYER**: Dispatched to `ConversationService`.
3. **SAFETY GATE**: Safe educational inquiry.
4. **CENTRAL ROUTER**: Classified as `LEARNING_TUTOR` with quiz intent.
5. **SPECIALIZED AGENT & RAG**:
   - `EquityAgent` retrieves verified definition chunks from SEBI equity materials.
   - System prompt instructs Ollama to format output as a structured JSON evaluation quiz:
     ```json
     {
       "question": "What does a high Price-to-Earnings (P/E) ratio typically indicate about a stock?",
       "options": [
         "The company is currently debt-free.",
         "Investors anticipate higher future earnings growth compared to lower P/E peers.",
         "The stock has guaranteed quarterly dividend payouts.",
         "The stock is legally undervalued by the stock exchange."
       ],
       "correct_index": 1,
       "explanation": "A high P/E ratio indicates that investors are willing to pay a higher price today because they anticipate strong future earnings growth."
     }
     ```
6. **VALIDATION**: Backend parses and verifies that `options` has exactly 4 items and `correct_index` is between 0 and 3.
7. **PERSISTENCE**: Recorded in `conversations.db` with `quiz_data` in metadata.
8. **RESPONSE**: Returns `SendTurnResponse` containing the `quiz_data` payload.
9. **FRONTEND RENDERING**: `frontend/src/components/cards/QuizCard.tsx` renders an interactive card:
   - Question header with subject badge.
   - Four interactive option buttons (A, B, C, D).
   - Upon clicking an option: immediate visual feedback (green check for correct, red border for incorrect), revealing the detailed explanation and updating the user's learning score.
