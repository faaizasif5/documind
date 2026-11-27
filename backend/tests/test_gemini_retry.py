"""Gemini 429 translation: RetryInfo delay, quota id, daily quota. No network calls."""

from typing import Any

import pytest
from google.genai import errors

from app.core.config import Settings
from app.core.exceptions import ProviderRateLimitError
from app.services.providers.gemini_provider import (
    GeminiEmbeddingProvider,
    is_daily_quota,
    parse_retry_delay,
    violated_quota,
)

_MINUTE_QUOTA = "EmbedContentRequestsPerMinutePerUserPerProjectPerModel-FreeTier"
_DAY_QUOTA = "EmbedContentRequestsPerDayPerUserPerProjectPerModel-FreeTier"


def _rate_limit_error(
    retry_delay: str | None = "48s", quota_id: str = _MINUTE_QUOTA
) -> errors.APIError:
    details: list[dict[str, Any]] = [
        {
            "@type": "type.googleapis.com/google.rpc.QuotaFailure",
            "violations": [{"quotaId": quota_id}],
        }
    ]
    if retry_delay is not None:
        details.append(
            {"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": retry_delay}
        )
    return errors.APIError(
        429, {"error": {"code": 429, "status": "RESOURCE_EXHAUSTED", "details": details}}
    )


class _Embedding:
    def __init__(self) -> None:
        self.values = [0.1, 0.2]


class _Result:
    def __init__(self, n: int) -> None:
        self.embeddings = [_Embedding() for _ in range(n)]


class _FakeModels:
    def __init__(self, failures: list[errors.APIError]) -> None:
        self._failures = list(failures)
        self.calls = 0

    async def embed_content(self, *, model: str, contents: list[str], config: Any) -> _Result:
        self.calls += 1
        if self._failures:
            raise self._failures.pop(0)
        return _Result(len(contents))


def _provider(models: _FakeModels) -> GeminiEmbeddingProvider:
    settings = Settings(
        database_url="postgresql+asyncpg://u:p@localhost:5432/db",
        gemini_api_key="test-key",
    )
    provider = GeminiEmbeddingProvider(settings)

    class _Aio:
        pass

    class _Client:
        aio = _Aio()

    _Client.aio.models = models  # type: ignore[attr-defined]
    provider._client = _Client()  # type: ignore[assignment]
    return provider


def test_parse_retry_delay() -> None:
    assert parse_retry_delay(_rate_limit_error("48s")) == 48.0
    assert parse_retry_delay(_rate_limit_error("12.5s")) == 12.5
    assert parse_retry_delay(_rate_limit_error(None)) is None


def test_quota_detection() -> None:
    assert violated_quota(_rate_limit_error()) == _MINUTE_QUOTA
    assert is_daily_quota(_rate_limit_error(quota_id=_DAY_QUOTA))
    assert not is_daily_quota(_rate_limit_error())


async def test_success_returns_vectors() -> None:
    vectors = await _provider(_FakeModels([])).embed_documents(["a", "b"])
    assert vectors == [[0.1, 0.2], [0.1, 0.2]]


async def test_429_becomes_rate_limit_error_with_server_delay() -> None:
    models = _FakeModels([_rate_limit_error("48s")])

    with pytest.raises(ProviderRateLimitError) as info:
        await _provider(models).embed_documents(["a"])

    assert info.value.retry_after_seconds == 48.0
    assert not info.value.daily_quota
    assert _MINUTE_QUOTA in info.value.message
    # Exactly one attempt: retries belong to the rate-limited wrapper.
    assert models.calls == 1


async def test_daily_quota_is_flagged() -> None:
    models = _FakeModels([_rate_limit_error("3600s", quota_id=_DAY_QUOTA)])

    with pytest.raises(ProviderRateLimitError) as info:
        await _provider(models).embed_query("q")

    assert info.value.daily_quota


async def test_non_rate_limit_errors_pass_through() -> None:
    models = _FakeModels([errors.APIError(400, {"error": {"code": 400, "status": "INVALID"}})])

    with pytest.raises(errors.APIError):
        await _provider(models).embed_documents(["a"])
