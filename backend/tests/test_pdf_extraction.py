import fitz
import pytest

from app.services.pdf_extraction import PDFExtractionError, extract_pages, get_page_count


def _make_pdf(pages_text: list[str]) -> bytes:
    document = fitz.open()
    for text in pages_text:
        page = document.new_page()
        page.insert_text((72, 72), text)
    pdf_bytes: bytes = document.tobytes()
    document.close()
    return pdf_bytes


async def test_extract_pages_returns_text_per_page() -> None:
    pdf_bytes = _make_pdf(["Hello DocuMind", "Second page content"])

    pages = await extract_pages(pdf_bytes)

    assert len(pages) == 2
    assert "Hello DocuMind" in pages[0]
    assert "Second page content" in pages[1]


def test_get_page_count() -> None:
    pdf_bytes = _make_pdf(["a", "b", "c"])

    assert get_page_count(pdf_bytes) == 3


def test_invalid_pdf_raises() -> None:
    with pytest.raises(PDFExtractionError):
        get_page_count(b"this is not a pdf")
