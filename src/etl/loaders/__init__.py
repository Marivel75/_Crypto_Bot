"""ETL loaders — TimescaleDB and MinIO persistence."""

from __future__ import annotations

from src.etl.loaders.minio_loader import (
    BUCKET_DATASETS,
    BUCKET_MLFLOW,
    BUCKET_MODELS,
    BUCKET_RAW,
    ensure_buckets_exist,
    get_minio_client,
    upload_dataset_parquet,
    upload_ohlcv_parquet,
    upload_raw_json,
)
from src.etl.loaders.timescaledb import (
    detect_gaps,
    fetch_ohlcv_for_indicators,
    get_engine,
    insert_indicators_batch,
    insert_news_batch,
    insert_ohlcv_batch,
)

__all__ = [
    "BUCKET_DATASETS",
    "BUCKET_MLFLOW",
    "BUCKET_MODELS",
    "BUCKET_RAW",
    "detect_gaps",
    "ensure_buckets_exist",
    "fetch_ohlcv_for_indicators",
    "get_engine",
    "get_minio_client",
    "insert_indicators_batch",
    "insert_news_batch",
    "insert_ohlcv_batch",
    "upload_dataset_parquet",
    "upload_ohlcv_parquet",
    "upload_raw_json",
]
