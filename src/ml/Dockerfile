# --- Builder stage ---
FROM python:3.11.8-slim AS builder

COPY src/shared/requirements.txt /tmp/shared-requirements.txt
RUN pip install --no-cache-dir --prefix=/install -r /tmp/shared-requirements.txt

COPY src/ml/requirements.txt /tmp/ml-requirements.txt
RUN pip install --no-cache-dir --prefix=/install -r /tmp/ml-requirements.txt

# --- Runtime stage ---
FROM python:3.11.8-slim

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
