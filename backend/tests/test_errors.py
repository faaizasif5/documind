import uuid
from collections.abc import AsyncIterator, Sequence
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes import chat as chat_route
from app.core.auth import CurrentUser, get_current_user
from app.db.session import get_db_session
from app.main import create_app
from app.models import Document, DocumentStatus


class _FakeScalars:
    def __init__(self, rows: Sequence[Document]) -> None:
        self._rows = list(rows)

    def all(self) -> list[Document]:
        return self._rows


class _FakeResult:
    def __init__(self, rows: Sequence[Document]) -> None:
        self._rows = list(rows)

    def scalars(self) -> _FakeScalars:
        return _FakeScalars(self._rows)


class _FakeSession:
    """Minimal async stand-in so route logic runs without a real database."""

    def __init__(self, document: Document | None = None) -> None:
        self._document = document
        self.deleted = False
        self.committed = False

    async def get(self, _model: Any, _pk: Any) -> Document | None:
        return self._document

    async def execute(self, _stmt: Any) -> _FakeResult:
        rows = [self._document] if self._document is not None else []
        return _FakeResult(rows)

    async def delete(self, _obj: Any) -> None:
        self.deleted = True

    async def commit(self) -> None:
        self.committed = True


def _build_app(
    session: _FakeSession | None = None,
    *,
    user_id: uuid.UUID | None = None,
) -> FastAPI:
    app = create_app()
    resolved_user = user_id
    if resolved_user is None and session is not None and session._document is not None:
        resolved_user = session._document.user_id
    if resolved_user is None:
        resolved_user = uuid.uuid4()

    async def _current_user() -> CurrentUser:
        return CurrentUser(id=resolved_user)

    app.dependency_overrides[get_current_user] = _current_user

    if session is not None:

        async def _override() -> AsyncIterator[_FakeSession]:
            yield session

        app.dependency_overrides[get_db_session] = _override
    return app


def _sample_document(*, user_id: uuid.UUID | None = None) -> Document:
    return Document(
        id=uuid.uuid4(),
        user_id=user_id or uuid.uuid4(),
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
    document = _sample_document()
    session = _FakeSession(document=document)
    client = TestClient(_build_app(session, user_id=document.user_id))

    response = client.delete(f"/api/v1/documents/{document.id}")

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
