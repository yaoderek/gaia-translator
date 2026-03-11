# GAIA Translator

Interdisciplinary scientific translation tool for a geohazard research lab. Translates domain-specific jargon between disciplines (hydrology, seismology, atmospheric science, climatology, geology, computer science, applied mathematics) using RAG-powered LLM translation with scientific literature citations and figure references.

## Architecture

- **Frontend**: React + TypeScript + Vite + Tailwind CSS
- **Backend**: Python FastAPI + OpenAI GPT-4o + ChromaDB + PyMuPDF
- **RAG Pipeline**: PDF ingestion → section-aware chunking → OpenAI embeddings → ChromaDB vector search

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- OpenAI API key

### 1. Backend

```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Configure your API key
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# Start the server
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 in your browser.

### 3. Ingest Papers

Drop PDF files into `backend/data/papers/`, then either:

- Click the "Ingest Papers" button in the UI, or
- `curl -X POST http://localhost:8000/api/ingest`

### Docker

```bash
docker compose up --build
```

Frontend at http://localhost:5173, backend at http://localhost:8000.

## Usage

1. Select a **source discipline** (the language you're translating from)
2. Select a **target discipline** (who you're translating for)
3. Paste or type the technical text
4. Click **Translate** (or Cmd+Enter)
5. View the translation with inline citations, referenced figures, and follow-up questions

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health check |
| GET | `/api/disciplines` | List available disciplines |
| POST | `/api/translate` | Translate text (SSE streaming) |
| POST | `/api/ingest` | Ingest PDFs from data/papers/ |
| GET | `/api/papers` | List ingested papers |
| GET | `/api/figures/{id}` | Serve extracted figure image |

## Starter Papers

Seed the RAG database with papers from the Denolle Quake Lab (UW):

- Shi et al. (2026) -- Agroseismology: soil hydrodynamics via seismic methods
- Feng et al. (2026) -- Near-surface seismic velocity response to hydrological variations
- Denolle et al. (2025) -- Ambient field seismology in critical zone hydrology
- Makus et al. (2024) -- Environmental influences on seismic velocity at Mt. St. Helens
- Toghramadjian et al. (2026) -- Dense urban nodal arrays for seismic hazard
- Diewald et al. (2024) -- Temperature/humidity effects on coda waves
