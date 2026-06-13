from typing import Protocol, runtime_checkable


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Provider-agnostic embedding interface.

    Implementations must return vectors of length ``settings.embedding_dim``.
    Document and query embeddings are separated because some providers (Gemini)
    accept a task type that improves retrieval quality.
    """

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of document chunks."""
        ...

    async def embed_query(self, text: str) -> list[float]:
        """Embed a single search query."""
        ...
