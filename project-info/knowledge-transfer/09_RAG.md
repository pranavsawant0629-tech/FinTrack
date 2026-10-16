<!-- Generated against commit: 42228bb55d6016ffff439024bbf4aec135269f95 | Date: 2026-09-13 | Verified against live repository state: YES -->

# Finova AI — Master Project Bible: Complete Knowledge Transfer & Code Atlas
**Volume 09: Retrieval-Augmented Generation (RAG) & Citation Provenance**  
**Target Release**: Phase 13 Release Candidate (`d64eb5f1b932231a8b72c3d3f59bd5378e880118`)  
**Commit Baseline**: `42228bb55d6016ffff439024bbf4aec135269f95`  
**Classification**: Information Retrieval Systems & Grounding Pipeline

---

## 1. RAG from First Principles

### 1.1 The Failure of Raw LLM Generation in Financial Regulation
[FACT] Large language models (LLMs) operate by computing statistical probabilities of next-token sequences:
$$P(w_t \mid w_1, \dots, w_{t-1})$$
In financial regulation, this architecture causes severe operational failures:
1. **Regulatory Hallucination**: An LLM asked about grievance redressal might invent a procedure or cite a non-existent clause (e.g. *"SEBI Circular 2023/45/A"*).
2. **Knowledge Cutoffs**: Real-world exchange rules, holiday schedules, and market regulations change over time. Retraining a 7B parameter model on every regulatory update is computationally prohibitive and risks catastrophic forgetting.
3. **Lack of Verifiable Provenance**: A raw LLM cannot provide the user with a specific booklet name, page number, or official download link for its claims.

### 1.2 The RAG Solution
**Retrieval-Augmented Generation (RAG)** fundamentally separates **knowledge storage** from **language reasoning**:
- **Parametric Knowledge (The LLM)**: Acts purely as an articulate pedagogical tutor, structuring sentences, explaining jargon simply, and synthesizing clear explanations.
- **Non-Parametric Knowledge (The Vector Database)**: Serves as the external source of truth, storing exact paragraphs extracted from verified, authoritative documents.

### 1.3 How Semantic Vector Space Works
1. **High-Dimensional Geometry**: Text sentences are transformed into dense vectors (lists of 384 floating-point numbers) using a neural embedding model.
2. **Semantic Proximity**: Sentences with similar conceptual meanings point in nearly the same direction in vector space, even if they share zero overlapping words.
   - Example: *"How do I open a Demat account?"* and *"Requirements for trading on an exchange"* have high cosine similarity despite different vocabularies.
3. **Cosine Similarity Metric**:
   $$\text{Cosine Similarity}(\mathbf{u}, \mathbf{v}) = \frac{\mathbf{u} \cdot \mathbf{v}}{\|\mathbf{u}\|_2 \|\mathbf{v}\|_2} = \sum_{i=1}^{d} u_i v_i \quad (\text{for normalized vectors})$$
   Values range from $-1.0$ (opposite) to $+1.0$ (identical direction).

---

## 2. Finova AI's End-to-End RAG Pipeline

[FACT] Finova AI implements a 12-stage retrieval and grounding pipeline:

```text
1. SOURCE DOCUMENT SELECTION
   Official SEBI/NISM investor education PDFs identified in data/manifest.json.
   │
   ▼
2. AUTOMATED ACQUISITION (scripts/ingest_docs.py)
   Downloads raw PDFs into data/raw/ with HTTP timeout and local file caching.
   │
   ▼
3. PDF TEXT EXTRACTION (app/rag/document_parser.py)
   pypdf extracts text page-by-page, attaching doc_id and page numbers.
   Corruption safeguard monitors unprintable character ratios.
   │
   ▼
4. TEXT CHUNKING (app/rag/chunking.py)
   Segments documents into 600-character chunks with 100-character overlap.
   Splits on sentence and paragraph boundaries to preserve complete thoughts.
   │
   ▼
5. DENSE EMBEDDING GENERATION (app/rag/embeddings.py)
   FastEmbed ONNX runtime converts chunk texts into 384-d vectors via BGE-small.
   │
   ▼
6. VECTOR INDEXING (app/rag/vector_store.py)
   Qdrant embedded database stores vectors and payload metadata in data/qdrant_storage/.
   │
   ▼
7. QUERY EMBEDDING (app/rag/retriever.py)
   User question is embedded into a 384-d vector via the same BGE-small model.
   │
   ▼
8. COSINE SIMILARITY SEARCH (app/rag/retriever.py)
   Qdrant evaluates HNSW vector distance; filters chunks by threshold (>= 0.65).
   │
   ▼
9. OUT-OF-CORPUS DECISION GATE (app/rag/service.py)
   If 0 chunks meet threshold: Returns UNGROUNDED_TOPIC_MESSAGE immediately.
   LLM is COMPLETELY BYPASSSED.
   │
   ▼
10. PROMPT ASSEMBLY & INFERENCE (app/rag/service.py)
    If chunks >= 1: Wraps context in strict delimiter blocks and sends to Ollama Qwen 2.5.
    │
    ▼
11. CITATION VALIDATION (app/rag/service.py)
    CitationValidator scans model reply. Strips any fabricated citation markers.
    Determines grounding_status (fully_grounded, partially_grounded, ungrounded).
    │
    ▼
12. FINAL RESPONSE RENDERING
    Emits answer with clickable CitationCards and colored GroundingBadge.
```

