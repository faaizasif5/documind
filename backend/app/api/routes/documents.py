import uuid
from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.session import get_db_session
from app.models import Document, DocumentStatus
from app.schemas.document import DocumentResponse
from app.services import pdf_extraction
from app.services.ingestion import process_document

router = APIRouter(prefix="/documents", tags=["documents"])

DbSession = Annotated[AsyncSession, Depends(get_db_session)]
AppSettings = Annotated[Settings, Depends(get_settings)]


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile,
    session: DbSession,
    settings: AppSettings,
) -> Document:
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PDF files are supported",
        )

    pdf_bytes = await file.read()
    if len(pdf_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty"
        )
    if len(pdf_bytes) > settings.upload_max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File exceeds the maximum allowed size",
        )

    try:
        page_count = pdf_extraction.get_page_count(pdf_bytes)
    except pdf_extraction.PDFExtractionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not read the PDF file",
        ) from exc

    document = Document(
        filename=file.filename or "untitled.pdf",
        file_size=len(pdf_bytes),
        page_count=page_count,
        status=DocumentStatus.processing,
    )
    session.add(document)
    await session.commit()
    await session.refresh(document)

    # Heavy work (extract/chunk/embed) runs after the response is returned.
    background_tasks.add_task(process_document, document.id, pdf_bytes)
    return document


@router.get("", response_model=list[DocumentResponse])
async def list_documents(session: DbSession) -> Sequence[Document]:
    result = await session.execute(select(Document).order_by(Document.created_at.desc()))
    return result.scalars().all()


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: uuid.UUID, session: DbSession) -> Document:
    document = await session.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return document
