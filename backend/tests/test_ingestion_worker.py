"""Worker outcome handling with a fake queue (no DB, no AI)."""

import asyncio
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

import fitz
import pytest

from app.core.config import Settings
from app.core.exceptions import ProviderRateLimitError
from app.services.ingestion import PendingChunk
from app.services.job_queue import ClaimedJob
from app.workers.ingestion_worker import IngestionWorker


def _pdf() -> bytes:
    document = fitz.open()
    for n in range(3):
        document.new_page().insert_text((72, 72), f"page {n} text")
    data: bytes = document.tobytes()
    document.close()
    return data


@dataclass
class _FakeQueue:
    job: ClaimedJob | None
    pdf: bytes | None = field(default_factory=_pdf)
    lease_ok: bool = True
    events: list[tuple[str, dict[str, Any]]] = field(default_factory=list)

    async def claim(self, worker_id: str) -> ClaimedJob | None:
        job, self.job = self.job, None
        return job

    async def load_pdf(self, job_id: uuid.UUID) -> bytes | None:
        return self.pdf

    async def renew_lease(self, job_id: uuid.UUID, worker_id: str) -> bool:
        self.events.append(("renew", {}))
        return self.lease_ok

    async def complete(self, job_id: uuid.UUID, worker_id: str) -> None:
        self.events.append(("complete", {}))

    async def reschedule(
        self,
        job_id: uuid.UUID,
        worker_id: str,
        *,
        delay_seconds: float,
        refund_attempt: bool,
        error: str | None = None,
    ) -> None:
        self.events.append(
            ("reschedule", {"delay": delay_seconds, "refund": refund_attempt, "error": error})
        )

    async def fail(
        self,
        job: ClaimedJob,
        worker_id: str,
        *,
        user_message: str,
        error: str | None = None,
    ) -> None:
        self.events.append(("fail", {"message": user_message}))


class _Store:
    def __init__(self) -> None:
        self.saved = 0
        self.ready = False

    async def committed_chunk_count(self, document_id: uuid.UUID) -> int:
        return self.saved

    async def set_total_chunks(self, document_id: uuid.UUID, total: int) -> None:
        pass

    async def save_batch(
        self,
        document_id: uuid.UUID,
        chunks: Sequence[PendingChunk],
        embeddings: Sequence[list[float]],
    ) -> None:
        self.saved += len(chunks)

    async def mark_ready(self, document_id: uuid.UUID) -> None:
        self.ready = True


class _Provider:
    def __init__(self, error: Exception | None = None, delay: float = 0.0) -> None:
        self._error = error
        self._delay = delay

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if self._delay:
            await asyncio.sleep(self._delay)
        if self._error is not None:
            raise self._error
        return [[0.0] for _ in texts]

    async def embed_query(self, text: str) -> list[float]:
        return [0.0]


def _settings(**overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "database_url": "postgresql+asyncpg://u:p@localhost:5432/db",
        "ingestion_max_attempts": 3,
        "ingestion_retry_backoff_seconds": 30.0,
        "ingestion_lease_seconds": 120,
    }
    values.update(overrides)
    return Settings(**values)


def _job(attempts: int = 1) -> ClaimedJob:
    return ClaimedJob(id=uuid.uuid4(), document_id=uuid.uuid4(), attempts=attempts)


def _worker(
    queue: _FakeQueue, provider: _Provider | None = None, store: _Store | None = None, **kw: Any
) -> IngestionWorker:
    return IngestionWorker(
        queue=queue,
        store=store or _Store(),
        provider_factory=lambda: provider or _Provider(),
        settings=_settings(**kw),
        worker_id="test-worker",
    )


def _kinds(queue: _FakeQueue) -> list[str]:
    return [kind for kind, _ in queue.events if kind != "renew"]


async def test_empty_queue_returns_false() -> None:
    assert await _worker(_FakeQueue(job=None)).run_once() is False


