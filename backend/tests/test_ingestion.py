"""Streaming/resumable ingestion against an in-memory ChunkStore (no DB, no AI)."""

import uuid
from collections.abc import Sequence

import fitz
import pytest

from app.services.ingestion import IngestionError, PendingChunk, ingest_document


def _make_pdf(pages_text: list[str]) -> bytes:
    document = fitz.open()
    for text in pages_text:
        page = document.new_page()
        if text:
            page.insert_text((72, 72), text)
    pdf_bytes: bytes = document.tobytes()
    document.close()
    return pdf_bytes


class _MemoryStore:
    def __init__(self) -> None:
        self.chunks: dict[int, PendingChunk] = {}
        self.total: int | None = None
        self.ready = False
        self.batches: list[int] = []

    async def committed_chunk_count(self, document_id: uuid.UUID) -> int:
        return len(self.chunks)

    async def set_total_chunks(self, document_id: uuid.UUID, total: int) -> None:
        self.total = total

    async def save_batch(
        self,
        document_id: uuid.UUID,
        chunks: Sequence[PendingChunk],
        embeddings: Sequence[list[float]],
    ) -> None:
        for chunk in chunks:
            self.chunks.setdefault(chunk.chunk_index, chunk)
        self.batches.append(len(chunks))

    async def mark_ready(self, document_id: uuid.UUID) -> None:
        self.ready = True


class _CountingProvider:
    def __init__(self, fail_on_call: int | None = None, short_by: int = 0) -> None:
        self.calls = 0
        self.embedded = 0
        self._fail_on_call = fail_on_call
        self._short_by = short_by

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self.calls += 1
        if self.calls == self._fail_on_call:
            raise RuntimeError("transient provider failure")
        self.embedded += len(texts)
        return [[0.0] for _ in range(len(texts) - self._short_by)]

    async def embed_query(self, text: str) -> list[float]:
        return [0.0]


PAGES = [f"Page {n} content about topic {n}." for n in range(1, 8)]


async def test_ingests_in_batches_and_marks_ready() -> None:
    store = _MemoryStore()
    provider = _CountingProvider()

    total = await ingest_document(
        uuid.uuid4(), _make_pdf(PAGES), provider, store, batch_size=3, max_chunks=100
    )

    assert total == 7
    assert store.total == 7
    assert store.batches == [3, 3, 1]
    assert store.ready
    assert [store.chunks[i].page_number for i in range(7)] == list(range(1, 8))


async def test_resumes_after_failure_without_reembedding_committed_chunks() -> None:
    document_id = uuid.uuid4()
    pdf = _make_pdf(PAGES)
    store = _MemoryStore()

    with pytest.raises(RuntimeError):
        await ingest_document(
            document_id, pdf, _CountingProvider(fail_on_call=2), store, batch_size=3, max_chunks=100
        )
    assert len(store.chunks) == 3
    assert not store.ready

    resumed = _CountingProvider()
    await ingest_document(document_id, pdf, resumed, store, batch_size=3, max_chunks=100)

    assert resumed.embedded == 4
    assert sorted(store.chunks) == list(range(7))
    assert store.ready


async def test_fully_committed_document_just_marks_ready() -> None:
    document_id = uuid.uuid4()
    pdf = _make_pdf(PAGES)
    store = _MemoryStore()
    await ingest_document(
        document_id, pdf, _CountingProvider(), store, batch_size=10, max_chunks=100
    )
    store.ready = False

    provider = _CountingProvider()
    await ingest_document(document_id, pdf, provider, store, batch_size=10, max_chunks=100)

    assert provider.calls == 0
    assert store.ready


async def test_pdf_without_text_is_a_user_facing_error() -> None:
    with pytest.raises(IngestionError, match="No extractable text"):
        await ingest_document(
            uuid.uuid4(),
            _make_pdf(["", ""]),
            _CountingProvider(),
            _MemoryStore(),
            batch_size=3,
            max_chunks=100,
        )


async def test_unreadable_pdf_is_a_user_facing_error() -> None:
    with pytest.raises(IngestionError, match="Could not read"):
        await ingest_document(
            uuid.uuid4(),
            b"not a pdf",
            _CountingProvider(),
            _MemoryStore(),
            batch_size=3,
            max_chunks=100,
        )


async def test_embedding_count_mismatch_is_rejected() -> None:
    store = _MemoryStore()
    with pytest.raises(RuntimeError, match="embeddings for"):
        await ingest_document(
            uuid.uuid4(),
            _make_pdf(PAGES),
            _CountingProvider(short_by=1),
            store,
            batch_size=3,
            max_chunks=100,
        )
    assert store.chunks == {}


async def test_document_over_chunk_cap_is_rejected_before_embedding() -> None:
    store = _MemoryStore()
    provider = _CountingProvider()

    with pytest.raises(IngestionError, match="7 text chunks and the limit is 5"):
        await ingest_document(
            uuid.uuid4(), _make_pdf(PAGES), provider, store, batch_size=3, max_chunks=5
        )

    assert provider.calls == 0
    assert store.total is None
    assert store.chunks == {}


async def test_document_at_chunk_cap_is_accepted() -> None:
    store = _MemoryStore()

    total = await ingest_document(
        uuid.uuid4(), _make_pdf(PAGES), _CountingProvider(), store, batch_size=3, max_chunks=7
    )

    assert total == 7
    assert store.ready
