"""API-level guards: upload rejection, filename sanitization, query validation."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from api.main import create_app
from api.routes import (
    _MAX_SAFE_FILENAME_LEN,
    _safe_filename,
    _session_history,
    _trim_chat_history,
    chat_history,
)
from api.schemas import QueryRequest
from rag.config import get_settings


@pytest.fixture()
def client() -> TestClient:
    return TestClient(create_app())


def test_safe_filename_strips_path_traversal() -> None:
    assert _safe_filename("../../etc/passwd") == "passwd"
    assert _safe_filename("nested/../secret.txt") == "secret.txt"
    assert _safe_filename("/abs/path/notes.PDF") == "notes.PDF"


def test_safe_filename_sanitizes_special_chars_and_empty() -> None:
    assert _safe_filename("weird name!!.txt") == "weird_name_.txt"
    assert _safe_filename("...") == "upload.bin"
    assert _safe_filename("___") == "upload.bin"


def test_safe_filename_strips_null_bytes() -> None:
    # Nulls are removed before basename; remaining chars still go through the allowlist.
    assert _safe_filename("notes.txt\x00.exe") == "notes.txt.exe"
    assert _safe_filename("\x00") == "upload.bin"


def test_safe_filename_truncates_long_names() -> None:
    long_stem = "a" * (_MAX_SAFE_FILENAME_LEN + 40)
    cleaned = _safe_filename(f"{long_stem}.txt")
    assert len(cleaned) <= _MAX_SAFE_FILENAME_LEN
    assert cleaned.endswith(".txt")


def test_trim_chat_history_keeps_newest_turns() -> None:
    history = [{"user": f"u{i}", "ai": f"a{i}"} for i in range(5)]
    _trim_chat_history(history, max_turns=3)
    assert history == [
        {"user": "u2", "ai": "a2"},
        {"user": "u3", "ai": "a3"},
        {"user": "u4", "ai": "a4"},
    ]


def test_trim_chat_history_noop_when_under_limit() -> None:
    history = [{"user": "u", "ai": "a"}]
    _trim_chat_history(history, max_turns=5)
    assert history == [{"user": "u", "ai": "a"}]


def test_session_history_evicts_oldest_when_over_cap() -> None:
    chat_history.clear()
    try:
        _session_history("s1", max_sessions=2)
        _session_history("s2", max_sessions=2)
        assert set(chat_history) == {"s1", "s2"}
        _session_history("s3", max_sessions=2)
        assert "s1" not in chat_history
        assert set(chat_history) == {"s2", "s3"}
        # Existing session must not trigger another eviction.
        _session_history("s2", max_sessions=2)
        assert set(chat_history) == {"s2", "s3"}
    finally:
        chat_history.clear()


def test_ingest_rejects_disallowed_extension(client: TestClient) -> None:
    response = client.post(
        "/api/ingest",
        files={"file": ("malware.exe", b"not-a-real-binary", "application/octet-stream")},
    )
    assert response.status_code == 400
    assert "Only PDF and TXT" in response.json()["detail"]


def test_ingest_rejects_png_upload(client: TestClient) -> None:
    response = client.post(
        "/api/ingest",
        files={"file": ("photo.png", b"\x89PNG", "image/png")},
    )
    assert response.status_code == 400
    assert "Invalid file type" in response.json()["detail"]


def test_ingest_rejects_null_byte_filename(client: TestClient) -> None:
    response = client.post(
        "/api/ingest",
        files={"file": ("notes.txt\x00.exe", b"hello", "text/plain")},
    )
    assert response.status_code == 400
    assert "Invalid file type" in response.json()["detail"]


def test_ingest_rejects_empty_upload(client: TestClient) -> None:
    response = client.post(
        "/api/ingest",
        files={"file": ("notes.txt", b"", "text/plain")},
    )
    assert response.status_code == 400
    assert "Empty uploads" in response.json()["detail"]


def test_ingest_rejects_oversized_upload(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("MAX_UPLOAD_BYTES", "32")
    monkeypatch.setenv("TEMP_UPLOAD_DIR", str(tmp_path))
    get_settings.cache_clear()
    try:
        oversized = TestClient(create_app())
        response = oversized.post(
            "/api/ingest",
            files={"file": ("notes.txt", b"x" * 64, "text/plain")},
        )
        assert response.status_code == 413
        assert "maximum upload size" in response.json()["detail"]
    finally:
        get_settings.cache_clear()


def test_query_rejects_empty_question_via_api(client: TestClient) -> None:
    response = client.post(
        "/api/query",
        json={"question": "", "session_id": "s1"},
    )
    assert response.status_code == 422


def test_query_rejects_whitespace_only_question_via_api(client: TestClient) -> None:
    response = client.post(
        "/api/query",
        json={"question": "   ", "session_id": "s1"},
    )
    assert response.status_code == 422


def test_query_rejects_invalid_session_id_via_api(client: TestClient) -> None:
    response = client.post(
        "/api/query",
        json={"question": "hello", "session_id": "bad id!"},
    )
    assert response.status_code == 422


def test_query_request_model_rejects_blank_question() -> None:
    with pytest.raises(ValidationError):
        QueryRequest(question="\t\n", session_id="ok")
