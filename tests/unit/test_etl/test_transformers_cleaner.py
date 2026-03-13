"""Unit tests for src.etl.transformers.cleaner — pure functions, no I/O."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

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

_BASE_TS = datetime(2023, 11, 14, 22, 0, 0, tzinfo=timezone.utc)


def _make_record(
    *,
    symbol: str = "BTCUSDT",
    timeframe: str = "1h",
    timestamp: datetime | None = None,
    price_open: str = "100.00",
    price_high: str = "110.00",
    price_low: str = "90.00",
    price_close: str = "105.00",
    volume: str = "1000.00",
    skip_validation: bool = False,
) -> OHLCVRecord:
    kwargs = {
        "symbol": symbol,
        "timeframe": timeframe,
        "timestamp": timestamp or _BASE_TS,
        "price_open": Decimal(price_open),
        "price_high": Decimal(price_high),
        "price_low": Decimal(price_low),
        "price_close": Decimal(price_close),
        "volume_24h": Decimal(volume),
        "market_cap": None,
        "source": "binance",
    }
    if skip_validation:
        return OHLCVRecord.model_construct(**kwargs)
    return OHLCVRecord(**kwargs)


# ---------------------------------------------------------------------------
# deduplicate_ohlcv
# ---------------------------------------------------------------------------


class TestDeduplicateOhlcv:
    def test_empty_list_returns_empty(self) -> None:
        assert deduplicate_ohlcv([]) == []

    def test_single_record_returned_unchanged(self) -> None:
        record = _make_record()
        result = deduplicate_ohlcv([record])
        assert result == [record]

    def test_no_duplicates_returns_all_records(self) -> None:
        r1 = _make_record(timestamp=_BASE_TS)
        r2 = _make_record(timestamp=_BASE_TS + timedelta(hours=1))
        result = deduplicate_ohlcv([r1, r2])
        assert len(result) == 2

    def test_exact_duplicate_kept_once(self) -> None:
        record = _make_record()
        result = deduplicate_ohlcv([record, record])
        assert len(result) == 1

    def test_first_occurrence_is_kept(self) -> None:
        r1 = _make_record(price_close="105.00")
        r2 = _make_record(price_close="999.00")  # same key, different price
        result = deduplicate_ohlcv([r1, r2])
        assert result[0].price_close == Decimal("105.00")

    def test_different_symbols_not_deduplicated(self) -> None:
        r1 = _make_record(symbol="BTCUSDT")
        r2 = _make_record(symbol="ETHUSDT")
        result = deduplicate_ohlcv([r1, r2])
        assert len(result) == 2

    def test_different_timeframes_not_deduplicated(self) -> None:
        r1 = _make_record(timeframe="1h")
        r2 = _make_record(timeframe="4h")
        result = deduplicate_ohlcv([r1, r2])
        assert len(result) == 2

    def test_different_timestamps_not_deduplicated(self) -> None:
        r1 = _make_record(timestamp=_BASE_TS)
        r2 = _make_record(timestamp=_BASE_TS + timedelta(hours=1))
        r3 = _make_record(timestamp=_BASE_TS + timedelta(hours=2))
        result = deduplicate_ohlcv([r1, r2, r3])
        assert len(result) == 3

    def test_multiple_duplicates_removed(self) -> None:
        record = _make_record()
        result = deduplicate_ohlcv([record, record, record])
        assert len(result) == 1

    def test_mixed_unique_and_duplicate(self) -> None:
        r1 = _make_record(timestamp=_BASE_TS)
        r2 = _make_record(timestamp=_BASE_TS)  # duplicate of r1
        r3 = _make_record(timestamp=_BASE_TS + timedelta(hours=1))
        result = deduplicate_ohlcv([r1, r2, r3])
        assert len(result) == 2


# ---------------------------------------------------------------------------
# validate_ohlcv_relationships
# ---------------------------------------------------------------------------


class TestValidateOhlcvRelationships:
    def test_valid_record_returns_empty_errors(self) -> None:
        record = _make_record()
        errors = validate_ohlcv_relationships(record)
        assert errors == []

    def test_high_less_than_open_is_violation(self) -> None:
        record = _make_record(
            price_open="110.00",
            price_high="100.00",  # high < open
            price_low="90.00",
            price_close="105.00",
            skip_validation=True,
        )
        errors = validate_ohlcv_relationships(record)
        assert any("high" in e and "open" in e for e in errors)

    def test_high_less_than_close_is_violation(self) -> None:
        record = _make_record(
            price_open="100.00",
            price_high="104.00",  # high < close
            price_low="90.00",
            price_close="105.00",
            skip_validation=True,
        )
        errors = validate_ohlcv_relationships(record)
        assert any("high" in e and "close" in e for e in errors)

    def test_low_greater_than_open_is_violation(self) -> None:
        record = _make_record(
            price_open="100.00",
            price_high="120.00",
            price_low="105.00",  # low > open
            price_close="110.00",
            skip_validation=True,
        )
        errors = validate_ohlcv_relationships(record)
        assert any("low" in e and "open" in e for e in errors)

    def test_low_greater_than_close_is_violation(self) -> None:
        record = _make_record(
            price_open="100.00",
            price_high="120.00",
            price_low="112.00",  # low > close
            price_close="110.00",
            skip_validation=True,
        )
        errors = validate_ohlcv_relationships(record)
        assert any("low" in e and "close" in e for e in errors)

    def test_high_less_than_low_is_violation(self) -> None:
        record = _make_record(
            price_open="100.00",
            price_high="95.00",  # high < low
            price_low="100.00",
            price_close="97.00",
            skip_validation=True,
        )
        errors = validate_ohlcv_relationships(record)
        assert any("high" in e and "low" in e for e in errors)

    def test_negative_volume_is_violation(self) -> None:
        record = _make_record(volume="-1.00", skip_validation=True)
        errors = validate_ohlcv_relationships(record)
        assert any("volume" in e for e in errors)

    def test_zero_volume_is_valid(self) -> None:
        record = _make_record(volume="0.00")
        errors = validate_ohlcv_relationships(record)
        assert errors == []

    def test_multiple_violations_all_reported(self) -> None:
        # high < open AND high < close AND high < low
        record = _make_record(
            price_open="110.00",
            price_high="80.00",
            price_low="95.00",
            price_close="108.00",
            skip_validation=True,
        )
        errors = validate_ohlcv_relationships(record)
        assert len(errors) >= 2

    def test_candle_with_equal_ohlc_is_valid(self) -> None:
        """Doji candle: all prices equal is valid."""
        record = _make_record(
            price_open="100.00",
            price_high="100.00",
            price_low="100.00",
            price_close="100.00",
        )
        errors = validate_ohlcv_relationships(record)
        assert errors == []


# ---------------------------------------------------------------------------
# filter_valid_records
# ---------------------------------------------------------------------------


class TestFilterValidRecords:
    def test_all_valid_returns_all_in_valid_partition(self) -> None:
        records = [_make_record(timestamp=_BASE_TS + timedelta(hours=i)) for i in range(3)]
        valid, invalid = filter_valid_records(records)
        assert len(valid) == 3
        assert len(invalid) == 0

    def test_all_invalid_returns_all_in_invalid_partition(self) -> None:
        bad = _make_record(
            price_open="110.00", price_high="90.00", price_low="80.00", price_close="95.00", skip_validation=True
        )
        records = [bad, bad, bad]
        valid, invalid = filter_valid_records(records)
        assert len(valid) == 0
        assert len(invalid) == 3

    def test_mixed_records_partitioned_correctly(self) -> None:
        good = _make_record(timestamp=_BASE_TS)
        bad = _make_record(
            timestamp=_BASE_TS + timedelta(hours=1),
            price_open="110.00",
            price_high="90.00",  # invalid: high < open
            price_low="80.00",
            price_close="95.00",
            skip_validation=True,
        )
        valid, invalid = filter_valid_records([good, bad])
        assert len(valid) == 1
        assert len(invalid) == 1
        assert valid[0].timestamp == _BASE_TS

    def test_empty_list_returns_two_empty_lists(self) -> None:
        valid, invalid = filter_valid_records([])
        assert valid == []
        assert invalid == []

    def test_returns_tuple_of_two_lists(self) -> None:
        result = filter_valid_records([_make_record()])
        assert isinstance(result, tuple)
        assert len(result) == 2


# ---------------------------------------------------------------------------
# detect_gaps
# ---------------------------------------------------------------------------


class TestDetectGaps:
    def test_empty_list_returns_empty(self) -> None:
        assert detect_gaps([], timedelta(hours=1)) == []

    def test_single_record_returns_empty(self) -> None:
        record = _make_record()
        assert detect_gaps([record], timedelta(hours=1)) == []

    def test_consecutive_records_no_gaps(self) -> None:
        records = [_make_record(timestamp=_BASE_TS + timedelta(hours=i)) for i in range(5)]
        gaps = detect_gaps(records, timedelta(hours=1))
        assert gaps == []

    def test_single_missing_candle_detected(self) -> None:
        r1 = _make_record(timestamp=_BASE_TS)
        r2 = _make_record(timestamp=_BASE_TS + timedelta(hours=2))  # skip one hour
        gaps = detect_gaps([r1, r2], timedelta(hours=1))
        assert len(gaps) == 1
        assert gaps[0][2] == 1  # 1 missing candle

    def test_multiple_missing_candles_counted(self) -> None:
        r1 = _make_record(timestamp=_BASE_TS)
        r2 = _make_record(timestamp=_BASE_TS + timedelta(hours=5))  # 4 missing
        gaps = detect_gaps([r1, r2], timedelta(hours=1))
        assert len(gaps) == 1
        assert gaps[0][2] == 4

    def test_gap_tuple_contains_correct_bordering_records(self) -> None:
        r1 = _make_record(timestamp=_BASE_TS)
        r2 = _make_record(timestamp=_BASE_TS + timedelta(hours=3))
        gaps = detect_gaps([r1, r2], timedelta(hours=1))
        before_gap, after_gap, missing = gaps[0]
        assert before_gap.timestamp == _BASE_TS
        assert after_gap.timestamp == _BASE_TS + timedelta(hours=3)
        assert missing == 2

    def test_multiple_separate_gaps_all_detected(self) -> None:
        records = [
            _make_record(timestamp=_BASE_TS),
            _make_record(timestamp=_BASE_TS + timedelta(hours=2)),  # gap here
            _make_record(timestamp=_BASE_TS + timedelta(hours=3)),
            _make_record(timestamp=_BASE_TS + timedelta(hours=5)),  # gap here
        ]
        gaps = detect_gaps(records, timedelta(hours=1))
        assert len(gaps) == 2

    def test_daily_interval_gap_detection(self) -> None:
        r1 = _make_record(timestamp=_BASE_TS)
        r2 = _make_record(timestamp=_BASE_TS + timedelta(days=3))  # 2 missing days
        gaps = detect_gaps([r1, r2], timedelta(days=1))
        assert len(gaps) == 1
        assert gaps[0][2] == 2


# ---------------------------------------------------------------------------
# parse_timeframe_to_timedelta
# ---------------------------------------------------------------------------


class TestParseTimeframeToTimedelta:
    @pytest.mark.parametrize(
        ("timeframe", "expected"),
        [
            ("1m", timedelta(minutes=1)),
            ("5m", timedelta(minutes=5)),
            ("1h", timedelta(hours=1)),
            ("2h", timedelta(hours=2)),
            ("3h", timedelta(hours=3)),
            ("4h", timedelta(hours=4)),
            ("1D", timedelta(days=1)),
            ("1W", timedelta(weeks=1)),
            ("1M", timedelta(days=30)),
        ],
    )
    def test_known_timeframe_returns_correct_delta(self, timeframe: str, expected: timedelta) -> None:
        assert parse_timeframe_to_timedelta(timeframe) == expected

    def test_unknown_timeframe_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="Unknown timeframe"):
            parse_timeframe_to_timedelta("6h")

    def test_error_message_lists_valid_timeframes(self) -> None:
        with pytest.raises(ValueError, match="1h"):
            parse_timeframe_to_timedelta("bad")

    def test_empty_string_raises_value_error(self) -> None:
        with pytest.raises(ValueError):
            parse_timeframe_to_timedelta("")

    def test_case_sensitive_1d_not_valid(self) -> None:
        """'1d' (lowercase) is NOT in the map — only '1D' is."""
        with pytest.raises(ValueError):
            parse_timeframe_to_timedelta("1d")
