import uuid

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    top_k: int = Field(default=5, ge=1, le=20)
    document_id: uuid.UUID | None = None


class Source(BaseModel):
    """A citation the answer can reference; `number` matches the inline [Source N] marker."""

    number: int = Field(ge=1)
    document_id: uuid.UUID
    filename: str
    page_number: int
