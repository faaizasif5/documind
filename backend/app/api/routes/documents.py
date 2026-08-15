import uuid
from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUserDep
from app.core.config import Settings, get_settings
from app.db.session import get_db_session
from app.models import Document, DocumentStatus
from app.schemas.document import DocumentResponse
from app.schemas.errors import ErrorResponse
from app.services import pdf_extraction
from app.services.ingestion import process_document

router = APIRouter(prefix="/documents", tags=["documents"])

DbSession = Annotated[AsyncSession, Depends(get_db_session)]
AppSettings = Annotated[Settings, Depends(get_settings)]

_AUTH_ERROR: dict[int | str, dict[str, type[ErrorResponse]]] = {401: {"model": ErrorResponse}}
_NOT_FOUND_ERROR: dict[int | str, dict[str, type[ErrorResponse]]] = {
    401: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
}
_UPLOAD_ERRORS: dict[int | str, dict[str, type[ErrorResponse]]] = {
    400: {"model": ErrorResponse},
    401: {"model": ErrorResponse},
    413: {"model": ErrorResponse},
    415: {"model": ErrorResponse},
    422: {"model": ErrorResponse},
}


def _owned_or_404(document: Document | None, user_id: uuid.UUID) -> Document:
    """Return the document only if it belongs to ``user_id``; otherwise 404.

    Cross-user access intentionally looks identical to a missing document so we
    do not leak existence across tenants.
    """
    if document is None or document.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return document


@router.post(
    "",
    response_model=DocumentResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses=_UPLOAD_ERRORS,
)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile,
    session: DbSession,
    settings: AppSettings,
    user: CurrentUserDep,
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
        user_id=user.id,
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


@router.get(
    "",
    response_model=list[DocumentResponse],
    responses=_AUTH_ERROR,
)
async def list_documents(session: DbSession, user: CurrentUserDep) -> Sequence[Document]:
    result = await session.execute(
        select(Document).where(Document.user_id == user.id).order_by(Document.created_at.desc())
    )
    return result.scalars().all()


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    responses=_NOT_FOUND_ERROR,
)
async def get_document(
    document_id: uuid.UUID,
    session: DbSession,
    user: CurrentUserDep,
) -> Document:
    document = await session.get(Document, document_id)
    return _owned_or_404(document, user.id)


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=_NOT_FOUND_ERROR,
)
async def delete_document(
    document_id: uuid.UUID,
    session: DbSession,
    user: CurrentUserDep,
) -> None:
    document = await session.get(Document, document_id)
    owned = _owned_or_404(document, user.id)

    # Chunks are removed by the FK ON DELETE CASCADE (passive_deletes=True).
    await session.delete(owned)
    await session.commit()
