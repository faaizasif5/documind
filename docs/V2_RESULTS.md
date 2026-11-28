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
| 2026-11-28 | baseline | `f46ae91+dirty` | 60 | 4.800 | 4.080 | 0.748 | 0.400 | 0.000 | 0 | superseded: judge gpt-oss-120b, rubric v1 under-counted refusals |
| 2026-11-28 | baseline | `f46ae91+dirty` | 60 | 4.667 | 4.208 | 0.748 | 0.800 | 0.040 | 0 | judge gpt-oss-20b, rubric v2 (current baseline). Manual read: the 2 unrefused unanswerables (un-04, un-10) do decline ("no mention of…"); judge mislabel |
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

### answers: baseline (`f46ae91+dirty`, 2026-11-28) — superseded (judge gpt-oss-120b, rubric v1)

| Group | n | faithfulness | correctness | citation_precision | refusal_rate | false_refusal_rate | uncited_answers |
|---|---|---|---|---|---|---|---|
| overall | 60 | 4.800 | 4.080 | 0.748 | 0.400 | 0.000 | 0 |
| cross_page | 8 | 5.000 | 4.750 | 0.800 | – | 0.000 | 0 |
| exact_term | 10 | 5.000 | 5.000 | 0.950 | – | 0.000 | 0 |
| follow_up | 7 | 5.000 | 2.857 | 0.250 | – | 0.000 | 0 |
| lookup | 15 | 5.000 | 4.867 | 0.922 | – | 0.000 | 0 |
| multi_hop | 10 | 4.000 | 2.300 | 0.590 | – | 0.000 | 0 |
| unanswerable | 10 | – | – | – | 0.400 | – | 0 |

### answers: baseline (`f46ae91+dirty`, 2026-11-28) — current (judge gpt-oss-20b, rubric v2)

| Group | n | faithfulness | correctness | citation_precision | refusal_rate | false_refusal_rate | uncited_answers |
|---|---|---|---|---|---|---|---|
| overall | 60 | 4.667 | 4.208 | 0.748 | 0.800 | 0.040 | 0 |
| cross_page | 8 | 5.000 | 4.750 | 0.800 | – | 0.000 | 0 |
| exact_term | 10 | 5.000 | 5.000 | 0.950 | – | 0.000 | 0 |
| follow_up | 7 | 5.000 | 3.000 | 0.250 | – | 0.000 | 0 |
| lookup | 15 | 4.867 | 4.733 | 0.922 | – | 0.000 | 0 |
| multi_hop | 10 | 3.250 | 2.750 | 0.550 | – | 0.200 | 0 |
| unanswerable | 10 | – | – | – | 0.800 | – | 0 |

<!-- breakdowns -->
