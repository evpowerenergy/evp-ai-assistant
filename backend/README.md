# Backend - AI Assistant API

FastAPI backend สำหรับ Internal AI Assistant

## Tech Stack

- **FastAPI** - Web framework
- **LangChain + LangGraph** - AI orchestration
- **OpenAI** - LLM
- **Supabase** - Database (PostgreSQL + pgvector)
- **LINE SDK** - LINE Messaging API

## Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment variables
cp .env.example .env
# Edit .env with your credentials

# Run development server
uvicorn app.main:app --reload
```

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app
│   ├── config.py            # Configuration
│   ├── api/                 # API routes
│   ├── core/                # Auth, permissions, audit
│   ├── orchestrator/        # LangGraph workflow
│   ├── tools/               # AI tools (DB, RAG, LINE)
│   └── services/            # Supabase, LLM, Vector store
├── tests/                   # Tests
├── requirements.txt
└── Dockerfile
```

## API Endpoints

- `GET /health` - Health check
- `POST /api/v1/chat` - Chat endpoint (TODO)
- `POST /api/v1/line/webhook` - LINE webhook (TODO)
- `POST /api/v1/ingest` - Document ingestion (TODO)

## Development

```bash
# Run with auto-reload
uvicorn app.main:app --reload

# Run tests
pytest
```

## Deployment

Deploy to GCP Cloud Run using GitHub Actions workflow.
