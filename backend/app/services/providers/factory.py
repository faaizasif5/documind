from app.core.config import Settings, get_settings
from app.services.providers.base import CompletionProvider, EmbeddingProvider
from app.services.providers.gemini_provider import (
    GeminiCompletionProvider,
    GeminiEmbeddingProvider,
)
from app.services.providers.openai_provider import (
    OpenAICompletionProvider,
    OpenAIEmbeddingProvider,
)


def get_embedding_provider(settings: Settings | None = None) -> EmbeddingProvider:
    """Return the embedding provider selected by ``settings.llm_provider``."""
    settings = settings or get_settings()
    if settings.llm_provider == "openai":
        return OpenAIEmbeddingProvider(settings)
    return GeminiEmbeddingProvider(settings)


def get_completion_provider(settings: Settings | None = None) -> CompletionProvider:
    """Return the completion provider selected by ``settings.llm_provider``."""
    settings = settings or get_settings()
    if settings.llm_provider == "openai":
        return OpenAICompletionProvider(settings)
    return GeminiCompletionProvider(settings)
