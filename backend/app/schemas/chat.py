import uuid
from typing import Literal

from pydantic import BaseModel, Field


class ChatTurn(BaseModel):
    """One earlier message in the conversation, sent so follow-ups can be understood."""

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=8000)


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    top_k: int = Field(default=5, ge=1, le=20)
    document_id: uuid.UUID | None = None
    history: list[ChatTurn] = Field(default_factory=list, max_length=6)


class Source(BaseModel):
    """A citation the answer can reference; `number` matches the inline [Source N] marker."""

    number: int = Field(ge=1)
    document_id: uuid.UUID
    filename: str
    page_number: int
