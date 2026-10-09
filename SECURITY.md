# Security Policy

## Supported versions

This repository is a portfolio/learning project. Only the latest `main` branch receives fixes.

## Reporting a vulnerability

Please **do not** open a public issue for security-sensitive findings.

Email or privately message the repository owner (`muhammad-a-dev`) with:

- a short description of the issue
- steps to reproduce
- impact assessment if known

## Secrets handling

- Never commit `.env`, API keys, tokens, or credentials.
- Use [`.env.example`](.env.example) as the template. Keep placeholder values empty in git; put real `HUGGINGFACE_API_KEY` / `GROQ_API_KEY` values only in a local `.env` or a secret manager.
- Do not log, print, or return raw API keys in responses, exceptions, or CI output.
- Prefer environment variables over hard-coding credentials in examples or tests.
- Rotate any key that may have been exposed (chat, gist, ticket, screenshot).

## Local data stores

Uploaded documents and Chroma embeddings live under `TEMP_UPLOAD_DIR` and `CHROMA_PERSIST_DIRECTORY`. Treat those directories as sensitive if they hold private content. Do not commit them, and avoid sharing volume dumps casually.

## Upload and session bounds

- Ingest reads uploads in chunks and rejects payloads larger than `MAX_UPLOAD_BYTES` (default 10 MiB) as soon as the stream exceeds the cap, so oversized bodies are not fully buffered in memory.
- Empty uploads are rejected before writing to disk.
- After a bounded read, upload bytes must match the declared extension: PDF bodies must start with `%PDF`; TXT bodies must be valid UTF-8 without NUL bytes. Mismatches return HTTP 400 with a fixed message.
- Uploaded filenames are sanitized (null bytes stripped) and truncated to limit path traversal and oversized name abuse; null-byte filenames are rejected as invalid uploads.
- Resolved temp upload paths must stay under `TEMP_UPLOAD_DIR` (blocks symlink escapes outside the temp root).
- `session_id` must be 1-128 characters of letters, digits, `.`, `_`, or `-` (no spaces, null bytes, or control characters).
- In-process chat history is capped by `MAX_CHAT_HISTORY_TURNS` (default 20 newest turns per session), `MAX_CHAT_SESSIONS` (default 100 sessions; oldest sessions are evicted first), and `MAX_STORED_RESPONSE_CHARS` (default 8192 characters kept per stored AI reply).

## Temp uploads and error responses

- Each ingest write uses a unique prefix under `TEMP_UPLOAD_DIR` so same-name uploads cannot overwrite each other.
- Temp upload files are deleted after ingest finishes (success or failure). Document text already lives in Chroma; keeping the raw file on disk is unnecessary.
- HTTP 500 responses for read/save/ingest/query failures use fixed client messages. Exception details stay in server logs only.
- `X-Sources` values are stripped of control characters (including CR/LF) and commas so source labels cannot split or inject response headers.

## Scope notes

This service stores uploaded documents locally and keeps chat history in process memory. Do not deploy it to the public internet without authentication, rate limiting, and hardened storage.
