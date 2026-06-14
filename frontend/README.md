# DocuMind — Frontend

Next.js 14 (App Router) client for the DocuMind RAG document Q&A API. Upload PDFs,
watch them process, and ask grounded questions with streamed answers and citations.

## Stack

- Next.js 14 + TypeScript (App Router)
- Tailwind CSS + shadcn/ui (Radix primitives)
- TanStack Query for document list / upload / delete (with status polling)
- Custom `fetch` + `ReadableStream` SSE consumer for the streaming `/chat` endpoint
  (the browser's native `EventSource` only supports GET, but `/chat` is a POST)

## Getting started

```bash
npm install
cp .env.local.example .env.local   # adjust NEXT_PUBLIC_API_BASE_URL if needed
npm run dev                         # http://localhost:3000
```

The backend must be running (default `http://127.0.0.1:8000`) and its
`BACKEND_CORS_ORIGINS` must include `http://localhost:3000`.

## Scripts

```bash
npm run dev      # dev server
npm run build    # production build
npm run start    # serve the production build
npm run lint     # eslint
```

## Layout

```
app/                 root layout (providers + toaster) + single-page UI
components/
  ui/                shadcn primitives
  query-provider.tsx TanStack Query client provider
  upload-dropzone.tsx
  document-list.tsx
  chat-panel.tsx     scope selector + transcript + composer
  message.tsx
  citation-chips.tsx
hooks/
  use-documents.ts   list / upload / delete (+ polling while processing)
  use-chat.ts        SSE chat state machine
lib/
  api.ts             typed API client + ApiError
  sse.ts             POST-based SSE stream consumer
  types.ts           response/request types mirroring the backend schemas
  query-keys.ts
```

## Notes

- Chat is **single-turn / stateless** (matches the backend): each question is
  answered independently with no conversation memory.
- Use the **Scope** selector to restrict a question to one document
  (sends `document_id`), or keep "All documents" for the whole corpus.
