"""API-level guards: upload rejection, filename sanitization, query validation."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from api.main import create_app
from api.routes import _safe_filename
from api.schemas import QueryRequest


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


def test_query_request_model_rejects_blank_question() -> None:
    with pytest.raises(ValidationError):
        QueryRequest(question="\t\n", session_id="ok")
