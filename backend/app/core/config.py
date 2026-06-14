from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

LLMProvider = Literal["openai", "gemini"]


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    app_env: str = "local"
    app_name: str = "DocuMind API"
    api_v1_prefix: str = "/api/v1"
    backend_cors_origins: str = "http://localhost:3000"

    database_url: str
    # Direct/session-pooler URL used only by Alembic migrations (DDL + prepared
    # statements). Falls back to database_url when unset.
    database_migration_url: str | None = None

    # AI provider selection. Keys are validated lazily when a provider is built,
    # so the app boots without a key for work that doesn't call the AI.
    llm_provider: LLMProvider = "gemini"
    openai_api_key: str | None = None
    gemini_api_key: str | None = None
    openai_embedding_model: str = "text-embedding-3-small"
    gemini_embedding_model: str = "gemini-embedding-001"
    openai_completion_model: str = "gpt-4o-mini"
    gemini_completion_model: str = "gemini-2.5-flash"

    embedding_dim: int = 1536
    embedding_batch_size: int = 64
    chunk_size: int = 512
    chunk_overlap: int = 50
    upload_max_bytes: int = 10 * 1024 * 1024

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.backend_cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
