"""FastAPI application entrypoint."""

from __future__ import annotations

import logging

from fastapi import FastAPI

from api.routes import router as api_router
from rag.config import get_settings


def configure_logging(level: str) -> None:
    """Configure structured-ish application logging once at startup."""
    root = logging.getLogger()
    if not root.handlers:
        logging.basicConfig(
            level=getattr(logging, level.upper(), logging.INFO),
            format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        )
    else:
        root.setLevel(getattr(logging, level.upper(), logging.INFO))


def create_app() -> FastAPI:
    """Application factory used by uvicorn and tests."""
    settings = get_settings()
    configure_logging(settings.log_level)

    application = FastAPI(
        title="Basic RAG with FastAPI",
        description=(
            "Document ingestion and streaming RAG queries over a local Chroma vector store."
        ),
        version="0.1.0",
    )
    application.include_router(api_router, prefix="/api")

    @application.get("/")
    def read_root() -> dict[str, str]:
        return {
            "service": "basic-rag-with-fastapi",
            "docs": "/docs",
            "ingest": "/api/ingest",
            "query": "/api/query",
        }

    @application.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return application


app = create_app()
