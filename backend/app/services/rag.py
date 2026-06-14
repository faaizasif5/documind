import json
import logging
import uuid
from collections.abc import AsyncIterator, Sequence

from app.schemas.chat import Source
from app.services.providers.base import CompletionProvider
from app.services.retrieval import RetrievedChunk

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are DocuMind, an assistant that answers questions about the user's uploaded "
    "documents. Answer using ONLY the information in the provided context. Cite the "
    "sources you rely on inline using their numbers, e.g. [Source 1]. If the context "
    "does not contain the answer, say you don't know based on the provided documents. "
    "Never invent information that is not in the context."
)

NO_CONTEXT_MESSAGE = "I couldn't find anything relevant in the uploaded documents to answer that."
STREAM_ERROR_MESSAGE = "The answer stream was interrupted by an upstream error."


def build_user_prompt(question: str, chunks: Sequence[RetrievedChunk]) -> str:
    """Assemble the context + question prompt with numbered, cited source blocks."""
    blocks = [
        f"[Source {index}: {chunk.filename}, page {chunk.page_number}]\n{chunk.content}"
        for index, chunk in enumerate(chunks, start=1)
    ]
    context = "\n\n".join(blocks)
    return f"Context:\n{context}\n\nQuestion: {question}"


def dedupe_sources(chunks: Sequence[RetrievedChunk]) -> list[Source]:
    """Collapse retrieved chunks into unique (document, page) citations, in order."""
    seen: set[tuple[uuid.UUID, int]] = set()
    sources: list[Source] = []
    for chunk in chunks:
        key = (chunk.document_id, chunk.page_number)
        if key in seen:
            continue
        seen.add(key)
        sources.append(
            Source(
                document_id=chunk.document_id,
                filename=chunk.filename,
                page_number=chunk.page_number,
            )
        )
    return sources


def _sse(event: str, data: object) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


async def stream_chat_response(
    provider: CompletionProvider,
    question: str,
    chunks: Sequence[RetrievedChunk],
) -> AsyncIterator[str]:
    """Yield Server-Sent Events: answer tokens, then citations, then a done marker."""
    if not chunks:
        yield _sse("token", {"text": NO_CONTEXT_MESSAGE})
        yield _sse("sources", [])
        yield _sse("done", {})
        return

    user_prompt = build_user_prompt(question, chunks)
    try:
        async for delta in provider.stream_completion(SYSTEM_PROMPT, user_prompt):
            yield _sse("token", {"text": delta})
    except Exception:
        # The HTTP status is already sent, so signal the failure in-band and stop.
        logger.exception("Completion stream failed")
        yield _sse("error", {"message": STREAM_ERROR_MESSAGE})
        yield _sse("done", {})
        return

    sources = [source.model_dump(mode="json") for source in dedupe_sources(chunks)]
    yield _sse("sources", sources)
    yield _sse("done", {})
