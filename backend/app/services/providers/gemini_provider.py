import re
from collections.abc import AsyncIterator
from typing import Any, cast

from google import genai
from google.genai import errors, types

from app.core.config import Settings
from app.core.exceptions import ProviderRateLimitError

_RATE_LIMITED = 429
_RETRY_DELAY_PATTERN = re.compile(r"^(\d+(?:\.\d+)?)s$")


def _error_details(exc: errors.APIError) -> list[dict[str, Any]]:
    payload = exc.details if isinstance(exc.details, dict) else {}
    error = payload.get("error", payload)
    details = error.get("details") if isinstance(error, dict) else None
    return [item for item in details if isinstance(item, dict)] if isinstance(details, list) else []


def parse_retry_delay(exc: errors.APIError) -> float | None:
    """Return the server's ``RetryInfo.retryDelay`` in seconds, if present (e.g. "48s")."""
    for item in _error_details(exc):
        if str(item.get("@type", "")).endswith("RetryInfo"):
            match = _RETRY_DELAY_PATTERN.match(str(item.get("retryDelay", "")))
            if match:
                return float(match.group(1))
    return None


def violated_quota(exc: errors.APIError) -> str | None:
    """The ``quotaId`` of the first QuotaFailure violation, e.g. "...PerMinute...-FreeTier"."""
    for item in _error_details(exc):
        if str(item.get("@type", "")).endswith("QuotaFailure"):
            for violation in item.get("violations", []) or []:
                if isinstance(violation, dict) and violation.get("quotaId"):
                    return str(violation["quotaId"])
    return None


def is_daily_quota(exc: errors.APIError) -> bool:
    """True when the violated quota is per-day: retrying within minutes cannot succeed."""
    quota_id = violated_quota(exc)
    return quota_id is not None and "PerDay" in quota_id


class GeminiEmbeddingProvider:
    """EmbeddingProvider backed by Google's Gemini embeddings API.

    Makes exactly one attempt per call. A 429 is translated into
    ``ProviderRateLimitError`` (with the server's retry delay and whether the
    daily quota is exhausted); retrying is the rate-limited wrapper's job, so
    every attempt is recorded by the shared limiter.
    """

    def __init__(self, settings: Settings) -> None:
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is required when LLM_PROVIDER=gemini")
        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._model = settings.gemini_embedding_model
        self._dim = settings.embedding_dim

    async def _embed(self, texts: list[str], task_type: str) -> list[list[float]]:
        config = types.EmbedContentConfig(task_type=task_type, output_dimensionality=self._dim)
        try:
            result = await self._client.aio.models.embed_content(
                model=self._model,
                contents=cast(Any, texts),
                config=config,
            )
        except errors.APIError as exc:
            if exc.code != _RATE_LIMITED:
                raise
            raise ProviderRateLimitError(
                f"Gemini embedding rate limited ({violated_quota(exc) or 'unknown quota'})",
                retry_after_seconds=parse_retry_delay(exc),
                daily_quota=is_daily_quota(exc),
            ) from exc
        return _vectors(result)

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return await self._embed(texts, "RETRIEVAL_DOCUMENT")

    async def embed_query(self, text: str) -> list[float]:
        embeddings = await self._embed([text], "RETRIEVAL_QUERY")
        return embeddings[0]


def _vectors(result: types.EmbedContentResponse) -> list[list[float]]:
    if not result.embeddings:
        raise RuntimeError("Gemini returned no embeddings")
    vectors: list[list[float]] = []
    for embedding in result.embeddings:
        if embedding.values is None:
            raise RuntimeError("Gemini returned an empty embedding")
        vectors.append(list(embedding.values))
    return vectors


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
