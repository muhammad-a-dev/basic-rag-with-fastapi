"""Pydantic request and response models."""

import re

from pydantic import BaseModel, Field, field_validator

_SESSION_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,128}$")


class QueryRequest(BaseModel):
    """Body for POST /api/query."""

    question: str = Field(..., min_length=1, max_length=500)
    session_id: str = Field(..., min_length=1, max_length=128)

    @field_validator("question")
    @classmethod
    def strip_question(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("question must not be blank")
        if "\x00" in cleaned:
            raise ValueError("question must not contain null bytes")
        return cleaned

    @field_validator("session_id")
    @classmethod
    def strip_session_id(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("session_id must not be blank")
        if "\x00" in cleaned or not _SESSION_ID_RE.fullmatch(cleaned):
            raise ValueError(
                "session_id must be 1-128 chars of letters, digits, ., _, or -"
            )
        return cleaned


class IngestResponse(BaseModel):
    """Response for successful document ingestion."""

    status: str
    chunks_stored: int
    filename: str


class EmptyRetrievalResponse(BaseModel):
    """JSON fallback when retrieval finds no relevant documents."""

    response: str
    sources: list[str]
