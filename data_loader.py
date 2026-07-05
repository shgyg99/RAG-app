from openai import OpenAI, OpenAIError
from llama_index.readers.file import PDFReader
from llama_index.core.node_parser import SentenceSplitter
from dotenv import load_dotenv
import os

load_dotenv()

API_KEY = os.getenv("API_KEY")
API_URL = os.getenv("API_URL")

client_kwargs = {"api_key": API_KEY, "timeout": float(os.getenv("OPENAI_TIMEOUT", "60"))} if API_KEY else None
if client_kwargs and API_URL:
    client_kwargs["base_url"] = API_URL

client = OpenAI(**client_kwargs) if client_kwargs else None
EMBED_MODEL = os.getenv("EMBED_MODEL", "text-embedding-3-large")
EMBED_DIM = 3072 if EMBED_MODEL == "text-embedding-3-large" else 1536

splitter = SentenceSplitter(chunk_size=1000, chunk_overlap=200)

def load_and_chunk_pdf(path: str):
    docs = PDFReader().load_data(file=path)
    texts = [d.text for d in docs if getattr(d, "text", None)]
    chunks = []
    for t in texts:
        chunks.extend(splitter.split_text(t))
    return chunks

def embed_texts(texts: list[str]) -> list[list[float]]:
    if client is None:
        raise RuntimeError("API_KEY is not configured for embeddings.")
    if not texts:
        return []
    try:
        response = client.embeddings.create(
            model=EMBED_MODEL,
            input=texts
        )
    except OpenAIError as exc:
        raise RuntimeError(f"Embedding request failed for model {EMBED_MODEL}: {exc}") from exc
    return [item.embedding for item in response.data]
