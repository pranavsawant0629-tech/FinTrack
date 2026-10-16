import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct

from app.rag.embeddings import EmbeddingManager
from app.rag.document_parser import DocumentParser
from app.rag.chunking import TextChunker

# 8 representative evaluation questions covering core Indian financial education
EVAL_DATASET = [
    {
        "id": "q1_demat_trading",
        "query": "What are the requirements and steps for buying and selling shares on a stock exchange?",
        "expected_topic": "Trading Mechanism",
    },
    {
        "id": "q2_ipo_primary",
        "query": "What is an Initial Public Offering (IPO) and how does the primary market operate?",
        "expected_topic": "Primary Market",
    },
    {
        "id": "q3_corporate_actions",
        "query": "What are corporate actions such as dividends, bonus shares, and stock splits?",
        "expected_topic": "Corporate Actions",
    },
    {
        "id": "q4_etf_basics",
        "query": "What is an Exchange Traded Fund (ETF) and how does it track an index?",
        "expected_topic": "Exchange Traded Funds",
    },
    {
        "id": "q5_mutual_funds",
        "query": "How do open-ended mutual funds work and how is Net Asset Value (NAV) calculated?",
        "expected_topic": "Mutual Funds",
    },
    {
        "id": "q6_corporate_bonds",
        "query": "What are corporate bonds, debentures, credit ratings, and coupon rates?",
        "expected_topic": "Fixed Income",
    },
    {
        "id": "q7_derivatives",
        "query": "How do futures and options contracts work and what are the risks in derivatives trading?",
        "expected_topic": "Derivatives",
    },
    {
        "id": "q8_scores_grievance",
        "query": "How can an investor lodge a complaint and track grievance redressal through SCORES?",
        "expected_topic": "Investor Protection",
    },
]


def run_benchmark():
    print("=" * 80)
    print("FINOVA AI — EMBEDDING MODEL BENCHMARK EVALUATION")
    print("=" * 80)

    models_to_test = [
        ("BAAI/bge-small-en-v1.5", "BGE-Small-EN-v1.5"),
        ("sentence-transformers/all-MiniLM-L6-v2", "All-MiniLM-L6-v2"),
    ]

    # Parse representative documents for indexing in an in-memory benchmark store
    raw_dir = BASE_DIR / "data" / "raw"
    manifest_file = BASE_DIR / "data" / "manifest.json"
    manifest_map = {}
    if manifest_file.exists():
        import json
        with open(manifest_file, "r", encoding="utf-8") as mf:
            manifest_map = {item["filename"]: item for item in json.load(mf)}

    sample_files = list(raw_dir.glob("*.pdf"))
    if not sample_files:
        raise FileNotFoundError(f"No documents found in {raw_dir} for benchmarking.")

    parser = DocumentParser()
    chunker = TextChunker(chunk_size=500, chunk_overlap=80)

    print(f"\nPreparing benchmark document corpus from {len(sample_files)} documents...")
    parsed_docs = [
        parser.parse_file(f, extra_metadata=manifest_map.get(f.name, {"topic": f.stem}))
        for f in sample_files
    ]
    all_chunks = []
    for d in parsed_docs:
        all_chunks.extend(chunker.chunk_document(d))

    print(f"Total benchmark chunks prepared: {len(all_chunks)}")
    chunk_texts = [c.text for c in all_chunks]

    benchmark_results = {}

    for model_id, display_name in models_to_test:
        print(f"\n" + "-" * 50)
        print(f"Evaluating: {display_name} ({model_id})")
        print("-" * 50)

        t0 = time.time()
        embedder = EmbeddingManager(model_name=model_id)
        load_time = time.time() - t0
        print(f"  Model loaded in {load_time:.2f}s | Vector Dimension: {embedder.dimension}")

        # Benchmark Batch Ingestion Speed
        t_embed_start = time.time()
        embeddings = embedder.embed_documents(chunk_texts, batch_size=32)
        embed_time = time.time() - t_embed_start
        embed_throughput = len(chunk_texts) / embed_time if embed_time > 0 else 0
        print(f"  Embedded {len(chunk_texts)} chunks in {embed_time:.2f}s ({embed_throughput:.1f} chunks/sec)")

        # Index into isolated in-memory Qdrant instance
        mem_client = QdrantClient(":memory:")
        coll_name = "bench_coll"
        mem_client.create_collection(
            collection_name=coll_name,
            vectors_config=VectorParams(size=embedder.dimension, distance=Distance.COSINE),
        )

        points = [
            PointStruct(
                id=i,
                vector=emb,
                payload={
                    "text": c.text,
                    "doc_id": c.doc_id,
                    "topic": c.metadata.get("topic", c.doc_id),
                },
            )
            for i, (c, emb) in enumerate(zip(all_chunks, embeddings))
        ]
        mem_client.upsert(collection_name=coll_name, points=points)

        # Benchmark Query Latency and Retrieval Relevance
        latencies = []
        top1_scores = []
        topic_matches = 0

        for item in EVAL_DATASET:
            t_q0 = time.time()
            q_vec = embedder.embed_query(item["query"])
            q_latency = (time.time() - t_q0) * 1000
            latencies.append(q_latency)

            search_res = mem_client.query_points(
                collection_name=coll_name,
                query=q_vec,
                limit=3,
                with_payload=True,
            )

            if search_res.points:
                top_hit = search_res.points[0]
                score = top_hit.score
                top1_scores.append(score)
                hit_topic = (top_hit.payload or {}).get("topic", "").lower()
                hit_doc = (top_hit.payload or {}).get("doc_id", "").lower()
                exp = item["expected_topic"].lower()

                if exp in hit_topic or exp in hit_doc:
                    topic_matches += 1

        accuracy = (topic_matches / len(EVAL_DATASET)) * 100
        avg_latency = float(np.mean(latencies))
        p95_latency = float(np.percentile(latencies, 95))
        avg_score = float(np.mean(top1_scores)) if top1_scores else 0.0

        benchmark_results[display_name] = {
            "model_id": model_id,
            "dimension": embedder.dimension,
            "embed_throughput": round(embed_throughput, 1),
            "avg_latency_ms": round(avg_latency, 2),
            "p95_latency_ms": round(p95_latency, 2),
            "avg_top1_score": round(avg_score, 4),
            "top1_topic_accuracy": round(accuracy, 1),
        }

    # Print Final Summary Table
    print("\n" + "=" * 95)
    print("FINAL BENCHMARK COMPARISON")
    print("=" * 95)
    header = f"{'Metric':<28}"
    for name in benchmark_results.keys():
        header += f" | {name:<20}"
    print(header)
    print("-" * 95)

    metrics = [
        ("Vector Dimension", "dimension"),
        ("Throughput (chunks/sec)", "embed_throughput"),
        ("Avg Query Latency (ms)", "avg_latency_ms"),
        ("P95 Query Latency (ms)", "p95_latency_ms"),
        ("Avg Top-1 Cosine Sim", "avg_top1_score"),
        ("Top-1 Topic Accuracy (%)", "top1_topic_accuracy"),
    ]

    for label, key in metrics:
        row = f"{label:<28}"
        for res in benchmark_results.values():
            row += f" | {str(res[key]):<20}"
        print(row)
    print("=" * 95)

    return benchmark_results


if __name__ == "__main__":
    run_benchmark()
