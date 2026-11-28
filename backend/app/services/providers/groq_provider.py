from collections.abc import AsyncIterator
from typing import Any, cast

import openai
from openai import AsyncOpenAI

from app.core.config import Settings
from app.core.exceptions import ProviderRateLimitError

# Groq names the exhausted window in its 429 message, e.g.
# "... on requests per day (RPD): Limit 1000, Used 1000 ..." or "... tokens per minute (TPM) ...".
_DAILY_MARKERS = ("per day", "(RPD)", "(TPD)")


def retry_after_seconds(exc: openai.RateLimitError) -> float | None:
    header = exc.response.headers.get("retry-after")
    try:
        return float(header) if header is not None else None
    except ValueError:
        return None


def is_daily_limit(exc: openai.RateLimitError) -> bool:
    message = str(exc)
    return any(marker in message for marker in _DAILY_MARKERS)


class GroqCompletionProvider:
    """CompletionProvider backed by Groq's OpenAI-compatible chat API (streaming).

    One attempt per call, like the Gemini providers: the SDK's own retries are off and a
    429 becomes ``ProviderRateLimitError`` with Groq's retry hint, so callers decide
    whether and when to retry.
    """

    def __init__(self, settings: Settings) -> None:
        if not settings.groq_api_key:
            raise ValueError("GROQ_API_KEY is required when COMPLETION_PROVIDER=groq")
        self._client = AsyncOpenAI(
            api_key=settings.groq_api_key, base_url=settings.groq_base_url, max_retries=0
        )
        self._model = settings.groq_completion_model
        self._extra_body: dict[str, Any] = (
            {"reasoning_format": settings.groq_reasoning_format}
            if settings.groq_reasoning_format
            else {}
        )

    async def stream_completion(self, system_prompt: str, user_prompt: str) -> AsyncIterator[str]:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        try:
            stream = await self._client.chat.completions.create(
                model=self._model,
                messages=cast(Any, messages),
                stream=True,
                extra_body=self._extra_body or None,
            )
        except openai.RateLimitError as exc:
            raise ProviderRateLimitError(
                f"Groq chat rate limited ({self._model})",
                retry_after_seconds=retry_after_seconds(exc),
                daily_quota=is_daily_limit(exc),
            ) from exc
        async for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
