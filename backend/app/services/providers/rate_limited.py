import logging
from collections.abc import Awaitable, Callable
from typing import TypeVar

from app.core.exceptions import ProviderRateLimitError
from app.services.chunking import count_tokens
from app.services.providers.base import EmbeddingProvider
from app.services.rate_limiter import SlidingWindowRateLimiter

logger = logging.getLogger(__name__)

_T = TypeVar("_T")

_FALLBACK_BACKOFF_SECONDS = 2.0
_MAX_FALLBACK_BACKOFF_SECONDS = 60.0
# Interactive query embeddings fail fast rather than hold a chat request for minutes.
_QUERY_MAX_ATTEMPTS = 2


class RateLimitedEmbeddingProvider:
    """EmbeddingProvider decorator: proactive throttling plus 429 retries.

    Every attempt, retries included, acquires from the shared limiter, so the
    limiter's ledger matches what the provider actually received. A 429 pauses
    all callers for the server's retry delay (``RetryInfo``), falling back to
    exponential backoff; daily-quota exhaustion is raised without retrying.

    Each text counts as one request (that is how Gemini's free tier meters batch
    embeddings). Document batches come from background ingestion and must leave
    ``reserve_requests`` free; query embeddings come from chat and may use it.
    """

    def __init__(
        self,
        inner: EmbeddingProvider,
        limiter: SlidingWindowRateLimiter,
        *,
        reserve_requests: int,
        max_attempts: int,
    ) -> None:
        self.inner = inner
        self._limiter = limiter
        self._reserve = reserve_requests
        self._max_attempts = max(1, max_attempts)

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return await self._call(
            lambda: self.inner.embed_documents(texts),
            requests=len(texts),
            tokens=count_tokens(texts),
            reserve=self._reserve,
            max_attempts=self._max_attempts,
        )

    async def embed_query(self, text: str) -> list[float]:
        return await self._call(
            lambda: self.inner.embed_query(text),
            requests=1,
            tokens=count_tokens([text]),
            reserve=0,
            max_attempts=min(self._max_attempts, _QUERY_MAX_ATTEMPTS),
        )

    async def _call(
        self,
        attempt_once: Callable[[], Awaitable[_T]],
        *,
        requests: int,
        tokens: int,
        reserve: int,
        max_attempts: int,
    ) -> _T:
        backoff = _FALLBACK_BACKOFF_SECONDS
        for attempt in range(1, max_attempts + 1):
            await self._limiter.acquire(requests, tokens, reserve_requests=reserve)
            try:
                return await attempt_once()
            except ProviderRateLimitError as exc:
                if exc.daily_quota or attempt == max_attempts:
                    raise
                delay = exc.retry_after_seconds
                if delay is None:
                    delay = backoff
                    backoff = min(backoff * 2, _MAX_FALLBACK_BACKOFF_SECONDS)
                logger.warning(
                    "%s; pausing embeddings %.1fs (attempt %d/%d)",
                    exc.message,
                    delay,
                    attempt,
                    max_attempts,
                )
                self._limiter.pause_for(delay)
        raise RuntimeError("unreachable")  # pragma: no cover
