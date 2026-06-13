import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Chunk, Document


@dataclass(slots=True)
class RetrievedChunk:
    document_id: uuid.UUID
    filename: str
    page_number: int
    chunk_index: int
    content: str


async def retrieve_chunks(
    session: AsyncSession,
    query_embedding: list[float],
    top_k: int,
    document_id: uuid.UUID | None = None,
) -> list[RetrievedChunk]:
    """Return the ``top_k`` chunks most similar to the query embedding (cosine)."""
    stmt = select(Chunk, Document.filename).join(Document, Chunk.document_id == Document.id)
    if document_id is not None:
        stmt = stmt.where(Chunk.document_id == document_id)
    stmt = stmt.order_by(Chunk.embedding.cosine_distance(query_embedding)).limit(top_k)

    result = await session.execute(stmt)
    return [
        RetrievedChunk(
            document_id=chunk.document_id,
            filename=filename,
            page_number=chunk.page_number,
            chunk_index=chunk.chunk_index,
            content=chunk.content,
        )
        for chunk, filename in result.tuples().all()
    ]
