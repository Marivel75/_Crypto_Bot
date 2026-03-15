# --- Builder stage ---
FROM python:3.11-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
COPY pyproject.toml /tmp/
RUN uv pip install --system --no-cache --prefix=/install \
    -r /tmp/pyproject.toml --extra etl

# --- Runtime stage ---
FROM python:3.11-slim

RUN useradd --uid 1001 --create-home appuser

WORKDIR /app

COPY --from=builder /install /usr/local

COPY --chown=appuser:appuser src/shared/ /app/src/shared/
COPY --chown=appuser:appuser src/etl/ /app/src/etl/

ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER appuser

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1

EXPOSE 8080

CMD ["python", "-m", "src.etl.main"]
