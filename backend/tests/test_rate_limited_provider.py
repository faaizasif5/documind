"""Retries go through the shared limiter; a 429 pauses every caller. No network calls."""

import pytest

from app.core.exceptions import ProviderRateLimitError
from app.services.providers.rate_limited import RateLimitedEmbeddingProvider
from app.services.rate_limiter import SlidingWindowRateLimiter


class _Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    async def sleep(self, seconds: float) -> None:
        self.now += seconds


class _FlakyProvider:
    """Raises the queued errors first, then succeeds; records call times."""

    def __init__(self, clock: _Clock, errors: list[ProviderRateLimitError]) -> None:
        self._clock = clock
        self._errors = list(errors)
        self.call_times: list[float] = []

    async def _attempt(self, n: int) -> list[list[float]]:
        self.call_times.append(self._clock.now)
        if self._errors:
            raise self._errors.pop(0)
        return [[0.0] for _ in range(n)]

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return await self._attempt(len(texts))

    async def embed_query(self, text: str) -> list[float]:
        return (await self._attempt(1))[0]


def _wrapped(
    clock: _Clock, inner: _FlakyProvider, *, rpm: int = 100, max_attempts: int = 5
) -> tuple[RateLimitedEmbeddingProvider, SlidingWindowRateLimiter]:
    limiter = SlidingWindowRateLimiter(
        rpm, 1_000_000, margin_seconds=0, clock=clock, sleep=clock.sleep
    )
    provider = RateLimitedEmbeddingProvider(
        inner, limiter, reserve_requests=10, max_attempts=max_attempts
    )
    return provider, limiter


def _limited(retry_after: float | None = 48.0, daily: bool = False) -> ProviderRateLimitError:
    return ProviderRateLimitError(retry_after_seconds=retry_after, daily_quota=daily)


async def test_retry_waits_server_delay_and_is_recorded_by_limiter() -> None:
    clock = _Clock()
    inner = _FlakyProvider(clock, [_limited(48.0)])
    provider, limiter = _wrapped(clock, inner)

    await provider.embed_documents(["x"] * 30)

    assert inner.call_times == [0.0, 48.0]
    # Both attempts are in the ledger: 60 used, so a 40-text batch must wait.
    await provider.embed_documents(["x"] * 40)
    assert clock.now == pytest.approx(60.0)


async def test_429_pauses_other_callers_too() -> None:
    clock = _Clock()
    inner = _FlakyProvider(clock, [_limited(30.0)])
    provider, _ = _wrapped(clock, inner)

    await provider.embed_documents(["x"])  # fails at t=0, retried at t=30
    await provider.embed_query("question")

    assert inner.call_times == [0.0, 30.0, 30.0]


async def test_fallback_backoff_without_retry_hint() -> None:
    clock = _Clock()
    inner = _FlakyProvider(clock, [_limited(None), _limited(None)])
    provider, _ = _wrapped(clock, inner)

    await provider.embed_documents(["x"])

    assert inner.call_times == [0.0, 2.0, 6.0]


async def test_gives_up_after_max_attempts() -> None:
    clock = _Clock()
    inner = _FlakyProvider(clock, [_limited(10.0)] * 3)
    provider, _ = _wrapped(clock, inner, max_attempts=3)

    with pytest.raises(ProviderRateLimitError):
        await provider.embed_documents(["x"])

    assert len(inner.call_times) == 3


async def test_daily_quota_is_not_retried() -> None:
    clock = _Clock()
    inner = _FlakyProvider(clock, [_limited(3600.0, daily=True)])
    provider, _ = _wrapped(clock, inner)

    with pytest.raises(ProviderRateLimitError):
        await provider.embed_documents(["x"])

    assert inner.call_times == [0.0]


async def test_query_fails_fast() -> None:
    clock = _Clock()
    inner = _FlakyProvider(clock, [_limited(5.0)] * 5)
    provider, _ = _wrapped(clock, inner)

    with pytest.raises(ProviderRateLimitError):
        await provider.embed_query("question")

    assert len(inner.call_times) == 2
