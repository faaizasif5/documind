"""Pure metric functions. Retrieval is ranked by chunk: the k chunks the LLM would see.

A page counts as found if any retrieved chunk comes from it, matched on
(filename, page_number).
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from statistics import fmean

PageRef = tuple[str, int]

DEFAULT_KS: tuple[int, ...] = (1, 3, 5, 10)


def recall_at_k(expected: set[PageRef], retrieved: Sequence[PageRef], k: int) -> float:
    """Fraction of expected evidence pages present among the top-k retrieved chunks."""
    if not expected:
        raise ValueError("recall is undefined without expected evidence")
    return len(expected & set(retrieved[:k])) / len(expected)


def reciprocal_rank(expected: set[PageRef], retrieved: Sequence[PageRef]) -> float:
    for rank, page in enumerate(retrieved, start=1):
        if page in expected:
            return 1.0 / rank
    return 0.0


@dataclass(frozen=True, slots=True)
class RetrievalScore:
    item_id: str
    tag: str
    recall: dict[int, float]
    reciprocal_rank: float


def score_retrieval(
    item_id: str,
    tag: str,
    expected: set[PageRef],
    retrieved: Sequence[PageRef],
    ks: Sequence[int] = DEFAULT_KS,
) -> RetrievalScore:
    return RetrievalScore(
        item_id=item_id,
        tag=tag,
        recall={k: recall_at_k(expected, retrieved, k) for k in ks},
        reciprocal_rank=reciprocal_rank(expected, retrieved),
    )


def _group(tags: Iterable[str]) -> list[str]:
    return ["overall", *sorted(set(tags))]


def summarize_retrieval(
    scores: Sequence[RetrievalScore], ks: Sequence[int] = DEFAULT_KS
) -> dict[str, dict[str, float]]:
    """Mean recall@k and MRR, overall and per tag. ``n`` is the question count."""
    summary: dict[str, dict[str, float]] = {}
    for group in _group(score.tag for score in scores):
        members = [s for s in scores if group == "overall" or s.tag == group]
        if not members:
            continue
        row = {f"recall@{k}": fmean(s.recall[k] for s in members) for k in ks}
        row["mrr"] = fmean(s.reciprocal_rank for s in members)
        row["n"] = float(len(members))
        summary[group] = row
    return summary


def citation_precision(cited: set[PageRef], expected: set[PageRef]) -> float | None:
    """Share of explicitly cited pages that are real evidence. None when nothing was cited."""
    if not cited:
        return None
    return len(cited & expected) / len(cited)


@dataclass(frozen=True, slots=True)
class AnswerScore:
    item_id: str
    tag: str
    answerable: bool
    refused: bool
    faithfulness: int | None
    correctness: int | None
    citation_precision: float | None


@dataclass(slots=True)
class _Accumulator:
    faithfulness: list[int] = field(default_factory=list)
    correctness: list[int] = field(default_factory=list)
    citation: list[float] = field(default_factory=list)
    uncited: int = 0
    answerable: int = 0
    answerable_refused: int = 0
    unanswerable: int = 0
    unanswerable_refused: int = 0


def _mean_or_none(values: Sequence[float]) -> float | None:
    return fmean(values) if values else None


def summarize_answers(scores: Sequence[AnswerScore]) -> dict[str, dict[str, float | None]]:
    """Answer metrics overall and per tag.

    Faithfulness, correctness and citation precision use only answerable questions
    the system actually answered; refusals are tracked separately as refusal_rate
    (unanswerable, higher is better) and false_refusal_rate (answerable, lower is better).
    """
    summary: dict[str, dict[str, float | None]] = {}
    for group in _group(score.tag for score in scores):
        acc = _Accumulator()
        for s in scores:
            if group != "overall" and s.tag != group:
                continue
            if not s.answerable:
                acc.unanswerable += 1
                acc.unanswerable_refused += int(s.refused)
                continue
            acc.answerable += 1
            if s.refused:
                acc.answerable_refused += 1
                continue
            if s.faithfulness is not None:
                acc.faithfulness.append(s.faithfulness)
            if s.correctness is not None:
                acc.correctness.append(s.correctness)
            if s.citation_precision is None:
                acc.uncited += 1
            else:
                acc.citation.append(s.citation_precision)
        summary[group] = {
            "faithfulness": _mean_or_none(acc.faithfulness),
            "correctness": _mean_or_none(acc.correctness),
            "citation_precision": _mean_or_none(acc.citation),
            "uncited_answers": float(acc.uncited),
            "refusal_rate": (
                acc.unanswerable_refused / acc.unanswerable if acc.unanswerable else None
            ),
            "false_refusal_rate": (
                acc.answerable_refused / acc.answerable if acc.answerable else None
            ),
            "n": float(acc.answerable + acc.unanswerable),
        }
    return summary


def regressions(
    current: dict[str, dict[str, float]],
    baseline: dict[str, dict[str, float]],
    tolerance: float,
) -> list[str]:
    """Metrics that dropped more than ``tolerance`` below the baseline (higher is better)."""
    failures: list[str] = []
    for group, metrics in baseline.items():
        for name, expected in metrics.items():
            if name == "n":
                continue
            actual = current.get(group, {}).get(name)
            if actual is None:
                failures.append(f"{group}.{name}: missing (baseline {expected:.3f})")
            elif actual < expected - tolerance:
                failures.append(f"{group}.{name}: {actual:.3f} < baseline {expected:.3f}")
    return failures
