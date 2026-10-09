"""API-level guards: upload rejection, filename sanitization, query validation."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from api.main import create_app
from api.routes import (
    _MAX_SAFE_FILENAME_LEN,
    _ensure_under_dir,
    _read_upload_bounded,
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



def test_ingest_rejects_pdf_without_magic(client: TestClient) -> None:
    response = client.post(
        "/api/ingest",
        files={"file": ("fake.pdf", b"plain text disguised as pdf", "application/pdf")},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "File content does not match the declared type."


def test_ingest_rejects_txt_with_nul(client: TestClient) -> None:
    response = client.post(
        "/api/ingest",
        files={"file": ("notes.txt", b"hello\x00world", "text/plain")},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "File content does not match the declared type."


def test_ingest_rejects_txt_non_utf8(client: TestClient) -> None:
    response = client.post(
        "/api/ingest",
        files={"file": ("notes.txt", b"\xff\xfe binary junk", "text/plain")},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "File content does not match the declared type."


def test_ingest_accepts_pdf_with_magic(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.setenv("TEMP_UPLOAD_DIR", str(tmp_path))
    get_settings.cache_clear()

    def fake_load(_path):
        return [object()]

    def fake_chunk(document, settings=None):
        return [object(), object()]

    class FakeEmbeddings:
        pass

    class FakeStore:
        def add_documents(self, chunks):
            return None

    monkeypatch.setattr("api.routes.load_document", fake_load)
    monkeypatch.setattr("api.routes.chunk_document", fake_chunk)
    monkeypatch.setattr("api.routes.embedding_model", lambda settings=None: FakeEmbeddings())
    monkeypatch.setattr(
        "api.routes.vectorstore_initializer",
        lambda embeddings, settings=None: FakeStore(),
    )
    try:
        client = TestClient(create_app())
        response = client.post(
            "/api/ingest",
            files={"file": ("paper.pdf", b"%PDF-1.4\n1 0 obj", "application/pdf")},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "success"
        assert body["chunks_stored"] == 2
        assert body["filename"] == "paper.pdf"
    finally:
        get_settings.cache_clear()


def test_ingest_accepts_utf8_txt(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.setenv("TEMP_UPLOAD_DIR", str(tmp_path))
    get_settings.cache_clear()

    def fake_load(_path):
        return [object()]

    def fake_chunk(document, settings=None):
        return [object()]

    class FakeEmbeddings:
        pass

    class FakeStore:
        def add_documents(self, chunks):
            return None

    monkeypatch.setattr("api.routes.load_document", fake_load)
    monkeypatch.setattr("api.routes.chunk_document", fake_chunk)
    monkeypatch.setattr("api.routes.embedding_model", lambda settings=None: FakeEmbeddings())
    monkeypatch.setattr(
        "api.routes.vectorstore_initializer",
        lambda embeddings, settings=None: FakeStore(),
    )
    try:
        client = TestClient(create_app())
        response = client.post(
            "/api/ingest",
            files={"file": ("notes.txt", "hello world".encode("utf-8"), "text/plain")},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "success"
        assert body["chunks_stored"] == 1
        assert body["filename"] == "notes.txt"
    finally:
        get_settings.cache_clear()


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


def test_header_safe_sources_strips_controls_and_commas() -> None:
    from api.routes import _header_safe_sources

    assert _header_safe_sources(["notes.txt", "a,b\r\nSet-Cookie: x"]) == (
        "notes.txt, a bSet-Cookie: x"
    )
    assert _header_safe_sources(["\x00", "  "]) == ""


def test_unique_upload_path_prefixes_safe_name(tmp_path) -> None:
    from api.routes import _unique_upload_path

    path = _unique_upload_path(tmp_path, "notes.txt")
    assert path.parent == tmp_path
    assert path.name.endswith("_notes.txt")
    assert len(path.name.split("_", 1)[0]) == 12


def test_ingest_removes_temp_file_after_pipeline_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.setenv("TEMP_UPLOAD_DIR", str(tmp_path))
    get_settings.cache_clear()

    def boom(*_args, **_kwargs):
        raise RuntimeError("secret path /var/leak and key sk-test")

    monkeypatch.setattr("api.routes.load_document", boom)
    try:
        client = TestClient(create_app())
        response = client.post(
            "/api/ingest",
            files={"file": ("notes.txt", b"hello world", "text/plain")},
        )
        assert response.status_code == 500
        detail = response.json()["detail"]
        assert detail == "Ingestion failed."
        assert "secret" not in detail
        assert "sk-test" not in detail
        leftovers = list(tmp_path.iterdir())
        assert leftovers == []
    finally:
        get_settings.cache_clear()


@pytest.mark.asyncio
async def test_read_upload_bounded_accepts_exact_max() -> None:
    import io

    from starlette.datastructures import Headers
    from starlette.datastructures import UploadFile as StarletteUploadFile

    body = b"x" * 32
    upload = StarletteUploadFile(
        file=io.BytesIO(body),
        filename="notes.txt",
        headers=Headers({"content-type": "text/plain"}),
    )
    assert await _read_upload_bounded(upload, 32) == body


@pytest.mark.asyncio
async def test_read_upload_bounded_rejects_oversize() -> None:
    import io

    from starlette.datastructures import Headers
    from starlette.datastructures import UploadFile as StarletteUploadFile

    body = b"x" * 33
    upload = StarletteUploadFile(
        file=io.BytesIO(body),
        filename="notes.txt",
        headers=Headers({"content-type": "text/plain"}),
    )
    with pytest.raises(ValueError, match="upload_too_large"):
        await _read_upload_bounded(upload, 32)


def test_ensure_under_dir_accepts_child(tmp_path) -> None:
    child = tmp_path / "a" / "b.txt"
    child.parent.mkdir(parents=True)
    child.write_text("ok", encoding="utf-8")
    assert _ensure_under_dir(child, tmp_path) == child.resolve()


def test_ensure_under_dir_rejects_escape(tmp_path) -> None:
    outside = tmp_path.parent / "outside.txt"
    with pytest.raises(ValueError, match="path_escapes_root"):
        _ensure_under_dir(outside, tmp_path)


def test_stored_response_cap_applied_in_query_stream(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Streaming may yield a long answer; only the configured prefix is stored."""
    from types import SimpleNamespace

    chat_history.clear()
    get_settings.cache_clear()
    monkeypatch.setenv("MAX_STORED_RESPONSE_CHARS", "10")
    get_settings.cache_clear()

    class FakeChain:
        def retrieve(self, question, history=None):
            return SimpleNamespace(prompt="p", sources=["notes.txt"])

        def stream_answer(self, prompt):
            yield "abcdefghijklmnop"

    monkeypatch.setattr("api.routes.get_rag_chain", lambda settings: FakeChain())
    try:
        client = TestClient(create_app())
        with client.stream(
            "POST",
            "/api/query",
            json={"question": "hello", "session_id": "cap-test"},
        ) as response:
            assert response.status_code == 200
            body = b"".join(response.iter_bytes()).decode()
        assert body == "abcdefghijklmnop"
        assert chat_history["cap-test"][0]["ai"] == "abcdefghij"
    finally:
        chat_history.clear()
        get_settings.cache_clear()
