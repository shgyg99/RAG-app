import asyncio
from pathlib import Path
import time

import streamlit as st
import inngest
from dotenv import load_dotenv 
import os
import requests

load_dotenv()

st.set_page_config(page_title="RAG Ingest PDF", page_icon="🥸", layout="centered")

def _strip_api_version(url: str) -> str:
    return url.rstrip("/").removesuffix("/v1")


def _inngest_origin() -> str:
    return _strip_api_version(os.getenv("INNGEST_API_BASE", "http://127.0.0.1:8288"))


def _inngest_event_origin() -> str:
    return _strip_api_version(os.getenv("INNGEST_EVENT_API_BASE", _inngest_origin()))


def check_inngest_dev_server() -> None:
    try:
        requests.get(f"{_inngest_origin()}/v1/events", timeout=3)
    except requests.RequestException as exc:
        raise RuntimeError(
            "Inngest dev server is not reachable. Start it with: "
            "npx inngest-cli@latest dev -u http://127.0.0.1:8000/api/inngest"
        ) from exc 


@st.cache_resource
def get_inngest_client() -> inngest.Inngest:
    return inngest.Inngest(
        app_id="rag_app",
        is_production=False,
        api_base_url=_inngest_origin(),
        event_api_base_url=_inngest_event_origin(),
        request_timeout=int(os.getenv("INNGEST_REQUEST_TIMEOUT_MS", "60000")),
    )
    
def save_uploaded_pdf(file) -> Path:
    upload_dir = Path("uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / file.name
    file_bytes = file.getbuffer()
    file_path.write_bytes(file_bytes)
    return file_path

async def send_rag_ingest_event(pdf_path: Path) -> None:
    check_inngest_dev_server()
    client = get_inngest_client()
    await client.send(
        inngest.Event(
            name="rag/ingest_pdf",
            data={"pdf_path": str(pdf_path.resolve()),
                  "source_id": pdf_path.name,
            }
        )
    )
    
st.title("Upload a PDF to Ingest")
uploaded = st.file_uploader("Choose a PDF", type="pdf", accept_multiple_files=False)

if uploaded is not None:
    with st.spinner("Uploading and triggering ingestion..."):
        path = save_uploaded_pdf(uploaded)
        try:
            asyncio.run(send_rag_ingest_event(path))
        except Exception as exc:
            st.error(f"Failed to send ingest event: {exc}")
            st.stop()
        time.sleep(0.3)
    st.success(f"PDF '{path.name}' uploaded and ingestion triggered successfully!")
    st.caption("You can upload another PDF at any time.")
    
st.divider()
st.title("Ask a Question about your PDFs")

async def send_rag_query_event(question: str, top_k: int=5) -> None:
    check_inngest_dev_server()
    client = get_inngest_client()
    result = await client.send(
        inngest.Event(
            name="rag/query_pdf_ai",
            data={"question": question, "top_k": top_k}
        )
    )
    
    return result[0]

def _inngest_api_base() -> str:
    return f"{_inngest_origin()}/v1"

def fetch_runs(event_id: str) -> list[dict]:
    url = f"{_inngest_api_base()}/events/{event_id}/runs"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    return data.get("data", [])


def describe_run_failure(run: dict) -> str:
    for key in ("error", "error_message", "message"):
        value = run.get(key)
        if value:
            return str(value)

    output = run.get("output") or {}
    if isinstance(output, dict):
        for key in ("error", "message", "body"):
            value = output.get(key)
            if value:
                return str(value)

    run_id = run.get("run_id", "unknown")
    return f"No error details returned by Inngest. Check the Inngest dev UI/logs for run {run_id}."


def wait_for_run_output(event_id: str, timeout_s: float=120.0, poll_interval_s: float = 0.5) -> dict:
    start_time = time.time()
    last_status = None
    latest_run = None
    while True:
        runs = fetch_runs(event_id)
        if runs:
            run = runs[0]
            latest_run = runs[0]
            status = latest_run.get("status")
            last_status = status or last_status
            normalized_status = (status or "").lower()
            if normalized_status in {"completed", "succeeded", "success", "finished"}:
                output = run.get("output") or {}
                if isinstance(output, dict):
                    return output
                return {"answer": str(output)}
            if normalized_status in {"failed", "error", "cancelled", "canceled"}:
                raise RuntimeError(f"Run failed with status {status}: {describe_run_failure(latest_run)}")
        if time.time() - start_time > timeout_s:
            output = latest_run.get("output") if latest_run else None
            if output is not None:
                if isinstance(output, dict):
                    return output
                return {"answer": str(output)}
            raise TimeoutError(f"Timeout waiting for run output for event {event_id}. Last status: {last_status}")
        time.sleep(poll_interval_s)
        
        
with st.form("rag_query_form"):
    question = st.text_input("Enter your question about the PDFs:")
    top_k = st.number_input("Number of top results to retrieve:", min_value=1, max_value=20, value=3, step=1)
    submit_button = st.form_submit_button("Ask")
    
    if submit_button and question.strip():
        with st.spinner("Sending event and generating response..."):
            try:
                event_id = asyncio.run(send_rag_query_event(question.strip(), int(top_k)))
                output = wait_for_run_output(event_id)
                if output.get("error"):
                    st.error(output["error"])
                    st.stop()
                st.session_state["last_answer"] = output.get("answer", "No answer returned.")
                st.session_state["last_sources"] = output.get("sources", [])
            except Exception as exc:
                st.error(str(exc))
                st.stop()

if st.session_state.get("last_answer"):
    st.subheader("Answer:")
    st.write(st.session_state["last_answer"])
    sources = st.session_state.get("last_sources", [])
    if sources:
        st.caption("Sources")
        for s in sources:
            st.write(f"- {s}")
