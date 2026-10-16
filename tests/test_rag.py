import pytest
from fastapi.testclient import TestClient
from qdrant_client import QdrantClient

from app.main import app
from app.rag.document_parser import DocumentParser, ParsedDocument, PageContent
from app.rag.chunking import TextChunker, DocumentChunk
from app.rag.embeddings import EmbeddingManager, embedding_manager
from app.rag.vector_store import QdrantVectorStore
from app.rag.retriever import RAGRetriever


@pytest.fixture
def client():
    return TestClient(app)


def test_document_parser_clean_text():
    raw = "Investor-\nprotection  is    important.\r\n\r\n\n\nSEBI   regulates  markets."
    cleaned = DocumentParser.clean_text(raw)
    assert "Investorprotection" in cleaned
    assert "   " not in cleaned
    assert "\r" not in cleaned
    assert "\n\n" in cleaned


def test_document_parser_font_encoding_repair():
    corrupted = "Ho\u01c1 to lodge a \u0110o\u0175plai\u0176t i\u0176 SCO\u2018ES? \u03ec\u03ed\u03ee\u03ef\u03f0"
    cleaned = DocumentParser.clean_text(corrupted, file_name="igrbrochure.pdf")
    assert cleaned == "How to lodge a complaint in SCORES? 01234"


def test_document_parser_corruption_safeguard():
    clean = "This is a clean financial document about equities and primary markets."
    assert DocumentParser.detect_corruption_indicators(clean)["is_corrupted"] is False

    corrupted = "Ho\u01c1 to lodge a \u0110o\u0175plai\u0176t i\u0176 SCORES? " * 10
    indicators = DocumentParser.detect_corruption_indicators(corrupted)
    assert indicators["is_corrupted"] is True
    assert indicators["unusual_count"] >= 10


def test_chunking_size_and_overlap():
    content = "Paragraph 1: Indian equity markets operate with high transparency. " * 10
    doc = ParsedDocument(
        doc_id="test_doc",
        file_name="test_doc.txt",
        file_path="/tmp/test_doc.txt",
        file_type="txt",
        total_pages=1,
        full_text=content,
        pages=[PageContent(page_number=1, text=content)],
        metadata={"source": "SEBI", "authority_level": "Tier 1", "topic": "Equities"}
    )
    chunker = TextChunker(chunk_size=50, chunk_overlap=15)
    chunks = chunker.chunk_document(doc)

    assert len(chunks) > 1
    for idx, c in enumerate(chunks):
        assert c.doc_id == "test_doc"
        assert c.chunk_index == idx
        assert c.page_numbers == [1]
        assert c.metadata["source"] == "SEBI"


def test_embedding_dynamic_dimension():
    em = EmbeddingManager()
    dim = em.dimension
    assert isinstance(dim, int)
    assert dim > 0

    vector = em.embed_query("What is an ETF?")
    assert len(vector) == dim
    assert all(isinstance(val, float) for val in vector)


def test_vector_store_in_memory_lifecycle():
    # Use isolated in-memory Qdrant instance for test
    mem_client = QdrantClient(":memory:")
    store = QdrantVectorStore(collection_name="test_collection", client=mem_client)

    dim = 384
    store.ensure_collection(vector_size=dim)
    assert mem_client.collection_exists("test_collection")

    chunk = DocumentChunk(
        chunk_id="chk_01",
        doc_id="doc_01",
        chunk_index=0,
        text="The settlement cycle in India is T+1.",
        token_count=10,
        page_numbers=[1],
        metadata={"source": "SEBI", "authority_level": "Tier 1", "topic": "Equity"}
    )
    dummy_vector = [0.1] * dim

    upserted = store.upsert_chunks([chunk], [dummy_vector])
    assert upserted == 1
    assert store.count() == 1

    results = store.search(query_vector=dummy_vector, limit=1)
    assert len(results) == 1
    assert results[0].chunk_id == "chk_01"
    assert results[0].doc_id == "doc_01"
    assert results[0].text == "The settlement cycle in India is T+1."
    assert results[0].score > 0.99


def test_api_rag_retrieve_endpoint(client):
    response = client.post(
        "/rag/retrieve",
        json={"query": "What are the rules for buying and selling shares?", "top_k": 2}
    )
    assert response.status_code == 200
    data = response.json()

    assert "query" in data
    assert "total_results" in data
    assert "chunks" in data
    assert len(data["chunks"]) <= 2

    # Verify no LLM generation field exists
    assert "reply" not in data
    assert "answer" not in data

    # Verify chunk structure and provenance
    if data["total_results"] > 0:
        first = data["chunks"][0]
        assert "chunk_id" in first
        assert "doc_id" in first
        assert "text" in first
        assert "score" in first
        assert "source" in first
        assert "authority_level" in first
        assert "country" in first
        assert "topic" in first
        assert "url" in first
        assert "licensing_usage_status" in first
        assert first["source"] == "SEBI"
        assert first["authority_level"] == "Tier 1"
