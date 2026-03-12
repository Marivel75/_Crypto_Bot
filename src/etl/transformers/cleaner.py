"""Data cleaning and validation utilities for ETL pipeline."""

from __future__ import annotations

import logging
from datetime import timedelta

from src.shared.models.crypto import OHLCVRecord

logger = logging.getLogger(__name__)


def deduplicate_ohlcv(records: list[OHLCVRecord]) -> list[OHLCVRecord]:
    """Remove duplicate OHLCV records by (symbol, timeframe, timestamp).

    Keeps the first occurrence of each unique key.
    """
    seen: set[tuple[str, str, str]] = set()
    unique: list[OHLCVRecord] = []
    for record in records:
        key = (record.symbol, record.timeframe, str(record.timestamp))
        if key not in seen:
            seen.add(key)
            unique.append(record)

    removed = len(records) - len(unique)
    if removed > 0:
        logger.info("Deduplicated OHLCV: removed %d duplicates from %d records", removed, len(records))
    return unique


def validate_ohlcv_relationships(record: OHLCVRecord) -> list[str]:
    """Validate OHLCV price invariants.

    Returns list of violation descriptions (empty if valid).
    Checks:
    - high >= max(open, close)
    - low <= min(open, close)
    - high >= low
    - volume >= 0
    """
    errors: list[str] = []

    if record.price_high < record.price_open:
        errors.append(f"high ({record.price_high}) < open ({record.price_open})")
    if record.price_high < record.price_close:
        errors.append(f"high ({record.price_high}) < close ({record.price_close})")
    if record.price_low > record.price_open:
        errors.append(f"low ({record.price_low}) > open ({record.price_open})")
    if record.price_low > record.price_close:
        errors.append(f"low ({record.price_low}) > close ({record.price_close})")
    if record.price_high < record.price_low:
        errors.append(f"high ({record.price_high}) < low ({record.price_low})")
    if record.volume_24h < 0:
        errors.append(f"volume ({record.volume_24h}) < 0")

    return errors


def filter_valid_records(
    records: list[OHLCVRecord],
) -> tuple[list[OHLCVRecord], list[OHLCVRecord]]:
    """Partition OHLCV records into valid and invalid based on price invariants.

    Returns:
        Tuple of (valid_records, invalid_records).
    """
    valid: list[OHLCVRecord] = []
    invalid: list[OHLCVRecord] = []

    for record in records:
        errors = validate_ohlcv_relationships(record)
        if errors:
            logger.warning(
                "Invalid OHLCV record %s/%s at %s: %s",
                record.symbol,
                record.timeframe,
                record.timestamp,
                "; ".join(errors),
            )
            invalid.append(record)
        else:
            valid.append(record)

    if invalid:
        logger.info(
            "OHLCV validation: %d valid, %d invalid out of %d total",
            len(valid),
            len(invalid),
            len(records),
        )
    return valid, invalid


def detect_gaps(
    records: list[OHLCVRecord],
    expected_interval: timedelta,
) -> list[tuple[OHLCVRecord, OHLCVRecord, int]]:
    """Detect gaps in a sorted OHLCV time series.

    Args:
        records: OHLCV records sorted by timestamp (ascending).
        expected_interval: Expected time between consecutive records.

    Returns:
        List of (record_before_gap, record_after_gap, missing_count) tuples.
    """
    if len(records) < 2:
        return []

    gaps: list[tuple[OHLCVRecord, OHLCVRecord, int]] = []
    for i in range(1, len(records)):
        actual_diff = records[i].timestamp - records[i - 1].timestamp
        expected_count = int(actual_diff / expected_interval)
        if expected_count > 1:
            missing = expected_count - 1
            gaps.append((records[i - 1], records[i], missing))

    if gaps:
        total_missing = sum(g[2] for g in gaps)
        logger.warning(
            "Detected %d gaps (%d missing candles) in %s/%s",
            len(gaps),
            total_missing,
            records[0].symbol,
            records[0].timeframe,
        )
    return gaps


_TIMEFRAME_INTERVALS: dict[str, timedelta] = {
    "1m": timedelta(minutes=1),
    "5m": timedelta(minutes=5),
    "1h": timedelta(hours=1),
    "2h": timedelta(hours=2),
    "3h": timedelta(hours=3),
    "4h": timedelta(hours=4),
    "1D": timedelta(days=1),
    "1W": timedelta(weeks=1),
    "1M": timedelta(days=30),
}


def parse_timeframe_to_timedelta(timeframe: str) -> timedelta:
    """Convert a timeframe string to a timedelta.

    Raises:
        ValueError: If timeframe is not recognized.
    """
    interval = _TIMEFRAME_INTERVALS.get(timeframe)
    if interval is None:
        raise ValueError(f"Unknown timeframe '{timeframe}'. Valid: {list(_TIMEFRAME_INTERVALS)}")
    return interval
