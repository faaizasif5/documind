"""Content-addressed embedding cache, committed to git so CI evals need no API calls.

Vectors are stored as float32, which is lossless here: pgvector stores float4.
"""

import base64
import gzip
import hashlib
import json
import sys
from array import array
from pathlib import Path
from typing import Literal

from app.services.providers.base import EmbeddingProvider

Task = Literal["document", "query"]


def cache_key(model: str, dim: int, task: Task, text: str) -> str:
    """Identity of an embedding: changing the model, dimension, task type or text misses."""
    return hashlib.sha256("\x1f".join((model, str(dim), task, text)).encode("utf-8")).hexdigest()


def _encode(vector: list[float]) -> str:
    packed = array("f", vector)
    if sys.byteorder == "big":
        packed.byteswap()
    return base64.b64encode(packed.tobytes()).decode("ascii")


def _decode(data: str) -> list[float]:
    packed = array("f")
    packed.frombytes(base64.b64decode(data))
    if sys.byteorder == "big":
        packed.byteswap()
    return packed.tolist()


class EmbeddingCache:
    def __init__(self, path: Path, vectors: dict[str, str] | None = None) -> None:
        self.path = path
        self._vectors = vectors or {}
        self.dirty = False

    @classmethod
    def load(cls, path: Path) -> "EmbeddingCache":
        vectors: dict[str, str] = {}
        if path.exists():
            with gzip.open(path, "rt", encoding="utf-8") as handle:
                for line in handle:
                    if line.strip():
                        record = json.loads(line)
                        vectors[record["k"]] = record["v"]
        return cls(path, vectors)

    def __len__(self) -> int:
        return len(self._vectors)

    def get(self, key: str) -> list[float] | None:
        data = self._vectors.get(key)
        return None if data is None else _decode(data)

    def put(self, key: str, vector: list[float]) -> None:
        self._vectors[key] = _encode(vector)
        self.dirty = True

    def save(self) -> None:
        """Write sorted by key with a fixed gzip mtime so unchanged caches diff cleanly."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        lines = "".join(
            json.dumps({"k": key, "v": self._vectors[key]}) + "\n" for key in sorted(self._vectors)
        )
        with open(self.path, "wb") as raw, gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as gz:
            gz.write(lines.encode("utf-8"))
        self.dirty = False


class CacheMissError(RuntimeError):
    """Offline mode needed an embedding that is not in the cache."""


class CachedEmbeddingProvider:
    """EmbeddingProvider that serves from the cache and only calls ``inner`` on a miss.

    With ``inner=None`` (offline/CI) any miss raises ``CacheMissError``: an eval run
    can never spend quota by accident.
    """

    def __init__(
        self,
        cache: EmbeddingCache,
        *,
        model: str,
        dim: int,
        inner: EmbeddingProvider | None,
    ) -> None:
        self._cache = cache
        self._model = model
        self._dim = dim
        self._inner = inner
        self.hits = 0
        self.misses = 0

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return await self._embed(texts, "document")

    async def embed_query(self, text: str) -> list[float]:
        return (await self._embed([text], "query"))[0]

    async def _embed(self, texts: list[str], task: Task) -> list[list[float]]:
        keys = [cache_key(self._model, self._dim, task, text) for text in texts]
        found = {key: vector for key in keys if (vector := self._cache.get(key)) is not None}
        missing = [(key, text) for key, text in zip(keys, texts, strict=True) if key not in found]
        self.hits += len(texts) - len(missing)
        self.misses += len(missing)
        if missing:
            if self._inner is None:
                raise CacheMissError(
                    f"{len(missing)} {task} embedding(s) missing from the cache; "
                    "run the eval online once to fill it"
                )
            embed = (
                self._inner.embed_documents
                if task == "document"
                else self._embed_queries_one_by_one
            )
            vectors = await embed([text for _, text in missing])
            for (key, _), vector in zip(missing, vectors, strict=True):
                self._cache.put(key, vector)
                # Serve the float32 round-trip so online and offline runs see identical vectors.
                cached = self._cache.get(key)
                assert cached is not None
                found[key] = cached
        return [found[key] for key in keys]

    async def _embed_queries_one_by_one(self, texts: list[str]) -> list[list[float]]:
        # Query embeddings use the query task type, which only embed_query exposes.
        assert self._inner is not None
        return [await self._inner.embed_query(text) for text in texts]
