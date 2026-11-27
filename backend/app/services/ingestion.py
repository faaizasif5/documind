"""Streaming, resumable document ingestion.

extract → chunk → (embed one batch → insert → commit)*. Only one batch of
embeddings is ever held in memory, and every committed batch is durable, so a
restarted job resumes from the last committed chunk instead of re-embedding.
"""

import asyncio
import logging
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import Chunk, Document, DocumentStatus
from app.services.chunking import chunk_page_text
from app.services.pdf_extraction import PDFExtractionError, extract_pages
from app.services.providers.base import EmbeddingProvider

logger = logging.getLogger(__name__)


class IngestionError(Exception):
    """Non-retryable ingestion failure carrying a message that is safe to show users."""

    def __init__(self, user_message: str) -> None:
        super().__init__(user_message)
        self.user_message = user_message


@dataclass(frozen=True, slots=True)
class PendingChunk:
    page_number: int
    chunk_index: int
    content: str


def build_pending_chunks(pages: list[str]) -> list[PendingChunk]:
    """Chunk each page independently so every chunk keeps an exact page number.

    Deterministic for fixed chunk settings, which is what makes resuming by
    ``chunk_index`` safe.
    """
    pending: list[PendingChunk] = []
    chunk_index = 0
    for page_offset, page_text in enumerate(pages):
        for content in chunk_page_text(page_text):
            pending.append(
                PendingChunk(page_number=page_offset + 1, chunk_index=chunk_index, content=content)
            )
            chunk_index += 1
    return pending


class ChunkStore(Protocol):
    """Persistence used by ingestion; Postgres in production, in-memory in tests."""

    async def committed_chunk_count(self, document_id: uuid.UUID) -> int: ...

    async def set_total_chunks(self, document_id: uuid.UUID, total: int) -> None: ...

    async def save_batch(
        self,
        document_id: uuid.UUID,
        chunks: Sequence[PendingChunk],
        embeddings: Sequence[list[float]],
    ) -> None: ...

    async def mark_ready(self, document_id: uuid.UUID) -> None: ...


async def ingest_document(
    document_id: uuid.UUID,
    pdf_bytes: bytes,
    provider: EmbeddingProvider,
    store: ChunkStore,
    batch_size: int,
    max_chunks: int,
) -> int:
    """Ingest (or resume ingesting) a document. Returns the total chunk count.

    Documents over ``max_chunks`` are rejected after chunking but before any
    embedding call, so an oversized PDF costs no quota.

    Raises ``IngestionError`` for problems retrying cannot fix; any other
    exception is treated as transient by the caller.
    """
    try:
        pages = await extract_pages(pdf_bytes)
    except PDFExtractionError as exc:
        raise IngestionError("Could not read the PDF file.") from exc

    # Tokenizer-based splitting is CPU-bound; keep it off the event loop.
    pending = await asyncio.to_thread(build_pending_chunks, pages)
    if not pending:
        raise IngestionError(
            "No extractable text found. Scanned or image-only PDFs are not supported yet."
        )
    if len(pending) > max_chunks:
        raise IngestionError(
            f"This PDF is too long to process: it splits into {len(pending)} text chunks "
            f"and the limit is {max_chunks} per document. Try uploading a shorter section."
        )

    await store.set_total_chunks(document_id, len(pending))
    start = await store.committed_chunk_count(document_id)
    if start:
        logger.info("Resuming document %s at chunk %d/%d", document_id, start, len(pending))

    for offset in range(start, len(pending), batch_size):
        batch = pending[offset : offset + batch_size]
        embeddings = await provider.embed_documents([item.content for item in batch])
        if len(embeddings) != len(batch):
            raise RuntimeError(
                f"Provider returned {len(embeddings)} embeddings for {len(batch)} chunks"
            )
        await store.save_batch(document_id, batch, embeddings)

    await store.mark_ready(document_id)
    logger.info("Document %s ingested: %d chunks", document_id, len(pending))
    return len(pending)


class PostgresChunkStore:
    """ChunkStore that commits one short transaction per batch."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def committed_chunk_count(self, document_id: uuid.UUID) -> int:
        async with self._session_factory() as session:
            count = await session.scalar(
                select(func.count()).select_from(Chunk).where(Chunk.document_id == document_id)
            )
            return int(count or 0)

    async def set_total_chunks(self, document_id: uuid.UUID, total: int) -> None:
        async with self._session_factory() as session:
            await session.execute(
                update(Document).where(Document.id == document_id).values(total_chunks=total)
            )
            await session.commit()

    async def save_batch(
        self,
        document_id: uuid.UUID,
        chunks: Sequence[PendingChunk],
        embeddings: Sequence[list[float]],
    ) -> None:
        rows = [
            {
                "id": uuid.uuid4(),
                "document_id": document_id,
                "content": item.content,
                "page_number": item.page_number,
                "chunk_index": item.chunk_index,
                "embedding": embedding,
            }
            for item, embedding in zip(chunks, embeddings, strict=True)
        ]
        # Idempotent on (document_id, chunk_index) in case a batch is replayed.
        insert_stmt = (
            insert(Chunk)
            .values(rows)
            .on_conflict_do_nothing(index_elements=[Chunk.document_id, Chunk.chunk_index])
        )
        processed = (
            select(func.count())
            .select_from(Chunk)
            .where(Chunk.document_id == document_id)
            .scalar_subquery()
        )
        async with self._session_factory() as session:
            await session.execute(insert_stmt)
            await session.execute(
                update(Document)
                .where(Document.id == document_id)
                .values(processed_chunks=processed)
            )
            await session.commit()

    async def mark_ready(self, document_id: uuid.UUID) -> None:
        async with self._session_factory() as session:
            await session.execute(
                update(Document)
                .where(Document.id == document_id)
                .values(status=DocumentStatus.ready, error_message=None)
            )
            await session.commit()
