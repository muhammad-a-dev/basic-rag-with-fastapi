"""Vector store helpers, retrieval, prompting, and LLM streaming."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from langchain.chat_models import init_chat_model
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

from rag.config import Settings, get_settings

logger = logging.getLogger(__name__)


def llm_model(*, settings: Settings | None = None):
    """Initialize the configured chat model."""
    cfg = settings or get_settings()
    return init_chat_model(cfg.llm_model_name, temperature=0)


def vectorstore_initializer(
    embedding_model: Any,
    *,
    settings: Settings | None = None,
) -> Chroma:
    """Open (or create) the persistent Chroma vector store."""
    cfg = settings or get_settings()
    persist_directory = str(cfg.chroma_path)
    cfg.chroma_path.mkdir(parents=True, exist_ok=True)
    vectorstore = Chroma(
        persist_directory=persist_directory,
        embedding_function=embedding_model,
    )
    logger.info("Initialized Chroma vector store at %s", persist_directory)
    return vectorstore


def query_retriever(
    vectorstore: Chroma,
    question: str,
    *,
    settings: Settings | None = None,
) -> list[Document]:
    """Retrieve documents using similarity score thresholding."""
    cfg = settings or get_settings()
    retriever = vectorstore.as_retriever(
        search_type="similarity_score_threshold",
        search_kwargs={
            "k": cfg.retriever_k,
            "score_threshold": cfg.retriever_score_threshold,
        },
    )
    return retriever.invoke(question)


def similarity_search(
    vectorstore: Chroma,
    question: str,
    *,
    k: int = 3,
) -> list[Document]:
    """Simple top-k similarity search (used by offline evaluation)."""
    return vectorstore.similarity_search(question, k=k)


def normalize_source_label(source: str, temp_dir: str | Path | None = None) -> str:
    """Normalize a document source path for response headers (cross-platform)."""
    # Normalize Windows separators so Path.name behaves consistently on Linux CI.
    normalized = source.replace("\\", "/")
    path = Path(normalized)
    label = path.name
    if temp_dir is not None:
        try:
            label = str(path.relative_to(Path(temp_dir))).replace("\\", "/")
        except ValueError:
            label = path.name
    return label


def extract_sources(
    docs: list[Document],
    *,
    temp_dir: str | Path | None = None,
) -> list[str]:
    """Return unique, display-friendly source labels from retrieved docs."""
    sources: list[str] = []
    seen: set[str] = set()
    for doc in docs:
        raw = str(doc.metadata.get("source", "unknown"))
        label = normalize_source_label(raw, temp_dir=temp_dir)
        if label not in seen:
            seen.add(label)
            sources.append(label)
    return sources


def generate_augmented_prompt(
    docs: list[Document],
    question: str,
    history: list[dict[str, str]] | None = None,
) -> str:
    """Build a grounded prompt from retrieved docs and optional chat history."""
    docs_content = "\n\n".join(doc.page_content for doc in docs)

    if history:
        history_text = "\n\n".join(
            f"User: {turn['user']}\nAI: {turn['ai']}" for turn in history
        )
    else:
        history_text = "No conversation history."

    return (
        "Answer the question based on the following retrieved documents only:\n\n"
        f"{docs_content}\n\n"
        f"Question: {question}.\n"
        f"Conversation history: {history_text}. "
        "If the answer is not contained within the retrieved documents, say you don't know "
        "with a brief reason, a general reply, or a clarifying question. Max 30 words."
    )


def response_generator(model: Any, augmented_prompt: str) -> Iterator[str]:
    """Yield streamed token chunks from the chat model."""
    for chunk in model.stream(augmented_prompt):
        content = getattr(chunk, "content", None)
        if content:
            yield content
