"""MinIO loader — upload OHLCV Parquet, datasets, and raw JSON to S3-compatible storage."""

from __future__ import annotations

import asyncio
import io
import json
import logging
from typing import TYPE_CHECKING

from minio import Minio

if TYPE_CHECKING:
    import pandas as pd

from src.shared.config import settings

logger = logging.getLogger(__name__)

# Public bucket name constants — imported by other ETL modules.
BUCKET_RAW: str = "raw"
BUCKET_DATASETS: str = "datasets"
BUCKET_MODELS: str = "models"
BUCKET_MLFLOW: str = "mlflow-artifacts"

_BUCKETS = (BUCKET_RAW, BUCKET_DATASETS, BUCKET_MODELS, BUCKET_MLFLOW)

_client: Minio | None = None


def get_minio_client() -> Minio:
    """Return a shared MinIO client singleton."""
    global _client  # noqa: PLW0603
    if _client is None:
        endpoint = settings.minio_endpoint.replace("http://", "").replace("https://", "")
        _client = Minio(
            endpoint,
            access_key=settings.minio_root_user,
            secret_key=settings.minio_root_password,
            secure=settings.minio_endpoint.startswith("https"),
        )
    return _client


async def ensure_buckets_exist() -> None:
    """Create required MinIO buckets if they do not exist."""
    client = get_minio_client()
    for bucket in _BUCKETS:
        exists = await asyncio.to_thread(client.bucket_exists, bucket)
        if not exists:
            await asyncio.to_thread(client.make_bucket, bucket)
            logger.info("Created MinIO bucket: %s", bucket)
        else:
            logger.debug("MinIO bucket already exists: %s", bucket)


async def upload_ohlcv_parquet(
    records: list[dict[str, object]],
    symbol: str,
    date: str,
) -> str:
    """Serialize OHLCV records to Parquet and upload to MinIO raw bucket.

    Args:
        records: List of OHLCV dicts with keys matching the OHLCVRecord fields.
        symbol: Trading pair symbol (e.g. "BTCUSDT").
        date: ISO date string (e.g. "2024-11-01").

    Returns:
        The object key in MinIO.
    """
    import pandas as pd

    df = pd.DataFrame(records)
    buffer = io.BytesIO()
    df.to_parquet(buffer, engine="pyarrow", index=False)
    buffer.seek(0)

    object_key = f"binance/{symbol}/{date}/ohlcv.parquet"
    client = get_minio_client()
    await asyncio.to_thread(
        client.put_object,
        "raw",
        object_key,
        buffer,
        length=buffer.getbuffer().nbytes,
        content_type="application/octet-stream",
    )
    logger.info("Uploaded OHLCV Parquet: raw/%s", object_key)
    return object_key


async def upload_dataset_parquet(
    data: bytes,
    filename: str,
) -> str:
    """Upload a prepared dataset Parquet file to the datasets bucket.

    Args:
        data: Raw Parquet bytes.
        filename: Target filename (e.g. "features_20241101.parquet").

    Returns:
        The object key in MinIO.
    """
    buffer = io.BytesIO(data)
    client = get_minio_client()
    await asyncio.to_thread(
        client.put_object,
        "datasets",
        filename,
        buffer,
        length=len(data),
        content_type="application/octet-stream",
    )
    logger.info("Uploaded dataset: datasets/%s", filename)
    return filename


async def upload_raw_json(
    data: object,
    bucket: str,
    object_key: str,
) -> str:
    """Upload a JSON-serializable object to the specified bucket.

    Args:
        data: JSON-serializable Python object.
        bucket: Target bucket name.
        object_key: Object key/path within the bucket.

    Returns:
        The object key in MinIO.
    """
    payload = json.dumps(data, default=str).encode("utf-8")
    buffer = io.BytesIO(payload)
    client = get_minio_client()
    await asyncio.to_thread(
        client.put_object,
        bucket,
        object_key,
        buffer,
        length=len(payload),
        content_type="application/json",
    )
    logger.info("Uploaded JSON: %s/%s", bucket, object_key)
    return object_key


async def upload_dataframe(
    bucket: str,
    key: str,
    df: pd.DataFrame,  # noqa: F821
) -> None:
    """Serialise a DataFrame to Parquet and upload to MinIO.

    Args:
        bucket: Target bucket name (created automatically if absent).
        key: Object key, e.g. ``"BTCUSDT/2024-01-01/features.parquet"``.
        df: DataFrame to serialise.
    """

    buffer = io.BytesIO()
    df.to_parquet(buffer, engine="pyarrow", index=False)
    data = buffer.getvalue()
    size = len(data)

    client = get_minio_client()
    # Ensure bucket exists
    exists = await asyncio.to_thread(client.bucket_exists, bucket)
    if not exists:
        await asyncio.to_thread(client.make_bucket, bucket)
        logger.info("Created MinIO bucket: %s", bucket)

    await asyncio.to_thread(
        client.put_object,
        bucket,
        key,
        io.BytesIO(data),
        size,
        content_type="application/octet-stream",
    )
    logger.info(
        "Uploaded DataFrame: bucket=%s key=%s rows=%d size_bytes=%d",
        bucket,
        key,
        len(df),
        size,
    )


async def download_dataframe(
    bucket: str,
    key: str,
) -> pd.DataFrame:  # noqa: F821
    """Download a Parquet object from MinIO and deserialise to a DataFrame.

    Args:
        bucket: Source bucket name.
        key: Object key to download.

    Returns:
        Deserialised ``pandas.DataFrame``.
    """
    import pandas as pd  # local import to avoid top-level dep if pandas absent
    from minio.error import S3Error

    client = get_minio_client()

    def _fetch() -> bytes:
        try:
            response = client.get_object(bucket, key)
            raw = response.read()
            response.close()
            response.release_conn()
            return raw
        except S3Error as exc:
            raise exc

    raw_bytes: bytes = await asyncio.to_thread(_fetch)
    df: pd.DataFrame = pd.read_parquet(io.BytesIO(raw_bytes))
    logger.info(
        "Downloaded DataFrame: bucket=%s key=%s rows=%d",
        bucket,
        key,
        len(df),
    )
    return df
