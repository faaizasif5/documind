"""Eval runner end-to-end against real Postgres+pgvector (skipped without TEST_DATABASE_URL).

Loads a tiny corpus through production ingestion and searches it with production
retrieval, using keyword one-hot embeddings so the expected ranking is known.
"""

import os
from collections.abc import AsyncIterator
from pathlib import Path

import fitz
import pytest
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.db.base import Base
from app.models import Chunk
from evals.metrics import summarize_retrieval
from evals.runner import eval_document_id, load_corpus, reset_corpus, run_retrieval
from evals.schema import CorpusManifest, Evidence, GoldenItem, sha256_file

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not TEST_DATABASE_URL, reason="TEST_DATABASE_URL not set")

_WORDS = ["alpha", "beta", "gamma", "delta"]


class _KeywordEmbedder:
    """Vector = one-hot over the keywords present: cosine ranks pages by shared words."""

    def _vector(self, text: str) -> list[float]:
        vector = [0.0] * 1536
        for index, word in enumerate(_WORDS):
            if word in text.lower():
                vector[index] = 1.0
        vector[1535] = 0.01  # avoid zero vectors (cosine undefined)
        return vector

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(t) for t in texts]

    async def embed_query(self, text: str) -> list[float]:
        return self._vector(text)


@pytest.fixture
async def factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    assert TEST_DATABASE_URL is not None
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


def _corpus(tmp_path: Path) -> CorpusManifest:
    pdf = fitz.open()
    for page_text in ["alpha facts here", "beta facts here", "gamma facts here"]:
        pdf.new_page().insert_text((72, 72), page_text)
    path = tmp_path / "doc.pdf"
    pdf.save(path)
    pdf.close()
    return CorpusManifest.model_validate(
        {
            "documents": [
                {
                    "filename": "doc.pdf",
                    "title": "Doc",
                    "source_url": "https://example.gov/doc.pdf",
                    "license": "Public domain",
                    "sha256": sha256_file(path),
                    "page_count": 3,
                }
            ]
        }
    )


def _q(item_id: str, question: str, page: int) -> GoldenItem:
    return GoldenItem(
        id=item_id,
        question=question,
        tag="lookup",
        evidence=[Evidence(filename="doc.pdf", page=page)],
        reference_answer="x",
    )


async def test_load_corpus_is_idempotent_and_retrieval_scores(
    factory: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    manifest = _corpus(tmp_path)
    embedder = _KeywordEmbedder()
    settings = get_settings()

    first = await load_corpus(factory, embedder, manifest, tmp_path, settings)
    second = await load_corpus(factory, embedder, manifest, tmp_path, settings)

    assert first == second == {"doc.pdf": 3}
    async with factory() as session:
        count = await session.scalar(
            select(func.count())
            .select_from(Chunk)
            .where(Chunk.document_id == eval_document_id("doc.pdf"))
        )
    assert count == 3

    records = await run_retrieval(
        factory,
        embedder,
        [_q("q1", "tell me about beta", 2), _q("q2", "what is gamma", 3)],
        ks=(1, 3),
    )
    summary = summarize_retrieval([r.score for r in records], ks=(1, 3))

    assert summary["overall"]["recall@1"] == 1.0
    assert summary["overall"]["mrr"] == 1.0
    assert records[0].retrieved[0] == ("doc.pdf", 2)


async def test_reset_corpus_removes_eval_documents(
    factory: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    manifest = _corpus(tmp_path)
    await load_corpus(factory, _KeywordEmbedder(), manifest, tmp_path, get_settings())

    await reset_corpus(factory)

    async with factory() as session:
        assert await session.scalar(select(func.count()).select_from(Chunk)) == 0
