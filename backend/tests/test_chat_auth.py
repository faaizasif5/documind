"""Chat route auth + per-user retrieval scoping (DB-free)."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes import chat as chat_route
from app.core.auth import CurrentUser, get_current_user
from app.db.session import get_db_session
from app.main import create_app
from app.models import Document, DocumentStatus
from app.services.retrieval import RetrievedChunk


class _FakeSession:
    def __init__(self, document: Document | None = None) -> None:
        self._document = document

    async def get(self, _model: Any, pk: Any) -> Document | None:
        if self._document is not None and self._document.id == pk:
            return self._document
        return None


class _EmbeddingProvider:
    async def embed_query(self, _question: str) -> list[float]:
        return [0.1, 0.2]


class _CompletionProvider:
    async def stream_completion(self, _system_prompt: str, _user_prompt: str) -> AsyncIterator[str]:
        if False:  # pragma: no cover
            yield ""


def _document(*, owner: uuid.UUID) -> Document:
    return Document(
        id=uuid.uuid4(),
        user_id=owner,
        filename="policy.pdf",
        file_size=10,
        page_count=1,
        status=DocumentStatus.ready,
        created_at=datetime.now(UTC),
    )


def _build_app(
    session: _FakeSession,
    *,
    user_id: uuid.UUID | None = None,
    authenticate: bool = True,
) -> FastAPI:
    app = create_app()

    async def _db() -> AsyncIterator[_FakeSession]:
        yield session

    app.dependency_overrides[get_db_session] = _db

    if authenticate:
        resolved = user_id or uuid.uuid4()

        async def _user() -> CurrentUser:
            return CurrentUser(id=resolved)

        app.dependency_overrides[get_current_user] = _user

    return app


def _patch_providers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(chat_route, "get_embedding_provider", lambda _s: _EmbeddingProvider())
    monkeypatch.setattr(chat_route, "get_completion_provider", lambda _s: _CompletionProvider())


def test_chat_requires_auth() -> None:
    client = TestClient(_build_app(_FakeSession(), authenticate=False))

    response = client.post("/api/v1/chat", json={"question": "What is the refund policy?"})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_chat_other_users_document_id_returns_404(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Ownership fails before providers run; still patch so a regression can't hit network.
    _patch_providers(monkeypatch)
    owner = uuid.uuid4()
    other = uuid.uuid4()
    document = _document(owner=owner)
    client = TestClient(_build_app(_FakeSession(document), user_id=other))

    response = client.post(
        "/api/v1/chat",
        json={"question": "What is the refund policy?", "document_id": str(document.id)},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_chat_passes_user_id_to_retrieval(monkeypatch: pytest.MonkeyPatch) -> None:
    user_id = uuid.uuid4()
    captured: dict[str, Any] = {}
    _patch_providers(monkeypatch)

    async def _retrieve(
        _session: Any,
        _embedding: list[float],
        _top_k: int,
        user_id: uuid.UUID,
        document_id: uuid.UUID | None = None,
    ) -> list[RetrievedChunk]:
        captured["user_id"] = user_id
        captured["document_id"] = document_id
        return []

    monkeypatch.setattr(chat_route, "retrieve_chunks", _retrieve)

    client = TestClient(_build_app(_FakeSession(), user_id=user_id))
    response = client.post("/api/v1/chat", json={"question": "What is the refund policy?"})

    assert response.status_code == 200
    assert captured["user_id"] == user_id
    assert captured["document_id"] is None
    assert "I couldn't find anything relevant" in response.text


def test_chat_owned_document_id_reaches_retrieval(monkeypatch: pytest.MonkeyPatch) -> None:
    owner = uuid.uuid4()
    document = _document(owner=owner)
    captured: dict[str, Any] = {}
    _patch_providers(monkeypatch)

    async def _retrieve(
        _session: Any,
        _embedding: list[float],
        _top_k: int,
        user_id: uuid.UUID,
        document_id: uuid.UUID | None = None,
    ) -> list[RetrievedChunk]:
        captured["user_id"] = user_id
        captured["document_id"] = document_id
        return []

    monkeypatch.setattr(chat_route, "retrieve_chunks", _retrieve)

    client = TestClient(_build_app(_FakeSession(document), user_id=owner))
    response = client.post(
        "/api/v1/chat",
        json={"question": "What is the refund policy?", "document_id": str(document.id)},
    )

    assert response.status_code == 200
    assert captured["user_id"] == owner
    assert captured["document_id"] == document.id
