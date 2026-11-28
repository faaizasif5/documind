"""Follow-up rewriting: prompt shape, cleanup, and the chat route's use of it (no API calls)."""

import uuid
from collections.abc import AsyncIterator
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api.routes import chat as chat_route
from app.core.auth import CurrentUser, get_current_user
from app.db.session import get_db_session
from app.main import create_app
from app.schemas.chat import ChatRequest, ChatTurn
from app.services.query_rewrite import (
    MAX_HISTORY_TURNS,
    MAX_TURN_CHARS,
    build_rewrite_prompt,
    clean_rewrite,
    format_history,
    rewrite_query,
)
from app.services.retrieval import RetrievedChunk

HISTORY = [
    ChatTurn(role="user", content="What are the CSF 2.0 Functions?"),
    ChatTurn(role="assistant", content="GOVERN, IDENTIFY, PROTECT, DETECT, RESPOND, RECOVER."),
]


class _Rewriter:
    def __init__(self, reply: str = "", error: Exception | None = None) -> None:
        self._reply = reply
        self._error = error
        self.prompts: list[str] = []

    async def stream_completion(self, system_prompt: str, user_prompt: str) -> AsyncIterator[str]:
        self.prompts.append(user_prompt)
        if self._error is not None:
            raise self._error
        yield self._reply


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Which CSF 2.0 Function is central?", "Which CSF 2.0 Function is central?"),
        ('  "Which CSF 2.0 Function is central?"  ', "Which CSF 2.0 Function is central?"),
        ("Standalone question: Which Function is central?", "Which Function is central?"),
        ("\n\nWhich Function?\nExplanation: it refers to CSF.", "Which Function?"),
        ("   \n  ", None),
        ('""', None),
    ],
)
def test_clean_rewrite(raw: str, expected: str | None) -> None:
    assert clean_rewrite(raw) == expected


def test_format_history_keeps_last_turns_and_truncates() -> None:
    turns = [ChatTurn(role="user", content=f"q{i}") for i in range(10)]
    turns.append(ChatTurn(role="assistant", content="x" * (MAX_TURN_CHARS + 50)))

    lines = format_history(turns).splitlines()

    assert len(lines) == MAX_HISTORY_TURNS
    assert lines[0] == "User: q5"
    assert lines[-1].startswith("Assistant: xxx")
    assert lines[-1].endswith(" …")


def test_rewrite_prompt_contains_conversation_and_question() -> None:
    prompt = build_rewrite_prompt("Which one is central?", HISTORY)

    assert "User: What are the CSF 2.0 Functions?" in prompt
    assert "Assistant: GOVERN, IDENTIFY" in prompt
    assert prompt.endswith("Latest question: Which one is central?\n\nStandalone question:")


async def test_no_history_skips_the_model() -> None:
    provider = _Rewriter("unused")

    assert await rewrite_query(provider, "What is GOVERN?", []) == "What is GOVERN?"
    assert provider.prompts == []


async def test_history_uses_the_cleaned_rewrite() -> None:
    provider = _Rewriter('"Which CSF 2.0 Function is central?"')

    query = await rewrite_query(provider, "Which one is central?", HISTORY)

    assert query == "Which CSF 2.0 Function is central?"


async def test_empty_rewrite_falls_back_to_question() -> None:
    assert await rewrite_query(_Rewriter("  "), "Which one?", HISTORY) == "Which one?"


def test_chat_request_caps_history_at_six_turns() -> None:
    turn = {"role": "user", "content": "hi"}
    ChatRequest.model_validate({"question": "q", "history": [turn] * 6})
    with pytest.raises(ValidationError):
        ChatRequest.model_validate({"question": "q", "history": [turn] * 7})


def _authenticated_app() -> FastAPI:
    app = create_app()

    async def _db() -> AsyncIterator[None]:
        yield None

    async def _user() -> CurrentUser:
        return CurrentUser(id=uuid.uuid4())

    app.dependency_overrides[get_db_session] = _db
    app.dependency_overrides[get_current_user] = _user
    return app


class _Embedder:
    def __init__(self) -> None:
        self.queries: list[str] = []

    async def embed_query(self, text: str) -> list[float]:
        self.queries.append(text)
        return [0.1]


def _post_follow_up(
    monkeypatch: pytest.MonkeyPatch, completion: _Rewriter
) -> tuple[Any, _Embedder]:
    embedder = _Embedder()
    monkeypatch.setattr(chat_route, "get_embedding_provider", lambda _s: embedder)
    monkeypatch.setattr(chat_route, "get_completion_provider", lambda _s: completion)

    async def _retrieve(*_args: Any, **_kwargs: Any) -> list[RetrievedChunk]:
        return []

    monkeypatch.setattr(chat_route, "retrieve_chunks", _retrieve)
    client = TestClient(_authenticated_app())
    response = client.post(
        "/api/v1/chat",
        json={
            "question": "Which one is central?",
            "history": [turn.model_dump() for turn in HISTORY],
        },
    )
    return response, embedder


def test_chat_searches_with_the_rewritten_query(monkeypatch: pytest.MonkeyPatch) -> None:
    response, embedder = _post_follow_up(
        monkeypatch, _Rewriter("Which CSF 2.0 Function is central?")
    )

    assert response.status_code == 200
    assert embedder.queries == ["Which CSF 2.0 Function is central?"]
    assert 'event: query\ndata: {"text": "Which CSF 2.0 Function is central?"}' in response.text


def test_chat_falls_back_to_raw_question_when_rewrite_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response, embedder = _post_follow_up(monkeypatch, _Rewriter(error=RuntimeError("down")))

    assert response.status_code == 200
    assert embedder.queries == ["Which one is central?"]
    assert "event: query" not in response.text
