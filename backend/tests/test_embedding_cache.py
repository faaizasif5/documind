from pathlib import Path

import pytest

from evals.embedding_cache import CachedEmbeddingProvider, CacheMissError, EmbeddingCache, cache_key


class _Inner:
    def __init__(self) -> None:
        self.document_calls: list[list[str]] = []
        self.query_calls: list[str] = []

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        self.document_calls.append(texts)
        return [[float(len(t)), 0.1] for t in texts]

    async def embed_query(self, text: str) -> list[float]:
        self.query_calls.append(text)
        return [float(len(text)), 0.2]


def _provider(cache: EmbeddingCache, inner: _Inner | None) -> CachedEmbeddingProvider:
    return CachedEmbeddingProvider(cache, model="gemini:m", dim=2, inner=inner)


def test_key_depends_on_every_identity_field() -> None:
    base = cache_key("m", 2, "document", "text")
    assert base != cache_key("m2", 2, "document", "text")
    assert base != cache_key("m", 3, "document", "text")
    assert base != cache_key("m", 2, "query", "text")
    assert base != cache_key("m", 2, "document", "text ")


async def test_only_misses_reach_the_provider(tmp_path: Path) -> None:
    cache = EmbeddingCache(tmp_path / "c.jsonl.gz")
    inner = _Inner()
    provider = _provider(cache, inner)

    await provider.embed_documents(["aa", "bbb"])
    vectors = await provider.embed_documents(["bbb", "cccc", "aa"])

    assert inner.document_calls == [["aa", "bbb"], ["cccc"]]
    assert [v[0] for v in vectors] == [3.0, 4.0, 2.0]
    assert (provider.hits, provider.misses) == (2, 3)


async def test_query_and_document_embeddings_are_cached_separately(tmp_path: Path) -> None:
    cache = EmbeddingCache(tmp_path / "c.jsonl.gz")
    inner = _Inner()
    provider = _provider(cache, inner)

    await provider.embed_documents(["same"])
    query = await provider.embed_query("same")

    assert inner.query_calls == ["same"]
    assert query[1] == pytest.approx(0.2)


async def test_round_trip_is_float32_and_stable(tmp_path: Path) -> None:
    path = tmp_path / "c.jsonl.gz"
    cache = EmbeddingCache(path)
    online = _provider(cache, _Inner())
    first = await online.embed_documents(["xyz"])
    cache.save()
    raw = path.read_bytes()

    reloaded = EmbeddingCache.load(path)
    offline = await _provider(reloaded, None).embed_documents(["xyz"])
    reloaded.put(cache_key("gemini:m", 2, "document", "xyz"), offline[0])
    reloaded.save()

    assert offline == first  # online run already served the float32 round-trip
    assert first[0][1] == pytest.approx(0.1, rel=1e-6) and first[0][1] != 0.1
    assert path.read_bytes() == raw  # deterministic file: no spurious git diffs


async def test_offline_miss_raises_instead_of_calling_api(tmp_path: Path) -> None:
    provider = _provider(EmbeddingCache(tmp_path / "c.jsonl.gz"), None)

    with pytest.raises(CacheMissError, match="1 query embedding"):
        await provider.embed_query("never embedded")
