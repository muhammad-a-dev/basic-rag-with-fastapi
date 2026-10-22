"""Application settings loaded from environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the RAG API."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    huggingface_api_key: str = Field(default="", alias="HUGGINGFACE_API_KEY")
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")

    embedding_model_name: str = Field(
        default="BAAI/bge-small-en-v1.5",
        alias="EMBEDDING_MODEL_NAME",
    )
    llm_model_name: str = Field(
        default="groq:openai/gpt-oss-120b",
        alias="LLM_MODEL_NAME",
    )

    chroma_persist_directory: str = Field(
        default="chroma_db",
        alias="CHROMA_PERSIST_DIRECTORY",
    )
    temp_upload_dir: str = Field(default="temp", alias="TEMP_UPLOAD_DIR")

    # Retrieval knobs are bounded so a bad env value cannot turn every query
    # into a huge paid LLM prompt (RETRIEVER_K x CHUNK_SIZE characters).
    chunk_size: int = Field(default=500, alias="CHUNK_SIZE", ge=1, le=8_000)
    chunk_overlap: int = Field(default=50, alias="CHUNK_OVERLAP", ge=0)
    retriever_k: int = Field(default=3, alias="RETRIEVER_K", ge=1, le=20)
    retriever_score_threshold: float = Field(
        default=0.5,
        alias="RETRIEVER_SCORE_THRESHOLD",
        ge=0.0,
        le=1.0,
    )
    max_upload_bytes: int = Field(
        default=10_485_760,
        alias="MAX_UPLOAD_BYTES",
        ge=1,
    )
    max_ingest_chunks: int = Field(
        default=2_000,
        alias="MAX_INGEST_CHUNKS",
        ge=1,
    )
    # PDF text extraction runs per page before chunking, so a small file with
    # thousands of (possibly blank) pages can still burn CPU for a long time.
    max_pdf_pages: int = Field(
        default=500,
        alias="MAX_PDF_PAGES",
        ge=1,
    )
    max_chat_history_turns: int = Field(
        default=20,
        alias="MAX_CHAT_HISTORY_TURNS",
        ge=1,
    )
    max_chat_sessions: int = Field(
        default=100,
        alias="MAX_CHAT_SESSIONS",
        ge=1,
    )
    max_stored_response_chars: int = Field(
        default=8_192,
        alias="MAX_STORED_RESPONSE_CHARS",
        ge=1,
    )
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    @model_validator(mode="after")
    def _overlap_smaller_than_chunk(self) -> "Settings":
        # The text splitter raises on overlap >= size, which would surface as
        # an HTTP 500 on every ingest. Fail at startup instead.
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("CHUNK_OVERLAP must be smaller than CHUNK_SIZE")
        return self

    @property
    def project_root(self) -> Path:
        return Path(__file__).resolve().parent.parent

    @property
    def chroma_path(self) -> Path:
        path = Path(self.chroma_persist_directory)
        if not path.is_absolute():
            path = self.project_root / path
        return path

    @property
    def temp_path(self) -> Path:
        path = Path(self.temp_upload_dir)
        if not path.is_absolute():
            path = self.project_root / path
        return path


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
