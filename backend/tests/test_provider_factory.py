import pytest

from app.core.config import Settings
from app.services.providers.factory import get_embedding_provider
from app.services.providers.gemini_provider import GeminiEmbeddingProvider
from app.services.providers.openai_provider import OpenAIEmbeddingProvider


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
    assert isinstance(provider, GeminiEmbeddingProvider)


def test_factory_returns_openai_provider() -> None:
    provider = get_embedding_provider(_settings(llm_provider="openai"))
    assert isinstance(provider, OpenAIEmbeddingProvider)


def test_gemini_requires_key() -> None:
    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        get_embedding_provider(_settings(llm_provider="gemini", gemini_api_key=None))


def test_openai_requires_key() -> None:
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        get_embedding_provider(_settings(llm_provider="openai", openai_api_key=None))
