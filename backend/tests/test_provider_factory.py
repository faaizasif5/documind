import pytest

from app.core.config import Settings
from app.services.providers.factory import get_completion_provider, get_embedding_provider
from app.services.providers.gemini_provider import (
    GeminiCompletionProvider,
    GeminiEmbeddingProvider,
)
from app.services.providers.groq_provider import GroqCompletionProvider
from app.services.providers.rate_limited import RateLimitedEmbeddingProvider


def _settings(**overrides: object) -> Settings:
    base: dict[str, object] = {
        "database_url": "postgresql+asyncpg://u:p@localhost:5432/db",
        "gemini_api_key": "test-gemini-key",
        "groq_api_key": "test-groq-key",
    }
    base.update(overrides)
    return Settings(**base)  # type: ignore[arg-type]


def test_embeddings_always_use_gemini() -> None:
    provider = get_embedding_provider(_settings(completion_provider="groq"))
    assert isinstance(provider, RateLimitedEmbeddingProvider)
    assert isinstance(provider.inner, GeminiEmbeddingProvider)


def test_gemini_embeddings_require_key() -> None:
    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        get_embedding_provider(_settings(gemini_api_key=None))


def test_chat_defaults_to_groq() -> None:
    assert isinstance(get_completion_provider(_settings()), GroqCompletionProvider)


def test_chat_can_use_gemini() -> None:
    provider = get_completion_provider(_settings(completion_provider="gemini"))
    assert isinstance(provider, GeminiCompletionProvider)


def test_groq_chat_requires_key() -> None:
    with pytest.raises(ValueError, match="GROQ_API_KEY"):
        get_completion_provider(_settings(groq_api_key=None))


def test_openai_is_no_longer_a_provider() -> None:
    with pytest.raises(ValueError):
        _settings(completion_provider="openai")


def test_providers_share_one_process_wide_limiter() -> None:
    first = get_embedding_provider(_settings())
    second = get_embedding_provider(_settings())
    assert first._limiter is second._limiter


def test_batch_size_must_fit_ingestion_budget() -> None:
    with pytest.raises(ValueError, match="EMBEDDING_BATCH_SIZE"):
        _settings(embedding_rpm=100, embedding_query_reserve_rpm=10, embedding_batch_size=91)
