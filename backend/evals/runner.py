"""Corpus loading and eval loops, run against a disposable migrated database.

Everything goes through production code: ``ingest_document`` + ``PostgresChunkStore``
to load the corpus and ``retrieve_chunks`` (real pgvector/HNSW SQL) to search it.
"""

import logging
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import delete, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings
from app.models import Document, DocumentStatus
from app.services.ingestion import PostgresChunkStore, ingest_document
from app.services.providers.base import CompletionProvider, EmbeddingProvider
from app.services.rate_limiter import SlidingWindowRateLimiter
from app.services.retrieval import RetrievedChunk, retrieve_chunks
from evals.generation import generate_answer
from evals.judge import Judge, JudgeVerdict
from evals.metrics import (
    DEFAULT_KS,
    AnswerScore,
    PageRef,
    RetrievalScore,
    citation_precision,
    score_retrieval,
)
from evals.schema import CorpusManifest, GoldenItem, sha256_file

logger = logging.getLogger(__name__)

# Fixed tenant that owns the eval corpus; retrieval is user-scoped exactly as in prod.
EVAL_USER_ID = uuid.UUID("00000000-0000-4000-8000-00000000e7a1")
_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}
_ALEMBIC_INI = Path(__file__).resolve().parent.parent / "alembic.ini"


def eval_document_id(filename: str) -> uuid.UUID:
    """Deterministic ids make corpus loading idempotent across runs."""
    return uuid.uuid5(uuid.NAMESPACE_URL, f"documind-eval/{filename}")


def require_disposable_database(url: str, *, allow_remote: bool) -> None:
    host = make_url(url).host or ""
    if host not in _LOCAL_HOSTS and not allow_remote:
        raise SystemExit(
            f"Refusing to run evals against non-local database host {host!r}. Evals write "
            "an eval tenant's documents; point EVAL_DATABASE_URL at a disposable local DB "
            "or pass --allow-remote-db deliberately."
        )


def make_session_factory(url: str) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(url)
    return engine, async_sessionmaker(engine, expire_on_commit=False)


async def require_migrated(factory: async_sessionmaker[AsyncSession]) -> None:
    head = ScriptDirectory.from_config(Config(str(_ALEMBIC_INI))).get_current_head()
    async with factory() as session:
        try:
            current = await session.scalar(text("SELECT version_num FROM alembic_version"))
        except Exception as exc:
            raise SystemExit(
                "Eval database has no schema. Run: "
                "DATABASE_MIGRATION_URL=<eval url> alembic upgrade head"
            ) from exc
    if current != head:
        raise SystemExit(f"Eval database is at migration {current}, expected head {head}")


async def reset_corpus(factory: async_sessionmaker[AsyncSession]) -> None:
    """Drop the eval tenant's documents (chunks and jobs cascade)."""
    async with factory() as session:
        await session.execute(delete(Document).where(Document.user_id == EVAL_USER_ID))
        await session.commit()


async def load_corpus(
    factory: async_sessionmaker[AsyncSession],
    provider: EmbeddingProvider,
    manifest: CorpusManifest,
    corpus_dir: Path,
    settings: Settings,
    *,
    after_document: Callable[[], None] | None = None,
) -> dict[str, int]:
    """Ingest every corpus PDF once; already-ready documents are skipped."""
    chunk_counts: dict[str, int] = {}
    store = PostgresChunkStore(factory)
    for entry in manifest.documents:
        path = corpus_dir / entry.filename
        if sha256_file(path) != entry.sha256:
            raise SystemExit(f"Corpus file {entry.filename} does not match its manifest hash")
        document_id = eval_document_id(entry.filename)
        async with factory() as session:
            existing = await session.get(Document, document_id)
            if existing is not None and existing.status == DocumentStatus.ready:
                chunk_counts[entry.filename] = existing.total_chunks or 0
                continue
            if existing is None:
                session.add(
                    Document(
                        id=document_id,
                        user_id=EVAL_USER_ID,
                        filename=entry.filename,
                        file_size=path.stat().st_size,
                        page_count=entry.page_count,
                        status=DocumentStatus.processing,
                    )
                )
                await session.commit()
        logger.info("Ingesting %s", entry.filename)
        chunk_counts[entry.filename] = await ingest_document(
            document_id,
            path.read_bytes(),
            provider,
            store,
            settings.embedding_batch_size,
            settings.max_chunks_per_document,
        )
        if after_document is not None:
            after_document()
    return chunk_counts


async def _retrieve(
    factory: async_sessionmaker[AsyncSession],
    provider: EmbeddingProvider,
    question: str,
    top_k: int,
) -> list[RetrievedChunk]:
    embedding = await provider.embed_query(question)
    async with factory() as session:
        return await retrieve_chunks(session, embedding, top_k, user_id=EVAL_USER_ID)


def _pages(chunks: Sequence[RetrievedChunk]) -> list[PageRef]:
    return [(chunk.filename, chunk.page_number) for chunk in chunks]


@dataclass(slots=True)
class RetrievalRecord:
    score: RetrievalScore
    expected: list[PageRef]
    retrieved: list[PageRef]


async def run_retrieval(
    factory: async_sessionmaker[AsyncSession],
    provider: EmbeddingProvider,
    items: Sequence[GoldenItem],
    ks: Sequence[int] = DEFAULT_KS,
) -> list[RetrievalRecord]:
    records: list[RetrievalRecord] = []
    for item in items:
        if not item.answerable:
            continue
        retrieved = _pages(await _retrieve(factory, provider, item.question, max(ks)))
        records.append(
            RetrievalRecord(
                score=score_retrieval(item.id, item.tag, item.evidence_pages, retrieved, ks),
                expected=sorted(item.evidence_pages),
                retrieved=retrieved,
            )
        )
    return records


@dataclass(slots=True)
class AnswerRecord:
    score: AnswerScore
    question: str
    answer: str
    cited: list[PageRef]
    retrieved: list[PageRef]
    verdict: JudgeVerdict


async def run_answers(
    factory: async_sessionmaker[AsyncSession],
    embedder: EmbeddingProvider,
    completion: CompletionProvider,
    judge: Judge,
    items: Sequence[GoldenItem],
    generation_limiter: SlidingWindowRateLimiter,
    *,
    top_k: int,
    max_attempts: int,
    after_item: Callable[[], None] | None = None,
) -> list[AnswerRecord]:
    records: list[AnswerRecord] = []
    for item in items:
        chunks = await _retrieve(factory, embedder, item.question, top_k)
        generated = await generate_answer(
            completion,
            item.question,
            chunks,
            generation_limiter,
            max_attempts=max_attempts,
        )
        verdict = await judge.evaluate(
            question=item.question,
            reference_answer=item.reference_answer,
            answer=generated.text,
            sources=generated.judge_sources,
        )
        records.append(
            AnswerRecord(
                score=AnswerScore(
                    item_id=item.id,
                    tag=item.tag,
                    answerable=item.answerable,
                    refused=verdict.refused,
                    faithfulness=verdict.faithfulness,
                    correctness=verdict.correctness,
                    citation_precision=(
                        citation_precision(generated.cited_pages, item.evidence_pages)
                        if item.answerable
                        else None
                    ),
                ),
                question=item.question,
                answer=generated.text,
                cited=sorted(generated.cited_pages),
                retrieved=_pages(chunks),
                verdict=verdict,
            )
        )
        if after_item is not None:
            after_item()
    return records
