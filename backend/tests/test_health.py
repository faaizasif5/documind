import importlib

from fastapi.testclient import TestClient
from pytest import MonkeyPatch


def test_health_check_returns_ok(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost/test")
    monkeypatch.setenv("OPENAI_API_KEY", "test-api-key")

    config = importlib.import_module("app.core.config")
    config.get_settings.cache_clear()

    main = importlib.import_module("app.main")
    app = main.create_app()

    response = TestClient(app).get("/api/v1/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "DocuMind API"}
