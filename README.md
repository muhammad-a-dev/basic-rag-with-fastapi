# Basic RAG with FastAPI

A focused Retrieval-Augmented Generation (RAG) service that lets you ingest PDF/TXT documents, store embeddings in a local Chroma database, and stream grounded answers from an LLM.

This repository is a **portfolio / learning capstone**, not a turnkey production platform. It demonstrates clean FastAPI layering, LangChain retrieval, streaming responses, configuration hygiene, tests, and CI.

## Problem

Building a useful Q&A experience over private documents usually requires:

1. accepting uploads,
2. chunking and embedding content,
3. retrieving only relevant context,
4. generating answers that stay grounded in that context,
5. returning tokens quickly enough to feel interactive.

Many demos stop at a notebook. This project packages those steps behind a small HTTP API.

## Solution

- **Ingest** PDF or TXT files through `POST /api/ingest`
- **Persist** chunk embeddings in local Chroma
- **Query** with `POST /api/query`, retrieving top relevant chunks and streaming the LLM response
- Keep lightweight **in-memory session history** so follow-up questions can reference prior turns

## Features

- FastAPI endpoints with Pydantic request validation
- Recursive character chunking
- Hugging Face endpoint embeddings (`BAAI/bge-small-en-v1.5` by default)
- Similarity-threshold retrieval via Chroma
- Token streaming responses (`text/plain`) with `X-Sources` header
- pydantic-settings configuration (`.env` supported)
- Structured logging (no `print` debugging in the request path)
- Unit tests and GitHub Actions CI that run **without real API keys**
- Optional offline RAGAS evaluation script under `eval/`

## Architecture

```text
Client
  │
  ├─ POST /api/ingest  → load → chunk → embed → Chroma
  │
  └─ POST /api/query   → retrieve → augment prompt → stream LLM tokens
```

Layering:

| Layer | Responsibility |
| --- | --- |
| `api/` | HTTP routes, upload handling, response streaming |
| `rag/` | settings, ingestion, retrieval, chain orchestration |
| `eval/` | offline quality evaluation (not part of CI) |
| `tests/` | unit tests with mocked LLM / vector store |

## Stack

- Python 3.11+
- FastAPI + Uvicorn
- LangChain (+ community / Hugging Face / text-splitters)
- ChromaDB
- pydantic-settings
- pytest + ruff (dev)
- RAGAS + datasets (optional eval extras)

## Install

```bash
git clone https://github.com/muhammad-a-dev/basic-rag-with-fastapi.git
cd basic-rag-with-fastapi
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

For offline evaluation tooling:

```bash
pip install -e ".[dev,eval]"
```

## Configuration

Copy the example env file and fill in secrets locally:

```bash
cp .env.example .env
```

| Variable | Purpose |
| --- | --- |
| `HUGGINGFACE_API_KEY` | Hugging Face Inference embeddings |
| `GROQ_API_KEY` | Groq-hosted chat model used by LangChain |
| `EMBEDDING_MODEL_NAME` | Defaults to `BAAI/bge-small-en-v1.5` |
| `LLM_MODEL_NAME` | Defaults to `groq:openai/gpt-oss-120b` |
| `CHROMA_PERSIST_DIRECTORY` | Local vector store directory |
| `TEMP_UPLOAD_DIR` | Temporary upload storage |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | Chunking parameters |
| `RETRIEVER_K` / `RETRIEVER_SCORE_THRESHOLD` | Retrieval knobs |
| `LOG_LEVEL` | Logging verbosity |

Never commit `.env`.

## Usage

Start the API:

```bash
uvicorn api.main:app --reload
```

Open interactive docs at `http://127.0.0.1:8000/docs`.

### Ingest a document

```bash
curl -X POST "http://127.0.0.1:8000/api/ingest" \
  -F "file=@./sample.txt"
```

### Ask a question (streamed plain text)

```bash
curl -N -X POST "http://127.0.0.1:8000/api/query" \
  -H "Content-Type: application/json" \
  -d '{"question":"What is the main claim?","session_id":"demo-1"}'
```

Successful retrieval streams tokens and includes an `X-Sources` response header. If nothing relevant is found, the API returns JSON explaining that no documents matched.

## Project structure

```text
.
├── api/
│   ├── main.py          # FastAPI app factory, logging, health
│   ├── routes.py        # /ingest and /query
│   └── schemas.py       # request/response models
├── rag/
│   ├── config.py        # pydantic-settings
│   ├── ingestion.py     # load / chunk / embeddings
│   ├── retriever.py     # Chroma, prompt, streaming helpers
│   └── chain.py         # retrieve + stream orchestration
├── eval/
│   ├── evaluate.py      # optional RAGAS script
│   └── evaluate.ipynb   # exploratory notebook
├── tests/               # unit tests (mocked providers)
├── .github/workflows/ci.yml
├── pyproject.toml
├── .env.example
├── LICENSE
├── CONTRIBUTING.md
└── SECURITY.md
```

## Testing

```bash
ruff check .
pytest
```

CI runs the same checks on pull requests. Provider calls are mocked in unit tests, so no API keys are required for green CI.

## Security

- Secrets belong in environment variables / `.env` (gitignored)
- Upload filenames are sanitized before writing to disk
- Only `.pdf` and `.txt` uploads are accepted
- Chat history is **in-memory only** (lost on restart; not multi-process safe)
- Do not expose this service publicly without auth, rate limits, and hardened storage

See [SECURITY.md](SECURITY.md) for reporting guidance.

## Roadmap

- Persistent session / chat history store
- Authentication and per-user document isolation
- Stronger content safety / prompt-injection defenses
- Docker Compose deployment profile
- Broader evaluation set and regression harness wired to CI (with mocks or fixtures)

## License

MIT — see [LICENSE](LICENSE).
