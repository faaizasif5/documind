import uuid
from collections.abc import AsyncIterator
from pathlib import Path

import pytest

from app.core.exceptions import ProviderRateLimitError
from app.services.rag import NO_CONTEXT_MESSAGE
from app.services.rate_limiter import SlidingWindowRateLimiter
from app.services.retrieval import RetrievedChunk
from evals.generation import TextCache, answer_cache_key, generate_answer

DOC_A, DOC_B = uuid.uuid4(), uuid.uuid4()
MODEL = "gemini:test-model"


def _chunk(document_id: uuid.UUID, filename: str, page: int, content: str) -> RetrievedChunk:
    return RetrievedChunk(
        document_id=document_id,
        filename=filename,
        page_number=page,
        chunk_index=page,
        content=content,
    )


class _Provider:
    def __init__(self, text: str, error: Exception | None = None) -> None:
        self._text = text
        self._error = error
        self.prompts: list[str] = []

    async def stream_completion(self, system_prompt: str, user_prompt: str) -> AsyncIterator[str]:
        self.prompts.append(user_prompt)
        if self._error is not None:
            raise self._error
        for word in self._text.split(" "):
            yield word + " "


def _limiter() -> SlidingWindowRateLimiter:
    return SlidingWindowRateLimiter(100, 10**9)


def _cache(tmp_path: Path) -> TextCache:
    return TextCache(tmp_path / "answers.jsonl")


async def test_cited_pages_come_from_explicit_markers_only(tmp_path: Path) -> None:
    chunks = [
        _chunk(DOC_A, "a.pdf", 1, "alpha"),
        _chunk(DOC_A, "a.pdf", 1, "alpha two"),
        _chunk(DOC_B, "b.pdf", 4, "beta"),
    ]
    provider = _Provider("Alpha is first [Source 2].")

    answer = await generate_answer(
        provider, "Q?", chunks, _limiter(), _cache(tmp_path), model=MODEL, max_attempts=1
    )

    assert answer.cited_pages == {("b.pdf", 4)}
    assert [label for label, _ in answer.judge_sources] == [
        "Source 1: a.pdf, page 1",
        "Source 1: a.pdf, page 1",
        "Source 2: b.pdf, page 4",
    ]
    assert "[Source 2: b.pdf, page 4]" in provider.prompts[0]


async def test_uncited_answer_has_no_cited_pages(tmp_path: Path) -> None:
    answer = await generate_answer(
        _Provider("No markers here."),
        "Q?",
        [_chunk(DOC_A, "a.pdf", 1, "x")],
        _limiter(),
        _cache(tmp_path),
        model=MODEL,
        max_attempts=1,
    )
    assert answer.cited_pages == set()


async def test_no_chunks_uses_production_no_context_message(tmp_path: Path) -> None:
    provider = _Provider("unused")

    answer = await generate_answer(
        provider, "Q?", [], _limiter(), _cache(tmp_path), model=MODEL, max_attempts=1
    )

    assert answer.text == NO_CONTEXT_MESSAGE
    assert provider.prompts == []


async def test_cached_answer_skips_the_provider(tmp_path: Path) -> None:
    chunks = [_chunk(DOC_A, "a.pdf", 1, "alpha")]
    cache = _cache(tmp_path)
    first_provider = _Provider("Alpha [Source 1].")
    first = await generate_answer(
        first_provider, "Q?", chunks, _limiter(), cache, model=MODEL, max_attempts=1
    )

    second_provider = _Provider("different text")
    second = await generate_answer(
        second_provider, "Q?", chunks, _limiter(), cache, model=MODEL, max_attempts=1
    )

    assert not first.from_cache and second.from_cache
    assert second.text == first.text
    assert second.cited_pages == {("a.pdf", 1)}
    assert second_provider.prompts == []


async def test_answer_cache_survives_save_and_load(tmp_path: Path) -> None:
    chunks = [_chunk(DOC_A, "a.pdf", 1, "alpha")]
    cache = _cache(tmp_path)
    await generate_answer(
        _Provider("Alpha."), "Q?", chunks, _limiter(), cache, model=MODEL, max_attempts=1
    )
    cache.save()

    provider = _Provider("unused")
    reloaded = TextCache.load(cache.path)
    answer = await generate_answer(
        provider, "Q?", chunks, _limiter(), reloaded, model=MODEL, max_attempts=1
    )

    assert answer.from_cache
    assert provider.prompts == []


async def test_daily_quota_error_propagates_and_caches_nothing(tmp_path: Path) -> None:
    cache = _cache(tmp_path)
    provider = _Provider("", error=ProviderRateLimitError("quota", daily_quota=True))

    with pytest.raises(ProviderRateLimitError):
        await generate_answer(
            provider,
            "Q?",
            [_chunk(DOC_A, "a.pdf", 1, "alpha")],
            _limiter(),
            cache,
            model=MODEL,
            max_attempts=3,
        )

    assert len(provider.prompts) == 1
    assert not cache.dirty


def test_answer_cache_key_depends_on_model_and_prompt() -> None:
    assert answer_cache_key("m1", "p") != answer_cache_key("m2", "p")
    assert answer_cache_key("m1", "p") != answer_cache_key("m1", "p2")
    assert answer_cache_key("m1", "p") == answer_cache_key("m1", "p")
