"""Unit tests for API request validation."""

import pytest
from pydantic import ValidationError

from api.schemas import QueryRequest


def test_query_request_accepts_valid_payload() -> None:
    req = QueryRequest(question="What is RAG?", session_id="session-1")
    assert req.question == "What is RAG?"
    assert req.session_id == "session-1"


def test_query_request_strips_whitespace() -> None:
    req = QueryRequest(question="  hello  ", session_id="  abc  ")
    assert req.question == "hello"
    assert req.session_id == "abc"


def test_query_request_rejects_blank_question() -> None:
    with pytest.raises(ValidationError):
        QueryRequest(question="   ", session_id="session-1")


def test_query_request_rejects_empty_question() -> None:
    with pytest.raises(ValidationError):
        QueryRequest(question="", session_id="session-1")


def test_query_request_rejects_overlong_question() -> None:
    with pytest.raises(ValidationError):
        QueryRequest(question="x" * 501, session_id="session-1")


def test_query_request_rejects_blank_session_id() -> None:
    with pytest.raises(ValidationError):
        QueryRequest(question="hello", session_id="  ")
