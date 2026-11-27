"""Job queue + chunk store against a real Postgres with pgvector.

Skipped unless TEST_DATABASE_URL points at a disposable database, e.g.

    docker run -d -p 5433:5432 -e POSTGRES_PASSWORD=postgres pgvector/pgvector:pg16
    $env:TEST_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5433/postgres"

The schema is dropped and recreated, so never point this at a real database.
"""

import asyncio
import os
import uuid
from collections.abc import AsyncIterator

import pytest
from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.db.base import Base
from app.models import Chunk, Document, DocumentStatus, IngestionJob, IngestionJobStatus
from app.services.ingestion import PendingChunk, PostgresChunkStore
from app.services.job_queue import JobQueue, enqueue_ingestion

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL, reason="TEST_DATABASE_URL not set (needs Postgres + pgvector)"
)


@pytest.fixture
async def session_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    assert TEST_DATABASE_URL is not None
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


async def _add_document(
    factory: async_sessionmaker[AsyncSession], pdf: bytes = b"%PDF"
) -> uuid.UUID:
    document_id = uuid.uuid4()
    async with factory() as session:
        session.add(
            Document(
                id=document_id,
                user_id=uuid.uuid4(),
                filename="a.pdf",
                file_size=len(pdf),
                page_count=1,
                status=DocumentStatus.processing,
            )
        )
        enqueue_ingestion(session, document_id, pdf)
        await session.commit()
    return document_id


async def test_concurrent_claims_never_return_the_same_job(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    for _ in range(5):
        await _add_document(session_factory)
    queue = JobQueue(session_factory, lease_seconds=60)

    claims = await asyncio.gather(*(queue.claim(f"w{i}") for i in range(8)))

    claimed = [job.id for job in claims if job is not None]
    assert len(claimed) == 5
    assert len(set(claimed)) == 5


async def test_jobs_not_yet_due_are_skipped(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _add_document(session_factory)
    async with session_factory() as session:
        await session.execute(
            update(IngestionJob).values(next_run_at=text("now() + interval '1 hour'"))
        )
        await session.commit()

    assert await JobQueue(session_factory, lease_seconds=60).claim("w") is None


async def test_expired_lease_is_reclaimed_and_old_owner_is_fenced(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _add_document(session_factory)
    queue = JobQueue(session_factory, lease_seconds=60)
    first = await queue.claim("crashed-worker")
    assert first is not None
    async with session_factory() as session:
        await session.execute(
            update(IngestionJob).values(lease_expires_at=text("now() - interval '1 second'"))
        )
        await session.commit()

    second = await queue.claim("new-worker")

    assert second is not None and second.id == first.id
    assert second.attempts == 2
    assert await queue.renew_lease(first.id, "crashed-worker") is False
    assert await queue.renew_lease(second.id, "new-worker") is True


async def test_rate_limit_reschedule_refunds_attempt(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _add_document(session_factory)
    queue = JobQueue(session_factory, lease_seconds=60)
    job = await queue.claim("w")
    assert job is not None

    await queue.reschedule(job.id, "w", delay_seconds=0, refund_attempt=True)

    again = await queue.claim("w")
    assert again is not None and again.attempts == 1


async def test_fail_marks_document_and_drops_pdf(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    document_id = await _add_document(session_factory)
    queue = JobQueue(session_factory, lease_seconds=60)
    job = await queue.claim("w")
    assert job is not None

    await queue.fail(job, "w", user_message="Could not read the PDF file.")

    async with session_factory() as session:
        document = await session.get(Document, document_id)
        stored = await session.get(IngestionJob, job.id)
    assert document is not None and stored is not None
    assert document.status == DocumentStatus.failed
    assert document.error_message == "Could not read the PDF file."
    assert stored.status == IngestionJobStatus.failed
    assert stored.pdf_bytes is None


async def test_complete_clears_pdf(session_factory: async_sessionmaker[AsyncSession]) -> None:
    await _add_document(session_factory)
    queue = JobQueue(session_factory, lease_seconds=60)
    job = await queue.claim("w")
    assert job is not None

    await queue.complete(job.id, "w")

    async with session_factory() as session:
        stored = await session.get(IngestionJob, job.id)
    assert stored is not None
    assert stored.status == IngestionJobStatus.succeeded
    assert stored.pdf_bytes is None


async def test_save_batch_is_idempotent_and_tracks_progress(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    document_id = await _add_document(session_factory)
    store = PostgresChunkStore(session_factory)
    batch = [PendingChunk(page_number=1, chunk_index=i, content=f"c{i}") for i in range(3)]
    vectors = [[0.0] * 1536 for _ in batch]

    await store.set_total_chunks(document_id, 3)
    await store.save_batch(document_id, batch, vectors)
    await store.save_batch(document_id, batch, vectors)  # replayed after a crash

    assert await store.committed_chunk_count(document_id) == 3
    async with session_factory() as session:
        document = await session.get(Document, document_id)
        indexes = (
            await session.scalars(select(Chunk.chunk_index).where(Chunk.document_id == document_id))
        ).all()
    assert document is not None
    assert document.processed_chunks == 3
    assert document.total_chunks == 3
    assert sorted(indexes) == [0, 1, 2]


async def test_deleting_document_cascades_to_job(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    document_id = await _add_document(session_factory)
    queue = JobQueue(session_factory, lease_seconds=60)
    job = await queue.claim("w")
    assert job is not None

    async with session_factory() as session:
        document = await session.get(Document, document_id)
        await session.delete(document)
        await session.commit()

    assert await queue.renew_lease(job.id, "w") is False
