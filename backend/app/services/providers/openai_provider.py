from openai import AsyncOpenAI

from app.core.config import Settings


class OpenAIEmbeddingProvider:
    """EmbeddingProvider backed by OpenAI's embeddings API."""

    def __init__(self, settings: Settings) -> None:
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required when LLM_PROVIDER=openai")
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)
        self._model = settings.openai_embedding_model

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        response = await self._client.embeddings.create(model=self._model, input=texts)
        return [item.embedding for item in response.data]

    async def embed_query(self, text: str) -> list[float]:
        response = await self._client.embeddings.create(model=self._model, input=[text])
        return response.data[0].embedding
