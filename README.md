# RAG PDF App

A local Retrieval-Augmented Generation (RAG) app for uploading PDFs, indexing their content in Qdrant, and asking questions over the indexed documents.

The app uses:

- Streamlit for the user interface.
- FastAPI as the local Inngest function endpoint.
- Inngest for background workflows.
- Qdrant as the vector database.
- OpenAI-compatible APIs for embeddings and answer generation.
- LlamaIndex utilities for PDF loading and text splitting.

## How It Works

1. Upload a PDF from the Streamlit app.
2. Streamlit sends a `rag/ingest_pdf` event to Inngest.
3. The FastAPI/Inngest worker loads the PDF, chunks the text, embeds the chunks, and stores them in Qdrant.
4. Ask a question in Streamlit.
5. Streamlit sends a `rag/query_pdf_ai` event to Inngest.
6. The worker embeds the question, searches Qdrant, sends the retrieved context to the configured LLM, and returns the answer to Streamlit.

## Project Structure

```text
.
|-- main.py             # FastAPI app and Inngest functions
|-- streamlit_app.py    # Streamlit UI
|-- data_loader.py      # PDF loading, chunking, and embeddings
|-- vector_db.py        # Qdrant wrapper
|-- custom_types.py     # Pydantic models for workflow outputs
|-- Dockerfile          # Python image for FastAPI and Streamlit
|-- docker-compose.yml  # Local dev stack
|-- pyproject.toml      # Python dependencies
|-- uv.lock             # Locked dependency versions
`-- README.md
```

## Requirements

- Docker Desktop with Docker Compose
- An OpenAI-compatible API key and base URL

Python, `uv`, and Node.js are only needed if you choose to run the services manually outside Docker.

## Environment Variables

Create a `.env` file in the project root:

```env
API_URL=https://api.openai.com/v1
API_KEY=your_api_key_here
API_MODEL=gpt-4o-mini
EMBED_MODEL=text-embedding-3-large

INNGEST_API_BASE=http://127.0.0.1:8288
INNGEST_EVENT_API_BASE=http://127.0.0.1:8288
INNGEST_REQUEST_TIMEOUT_MS=60000
QDRANT_URL=http://127.0.0.1:6333
OPENAI_TIMEOUT=60
```

Notes:

- `API_URL` can point to OpenAI or another OpenAI-compatible provider.
- `EMBED_MODEL=text-embedding-3-large` creates 3072-dimensional vectors.
- If you change the embedding model to a 1536-dimensional model, recreate the Qdrant collection or update the vector dimension.
- Do not commit `.env`; it contains secrets and is ignored by Git.
- Docker Compose overrides service-to-service URLs internally:
  - `INNGEST_API_BASE=http://inngest:8288`
  - `INNGEST_EVENT_API_BASE=http://inngest:8288`
  - `QDRANT_URL=http://qdrant:6333`

## Install Dependencies

Docker installs the Python dependencies from `pyproject.toml` and `uv.lock` while building the app image:

```dockerfile
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen
```

You do not need to run `uv sync` on your host machine for Docker-based usage.

## Run with Docker

Build and start the full stack:

```powershell
docker compose up --build
```

Or run it in the background:

```powershell
docker compose up --build -d
```

This starts:

- Qdrant on `http://127.0.0.1:6333`
- FastAPI worker on `http://127.0.0.1:8000`
- Inngest dev server on `http://127.0.0.1:8288`
- Streamlit UI on `http://127.0.0.1:8501`

Open:

```text
http://127.0.0.1:8501
```

## Docker Commands

Stop the stack:

```powershell
docker compose down
```

Rebuild after changing dependencies or the Dockerfile:

```powershell
docker compose build
docker compose up
```

Restart one service:

```powershell
docker compose restart api
docker compose restart streamlit
docker compose restart inngest
docker compose restart qdrant
```

Watch logs:

```powershell
docker compose logs -f
docker compose logs -f api
docker compose logs -f inngest
docker compose logs -f streamlit
docker compose logs -f qdrant
```

Check container status:

```powershell
docker compose ps
```

Open a shell inside the Python app container:

```powershell
docker compose exec api sh
```

Remove stopped containers and the Compose network:

```powershell
docker compose down
```

Remove containers and anonymous volumes. This does not remove the bind-mounted `qdrant_storage/` folder:

```powershell
docker compose down -v
```

## Usage

1. Upload a PDF in the Streamlit UI.
2. Wait for the ingestion event to complete.
3. Ask a question about the uploaded PDFs.
4. The app displays the generated answer and source document names.

## Common Problems

### `SendEventsError: never received response while sending events`

The Inngest dev server is not running or is not reachable on port `8288`.

Restart it with Docker Compose:

```powershell
docker compose restart inngest
```

Also make sure FastAPI is running on port `8000`.

### `404 Not Found` for `/api/ingest`

The Inngest endpoint is:

```text
/api/inngest
```

not:

```text
/api/ingest
```

### SSL errors on `127.0.0.1:8288`

Use HTTP, not HTTPS:

```env
INNGEST_API_BASE=http://127.0.0.1:8288
```

Inside Docker Compose, service-to-service URLs use service names instead:

```env
INNGEST_API_BASE=http://inngest:8288
INNGEST_EVENT_API_BASE=http://inngest:8288
QDRANT_URL=http://qdrant:6333
```

These Docker-specific values are already set in `docker-compose.yml`.

### `QdrantClient` has no attribute `search`

This project uses the newer Qdrant client API:

```python
client.query_points(...)
```

not the older `client.search(...)`.

### Embedding or LLM connection errors

Check:

- `API_URL`
- `API_KEY`
- network access to your provider
- whether the provider supports `EMBED_MODEL` and `API_MODEL`

You can smoke-test embeddings with:

```powershell
docker compose exec api python -c "from data_loader import embed_texts; print(len(embed_texts(['hello'])[0]))"
```

## Development Notes

- Uploaded files are stored in `uploads/`.
- Qdrant local data is stored in `qdrant_storage/`.
- Runtime logs, uploads, local vector storage, virtual environments, and `.env` are ignored by Git.
- `uv.lock` should be committed for reproducible installs.
- FastAPI and Streamlit use the same Python Docker image.
- Inngest uses the official `inngest/inngest` Docker image.
- Source code is bind-mounted into the app containers for local development.

## Quick Health Check

After starting the services, these ports should be listening:

```text
FastAPI   http://127.0.0.1:8000
Inngest   http://127.0.0.1:8288
Streamlit http://127.0.0.1:8501
Qdrant    http://127.0.0.1:6333
```

On PowerShell:

```powershell
Test-NetConnection 127.0.0.1 -Port 8000
Test-NetConnection 127.0.0.1 -Port 8288
Test-NetConnection 127.0.0.1 -Port 8501
Test-NetConnection 127.0.0.1 -Port 6333
```
