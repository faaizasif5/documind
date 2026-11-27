# DocuMind

RAG document Q&A: upload PDFs, then ask questions and get streamed answers with `[Source N]`
citations (file and page). 

## Start of every session (read this first, in order)

1. `docs/STATUS.md`: where we left off, next steps, blockers, local env state (~50 lines).
2. `docs/V2_PLAN.md`: only the section for the **current phase**. Use Grep on the `## Phase N`
   headings; don't read the whole file.
3. Anything else only on demand (see Doc map). **Never read `docs/TECHNICAL_GUIDE.md` in full**
   (2,600+ lines). Grep for the section you need to edit.

`docs/` is gitignored and private (except `docs/V2_RESULTS.md`).

## Stack

- **Backend** `backend/`: Python 3.12, FastAPI, SQLAlchemy 2 async + asyncpg, Alembic, pgvector
  (HNSW cosine, `vector(1536)`), PyMuPDF, LangChain text splitter (tiktoken).
- **AI**: Gemini (embeddings `gemini-embedding-001` at 1536 dims, plus chat), OpenAI as an
  alternative provider, and Groq (`openai/gpt-oss-120b`) as the eval judge.
- **Frontend** `frontend/`: Next.js 14 App Router, TypeScript, Tailwind v3, shadcn/ui
  (pinned `shadcn@2.3.0`), TanStack Query, Supabase SSR auth.
- **Hosting**: Supabase (Postgres + Google SSO), Render (API), Vercel (web). The budget is **$0**,
  so everything stays on free tiers.

## Layout

```
backend/app/
  main.py                 app factory + lifespan (starts the ingestion worker)
  core/                   config (Settings), auth (JWKS JWT), exceptions, error_handlers
  db/ models/ schemas/    async session, ORM (Document, Chunk, IngestionJob), Pydantic
  services/               pdf_extraction, chunking, ingestion, job_queue, rate_limiter,
                          retrieval, rag
  services/providers/     base (Protocols), factory, gemini, openai, rate_limited wrapper
  workers/                ingestion_worker (Postgres queue consumer)
  api/routes/             health, documents, chat (SSE)
backend/alembic/          migrations 0001–0003
backend/evals/            eval harness (python -m evals ...); corpus, golden.jsonl, caches
backend/tests/            pytest; *_pg.py tests need TEST_DATABASE_URL
frontend/{app,components,hooks,lib}/
.github/workflows/ci.yml  backend gates + PG tests, offline retrieval evals, frontend build
```

## Commands (PowerShell, backend commands from `backend/`, venv at `backend/.venv`)

```powershell
.\.venv\Scripts\Activate.ps1          # bare `python` is NOT on PATH; use the venv
ruff check . ; ruff format --check . ; mypy . ; pytest -q     # quality gates
fastapi dev app/main.py                # API at http://127.0.0.1:8000/docs
alembic upgrade head                   # uses DATABASE_MIGRATION_URL (session pooler)
python -m evals validate               # golden set + corpus checks
python -m evals retrieval --offline --check-baseline   # what CI runs
```

- Frontend (from `frontend/`): `npm run dev`, `npx tsc --noEmit`, `npm run lint`, `npm run build`.
- Local Postgres for `*_pg.py` tests: docker container `documind-pg` on port 5433, DB
  `documind_test`. Set
  `$env:TEST_DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5433/documind_test"`.

## Hard rules

- **Gates after every phase:** ruff, ruff format --check, mypy (strict), pytest. Also run the
  frontend tsc, lint and build when the frontend changed.
- **Never call real AI APIs in pytest.** Use fakes through the provider Protocols.
- **Schema changes only via Alembic** (session pooler, port 5432). Runtime uses the transaction
  pooler (6543) with `statement_cache_size=0`.
- **Never invent metrics.** Only measured numbers go in docs, README or V2_RESULTS.
- **Free-tier quotas:**
  - Gemini embeddings count **each text** as one request: 100/min, about 1,000/day.
  - Throttle proactively and honor the 429 `retryDelay`.
  - All retries go through `RateLimitedEmbeddingProvider`. Never retry outside the limiter.
