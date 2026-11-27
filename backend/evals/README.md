# DocuMind evals

Offline evaluation harness for retrieval and answer quality. Separate from `pytest`
(unit tests for this code live in `tests/test_eval_*.py`).

## Corpus

Three public-domain NIST PDFs in `corpus/` (242 chunks at `CHUNK_SIZE=512`):

| File | Title | Pages |
|---|---|---|
| `NIST.AI.100-1.pdf` | AI Risk Management Framework 1.0 | 48 |
| `NIST.AI.600-1.pdf` | AI RMF Generative AI Profile | 64 |
| `NIST.CSWP.29.pdf` | Cybersecurity Framework 2.0 | 32 |

`corpus/manifest.json` pins each file's source URL and SHA-256; `python -m evals validate`
fails on any mismatch. The AI RMF and the GenAI Profile overlap in topic on purpose: they give
realistic cross-document distractors and multi-hop questions.

## Golden set (`golden.jsonl`)

60 questions: lookup 15, exact_term 10, multi_hop 10, cross_page 8, follow_up 7, unanswerable 10.

Conventions:

- **`page` is the physical PDF page (1-based)**, which is what ingestion stores. It is not the
  printed page label (the AI RMF's printed "Page 4" is physical page 9).
- `evidence` lists every page needed for a complete answer; recall@k requires all of them.
  Questions were chosen so the evidence text appears only on the cited pages. The GenAI Profile's
  tables repeat many AI RMF subcategories, so exact_term items use ones that appear once.
- `multi_hop`: evidence on 2+ pages, mostly across documents. `cross_page`: the answer spans
  adjacent pages of one file. `follow_up`: the question only makes sense with `history`. The
  baseline sends it single-turn (no conversation memory yet), so it is expected to score low.
- `unanswerable`: no evidence; the correct behavior is to refuse.

The schema enforces these rules (`schema.py`); `tests/test_eval_schema.py` validates the
committed file against the corpus on every pytest run.

## Running

```powershell
# disposable local Postgres + pgvector, migrated to head
docker run -d --name documind-pg -p 5433:5432 -e POSTGRES_PASSWORD=postgres pgvector/pgvector:pg16
docker exec documind-pg psql -U postgres -c "CREATE DATABASE documind_eval"
$env:DATABASE_MIGRATION_URL = "postgresql+asyncpg://postgres:postgres@localhost:5433/documind_eval"
alembic upgrade head

# backend/.env.eval (gitignored)
#   EVAL_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5433/documind_eval

python -m evals validate
python -m evals retrieval                       # first run fills the embedding cache
python -m evals retrieval --offline --check-baseline
python -m evals answers                         # needs GROQ_API_KEY
```

Add `--record --label <name>` to append a row to `docs/V2_RESULTS.md`, and `--write-baseline`
(retrieval only) to update `baseline.json` from a real run.

## Quota

A full corpus embed costs ~242 Gemini embedding requests plus one per question; the free tier
allows roughly 1,000/day. Everything is cached in `cache/` (committed), so repeat runs and CI
cost nothing. Any change to chunk text (chunk size, Phase 2 stitching/headings) misses the cache
and needs one online run.
