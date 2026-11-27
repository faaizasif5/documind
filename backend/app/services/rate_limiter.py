"""Proactive client-side throttle for provider quotas.

A sliding 60 s window is used instead of a classic token bucket: a bucket of
capacity C refilling at C/min can admit up to 2C requests inside one 60 s span
(a full burst, then a full refill), which would trip Gemini's per-minute quota.
A sliding window never admits more than the configured limit in any 60 s span.

Grants are stamped when admitted, slightly before the provider receives the
request, so the window carries a safety margin to absorb that skew.
"""

import asyncio
import time
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

_WINDOW_SECONDS = 60.0
_DEFAULT_MARGIN_SECONDS = 5.0


@dataclass(frozen=True, slots=True)
class _Grant:
    at: float
    requests: int
    tokens: int


class SlidingWindowRateLimiter:
    """Admit (requests, tokens) only while the trailing window stays within limits.

    ``reserve_requests`` lets background work leave headroom for interactive
    callers that share the same quota (ingestion vs chat query embeddings).
    The check-and-record step has no ``await`` between them, so it is atomic on
    a single event loop and needs no lock.
    """

    def __init__(
        self,
        requests_per_window: int,
        tokens_per_window: int,
        *,
        window_seconds: float = _WINDOW_SECONDS,
        margin_seconds: float = _DEFAULT_MARGIN_SECONDS,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        if requests_per_window < 1 or tokens_per_window < 1:
            raise ValueError("Rate limits must be positive")
        self._max_requests = requests_per_window
        self._max_tokens = tokens_per_window
        self._window = window_seconds + margin_seconds
        self._clock = clock
        self._sleep = sleep
        self._grants: deque[_Grant] = deque()
        self._used_requests = 0
        self._used_tokens = 0
        self._paused_until = 0.0

    def pause_for(self, seconds: float) -> None:
        """Hold every caller for ``seconds`` (the provider said its quota is cooling)."""
        self._paused_until = max(self._paused_until, self._clock() + seconds)

    async def acquire(self, requests: int, tokens: int, *, reserve_requests: int = 0) -> None:
        if requests < 1:
            raise ValueError("requests must be >= 1")
        if requests + reserve_requests > self._max_requests:
            raise ValueError("Request batch can never fit within the rate limit")
        # A single oversized batch is admitted alone rather than blocking forever.
        tokens = min(tokens, self._max_tokens)
        while True:
            now = self._clock()
            if now < self._paused_until:
                await self._sleep(self._paused_until - now)
                continue
            self._evict(now)
            wait = self._wait_seconds(now, requests + reserve_requests, tokens)
            if wait <= 0:
                self._grants.append(_Grant(at=now, requests=requests, tokens=tokens))
                self._used_requests += requests
                self._used_tokens += tokens
                return
            await self._sleep(wait)

    def _evict(self, now: float) -> None:
        while self._grants and self._grants[0].at + self._window <= now:
            expired = self._grants.popleft()
            self._used_requests -= expired.requests
            self._used_tokens -= expired.tokens

    def _wait_seconds(self, now: float, requests: int, tokens: int) -> float:
        """Seconds until enough of the oldest grants expire to fit this request."""
        excess_requests = self._used_requests + requests - self._max_requests
        excess_tokens = self._used_tokens + tokens - self._max_tokens
        if excess_requests <= 0 and excess_tokens <= 0:
            return 0.0
        freed_requests = 0
        freed_tokens = 0
        for grant in self._grants:
            freed_requests += grant.requests
            freed_tokens += grant.tokens
            if freed_requests >= excess_requests and freed_tokens >= excess_tokens:
                return grant.at + self._window - now
        return self._window  # pragma: no cover - unreachable given acquire() validation
