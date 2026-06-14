import logging
import uuid
from dataclasses import dataclass

from app.core.config import get_settings
from app.db.session import AsyncSessionLocal
from app.models import Chunk, Document, DocumentStatus
from app.services.chunking import chunk_page_text
from app.services.pdf_extraction import extract_pages
from app.services.providers.base import EmbeddingProvider
from app.services.providers.factory import get_embedding_provider

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class _PendingChunk:
    page_number: int
    chunk_index: int
    content: str


def _build_pending_chunks(pages: list[str]) -> list[_PendingChunk]:
    """Chunk each page independently so every chunk keeps an exact page number."""
    pending: list[_PendingChunk] = []
    chunk_index = 0
    for page_offset, page_text in enumerate(pages):
        for content in chunk_page_text(page_text):
            pending.append(
                _PendingChunk(
                    page_number=page_offset + 1,
                    chunk_index=chunk_index,
                    content=content,
                )
            )
            chunk_index += 1
    return pending


async def _embed_in_batches(
    provider: EmbeddingProvider, texts: list[str], batch_size: int
) -> list[list[float]]:
    embeddings: list[list[float]] = []
    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]
        embeddings.extend(await provider.embed_documents(batch))
    return embeddings


async def _mark_failed(document_id: uuid.UUID) -> None:
    async with AsyncSessionLocal() as session:
        document = await session.get(Document, document_id)
        if document is not None:
            document.status = DocumentStatus.failed
            await session.commit()


async def process_document(document_id: uuid.UUID, pdf_bytes: bytes) -> None:
    """Background task: extract, chunk, embed, and persist a document's chunks.

    Opens its own DB session because the request-scoped session is already
    closed by the time this runs after the HTTP response.
    """
    settings = get_settings()
    try:
        provider = get_embedding_provider(settings)
        pages = await extract_pages(pdf_bytes)
        pending = _build_pending_chunks(pages)

        if not pending:
            logger.warning("Document %s produced no extractable text", document_id)
            await _mark_failed(document_id)
            return

        embeddings = await _embed_in_batches(
            provider, [item.content for item in pending], settings.embedding_batch_size
        )

        async with AsyncSessionLocal() as session:
            session.add_all(
                [
                    Chunk(
                        document_id=document_id,
                        content=item.content,
                        page_number=item.page_number,
                        chunk_index=item.chunk_index,
                        embedding=embedding,
                    )
                    for item, embedding in zip(pending, embeddings, strict=True)
                ]
            )
            document = await session.get(Document, document_id)
            if document is not None:
                document.status = DocumentStatus.ready
            await session.commit()

        logger.info("Document %s processed: %d chunks", document_id, len(pending))
    except Exception:
        logger.exception("Failed to process document %s", document_id)
        await _mark_failed(document_id)
