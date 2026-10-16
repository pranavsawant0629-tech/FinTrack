import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel

# Resolve project root and load .env from there
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Settings(BaseModel):
    # App Settings
    app_env: str = os.getenv("APP_ENV", "development")
    app_host: str = os.getenv("APP_HOST", "127.0.0.1")
    app_port: int = int(os.getenv("APP_PORT", "8000"))

    # LLM Settings (Ollama)
    ollama_host: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "qwen2.5:7b-instruct")

    # Qdrant Vector Store Settings
    qdrant_mode: str = os.getenv("QDRANT_MODE", "embedded")
    qdrant_path: str = os.getenv("QDRANT_PATH", "./data/qdrant_storage")
    qdrant_host: str = os.getenv("QDRANT_HOST", "localhost")
    qdrant_port: int = int(os.getenv("QDRANT_PORT", "6333"))
    qdrant_collection_name: str = os.getenv("QDRANT_COLLECTION_NAME", "finova_knowledge")

    # Embedding Settings
    embedding_provider: str = os.getenv("EMBEDDING_PROVIDER", "fastembed")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")

    # RAG Retrieval & Chunking Settings
    rag_top_k: int = int(os.getenv("RAG_TOP_K", "4"))
    rag_similarity_threshold: float = float(os.getenv("RAG_SIMILARITY_THRESHOLD", "0.65"))
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "600"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "100"))


settings = Settings()