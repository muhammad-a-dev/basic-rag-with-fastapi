# Lightweight image for the Basic RAG FastAPI service.
# Requires HUGGINGFACE_API_KEY and GROQ_API_KEY at runtime for real queries.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    LOG_LEVEL=INFO \
    CHROMA_PERSIST_DIRECTORY=/app/data/chroma_db \
    TEMP_UPLOAD_DIR=/app/data/temp

WORKDIR /app

# Install package first for better layer caching.
COPY pyproject.toml README.md LICENSE ./
COPY api ./api
COPY rag ./rag
COPY eval ./eval
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/data/chroma_db /app/data/temp \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
