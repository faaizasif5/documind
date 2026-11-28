import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUserDep
from app.core.config import Settings, get_settings
from app.core.exceptions import ProviderError
from app.db.session import get_db_session
from app.models import Document
from app.schemas.chat import ChatRequest
from app.schemas.errors import ErrorResponse
from app.services.providers.base import CompletionProvider
from app.services.providers.factory import get_completion_provider, get_embedding_provider
from app.services.query_rewrite import rewrite_query
from app.services.rag import stream_chat_response
from app.services.retrieval import retrieve_chunks

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

DbSession = Annotated[AsyncSession, Depends(get_db_session)]
AppSettings = Annotated[Settings, Depends(get_settings)]

# Disable proxy/server buffering so tokens reach the client as they stream.
_SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}

_CHAT_ERRORS: dict[int | str, dict[str, type[ErrorResponse]]] = {
    401: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
    502: {"model": ErrorResponse},
}


async def _require_owned_document(
    session: AsyncSession,
    document_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Document:
    """Load ``document_id`` if it belongs to ``user_id``; otherwise 404 (not 403)."""
    document = await session.get(Document, document_id)
    if document is None or document.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    return document


@router.post("", responses=_CHAT_ERRORS)
async def chat(
    payload: ChatRequest,
    session: DbSession,
    settings: AppSettings,
    user: CurrentUserDep,
) -> StreamingResponse:
    # Optional document scope: reject cross-user IDs before any embedding work.
    if payload.document_id is not None:
        await _require_owned_document(session, payload.document_id, user.id)

    try:
        completion_provider = get_completion_provider(settings)
    except Exception as exc:
        raise ProviderError("Failed to initialize the completion provider") from exc

    search_query = await _standalone_query(completion_provider, payload)

    # DB + embedding work happens here (request scope) before streaming starts,
    # so provider failures surface as a proper 502 rather than a broken stream.
    try:
        embedding_provider = get_embedding_provider(settings)
        query_embedding = await embedding_provider.embed_query(search_query)
    except Exception as exc:
        raise ProviderError("Failed to embed the question") from exc

    chunks = await retrieve_chunks(
        session,
        query_embedding,
        payload.top_k,
        user_id=user.id,
        document_id=payload.document_id,
    )

    return StreamingResponse(
        stream_chat_response(
            completion_provider,
            payload.question,
            chunks,
            history=payload.history,
            search_query=search_query,
        ),
        media_type="text/event-stream",
        headers=_SSE_HEADERS,
    )


async def _standalone_query(provider: CompletionProvider, payload: ChatRequest) -> str:
    """Rewrite a follow-up for search; on any failure, search with the question as asked.

    A failed rewrite only makes retrieval a little worse, so it must never fail the chat.
    """
    try:
        return await rewrite_query(provider, payload.question, payload.history)
    except Exception:
        logger.warning("Query rewrite failed; searching with the raw question", exc_info=True)
        return payload.question
