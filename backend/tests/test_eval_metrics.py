import pytest

from evals.metrics import (
    AnswerScore,
    citation_precision,
    recall_at_k,
    reciprocal_rank,
    regressions,
    score_retrieval,
    summarize_answers,
    summarize_retrieval,
)

A1, A2, A3, B1 = ("a.pdf", 1), ("a.pdf", 2), ("a.pdf", 3), ("b.pdf", 1)


def test_recall_counts_distinct_expected_pages_in_top_k() -> None:
    retrieved = [A3, A1, A1, B1, A2]
    assert recall_at_k({A1, A2}, retrieved, 1) == 0.0
    assert recall_at_k({A1, A2}, retrieved, 3) == 0.5
    assert recall_at_k({A1, A2}, retrieved, 5) == 1.0


def test_recall_requires_expected_evidence() -> None:
    with pytest.raises(ValueError):
        recall_at_k(set(), [A1], 1)


def test_reciprocal_rank_uses_first_relevant_chunk() -> None:
    assert reciprocal_rank({A2}, [A1, A3, A2]) == pytest.approx(1 / 3)
    assert reciprocal_rank({A2}, [A1]) == 0.0


def test_summary_is_overall_and_per_tag() -> None:
    scores = [
        score_retrieval("q1", "lookup", {A1}, [A1], ks=(1,)),
        score_retrieval("q2", "lookup", {A2}, [A1, A2], ks=(1,)),
        score_retrieval("q3", "multi_hop", {A1, B1}, [A1, A3], ks=(1,)),
    ]

    summary = summarize_retrieval(scores, ks=(1,))

    assert summary["overall"]["recall@1"] == pytest.approx((1 + 0 + 0.5) / 3)
    assert summary["overall"]["mrr"] == pytest.approx((1 + 0.5 + 1) / 3)
    assert summary["lookup"]["n"] == 2
    assert summary["multi_hop"]["recall@1"] == 0.5


def test_citation_precision() -> None:
    assert citation_precision(set(), {A1}) is None
    assert citation_precision({A1, B1}, {A1, A2}) == 0.5


def _answer(
    tag: str,
    *,
    answerable: bool = True,
    refused: bool = False,
    faith: int = 5,
    correct: int | None = 4,
    cite: float | None = 1.0,
) -> AnswerScore:
    return AnswerScore(
        item_id=tag,
        tag=tag,
        answerable=answerable,
        refused=refused,
        faithfulness=faith,
        correctness=correct,
        citation_precision=cite,
    )


def test_answer_summary_separates_refusals() -> None:
    scores = [
        _answer("lookup", faith=5, correct=4, cite=1.0),
        _answer("lookup", faith=3, correct=2, cite=None),
        _answer("lookup", refused=True),
        _answer("unanswerable", answerable=False, refused=True, correct=None, cite=None),
        _answer("unanswerable", answerable=False, refused=False, correct=None, cite=None),
    ]

    overall = summarize_answers(scores)["overall"]

    assert overall["faithfulness"] == 4.0
    assert overall["correctness"] == 3.0
    assert overall["citation_precision"] == 1.0
    assert overall["uncited_answers"] == 1
    assert overall["refusal_rate"] == 0.5
    assert overall["false_refusal_rate"] == pytest.approx(1 / 3)
    assert overall["n"] == 5


def test_regressions_respect_tolerance_and_missing_metrics() -> None:
    baseline = {"overall": {"recall@5": 0.80, "mrr": 0.60, "n": 40.0}}

    assert regressions({"overall": {"recall@5": 0.79, "mrr": 0.60}}, baseline, 0.02) == []
    failures = regressions({"overall": {"recall@5": 0.70}}, baseline, 0.02)
    assert any("recall@5" in failure for failure in failures)
    assert any("mrr: missing" in failure for failure in failures)
