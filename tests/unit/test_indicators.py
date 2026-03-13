"""Unit tests for ETL indicator computation functions.

Note: tests that invoke pandas_ta are skipped when the numba dependency
required by pandas_ta 0.4.x is not available in the current environment.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

# ---------------------------------------------------------------------------
# Check if pandas_ta is usable (requires numba in 0.4.x)
# ---------------------------------------------------------------------------

_pandas_ta_available = False
try:
    import pandas_ta  # noqa: F401

    _pandas_ta_available = True
except (ImportError, ModuleNotFoundError):
    pass

_requires_pandas_ta = pytest.mark.skipif(
    not _pandas_ta_available,
    reason="pandas_ta not importable (numba missing)",
)

_BASE_TS = datetime(2024, 1, 1, tzinfo=timezone.utc)
_BTC_PRICE = 40_000.0


def _make_rows(n: int, base_price: float = _BTC_PRICE) -> list[dict[str, object]]:
    """Generate n synthetic OHLCV row dicts for testing."""
    rows: list[dict[str, object]] = []
    for i in range(n):
        ts = _BASE_TS + timedelta(hours=i * 4)
        close = base_price + (i % 10) * 100.0
        rows.append(
            {
                "timestamp": ts.isoformat(),
                "price_open": close - 50,
                "price_high": close + 100,
                "price_low": close - 100,
                "price_close": close,
                "volume_24h": 1_000.0 + i * 10,
            }
        )
    return rows


# ---------------------------------------------------------------------------
# _compute_price_vs_bollinger — pure Python, no pandas_ta dependency
# ---------------------------------------------------------------------------


class TestComputePriceVsBollinger:
    """Tests the standalone _compute_price_vs_bollinger helper."""

    def _fn(self, price: float, upper: float, lower: float) -> Decimal | None:
        from src.etl.transformers.indicators import _compute_price_vs_bollinger

        return _compute_price_vs_bollinger(price, upper, lower)

    def test_price_at_upper_band_returns_one(self) -> None:
        result = self._fn(100.0, 100.0, 80.0)
        assert result is not None
        assert float(result) == pytest.approx(1.0)

    def test_price_at_lower_band_returns_minus_one(self) -> None:
        result = self._fn(80.0, 100.0, 80.0)
        assert result is not None
        assert float(result) == pytest.approx(-1.0)

    def test_price_at_midpoint_returns_zero(self) -> None:
        result = self._fn(90.0, 100.0, 80.0)
        assert result is not None
        assert float(result) == pytest.approx(0.0)

    def test_zero_band_width_returns_none(self) -> None:
        result = self._fn(100.0, 100.0, 100.0)
        assert result is None

    def test_price_above_upper_clamps_to_one(self) -> None:
        result = self._fn(200.0, 100.0, 80.0)
        assert result is not None
        assert float(result) == pytest.approx(1.0)

    def test_price_below_lower_clamps_to_minus_one(self) -> None:
        result = self._fn(0.0, 100.0, 80.0)
        assert result is not None
        assert float(result) == pytest.approx(-1.0)

    def test_result_is_decimal(self) -> None:
        result = self._fn(95.0, 100.0, 80.0)
        assert isinstance(result, Decimal)


# ---------------------------------------------------------------------------
# _compute_trend_slope — requires pandas but NOT pandas_ta
# ---------------------------------------------------------------------------


class TestComputeTrendSlope:
    """Tests the linear-regression trend slope helper (pure pandas/numpy)."""

    def _fn(self, rows: list[dict[str, object]], window: int = 20) -> dict:
        from src.etl.transformers.indicators import _build_dataframe, _compute_trend_slope

        df = _build_dataframe(rows)
        return _compute_trend_slope(df, window=window)

    def test_uptrend_has_positive_slope(self) -> None:
        rows = []
        for i in range(30):
            close = 1_000.0 + i * 10.0
            ts = _BASE_TS + timedelta(days=i)
            rows.append(
                {
                    "timestamp": ts.isoformat(),
                    "price_open": close - 5,
                    "price_high": close + 5,
                    "price_low": close - 5,
                    "price_close": close,
                    "volume_24h": 1_000.0,
                }
            )
        result = self._fn(rows)
        last_idx = max(result.keys())
        slope, _ = result[last_idx]
        assert slope > 0

    def test_downtrend_has_negative_slope(self) -> None:
        rows = []
        for i in range(30):
            close = 5_000.0 - i * 50.0
            ts = _BASE_TS + timedelta(days=i)
            rows.append(
                {
                    "timestamp": ts.isoformat(),
                    "price_open": close + 5,
                    "price_high": close + 10,
                    "price_low": close - 5,
                    "price_close": close,
                    "volume_24h": 1_000.0,
                }
            )
        result = self._fn(rows)
        last_idx = max(result.keys())
        slope, _ = result[last_idx]
        assert slope < 0

    def test_insufficient_data_returns_empty(self) -> None:
        rows = _make_rows(10)
        result = self._fn(rows, window=20)
        assert result == {}

    def test_stable_flat_price_trend_type(self) -> None:
        rows = []
        for i in range(30):
            ts = _BASE_TS + timedelta(days=i)
            rows.append(
                {
                    "timestamp": ts.isoformat(),
                    "price_open": 10_000.0,
                    "price_high": 10_001.0,
                    "price_low": 9_999.0,
                    "price_close": 10_000.0,
                    "volume_24h": 1_000.0,
                }
            )
        result = self._fn(rows)
        last_idx = max(result.keys())
        _, trend_type = result[last_idx]
        assert trend_type == "stable"


# ---------------------------------------------------------------------------
# _compute_rsi — requires pandas_ta
# ---------------------------------------------------------------------------


@_requires_pandas_ta
class TestComputeRSI:
    def _fn(self, rows: list[dict[str, object]], period: int = 14):
        from src.etl.transformers.indicators import _build_dataframe, _compute_rsi

        df = _build_dataframe(rows)
        return _compute_rsi(df, period=period)

    def test_rsi_returns_series_of_same_length(self) -> None:
        rows = _make_rows(50)
        rsi = self._fn(rows)
        assert len(rsi) == 50

    def test_rsi_values_between_0_and_100(self) -> None:
        rows = _make_rows(50)
        rsi = self._fn(rows)
        valid = rsi.dropna()
        assert (valid >= 0).all()
        assert (valid <= 100).all()

    def test_rsi_has_early_nan_values(self) -> None:
        rows = _make_rows(30)
        rsi = self._fn(rows, period=14)
        assert rsi.isna().any()

    def test_rsi_near_100_for_steady_uptrend(self) -> None:
        rows = []
        for i in range(50):
            close = 10_000.0 + i * 500.0
            ts = _BASE_TS + timedelta(hours=i)
            rows.append(
                {
                    "timestamp": ts.isoformat(),
                    "price_open": close - 10,
                    "price_high": close + 10,
                    "price_low": close - 20,
                    "price_close": close,
                    "volume_24h": 1_000.0,
                }
            )
        rsi = self._fn(rows)
        last_valid = rsi.dropna().iloc[-1]
        assert last_valid >= 60.0

    def test_rsi_near_0_for_steady_downtrend(self) -> None:
        rows = []
        for i in range(50):
            close = 10_000.0 - i * 200.0
            ts = _BASE_TS + timedelta(hours=i)
            rows.append(
                {
                    "timestamp": ts.isoformat(),
                    "price_open": close + 10,
                    "price_high": close + 20,
                    "price_low": close - 10,
                    "price_close": close,
                    "volume_24h": 1_000.0,
                }
            )
        rsi = self._fn(rows)
        last_valid = rsi.dropna().iloc[-1]
        assert last_valid <= 40.0


# ---------------------------------------------------------------------------
# compute_indicators_for_symbol — public API (requires pandas_ta)
# ---------------------------------------------------------------------------


@_requires_pandas_ta
class TestComputeIndicatorsForSymbol:
    def test_returns_empty_with_insufficient_data(self) -> None:
        from src.etl.transformers.indicators import compute_indicators_for_symbol

        rows = _make_rows(10)
        result = compute_indicators_for_symbol(rows, "BTCUSDT", "1h")
        assert result == []

    def test_returns_records_for_rsi_bb_timeframe(self) -> None:
        from src.etl.transformers.indicators import compute_indicators_for_symbol

        rows = _make_rows(50)
        result = compute_indicators_for_symbol(rows, "BTCUSDT", "4h")
        assert len(result) > 0

    def test_records_have_correct_symbol_and_timeframe(self) -> None:
        from src.etl.transformers.indicators import compute_indicators_for_symbol

        rows = _make_rows(30)
        result = compute_indicators_for_symbol(rows, "ETHUSDT", "1h")
        for rec in result:
            assert rec.symbol == "ETHUSDT"
            assert rec.timeframe == "1h"

    def test_trend_not_computed_for_1h_timeframe(self) -> None:
        from src.etl.transformers.indicators import compute_indicators_for_symbol

        rows = _make_rows(50)
        result = compute_indicators_for_symbol(rows, "BTCUSDT", "1h")
        records_with_trend = [r for r in result if r.trend_slope is not None]
        assert len(records_with_trend) == 0
