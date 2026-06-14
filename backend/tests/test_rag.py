import uuid
from collections.abc import AsyncIterator

from app.services.rag import build_user_prompt, dedupe_sources, stream_chat_response
from app.services.retrieval import RetrievedChunk


def _chunk(
    page: int, document_id: uuid.UUID | None = None, content: str = "text"
) -> RetrievedChunk:
    return RetrievedChunk(
        document_id=document_id or uuid.uuid4(),
        filename="a.pdf",
        page_number=page,
        chunk_index=0,
        content=content,
    )


class _FakeProvider:
    async def stream_completion(self, system_prompt: str, user_prompt: str) -> AsyncIterator[str]:
        for token in ["Hello", " world"]:
            yield token


class _FailingProvider:
    async def stream_completion(self, system_prompt: str, user_prompt: str) -> AsyncIterator[str]:
        yield "partial"
        raise RuntimeError("provider exploded")


def test_build_user_prompt_includes_numbered_sources() -> None:
    chunks = [_chunk(1, content="refund policy"), _chunk(2, content="shipping info")]

    prompt = build_user_prompt("What is the policy?", chunks)

    assert "[Source 1: a.pdf, page 1]" in prompt
    assert "[Source 2: a.pdf, page 2]" in prompt
    assert "Question: What is the policy?" in prompt


def test_dedupe_sources_collapses_same_document_page() -> None:
    document_id = uuid.uuid4()
    chunks = [_chunk(1, document_id), _chunk(1, document_id), _chunk(2, document_id)]

    sources = dedupe_sources(chunks)

    assert len(sources) == 2
    assert sources[0].page_number == 1
    assert sources[1].page_number == 2


async def test_stream_chat_response_emits_token_source_done_events() -> None:
    chunks = [_chunk(1)]

    events = [event async for event in stream_chat_response(_FakeProvider(), "q?", chunks)]
    joined = "".join(events)

    assert joined.count("event: token") == 2
    assert "event: sources" in joined
    assert joined.strip().endswith("event: done\ndata: {}")


async def test_stream_chat_response_handles_no_chunks() -> None:
    events = [event async for event in stream_chat_response(_FakeProvider(), "q?", [])]
    joined = "".join(events)

    assert "event: token" in joined
    assert "event: sources\ndata: []" in joined
    assert "event: done" in joined


async def test_stream_chat_response_emits_error_event_on_failure() -> None:
    chunks = [_chunk(1)]

    events = [event async for event in stream_chat_response(_FailingProvider(), "q?", chunks)]
    joined = "".join(events)

    assert "event: error" in joined
    assert "event: sources" not in joined
    assert joined.strip().endswith("event: done\ndata: {}")
