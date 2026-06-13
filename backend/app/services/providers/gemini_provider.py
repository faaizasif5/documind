import asyncio
from collections.abc import AsyncIterator
from typing import Any, cast

from google import genai
from google.genai import errors, types

from app.core.config import Settings

# Free-tier Gemini enforces low rate limits; retry transient 429s with backoff.
_MAX_RETRIES = 5
_INITIAL_BACKOFF_SECONDS = 2.0
_RATE_LIMITED = 429


class GeminiEmbeddingProvider:
    """EmbeddingProvider backed by Google's Gemini embeddings API."""

    def __init__(self, settings: Settings) -> None:
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is required when LLM_PROVIDER=gemini")
        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._model = settings.gemini_embedding_model
        self._dim = settings.embedding_dim

    async def _embed(self, texts: list[str], task_type: str) -> list[list[float]]:
        config = types.EmbedContentConfig(task_type=task_type, output_dimensionality=self._dim)
        backoff = _INITIAL_BACKOFF_SECONDS
        for attempt in range(_MAX_RETRIES):
            try:
                result = await self._client.aio.models.embed_content(
                    model=self._model,
                    contents=cast(Any, texts),
                    config=config,
                )
                if not result.embeddings:
                    raise RuntimeError("Gemini returned no embeddings")
                vectors: list[list[float]] = []
                for embedding in result.embeddings:
                    if embedding.values is None:
                        raise RuntimeError("Gemini returned an empty embedding")
                    vectors.append(list(embedding.values))
                return vectors
            except errors.APIError as exc:
                is_last_attempt = attempt == _MAX_RETRIES - 1
                if exc.code == _RATE_LIMITED and not is_last_attempt:
                    await asyncio.sleep(backoff)
                    backoff *= 2
                    continue
                raise
        raise RuntimeError("Gemini embedding retries exhausted")  # pragma: no cover

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return await self._embed(texts, task_type="RETRIEVAL_DOCUMENT")

    async def embed_query(self, text: str) -> list[float]:
        embeddings = await self._embed([text], task_type="RETRIEVAL_QUERY")
        return embeddings[0]


class GeminiCompletionProvider:
    """CompletionProvider backed by Google's Gemini generate-content API (streaming)."""

    def __init__(self, settings: Settings) -> None:
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is required when LLM_PROVIDER=gemini")
        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._model = settings.gemini_completion_model

    async def stream_completion(self, system_prompt: str, user_prompt: str) -> AsyncIterator[str]:
        config = types.GenerateContentConfig(system_instruction=system_prompt)
        stream = await self._client.aio.models.generate_content_stream(
            model=self._model,
            contents=cast(Any, user_prompt),
            config=config,
        )
        async for chunk in stream:
            if chunk.text:
                yield chunk.text
