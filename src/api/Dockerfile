# --- Builder stage ---
FROM python:3.11.8-slim AS builder

COPY src/shared/requirements.txt /tmp/shared-requirements.txt
RUN pip install --no-cache-dir --prefix=/install -r /tmp/shared-requirements.txt

COPY src/api/requirements.txt /tmp/api-requirements.txt
RUN pip install --no-cache-dir --prefix=/install -r /tmp/api-requirements.txt

# --- Runtime stage ---
FROM python:3.11.8-slim

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --uid 1001 --create-home appuser

WORKDIR /app

COPY --from=builder /install /usr/local

COPY --chown=appuser:appuser src/shared/ /app/src/shared/
COPY --chown=appuser:appuser src/api/ /app/src/api/
COPY --chown=appuser:appuser src/etl/migrations/ /app/src/etl/migrations/
COPY --chown=appuser:appuser alembic.ini /app/alembic.ini

ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
