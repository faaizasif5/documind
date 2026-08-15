import uuid
from collections.abc import AsyncIterator

from app.services.rag import (
    build_sources,
    build_user_prompt,
    cited_sources,
    parse_cited_numbers,
    stream_chat_response,
)
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


class _CitingProvider:
    """Answers while citing only the second source."""

    async def stream_completion(self, system_prompt: str, user_prompt: str) -> AsyncIterator[str]:
        for token in ["Refunds take 30 days ", "[Source 2]."]:
            yield token


def test_build_user_prompt_includes_numbered_sources() -> None:
    chunks = [_chunk(1, content="refund policy"), _chunk(2, content="shipping info")]

    prompt = build_user_prompt("What is the policy?", chunks)

    assert "[Source 1: a.pdf, page 1]" in prompt
    assert "[Source 2: a.pdf, page 2]" in prompt
    assert "Question: What is the policy?" in prompt


def test_build_user_prompt_reuses_one_number_per_document_page() -> None:
    document_id = uuid.uuid4()
    chunks = [
        _chunk(1, document_id, content="first half"),
        _chunk(1, document_id, content="second half"),
        _chunk(2, document_id, content="next page"),
    ]

    prompt = build_user_prompt("What is the policy?", chunks)

    # Both page-1 chunks share [Source 1] so marker numbers match the sources list.
    assert prompt.count("[Source 1: a.pdf, page 1]") == 2
    assert "[Source 2: a.pdf, page 2]" in prompt
    assert "[Source 3" not in prompt


def test_build_sources_collapses_same_document_page() -> None:
    document_id = uuid.uuid4()
    chunks = [_chunk(1, document_id), _chunk(1, document_id), _chunk(2, document_id)]

    sources = build_sources(chunks)

    assert [(source.number, source.page_number) for source in sources] == [(1, 1), (2, 2)]


def test_cited_sources_keeps_only_referenced_numbers() -> None:
    sources = build_sources([_chunk(1), _chunk(2), _chunk(3)])

    cited = cited_sources("Answer body [Source 3] and [Source 1].", sources)

    assert [source.number for source in cited] == [1, 3]


def test_cited_sources_reads_grouped_citation_markers() -> None:
    sources = build_sources([_chunk(1), _chunk(2), _chunk(3), _chunk(4), _chunk(5)])

    cited = cited_sources(
        "Overview [Source 1, Source 2, Source 5]. Details [Source 4].", sources
    )

    assert [source.number for source in cited] == [1, 2, 4, 5]


def test_parse_cited_numbers_handles_marker_variations() -> None:
    assert parse_cited_numbers("a [Source 1] b [Source 3]") == {1, 3}
    assert parse_cited_numbers("[Source 1, Source 2, Source 3]") == {1, 2, 3}
    assert parse_cited_numbers("[Sources 2 and 4]") == {2, 4}
    assert parse_cited_numbers("[Source 1][Source 2]") == {1, 2}
    assert parse_cited_numbers("no citations here") == set()


def test_cited_sources_falls_back_when_nothing_resolvable() -> None:
    sources = build_sources([_chunk(1), _chunk(2)])

    assert cited_sources("No markers here.", sources) == list(sources)
    assert cited_sources("Bogus [Source 9] marker.", sources) == list(sources)


async def test_stream_chat_response_emits_token_source_done_events() -> None:
    chunks = [_chunk(1)]

    events = [event async for event in stream_chat_response(_FakeProvider(), "q?", chunks)]
    joined = "".join(events)

    assert joined.count("event: token") == 2
    assert "event: sources" in joined
    assert joined.strip().endswith("event: done\ndata: {}")


async def test_stream_chat_response_emits_only_cited_sources() -> None:
    chunks = [_chunk(1), _chunk(2), _chunk(3)]

    events = [event async for event in stream_chat_response(_CitingProvider(), "q?", chunks)]
    joined = "".join(events)

    assert '"number": 2' in joined
    assert '"number": 1' not in joined
    assert '"number": 3' not in joined


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
