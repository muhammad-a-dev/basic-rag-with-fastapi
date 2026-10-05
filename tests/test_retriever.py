"""Unit tests for retriever helpers with mocked vector stores and models."""

from types import SimpleNamespace
from unittest.mock import MagicMock

from langchain_core.documents import Document

from rag.config import Settings
from rag.retriever import query_retriever, response_generator, similarity_search


def test_query_retriever_passes_threshold_settings() -> None:
    settings = Settings(retriever_k=5, retriever_score_threshold=0.42)
    docs = [Document(page_content="hit")]
    retriever = MagicMock()
    retriever.invoke.return_value = docs
    store = MagicMock()
    store.as_retriever.return_value = retriever

    result = query_retriever(store, "what?", settings=settings)

    assert result == docs
    store.as_retriever.assert_called_once_with(
        search_type="similarity_score_threshold",
        search_kwargs={"k": 5, "score_threshold": 0.42},
    )
    retriever.invoke.assert_called_once_with("what?")


def test_similarity_search_forwards_k() -> None:
    store = MagicMock()
    store.similarity_search.return_value = []

    assert similarity_search(store, "q", k=7) == []
    store.similarity_search.assert_called_once_with("q", k=7)


def test_response_generator_skips_empty_chunks() -> None:
    model = MagicMock()
    model.stream.return_value = iter(
        [
            SimpleNamespace(content="Hello"),
            SimpleNamespace(content=""),
            SimpleNamespace(content=None),
            SimpleNamespace(),
            SimpleNamespace(content=" world"),
        ]
    )

    assert list(response_generator(model, "prompt")) == ["Hello", " world"]
    model.stream.assert_called_once_with("prompt")
