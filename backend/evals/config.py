from pydantic_settings import BaseSettings, SettingsConfigDict


class EvalSettings(BaseSettings):
    """Eval-only configuration.

    Eval keys live in ``backend/.env.eval`` (gitignored) or the environment, never in
    ``.env``: the app's Settings rejects unknown keys there. ``GROQ_API_KEY`` is shared
    with the app and may stay in ``.env``.
    """

    model_config = SettingsConfigDict(
        env_file=(".env", ".env.eval"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Disposable Postgres+pgvector with migrations applied. Never the production DB.
    eval_database_url: str | None = None

    groq_api_key: str | None = None
    eval_judge_base_url: str = "https://api.groq.com/openai/v1"
    # Groq retires models (llama-3.3-70b-versatile is gone); list them via GET {base_url}/models.
    eval_judge_model: str = "openai/gpt-oss-120b"
    # Conservative defaults; the providers' 429 retry hints take over if these are too high.
    eval_judge_rpm: int = 20
    eval_generation_rpm: int = 5
    eval_max_attempts: int = 5
