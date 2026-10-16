import hashlib
import uuid
from typing import Any
from pathlib import Path
from pydantic import BaseModel, Field
from qdrant_client import QdrantClient
from qdrant_client.http.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
)

from config.settings import settings
from app.rag.chunking import DocumentChunk


class SearchResult(BaseModel):
    chunk_id: str
    doc_id: str
    text: str
    score: float
    page_numbers: list[int] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class QdrantVectorStore:
    """
    Vector store abstraction over Qdrant.
    Supports both local embedded disk storage and remote Qdrant server mode.
    Vector dimensions are dynamically configured, never hard-coded.
    """

    def __init__(
        self,
        collection_name: str | None = None,
        mode: str | None = None,
        storage_path: str | None = None,
        host: str | None = None,
        port: int | None = None,
        client: QdrantClient | None = None,
    ):
        self.collection_name = collection_name or settings.qdrant_collection_name
        self.mode = mode or settings.qdrant_mode

        if client is not None:
            self.client = client
        elif self.mode == "embedded":
            path = storage_path or settings.qdrant_path
            Path(path).mkdir(parents=True, exist_ok=True)
            self.client = QdrantClient(path=path)
        else:
            h = host or settings.qdrant_host
            p = port or settings.qdrant_port
            self.client = QdrantClient(host=h, port=p)

    def ensure_collection(self, vector_size: int, recreate: bool = False) -> None:
        """
        Ensures that the collection exists with the dynamically detected vector size.
        """
        exists = self.client.collection_exists(self.collection_name)
        if exists:
            if recreate:
                self.client.delete_collection(self.collection_name)
                exists = False
            else:
                return

        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )

    @staticmethod
    def _generate_point_id(chunk_id: str) -> str:
        """
        Deterministically converts a string chunk_id into a valid UUID string.
        """
        hash_digest = hashlib.md5(chunk_id.encode("utf-8")).hexdigest()
        return str(uuid.UUID(hash_digest))

    def upsert_chunks(
        self,
        chunks: list[DocumentChunk],
        embeddings: list[list[float]],
    ) -> int:
        """
        Upserts document chunks and their embeddings into the collection.
        Returns the count of points upserted.
        """
        if not chunks:
            return 0
        if len(chunks) != len(embeddings):
            raise ValueError(f"Number of chunks ({len(chunks)}) != number of embeddings ({len(embeddings)})")

        vector_dim = len(embeddings[0])
        self.ensure_collection(vector_size=vector_dim)

        points: list[PointStruct] = []
        for chunk, emb in zip(chunks, embeddings):
            point_id = self._generate_point_id(chunk.chunk_id)
            payload = {
                "chunk_id": chunk.chunk_id,
                "doc_id": chunk.doc_id,
                "chunk_index": chunk.chunk_index,
                "text": chunk.text,
                "token_count": chunk.token_count,
                "page_numbers": chunk.page_numbers,
                **chunk.metadata,
            }
            points.append(
                PointStruct(
                    id=point_id,
                    vector=emb,
                    payload=payload,
                )
            )

        self.client.upsert(
            collection_name=self.collection_name,
            points=points,
        )
        return len(points)

    def search(
        self,
        query_vector: list[float],
        limit: int | None = None,
        score_threshold: float | None = None,
        topic: str | None = None,
        authority_level: str | None = None,
    ) -> list[SearchResult]:
        """
        Performs vector similarity search with optional metadata filtering and thresholding.
        """
        lim = limit or settings.rag_top_k
        thresh = score_threshold if score_threshold is not None else settings.rag_similarity_threshold

        must_filters = []
        if topic:
            must_filters.append(FieldCondition(key="topic", match=MatchValue(value=topic)))
        if authority_level:
            must_filters.append(FieldCondition(key="authority_level", match=MatchValue(value=authority_level)))

        query_filter = Filter(must=must_filters) if must_filters else None

        # Execute search via Qdrant query_points (qdrant-client >= 1.10)
        search_res = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            limit=lim,
            score_threshold=thresh,
            query_filter=query_filter,
            with_payload=True,
        )

        results: list[SearchResult] = []
        for pt in search_res.points:
            payload = pt.payload or {}
            results.append(
                SearchResult(
                    chunk_id=payload.get("chunk_id", str(pt.id)),
                    doc_id=payload.get("doc_id", "unknown"),
                    text=payload.get("text", ""),
                    score=float(pt.score),
                    page_numbers=payload.get("page_numbers", []),
                    metadata={k: v for k, v in payload.items() if k not in ("text",)},
                )
            )

        return results

    def count(self) -> int:
        """
        Returns total number of points in the collection.
        """
        if not self.client.collection_exists(self.collection_name):
            return 0
        return self.client.count(collection_name=self.collection_name).count


# Default shared vector store instance
vector_store = QdrantVectorStore()
