import uuid
from collections.abc import AsyncIterator
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes import chat as chat_route
from app.db.session import get_db_session
from app.main import create_app
from app.models import Document, DocumentStatus


class _FakeSession:
    """Minimal async stand-in so route logic runs without a real database."""

    def __init__(self, document: Document | None = None) -> None:
        self._document = document
        self.deleted = False
        self.committed = False

    async def get(self, _model: Any, _pk: Any) -> Document | None:
        return self._document

    async def delete(self, _obj: Any) -> None:
        self.deleted = True

    async def commit(self) -> None:
        self.committed = True


def _build_app(session: _FakeSession | None = None) -> FastAPI:
    app = create_app()
    if session is not None:

        async def _override() -> AsyncIterator[_FakeSession]:
            yield session

        app.dependency_overrides[get_db_session] = _override
    return app


def _sample_document() -> Document:
    return Document(
        id=uuid.uuid4(),
        filename="a.pdf",
        file_size=10,
        page_count=1,
        status=DocumentStatus.ready,
    )


def test_validation_error_returns_envelope() -> None:
    client = TestClient(_build_app(_FakeSession()))

    response = client.post("/api/v1/chat", json={"question": ""})

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "validation_error"
    assert any(item["field"] == "question" for item in body["error"]["details"])


def test_unsupported_media_type_returns_envelope() -> None:
    client = TestClient(_build_app(_FakeSession()))

    response = client.post(
        "/api/v1/documents",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )

    assert response.status_code == 415
    assert response.json()["error"]["code"] == "unsupported_media_type"


def test_get_document_not_found_returns_envelope() -> None:
    client = TestClient(_build_app(_FakeSession(document=None)))

    response = client.get(f"/api/v1/documents/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json()["error"] == {"code": "not_found", "message": "Document not found"}


def test_delete_document_cascades_and_returns_204() -> None:
    session = _FakeSession(document=_sample_document())
    client = TestClient(_build_app(session))

    response = client.delete(f"/api/v1/documents/{uuid.uuid4()}")

    assert response.status_code == 204
    assert response.content == b""
    assert session.deleted is True
    assert session.committed is True


def test_delete_document_not_found_returns_envelope() -> None:
    client = TestClient(_build_app(_FakeSession(document=None)))

    response = client.delete(f"/api/v1/documents/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_chat_provider_error_returns_502(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom(_settings: Any) -> Any:
        raise RuntimeError("provider down")

    monkeypatch.setattr(chat_route, "get_embedding_provider", _boom)
    client = TestClient(_build_app(_FakeSession()))

    response = client.post("/api/v1/chat", json={"question": "hello?"})

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "upstream_provider_error"
