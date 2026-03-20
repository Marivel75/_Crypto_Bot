# Data Engineering Rules

## Scope: `src/etl/`

## Pipeline Rules
- All collectors must handle rate limits gracefully (exponential backoff)
- Validate incoming data with Pydantic before inserting
- Deduplicate OHLCV data by (symbol, timeframe, timestamp) unique constraint
- Log every ETL run: start time, records fetched, records inserted, errors
- APScheduler jobs must be idempotent (safe to re-run)

## TimescaleDB
- OHLCV table is a hypertable partitioned by time
- Use `add_compression_policy` for data older than 7 days
- Use `add_retention_policy` for data older than 2 years
- Always use parameterized queries
- Batch inserts with `executemany` or `COPY`

## MinIO
- Bucket naming: `datasets`, `models`, `mlflow-artifacts`
- Object keys: `{type}/{symbol}/{date}/{filename}`
- Set lifecycle rules for temporary data

## Data Quality
- Check for gaps in OHLCV data after each collection
- Alert if data staleness > 2x expected interval
- Validate OHLCV: open/high/low/close relationships, volume >= 0
- Track API response times and error rates

## DO NOT
- Access MinIO or TimescaleDB from frontend code
- Modify `src/api/`, `src/ml/`, `src/frontend/`
- Use paid APIs
