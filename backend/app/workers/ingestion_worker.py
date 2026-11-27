"""Background worker that drains the Postgres ingestion queue.

Runs one job at a time inside the API process (started from the FastAPI
lifespan). One job at a time is deliberate: the embedding quota is the
bottleneck, and Render's free instance has little RAM to spare.
"""

import asyncio
import logging
import os
import socket
import uuid
from collections.abc import Awaitable, Callable
from contextlib import suppress
from typing import Protocol, TypeVar

from app.core.config import Settings
from app.core.exceptions import ProviderRateLimitError
from app.db.session import AsyncSessionLocal
from app.services.ingestion import ChunkStore, IngestionError, PostgresChunkStore, ingest_document
from app.services.job_queue import ClaimedJob, JobQueue
from app.services.providers.base import EmbeddingProvider
from app.services.providers.factory import get_embedding_provider

logger = logging.getLogger(__name__)

_T = TypeVar("_T")

_RATE_LIMIT_FALLBACK_SECONDS = 60.0
_DAILY_QUOTA_FALLBACK_SECONDS = 3600.0
_REPEATED_CRASH_MESSAGE = "Processing failed repeatedly. Please upload the file again."
_MISSING_FILE_MESSAGE = "The uploaded file is no longer available. Please upload it again."


class IngestionQueue(Protocol):
    async def claim(self, worker_id: str) -> ClaimedJob | None: ...

    async def load_pdf(self, job_id: uuid.UUID) -> bytes | None: ...

    async def renew_lease(self, job_id: uuid.UUID, worker_id: str) -> bool: ...

    async def complete(self, job_id: uuid.UUID, worker_id: str) -> None: ...

    async def reschedule(
        self,
        job_id: uuid.UUID,
        worker_id: str,
        *,
        delay_seconds: float,
        refund_attempt: bool,
        error: str | None = None,
    ) -> None: ...

    async def fail(
        self,
        job: ClaimedJob,
        worker_id: str,
        *,
        user_message: str,
        error: str | None = None,
    ) -> None: ...


class LeaseLostError(Exception):
    """Another worker reclaimed the job, or the job (and its document) was deleted."""


def _default_worker_id() -> str:
    return f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex[:8]}"[:64]


class IngestionWorker:
    def __init__(
        self,
        *,
        queue: IngestionQueue,
        store: ChunkStore,
        provider_factory: Callable[[], EmbeddingProvider],
        settings: Settings,
        worker_id: str | None = None,
    ) -> None:
        self._queue = queue
        self._store = store
        self._provider_factory = provider_factory
        self._batch_size = settings.embedding_batch_size
        self._max_chunks = settings.max_chunks_per_document
        self._poll_interval = settings.ingestion_poll_interval_seconds
        self._heartbeat_interval = settings.ingestion_lease_seconds / 3
        self._max_attempts = settings.ingestion_max_attempts
        self._retry_backoff = settings.ingestion_retry_backoff_seconds
        self.worker_id = worker_id or _default_worker_id()
        self._stopping = asyncio.Event()
        self._task: asyncio.Task[None] | None = None

    def start(self) -> None:
        self._task = asyncio.create_task(self._run(), name="ingestion-worker")

    async def stop(self) -> None:
        self._stopping.set()
        if self._task is not None:
            self._task.cancel()
            with suppress(asyncio.CancelledError):
                await self._task

    async def _run(self) -> None:
        logger.info("Ingestion worker %s started", self.worker_id)
        while not self._stopping.is_set():
            try:
                handled = await self.run_once()
            except Exception:
                # A DB blip must not kill the loop; back off and try again.
                logger.exception("Ingestion worker iteration failed")
                handled = False
            if not handled:
                with suppress(TimeoutError):
                    await asyncio.wait_for(self._stopping.wait(), timeout=self._poll_interval)

    async def run_once(self) -> bool:
        """Claim and process at most one job. Returns False when the queue was empty."""
        job = await self._queue.claim(self.worker_id)
        if job is None:
            return False
        await self._process(job)
        return True

    async def _process(self, job: ClaimedJob) -> None:
        if job.attempts > self._max_attempts:
            # Only reachable via lease expiry, i.e. the process died mid-job repeatedly.
            await self._queue.fail(
                job,
                self.worker_id,
                user_message=_REPEATED_CRASH_MESSAGE,
                error="max attempts exceeded via lease expiry",
            )
            return

        pdf_bytes = await self._queue.load_pdf(job.id)
        if pdf_bytes is None:
            await self._queue.fail(job, self.worker_id, user_message=_MISSING_FILE_MESSAGE)
            return

        try:
            await self._with_lease(
                job.id,
                ingest_document(
                    job.document_id,
                    pdf_bytes,
                    self._provider_factory(),
                    self._store,
                    self._batch_size,
                    self._max_chunks,
                ),
            )
        except asyncio.CancelledError:
            # Graceful shutdown/redeploy: hand the job straight back without using an attempt.
            await asyncio.shield(
                self._queue.reschedule(job.id, self.worker_id, delay_seconds=0, refund_attempt=True)
            )
            raise
        except LeaseLostError:
            logger.warning("Lost lease on job %s; abandoning it", job.id)
        except IngestionError as exc:
            await self._queue.fail(job, self.worker_id, user_message=exc.user_message)
        except ProviderRateLimitError as exc:
            await self._on_rate_limited(job, exc)
        except Exception as exc:
            logger.exception("Ingestion job %s failed (attempt %d)", job.id, job.attempts)
            await self._on_transient_error(job, exc)
        else:
            await self._queue.complete(job.id, self.worker_id)

    async def _on_rate_limited(self, job: ClaimedJob, exc: ProviderRateLimitError) -> None:
        fallback = (
            _DAILY_QUOTA_FALLBACK_SECONDS if exc.daily_quota else _RATE_LIMIT_FALLBACK_SECONDS
        )
        delay = exc.retry_after_seconds or fallback
        logger.warning(
            "Job %s rate limited (daily=%s); resuming in %.0fs", job.id, exc.daily_quota, delay
        )
        # Waiting for quota is not a failure: progress is kept and the attempt refunded.
        await self._queue.reschedule(
            job.id, self.worker_id, delay_seconds=delay, refund_attempt=True, error=str(exc)
        )

    async def _on_transient_error(self, job: ClaimedJob, exc: Exception) -> None:
        if job.attempts >= self._max_attempts:
            await self._queue.fail(
                job,
                self.worker_id,
                user_message=(
                    f"Processing failed after {job.attempts} attempts. Please try again later."
                ),
                error=repr(exc),
            )
            return
        delay = self._retry_backoff * 2 ** (job.attempts - 1)
        await self._queue.reschedule(
            job.id, self.worker_id, delay_seconds=delay, refund_attempt=False, error=repr(exc)
        )

    async def _with_lease(self, job_id: uuid.UUID, work: Awaitable[_T]) -> _T:
        """Run ``work`` while renewing the job lease; cancel it if the lease is lost."""
        task = asyncio.ensure_future(work)
        try:
            while True:
                done, _ = await asyncio.wait({task}, timeout=self._heartbeat_interval)
                if task in done:
                    return task.result()
                if not await self._queue.renew_lease(job_id, self.worker_id):
                    raise LeaseLostError
        finally:
            if not task.done():
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task


def build_ingestion_worker(settings: Settings) -> IngestionWorker:
    return IngestionWorker(
        queue=JobQueue(AsyncSessionLocal, lease_seconds=settings.ingestion_lease_seconds),
        store=PostgresChunkStore(AsyncSessionLocal),
        provider_factory=lambda: get_embedding_provider(settings),
        settings=settings,
    )
