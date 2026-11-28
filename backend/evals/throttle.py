"""Rate-limited calls for eval traffic (judge + answer generation).

Same rule as the app: every attempt, including retries, acquires from a limiter,
and a 429 pauses all callers for the provider's retry hint.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

import openai
from google.genai import errors as genai_errors

from app.core.exceptions import ProviderRateLimitError
from app.services.providers.gemini_provider import is_daily_quota, parse_retry_delay
from app.services.providers.groq_provider import is_daily_limit, retry_after_seconds
from app.services.rate_limiter import SlidingWindowRateLimiter

_FALLBACK_BACKOFF_SECONDS = 2.0
_MAX_FALLBACK_BACKOFF_SECONDS = 60.0


@dataclass(frozen=True, slots=True)
class RateLimitSignal:
    retry_after_seconds: float | None
    daily_quota: bool


def rate_limit_signal(exc: BaseException) -> RateLimitSignal | None:
    """Normalize 429s from the SDKs evals use; None for any other error."""
    if isinstance(exc, ProviderRateLimitError):
        return RateLimitSignal(exc.retry_after_seconds, exc.daily_quota)
    if isinstance(exc, genai_errors.APIError) and exc.code == 429:
        return RateLimitSignal(parse_retry_delay(exc), is_daily_quota(exc))
    if isinstance(exc, openai.RateLimitError):
        # Groq's per-day limits (RPD/TPD) roll over a 24 h window: waiting minutes won't help.
        return RateLimitSignal(retry_after_seconds(exc), daily_quota=is_daily_limit(exc))
    return None


async def call_with_limits[T](
    attempt: Callable[[], Awaitable[T]],
    limiter: SlidingWindowRateLimiter,
    *,
    max_attempts: int,
    tokens: int = 1,
) -> T:
    backoff = _FALLBACK_BACKOFF_SECONDS
    for attempt_number in range(1, max_attempts + 1):
        await limiter.acquire(1, tokens)
        try:
            return await attempt()
        except Exception as exc:
            signal = rate_limit_signal(exc)
            if signal is None or signal.daily_quota or attempt_number == max_attempts:
                raise
            delay = signal.retry_after_seconds
            if delay is None:
                delay = backoff
                backoff = min(backoff * 2, _MAX_FALLBACK_BACKOFF_SECONDS)
            limiter.pause_for(delay)
    raise RuntimeError("unreachable")  # pragma: no cover
