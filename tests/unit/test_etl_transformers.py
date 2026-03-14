"""Unit tests for ETL transformers: indicator computation and data cleaning.

Covers:
- TestRSIComputation     — RSI via compute_indicators_for_symbol
- TestBollingerComputation — Bollinger Bands via compute_indicators_for_symbol
- TestCleaner            — validate_ohlcv_relationships, deduplicate_ohlcv, detect_gaps
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from src.etl.transformers.cleaner import (
    deduplicate_ohlcv,
    detect_gaps,
    validate_ohlcv_relationships,
)
from src.etl.transformers.indicators import compute_indicators_for_symbol
from src.shared.models.crypto import OHLCVRecord

# ---------------------------------------------------------------------------
# Fixed reference timestamp (UTC, no drift across test runs)
# ---------------------------------------------------------------------------
_T0 = datetime(2024, 1, 15, 0, 0, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ohlcv_record(
    *,
    symbol: str = "BTCUSDT",
    timeframe: str = "1h",
    timestamp: datetime | None = None,
    price_open: float = 50_000.0,
    price_high: float = 50_500.0,
    price_low: float = 49_500.0,
    price_close: float = 50_200.0,
    volume: float = 1_000.0,
    source: str = "binance",
    skip_validation: bool = False,
) -> OHLCVRecord:
    kwargs = {
        "symbol": symbol,
        "timeframe": timeframe,
        "timestamp": timestamp or _T0,
        "price_open": Decimal(str(price_open)),
        "price_high": Decimal(str(price_high)),
        "price_low": Decimal(str(price_low)),
        "price_close": Decimal(str(price_close)),
        "volume_24h": Decimal(str(volume)),
        "source": source,
    }
    if skip_validation:
        return OHLCVRecord.model_construct(**kwargs)
    return OHLCVRecord(**kwargs)


def _make_row_dict(
    *,
    timestamp: datetime,
    price_open: float,
    price_high: float,
    price_low: float,
    price_close: float,
    volume: float = 1_000.0,
) -> dict[str, Any]:
    """Build the row-dict format expected by compute_indicators_for_symbol."""
    return {
        "timestamp": timestamp,
        "price_open": price_open,
        "price_high": price_high,
        "price_low": price_low,
        "price_close": price_close,
        "volume_24h": volume,
    }


def _declining_prices(n: int, start: float = 50_000.0, step: float = 200.0) -> list[float]:
    """Return a strictly descending price series of length n."""
    return [start - i * step for i in range(n)]


def _rising_prices(n: int, start: float = 40_000.0, step: float = 200.0) -> list[float]:
    """Return a strictly ascending price series of length n."""
    return [start + i * step for i in range(n)]


def _build_rows_from_closes(
    closes: list[float],
    start_ts: datetime = _T0,
    interval: timedelta = timedelta(hours=1),
) -> list[dict[str, Any]]:
    """Build OHLCV row dicts from a list of close prices."""
    rows: list[dict[str, Any]] = []
    for i, close in enumerate(closes):
        ts = start_ts + i * interval
        rows.append(
            _make_row_dict(
                timestamp=ts,
                price_open=close - 50.0,
                price_high=close + 100.0,
                price_low=close - 100.0,
                price_close=close,
            )
        )
    return rows


# ---------------------------------------------------------------------------
# TestRSIComputation
# ---------------------------------------------------------------------------


class TestRSIComputation:
    """RSI is computed via the public compute_indicators_for_symbol function.

    The function requires >= 20 rows to proceed and uses pandas-ta RSI(14).
    We need at least 15 rows (period + 1) of data for RSI to produce a
    non-NaN value, and at least 20 rows total to pass the function guard.
    """

    def test_rsi_oversold(self) -> None:
        """Consistently declining prices should produce RSI < 30."""
        closes = _declining_prices(n=50, start=50_000.0, step=300.0)
        rows = _build_rows_from_closes(closes)

        records = compute_indicators_for_symbol(rows, symbol="BTCUSDT", timeframe="1h")

        # Filter to records that have a valid RSI value
        rsi_values = [float(r.rsi) for r in records if r.rsi is not None]
        assert len(rsi_values) > 0, "Expected at least one RSI value to be computed"

        # The tail end of a sharp decline should push RSI well below 30
        final_rsi = rsi_values[-1]
        assert final_rsi < 30.0, f"Expected RSI < 30 for declining prices, got {final_rsi:.2f}"

    def test_rsi_overbought(self) -> None:
        """Consistently rising prices should produce RSI > 70."""
        closes = _rising_prices(n=50, start=40_000.0, step=300.0)
        rows = _build_rows_from_closes(closes)

        records = compute_indicators_for_symbol(rows, symbol="BTCUSDT", timeframe="1h")

        rsi_values = [float(r.rsi) for r in records if r.rsi is not None]
        assert len(rsi_values) > 0, "Expected at least one RSI value to be computed"

        final_rsi = rsi_values[-1]
        assert final_rsi > 70.0, f"Expected RSI > 70 for rising prices, got {final_rsi:.2f}"

    def test_rsi_neutral(self) -> None:
        """Alternating up/down prices should produce RSI near 50."""
        # Build a series that alternates: up 200, down 200, up 200 …
        n = 50
        closes: list[float] = []
        price = 50_000.0
        for i in range(n):
            price += 200.0 if i % 2 == 0 else -200.0
            closes.append(price)

        rows = _build_rows_from_closes(closes)
        records = compute_indicators_for_symbol(rows, symbol="BTCUSDT", timeframe="1h")

        rsi_values = [float(r.rsi) for r in records if r.rsi is not None]
        assert len(rsi_values) > 0

        # Neutral RSI should sit in the mid-range [30, 70]
        final_rsi = rsi_values[-1]
        assert 30.0 <= final_rsi <= 70.0, f"Expected neutral RSI in [30, 70], got {final_rsi:.2f}"

    def test_rsi_insufficient_data(self) -> None:
        """Fewer than 20 rows should return an empty list (function guard)."""
        closes = _rising_prices(n=15)
        rows = _build_rows_from_closes(closes)

        records = compute_indicators_for_symbol(rows, symbol="BTCUSDT", timeframe="1h")

        assert records == [], "Expected empty list when fewer than 20 rows are provided"

    def test_rsi_not_computed_for_excluded_timeframe(self) -> None:
        """RSI is only computed for RSI_BB timeframes; '1W' should have rsi=None."""
        closes = _rising_prices(n=50)
        rows = _build_rows_from_closes(closes)

        records = compute_indicators_for_symbol(rows, symbol="BTCUSDT", timeframe="1W")

        # All RSI values must be None for a non-RSI_BB timeframe
        rsi_values = [r.rsi for r in records if r.rsi is not None]
        assert rsi_values == [], "RSI should not be computed for '1W' timeframe"


# ---------------------------------------------------------------------------
# TestBollingerComputation
# ---------------------------------------------------------------------------


class TestBollingerComputation:
    """Bollinger Bands are computed alongside RSI for applicable timeframes."""

    def test_bollinger_bands_normal(self) -> None:
        """For normal price data, upper >= middle >= lower must hold."""
        closes = [50_000.0 + 100.0 * (i % 7 - 3) for i in range(50)]
        rows = _build_rows_from_closes(closes)

        records = compute_indicators_for_symbol(rows, symbol="BTCUSDT", timeframe="4h")

        bb_records = [r for r in records if r.bollinger_upper is not None]
        assert len(bb_records) > 0, "Expected Bollinger Band records to be computed"

        for rec in bb_records:
            upper = float(rec.bollinger_upper)  # type: ignore[arg-type]
            middle = float(rec.bollinger_middle)  # type: ignore[arg-type]
            lower = float(rec.bollinger_lower)  # type: ignore[arg-type]
            assert upper >= middle, f"upper ({upper}) must be >= middle ({middle})"
            assert middle >= lower, f"middle ({middle}) must be >= lower ({lower})"

    def test_bollinger_constant_prices(self) -> None:
        """Constant prices yield zero std dev: upper == middle == lower."""
        closes = [50_000.0] * 50
        rows = _build_rows_from_closes(closes)

        records = compute_indicators_for_symbol(rows, symbol="BTCUSDT", timeframe="1h")

        bb_records = [r for r in records if r.bollinger_upper is not None]
        assert len(bb_records) > 0

        for rec in bb_records:
            upper = float(rec.bollinger_upper)  # type: ignore[arg-type]
            middle = float(rec.bollinger_middle)  # type: ignore[arg-type]
            lower = float(rec.bollinger_lower)  # type: ignore[arg-type]
            assert abs(upper - middle) < 1e-4, f"Constant prices: upper ({upper}) should equal middle ({middle})"
            assert abs(middle - lower) < 1e-4, f"Constant prices: middle ({middle}) should equal lower ({lower})"

    def test_bollinger_insufficient_data(self) -> None:
        """Fewer than 20 rows should return an empty list."""
        closes = _rising_prices(n=19)
        rows = _build_rows_from_closes(closes)

        records = compute_indicators_for_symbol(rows, symbol="BTCUSDT", timeframe="1h")

        assert records == [], "Expected empty list when fewer than 20 rows provided"

    def test_bollinger_price_vs_bollinger_range(self) -> None:
        """price_vs_bollinger must be in [-1, 1] for all computed records."""
        closes = [50_000.0 + 500.0 * (i % 5 - 2) for i in range(50)]
        rows = _build_rows_from_closes(closes)

        records = compute_indicators_for_symbol(rows, symbol="BTCUSDT", timeframe="2h")

        pvb_records = [r for r in records if r.price_vs_bollinger is not None]
        assert len(pvb_records) > 0

        for rec in pvb_records:
            pvb = float(rec.price_vs_bollinger)  # type: ignore[arg-type]
            assert -1.0 <= pvb <= 1.0, f"price_vs_bollinger={pvb} out of [-1, 1]"

    def test_bollinger_not_computed_for_excluded_timeframe(self) -> None:
        """Bollinger Bands should not be computed for '1W' timeframe."""
        closes = _rising_prices(n=50)
        rows = _build_rows_from_closes(closes)

        records = compute_indicators_for_symbol(rows, symbol="BTCUSDT", timeframe="1W")

        bb_records = [r for r in records if r.bollinger_upper is not None]
        assert bb_records == [], "Bollinger Bands should not be computed for '1W'"


# ---------------------------------------------------------------------------
# TestCleaner
# ---------------------------------------------------------------------------


class TestCleaner:
    """Tests for validate_ohlcv_relationships, deduplicate_ohlcv, detect_gaps."""

    # ------------------------------------------------------------------
    # validate_ohlcv_relationships
    # ------------------------------------------------------------------

    def test_validate_ohlcv_valid(self) -> None:
        """A well-formed OHLCV record should produce no validation errors."""
        record = _make_ohlcv_record(
            price_open=50_000.0,
            price_high=51_000.0,
            price_low=49_000.0,
            price_close=50_500.0,
            volume=1_000.0,
        )
        errors = validate_ohlcv_relationships(record)
        assert errors == [], f"Expected no errors, got: {errors}"

    def test_validate_ohlcv_invalid_high_less_than_close(self) -> None:
        """high < close is a violation that must be reported."""
        record = _make_ohlcv_record(
            price_open=50_000.0,
            price_high=49_000.0,  # lower than close — invalid
            price_low=48_000.0,
            price_close=50_500.0,
        )
        errors = validate_ohlcv_relationships(record)
        assert len(errors) > 0, "Expected violation for high < close"
        assert any("high" in e and "close" in e for e in errors), (
            f"Expected a 'high < close' error message, got: {errors}"
        )

    def test_validate_ohlcv_invalid_low_greater_than_open(self) -> None:
        """low > open is a violation that must be reported."""
        record = _make_ohlcv_record(
            price_open=50_000.0,
            price_high=51_000.0,
            price_low=50_800.0,  # higher than open — invalid
            price_close=50_900.0,
        )
        errors = validate_ohlcv_relationships(record)
        assert len(errors) > 0
        assert any("low" in e and "open" in e for e in errors)

    def test_validate_ohlcv_invalid_high_less_than_low(self) -> None:
        """high < low is a fundamental OHLCV violation."""
        record = _make_ohlcv_record(
            price_open=50_000.0,
            price_high=48_000.0,  # below low — invalid
            price_low=49_000.0,
            price_close=49_500.0,
            skip_validation=True,
        )
        errors = validate_ohlcv_relationships(record)
        assert len(errors) > 0
        assert any("high" in e and "low" in e for e in errors)

    def test_validate_ohlcv_negative_volume(self) -> None:
        """Negative volume is a violation."""
        record = _make_ohlcv_record(
            price_open=50_000.0,
            price_high=51_000.0,
            price_low=49_000.0,
            price_close=50_500.0,
            volume=-1.0,
            skip_validation=True,
        )
        errors = validate_ohlcv_relationships(record)
        assert len(errors) > 0
        assert any("volume" in e for e in errors)

    def test_validate_ohlcv_doji_candle(self) -> None:
        """open == close (doji) with high == low == open is valid."""
        record = _make_ohlcv_record(
            price_open=50_000.0,
            price_high=50_000.0,
            price_low=50_000.0,
            price_close=50_000.0,
        )
        errors = validate_ohlcv_relationships(record)
        assert errors == [], f"Doji candle should be valid, got: {errors}"

    # ------------------------------------------------------------------
    # deduplicate_ohlcv
    # ------------------------------------------------------------------

    def test_deduplicate_no_duplicates(self) -> None:
        """List with no duplicates should be returned unchanged."""
        records = [_make_ohlcv_record(timestamp=_T0 + timedelta(hours=i)) for i in range(5)]
        result = deduplicate_ohlcv(records)
        assert len(result) == 5

    def test_deduplicate_removes_exact_duplicates(self) -> None:
        """Records sharing (symbol, timeframe, timestamp) should be deduplicated."""
        ts = _T0
        records = [
            _make_ohlcv_record(timestamp=ts),
            _make_ohlcv_record(timestamp=ts),  # duplicate
            _make_ohlcv_record(timestamp=ts + timedelta(hours=1)),
        ]
        result = deduplicate_ohlcv(records)
        assert len(result) == 2

    def test_deduplicate_preserves_order(self) -> None:
        """The first occurrence of each key should be kept, in order."""
        ts1 = _T0
        ts2 = _T0 + timedelta(hours=1)
        ts3 = _T0 + timedelta(hours=2)
        records = [
            _make_ohlcv_record(timestamp=ts1, price_close=50_000.0),
            _make_ohlcv_record(timestamp=ts2, price_close=51_000.0),
            _make_ohlcv_record(timestamp=ts1, price_close=99_999.0),  # dup — must be dropped
            _make_ohlcv_record(timestamp=ts3, price_close=52_000.0),
        ]
        result = deduplicate_ohlcv(records)
        assert len(result) == 3
        assert float(result[0].price_close) == 50_000.0  # first occurrence kept

    def test_deduplicate_different_symbols_not_merged(self) -> None:
        """Same timestamp but different symbols are not duplicates."""
        ts = _T0
        records = [
            _make_ohlcv_record(symbol="BTCUSDT", timestamp=ts),
            _make_ohlcv_record(symbol="ETHUSDT", timestamp=ts),
        ]
        result = deduplicate_ohlcv(records)
        assert len(result) == 2

    def test_deduplicate_empty_list(self) -> None:
        """Empty input should return an empty list."""
        assert deduplicate_ohlcv([]) == []

    # ------------------------------------------------------------------
    # detect_gaps
    # ------------------------------------------------------------------

    def test_detect_gaps_no_gaps(self) -> None:
        """Consecutive hourly records with no gaps should return empty list."""
        interval = timedelta(hours=1)
        records = [_make_ohlcv_record(timestamp=_T0 + i * interval) for i in range(10)]
        gaps = detect_gaps(records, expected_interval=interval)
        assert gaps == []

    def test_detect_gaps_single_gap(self) -> None:
        """One missing candle between two records should be reported."""
        interval = timedelta(hours=1)
        # Build records with a 2-hour jump between index 4 and 5 (1 candle missing)
        timestamps = [_T0 + i * interval for i in range(5)]
        timestamps.append(_T0 + 6 * interval)  # skip hour 5 → gap of 1

        records = [_make_ohlcv_record(timestamp=ts) for ts in timestamps]
        gaps = detect_gaps(records, expected_interval=interval)

        assert len(gaps) == 1
        before, after, missing = gaps[0]
        assert missing == 1
        assert before.timestamp == _T0 + 4 * interval
        assert after.timestamp == _T0 + 6 * interval

    def test_detect_gaps_multiple_gaps(self) -> None:
        """Multiple gaps across the series should all be detected."""
        interval = timedelta(hours=4)
        # Timestamps: 0h, 4h, 8h, 20h (gap of 2), 24h, 36h (gap of 2)
        offsets_hours = [0, 4, 8, 20, 24, 36]
        records = [_make_ohlcv_record(timestamp=_T0 + timedelta(hours=h)) for h in offsets_hours]
        gaps = detect_gaps(records, expected_interval=interval)

        assert len(gaps) == 2
        missing_counts = sorted(g[2] for g in gaps)
        assert missing_counts == [2, 2]

    def test_detect_gaps_large_gap(self) -> None:
        """A gap spanning many candles should report the correct missing count."""
        interval = timedelta(hours=1)
        records = [
            _make_ohlcv_record(timestamp=_T0),
            _make_ohlcv_record(timestamp=_T0 + timedelta(hours=10)),  # 9 missing
        ]
        gaps = detect_gaps(records, expected_interval=interval)

        assert len(gaps) == 1
        _, _, missing = gaps[0]
        assert missing == 9

    def test_detect_gaps_single_record(self) -> None:
        """A single record cannot form a gap — should return empty list."""
        records = [_make_ohlcv_record()]
        gaps = detect_gaps(records, expected_interval=timedelta(hours=1))
        assert gaps == []

    def test_detect_gaps_empty_list(self) -> None:
        """Empty input should return an empty list."""
        gaps = detect_gaps([], expected_interval=timedelta(hours=1))
        assert gaps == []
