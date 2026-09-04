# Contributing

Thanks for your interest in improving this project.

## Setup

1. Fork and clone the repository.
2. Create a virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

3. Copy `.env.example` to `.env` and add your API keys for local runs that call real providers.

## Development workflow

- Create a focused branch from `main`.
- Prefer small, reviewable changes.
- Run lint and tests before opening a PR:

```bash
ruff check .
pytest
```

## Pull requests

- Describe the problem and the approach.
- Note any follow-up work you intentionally left out.
- Do not commit secrets, `.env`, local vector DB data, or uploaded temp files.
