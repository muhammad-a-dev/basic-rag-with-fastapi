# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Keep a Changelog file so release history is easy to find from the README.
- Config unit tests for string-env coercion of chunk/retriever knobs and absolute Chroma path overrides.
- Helper unit tests for unsupported upload rejection, chunk splitting, missing-source labels, and extension edge cases.
- Upload size cap (`MAX_UPLOAD_BYTES`, default 10 MiB), empty-upload rejection, long filename truncation, and in-memory chat history trim (`MAX_CHAT_HISTORY_TURNS`).
- Concurrent chat session cap (`MAX_CHAT_SESSIONS`, default 100) with oldest-first eviction.

### Changed

- Clarified in the README that chat history is in-memory only and not multi-process safe.
- Tightened secrets guidance in `SECURITY.md` and `.env.example` (empty keys in git, no key logging, treat local Chroma/upload dirs as sensitive).

### Security

- Reject empty and oversized ingest payloads before writing to disk; document upload/history bounds in `SECURITY.md`.
- Reject null-byte upload filenames; constrain `session_id` to safe characters; strip null bytes during filename sanitization; cap concurrent in-memory chat sessions.

## [0.1.0] - 2026-09-04

Initial public portfolio release of **basic-rag-with-fastapi** — a focused RAG HTTP API for document Q&A.

### Added

- FastAPI ingest (`POST /api/ingest`) for PDF and TXT uploads
- Local Chroma persistence for chunk embeddings
- Streaming query endpoint (`POST /api/query`) with `X-Sources` header
- Hugging Face embeddings (`BAAI/bge-small-en-v1.5` by default) and Groq-hosted chat model
- pydantic-settings configuration via `.env`
- Upload filename sanitization and filetype allowlist (`.pdf` / `.txt`)
- Unit tests with mocked providers (no API keys required for CI)
- GitHub Actions CI (ruff + pytest)
- Optional offline RAGAS evaluation under `eval/`
- Dockerfile with non-root runtime and `/health` check
- Community hygiene: MIT license, CONTRIBUTING, SECURITY

### Security

- Secrets stay in environment variables; `.env` is gitignored
- Service is a portfolio/learning capstone — not meant for public exposure without auth and rate limits
