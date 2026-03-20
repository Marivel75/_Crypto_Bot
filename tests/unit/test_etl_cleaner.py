"""Unit tests for ETL cleaner functions."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

UTC = timezone.utc
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

BASE_TS = datetime(2024, 1, 15, 0, 0, 0, tzinfo=UTC)


def _make_record(
    symbol: str = "BTCUSDT",
    timeframe: str = "1h",
    timestamp: datetime | None = None,
    price_open: str = "42000",
    price_high: str = "43000",
    price_low: str = "41000",
    price_close: str = "42500",
    volume_24h: str = "1000",
    source: str = "binance",
    *,
    skip_validation: bool = False,
) -> OHLCVRecord:
    kwargs = {
        "symbol": symbol,
        "timeframe": timeframe,
        "timestamp": timestamp or BASE_TS,
        "price_open": Decimal(price_open),
        "price_high": Decimal(price_high),
        "price_low": Decimal(price_low),
        "price_close": Decimal(price_close),
        "volume_24h": Decimal(volume_24h),
        "source": source,
    }
    if skip_validation:
        return OHLCVRecord.model_construct(**kwargs)
    return OHLCVRecord(**kwargs)


# ---------------------------------------------------------------------------
# deduplicate_ohlcv
# ---------------------------------------------------------------------------


class TestDeduplicateOHLCV:
    def test_empty_list_returns_empty(self) -> None:
        assert deduplicate_ohlcv([]) == []

    def test_no_duplicates_unchanged(self) -> None:
        records = [
            _make_record(timestamp=BASE_TS),
            _make_record(timestamp=BASE_TS + timedelta(hours=1)),
            _make_record(timestamp=BASE_TS + timedelta(hours=2)),
        ]
        result = deduplicate_ohlcv(records)
        assert len(result) == 3

    def test_exact_duplicates_removed(self) -> None:
        r = _make_record(timestamp=BASE_TS)
        records = [r, r, r]
        result = deduplicate_ohlcv(records)
        assert len(result) == 1

    def test_keeps_first_occurrence(self) -> None:
        r1 = _make_record(timestamp=BASE_TS, price_close="42500")
        r2 = _make_record(timestamp=BASE_TS, price_close="99999")  # same key, different price
        result = deduplicate_ohlcv([r1, r2])
        assert len(result) == 1
        assert result[0].price_close == Decimal("42500")

    def test_different_symbols_not_deduplicated(self) -> None:
        r1 = _make_record(symbol="BTCUSDT", timestamp=BASE_TS)
        r2 = _make_record(symbol="ETHUSDT", timestamp=BASE_TS)
        result = deduplicate_ohlcv([r1, r2])
        assert len(result) == 2

    def test_different_timeframes_not_deduplicated(self) -> None:
        r1 = _make_record(timeframe="1h", timestamp=BASE_TS)
        r2 = _make_record(timeframe="4h", timestamp=BASE_TS)
        result = deduplicate_ohlcv([r1, r2])
        assert len(result) == 2

    def test_different_timestamps_not_deduplicated(self) -> None:
        r1 = _make_record(timestamp=BASE_TS)
        r2 = _make_record(timestamp=BASE_TS + timedelta(hours=1))
        result = deduplicate_ohlcv([r1, r2])
        assert len(result) == 2

    def test_mixed_deduplication(self) -> None:
        t0 = BASE_TS
        t1 = BASE_TS + timedelta(hours=1)
        records = [
            _make_record(timestamp=t0),
            _make_record(timestamp=t0),  # duplicate
            _make_record(timestamp=t1),
        ]
        result = deduplicate_ohlcv(records)
        assert len(result) == 2

    def test_preserves_order(self) -> None:
        timestamps = [BASE_TS + timedelta(hours=i) for i in range(5)]
        records = [_make_record(timestamp=ts) for ts in timestamps]
        result = deduplicate_ohlcv(records)
        result_ts = [r.timestamp for r in result]
        assert result_ts == timestamps

    def test_single_record_unchanged(self) -> None:
        r = _make_record()
        result = deduplicate_ohlcv([r])
        assert len(result) == 1
        assert result[0] is r


# ---------------------------------------------------------------------------
# validate_ohlcv_relationships
# ---------------------------------------------------------------------------


class TestValidateOHLCVRelationships:
    def test_valid_record_returns_no_errors(self) -> None:
        r = _make_record(price_open="42000", price_high="43000", price_low="41000", price_close="42500")
        errors = validate_ohlcv_relationships(r)
        assert errors == []

    def test_high_less_than_open_is_error(self) -> None:
        r = _make_record(price_open="44000", price_high="43000", price_low="41000", price_close="42500")
        errors = validate_ohlcv_relationships(r)
        assert any("high" in e and "open" in e for e in errors)

    def test_high_less_than_close_is_error(self) -> None:
        r = _make_record(price_open="42000", price_high="43000", price_low="41000", price_close="44000")
        errors = validate_ohlcv_relationships(r)
        assert any("high" in e and "close" in e for e in errors)

    def test_low_greater_than_open_is_error(self) -> None:
        r = _make_record(price_open="40000", price_high="43000", price_low="41000", price_close="42500")
        errors = validate_ohlcv_relationships(r)
        assert any("low" in e and "open" in e for e in errors)

    def test_low_greater_than_close_is_error(self) -> None:
        r = _make_record(price_open="42000", price_high="43000", price_low="43500", price_close="42500", skip_validation=True)
        errors = validate_ohlcv_relationships(r)
        assert any("low" in e and "close" in e for e in errors)

    def test_high_less_than_low_is_error(self) -> None:
        r = _make_record(price_open="40000", price_high="39000", price_low="41000", price_close="40500", skip_validation=True)
        errors = validate_ohlcv_relationships(r)
        assert len(errors) > 0

    def test_negative_volume_is_error(self) -> None:
        r = _make_record(volume_24h="-1", skip_validation=True)
        errors = validate_ohlcv_relationships(r)
        assert any("volume" in e for e in errors)

    def test_zero_volume_is_valid(self) -> None:
        r = _make_record(volume_24h="0")
        errors = validate_ohlcv_relationships(r)
        assert errors == []

    def test_multiple_errors_reported(self) -> None:
        # high < open AND low > close
        r = _make_record(price_open="44000", price_high="43000", price_low="43500", price_close="42500", skip_validation=True)
        errors = validate_ohlcv_relationships(r)
        assert len(errors) >= 2

    def test_doji_candle_valid(self) -> None:
        # open == close (doji)
        r = _make_record(price_open="42000", price_high="42500", price_low="41500", price_close="42000")
        errors = validate_ohlcv_relationships(r)
        assert errors == []


# ---------------------------------------------------------------------------
# filter_valid_records
# ---------------------------------------------------------------------------


class TestFilterValidRecords:
    def test_all_valid_records(self) -> None:
        records = [_make_record(timestamp=BASE_TS + timedelta(hours=i)) for i in range(3)]
        valid, invalid = filter_valid_records(records)
        assert len(valid) == 3
        assert len(invalid) == 0

    def test_all_invalid_records(self) -> None:
        # Records with negative volume (bypass model validation)
        records = [_make_record(volume_24h="-100", timestamp=BASE_TS + timedelta(hours=i), skip_validation=True) for i in range(3)]
        valid, invalid = filter_valid_records(records)
        assert len(valid) == 0
        assert len(invalid) == 3

    def test_mixed_valid_and_invalid(self) -> None:
        valid_r = _make_record(timestamp=BASE_TS)
        invalid_r = _make_record(timestamp=BASE_TS + timedelta(hours=1), volume_24h="-1", skip_validation=True)
        valid, invalid = filter_valid_records([valid_r, invalid_r])
        assert len(valid) == 1
        assert len(invalid) == 1

    def test_empty_list(self) -> None:
        valid, invalid = filter_valid_records([])
        assert valid == []
        assert invalid == []

    def test_returns_tuple_of_two_lists(self) -> None:
        result = filter_valid_records([_make_record()])
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_invalid_record_not_in_valid_list(self) -> None:
        bad = _make_record(price_open="44000", price_high="43000", price_low="41000", price_close="42500")
        valid, invalid = filter_valid_records([bad])
        assert bad in invalid
        assert bad not in valid


# ---------------------------------------------------------------------------
# detect_gaps
# ---------------------------------------------------------------------------


class TestDetectGaps:
    def _consecutive_records(self, count: int, interval: timedelta) -> list[OHLCVRecord]:
        return [_make_record(timestamp=BASE_TS + interval * i) for i in range(count)]

    def test_empty_list_returns_no_gaps(self) -> None:
        assert detect_gaps([], timedelta(hours=1)) == []

    def test_single_record_returns_no_gaps(self) -> None:
        assert detect_gaps([_make_record()], timedelta(hours=1)) == []

    def test_consecutive_records_no_gaps(self) -> None:
        records = self._consecutive_records(5, timedelta(hours=1))
        gaps = detect_gaps(records, timedelta(hours=1))
        assert gaps == []

    def test_one_missing_candle_detected(self) -> None:
        r0 = _make_record(timestamp=BASE_TS)
        r1 = _make_record(timestamp=BASE_TS + timedelta(hours=2))  # skip 1 hour
        gaps = detect_gaps([r0, r1], timedelta(hours=1))
        assert len(gaps) == 1
        before, after, missing = gaps[0]
        assert missing == 1
        assert before is r0
        assert after is r1

    def test_multiple_missing_candles_detected(self) -> None:
        r0 = _make_record(timestamp=BASE_TS)
        r1 = _make_record(timestamp=BASE_TS + timedelta(hours=5))  # skip 4 hours
        gaps = detect_gaps([r0, r1], timedelta(hours=1))
        assert len(gaps) == 1
        _, _, missing = gaps[0]
        assert missing == 4

    def test_multiple_gaps_detected(self) -> None:
        r0 = _make_record(timestamp=BASE_TS)
        r1 = _make_record(timestamp=BASE_TS + timedelta(hours=3))  # gap: 2 missing
        r2 = _make_record(timestamp=BASE_TS + timedelta(hours=4))  # no gap
        r3 = _make_record(timestamp=BASE_TS + timedelta(hours=8))  # gap: 3 missing
        gaps = detect_gaps([r0, r1, r2, r3], timedelta(hours=1))
        assert len(gaps) == 2

    def test_gap_tuple_structure(self) -> None:
        r0 = _make_record(timestamp=BASE_TS)
        r1 = _make_record(timestamp=BASE_TS + timedelta(hours=3))
        gaps = detect_gaps([r0, r1], timedelta(hours=1))
        assert len(gaps) == 1
        item = gaps[0]
        assert len(item) == 3  # (record_before, record_after, missing_count)
        assert isinstance(item[2], int)

    def test_daily_timeframe_gap(self) -> None:
        r0 = _make_record(timestamp=BASE_TS)
        r1 = _make_record(timestamp=BASE_TS + timedelta(days=3))  # skip 2 days
        gaps = detect_gaps([r0, r1], timedelta(days=1))
        assert len(gaps) == 1
        _, _, missing = gaps[0]
        assert missing == 2


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
    def test_known_timeframe(self, timeframe: str, expected: timedelta) -> None:
        result = parse_timeframe_to_timedelta(timeframe)
        assert result == expected

    def test_unknown_timeframe_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="Unknown timeframe"):
            parse_timeframe_to_timedelta("6h")

    def test_empty_string_raises_value_error(self) -> None:
        with pytest.raises(ValueError):
            parse_timeframe_to_timedelta("")

    def test_case_sensitive_lowercase_d_raises(self) -> None:
        # "1D" is valid but "1d" is not
        with pytest.raises(ValueError):
            parse_timeframe_to_timedelta("1d")

    def test_return_type_is_timedelta(self) -> None:
        result = parse_timeframe_to_timedelta("1h")
        assert isinstance(result, timedelta)

    def test_error_message_lists_valid_timeframes(self) -> None:
        with pytest.raises(ValueError, match="Valid"):
            parse_timeframe_to_timedelta("99x")
