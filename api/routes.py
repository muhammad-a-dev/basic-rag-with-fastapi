"""HTTP routes for document ingestion and streaming RAG queries."""

from __future__ import annotations

import logging
import re
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from api.schemas import EmptyRetrievalResponse, IngestResponse, QueryRequest
from rag.chain import get_rag_chain
from rag.config import get_settings
from rag.ingestion import chunk_document, embedding_model, is_allowed_upload, load_document
from rag.retriever import vectorstore_initializer

logger = logging.getLogger(__name__)

router = APIRouter()
chat_history: dict[str, list[dict[str, str]]] = {}

_SAFE_FILENAME = re.compile(r"[^A-Za-z0-9._-]+")
_MAX_SAFE_FILENAME_LEN = 200


def _safe_filename(filename: str) -> str:
    """Reduce path traversal risk for uploaded filenames."""
    # Null bytes can confuse Path / OS APIs; strip before basenaming.
    name = Path(filename.replace("\x00", "")).name
    cleaned = _SAFE_FILENAME.sub("_", name).strip("._")
    if not cleaned:
        return "upload.bin"
    if len(cleaned) > _MAX_SAFE_FILENAME_LEN:
        suffix = Path(cleaned).suffix[:20]
        stem_budget = _MAX_SAFE_FILENAME_LEN - len(suffix)
        cleaned = f"{cleaned[:stem_budget]}{suffix}" if suffix else cleaned[:_MAX_SAFE_FILENAME_LEN]
    return cleaned


def _trim_chat_history(history: list[dict[str, str]], max_turns: int) -> None:
    """Keep only the newest max_turns conversation turns in place."""
    if max_turns < 1:
        history.clear()
        return
    overflow = len(history) - max_turns
    if overflow > 0:
        del history[:overflow]


def _session_history(
    session_id: str,
    *,
    max_sessions: int,
) -> list[dict[str, str]]:
    """Return chat history for session_id, evicting oldest sessions if needed."""
    if session_id not in chat_history:
        while len(chat_history) >= max_sessions:
            oldest = next(iter(chat_history))
            del chat_history[oldest]
            logger.info("Evicted chat session %s (session cap %s)", oldest, max_sessions)
        chat_history[session_id] = []
    return chat_history[session_id]


@router.post("/ingest", response_model=IngestResponse)
async def ingest(file: UploadFile = File(...)) -> IngestResponse:
    """Accept a PDF/TXT upload, chunk it, and store embeddings in Chroma."""
    settings = get_settings()

    if not is_allowed_upload(file.filename):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Only PDF and TXT files are allowed.",
        )

    assert file.filename is not None
    safe_name = _safe_filename(file.filename)

    try:
        contents = await file.read()
    except OSError as exc:
        logger.exception("Failed to read upload")
        raise HTTPException(status_code=500, detail=f"Failed to read file: {exc}") from exc
    finally:
        await file.close()

    if not contents:
        raise HTTPException(status_code=400, detail="Empty uploads are not allowed.")

    if len(contents) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=413,
            detail=(
                f"File exceeds maximum upload size of {settings.max_upload_bytes} bytes."
            ),
        )

    settings.temp_path.mkdir(parents=True, exist_ok=True)
    file_location = settings.temp_path / safe_name

    try:
        file_location.write_bytes(contents)
    except OSError as exc:
        logger.exception("Failed to save upload")
        raise HTTPException(status_code=500, detail=f"Failed to save file: {exc}") from exc

    try:
        document = load_document(file_location)
        chunks = chunk_document(document, settings=settings)
        embeddings = embedding_model(settings=settings)
        vectorstore = vectorstore_initializer(embeddings, settings=settings)
        vectorstore.add_documents(chunks)
    except Exception as exc:  # noqa: BLE001 - surface pipeline failures to clients
        logger.exception("Ingestion failed for %s", safe_name)
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {exc}") from exc

    logger.info("Ingested %s (%s chunks)", safe_name, len(chunks))
    return IngestResponse(status="success", chunks_stored=len(chunks), filename=safe_name)


@router.post("/query", response_model=None)
def query(request: QueryRequest) -> StreamingResponse | EmptyRetrievalResponse:
    """Retrieve context and stream a grounded answer for the question."""
    settings = get_settings()
    session_id = request.session_id
    question = request.question

    history = _session_history(session_id, max_sessions=settings.max_chat_sessions)
    chain = get_rag_chain(settings)

    try:
        result = chain.retrieve(question, history=history)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Query retrieval failed")
        raise HTTPException(status_code=500, detail=f"Query failed: {exc}") from exc

    if result is None:
        return EmptyRetrievalResponse(
            response="No relevant documents found to answer the question.",
            sources=[],
        )

    def stream_and_save_response():
        collected_response = ""
        try:
            for chunk in chain.stream_answer(result.prompt):
                collected_response += chunk
                yield chunk
        except Exception:
            logger.exception("Streaming generation failed")
            raise
        history.append({"user": question, "ai": collected_response})
        _trim_chat_history(history, settings.max_chat_history_turns)

    return StreamingResponse(
        stream_and_save_response(),
        media_type="text/plain",
        headers={"X-Sources": ", ".join(result.sources)},
    )
