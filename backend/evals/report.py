"""Run outputs, the committed regression baseline, and rows in docs/V2_RESULTS.md."""

import json
import subprocess
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

Summary = Mapping[str, Mapping[str, float | None]]

RETRIEVAL_MARKER = "<!-- retrieval-rows -->"
ANSWER_MARKER = "<!-- answer-rows -->"
BREAKDOWN_MARKER = "<!-- breakdowns -->"

_ANSWER_HEADER_CELLS = (
    "Date",
    "Label",
    "Commit",
    "n",
    "Faithfulness",
    "Correctness",
    "Citation precision",
    "Refusal rate (unanswerable)",
    "False refusal rate",
    "Uncited answers",
    "Notes",
)
_ANSWER_HEADER = "\n".join(
    ["| " + " | ".join(_ANSWER_HEADER_CELLS) + " |", "|" + "---|" * len(_ANSWER_HEADER_CELLS)]
)

RESULTS_TEMPLATE = f"""# DocuMind v2 — Eval results

Every number on this page was produced by running the harness in `backend/evals/`
(`python -m evals retrieval|answers --record`). Raw per-question outputs are written to
`backend/evals/runs/` (gitignored). Golden set: `backend/evals/golden.jsonl`.

## Retrieval

Answerable questions only. Ranked by chunk (the top-k chunks the LLM would see); a page
counts as found if any retrieved chunk comes from it, matched on (filename, page).

| Date | Label | Commit | n | recall@1 | recall@3 | recall@5 | recall@10 | MRR | Notes |
|---|---|---|---|---|---|---|---|---|---|
{RETRIEVAL_MARKER}

## Answers

LLM judge (different model family from the generator); faithfulness/correctness on a 1–5
scale over answered questions. Citation precision uses explicit `[Source N]` markers only.

{_ANSWER_HEADER}
{ANSWER_MARKER}

## Per-tag breakdowns

{BREAKDOWN_MARKER}
"""

RETRIEVAL_COLUMNS = ("recall@1", "recall@3", "recall@5", "recall@10", "mrr")
ANSWER_COLUMNS = (
    "faithfulness",
    "correctness",
    "citation_precision",
    "refusal_rate",
    "false_refusal_rate",
    "uncited_answers",
)


def git_commit() -> str:
    try:
        sha = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=True
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "status", "--porcelain"], capture_output=True, text=True, check=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return f"{sha}+dirty" if dirty else sha


_COUNT_COLUMNS = frozenset({"n", "uncited_answers"})


def fmt(value: float | None, column: str = "") -> str:
    if value is None:
        return "–"
    return str(int(value)) if column in _COUNT_COLUMNS else f"{value:.3f}"


def render_table(summary: Summary, columns: Sequence[str]) -> str:
    header = "| Group | n | " + " | ".join(columns) + " |"
    divider = "|" + "---|" * (len(columns) + 2)
    rows = [
        f"| {group} | {fmt(metrics.get('n'), 'n')} | "
        + " | ".join(fmt(metrics.get(column), column) for column in columns)
        + " |"
        for group, metrics in summary.items()
    ]
    return "\n".join([header, divider, *rows])


def write_run(runs_dir: Path, kind: str, label: str, payload: dict[str, Any]) -> Path:
    runs_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    path = runs_dir / f"{stamp}-{kind}-{label}.json"
    path.write_text(json.dumps(payload, indent=1, default=str), encoding="utf-8")
    return path


def _insert_before(text: str, marker: str, line: str) -> str:
    if marker not in text:
        raise ValueError(f"Results file is missing the {marker} marker")
    return text.replace(marker, f"{line}\n{marker}", 1)


def record_results(
    path: Path,
    *,
    kind: str,
    label: str,
    summary: Summary,
    notes: str,
) -> None:
    columns = RETRIEVAL_COLUMNS if kind == "retrieval" else ANSWER_COLUMNS
    marker = RETRIEVAL_MARKER if kind == "retrieval" else ANSWER_MARKER
    overall = summary["overall"]
    date = datetime.now(UTC).strftime("%Y-%m-%d")
    commit = git_commit()
    row = (
        f"| {date} | {label} | `{commit}` | {fmt(overall.get('n'), 'n')} | "
        + " | ".join(fmt(overall.get(column), column) for column in columns)
        + f" | {notes} |"
    )
    text = path.read_text(encoding="utf-8") if path.exists() else RESULTS_TEMPLATE
    text = _insert_before(text, marker, row)
    breakdown = f"### {kind}: {label} (`{commit}`, {date})\n\n{render_table(summary, columns)}\n"
    text = _insert_before(text, BREAKDOWN_MARKER, breakdown)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def load_baseline(path: Path) -> tuple[dict[str, dict[str, float]], float]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data["retrieval"], float(data["tolerance"])


def save_baseline(path: Path, summary: Summary, tolerance: float, commit: str) -> None:
    retrieval = {
        group: {name: float(value) for name, value in metrics.items() if value is not None}
        for group, metrics in summary.items()
    }
    payload = {"commit": commit, "tolerance": tolerance, "retrieval": retrieval}
    path.write_text(json.dumps(payload, indent=1, sort_keys=True) + "\n", encoding="utf-8")
