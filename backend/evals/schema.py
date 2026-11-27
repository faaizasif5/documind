"""Golden-set and corpus-manifest models, plus cross-checks between them."""

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

Tag = Literal["lookup", "exact_term", "multi_hop", "cross_page", "follow_up", "unanswerable"]
TAGS: tuple[Tag, ...] = (
    "lookup",
    "exact_term",
    "multi_hop",
    "cross_page",
    "follow_up",
    "unanswerable",
)


class Evidence(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    filename: str = Field(min_length=1)
    page: int = Field(ge=1)


class Turn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1)


class GoldenItem(BaseModel):
    """One evaluation question.

    ``evidence`` lists every (filename, page) that contains the answer. Retrieval is
    scored against it; unanswerable questions have none by definition.
    """

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    question: str = Field(min_length=1)
    tag: Tag
    evidence: list[Evidence] = Field(default_factory=list)
    reference_answer: str | None = None
    history: list[Turn] = Field(default_factory=list)

    @property
    def answerable(self) -> bool:
        return self.tag != "unanswerable"

    @property
    def evidence_pages(self) -> set[tuple[str, int]]:
        return {(item.filename, item.page) for item in self.evidence}

    @model_validator(mode="after")
    def _check_tag_rules(self) -> Self:
        if not self.answerable:
            if self.evidence:
                raise ValueError(f"{self.id}: unanswerable items must not list evidence")
            return self
        if not self.evidence:
            raise ValueError(f"{self.id}: answerable items need at least one evidence page")
        if not self.reference_answer:
            raise ValueError(f"{self.id}: answerable items need a reference_answer")
        if self.tag == "multi_hop" and len(self.evidence_pages) < 2:
            raise ValueError(f"{self.id}: multi_hop needs evidence on 2+ pages")
        if self.tag == "cross_page" and not _has_adjacent_pages(self.evidence_pages):
            raise ValueError(f"{self.id}: cross_page needs evidence on adjacent pages of one file")
        if self.tag == "follow_up" and not self.history:
            raise ValueError(f"{self.id}: follow_up needs conversation history")
        return self


def _has_adjacent_pages(pages: set[tuple[str, int]]) -> bool:
    return any((filename, page + 1) in pages for filename, page in pages)


class CorpusDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    filename: str = Field(min_length=1)
    title: str
    source_url: str
    license: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    page_count: int = Field(ge=1)


class CorpusManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    documents: list[CorpusDocument] = Field(min_length=1)

    def by_filename(self) -> dict[str, CorpusDocument]:
        return {document.filename: document for document in self.documents}


def load_golden(path: Path) -> list[GoldenItem]:
    items: list[GoldenItem] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            items.append(GoldenItem.model_validate_json(line))
        except ValueError as exc:
            raise ValueError(f"{path.name}:{line_number}: {exc}") from exc
    duplicates = {item_id for item_id, n in Counter(item.id for item in items).items() if n > 1}
    if duplicates:
        raise ValueError(f"Duplicate golden ids: {sorted(duplicates)}")
    return items


def load_manifest(path: Path) -> CorpusManifest:
    return CorpusManifest.model_validate(json.loads(path.read_text(encoding="utf-8")))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def corpus_problems(
    items: list[GoldenItem], manifest: CorpusManifest, corpus_dir: Path | None = None
) -> list[str]:
    """Evidence must point at real pages of corpus files; files must match their hashes."""
    documents = manifest.by_filename()
    problems: list[str] = []
    for item in items:
        for evidence in item.evidence:
            document = documents.get(evidence.filename)
            if document is None:
                problems.append(f"{item.id}: unknown file {evidence.filename}")
            elif evidence.page > document.page_count:
                problems.append(
                    f"{item.id}: {evidence.filename} has {document.page_count} pages, "
                    f"evidence cites page {evidence.page}"
                )
    if corpus_dir is not None:
        for document in manifest.documents:
            path = corpus_dir / document.filename
            if not path.exists():
                problems.append(f"missing corpus file {document.filename}")
            elif sha256_file(path) != document.sha256:
                problems.append(f"hash mismatch for {document.filename}")
    return problems
