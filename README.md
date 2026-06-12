# DocuMind

DocuMind is a RAG document Q&A application. Users upload PDFs, the backend extracts and embeds the content, and questions are answered with source-grounded citations.

This repository is being built as a monorepo:

```text
backend/   FastAPI, SQLAlchemy async, OpenAI, pgvector
frontend/  Next.js app, planned for a later phase
```

Current focus: backend foundation.
