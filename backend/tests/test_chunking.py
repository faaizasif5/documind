from app.services.chunking import chunk_page_text


def test_empty_text_returns_no_chunks() -> None:
    assert chunk_page_text("   \n  ") == []


def test_long_text_splits_into_multiple_chunks() -> None:
    text = "Retrieval augmented generation is useful. " * 200
    chunks = chunk_page_text(text)

    assert len(chunks) > 1
    assert all(chunk.strip() for chunk in chunks)


def test_short_text_returns_single_chunk() -> None:
    chunks = chunk_page_text("A short sentence about documents.")

    assert chunks == ["A short sentence about documents."]
