"""Cached follow-up rewriting for evals, built on the production rewriter.

Uses the same prompt and cleanup as ``app.services.query_rewrite``. Rewrites are cached by
(model, prompt) and committed, so offline CI retrieval runs reuse them without any API call.
"""

import hashlib
from collections.abc import Sequence

from app.services.providers.base import CompletionProvider
from app.services.query_rewrite import (
    REWRITE_SYSTEM_PROMPT,
    TurnLike,
    build_rewrite_prompt,
    clean_rewrite,
)
from app.services.rate_limiter import SlidingWindowRateLimiter
from evals.embedding_cache import CacheMissError
from evals.generation import TextCache
from evals.throttle import call_with_limits

REWRITE_CACHE_VERSION = "2026-11-28.v1"


def rewrite_cache_key(model: str, prompt: str) -> str:
    material = "\x1f".join((REWRITE_CACHE_VERSION, model, REWRITE_SYSTEM_PROMPT, prompt))
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


class CachedRewriter:
    """Standalone query for a golden item. ``provider=None`` means offline: misses fail."""

    def __init__(
        self,
        provider: CompletionProvider | None,
        cache: TextCache,
        limiter: SlidingWindowRateLimiter,
        *,
        model: str,
        max_attempts: int,
    ) -> None:
        self._provider = provider
        self._cache = cache
        self._limiter = limiter
        self._model = model
        self._max_attempts = max_attempts
        self.hits = 0
        self.misses = 0

    async def __call__(self, question: str, history: Sequence[TurnLike]) -> str:
        if not history:
            return question
        prompt = build_rewrite_prompt(question, history)
        key = rewrite_cache_key(self._model, prompt)
        cached = self._cache.get(key)
        if cached is not None:
            self.hits += 1
            return cached
        provider = self._provider
        if provider is None:
            raise CacheMissError(f"query rewrite missing from the cache: {question!r}")

        async def attempt() -> str:
            return "".join(
                [delta async for delta in provider.stream_completion(REWRITE_SYSTEM_PROMPT, prompt)]
            )

        text = await call_with_limits(attempt, self._limiter, max_attempts=self._max_attempts)
        self.misses += 1
        rewritten = clean_rewrite(text) or question
        self._cache.put(key, rewritten)
        return rewritten
