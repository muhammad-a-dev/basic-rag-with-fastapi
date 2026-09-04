"""Unit tests for path/source helpers and upload validation."""

from pathlib import Path

from langchain_core.documents import Document

from rag.ingestion import get_file_extension, is_allowed_upload
from rag.retriever import extract_sources, generate_augmented_prompt, normalize_source_label


def test_get_file_extension_lowercases() -> None:
    assert get_file_extension("Report.PDF") == ".pdf"


def test_is_allowed_upload() -> None:
    assert is_allowed_upload("notes.txt") is True
    assert is_allowed_upload("paper.pdf") is True
    assert is_allowed_upload("image.png") is False
    assert is_allowed_upload(None) is False
    assert is_allowed_upload("") is False


def test_normalize_source_label_uses_filename() -> None:
    windows_style = "temp" + chr(92) + "essay.pdf"
    assert normalize_source_label(windows_style) == "essay.pdf"
    assert normalize_source_label("temp/essay.pdf") == "essay.pdf"


def test_normalize_source_label_relative_to_temp_dir(tmp_path: Path) -> None:
    source = tmp_path / "uploads" / "doc.txt"
    label = normalize_source_label(str(source), temp_dir=tmp_path / "uploads")
    assert label == "doc.txt"


def test_extract_sources_deduplicates() -> None:
    windows_style = "temp" + chr(92) + "a.txt"
    docs = [
        Document(page_content="a", metadata={"source": "temp/a.txt"}),
        Document(page_content="b", metadata={"source": windows_style}),
        Document(page_content="c", metadata={"source": "temp/b.txt"}),
    ]
    assert extract_sources(docs) == ["a.txt", "b.txt"]


def test_generate_augmented_prompt_includes_docs_and_question() -> None:
    docs = [Document(page_content="Paris is in France.")]
    prompt = generate_augmented_prompt(docs, "Where is Paris?")
    assert "Paris is in France." in prompt
    assert "Where is Paris?" in prompt
    assert "No conversation history." in prompt


def test_generate_augmented_prompt_includes_history() -> None:
    docs = [Document(page_content="context")]
    history = [{"user": "Hi", "ai": "Hello"}]
    prompt = generate_augmented_prompt(docs, "Next?", history=history)
    assert "User: Hi" in prompt
    assert "AI: Hello" in prompt
