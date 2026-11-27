from functools import lru_cache
from typing import Literal, Self

from pydantic import Field, model_validator
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

    # Supabase Auth — project URL is required for JWKS JWT verification (ES256/RS256).
    # Example: https://<project-ref>.supabase.co
    supabase_url: str
    # Optional legacy HS256 shared secret (Previous key). Not needed when Current
    # signing key is ECC/RSA; keep only as a temporary fallback for old tokens.
    supabase_jwt_secret: str | None = None

    # AI provider selection. Keys are validated lazily when a provider is built,
    # so the app boots without a key for work that doesn't call the AI.
    llm_provider: LLMProvider = "gemini"
    openai_api_key: str | None = None
    gemini_api_key: str | None = None
    # Groq (OpenAI-compatible): eval judge now; completion fallback provider in v2 Phase 3.
    groq_api_key: str | None = None
    openai_embedding_model: str = "text-embedding-3-small"
    gemini_embedding_model: str = "gemini-embedding-001"
    openai_completion_model: str = "gpt-4o-mini"
    gemini_completion_model: str = "gemini-2.5-flash"

    embedding_dim: int = 1536
    # Chunks per embed call. Smaller batches give finer progress and smaller resume gaps;
    # they don't cost extra quota because Gemini counts every text as one request.
    embedding_batch_size: int = 32
    chunk_size: int = 512
    chunk_overlap: int = 50
    upload_max_bytes: int = 10 * 1024 * 1024

    # Proactive embedding throttle (sliding 60 s window, shared by ingestion and chat).
    # Gemini free tier counts each embedded text as one request: 100/min observed.
    embedding_rpm: int = 100
    embedding_tpm: int = 30_000
    # Requests per minute that ingestion must leave free so chat queries never starve.
    embedding_query_reserve_rpm: int = 10
    embedding_max_retries: int = 5

    # Durable ingestion worker (Postgres job queue).
    ingestion_worker_enabled: bool = True
    ingestion_poll_interval_seconds: float = 5.0
    ingestion_lease_seconds: int = 120
    ingestion_max_attempts: int = 3
    ingestion_retry_backoff_seconds: float = 30.0
    # Gemini's free tier allows roughly 1,000 embedded texts per day for the whole project
    # (shared by all users and chat). 500 keeps one document to about half a day's quota.
    max_chunks_per_document: int = Field(default=500, ge=1)

    @model_validator(mode="after")
    def _check_embedding_budget(self) -> Self:
        ingest_rpm = self.embedding_rpm - self.embedding_query_reserve_rpm
        if self.embedding_batch_size < 1 or self.embedding_batch_size > ingest_rpm:
            raise ValueError(
                "EMBEDDING_BATCH_SIZE must be between 1 and "
                "EMBEDDING_RPM - EMBEDDING_QUERY_RESERVE_RPM"
            )
        return self

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.backend_cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
