import asyncio

import fitz  # PyMuPDF


class PDFExtractionError(Exception):
    """Raised when a PDF cannot be opened or parsed."""


def _open(pdf_bytes: bytes) -> fitz.Document:
    try:
        return fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as exc:  # PyMuPDF raises various low-level errors
        raise PDFExtractionError("Could not open PDF file") from exc


def get_page_count(pdf_bytes: bytes) -> int:
    """Return the number of pages; also validates the bytes are a real PDF."""
    with _open(pdf_bytes) as document:
        return int(document.page_count)


def _extract_pages_sync(pdf_bytes: bytes) -> list[str]:
    with _open(pdf_bytes) as document:
        return [page.get_text() for page in document]


async def extract_pages(pdf_bytes: bytes) -> list[str]:
    """Extract text per page. Runs the blocking parse off the event loop.

    Returns a list where index ``i`` holds the text of page ``i + 1``.
    """
    return await asyncio.to_thread(_extract_pages_sync, pdf_bytes)
