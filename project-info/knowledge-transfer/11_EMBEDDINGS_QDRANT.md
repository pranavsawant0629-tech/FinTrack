<!-- Generated against commit: 42228bb55d6016ffff439024bbf4aec135269f95 | Date: 2026-09-13 | Verified against live repository state: YES -->

# Finova AI — Master Project Bible: Complete Knowledge Transfer & Code Atlas
**Volume 11: Vector Embeddings & Embedded Qdrant Database Engineering**  
**Target Release**: Phase 13 Release Candidate (`d64eb5f1b932231a8b72c3d3f59bd5378e880118`)  
**Commit Baseline**: `42228bb55d6016ffff439024bbf4aec135269f95`  
**Classification**: High-Dimensional Vector Spaces & Embedded Search Engines

---

## 1. Vector Embeddings: Theory & Mechanics

### 1.1 What is an Embedding?
[FACT] A **vector embedding** is a dense numerical projection of text into a high-dimensional continuous vector space:
$$f: \text{Text} \to \mathbb{R}^d$$
In Finova AI, $d = 384$. Every sentence or chunk is transformed into an ordered list of 384 32-bit floating-point numbers. In this space, geometric distance correlates directly with semantic meaning.

### 1.2 Why 384 Dimensions?
- **768–1536 Dimensions (Large Models like Ada-002, BGE-Large)**: Offer slightly richer representations for nuanced literary text, but quadruple memory requirements, increase vector search latency, and require heavy PyTorch GPU dependencies.
- **384 Dimensions (Small Models like BGE-Small-EN-v1.5, MiniLM)**: The sweet spot for local-first systems. 384 dimensions capture domain-specific financial terminology with high precision while remaining lightweight enough to evaluate cosine similarity in microseconds on consumer laptop CPUs.

### 1.3 FastEmbed & ONNX Runtime
[FACT] Rather than loading the heavy `transformers` or `sentence-transformers` libraries (which pull in ~2 GB of PyTorch binaries and CUDA overhead), Finova AI utilizes **`fastembed`**:
- Executes quantized **ONNX Runtime** graphs.
- Generates embeddings locally on CPU using multi-threaded SIMD instructions.
- Memory footprint is ~150 MB (over 90% reduction compared to standard PyTorch embedding pipelines).

---

## 2. The Embedding Benchmark: BGE-Small vs E5-Small

[FACT] During Phase 1 development, a formal head-to-head benchmark was executed on representative Indian financial questions using `scripts/benchmark_embeddings.py`.

### Benchmark Results Comparison:

| Metric | `BAAI/bge-small-en-v1.5` | `intfloat/e5-small-v2` | Winner / Rationale |
| :--- | :---: | :---: | :--- |
| **Vector Dimension** | **384** | **384** | Tie |
| **Average Query Latency** | **~5.00 ms** | ~84.00 ms | **BGE-Small (16.8x Faster)** |
| **P95 Query Latency** | **~5.37 ms** | ~85.87 ms | **BGE-Small (16.0x Faster)** |
| **Topic Retrieval Accuracy** | **75.0%** | 75.0% | **Tie (Identical Accuracy)** |
| **Top-1 Cosine Similarity** | 0.7782 | **0.8802** | E5-Small (+0.1020) |
| **Deployment Decision** | **SELECTED & LOCKED** | REJECTED | **BGE-Small Selected** |

### Why BGE-Small Was Retained Despite E5's Higher Similarity
[FACT] Beginners often assume that higher raw cosine similarity numbers always mean a better model. That is a common misunderstanding in vector search:
1. **Calibrated Scale vs Relative Rank**: E5 compresses similarity distributions upward (most queries score above 0.85 regardless of subtle nuances). BGE has a wider dynamic range, scoring exact matches at ~0.82 and partial matches at ~0.68, making the 0.65 threshold much more discriminatory.
2. **Identical Topic Accuracy**: Both models correctly matched the target educational topic in **75.0%** of benchmark queries. E5 provided zero measurable improvement in retrieval correctness.
3. **The 16.8x Latency Penalty**: E5 averaged 84ms per query on local CPU, while BGE averaged **5.0ms**. Because retrieval sits directly in the user interaction path, adding 80ms of unneeded latency with zero gain in accuracy was rejected.

---

## 3. Embedded Qdrant Vector Database

---

### 3.1 Why Qdrant?
[FACT] Qdrant is an open-source vector similarity search engine written in Rust. Finova AI runs Qdrant using the official `qdrant-client` library in **embedded disk mode**:
```python
self.client = QdrantClient(path="./data/qdrant_storage")
```
- **Zero Daemon Overhead**: Does not require Docker, external services, or listening TCP ports.
- **Embedded Persistence**: Writes vectors and payloads directly to RocksDB-backed storage files on disk.
- **Fast Startup**: Connects in $<50\text{ms}$ at application launch.

---

### 3.2 Collection Configuration & Distance Metric

In [app/rag/vector_store.py:45-55](file:///c:/Users/prana/OneDrive/Desktop/finova-ai/app/rag/vector_store.py):
```python
self.client.create_collection(
    collection_name="finova_knowledge",
    vectors_config=VectorParams(
        size=384,
        distance=Distance.COSINE
    ),
)
```

#### Cosine Distance in Qdrant:
Qdrant computes normalized dot products between vectors. When vectors are $L_2$-normalized ($\|\mathbf{v}\| = 1.0$), cosine similarity equals the inner product:
$$\text{Score} = \sum_{i=1}^{384} q_i \cdot d_i$$
Scores range from $0.0$ to $1.0$ for non-negative vectors.

---

### 3.3 Points, Vectors & Payloads

Every piece of knowledge in Qdrant is stored as a `PointStruct` consisting of:
1. **Point ID**: Integer or UUID identifying the chunk.
2. **Vector**: Array of 384 floating point values.
3. **Payload**: JSON metadata attached to the point:
   - `doc_id`: Filename of the source PDF (e.g. `primarymarkets.pdf`).
   - `chunk_index`: Position in the document.
   - `text`: Raw text content (600 characters).
   - `source`: Official publisher (`SEBI`).
   - `authority_level`: Regulatory tier (`Tier 1`).
   - `page_numbers`: Exact page numbers in the physical booklet.
   - `url`: Official SEBI portal link.

---

## 4. Vector Search & Retrieval Mechanics

When a search is executed via `vector_store.search()`:
1. The search query vector is passed to Qdrant's HNSW (Hierarchical Navigable Small World) index.
2. The index traverses vector graphs to find the top $k$ nearest neighbors in $O(\log N)$ time.
3. Qdrant filters points using `score_threshold = 0.65`.
4. The engine returns matching `ScoredPoint` instances containing the score and full payload.
5. The application transforms points into typed `RetrievedChunk` objects for downstream prompts.
