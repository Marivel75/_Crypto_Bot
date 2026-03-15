# --- Builder stage ---
FROM python:3.11-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
COPY pyproject.toml /tmp/
RUN uv pip install --system --no-cache --prefix=/install \
    -r /tmp/pyproject.toml --extra ml

# --- Runtime stage ---
FROM python:3.11-slim

RUN useradd --uid 1001 --create-home appuser

WORKDIR /app

COPY --from=builder /install /usr/local

COPY --chown=appuser:appuser src/shared/ /app/src/shared/
COPY --chown=appuser:appuser src/ml/ /app/src/ml/

ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER appuser

HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import src.ml.signal_generator" || exit 1

CMD ["python", "-m", "src.ml"]
