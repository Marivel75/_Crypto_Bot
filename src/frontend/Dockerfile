# --- Builder stage ---
FROM python:3.11-slim AS builder

COPY src/shared/requirements.txt /tmp/shared-requirements.txt
RUN pip install --no-cache-dir --prefix=/install -r /tmp/shared-requirements.txt

COPY src/frontend/requirements.txt /tmp/frontend-requirements.txt
RUN pip install --no-cache-dir --prefix=/install -r /tmp/frontend-requirements.txt

# --- Runtime stage ---
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --uid 1001 --create-home appuser

WORKDIR /app

COPY --from=builder /install /usr/local

COPY --chown=appuser:appuser src/shared/ /app/src/shared/
COPY --chown=appuser:appuser src/frontend/ /app/src/frontend/

ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

USER appuser

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

CMD ["streamlit", "run", "src/frontend/app.py", \
     "--server.maxUploadSize=5", \
     "--server.enableXsrfProtection=true"]
