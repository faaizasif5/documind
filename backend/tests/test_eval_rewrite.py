"""Eval rewriter: cache hits, offline misses, passthrough without history (no API calls)."""

from collections.abc import AsyncIterator
from pathlib import Path

import pytest

from app.services.rate_limiter import SlidingWindowRateLimiter
from evals.embedding_cache import CacheMissError
from evals.generation import TextCache
from evals.rewrite import CachedRewriter
from evals.schema import Turn

HISTORY = [
    Turn(role="user", content="What is confabulation?"),
    Turn(role="assistant", content="Confidently stated but false output."),
]


class _Provider:
    def __init__(self, reply: str) -> None:
        self._reply = reply
        self.calls = 0

    async def stream_completion(self, system_prompt: str, user_prompt: str) -> AsyncIterator[str]:
        self.calls += 1
        yield self._reply


def _rewriter(provider: _Provider | None, cache: TextCache) -> CachedRewriter:
    return CachedRewriter(
        provider, cache, SlidingWindowRateLimiter(100, 10**9), model="groq:m", max_attempts=1
    )


async def test_rewrite_is_cached_and_reused_offline(tmp_path: Path) -> None:
    cache = TextCache(tmp_path / "rewrites.jsonl")
    online = _Provider("Give an example of harm caused by confabulation.")
    first = await _rewriter(online, cache)("Give an example of that.", HISTORY)
    cache.save()

    offline = _rewriter(None, TextCache.load(cache.path))
    second = await offline("Give an example of that.", HISTORY)

    assert first == second == "Give an example of harm caused by confabulation."
    assert online.calls == 1
    assert offline.hits == 1


async def test_offline_miss_raises(tmp_path: Path) -> None:
    with pytest.raises(CacheMissError):
        await _rewriter(None, TextCache(tmp_path / "r.jsonl"))("Give an example?", HISTORY)


async def test_no_history_returns_question_without_calls(tmp_path: Path) -> None:
    provider = _Provider("unused")
    cache = TextCache(tmp_path / "r.jsonl")

    assert await _rewriter(provider, cache)("What is GOVERN?", []) == "What is GOVERN?"
    assert provider.calls == 0
    assert not cache.dirty
