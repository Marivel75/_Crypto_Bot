"""Unit tests for src.etl.transformers.indicators — pure computation, no I/O."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from src.etl.transformers.indicators import (
    _compute_price_vs_bollinger,
    compute_indicators_for_symbol,
)
from src.shared.models.crypto import IndicatorRecord

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BASE_TS = datetime(2023, 1, 1, 0, 0, 0, tzinfo=timezone.utc)


def _make_rows(
    n: int,
    *,
    base_price: float = 42000.0,
    trend: float = 10.0,
) -> list[dict[str, object]]:
    """Generate n OHLCV row dicts with a gentle upward trend.

    The prices are deterministic: no randomness, so tests are reproducible.
    high = close + 50, low = close - 50, open = previous close.
    """
    rows: list[dict[str, object]] = []
    price = base_price
    for i in range(n):
        close = price + trend * i
        rows.append(
            {
                "timestamp": _BASE_TS + timedelta(hours=i),
                "price_open": Decimal(str(round(close - 5, 2))),
                "price_high": Decimal(str(round(close + 50, 2))),
                "price_low": Decimal(str(round(close - 50, 2))),
                "price_close": Decimal(str(round(close, 2))),
                "volume_24h": Decimal("1000.00"),
            }
        )
    return rows


def _make_flat_rows(n: int, price: float = 50000.0) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for i in range(n):
        rows.append(
            {
                "timestamp": _BASE_TS + timedelta(hours=i),
                "price_open": Decimal(str(price)),
                "price_high": Decimal(str(price + 10)),
                "price_low": Decimal(str(price - 10)),
                "price_close": Decimal(str(price)),
                "volume_24h": Decimal("500.00"),
            }
        )
    return rows


# ---------------------------------------------------------------------------
# compute_indicators_for_symbol — insufficient data
# ---------------------------------------------------------------------------


class TestComputeIndicatorsInsufficientData:
    def test_fewer_than_20_rows_returns_empty(self) -> None:
        rows = _make_rows(19)
        result = compute_indicators_for_symbol(rows, "BTCUSDT", "1h")
        assert result == []

    def test_exactly_0_rows_returns_empty(self) -> None:
        result = compute_indicators_for_symbol([], "BTCUSDT", "4h")
        assert result == []

    def test_exactly_19_rows_returns_empty(self) -> None:
        rows = _make_rows(19)
        result = compute_indicators_for_symbol(rows, "ETHUSDT", "1h")
        assert result == []

    def test_exactly_20_rows_returns_some_records(self) -> None:
        rows = _make_rows(20)
        result = compute_indicators_for_symbol(rows, "BTCUSDT", "1h")
        # Should return at least some records (where indicators are non-null)
        assert len(result) > 0


# ---------------------------------------------------------------------------
# compute_indicators_for_symbol — return types and structure
# ---------------------------------------------------------------------------


class TestComputeIndicatorsReturnStructure:
    def test_returns_list_of_indicator_records(self) -> None:
        rows = _make_rows(50)
        result = compute_indicators_for_symbol(rows, "BTCUSDT", "1h")
        for rec in result:
            assert isinstance(rec, IndicatorRecord)

    def test_symbol_propagated_to_all_records(self) -> None:
        rows = _make_rows(50)
        result = compute_indicators_for_symbol(rows, "SOLUSDT", "1h")
        for rec in result:
            assert rec.symbol == "SOLUSDT"

    def test_timeframe_propagated_to_all_records(self) -> None:
        rows = _make_rows(50)
        result = compute_indicators_for_symbol(rows, "BTCUSDT", "4h")
        for rec in result:
            assert rec.timeframe == "4h"

    def test_timestamps_are_timezone_aware(self) -> None:
        rows = _make_rows(50)
        result = compute_indicators_for_symbol(rows, "BTCUSDT", "1h")
        for rec in result:
            assert rec.timestamp.tzinfo is not None


# ---------------------------------------------------------------------------
# RSI — range and timeframe routing
# ---------------------------------------------------------------------------


class TestComputeIndicatorsRsi:
    def test_rsi_is_in_range_0_to_100(self) -> None:
        rows = _make_rows(50)
        result = compute_indicators_for_symbol(rows, "BTCUSDT", "1h")
        rsi_values = [float(rec.rsi) for rec in result if rec.rsi is not None]
        assert len(rsi_values) > 0
        for v in rsi_values:
            assert 0.0 <= v <= 100.0, f"RSI out of range: {v}"

    @pytest.mark.parametrize("timeframe", ["1h", "2h", "3h", "4h", "1D"])
    def test_rsi_computed_for_rsi_bb_timeframes(self, timeframe: str) -> None:
        rows = _make_rows(50)
        result = compute_indicators_for_symbol(rows, "BTCUSDT", timeframe)
        rsi_values = [rec.rsi for rec in result if rec.rsi is not None]
        assert len(rsi_values) > 0, f"Expected RSI for timeframe {timeframe!r}"

    @pytest.mark.parametrize("timeframe", ["1m", "5m"])
    def test_rsi_not_computed_for_short_timeframes(self, timeframe: str) -> None:
        rows = _make_rows(50)
        result = compute_indicators_for_symbol(rows, "BTCUSDT", timeframe)
        # RSI is None for all records on non-RSI timeframes
        for rec in result:
            assert rec.rsi is None, f"Unexpected RSI on timeframe {timeframe!r}"

    def test_rsi_high_on_rising_prices(self) -> None:
        """Strong uptrend should produce RSI values well above 50."""
        rows = _make_rows(50, trend=100.0)  # steep uptrend
        result = compute_indicators_for_symbol(rows, "BTCUSDT", "1h")
        rsi_values = [float(rec.rsi) for rec in result if rec.rsi is not None]
        assert any(v > 60.0 for v in rsi_values)


# ---------------------------------------------------------------------------
# Bollinger Bands — ordering and timeframe routing
# ---------------------------------------------------------------------------


class TestComputeIndicatorsBollinger:
    def test_bollinger_bands_upper_gte_middle_gte_lower(self) -> None:
        rows = _make_rows(50)
        result = compute_indicators_for_symbol(rows, "BTCUSDT", "1h")

        for rec in result:
            if rec.bollinger_upper is not None:
                assert rec.bollinger_upper >= rec.bollinger_middle, (
                    f"upper {rec.bollinger_upper} < middle {rec.bollinger_middle}"
                )
                assert rec.bollinger_middle >= rec.bollinger_lower, (
                    f"middle {rec.bollinger_middle} < lower {rec.bollinger_lower}"
                )

    def test_bollinger_bands_all_three_present_together(self) -> None:
        rows = _make_rows(50)
        result = compute_indicators_for_symbol(rows, "BTCUSDT", "4h")
        bb_records = [rec for rec in result if rec.bollinger_upper is not None]
        for rec in bb_records:
            assert rec.bollinger_middle is not None
            assert rec.bollinger_lower is not None

    @pytest.mark.parametrize("timeframe", ["1m", "5m"])
    def test_bollinger_not_computed_for_short_timeframes(self, timeframe: str) -> None:
        rows = _make_rows(50)
        result = compute_indicators_for_symbol(rows, "BTCUSDT", timeframe)
        for rec in result:
            assert rec.bollinger_upper is None
            assert rec.bollinger_middle is None
            assert rec.bollinger_lower is None

    def test_price_vs_bollinger_present_when_bands_present(self) -> None:
        rows = _make_rows(50)
        result = compute_indicators_for_symbol(rows, "BTCUSDT", "1h")
        for rec in result:
            if rec.bollinger_upper is not None:
                assert rec.price_vs_bollinger is not None

    def test_price_vs_bollinger_in_range_minus_1_to_1(self) -> None:
        rows = _make_rows(50)
        result = compute_indicators_for_symbol(rows, "BTCUSDT", "1h")
        pvb_values = [float(rec.price_vs_bollinger) for rec in result if rec.price_vs_bollinger is not None]
        assert len(pvb_values) > 0
        for v in pvb_values:
            assert -1.0 <= v <= 1.0, f"price_vs_bollinger out of range: {v}"


# ---------------------------------------------------------------------------
# Trend — timeframe routing
# ---------------------------------------------------------------------------


class TestComputeIndicatorsTrend:
    @pytest.mark.parametrize("timeframe", ["1D", "1W", "1M"])
    def test_trend_computed_for_trend_timeframes(self, timeframe: str) -> None:
        rows = _make_rows(50)
        result = compute_indicators_for_symbol(rows, "BTCUSDT", timeframe)
        slope_values = [rec.trend_slope for rec in result if rec.trend_slope is not None]
        assert len(slope_values) > 0, f"Expected trend slope for timeframe {timeframe!r}"

    @pytest.mark.parametrize("timeframe", ["1h", "4h"])
    def test_trend_not_computed_for_intraday_timeframes(self, timeframe: str) -> None:
        rows = _make_rows(50)
        result = compute_indicators_for_symbol(rows, "BTCUSDT", timeframe)
        for rec in result:
            assert rec.trend_slope is None
            assert rec.trend_type is None

    def test_trend_type_is_valid_string(self) -> None:
        rows = _make_rows(50, trend=50.0)
        result = compute_indicators_for_symbol(rows, "BTCUSDT", "1D")
        for rec in result:
            if rec.trend_type is not None:
                assert rec.trend_type in ("stable", "aggressive")

    def test_flat_prices_yield_stable_trend_type(self) -> None:
        rows = _make_flat_rows(50)
        result = compute_indicators_for_symbol(rows, "BTCUSDT", "1D")
        trend_types = [rec.trend_type for rec in result if rec.trend_type is not None]
        assert len(trend_types) > 0
        assert all(t == "stable" for t in trend_types)


# ---------------------------------------------------------------------------
# Volume metadata
# ---------------------------------------------------------------------------


class TestComputeIndicatorsVolumeMeta:
    def test_volume_relatif_in_metadata(self) -> None:
        rows = _make_rows(50)
        result = compute_indicators_for_symbol(rows, "BTCUSDT", "1h")
        meta_records = [rec for rec in result if "volume_relatif" in rec.metadata]
        assert len(meta_records) > 0

    def test_volume_relatif_is_positive_float(self) -> None:
        rows = _make_rows(50)
        result = compute_indicators_for_symbol(rows, "BTCUSDT", "1h")
        for rec in result:
            vr = rec.metadata.get("volume_relatif")
            if vr is not None:
                assert isinstance(vr, float)
                assert vr >= 0.0


# ---------------------------------------------------------------------------
# _compute_price_vs_bollinger (private, tested directly for coverage)
# ---------------------------------------------------------------------------


class TestComputePriceVsBollinger:
    def test_price_at_middle_returns_zero(self) -> None:
        result = _compute_price_vs_bollinger(price=50.0, upper=60.0, lower=40.0)
        assert result is not None
        assert float(result) == pytest.approx(0.0, abs=1e-6)

    def test_price_at_upper_returns_one(self) -> None:
        result = _compute_price_vs_bollinger(price=60.0, upper=60.0, lower=40.0)
        assert result is not None
        assert float(result) == pytest.approx(1.0, abs=1e-6)

    def test_price_at_lower_returns_minus_one(self) -> None:
        result = _compute_price_vs_bollinger(price=40.0, upper=60.0, lower=40.0)
        assert result is not None
        assert float(result) == pytest.approx(-1.0, abs=1e-6)

    def test_price_above_upper_clamped_to_one(self) -> None:
        result = _compute_price_vs_bollinger(price=999.0, upper=60.0, lower=40.0)
        assert result is not None
        assert float(result) == pytest.approx(1.0, abs=1e-6)

    def test_price_below_lower_clamped_to_minus_one(self) -> None:
        result = _compute_price_vs_bollinger(price=0.0, upper=60.0, lower=40.0)
        assert result is not None
        assert float(result) == pytest.approx(-1.0, abs=1e-6)

    def test_zero_bandwidth_returns_none(self) -> None:
        result = _compute_price_vs_bollinger(price=50.0, upper=50.0, lower=50.0)
        assert result is None

    def test_result_is_decimal(self) -> None:
        result = _compute_price_vs_bollinger(price=55.0, upper=60.0, lower=40.0)
        assert isinstance(result, Decimal)

    def test_result_in_range_minus_1_to_1_for_arbitrary_price(self) -> None:
        for price in [41.0, 45.0, 50.0, 55.0, 59.0]:
            result = _compute_price_vs_bollinger(price=price, upper=60.0, lower=40.0)
            assert result is not None
            assert -1.0 <= float(result) <= 1.0
