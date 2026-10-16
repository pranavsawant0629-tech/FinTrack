from typing import Generator
from fastembed import TextEmbedding

from config.settings import settings


class EmbeddingManager:
    """
    Manages text embedding generation using FastEmbed (ONNX runtime).
    Dynamically determines vector dimensions without hard-coding.
    """

    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or settings.embedding_model
        # Initialize FastEmbed TextEmbedding
        self._model = TextEmbedding(model_name=self.model_name)
        # Dynamically determine dimension from the loaded model
        self._dimension: int | None = None
        self._determine_dimension()

    def _determine_dimension(self) -> None:
        """
        Dynamically detects the embedding dimension by probing the model with a sample token.
        Never hard-codes vector dimensions.
        """
        sample_embed = list(self._model.embed(["probe"]))[0]
        self._dimension = len(sample_embed)

    @property
    def dimension(self) -> int:
        """
        Returns the dynamically detected vector dimension.
        """
        if self._dimension is None:
            self._determine_dimension()
        return self._dimension

    def embed_text(self, text: str) -> list[float]:
        """
        Generates embedding vector for a single text.
        """
        embeddings = list(self._model.embed([text]))
        return [float(val) for val in embeddings[0]]

    def embed_documents(self, texts: list[str], batch_size: int = 64) -> list[list[float]]:
        """
        Generates embedding vectors for a batch of documents.
        """
        if not texts:
            return []

        # If model is E5, fastembed handles prefixes or we format standard passages
        embeddings_generator: Generator = self._model.embed(texts, batch_size=batch_size)
        return [[float(val) for val in emb] for emb in embeddings_generator]

    def embed_query(self, query: str) -> list[float]:
        """
        Generates embedding vector for a search query.
        For E5 models, fastembed or passage/query prefixing is applied if needed.
        """
        query_text = query
        if "e5" in self.model_name.lower() and not query.lower().startswith("query:"):
            query_text = f"query: {query}"

        return self.embed_text(query_text)


# Default shared embedding manager instance
embedding_manager = EmbeddingManager()
