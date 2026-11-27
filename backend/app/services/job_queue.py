"""Postgres-backed ingestion job queue.

Claiming uses ``FOR UPDATE SKIP LOCKED`` inside one short statement, then hands
ownership to a time-bound lease. No transaction is held open while a document
is embedded, which keeps this safe behind Supabase's transaction pooler. A job
whose lease expires (worker crashed, instance restarted) becomes claimable again.
"""

import uuid
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import Update, and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import Document, DocumentStatus, IngestionJob, IngestionJobStatus

_MAX_ERROR_LENGTH = 1000


@dataclass(frozen=True, slots=True)
class ClaimedJob:
    id: uuid.UUID
    document_id: uuid.UUID
    attempts: int


def enqueue_ingestion(session: AsyncSession, document_id: uuid.UUID, pdf_bytes: bytes) -> None:
    """Add a job in the caller's transaction so it commits atomically with its document."""
    session.add(IngestionJob(document_id=document_id, pdf_bytes=pdf_bytes))


class JobQueue:
    def __init__(
        self, session_factory: async_sessionmaker[AsyncSession], *, lease_seconds: int
    ) -> None:
        self._session_factory = session_factory
        self._lease = timedelta(seconds=lease_seconds)

    async def claim(self, worker_id: str) -> ClaimedJob | None:
        """Atomically take the oldest runnable job (queued and due, or lease expired)."""
        candidate = (
            select(IngestionJob.id)
            .where(
                or_(
                    and_(
                        IngestionJob.status == IngestionJobStatus.queued,
                        IngestionJob.next_run_at <= func.now(),
                    ),
                    and_(
                        IngestionJob.status == IngestionJobStatus.running,
                        IngestionJob.lease_expires_at < func.now(),
                    ),
                )
            )
            .order_by(IngestionJob.next_run_at)
            .limit(1)
            .with_for_update(skip_locked=True)
            .scalar_subquery()
        )
        stmt = (
            update(IngestionJob)
            .where(IngestionJob.id == candidate)
            .values(
                status=IngestionJobStatus.running,
                lease_owner=worker_id,
                lease_expires_at=func.now() + self._lease,
                # Counted on claim so a PDF that crashes the process can't loop forever.
                attempts=IngestionJob.attempts + 1,
            )
            .returning(IngestionJob.id, IngestionJob.document_id, IngestionJob.attempts)
            .execution_options(synchronize_session=False)
        )
        async with self._session_factory() as session:
            row = (await session.execute(stmt)).one_or_none()
            await session.commit()
        if row is None:
            return None
        return ClaimedJob(id=row.id, document_id=row.document_id, attempts=row.attempts)

    async def load_pdf(self, job_id: uuid.UUID) -> bytes | None:
        async with self._session_factory() as session:
            data: bytes | None = await session.scalar(
                select(IngestionJob.pdf_bytes).where(IngestionJob.id == job_id)
            )
            return data

    async def renew_lease(self, job_id: uuid.UUID, worker_id: str) -> bool:
        """Extend the lease. False means ownership was lost (reclaimed or job deleted)."""
        return await self._update_owned(
            job_id, worker_id, lease_expires_at=func.now() + self._lease
        )

    async def complete(self, job_id: uuid.UUID, worker_id: str) -> None:
        await self._update_owned(
            job_id,
            worker_id,
            status=IngestionJobStatus.succeeded,
            pdf_bytes=None,
            lease_owner=None,
            lease_expires_at=None,
            last_error=None,
        )

    async def reschedule(
        self,
        job_id: uuid.UUID,
        worker_id: str,
        *,
        delay_seconds: float,
        refund_attempt: bool,
        error: str | None = None,
    ) -> None:
        """Return the job to the queue. ``refund_attempt`` for waits that are not failures
        (rate limits, graceful shutdown)."""
        values: dict[str, object] = {
            "status": IngestionJobStatus.queued,
            "lease_owner": None,
            "lease_expires_at": None,
            "next_run_at": func.now() + timedelta(seconds=delay_seconds),
            "last_error": _truncate(error),
        }
        if refund_attempt:
            values["attempts"] = func.greatest(IngestionJob.attempts - 1, 0)
        await self._update_owned(job_id, worker_id, **values)

    async def fail(
        self,
        job: ClaimedJob,
        worker_id: str,
        *,
        user_message: str,
        error: str | None = None,
    ) -> None:
        """Terminal failure: drop the stored PDF and surface ``user_message`` on the document."""
        async with self._session_factory() as session:
            result = await session.execute(
                _owned(job.id, worker_id)
                .values(
                    status=IngestionJobStatus.failed,
                    pdf_bytes=None,
                    lease_owner=None,
                    lease_expires_at=None,
                    last_error=_truncate(error or user_message),
                )
                .execution_options(synchronize_session=False)
            )
            if _rowcount(result) == 1:
                await session.execute(
                    update(Document)
                    .where(Document.id == job.document_id)
                    .values(status=DocumentStatus.failed, error_message=user_message)
                )
            await session.commit()

    async def _update_owned(self, job_id: uuid.UUID, worker_id: str, **values: object) -> bool:
        async with self._session_factory() as session:
            result = await session.execute(
                _owned(job_id, worker_id)
                .values(**values)
                .execution_options(synchronize_session=False)
            )
            await session.commit()
        return _rowcount(result) == 1


def _owned(job_id: uuid.UUID, worker_id: str) -> Update:
    """UPDATE restricted to a running job this worker still owns (fencing)."""
    return update(IngestionJob).where(
        IngestionJob.id == job_id,
        IngestionJob.status == IngestionJobStatus.running,
        IngestionJob.lease_owner == worker_id,
    )


def _rowcount(result: object) -> int:
    return int(getattr(result, "rowcount", 0) or 0)


def _truncate(text: str | None) -> str | None:
    return text[:_MAX_ERROR_LENGTH] if text else text
