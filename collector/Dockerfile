FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .
COPY logger_settings.py .
COPY src/ src/
COPY config/ config/
COPY scripts/ scripts/

CMD ["python", "main.py", "--schedule"]
