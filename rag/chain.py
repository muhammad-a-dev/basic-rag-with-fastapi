"""RAG orchestration: retrieve context, build prompt, stream an answer."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from langchain_core.documents import Document

from rag.config import Settings, get_settings
from rag.ingestion import embedding_model
from rag.retriever import (
    extract_sources,
    generate_augmented_prompt,
    llm_model,
    query_retriever,
    response_generator,
    vectorstore_initializer,
)

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class RagResult:
    """Container for retrieval output used by the API layer."""

    documents: list[Document]
    sources: list[str]
    prompt: str


class RagChain:
    """Thin orchestration layer over embedding, retrieval, and generation."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def retrieve(
        self,
        question: str,
        history: list[dict[str, str]] | None = None,
        *,
        vectorstore: Any | None = None,
    ) -> RagResult | None:
        """Retrieve relevant docs and build an augmented prompt."""
        store = vectorstore or vectorstore_initializer(
            embedding_model(settings=self.settings),
            settings=self.settings,
        )
        documents = query_retriever(store, question, settings=self.settings)
        if not documents:
            logger.info("No documents retrieved for question")
            return None

        sources = extract_sources(documents, temp_dir=self.settings.temp_path)
        prompt = generate_augmented_prompt(documents, question, history=history)
        logger.info("Retrieved %s docs; sources=%s", len(documents), sources)
        return RagResult(documents=documents, sources=sources, prompt=prompt)

    def stream_answer(
        self,
        prompt: str,
        *,
        model: Any | None = None,
    ) -> Iterator[str]:
        """Stream an LLM answer for a prepared prompt."""
        chat_model = model or llm_model(settings=self.settings)
        yield from response_generator(chat_model, prompt)


def get_rag_chain(settings: Settings | None = None) -> RagChain:
    """Factory used by the API routes."""
    return RagChain(settings=settings)