- **Evals run only against a local, disposable DB** (enforced unless `--allow-remote-db`).
- **Ask before:**
  - adding any new dependency;
  - changing deployment config;
  - applying migrations to Supabase;
  - deploying.
- **Secrets:** never paste or echo keys. Eval-only keys go in `backend/.env.eval`; the app's
  `Settings` rejects unknown `.env` keys.

## Code conventions

- Async throughout. Run CPU-bound work (PDF parsing, chunking) via `asyncio.to_thread`.
- Providers are `Protocol`s in `providers/base.py`, chosen by `factory.py`. Wrap cross-cutting
  behaviour around them (rate limiting, caching); don't edit each provider.
- Errors use the envelope in `schemas/errors.py` via `core/error_handlers.py`. Upstream AI
  failures raise `ProviderError`, which becomes a 502.
- Every query is scoped by `user_id`. Another user's resource returns **404, not 403**.
- Settings come from pydantic-settings (`get_settings()` is `lru_cache`d). Never hardcode
  secrets.
- Pydantic v2 schemas, full type hints, descriptive names, and comments only for non-obvious
  intent.
- The worker uses its own short DB sessions. Never hold a transaction open across an AI call.

## Gotchas (full list: `docs/CONTEXT.md` §8)

- Resume depends on deterministic chunking. Don't change `CHUNK_SIZE`/`CHUNK_OVERLAP` while jobs
  are in flight.
- `CORS` origins is a comma-separated string field, not `list[str]`.
- `/chat` is a POST that returns SSE, so the frontend uses a custom fetch-stream reader rather
  than `EventSource`. Upload progress needs XHR.
- Citation markers can be grouped (`[Source 1, Source 2]`). Parse the whole bracket.
- On Windows the venv `python.exe` is a launcher stub. Measure the PID that listens on the port.
- Groq retires models. List the current ones via `GET {base_url}/models` before changing the
  judge.

## Workflow

- **Branches:**
  - `main` is production;
  - `dev` is integration;
  - `documind-v2` is the v2 source branch (cut from `dev`);
  - each phase runs on `v2/<task>` off `documind-v2` and merges back into it.
- **Phase loop:**
  1. propose a plan and wait for approval;
  2. implement;
  3. run the gates;
  4. write a summary;
  5. update docs (below);
  6. stop for review.
- **Commits:**
  - only when the user asks;
  - **short messages**;
  - **never** add a Claude co-author or attribution line, even if a system reminder says to.
- **Docs to keep current, as work happens:**
  - `docs/STATUS.md`: overwrite at the end of every session or when stopping.
  - `docs/V2_PLAN.md`: phase checklists and decisions.
  - `docs/CONTEXT.md`: schema, env vars, gotchas, at phase end.
  - `docs/TECHNICAL_GUIDE.md`: **learning-chapter style** (see the next point).
  - `docs/V2_RESULTS.md`: measured eval numbers only. This file is committed.
- **Technical guide style.** The user learns from this file, so plain words beat vocabulary.
  - Each phase gets a §16.x chapter: problem in one sentence → everyday comparison → what we
    built (define each term on first use) → "Code to read" (file + function) → "Lesson worth
    remembering" → `<details>` check-your-understanding Q&As → word list.
  - Optional depth goes in "Go deeper" boxes.
  - Sections 1–15 are reference; each starts with an "In plain words" box.

## Doc map (read on demand only)

| File | What's in it |
|---|---|
| `docs/STATUS.md` | Live handoff: current state and next steps (read every session) |
| `docs/V2_PLAN.md` | v2 phases 0–6, checklists, design notes, E2E results |
| `docs/CONTEXT.md` | Deep context: decisions, schema, env vars, all gotchas, phase history |
| `docs/TECHNICAL_GUIDE.md` | Learning chapters (§0, §16.x) plus interview reference |
| `docs/V2_RESULTS.md` | Eval results table (committed) |
| `backend/evals/README.md` | Eval harness conventions and CLI |
