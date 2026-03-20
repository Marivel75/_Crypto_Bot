# Data Engineering Team Context

You are working as the Data Engineering agent for crypto-bot.

## Your Scope

- **Code**: `src/etl/`, `src/shared/`
- **Doc**: `docs/01-data-engineering.md`
- **Commit scope**: `etl`, `shared`
- **Do NOT touch**: `src/api/`, `src/ml/`, `src/frontend/`

## Architecture

```
src/etl/
  collectors/          # binance.py, coingecko.py, ccxt.py, news_rss.py
  loaders/             # timescaledb_loader.py, minio_loader.py
  transformers/        # ohlcv_transformer.py, news_transformer.py
  scheduler.py         # APScheduler job definitions
  main.py              # ETL worker entry point

src/shared/
  config.py            # pydantic-settings Settings singleton
  models/              # CryptoRecord, OHLCVRecord, Signal, User, NewsItem
  exceptions.py        # Custom exception hierarchy
  constants.py         # SYMBOLS, TIMEFRAMES, EXCHANGE_LIMITS
```

## Pipeline Rules

- ALL collectors handle rate limits with exponential backoff
- Validate incoming data with Pydantic BEFORE inserting into DB
- Deduplicate OHLCV by `(symbol, timeframe, timestamp)` unique constraint
- Log every run: start_time, records_fetched, records_inserted, errors
- APScheduler jobs MUST be idempotent (safe to re-run after failure)

## TimescaleDB

- OHLCV is a hypertable partitioned by `timestamp`
- Compression policy: data older than 7 days
- Retention policy: data older than 2 years
- Batch inserts with `executemany` or `INSERT ... ON CONFLICT DO NOTHING`
- Always use parameterized queries

## MinIO Buckets

| Bucket | Content | Key pattern |
|--------|---------|-------------|
| `datasets` | Raw + processed data | `{type}/{symbol}/{date}/{file}` |
| `models` | Serialized ML models | `{model_name}/{version}/{file}` |
| `mlflow-artifacts` | MLflow run artifacts | managed by MLflow |

## Data Quality

- Check for OHLCV gaps after each collection run
- Alert if data staleness > 2x expected interval
- Validate OHLCV invariants: `low <= open,close <= high`, `volume >= 0`
- Track API response times and error rates in logs

## Workflow

1. Read `docs/01-data-engineering.md` for full pipeline spec
2. Read `src/shared/models/` to understand domain models
3. Read `src/shared/config.py` for all connection settings
4. Implement collector as a `BaseCollector` subclass
5. Write unit tests with `respx` mocking the external API
6. Run: `ruff check src/etl/ src/shared/ && mypy src/etl/ src/shared/ && pytest tests/unit/test_etl/ -v`
