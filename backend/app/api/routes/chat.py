from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import ProviderError
from app.db.session import get_db_session
from app.schemas.chat import ChatRequest
from app.schemas.errors import ErrorResponse
from app.services.providers.factory import get_completion_provider, get_embedding_provider
from app.services.rag import stream_chat_response
from app.services.retrieval import retrieve_chunks

router = APIRouter(prefix="/chat", tags=["chat"])

DbSession = Annotated[AsyncSession, Depends(get_db_session)]
AppSettings = Annotated[Settings, Depends(get_settings)]

# Disable proxy/server buffering so tokens reach the client as they stream.
_SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


@router.post("", responses={502: {"model": ErrorResponse}})
async def chat(
    payload: ChatRequest, session: DbSession, settings: AppSettings
) -> StreamingResponse:
    # DB + embedding work happens here (request scope) before streaming starts,
    # so provider failures surface as a proper 502 rather than a broken stream.
    try:
        embedding_provider = get_embedding_provider(settings)
        query_embedding = await embedding_provider.embed_query(payload.question)
    except Exception as exc:
        raise ProviderError("Failed to embed the question") from exc

    chunks = await retrieve_chunks(session, query_embedding, payload.top_k, payload.document_id)

    try:
        completion_provider = get_completion_provider(settings)
    except Exception as exc:
        raise ProviderError("Failed to initialize the completion provider") from exc

    return StreamingResponse(
        stream_chat_response(completion_provider, payload.question, chunks),
        media_type="text/event-stream",
        headers=_SSE_HEADERS,
    )
