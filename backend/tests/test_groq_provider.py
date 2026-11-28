"""GroqCompletionProvider with a fake OpenAI-compatible client (no API calls)."""

from collections.abc import AsyncIterator
from types import SimpleNamespace
from typing import Any

import httpx
import openai
import pytest

from app.core.config import Settings
from app.core.exceptions import ProviderRateLimitError
from app.services.providers.groq_provider import GroqCompletionProvider


def _settings(**overrides: object) -> Settings:
    base: dict[str, object] = {
        "database_url": "postgresql+asyncpg://u:p@localhost:5432/db",
        "groq_api_key": "test-groq-key",
        "groq_completion_model": "test/model",
    }
    base.update(overrides)
    return Settings(**base)  # type: ignore[arg-type]


def _chunk(content: str | None) -> SimpleNamespace:
    return SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=content))])


class _Completions:
    def __init__(self, chunks: list[SimpleNamespace], error: Exception | None = None) -> None:
        self._chunks = chunks
        self._error = error
        self.calls: list[dict[str, Any]] = []

    async def create(self, **kwargs: Any) -> AsyncIterator[SimpleNamespace]:
        self.calls.append(kwargs)
        if self._error is not None:
            raise self._error

        async def stream() -> AsyncIterator[SimpleNamespace]:
            for chunk in self._chunks:
                yield chunk

        return stream()


def _provider(completions: _Completions, **overrides: object) -> GroqCompletionProvider:
    provider = GroqCompletionProvider(_settings(**overrides))
    provider._client = SimpleNamespace(chat=SimpleNamespace(completions=completions))  # type: ignore[assignment]
    return provider


def _rate_limit_error(message: str, retry_after: str | None) -> openai.RateLimitError:
    headers = {"retry-after": retry_after} if retry_after else {}
    # openai>=3 types this as httpx2.Response; both accept an httpx.Response at runtime.
    response: Any = httpx.Response(429, headers=headers, request=httpx.Request("POST", "https://x"))
    return openai.RateLimitError(message, response=response, body=None)


async def _collect(provider: GroqCompletionProvider) -> str:
    return "".join([delta async for delta in provider.stream_completion("sys", "user")])


async def test_streams_text_and_skips_empty_chunks() -> None:
    completions = _Completions(
        [_chunk("Alpha "), _chunk(None), SimpleNamespace(choices=[]), _chunk("[Source 1].")]
    )

    text = await _collect(_provider(completions))

    assert text == "Alpha [Source 1]."
    call = completions.calls[0]
    assert call["model"] == "test/model"
    assert call["stream"] is True
    assert call["messages"] == [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "user"},
    ]


async def test_reasoning_format_is_sent_when_configured() -> None:
    hidden = _Completions([_chunk("x")])
    await _collect(_provider(hidden, groq_reasoning_format="hidden"))
    assert hidden.calls[0]["extra_body"] == {"reasoning_format": "hidden"}

    unset = _Completions([_chunk("x")])
    await _collect(_provider(unset, groq_reasoning_format=None))
    assert unset.calls[0]["extra_body"] is None


async def test_per_minute_429_carries_retry_hint() -> None:
    error = _rate_limit_error("Rate limit reached ... on tokens per minute (TPM)", "7")

    with pytest.raises(ProviderRateLimitError) as caught:
        await _collect(_provider(_Completions([], error)))

    assert caught.value.retry_after_seconds == pytest.approx(7.0)
    assert caught.value.daily_quota is False


async def test_daily_429_is_flagged_as_daily_quota() -> None:
    error = _rate_limit_error("Rate limit reached ... on requests per day (RPD)", None)

    with pytest.raises(ProviderRateLimitError) as caught:
        await _collect(_provider(_Completions([], error)))

    assert caught.value.daily_quota is True
    assert caught.value.retry_after_seconds is None


def test_sdk_retries_are_disabled() -> None:
    provider = GroqCompletionProvider(_settings())
    assert provider._client.max_retries == 0
