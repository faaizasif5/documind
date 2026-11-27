import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.document import DocumentStatus


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    filename: str
    file_size: int
    page_count: int
    status: DocumentStatus
    processed_chunks: int
    total_chunks: int | None
    error_message: str | None
    created_at: datetime
