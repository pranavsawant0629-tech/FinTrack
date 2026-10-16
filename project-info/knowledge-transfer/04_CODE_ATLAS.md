<!-- Generated against commit: 42228bb55d6016ffff439024bbf4aec135269f95 | Date: 2026-09-13 | Verified against live repository state: YES -->

# Finova AI — Master Project Bible: Complete Knowledge Transfer & Code Atlas
**Volume 04: Code-by-Code Deep Dive & Implementation Atlas**  
**Target Release**: Phase 13 Release Candidate (`d64eb5f1b932231a8b72c3d3f59bd5378e880118`)  
**Commit Baseline**: `42228bb55d6016ffff439024bbf4aec135269f95`  
**Classification**: Method-by-Method Code Architecture & Pedagogical Dissection

---

## 1. Architectural Code Map & Design Patterns

[FACT] The Finova AI backend is built on concrete software engineering design patterns that prevent coupling and guarantee deterministic behavior:

| Design Pattern | Where Implemented | Why It Was Chosen |
| :--- | :--- | :--- |
| **Singleton Engine** | `settings`, `llm_client`, `vector_store`, `embedding_manager` | Eliminates redundant object allocations, re-uses TCP/HTTP connection pools, and preserves thread-safe caches. |
| **Strategy / Provider Adapter** | `BaseMarketDataProvider` (`yfinance`, `twelve_data`), `BaseCryptoProvider` | Allows swapping external data vendors without altering domain agent logic. |
| **Frozen Value Object** | `SafetyValidationResult`, `RetrievedChunk`, `StockQuote` | Prevents mutable state leakage across async tasks. |
| **Pipeline / Filter** | `SecondarySafetyValidator` -> `IntentClassifier` -> `QueryDecomposer` -> `Agent` -> `ResponseComposer` | Enforces strict sequence: safety first, classification second, execution third, composition last. |
| **Dependency Injection** | `FastAPI` route dependencies, `SQLiteMemoryStore(db_path=":memory:")` | Enables isolated, zero-disk unit testing with in-memory SQLite fixtures. |

---

## 2. Central Orchestration & Safety Deep Dive

---

