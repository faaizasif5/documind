# DocuMind

DocuMind is a Retrieval-Augmented Generation (RAG) document Q&A application. Upload
PDFs, and the backend extracts, chunks, and embeds their content into a vector store;
questions are then answered by an LLM using the most relevant chunks, with **streamed,
source-grounded citations**.

## Architecture

```text
documind/
├── backend/    FastAPI (async) · SQLAlchemy 2.0 + asyncpg · pgvector on Supabase
│               pluggable Gemini/OpenAI providers · SSE streaming chat
└── frontend/   Next.js 14 (App Router, TS) · Tailwind + shadcn/ui · TanStack Query
```

- **Retrieval:** PDF text is split into token-aware, per-page chunks, embedded
  (1536-dim), and stored in PostgreSQL with a pgvector HNSW cosine index.
- **Generation:** at query time the question is embedded, the top-k chunks are
  retrieved, and the answer is streamed token-by-token over Server-Sent Events,
  followed by deduplicated citations (filename + page).
- **Pluggable AI:** Gemini (default) or OpenAI behind one interface, selected via the
  `LLM_PROVIDER` env var. Embeddings from different providers are not cross-compatible.

## Tech stack

| Layer    | Choices |
|----------|---------|
| Backend  | FastAPI, Pydantic v2, SQLAlchemy 2.0 async, asyncpg, Alembic |
| Vector DB| PostgreSQL + pgvector (Supabase), HNSW cosine index |
| AI       | Gemini (`gemini-2.5-flash`, `gemini-embedding-001`) or OpenAI (`gpt-4o-mini`, `text-embedding-3-small`) |
| Frontend | Next.js 14, TypeScript, Tailwind CSS, shadcn/ui, TanStack Query |
| Tooling  | ruff, mypy, pytest (backend); ESLint (frontend) |

## Getting started

Each app has its own setup instructions:

- **Backend** — see [`backend/README.md`](backend/README.md) (Python venv, env vars,
  Alembic migrations, dev server on `:8000`).
- **Frontend** — see [`frontend/README.md`](frontend/README.md) (Node 20+, `npm install`,
  dev server on `:3000`).

Quick start:

```bash
# Backend (PowerShell, from backend/)
python -m venv .venv; .\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
fastapi dev app/main.py        # http://127.0.0.1:8000/docs

# Frontend (from frontend/)
npm install
npm run dev                    # http://localhost:3000
```

The frontend reads the backend URL from `NEXT_PUBLIC_API_BASE_URL`, and the backend's
`BACKEND_CORS_ORIGINS` must include the frontend origin (`http://localhost:3000` by default).

