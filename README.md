# Capstone: Production-Ready RAG API + Git Workflow

A fully production-ready Retrieval-Augmented Generation (RAG) system built with **FastAPI**, **LangChain**, and **Chroma DB**. This repository implements token-by-token streaming responses, multi-session chat history persistence, automated RAGAS quality evaluation, robust safety guardrails, and structured application logging.

This project follows a strict production Git workflow, leveraging separate feature branches, decoupled components, and standard continuous integration practices.

---

## 🏗️ Architecture & Project Structure

The codebase is engineered with a modular, decoupled architecture separating the API presentation layer, core RAG logic, evaluation suites, and data storage.

```text
capstone_rag/
│
├── api/
│   ├── __init__.py
│   ├── main.py          # FastAPI application initialization & server config
│   ├── routes.py        # /ingest and /query API router endpoints
│   └── schemas.py       # Pydantic data validation and request/response models
│
├── rag/
│   ├── __init__.py
│   ├── ingestion.py     # Document loader, recursive character chunker & vector embedding pipeline
│   ├── retriever.py     # Vector store manager & semantic search retriever interface
│   └── chain.py         # Conversational RAG execution chain handling streaming & history
│
├── eval/
│   ├── __init__.py
│   └── evaluate.py      # RAGAS verification engine & metrics evaluation suite
│
├── data/                # Local data storage directory for raw source documents (PDF/TXT)
├── chroma_db/           # Persistent physical SQLite layer for local vector embeddings
├── .env                 # Protected environment infrastructure variables (API keys, paths)
├── .gitignore           # Explicit tracking exclusion list for local caches, DBs, and secrets
└── README.md            # Comprehensive project documentation