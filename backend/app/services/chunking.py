from functools import lru_cache

import tiktoken
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import get_settings

# text-embedding-3-small and Gemini both tokenize differently, but cl100k_base
# is a good, fast approximation for sizing chunks by tokens rather than characters.
_TOKEN_ENCODING = "cl100k_base"


@lru_cache
def _get_splitter() -> RecursiveCharacterTextSplitter:
    settings = get_settings()
    return RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        encoding_name=_TOKEN_ENCODING,
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )


@lru_cache
def _get_encoding() -> tiktoken.Encoding:
    return tiktoken.get_encoding(_TOKEN_ENCODING)


def count_tokens(texts: list[str]) -> int:
    """Approximate token count, used to stay under provider tokens-per-minute quotas."""
    encoding = _get_encoding()
    return sum(len(encoding.encode(text)) for text in texts)


def chunk_page_text(text: str) -> list[str]:
    """Split a single page's text into token-sized, non-empty chunks."""
    if not text.strip():
        return []
    pieces = _get_splitter().split_text(text)
    return [stripped for piece in pieces if (stripped := piece.strip())]
