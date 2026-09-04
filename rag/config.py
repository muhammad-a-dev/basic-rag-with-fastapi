"""Application settings loaded from environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the RAG API."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
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

    chunk_size: int = Field(default=500, alias="CHUNK_SIZE")
    chunk_overlap: int = Field(default=50, alias="CHUNK_OVERLAP")
    retriever_k: int = Field(default=3, alias="RETRIEVER_K")
    retriever_score_threshold: float = Field(
        default=0.5,
        alias="RETRIEVER_SCORE_THRESHOLD",
    )
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

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
