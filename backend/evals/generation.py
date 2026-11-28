"""Answer generation for evals, built from the production RAG pieces.

Uses the same SYSTEM_PROMPT, prompt builder and source numbering as
``app.services.rag.stream_chat_response``, but returns the full text and lets 429s
propagate (the SSE generator turns them into an in-band error event instead).

Generated answers are cached by (model, system prompt, user prompt). The free tier
allows only ~20 generations per day, so a 60-question run has to span several days:
each rerun skips the questions already answered and only spends quota on new ones.
"""

import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from app.services.providers.base import CompletionProvider
from app.services.query_rewrite import TurnLike
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

ANSWER_CACHE_VERSION = "2026-11-28.v1"


def answer_cache_key(model: str, prompt: str) -> str:
    material = "\x1f".join((ANSWER_CACHE_VERSION, model, SYSTEM_PROMPT, prompt))
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


class TextCache:
    """Key → text store saved as JSON lines (generated answers, query rewrites)."""

    def __init__(self, path: Path, answers: dict[str, str] | None = None) -> None:
        self.path = path
        self._answers = answers or {}
        self.dirty = False

    @classmethod
    def load(cls, path: Path) -> "TextCache":
        answers: dict[str, str] = {}
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    record = json.loads(line)
                    answers[record["k"]] = record["text"]
        return cls(path, answers)

    def get(self, key: str) -> str | None:
        return self._answers.get(key)

    def put(self, key: str, text: str) -> None:
        self._answers[key] = text
        self.dirty = True

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        lines = "".join(
            json.dumps({"k": key, "text": self._answers[key]}) + "\n"
            for key in sorted(self._answers)
        )
        self.path.write_text(lines, encoding="utf-8")
        self.dirty = False


@dataclass(frozen=True, slots=True)
class GeneratedAnswer:
    text: str
    cited_pages: set[PageRef]
    # (label, text) blocks exactly as numbered in the prompt, for the judge.
    judge_sources: list[tuple[str, str]]
    from_cache: bool = False


async def generate_answer(
    provider: CompletionProvider,
    question: str,
    chunks: Sequence[RetrievedChunk],
    limiter: SlidingWindowRateLimiter,
    cache: TextCache,
    *,
    model: str,
    max_attempts: int,
    history: Sequence[TurnLike] = (),
) -> GeneratedAnswer:
    if not chunks:
        return GeneratedAnswer(text=NO_CONTEXT_MESSAGE, cited_pages=set(), judge_sources=[])

    prompt = build_user_prompt(question, chunks, history)
    key = answer_cache_key(model, prompt)
    text = cache.get(key)
    from_cache = text is not None
    if text is None:

        async def attempt() -> str:
            return "".join(
                [delta async for delta in provider.stream_completion(SYSTEM_PROMPT, prompt)]
            )

        text = await call_with_limits(attempt, limiter, max_attempts=max_attempts)
        cache.put(key, text)

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
        from_cache=from_cache,
    )
