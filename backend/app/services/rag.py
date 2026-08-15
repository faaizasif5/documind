import json
import logging
import re
import uuid
from collections.abc import AsyncIterator, Sequence

from app.schemas.chat import Source
from app.services.providers.base import CompletionProvider
from app.services.retrieval import RetrievedChunk

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are DocuMind, an assistant that answers questions about the user's uploaded "
    "documents. Answer using ONLY the information in the provided context. Cite the "
    "sources you rely on inline using their numbers, e.g. [Source 1]. When a statement "
    "draws on several sources, cite each one separately, e.g. [Source 1][Source 3]. "
    "Cite only the sources that support the statement. If the context does not contain "
    "the answer, say you don't know based on the provided documents. Never invent "
    "information that is not in the context."
)

NO_CONTEXT_MESSAGE = "I couldn't find anything relevant in the uploaded documents to answer that."
STREAM_ERROR_MESSAGE = "The answer stream was interrupted by an upstream error."

# Models group citations despite the prompt ("[Source 1, Source 2]"), so match the
# whole bracketed reference and pull every number out of it.
CITATION_BLOCK_PATTERN = re.compile(r"\[\s*Sources?\b[^\]]*\]", re.IGNORECASE)
_NUMBER_PATTERN = re.compile(r"\d+")


def build_sources(chunks: Sequence[RetrievedChunk]) -> list[Source]:
    """Collapse retrieved chunks into unique (document, page) citations, in order.

    The assigned numbers are what the prompt shows the model, so the numbers in the
    answer's [Source N] markers always resolve against this list.
    """
    numbers: dict[tuple[uuid.UUID, int], int] = {}
    sources: list[Source] = []
    for chunk in chunks:
        key = (chunk.document_id, chunk.page_number)
        if key in numbers:
            continue
        numbers[key] = len(sources) + 1
        sources.append(
            Source(
                number=numbers[key],
                document_id=chunk.document_id,
                filename=chunk.filename,
                page_number=chunk.page_number,
            )
        )
    return sources


def build_user_prompt(question: str, chunks: Sequence[RetrievedChunk]) -> str:
    """Assemble the context + question prompt with numbered, cited source blocks."""
    numbers = {
        (source.document_id, source.page_number): source.number
        for source in build_sources(chunks)
    }
    blocks = [
        f"[Source {numbers[(chunk.document_id, chunk.page_number)]}: "
        f"{chunk.filename}, page {chunk.page_number}]\n{chunk.content}"
        for chunk in chunks
    ]
    context = "\n\n".join(blocks)
    return f"Context:\n{context}\n\nQuestion: {question}"


def parse_cited_numbers(answer: str) -> set[int]:
    """Collect every source number referenced by the answer's citation markers."""
    return {
        int(number)
        for block in CITATION_BLOCK_PATTERN.findall(answer)
        for number in _NUMBER_PATTERN.findall(block)
    }


def cited_sources(answer: str, sources: Sequence[Source]) -> list[Source]:
    """Narrow retrieved sources to the ones the answer actually cites.

    Retrieval returns top-k passages, but an answer usually leans on a subset;
    listing the rest implies the answer used documents it never touched. If the
    model cited nothing resolvable, fall back to everything so provenance is
    never silently dropped.
    """
    cited = parse_cited_numbers(answer)
    matched = [source for source in sources if source.number in cited]
    return matched or list(sources)


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
    answer_parts: list[str] = []
    try:
        async for delta in provider.stream_completion(SYSTEM_PROMPT, user_prompt):
            answer_parts.append(delta)
            yield _sse("token", {"text": delta})
    except Exception:
        # The HTTP status is already sent, so signal the failure in-band and stop.
        logger.exception("Completion stream failed")
        yield _sse("error", {"message": STREAM_ERROR_MESSAGE})
        yield _sse("done", {})
        return

    # Citations are resolved after streaming because they depend on the full answer.
    sources = [
        source.model_dump(mode="json")
        for source in cited_sources("".join(answer_parts), build_sources(chunks))
    ]
    yield _sse("sources", sources)
    yield _sse("done", {})
