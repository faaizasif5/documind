# DocuMind v2 — Eval results

Every number on this page was produced by running the harness in `backend/evals/`
(`python -m evals retrieval|answers --record`). Raw per-question outputs are written to
`backend/evals/runs/` (gitignored). Golden set: `backend/evals/golden.jsonl`.

## Retrieval

Answerable questions only. Ranked by chunk (the top-k chunks the LLM would see); a page
counts as found if any retrieved chunk comes from it, matched on (filename, page).

| Date | Label | Commit | n | recall@1 | recall@3 | recall@5 | recall@10 | MRR | Notes |
|---|---|---|---|---|---|---|---|---|---|
| 2026-11-28 | baseline | `a7e871e+dirty` | 50 | 0.470 | 0.760 | 0.840 | 0.880 | 0.733 |  |
<!-- retrieval-rows -->

## Answers

LLM judge (different model family from the generator); faithfulness/correctness on a 1–5
scale over answered questions. Citation precision uses explicit `[Source N]` markers only.

| Date | Label | Commit | n | Faithfulness | Correctness | Citation precision | Refusal rate (unanswerable) | False refusal rate | Uncited answers | Notes |
|---|---|---|---|---|---|---|---|---|---|---|
<!-- answer-rows -->

## Per-tag breakdowns

### retrieval: baseline (`a7e871e+dirty`, 2026-11-28)

| Group | n | recall@1 | recall@3 | recall@5 | recall@10 | mrr |
|---|---|---|---|---|---|---|
| overall | 50 | 0.470 | 0.760 | 0.840 | 0.880 | 0.733 |
| cross_page | 8 | 0.438 | 0.875 | 0.938 | 1.000 | 0.938 |
| exact_term | 10 | 0.400 | 0.900 | 1.000 | 1.000 | 0.642 |
| follow_up | 7 | 0.286 | 0.286 | 0.429 | 0.571 | 0.330 |
| lookup | 15 | 0.733 | 1.000 | 1.000 | 1.000 | 0.867 |
| multi_hop | 10 | 0.300 | 0.500 | 0.650 | 0.700 | 0.742 |

<!-- breakdowns -->