---

## 3. Subsystem Invariants & Implementation Details

---

### 3.1 Document Chunking Strategy (`app/rag/chunking.py`)

[FACT] Chunks in Finova AI are parameterized by two settings in `config/settings.py`:
- `chunk_size: int = 600` characters.
- `chunk_overlap: int = 100` characters.

#### Why 600 Characters?
- *Too Small (<200 chars)*: Chunks become isolated sentence fragments lacking sufficient context to explain financial mechanisms (e.g. splitting the definition of an IPO from its bidding rules).
- *Too Large (>1500 chars)*: Chunks contain multiple unrelated financial topics. The resulting embedding represents a blurry average of several concepts, degrading retrieval precision.
- *600 Characters (~90–120 words)*: Represents the ideal semantic density for financial definitions, regulatory clauses, and investor warnings.

#### Why 100 Character Overlap?
If a key legal rule or mathematical definition spans the boundary between Chunk $A$ and Chunk $B$, a zero-overlap chunker cuts the sentence in half. The 100-character overlap ensures that the boundary sentence appears completely in both chunks, preventing information loss.

---

### 3.2 The Qdrant Vector Store (`app/rag/vector_store.py`)

[FACT] Finova AI runs Qdrant in **embedded disk mode**:
```python
self.client = QdrantClient(path=self.path)  # path = "./data/qdrant_storage"
```
- **Storage Location**: `data/qdrant_storage/`.
- **Collection Name**: `finova_knowledge`.
- **Distance Metric**: `Distance.COSINE`.
- **Indexed Vector Size**: 384 dimensions.
- **Payload Schema**:
  ```json
  {
    "doc_id": "primarymarkets.pdf",
    "chunk_index": 14,
    "text": "The basis of allotment in an IPO is finalized by the issuer in consultation with the stock exchange...",
    "source": "SEBI",
    "authority_level": "Tier 1",
    "page_numbers": [12, 13],
    "url": "https://investor.sebi.gov.in",
    "publication_update_date": "2024-01-15"
  }
  ```

---

### 3.3 The Similarity Threshold (0.65) & Out-of-Corpus Handling

[FACT] The retrieval threshold in `app/rag/retriever.py` is configured to `0.65`:
```python
score_threshold = settings.rag_similarity_threshold  # 0.65
```

#### What Happens on Matching Queries?
If a query like *"What is an IPO?"* matches chunks with scores of `0.84`, `0.78`, and `0.71`, all three chunks are admitted into the prompt context.

#### What Happens on Out-of-Corpus Queries?
If a query asks about an unindexed subject (e.g. *"How do I file taxes in Germany?"* or *"Who won the cricket match?"*), top chunk scores typically range from `0.20` to `0.58`.
- Qdrant's search filter drops all chunks below `0.65`.
- The returned chunk array is **empty** (`chunks = []`).
- `RAGService.generate_answer()` detects `len(chunks) == 0` and **short-circuits immediately**:
  ```python
  if not retrieval.chunks:
      return RAGResponse(
          answer=self.UNGROUNDED_TOPIC_MESSAGE,
          grounding_status="ungrounded",
          citations=[],
          retrieved_chunks=[],
      )
  ```
  **Ollama is never called.** This completely eliminates hallucinated answers on out-of-corpus topics.

---

### 3.4 Citation Validation & Grounding Status

[FACT] When the LLM generates an answer, it is instructed to append citation tags: `[Source: SEBI, Doc: primarymarkets.pdf, Pages: 12]`.

Because language models cannot be trusted to cite accurately, `CitationValidator` scans the generated text and compares markers against the candidate chunks retrieved in that specific turn:
1. **`fully_grounded`**: All claims in the answer are supported by retrieved chunks, and all citation markers correspond to actual chunks retrieved.
2. **`partially_grounded`**: The answer contains valid citations, but some portions rely on general financial definitions or some citations were stripped.
3. **`ungrounded`**: No valid citations could be verified, or retrieval scores were below threshold.

---

## 4. Failure Modes & Recovery Matrix

| Failure Mode | Root Cause | System Defense / Fallback |
| :--- | :--- | :--- |
| **PDF Extraction Garbled** | Font encoding corruption in raw PDF (e.g. SCORES brochure) | `DocumentParser` calculates unprintable character ratio; flags safeguard warning and alerts developer |
| **Qdrant Storage Lock** | Concurrent processes trying to open embedded storage | SQLite-like single-process locking; tests use isolated `:memory:` collections |
| **LLM Hallucinates Citation** | Model invents a non-existent SEBI circular or page number | `CitationValidator` detects missing chunk ID, strips marker, and demotes status to `ungrounded` |
| **Query Outside Regulatory Scope** | User asks about real estate, US tax code, or astrology | Max similarity score falls below `0.65`; LLM is bypassed, returning standardized out-of-corpus notice |
