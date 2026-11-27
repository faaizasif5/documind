"""Answer generation for evals, built from the production RAG pieces.

Uses the same SYSTEM_PROMPT, prompt builder and source numbering as
``app.services.rag.stream_chat_response``, but returns the full text and lets 429s
propagate (the SSE generator turns them into an in-band error event instead).
"""

from collections.abc import Sequence
from dataclasses import dataclass

from app.services.providers.base import CompletionProvider
from app.services.rag import (
    NO_CONTEXT_MESSAGE,
    SYSTEM_PROMPT,
    build_sources,
    build_user_prompt,
    parse_cited_numbers,
)
from app.services.rate_limiter import SlidingWindowRateLimiter
from app.services.retrieval import RetrievedChunk
from evals.metrics import PageRef
from evals.throttle import call_with_limits


@dataclass(frozen=True, slots=True)
class GeneratedAnswer:
    text: str
    cited_pages: set[PageRef]
    # (label, text) blocks exactly as numbered in the prompt, for the judge.
    judge_sources: list[tuple[str, str]]


async def generate_answer(
    provider: CompletionProvider,
    question: str,
    chunks: Sequence[RetrievedChunk],
    limiter: SlidingWindowRateLimiter,
    *,
    max_attempts: int,
) -> GeneratedAnswer:
    if not chunks:
        return GeneratedAnswer(text=NO_CONTEXT_MESSAGE, cited_pages=set(), judge_sources=[])

    prompt = build_user_prompt(question, chunks)

    async def attempt() -> str:
        return "".join([delta async for delta in provider.stream_completion(SYSTEM_PROMPT, prompt)])

    text = await call_with_limits(attempt, limiter, max_attempts=max_attempts)

    sources = build_sources(chunks)
    numbers = {(source.document_id, source.page_number): source.number for source in sources}
    cited = parse_cited_numbers(text)
    return GeneratedAnswer(
        text=text,
        cited_pages={
            (source.filename, source.page_number) for source in sources if source.number in cited
        },
        judge_sources=[
            (
                f"Source {numbers[(chunk.document_id, chunk.page_number)]}: "
                f"{chunk.filename}, page {chunk.page_number}",
                chunk.content,
            )
            for chunk in chunks
        ],
    )