async def test_success_completes_job() -> None:
    queue = _FakeQueue(job=_job())
    store = _Store()

    assert await _worker(queue, store=store).run_once() is True

    assert _kinds(queue) == ["complete"]
    assert store.ready


async def test_unreadable_pdf_fails_with_user_message() -> None:
    queue = _FakeQueue(job=_job(), pdf=b"not a pdf")

    await _worker(queue).run_once()

    assert queue.events == [("fail", {"message": "Could not read the PDF file."})]


async def test_rate_limit_reschedules_with_server_delay_and_refunds_attempt() -> None:
    queue = _FakeQueue(job=_job())
    provider = _Provider(ProviderRateLimitError(retry_after_seconds=48.0))

    await _worker(queue, provider).run_once()

    assert queue.events == [
        (
            "reschedule",
            {"delay": 48.0, "refund": True, "error": "The AI provider rate limit was exceeded"},
        )
    ]


async def test_daily_quota_without_hint_waits_an_hour() -> None:
    queue = _FakeQueue(job=_job())
    provider = _Provider(ProviderRateLimitError(daily_quota=True))

    await _worker(queue, provider).run_once()

    kind, details = queue.events[0]
    assert kind == "reschedule"
    assert details["delay"] == 3600.0
    assert details["refund"] is True


async def test_transient_error_retries_with_exponential_backoff() -> None:
    queue = _FakeQueue(job=_job(attempts=2))

    await _worker(queue, _Provider(RuntimeError("boom"))).run_once()

    kind, details = queue.events[0]
    assert kind == "reschedule"
    assert details["delay"] == 60.0
    assert details["refund"] is False


async def test_transient_error_on_last_attempt_fails_document() -> None:
    queue = _FakeQueue(job=_job(attempts=3))

    await _worker(queue, _Provider(RuntimeError("boom"))).run_once()

    assert queue.events == [
        ("fail", {"message": "Processing failed after 3 attempts. Please try again later."})
    ]


async def test_job_reclaimed_after_repeated_crashes_is_failed_without_processing() -> None:
    queue = _FakeQueue(job=_job(attempts=4))
    store = _Store()

    await _worker(queue, store=store).run_once()

    assert _kinds(queue) == ["fail"]
    assert store.saved == 0


async def test_missing_pdf_bytes_fails_job() -> None:
    queue = _FakeQueue(job=_job(), pdf=None)

    await _worker(queue).run_once()

    assert _kinds(queue) == ["fail"]


async def test_lost_lease_abandons_job_without_touching_it() -> None:
    queue = _FakeQueue(job=_job(), lease_ok=False)
    # Lease of 0.03 s -> heartbeat every 0.01 s while the provider is still working.
    worker = _worker(queue, _Provider(delay=0.5), ingestion_lease_seconds=1)
    worker._heartbeat_interval = 0.01

    await worker.run_once()

    assert _kinds(queue) == []
    assert ("renew", {}) in queue.events


async def test_shutdown_mid_job_hands_job_back_without_using_attempt() -> None:
    queue = _FakeQueue(job=_job())
    worker = _worker(queue, _Provider(delay=5.0))

    task = asyncio.create_task(worker.run_once())
    await asyncio.sleep(0.05)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert queue.events == [("reschedule", {"delay": 0, "refund": True, "error": None})]


async def test_worker_loop_starts_and_stops_cleanly() -> None:
    queue = _FakeQueue(job=None)
    worker = _worker(queue, ingestion_poll_interval_seconds=0.01)

    worker.start()
    await asyncio.sleep(0.05)
    await worker.stop()

    assert worker._task is not None and worker._task.done()


async def test_oversized_document_fails_with_cap_message() -> None:
    queue = _FakeQueue(job=_job())
    store = _Store()

    await _worker(queue, store=store, max_chunks_per_document=2).run_once()

    kind, details = queue.events[0]
    assert kind == "fail"
    assert "limit is 2 per document" in details["message"]
    assert store.saved == 0