### File: `app/router/orchestrator.py`
**Class**: `CentralOrchestrator`  
**Location**: [app/router/orchestrator.py:34-195](file:///c:/Users/prana/OneDrive/Desktop/finova-ai/app/router/orchestrator.py)

#### Core Method: `handle_query()`

```python
def handle_query(
    self,
    query: str,
    conversation_id: str | None = None,
    user_id: str | None = None,
    domain_context: str | None = None,
) -> OrchestratorResponse:
```

#### Line-by-Line & Block Breakdown:

1. **Telemetry & Initialization (Lines 48–56)**:
   ```python
   start_time = time.time()
   request_id = str(uuid.uuid4())
   ```
   *Pedagogy*: Generates a unique tracking token for audit traces. Records sub-millisecond start time to calculate true execution latency.

2. **Stage 1: Pre-Routing Safety Validation (Lines 58–74)**:
   ```python
   safety_result = self.safety_validator.validate(query)
   if not safety_result.is_safe:
       return OrchestratorResponse(
           conversation_id=conversation_id or str(uuid.uuid4()),
           routing_intent="SAFETY_VIOLATION",
           primary_agent="SafetyGuardrail",
           response_text=safety_result.refusal_message or GLOBAL_REFUSAL_MESSAGE,
           grounding_status="ungrounded",
           citations=[],
       )
   ```
   *Pedagogy*: **Safety Invariant**: If regex pattern matching detects RIA impersonation, guaranteed return promises, or prompt injection, execution **halts immediately**. No LLM, no RAG, and no tools are invoked.

3. **Stage 2: Domain Context & Decomposition (Lines 76–112)**:
   ```python
   # Enforce tutor section domain immutability if provided
   forced_domain = normalize_domain(domain_context)
   if forced_domain and forced_domain != "general":
       routing_intent = forced_domain.upper()
       subtasks = [Subtask(task_id="task_1", domain=forced_domain, prompt=query)]
   else:
       routing_intent = self.classifier.classify(query)
       subtasks = self.decomposer.decompose(query, base_domain=routing_intent)
   ```
   *Pedagogy*:
   - If the user is chatting inside the "Derivatives Tutor" section, `domain_context="derivatives"` is passed from the client, locking the session to that agent.
   - If in "General Chat", `IntentClassifier` categorizes the query, and `QueryDecomposer` splits compound prompts into independent tasks.

4. **Stage 3: Subtask Dispatch & Execution (Lines 114–158)**:
   ```python
   subtask_results: list[SubtaskResult] = []
   for task in subtasks:
       agent = self._resolve_agent(task.domain)
       res = agent.ask(task.prompt, conversation_id=conversation_id, user_id=user_id)
       subtask_results.append(res)
   ```
   *Pedagogy*: Iterates through segmented tasks, dynamically mapping each domain to its specialized agent instance (`EquityAgent`, `DerivativesAgent`, etc.).

5. **Stage 4: Composition & Response Construction (Lines 160–185)**:
   ```python
   composed = self.composer.compose(subtask_results, query=query)
   # Persist messages and record telemetry...
   return composed
   ```

#### Input / Processing / Output Flow:
- **INPUT**: Raw prompt (`str`), optional session identifiers (`conversation_id`, `user_id`), optional subject section (`domain_context`).
- **PROCESSING**: Deterministic safety regex check $\rightarrow$ domain resolution $\rightarrow$ subtask partitioning $\rightarrow$ agent execution $\rightarrow$ unified markdown composition.
- **OUTPUT**: Structured `OrchestratorResponse` containing combined markdown text, structured financial cards (quotes, payoffs, quizzes), and citation provenance.

*Plain English*: The orchestrator acts as a strict air-traffic controller. It inspects incoming prompts for danger first. If safe, it checks whether the user is talking to a specific subject tutor. If not, it decides who should answer (or splits the question between multiple experts), collects their work, merges it cleanly, and hands it back to the user.

---

### File: `app/safety/validator.py`
**Class**: `SecondarySafetyValidator`  
**Location**: [app/safety/validator.py:41-168](file:///c:/Users/prana/OneDrive/Desktop/finova-ai/app/safety/validator.py)

#### Snippet: Regex Pattern Structure

```python
ROLEPLAY_ADVISORY_PATTERNS: ClassVar[list[re.Pattern[str]]] = [
    re.compile(
        r"\b(?:pretend|act\s+as|roleplay|simulate|imagine)\s+(?:you\s+are|being)?\s*(?:a|an)?\s*"
        r"(?:sebi\s+registered|investment\s+advis[oe]r|financial\s+plann?er|portfolio\s+manag(?:er|ement)|broker|trader|ria)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:buy|sell|dump|liquidate)\s+(?:all\s+)?my\s+[A-Za-z0-9&]+\b",
        re.IGNORECASE,
    ),
]
```

#### Line-by-Line Explanation:
- `ClassVar[list[re.Pattern[str]]]`: Python type hint denoting that this compiled regex list belongs to the class itself, compiled once at import time rather than re-compiled on every request.
- `\b`: Word boundary assertion, preventing false positive matches inside longer words.
- `(?:pretend|act\s+as|roleplay)`: Non-capturing group matching common jailbreak roleplay openings.
- `re.IGNORECASE`: Ensures case-insensitive evaluation (e.g., matching "RIA", "Ria", and "ria").

#### Input / Processing / Output Flow:
- **INPUT**: User prompt string.
- **PROCESSING**: Evaluates prompt against `ROLEPLAY_ADVISORY_PATTERNS`, `GUARANTEED_RETURN_PATTERNS`, and `PROMPT_INJECTION_PATTERNS`.
- **OUTPUT**: `SafetyValidationResult(is_safe=False, refusal_message=...)` if a pattern matches, else `SafetyValidationResult(is_safe=True)`.

*Plain English*: This class searches for dangerous phrasing using precise search formulas (regular expressions). It catches people trying to trick the AI into giving illegal personalized stock tips or pretending to be a licensed advisor, stopping the attack instantly without spending time or money calling the language model.

---

## 3. RAG Retrieval & Citation Integrity Deep Dive

---

### File: `app/rag/retriever.py`
**Class**: `RAGRetriever`  
**Location**: [app/rag/retriever.py:33-102](file:///c:/Users/prana/OneDrive/Desktop/finova-ai/app/rag/retriever.py)

#### Core Method: `retrieve()`

```python
def retrieve(
    self,
    query: str,
    top_k: int | None = None,
    score_threshold: float | None = None,
    topic: str | None = None,
    authority_level: str | None = None,
) -> RetrievalResponse:
    k = top_k or self.top_k
    thresh = score_threshold if score_threshold is not None else self.score_threshold

    # 1. Embed search query via FastEmbed
    query_vector = embedding_manager.embed_query(query)

    # 2. Execute cosine similarity search in embedded Qdrant
    search_results = vector_store.search(
        query_vector=query_vector,
        limit=k,
        score_threshold=thresh,
        topic=topic,
        authority_level=authority_level,
    )

    # 3. Transform Qdrant ScoredPoints to typed RetrievedChunks
    chunks = [
        RetrievedChunk(
            chunk_id=str(hit.id),
            doc_id=hit.payload.get("doc_id", ""),
            chunk_index=hit.payload.get("chunk_index", 0),
            text=hit.payload.get("text", ""),
            score=hit.score,
            source=hit.payload.get("source", "SEBI"),
            authority_level=hit.payload.get("authority_level", "Tier 1"),
            page_numbers=hit.payload.get("page_numbers", []),
            url=hit.payload.get("url", ""),
            publication_update_date=hit.payload.get("publication_update_date", ""),
        )
        for hit in search_results
    ]

    return RetrievalResponse(query=query, total_results=len(chunks), chunks=chunks)
```

#### Key Engineering Invariants:
1. **Zero LLM Invocation**: The retrieval pipeline is purely mathematical and algebraic. It produces ranked documents without calling Ollama.
2. **Payload Preservation**: Every metadata attribute stored during PDF ingestion (page numbers, document title, authority tier, SEBI URL) is reconstructed into the `RetrievedChunk` model.
3. **Threshold Gate (`thresh = 0.65`)**: Any document with a cosine similarity score below 0.65 is discarded by Qdrant's engine before reaching application memory.

#### Input / Processing / Output Flow:
- **INPUT**: Natural language query string, optional `top_k` (default 4), optional threshold (default 0.65).
- **PROCESSING**: Generates 384-d vector via ONNX FastEmbed $\rightarrow$ executes HNSW search in embedded Qdrant $\rightarrow$ filters results by threshold.
- **OUTPUT**: `RetrievalResponse` containing sorted list of `RetrievedChunk` instances.

*Plain English*: When you ask a question, this code converts your sentence into 384 numbers that represent its conceptual meaning. It searches the Qdrant database of official SEBI booklets to find the closest matching paragraphs. If the best match isn't close enough (score below 0.65), it drops it so the AI doesn't read irrelevant documents.

---

### File: `app/rag/service.py`
**Class**: `RAGService`  
**Location**: [app/rag/service.py:35-180](file:///c:/Users/prana/OneDrive/Desktop/finova-ai/app/rag/service.py)

#### Core Method: `generate_answer()`

```python
def generate_answer(
    self,
    query: str,
    top_k: int | None = None,
    conversation_history: list[dict[str, str]] | None = None,
) -> RAGResponse:
    # Step 1: Retrieve candidate knowledge chunks
    retrieval = self.retriever.retrieve(query=query, top_k=top_k)

    # Step 2: Strict Out-of-Corpus Handling
    if not retrieval.chunks:
        return RAGResponse(
            answer=self.UNGROUNDED_TOPIC_MESSAGE,
            grounding_status="ungrounded",
            citations=[],
            retrieved_chunks=[],
        )

    # Step 3: Context Assembly with Citation Delimiters
    context_blocks = []
    for c in retrieval.chunks:
        block = f"[Source: {c.source} | Doc: {c.doc_id} | Pages: {c.page_numbers}]\n{c.text}"
        context_blocks.append(block)
    assembled_context = "\n\n---\n\n".join(context_blocks)

    # Step 4: System Prompt Construction & Ollama Call
    prompt = self._build_prompt(query=query, context=assembled_context)
    raw_answer = self.llm.chat(
        message=query,
        system=prompt,
        conversation_history=conversation_history,
        max_tokens=600,
    )

    # Step 5: Citation Validation & Post-Processing
    validated_citations, status = self.citation_validator.verify_citations(
        raw_answer, retrieval.chunks
    )

    return RAGResponse(
        answer=raw_answer,
        grounding_status=status,
        citations=validated_citations,
        retrieved_chunks=retrieval.chunks,
    )
```

#### Key Engineering Invariants:
1. **Out-of-Corpus Short-Circuit**: If `retrieval.chunks` is empty (no chunks met the 0.65 threshold), the method returns `UNGROUNDED_TOPIC_MESSAGE` immediately. Ollama is **never called**, preventing the model from hallucinating unsourced information.
2. **Citation Verification**: Post-processing inspects the generated text. If the LLM cited a source that was not present in the retrieved chunks, `CitationValidator` strips the marker and demotes the status to `partially_grounded` or `ungrounded`.

*Plain English*: This service gets the matching SEBI paragraphs, formats them with clear source labels, and gives them to the language model with strict instructions to answer *only* using those paragraphs. If no matching paragraphs were found, it doesn't even talk to the AI—it immediately replies that it has no official information on that topic.

---

## 4. Deterministic Financial Mathematics Deep Dive

---

### File: `app/tools/calc/compounding.py`
**Location**: [app/tools/calc/compounding.py:15-85](file:///c:/Users/prana/OneDrive/Desktop/finova-ai/app/tools/calc/compounding.py)

#### Core Method: `calculate_sip()`

```python
def calculate_sip(
    monthly_investment: float,
    annual_rate_pct: float,
    tenure_years: int,
) -> SIPCalculationResult:
    if monthly_investment <= 0:
        raise ValueError("Monthly investment must be greater than zero.")
    if annual_rate_pct < 0:
        raise ValueError("Annual rate of return cannot be negative.")
    if tenure_years <= 0:
        raise ValueError("Tenure in years must be at least 1.")

    P = float(monthly_investment)
    r = (annual_rate_pct / 100.0) / 12.0  # Monthly interest rate
    n = tenure_years * 12                 # Total number of monthly installments

    total_invested = round(P * n, 2)

    # Edge Case: 0% Interest Rate
    if r == 0:
        future_value = total_invested
    else:
        # Annuity Due Formula: payments occur at beginning of monthly period
        future_value = round(P * (((1 + r) ** n - 1) / r) * (1 + r), 2)

    wealth_gained = round(future_value - total_invested, 2)

    return SIPCalculationResult(
        monthly_investment=P,
        annual_rate_pct=annual_rate_pct,
        tenure_years=tenure_years,
        total_invested=total_invested,
        wealth_gained=wealth_gained,
        future_value=future_value,
    )
```

#### Line-by-Line Mathematical Breakdown:
- `r = (annual_rate_pct / 100.0) / 12.0`: Converts nominal annual percentage into a monthly decimal fraction.
- `n = tenure_years * 12`: Converts annual horizon to discrete compounding periods.
- `P * (((1 + r) ** n - 1) / r) * (1 + r)`: The **Annuity Due** formula. The final `* (1 + r)` factor accounts for the fact that SIP installments are invested at the *start* of each month, earning compounding interest during that initial month.
- `wealth_gained = round(future_value - total_invested, 2)`: Computes purely the wealth generated by compound growth above the user's principal capital.

#### Input / Processing / Output Flow:
- **INPUT**: Monthly investment (e.g. ₹5,000), Expected rate (e.g. 12%), Years (e.g. 10).
- **PROCESSING**: Validates inputs $\rightarrow$ computes monthly compounding rate $\rightarrow$ applies Annuity Due formula $\rightarrow$ rounds to 2 decimal places.
- **OUTPUT**: `SIPCalculationResult(total_invested=600000.0, wealth_gained=561695.38, future_value=1161695.38)`.

*Plain English*: This function calculates how much a Monthly Mutual Fund SIP will grow over time. It uses standard compound interest mathematics where every monthly deposit earns interest starting on the day it is deposited. It runs in pure Python code so the result is always exact to the rupee.

---

### File: `app/tools/derivatives/payoff.py`
**Location**: [app/tools/derivatives/payoff.py:30-150](file:///c:/Users/prana/OneDrive/Desktop/finova-ai/app/tools/derivatives/payoff.py)

#### Core Method: `generate_option_payoff()`

```python
def generate_option_payoff(
    option_type: OptionType,  # CALL or PUT
    position_type: PositionType,  # LONG or SHORT
    strike_price: float,
    premium: float,
    range_pct: float = 0.15,
    num_points: int = 21,
) -> OptionPayoffResult:
    # 1. Determine Breakeven Price
    if option_type == OptionType.CALL:
        breakeven = round(strike_price + premium, 2)
        has_feasible_breakeven = True
    else:  # PUT
        # Long Put Breakeven = Strike - Premium
        breakeven = round(strike_price - premium, 2)
        has_feasible_breakeven = breakeven >= 0.0

    # 2. Generate Underlying Spot Price Grid (21 points)
    min_spot = strike_price * (1.0 - range_pct)
    max_spot = strike_price * (1.0 + range_pct)
    step = (max_spot - min_spot) / (num_points - 1)
    spot_prices = [round(min_spot + i * step, 2) for i in range(num_points)]

    # 3. Compute Terminal P&L Points
    payoff_points: list[PayoffPoint] = []
    for spot in spot_prices:
        if option_type == OptionType.CALL:
            intrinsic_value = max(0.0, spot - strike_price)
        else:
            intrinsic_value = max(0.0, strike_price - spot)

        if position_type == PositionType.LONG:
            pnl = round(intrinsic_value - premium, 2)
        else:
            pnl = round(premium - intrinsic_value, 2)

        payoff_points.append(PayoffPoint(spot_price=spot, pnl=pnl))

    return OptionPayoffResult(
        option_type=option_type.value,
        position_type=position_type.value,
        strike_price=strike_price,
        premium=premium,
        breakeven=breakeven,
        has_feasible_breakeven=has_feasible_breakeven,
        points=payoff_points,
    )
```

#### Line-by-Line Mathematical Breakdown:
- `OptionType.CALL: breakeven = strike_price + premium`: For a call option, the underlying asset must rise above strike by at least the premium paid to recover costs.
- `OptionType.PUT: breakeven = strike_price - premium`: For a put option, the underlying asset must fall below strike by the premium.
- `has_feasible_breakeven = breakeven >= 0.0`: [FACT - Phase 7 Fix] If an option has premium $P > K$ (e.g. Strike ₹10, Premium ₹15), the breakeven price is $-5$. Because a stock price cannot fall below ₹0, this position can never break even. Flagging `has_feasible_breakeven=False` prevents confusing the user.
- `intrinsic_value = max(0.0, spot - strike_price)`: Computes the terminal value of the option contract at expiration before accounting for premium.

*Plain English*: This calculates the profit or loss of an option contract across different stock prices at expiry. It calculates the breakeven price and generates a table of 21 sample stock prices and their corresponding profit or loss in rupees, which the frontend displays as an interactive chart.

---

## 5. Market Data Adapters & Cache Deep Dive

---

### File: `app/tools/market/cache.py`
**Class**: `MarketDataCache`  
**Location**: [app/tools/market/cache.py:25-95](file:///c:/Users/prana/OneDrive/Desktop/finova-ai/app/tools/market/cache.py)

#### Core Logic: Dynamic TTL Caching & Stale Fallback

```python
class MarketDataCache:
    def __init__(self):
        self._cache: dict[str, CachedQuote] = {}
        self._lock = threading.Lock()

    def get(self, symbol: str) -> StockQuote | None:
        key = symbol.strip().upper()
        now = time.time()
        with self._lock:
            entry = self._cache.get(key)
            if not entry:
                return None
            # Check if entry is within valid TTL window
            if now - entry.cached_at <= entry.ttl_seconds:
                return entry.quote
            # If expired, we do NOT delete immediately; preserved for stale fallback
            return None

    def get_stale_fallback(self, symbol: str) -> StockQuote | None:
        """Returns last known quote marked with is_stale=True during provider outages."""
        key = symbol.strip().upper()
        with self._lock:
            entry = self._cache.get(key)
            if entry:
                stale_copy = entry.quote.model_copy()
                stale_copy.is_stale = True
                return stale_copy
            return None
```

#### Key Engineering Invariants:
1. **Thread-Safe**: Uses `threading.Lock()` to prevent race conditions during concurrent API requests.
2. **Stale Data Preservation**: Expired quotes are retained in memory. If external upstream APIs (Yahoo Finance, Twelve Data) fail or time out, `get_stale_fallback()` returns the last known quote with `is_stale=True`, enabling graceful degradation.

*Plain English*: This is an in-memory storage box for stock quotes. If someone asks for TCS twice in 10 seconds, it hands back the saved quote without making another slow call to the internet. If the internet fails, it can still pull out the older quote with a visual warning that the data is stale.

---

## 6. Persistence & SQLite Memory Deep Dive

---

### File: `app/memory/store.py`
**Class**: `SQLiteMemoryStore`  
**Location**: [app/memory/store.py:25-140](file:///c:/Users/prana/OneDrive/Desktop/finova-ai/app/memory/store.py)

#### Schema Initialization & Upsert Query:

```python
def _init_schema(self) -> None:
    with self._lock:
        cur = self._conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS user_memories (
                memory_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                memory_type TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                source TEXT NOT NULL,
                confidence REAL NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(user_id, key)
            )
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_memories_user ON user_memories(user_id)")
```

#### Key Database Invariants:
1. **`UNIQUE(user_id, key)`**: Enforces that a specific user can have only one active record per memory key (e.g. `learning_level`). Storing a new value updates the existing row rather than creating duplicates.
2. **`CREATE INDEX idx_memories_user`**: Optimizes retrieval speed when fetching all memories belonging to a single user.
3. **`isolation_level=None`**: Runs in autocommit mode, ensuring ACID transactions complete immediately without dangling uncommitted locks.

*Plain English*: This initializes a table in SQLite to remember learner preferences (like whether you are a beginner or advanced). It makes sure your preferences never get mixed up with another user's preferences, and it creates a database index so looking up your profile takes less than one millisecond.
