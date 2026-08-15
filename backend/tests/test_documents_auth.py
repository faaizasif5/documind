"""Document route auth + ownership (DB-free via dependency overrides)."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator, Sequence
from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

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
    """Async session stand-in that filters list queries in Python by user_id."""

    def __init__(self, documents: list[Document] | None = None) -> None:
        self.documents = list(documents or [])
        self.deleted: Document | None = None
        self.committed = False
        self.added: Document | None = None

    async def get(self, _model: Any, pk: Any) -> Document | None:
        for document in self.documents:
            if document.id == pk:
                return document
        return None

    async def execute(self, stmt: Any) -> _FakeResult:
        # Mirror ``WHERE documents.user_id = :user_id`` for list_documents.
        user_id = _extract_user_id_filter(stmt)
        rows = (
            [doc for doc in self.documents if doc.user_id == user_id]
            if user_id is not None
            else list(self.documents)
        )
        return _FakeResult(rows)

    def add(self, document: Document) -> None:
        self.added = document
        self.documents.append(document)

    async def delete(self, document: Document) -> None:
        self.deleted = document
        self.documents = [item for item in self.documents if item.id != document.id]

    async def commit(self) -> None:
        self.committed = True

    async def refresh(self, document: Document) -> None:
        document.created_at = datetime.now(UTC)


def _extract_user_id_filter(stmt: Any) -> uuid.UUID | None:
    """Extract the ``user_id`` bind value from a SQLAlchemy SELECT WHERE clause."""
    where = getattr(stmt, "whereclause", None)
    if where is None:
        return None

    for element in where.get_children():
        value = getattr(element, "value", None)
        if isinstance(value, uuid.UUID):
            return value
        for child in getattr(element, "get_children", lambda: ())():
            child_value = getattr(child, "value", None)
            if isinstance(child_value, uuid.UUID):
                return child_value
    return None


def _document(*, owner: uuid.UUID, filename: str = "a.pdf") -> Document:
    return Document(
        id=uuid.uuid4(),
        user_id=owner,
        filename=filename,
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


def test_documents_require_auth() -> None:
    session = _FakeSession()
    client = TestClient(_build_app(session, authenticate=False))
    doc_id = uuid.uuid4()

    assert client.get("/api/v1/documents").status_code == 401
    assert client.get(f"/api/v1/documents/{doc_id}").status_code == 401
    assert client.delete(f"/api/v1/documents/{doc_id}").status_code == 401
    assert (
        client.post(
            "/api/v1/documents",
            files={"file": ("notes.pdf", b"%PDF-1.4", "application/pdf")},
        ).status_code
        == 401
    )


def test_list_documents_scoped_to_current_user() -> None:
    user_a = uuid.uuid4()
    user_b = uuid.uuid4()
    docs = [
        _document(owner=user_a, filename="a.pdf"),
        _document(owner=user_b, filename="b.pdf"),
        _document(owner=user_a, filename="a2.pdf"),
    ]
    client = TestClient(_build_app(_FakeSession(docs), user_id=user_a))

    response = client.get("/api/v1/documents")

    assert response.status_code == 200
    filenames = {item["filename"] for item in response.json()}
    assert filenames == {"a.pdf", "a2.pdf"}


def test_get_other_users_document_returns_404() -> None:
    owner = uuid.uuid4()
    other = uuid.uuid4()
    document = _document(owner=owner)
    client = TestClient(_build_app(_FakeSession([document]), user_id=other))

    response = client.get(f"/api/v1/documents/{document.id}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_get_own_document_returns_200() -> None:
    owner = uuid.uuid4()
    document = _document(owner=owner)
    client = TestClient(_build_app(_FakeSession([document]), user_id=owner))

    response = client.get(f"/api/v1/documents/{document.id}")

    assert response.status_code == 200
    assert response.json()["id"] == str(document.id)


def test_delete_other_users_document_returns_404() -> None:
    owner = uuid.uuid4()
    other = uuid.uuid4()
    document = _document(owner=owner)
    session = _FakeSession([document])
    client = TestClient(_build_app(session, user_id=other))

    response = client.delete(f"/api/v1/documents/{document.id}")

    assert response.status_code == 404
    assert session.deleted is None
    assert session.committed is False


def test_delete_own_document_returns_204() -> None:
    owner = uuid.uuid4()
    document = _document(owner=owner)
    session = _FakeSession([document])
    client = TestClient(_build_app(session, user_id=owner))

    response = client.delete(f"/api/v1/documents/{document.id}")

    assert response.status_code == 204
    assert session.deleted is document
    assert session.committed is True
