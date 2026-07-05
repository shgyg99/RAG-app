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
|-- pyproject.toml      # Python dependencies
|-- uv.lock             # Locked dependency versions
`-- README.md
```

## Requirements

- Python 3.12+
- `uv`
- Docker, for local Qdrant
- Node.js/npm, for `npx inngest-cli`
- An OpenAI-compatible API key and base URL

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
OPENAI_TIMEOUT=60
```

Notes:

- `API_URL` can point to OpenAI or another OpenAI-compatible provider.
- `EMBED_MODEL=text-embedding-3-large` creates 3072-dimensional vectors.
- If you change the embedding model to a 1536-dimensional model, recreate the Qdrant collection or update the vector dimension.
- Do not commit `.env`; it contains secrets and is ignored by Git.

## Install Dependencies

```powershell
uv sync
```

## Start Qdrant

PowerShell:

```powershell
docker run -d --name qdrant -p 6333:6333 -v "${PWD}\qdrant_storage:/qdrant/storage" qdrant/qdrant
```

If the container already exists:

```powershell
docker start qdrant
```

Qdrant will be available at:

```text
http://localhost:6333
```

## Run the App

Use three terminals from the project root.

Terminal 1: FastAPI worker

```powershell
uv run uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Terminal 2: Inngest dev server

```powershell
npx inngest-cli@latest dev -u http://127.0.0.1:8000/api/inngest
```

Terminal 3: Streamlit UI

```powershell
uv run streamlit run streamlit_app.py --server.address 127.0.0.1 --server.port 8501
```

Open:

```text
http://127.0.0.1:8501
```

## Usage

1. Upload a PDF in the Streamlit UI.
2. Wait for the ingestion event to complete.
3. Ask a question about the uploaded PDFs.
4. The app displays the generated answer and source document names.

## Common Problems

### `SendEventsError: never received response while sending events`

The Inngest dev server is not running or is not reachable on port `8288`.

Start it with:

```powershell
npx inngest-cli@latest dev -u http://127.0.0.1:8000/api/inngest
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
uv run python -c "from data_loader import embed_texts; print(len(embed_texts(['hello'])[0]))"
```

## Development Notes

- Uploaded files are stored in `uploads/`.
- Qdrant local data is stored in `qdrant_storage/`.
- Runtime logs, uploads, local vector storage, virtual environments, and `.env` are ignored by Git.
- `uv.lock` should be committed for reproducible installs.

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
