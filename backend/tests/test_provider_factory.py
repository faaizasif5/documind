import pytest

from app.core.config import Settings
from app.services.providers.factory import get_embedding_provider
from app.services.providers.gemini_provider import GeminiEmbeddingProvider
from app.services.providers.openai_provider import OpenAIEmbeddingProvider
from app.services.providers.rate_limited import RateLimitedEmbeddingProvider


def _settings(**overrides: object) -> Settings:
    base: dict[str, object] = {
        "database_url": "postgresql+asyncpg://u:p@localhost:5432/db",
        "llm_provider": "gemini",
        "gemini_api_key": "test-gemini-key",
        "openai_api_key": "test-openai-key",
    }
    base.update(overrides)
    return Settings(**base)  # type: ignore[arg-type]


def test_factory_returns_gemini_provider() -> None:
    provider = get_embedding_provider(_settings(llm_provider="gemini"))
    assert isinstance(provider, RateLimitedEmbeddingProvider)
    assert isinstance(provider.inner, GeminiEmbeddingProvider)


def test_factory_returns_openai_provider() -> None:
    provider = get_embedding_provider(_settings(llm_provider="openai"))
    assert isinstance(provider, RateLimitedEmbeddingProvider)
    assert isinstance(provider.inner, OpenAIEmbeddingProvider)


def test_gemini_requires_key() -> None:
    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        get_embedding_provider(_settings(llm_provider="gemini", gemini_api_key=None))


def test_openai_requires_key() -> None:
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        get_embedding_provider(_settings(llm_provider="openai", openai_api_key=None))


def test_providers_share_one_process_wide_limiter() -> None:
    first = get_embedding_provider(_settings())
    second = get_embedding_provider(_settings())
    assert first._limiter is second._limiter


def test_batch_size_must_fit_ingestion_budget() -> None:
    with pytest.raises(ValueError, match="EMBEDDING_BATCH_SIZE"):
        _settings(embedding_rpm=100, embedding_query_reserve_rpm=10, embedding_batch_size=91)
