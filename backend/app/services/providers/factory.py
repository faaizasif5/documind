from app.core.config import Settings, get_settings
from app.services.providers.base import EmbeddingProvider
from app.services.providers.gemini_provider import GeminiEmbeddingProvider
from app.services.providers.openai_provider import OpenAIEmbeddingProvider


def get_embedding_provider(settings: Settings | None = None) -> EmbeddingProvider:
    """Return the embedding provider selected by ``settings.llm_provider``."""
    settings = settings or get_settings()
    if settings.llm_provider == "openai":
        return OpenAIEmbeddingProvider(settings)
    return GeminiEmbeddingProvider(settings)
