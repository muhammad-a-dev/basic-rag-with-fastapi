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
- After chunking, an upload that produces more than `MAX_INGEST_CHUNKS` chunks (default 2000) is rejected with HTTP 413 before any embedding request is made. A small but text-dense file can otherwise fan out into thousands of paid embedding calls and Chroma rows. The temp file is still deleted.
- PDF uploads with more than `MAX_PDF_PAGES` pages (default 500) are rejected with HTTP 413. The page count is read from the PDF page tree before any text extraction, so a small file with thousands of pages cannot keep a worker busy inside the PDF loader. The temp file is still deleted.
- After a bounded read, upload bytes must match the declared extension: PDF bodies must start with `%PDF`; TXT bodies must be valid UTF-8 without NUL bytes. Mismatches return HTTP 400 with a fixed message.
- Uploaded filenames are sanitized (null bytes stripped) and truncated to limit path traversal and oversized name abuse; null-byte filenames are rejected as invalid uploads.
- Resolved temp upload paths must stay under `TEMP_UPLOAD_DIR` (blocks symlink escapes outside the temp root).
- `session_id` must be 1-128 characters of letters, digits, `.`, `_`, or `-` (no spaces, null bytes, or control characters).
- In-process chat history is capped by `MAX_CHAT_HISTORY_TURNS` (default 20 newest turns per session), `MAX_CHAT_SESSIONS` (default 100 sessions; oldest sessions are evicted first), and `MAX_STORED_RESPONSE_CHARS` (default 8192 characters kept per stored AI reply). While streaming, the in-memory collector for that stored reply stops growing once the cap is reached so a long LLM stream cannot inflate process memory for history.

## Retrieval and chunking bounds

- `RETRIEVER_K` must be 1-20 and `CHUNK_SIZE` must be 1-8000 characters. Each query sends up to `RETRIEVER_K` x `CHUNK_SIZE` characters of context to the paid LLM, so an unbounded value (for example a typo like `RETRIEVER_K=500`) would make every request a very large prompt.
- `CHUNK_OVERLAP` must be 0 or more and smaller than `CHUNK_SIZE`; otherwise the text splitter would fail on every ingest at request time.
- `RETRIEVER_SCORE_THRESHOLD` must be between 0 and 1.
- Out-of-range values fail settings validation at startup instead of surfacing later as HTTP 500 responses.

## Temp uploads and error responses

- Each ingest write uses a unique prefix under `TEMP_UPLOAD_DIR` so same-name uploads cannot overwrite each other.
- Temp upload files are deleted after ingest finishes (success or failure). Document text already lives in Chroma; keeping the raw file on disk is unnecessary.
- HTTP 500 responses for read/save/ingest/query failures use fixed client messages. Exception details stay in server logs only.
- `X-Sources` values are stripped of control characters (including CR/LF) and commas so source labels cannot split or inject response headers.

## Scope notes

This service stores uploaded documents locally and keeps chat history in process memory. Do not deploy it to the public internet without authentication, rate limiting, and hardened storage.
