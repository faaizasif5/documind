from functools import lru_cache

from app.core.config import Settings, get_settings
from app.services.providers.base import CompletionProvider, EmbeddingProvider
from app.services.providers.gemini_provider import (
    GeminiCompletionProvider,
    GeminiEmbeddingProvider,
)
from app.services.providers.groq_provider import GroqCompletionProvider
from app.services.providers.rate_limited import RateLimitedEmbeddingProvider
from app.services.rate_limiter import SlidingWindowRateLimiter


@lru_cache
def get_embedding_rate_limiter(rpm: int, tpm: int) -> SlidingWindowRateLimiter:
    """Process-wide limiter: one quota is shared by every provider instance and caller."""
    return SlidingWindowRateLimiter(rpm, tpm)


def build_raw_embedding_provider(settings: Settings) -> EmbeddingProvider:
    """Unthrottled Gemini embedding provider (embeddings always use Gemini)."""
    return GeminiEmbeddingProvider(settings)


def get_embedding_provider(settings: Settings | None = None) -> RateLimitedEmbeddingProvider:
    """Return the selected embedding provider behind the shared rate limiter."""
    settings = settings or get_settings()
    return RateLimitedEmbeddingProvider(
        build_raw_embedding_provider(settings),
        get_embedding_rate_limiter(settings.embedding_rpm, settings.embedding_tpm),
        reserve_requests=settings.embedding_query_reserve_rpm,
        max_attempts=settings.embedding_max_retries,
    )


def get_completion_provider(settings: Settings | None = None) -> CompletionProvider:
    """Return the chat provider selected by ``settings.completion_provider``."""
    settings = settings or get_settings()
    if settings.completion_provider == "gemini":
        return GeminiCompletionProvider(settings)
    return GroqCompletionProvider(settings)
