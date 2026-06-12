# DocuMind Backend

FastAPI backend for a RAG document Q&A application.

## Local Setup

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
fastapi dev app/main.py
```

The API health endpoint is available at:

```text
GET /api/v1/healthz
```

## Checks

```powershell
ruff check .
ruff format --check .
mypy .
pytest
```
