import uuid
from collections.abc import AsyncIterator

from app.services.rag import NO_CONTEXT_MESSAGE
from app.services.rate_limiter import SlidingWindowRateLimiter
from app.services.retrieval import RetrievedChunk
from evals.generation import generate_answer

DOC_A, DOC_B = uuid.uuid4(), uuid.uuid4()


def _chunk(document_id: uuid.UUID, filename: str, page: int, content: str) -> RetrievedChunk:
    return RetrievedChunk(
        document_id=document_id,
        filename=filename,
        page_number=page,
        chunk_index=page,
        content=content,
    )


class _Provider:
    def __init__(self, text: str) -> None:
        self._text = text
        self.prompts: list[str] = []

    async def stream_completion(self, system_prompt: str, user_prompt: str) -> AsyncIterator[str]:
        self.prompts.append(user_prompt)
        for word in self._text.split(" "):
            yield word + " "


def _limiter() -> SlidingWindowRateLimiter:
    return SlidingWindowRateLimiter(100, 10**9)


async def test_cited_pages_come_from_explicit_markers_only() -> None:
    chunks = [
        _chunk(DOC_A, "a.pdf", 1, "alpha"),
        _chunk(DOC_A, "a.pdf", 1, "alpha two"),
        _chunk(DOC_B, "b.pdf", 4, "beta"),
    ]
    provider = _Provider("Alpha is first [Source 2].")

    answer = await generate_answer(provider, "Q?", chunks, _limiter(), max_attempts=1)

    assert answer.cited_pages == {("b.pdf", 4)}
    assert [label for label, _ in answer.judge_sources] == [
        "Source 1: a.pdf, page 1",
        "Source 1: a.pdf, page 1",
        "Source 2: b.pdf, page 4",
    ]
    assert "[Source 2: b.pdf, page 4]" in provider.prompts[0]


async def test_uncited_answer_has_no_cited_pages() -> None:
    answer = await generate_answer(
        _Provider("No markers here."),
        "Q?",
        [_chunk(DOC_A, "a.pdf", 1, "x")],
        _limiter(),
        max_attempts=1,
    )
    assert answer.cited_pages == set()


async def test_no_chunks_uses_production_no_context_message() -> None:
    provider = _Provider("unused")

    answer = await generate_answer(provider, "Q?", [], _limiter(), max_attempts=1)

    assert answer.text == NO_CONTEXT_MESSAGE
    assert provider.prompts == []
