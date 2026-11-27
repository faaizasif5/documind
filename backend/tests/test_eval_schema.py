import json
from pathlib import Path

import pytest

from evals import paths
from evals.schema import (
    CorpusManifest,
    GoldenItem,
    corpus_problems,
    load_golden,
    load_manifest,
)

_E = [{"filename": "a.pdf", "page": 3}]


def _item(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "id": "q1",
        "question": "What?",
        "tag": "lookup",
        "evidence": _E,
        "reference_answer": "This.",
    }
    base.update(overrides)
    return base


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"evidence": []}, "at least one evidence"),
        ({"reference_answer": None}, "reference_answer"),
        ({"tag": "unanswerable"}, "must not list evidence"),
        ({"tag": "multi_hop"}, r"2\+ pages"),
        (
            {"tag": "cross_page", "evidence": [_E[0], {"filename": "a.pdf", "page": 5}]},
            "adjacent",
        ),
        ({"tag": "follow_up"}, "history"),
    ],
)
def test_tag_rules_are_enforced(overrides: dict[str, object], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        GoldenItem.model_validate(_item(**overrides))


def test_valid_items() -> None:
    GoldenItem.model_validate(_item(tag="unanswerable", evidence=[], reference_answer=None))
    GoldenItem.model_validate(
        _item(tag="cross_page", evidence=[_E[0], {"filename": "a.pdf", "page": 4}])
    )
    GoldenItem.model_validate(
        _item(tag="follow_up", history=[{"role": "user", "content": "Earlier question"}])
    )


def test_duplicate_ids_rejected(tmp_path: Path) -> None:
    path = tmp_path / "golden.jsonl"
    path.write_text("\n".join([json.dumps(_item()), json.dumps(_item())]), encoding="utf-8")

    with pytest.raises(ValueError, match="Duplicate"):
        load_golden(path)


def test_evidence_must_point_at_real_pages() -> None:
    manifest = CorpusManifest.model_validate(
        {
            "documents": [
                {
                    "filename": "a.pdf",
                    "title": "A",
                    "source_url": "https://example.gov/a.pdf",
                    "license": "Public domain",
                    "sha256": "0" * 64,
                    "page_count": 2,
                }
            ]
        }
    )
    items = [
        GoldenItem.model_validate(_item()),
        GoldenItem.model_validate(_item(id="q2", evidence=[{"filename": "zz.pdf", "page": 1}])),
    ]

    problems = corpus_problems(items, manifest)

    assert any("has 2 pages" in p for p in problems)
    assert any("unknown file zz.pdf" in p for p in problems)


def test_committed_golden_set_and_corpus_are_consistent() -> None:
    """Guards the real eval inputs: schema, page ranges and file hashes."""
    if not paths.GOLDEN_PATH.exists():
        pytest.skip("golden set not committed yet")
    manifest = load_manifest(paths.MANIFEST_PATH)
    items = load_golden(paths.GOLDEN_PATH)

    assert corpus_problems(items, manifest, paths.CORPUS_DIR) == []
    assert {item.tag for item in items} == {
        "lookup",
        "exact_term",
        "multi_hop",
        "cross_page",
        "follow_up",
        "unanswerable",
    }
