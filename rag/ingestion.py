"""Document loading, chunking, and embedding model factory."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_huggingface import HuggingFaceEndpointEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from rag.config import Settings, get_settings

if TYPE_CHECKING:
    from langchain_core.documents import Document

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".pdf", ".txt"}


def get_file_extension(filename: str) -> str:
    """Return the lowercase file extension including the leading dot."""
    return Path(filename).suffix.lower()


def is_allowed_upload(filename: str | None) -> bool:
    """Return True when the upload filename has an allowed extension."""
    if not filename:
        return False
    return get_file_extension(filename) in ALLOWED_EXTENSIONS


def load_document(file_path: str | Path) -> list[Document]:
    """Load a PDF or TXT file into LangChain documents."""
    path = Path(file_path)
    ext = path.suffix.lower()

    if ext == ".pdf":
        loader = PyPDFLoader(str(path))
    elif ext == ".txt":
        loader = TextLoader(str(path), encoding="utf-8")
    else:
        logger.error("Unsupported file type: %s", ext)
        raise ValueError("Unsupported file type. Only PDF and TXT are allowed.")

    documents = loader.load()
    logger.info("Loaded document %s (%s pages/parts)", path.name, len(documents))
    return documents


def chunk_document(
    document: list[Document],
    *,
    settings: Settings | None = None,
) -> list[Document]:
    """Split documents into overlapping character chunks."""
    cfg = settings or get_settings()
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=cfg.chunk_size,
        chunk_overlap=cfg.chunk_overlap,
    )
    chunks = splitter.split_documents(document)
    logger.info("Split into %s chunks", len(chunks))
    return chunks


def embedding_model(
    *,
    settings: Settings | None = None,
) -> HuggingFaceEndpointEmbeddings:
    """Create the Hugging Face endpoint embedding client."""
    cfg = settings or get_settings()
    return HuggingFaceEndpointEmbeddings(
        model=cfg.embedding_model_name,
        huggingfacehub_api_token=cfg.huggingface_api_key or None,
    )
