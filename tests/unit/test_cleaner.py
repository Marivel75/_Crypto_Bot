"""Unit tests for ETL cleaner — deduplication, validation, gap detection."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from src.etl.transformers.cleaner import (
    deduplicate_ohlcv,
    detect_gaps,
    filter_valid_records,
    parse_timeframe_to_timedelta,
    validate_ohlcv_relationships,
)
from src.shared.models.crypto import OHLCVRecord

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BASE_TS = datetime(2024, 3, 1, 0, 0, 0, tzinfo=timezone.utc)


def _make_record(
    symbol: str = "BTCUSDT",
    timeframe: str = "1h",
    timestamp: datetime | None = None,
    price_open: float = 50_000.0,
    price_high: float = 51_000.0,
    price_low: float = 49_000.0,
    price_close: float = 50_500.0,
    volume_24h: float = 1000.0,
) -> OHLCVRecord:
    return OHLCVRecord(
        symbol=symbol,
        timeframe=timeframe,
        timestamp=timestamp or _BASE_TS,
        price_open=Decimal(str(price_open)),
        price_high=Decimal(str(price_high)),
        price_low=Decimal(str(price_low)),
        price_close=Decimal(str(price_close)),
        volume_24h=Decimal(str(volume_24h)),
        source="binance",
    )


# ---------------------------------------------------------------------------
# deduplicate_ohlcv
# ---------------------------------------------------------------------------


class TestDeduplicateOHLCV:
    def test_no_duplicates_returns_same_count(self) -> None:
        records = [_make_record(timestamp=_BASE_TS + timedelta(hours=i)) for i in range(5)]
        result = deduplicate_ohlcv(records)
        assert len(result) == 5

    def test_exact_duplicate_removed(self) -> None:
        record = _make_record(timestamp=_BASE_TS)
        records = [record, record]
        result = deduplicate_ohlcv(records)
        assert len(result) == 1

    def test_keeps_first_occurrence(self) -> None:
        r1 = _make_record(timestamp=_BASE_TS, price_close=50_000.0)
        r2 = _make_record(timestamp=_BASE_TS, price_close=99_000.0)
        result = deduplicate_ohlcv([r1, r2])
        assert len(result) == 1
        assert result[0].price_close == Decimal("50000.0")

    def test_different_symbols_not_deduplicated(self) -> None:
        r1 = _make_record(symbol="BTCUSDT", timestamp=_BASE_TS)
        r2 = _make_record(symbol="ETHUSDT", timestamp=_BASE_TS)
        result = deduplicate_ohlcv([r1, r2])
        assert len(result) == 2

    def test_different_timeframes_not_deduplicated(self) -> None:
        r1 = _make_record(timeframe="1h", timestamp=_BASE_TS)
        r2 = _make_record(timeframe="4h", timestamp=_BASE_TS)
        result = deduplicate_ohlcv([r1, r2])
        assert len(result) == 2

    def test_empty_list_returns_empty(self) -> None:
        assert deduplicate_ohlcv([]) == []

    def test_multiple_duplicates_collapsed_to_one(self) -> None:
        record = _make_record(timestamp=_BASE_TS)
        records = [record] * 10
        result = deduplicate_ohlcv(records)
        assert len(result) == 1


# ---------------------------------------------------------------------------
# validate_ohlcv_relationships
# ---------------------------------------------------------------------------


class TestValidateOHLCVRelationships:
    def test_valid_record_returns_no_errors(self) -> None:
        record = _make_record()
        errors = validate_ohlcv_relationships(record)
        assert errors == []

    def test_high_below_open_is_invalid(self) -> None:
        record = _make_record(
            price_open=52_000.0,
            price_high=51_000.0,  # high < open
            price_low=49_000.0,
            price_close=50_500.0,
        )
        errors = validate_ohlcv_relationships(record)
        assert any("high" in e and "open" in e for e in errors)

    def test_high_below_close_is_invalid(self) -> None:
        record = _make_record(
            price_open=50_000.0,
            price_high=50_200.0,
            price_low=49_000.0,
            price_close=50_500.0,  # close > high
        )
        errors = validate_ohlcv_relationships(record)
        assert any("high" in e and "close" in e for e in errors)

    def test_low_above_open_is_invalid(self) -> None:
        record = _make_record(
            price_open=50_000.0,
            price_high=51_000.0,
            price_low=50_500.0,  # low > open
            price_close=50_800.0,
        )
        errors = validate_ohlcv_relationships(record)
        assert any("low" in e and "open" in e for e in errors)

    def test_low_above_close_is_invalid(self) -> None:
        record = _make_record(
            price_open=50_000.0,
            price_high=51_000.0,
            price_low=50_600.0,  # low > close
            price_close=50_500.0,
        )
        errors = validate_ohlcv_relationships(record)
        assert any("low" in e and "close" in e for e in errors)

    def test_high_below_low_is_invalid(self) -> None:
        # Model validator now rejects price_high < price_low at construction time
        with pytest.raises(ValidationError, match="price_high"):
            _make_record(
                price_open=50_000.0,
                price_high=49_000.0,  # high < low
                price_low=50_000.0,
                price_close=50_000.0,
            )

    def test_negative_volume_is_invalid(self) -> None:
        # Model validator now rejects negative volume at construction time
        with pytest.raises(ValidationError, match="volume_24h"):
            _make_record(volume_24h=-1.0)

    def test_zero_volume_is_valid(self) -> None:
        record = _make_record(volume_24h=0.0)
        errors = validate_ohlcv_relationships(record)
        assert errors == []


# ---------------------------------------------------------------------------
# filter_valid_records
# ---------------------------------------------------------------------------


class TestFilterValidRecords:
    def test_all_valid_partitions_correctly(self) -> None:
        records = [_make_record(timestamp=_BASE_TS + timedelta(hours=i)) for i in range(3)]
        valid, invalid = filter_valid_records(records)
        assert len(valid) == 3
        assert len(invalid) == 0

    def test_invalid_record_partitioned_to_invalid(self) -> None:
        valid_record = _make_record(timestamp=_BASE_TS)
        # Use model_construct to bypass model_validator (which now rejects high < low)
        invalid_record = OHLCVRecord.model_construct(
            symbol="BTCUSDT",
            timeframe="1h",
            timestamp=_BASE_TS + timedelta(hours=1),
            price_open=50_000.0,
            price_high=48_000.0,  # high < low → invalid
            price_low=49_000.0,
            price_close=50_000.0,
            volume_24h=1000.0,
            source="binance",
        )
        valid, invalid = filter_valid_records([valid_record, invalid_record])
        assert len(valid) == 1
        assert len(invalid) == 1

    def test_empty_list_returns_empty_partitions(self) -> None:
        valid, invalid = filter_valid_records([])
        assert valid == []
        assert invalid == []


# ---------------------------------------------------------------------------
# detect_gaps
# ---------------------------------------------------------------------------


class TestDetectGaps:
    def test_no_gaps_returns_empty(self) -> None:
        records = [_make_record(timestamp=_BASE_TS + timedelta(hours=i)) for i in range(5)]
        gaps = detect_gaps(records, timedelta(hours=1))
        assert gaps == []

    def test_detects_single_gap(self) -> None:
        records = [
            _make_record(timestamp=_BASE_TS),
            _make_record(timestamp=_BASE_TS + timedelta(hours=3)),  # 2 candles missing
        ]
        gaps = detect_gaps(records, timedelta(hours=1))
        assert len(gaps) == 1
        _, _, missing = gaps[0]
        assert missing == 2

    def test_detects_multiple_gaps(self) -> None:
        records = [
            _make_record(timestamp=_BASE_TS),
            _make_record(timestamp=_BASE_TS + timedelta(hours=5)),
            _make_record(timestamp=_BASE_TS + timedelta(hours=10)),
        ]
        gaps = detect_gaps(records, timedelta(hours=1))
        assert len(gaps) == 2

    def test_less_than_two_records_returns_empty(self) -> None:
        records = [_make_record(timestamp=_BASE_TS)]
        gaps = detect_gaps(records, timedelta(hours=1))
        assert gaps == []

    def test_empty_list_returns_empty(self) -> None:
        gaps = detect_gaps([], timedelta(hours=1))
        assert gaps == []


# ---------------------------------------------------------------------------
# parse_timeframe_to_timedelta
# ---------------------------------------------------------------------------


class TestParseTimeframeToTimedelta:
    def test_1h_parses(self) -> None:
        assert parse_timeframe_to_timedelta("1h") == timedelta(hours=1)

    def test_4h_parses(self) -> None:
        assert parse_timeframe_to_timedelta("4h") == timedelta(hours=4)

    def test_1d_parses(self) -> None:
        assert parse_timeframe_to_timedelta("1D") == timedelta(days=1)

    def test_1w_parses(self) -> None:
        assert parse_timeframe_to_timedelta("1W") == timedelta(weeks=1)

    def test_unknown_timeframe_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="Unknown timeframe"):
            parse_timeframe_to_timedelta("99x")

    def test_1m_parses(self) -> None:
        assert parse_timeframe_to_timedelta("1m") == timedelta(minutes=1)
