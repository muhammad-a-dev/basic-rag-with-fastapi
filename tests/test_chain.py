"""Unit tests for RagChain orchestration with mocked dependencies."""

from unittest.mock import MagicMock, patch

from langchain_core.documents import Document

from rag.chain import RagChain, RagResult
from rag.config import Settings


def _settings() -> Settings:
    return Settings(
        huggingface_api_key="",
        groq_api_key="",
        chroma_persist_directory="chroma_db",
        temp_upload_dir="temp",
    )


def test_retrieve_returns_none_when_no_docs() -> None:
    chain = RagChain(settings=_settings())
    store = MagicMock()

    with patch("rag.chain.query_retriever", return_value=[]):
        result = chain.retrieve("question?", history=[], vectorstore=store)

    assert result is None


def test_retrieve_builds_prompt_and_sources() -> None:
    chain = RagChain(settings=_settings())
    store = MagicMock()
    docs = [Document(page_content="useful context", metadata={"source": "temp/doc.txt"})]

    with patch("rag.chain.query_retriever", return_value=docs):
        result = chain.retrieve("What?", history=[{"user": "u", "ai": "a"}], vectorstore=store)

    assert isinstance(result, RagResult)
    assert result.documents == docs
    assert result.sources == ["doc.txt"]
    assert "useful context" in result.prompt
    assert "What?" in result.prompt


def test_stream_answer_yields_chunks() -> None:
    chain = RagChain(settings=_settings())
    model = MagicMock()

    with patch("rag.chain.response_generator", return_value=iter(["Hello", " world"])):
        chunks = list(chain.stream_answer("prompt", model=model))

    assert chunks == ["Hello", " world"]
