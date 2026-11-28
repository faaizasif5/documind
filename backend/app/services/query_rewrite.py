"""Turn a follow-up question into a standalone search query.

Retrieval embeds only the text it is given, so "Which one of those is in the middle?" finds
nothing useful on its own. One short completion call rewrites it using the recent
conversation ("Which CSF 2.0 Function is shown in the middle of the diagram?"); the rewritten
text is used for search only, while the answer prompt keeps the user's own words.
"""

from collections.abc import Sequence
from typing import Protocol

from app.services.providers.base import CompletionProvider

MAX_HISTORY_TURNS = 6
MAX_TURN_CHARS = 600
_MAX_QUERY_CHARS = 500
_PREFIXES = ("standalone question:", "rewritten question:", "question:")

REWRITE_SYSTEM_PROMPT = (
    "You rewrite the latest user question in a conversation into a standalone search "
    "query. Replace references such as 'it', 'they', 'those' or 'the highest one' with what "
    "they refer to in the conversation, and keep the user's intent and key terms. Do not "
    "answer the question and do not add facts that are not in the conversation. If the "
    "question already stands on its own, return it unchanged. Reply with the rewritten "
    "question only, on a single line."
)


class TurnLike(Protocol):
    @property
    def role(self) -> str: ...

    @property
    def content(self) -> str: ...


def format_history(history: Sequence[TurnLike]) -> str:
    """The last few turns as "User: ..." / "Assistant: ..." lines, each one truncated."""
    lines = []
    for turn in history[-MAX_HISTORY_TURNS:]:
        speaker = "User" if turn.role == "user" else "Assistant"
        text = " ".join(turn.content.split())
        if len(text) > MAX_TURN_CHARS:
            text = text[:MAX_TURN_CHARS].rstrip() + " …"
        lines.append(f"{speaker}: {text}")
    return "\n".join(lines)


def build_rewrite_prompt(question: str, history: Sequence[TurnLike]) -> str:
    return (
        f"Conversation:\n{format_history(history)}\n\n"
        f"Latest question: {question}\n\nStandalone question:"
    )


def clean_rewrite(text: str) -> str | None:
    """First non-empty line, minus labels and wrapping quotes; None if nothing usable."""
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        lowered = line.lower()
        for prefix in _PREFIXES:
            if lowered.startswith(prefix):
                line = line[len(prefix) :].strip()
                break
        line = line.strip("\"'“”` ").strip()
        return line[:_MAX_QUERY_CHARS] or None
    return None


async def rewrite_query(
    provider: CompletionProvider, question: str, history: Sequence[TurnLike]
) -> str:
    """Standalone version of ``question``; the question itself when there is no history.

    Provider errors propagate: the caller decides whether to fall back to the raw question.
    """
    if not history:
        return question
    prompt = build_rewrite_prompt(question, history)
    text = "".join(
        [delta async for delta in provider.stream_completion(REWRITE_SYSTEM_PROMPT, prompt)]
    )
    return clean_rewrite(text) or question
