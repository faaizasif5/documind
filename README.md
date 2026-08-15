# DocuMind

DocuMind is a production-oriented RAG document Q&A application. Sign in with Google,
upload PDFs, and ask questions against your private document library. Answers stream as
they are generated and include interactive citations to the source file and page.

**Live app:** [documind-eight-alpha.vercel.app](https://documind-eight-alpha.vercel.app/)

## Highlights

- Google SSO through Supabase Auth with FastAPI JWT verification
- Per-user document isolation across upload, listing, retrieval, chat, and deletion
- PDF upload transfer progress followed by background processing status
- Per-page, token-aware chunking with 1536-dimensional embeddings
- PostgreSQL/pgvector retrieval using an HNSW cosine index
- Gemini or OpenAI selected through configuration behind one provider interface
- Markdown answers streamed over POST-based Server-Sent Events
- Numbered, source-filtered citations with grouped citation support
- Structured API errors and fully async database/provider I/O
- Deployed on Vercel, Render, and Supabase

## How it works

During ingestion, the API validates a PDF, returns `202 Accepted`, and processes it in a
background task. PyMuPDF extracts each page, a token-aware splitter creates overlapping
chunks, and the configured provider embeds them for storage in pgvector.

For a question, DocuMind embeds the query, retrieves the top matching chunks belonging
to the signed-in user, and supplies those numbered sources to the completion model. The
answer streams token by token, followed by structured metadata for only the sources the
model cited.

## Technology

- **Frontend:** Next.js 14, TypeScript, Tailwind CSS, shadcn/ui, TanStack Query
- **Backend:** FastAPI, Pydantic v2, SQLAlchemy 2.0 async, asyncpg, Alembic
- **Data and auth:** Supabase PostgreSQL, pgvector, Supabase Auth
- **AI:** Gemini (`gemini-2.5-flash`, `gemini-embedding-001`) or OpenAI
  (`gpt-4o-mini`, `text-embedding-3-small`)
- **Hosting:** Vercel frontend and Render API
- **Quality:** Ruff, strict mypy, pytest, ESLint, TypeScript, Next.js production build

## Local setup

### Prerequisites

- Python 3.12+
- Node.js 20+
- A Supabase project (Postgres with pgvector + Google Auth)
- A Gemini API key or OpenAI API key

### Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
# Fill in values from .env.example, then:
alembic upgrade head
fastapi dev app/main.py
```

API: `http://127.0.0.1:8000` · docs: `/docs`  
Details: [`backend/README.md`](backend/README.md) and [`backend/.env.example`](backend/.env.example)

### Frontend

```powershell
cd frontend
Copy-Item .env.local.example .env.local
# Fill in values from .env.local.example, then:
npm install
npm run dev
```

App: [http://localhost:3000](http://localhost:3000) — signed-out visitors see the
marketing page; after Google sign-in, the same route opens the document Q&A app.  
Details: [`frontend/README.md`](frontend/README.md) and
[`frontend/.env.local.example`](frontend/.env.local.example)

## Verify the happy path

1. Sign in with Google.
2. Upload a text-based PDF and watch transfer progress change to processing, then ready.
3. Ask a question answered by the PDF.
4. Confirm the answer streams and includes numbered citation badges.
5. Open a citation and verify its filename and page number.
6. Sign out and confirm the public marketing page returns.

Scanned image-only PDFs require OCR and are not supported. Chat is currently stateless,
and switching AI providers requires re-uploading documents because embedding spaces are
not cross-compatible.

## Quality gates

Backend:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
ruff check .
ruff format --check .
mypy .
pytest -q
```

Frontend:

```powershell
cd frontend
npx tsc --noEmit
npm run lint
npm run build
```
