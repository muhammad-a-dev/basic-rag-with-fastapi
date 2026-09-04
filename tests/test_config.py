"""Unit tests for settings helpers."""

from pathlib import Path

from rag.config import Settings


def test_chroma_path_is_absolute_under_project_root() -> None:
    settings = Settings(chroma_persist_directory="chroma_db")
    assert settings.chroma_path.is_absolute()
    assert settings.chroma_path.name == "chroma_db"
    assert settings.project_root in settings.chroma_path.parents


def test_temp_path_respects_absolute_override(tmp_path: Path) -> None:
    settings = Settings(temp_upload_dir=str(tmp_path))
    assert settings.temp_path == tmp_path
