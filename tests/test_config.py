"""Unit tests for settings helpers."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from rag.config import Settings


def test_chroma_path_is_absolute_under_project_root() -> None:
    settings = Settings(chroma_persist_directory="chroma_db")
    assert settings.chroma_path.is_absolute()
    assert settings.chroma_path.name == "chroma_db"
    assert settings.project_root in settings.chroma_path.parents


def test_temp_path_respects_absolute_override(tmp_path: Path) -> None:
    settings = Settings(temp_upload_dir=str(tmp_path))
    assert settings.temp_path == tmp_path


def test_chroma_path_respects_absolute_override(tmp_path: Path) -> None:
    settings = Settings(chroma_persist_directory=str(tmp_path))
    assert settings.chroma_path == tmp_path


def test_numeric_knobs_coerce_from_strings() -> None:
    """Env vars arrive as strings; Settings should coerce chunk/retriever knobs."""
    settings = Settings(
        chunk_size="750",
        chunk_overlap="75",
        retriever_k="5",
        retriever_score_threshold="0.35",
        max_upload_bytes="2048",
        max_chat_history_turns="8",
        max_chat_sessions="50",
        max_stored_response_chars="4096",
        max_ingest_chunks="250",
        max_pdf_pages="40",
    )
    assert settings.chunk_size == 750
    assert settings.chunk_overlap == 75
    assert settings.retriever_k == 5
    assert settings.retriever_score_threshold == 0.35
    assert settings.max_upload_bytes == 2048
    assert settings.max_chat_history_turns == 8
    assert settings.max_chat_sessions == 50
    assert settings.max_stored_response_chars == 4096
    assert settings.max_ingest_chunks == 250
    assert settings.max_pdf_pages == 40


def test_upload_and_history_bounds_reject_zero() -> None:
    with pytest.raises(ValidationError):
        Settings(max_upload_bytes=0)
    with pytest.raises(ValidationError):
        Settings(max_chat_history_turns=0)
    with pytest.raises(ValidationError):
        Settings(max_chat_sessions=0)
    with pytest.raises(ValidationError):
        Settings(max_stored_response_chars=0)
    with pytest.raises(ValidationError):
        Settings(max_ingest_chunks=0)
    with pytest.raises(ValidationError):
        Settings(max_pdf_pages=0)


def test_retrieval_knobs_reject_out_of_range_values() -> None:
    with pytest.raises(ValidationError):
        Settings(retriever_k=0)
    with pytest.raises(ValidationError):
        Settings(retriever_k=21)
    with pytest.raises(ValidationError):
        Settings(chunk_size=0)
    with pytest.raises(ValidationError):
        Settings(chunk_size=8_001)
    with pytest.raises(ValidationError):
        Settings(chunk_overlap=-1)
    with pytest.raises(ValidationError):
        Settings(retriever_score_threshold=-0.1)
    with pytest.raises(ValidationError):
        Settings(retriever_score_threshold=1.5)


def test_retrieval_knobs_accept_edge_values() -> None:
    settings = Settings(
        retriever_k=20,
        chunk_size=8_000,
        chunk_overlap=0,
        retriever_score_threshold=1.0,
    )
    assert settings.retriever_k == 20
    assert settings.chunk_size == 8_000
    assert settings.chunk_overlap == 0
    assert settings.retriever_score_threshold == 1.0


def test_chunk_overlap_must_be_smaller_than_chunk_size() -> None:
    with pytest.raises(ValidationError, match="CHUNK_OVERLAP"):
        Settings(chunk_size=100, chunk_overlap=100)
    with pytest.raises(ValidationError, match="CHUNK_OVERLAP"):
        Settings(chunk_size=100, chunk_overlap=150)
    assert Settings(chunk_size=100, chunk_overlap=99).chunk_overlap == 99


def test_out_of_range_env_var_fails_fast(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RETRIEVER_K", "500")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)
