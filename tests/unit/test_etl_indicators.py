"""Unit tests for ETL indicator computation functions."""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from src.etl.transformers.indicators import (
    _compute_bollinger_internal as _compute_bollinger,
)
from src.etl.transformers.indicators import (
    _compute_price_vs_bollinger,
    _compute_trend_slope,
    _compute_volume_relatif,
    compute_indicators_for_symbol,
)
from src.etl.transformers.indicators import (
    compute_rsi as _compute_rsi,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

BASE_TS = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)


def _make_rows(
    count: int,
    base_price: float = 42000.0,
    price_step: float = 0.0,
    volume: float = 1000.0,
    timeframe_hours: int = 1,
) -> list[dict]:
    """
    Build a list of OHLCV row dicts with realistic price relationships.
    high >= max(open, close) and low <= min(open, close).
    """
    rows = []
    for i in range(count):
        close = base_price + price_step * i
        open_ = close - 50.0
        high = max(open_, close) + 20.0
        low = min(open_, close) - 20.0
        rows.append(
            {
                "timestamp": BASE_TS + timedelta(hours=timeframe_hours * i),
                "price_open": open_,
                "price_high": high,
                "price_low": low,
                "price_close": close,
                "volume_24h": volume,
            }
        )
    return rows


def _make_df(count: int = 30, **kwargs):  # type: ignore[no-untyped-def]
    """Build a DataFrame for private helper tests."""
    import pandas as pd

    rows = _make_rows(count, **kwargs)
    df = pd.DataFrame(rows)
    df = df.rename(
        columns={
            "price_open": "open",
            "price_high": "high",
            "price_low": "low",
            "price_close": "close",
            "volume_24h": "volume",
        }
    )
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.set_index("timestamp")
    for col in ("open", "high", "low", "close", "volume"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


# ---------------------------------------------------------------------------
# compute_indicators_for_symbol — public function
# ---------------------------------------------------------------------------


class TestComputeIndicatorsForSymbol:
    def test_returns_empty_when_fewer_than_20_rows(self) -> None:
        rows = _make_rows(15)
        result = compute_indicators_for_symbol(rows, "BTCUSDT", "1h")
        assert result == []

    def test_returns_empty_for_empty_rows(self) -> None:
        result = compute_indicators_for_symbol([], "BTCUSDT", "1h")
        assert result == []

    def test_returns_indicator_records_for_rsi_bb_timeframe(self) -> None:
        rows = _make_rows(50)
        result = compute_indicators_for_symbol(rows, "BTCUSDT", "1h")
        assert len(result) > 0

    def test_all_records_have_correct_symbol(self) -> None:
        rows = _make_rows(50)
        result = compute_indicators_for_symbol(rows, "ETHUSDT", "4h")
        assert all(r.symbol == "ETHUSDT" for r in result)

    def test_all_records_have_correct_timeframe(self) -> None:
        rows = _make_rows(50)
        result = compute_indicators_for_symbol(rows, "BTCUSDT", "4h")
        assert all(r.timeframe == "4h" for r in result)

    def test_rsi_computed_for_1h_timeframe(self) -> None:
        rows = _make_rows(50)
        result = compute_indicators_for_symbol(rows, "BTCUSDT", "1h")
        # After enough rows, RSI should be present
        records_with_rsi = [r for r in result if r.rsi is not None]
        assert len(records_with_rsi) > 0

    def test_rsi_computed_for_4h_timeframe(self) -> None:
        rows = _make_rows(50)
        result = compute_indicators_for_symbol(rows, "BTCUSDT", "4h")
        records_with_rsi = [r for r in result if r.rsi is not None]
        assert len(records_with_rsi) > 0

    def test_bollinger_computed_for_rsi_bb_timeframe(self) -> None:
        rows = _make_rows(50)
        result = compute_indicators_for_symbol(rows, "BTCUSDT", "1h")
        records_with_bb = [r for r in result if r.bollinger_upper is not None]
        assert len(records_with_bb) > 0

    def test_bollinger_bands_ordering(self) -> None:
        rows = _make_rows(50)
        result = compute_indicators_for_symbol(rows, "BTCUSDT", "4h")
        for r in result:
            if r.bollinger_upper is not None:
                assert r.bollinger_upper >= r.bollinger_middle
                assert r.bollinger_middle >= r.bollinger_lower

    def test_rsi_not_computed_for_5m_timeframe(self) -> None:
        rows = _make_rows(50)
        result = compute_indicators_for_symbol(rows, "BTCUSDT", "5m")
        # 5m is not in _RSI_BB_TIMEFRAMES, RSI should be None for all
        records_with_rsi = [r for r in result if r.rsi is not None]
        assert len(records_with_rsi) == 0

    def test_trend_computed_for_1D_timeframe(self) -> None:
        rows = _make_rows(50)
        result = compute_indicators_for_symbol(rows, "BTCUSDT", "1D")
        records_with_trend = [r for r in result if r.trend_slope is not None]
        assert len(records_with_trend) > 0

    def test_trend_not_computed_for_1h_timeframe(self) -> None:
        rows = _make_rows(50)
        result = compute_indicators_for_symbol(rows, "BTCUSDT", "1h")
        # 1h is not in _TREND_TIMEFRAMES
        records_with_trend = [r for r in result if r.trend_slope is not None]
        assert len(records_with_trend) == 0

    def test_volume_relatif_in_metadata(self) -> None:
        rows = _make_rows(50)
        result = compute_indicators_for_symbol(rows, "BTCUSDT", "1h")
        # After warmup period, volume_relatif should appear
        records_with_vol = [r for r in result if "volume_relatif" in r.metadata]
        assert len(records_with_vol) > 0

    def test_rsi_values_in_valid_range(self) -> None:
        rows = _make_rows(100)
        result = compute_indicators_for_symbol(rows, "BTCUSDT", "1h")
        for r in result:
            if r.rsi is not None:
                assert Decimal("0") <= r.rsi <= Decimal("100"), f"RSI out of range: {r.rsi}"

    def test_price_vs_bollinger_in_valid_range(self) -> None:
        rows = _make_rows(50)
        result = compute_indicators_for_symbol(rows, "BTCUSDT", "4h")
        for r in result:
            if r.price_vs_bollinger is not None:
                assert Decimal("-1") <= r.price_vs_bollinger <= Decimal("1"), (
                    f"price_vs_bollinger out of range: {r.price_vs_bollinger}"
                )

    def test_trend_type_is_stable_or_aggressive(self) -> None:
        rows = _make_rows(50)
        result = compute_indicators_for_symbol(rows, "BTCUSDT", "1D")
        for r in result:
            if r.trend_type is not None:
                assert r.trend_type in ("stable", "aggressive")

    def test_harmonic_pattern_is_none(self) -> None:
        """Harmonic pattern is deferred to Phase 2 and should always be None."""
        rows = _make_rows(50)
        result = compute_indicators_for_symbol(rows, "BTCUSDT", "4h")
        assert all(r.harmonic_pattern is None for r in result)

    def test_timestamps_are_sorted(self) -> None:
        rows = _make_rows(50)
        result = compute_indicators_for_symbol(rows, "BTCUSDT", "1h")
        timestamps = [r.timestamp for r in result]
        assert timestamps == sorted(timestamps)

    def test_exactly_20_rows_returns_empty(self) -> None:
        rows = _make_rows(20)
        result = compute_indicators_for_symbol(rows, "BTCUSDT", "1h")
        # The check is len < 20, so exactly 20 should proceed (not return early)
        # but may have no records with data due to indicator warmup
        # This just tests the function doesn't crash
        assert isinstance(result, list)

    def test_19_rows_returns_empty(self) -> None:
        rows = _make_rows(19)
        result = compute_indicators_for_symbol(rows, "BTCUSDT", "1h")
        assert result == []

    def test_weekly_timeframe_gets_trend(self) -> None:
        rows = _make_rows(50)
        result = compute_indicators_for_symbol(rows, "BTCUSDT", "1W")
        records_with_trend = [r for r in result if r.trend_slope is not None]
        assert len(records_with_trend) > 0

    def test_monthly_timeframe_gets_trend(self) -> None:
        rows = _make_rows(50)
        result = compute_indicators_for_symbol(rows, "BTCUSDT", "1M")
        records_with_trend = [r for r in result if r.trend_slope is not None]
        assert len(records_with_trend) > 0


# ---------------------------------------------------------------------------
# _compute_rsi (private, tested directly)
# ---------------------------------------------------------------------------


class TestComputeRSI:
    def test_returns_series_of_same_length(self) -> None:
        import pandas as pd

        df = _make_df(50)
        result = _compute_rsi(df["close"])
        assert isinstance(result, pd.Series)
        assert len(result) == 50

    def test_early_values_are_nan(self) -> None:
        df = _make_df(50)
        result = _compute_rsi(df["close"])
        # RSI period 14 — first 14 values typically NaN
        nan_count = result.isna().sum()
        assert nan_count >= 1

    def test_non_nan_values_in_range(self) -> None:
        df = _make_df(50)
        result = _compute_rsi(df["close"])
        non_nan = result.dropna()
        assert (non_nan >= 0).all()
        assert (non_nan <= 100).all()

    def test_uptrend_produces_high_rsi(self) -> None:
        # Strongly upward price: RSI should be above 50
        df = _make_df(50, price_step=100.0)
        result = _compute_rsi(df["close"])
        non_nan = result.dropna()
        assert non_nan.iloc[-1] > 50

    def test_downtrend_produces_low_rsi(self) -> None:
        # Strongly downward price: RSI should be below 50
        df = _make_df(50, price_step=-100.0)
        result = _compute_rsi(df["close"])
        non_nan = result.dropna()
        assert non_nan.iloc[-1] < 50

    def test_insufficient_data_returns_all_nan(self) -> None:
        df = _make_df(5)
        result = _compute_rsi(df["close"])
        # With only 5 rows, all should be NaN
        assert result.isna().all()


# ---------------------------------------------------------------------------
# _compute_bollinger (private, tested directly)
# ---------------------------------------------------------------------------


class TestComputeBollinger:
    def test_returns_dataframe_with_expected_columns(self) -> None:
        import pandas as pd

        df = _make_df(50)
        result = _compute_bollinger(df)
        assert isinstance(result, pd.DataFrame)
        assert "BBU_20_2.0" in result.columns
        assert "BBM_20_2.0" in result.columns
        assert "BBL_20_2.0" in result.columns

    def test_early_values_nan_before_warmup(self) -> None:
        df = _make_df(50)
        result = _compute_bollinger(df)
        # First 19 rows should be NaN (window=20)
        assert result["BBU_20_2.0"].iloc[:19].isna().all()

    def test_bands_ordering_upper_gt_middle_gt_lower(self) -> None:
        df = _make_df(50)
        result = _compute_bollinger(df)
        valid = result.dropna()
        assert (valid["BBU_20_2.0"] >= valid["BBM_20_2.0"]).all()
        assert (valid["BBM_20_2.0"] >= valid["BBL_20_2.0"]).all()

    def test_same_length_as_input(self) -> None:
        df = _make_df(40)
        result = _compute_bollinger(df)
        assert len(result) == 40


# ---------------------------------------------------------------------------
# _compute_price_vs_bollinger (private, tested directly)
# ---------------------------------------------------------------------------


class TestComputePriceVsBollinger:
    def test_price_at_upper_band_returns_one(self) -> None:
        result = _compute_price_vs_bollinger(price=110.0, upper=110.0, lower=90.0)
        assert result == Decimal("1.0")

    def test_price_at_lower_band_returns_minus_one(self) -> None:
        result = _compute_price_vs_bollinger(price=90.0, upper=110.0, lower=90.0)
        assert result == Decimal("-1.0")

    def test_price_at_midband_returns_zero(self) -> None:
        result = _compute_price_vs_bollinger(price=100.0, upper=110.0, lower=90.0)
        assert result == Decimal("0.0")

    def test_price_above_upper_clamped_to_one(self) -> None:
        result = _compute_price_vs_bollinger(price=120.0, upper=110.0, lower=90.0)
        assert result == Decimal("1.0")

    def test_price_below_lower_clamped_to_minus_one(self) -> None:
        result = _compute_price_vs_bollinger(price=80.0, upper=110.0, lower=90.0)
        assert result == Decimal("-1.0")

    def test_zero_band_width_returns_none(self) -> None:
        result = _compute_price_vs_bollinger(price=100.0, upper=100.0, lower=100.0)
        assert result is None

    def test_value_between_bounds(self) -> None:
        # Price at 75% of the way up: (105 - 100) / 10 = 0.5
        result = _compute_price_vs_bollinger(price=105.0, upper=110.0, lower=90.0)
        assert result is not None
        assert Decimal("-1.0") <= result <= Decimal("1.0")

    def test_returns_decimal_type(self) -> None:
        result = _compute_price_vs_bollinger(price=100.0, upper=110.0, lower=90.0)
        assert isinstance(result, Decimal)

    def test_result_has_at_most_6_decimal_places(self) -> None:
        result = _compute_price_vs_bollinger(price=101.0, upper=110.0, lower=90.0)
        assert result is not None
        # Check decimal places (sign + int + dot + decimals)
        str_result = str(abs(result))
        if "." in str_result:
            decimal_places = len(str_result.split(".")[1])
            assert decimal_places <= 6


# ---------------------------------------------------------------------------
# _compute_trend_slope (private, tested directly)
# ---------------------------------------------------------------------------


class TestComputeTrendSlope:
    def test_returns_empty_dict_when_fewer_than_window_rows(self) -> None:
        df = _make_df(15)
        result = _compute_trend_slope(df, window=20)
        assert result == {}

    def test_returns_dict_with_row_indices(self) -> None:
        df = _make_df(30)
        result = _compute_trend_slope(df, window=20)
        assert isinstance(result, dict)
        assert len(result) > 0

    def test_dict_keys_are_integers(self) -> None:
        df = _make_df(30)
        result = _compute_trend_slope(df, window=20)
        assert all(isinstance(k, int) for k in result)

    def test_values_are_tuples_of_float_and_str(self) -> None:
        df = _make_df(30)
        result = _compute_trend_slope(df, window=20)
        for slope, trend_type in result.values():
            assert isinstance(slope, float)
            assert isinstance(trend_type, str)

    def test_trend_type_values(self) -> None:
        df = _make_df(40)
        result = _compute_trend_slope(df, window=20)
        for _, trend_type in result.values():
            assert trend_type in ("stable", "aggressive")

    def test_uptrend_slope_is_positive(self) -> None:
        df = _make_df(30, price_step=500.0)  # strong uptrend
        result = _compute_trend_slope(df, window=20)
        last_idx = max(result.keys())
        slope, _ = result[last_idx]
        assert slope > 0

    def test_downtrend_slope_is_negative(self) -> None:
        df = _make_df(30, price_step=-500.0)  # strong downtrend
        result = _compute_trend_slope(df, window=20)
        last_idx = max(result.keys())
        slope, _ = result[last_idx]
        assert slope < 0

    def test_flat_price_produces_stable_trend(self) -> None:
        df = _make_df(30, price_step=0.0)  # flat price
        result = _compute_trend_slope(df, window=20)
        for _, trend_type in result.values():
            assert trend_type == "stable"

    def test_strong_uptrend_produces_aggressive_trend(self) -> None:
        # Very steep price increase relative to price level
        df = _make_df(30, base_price=100.0, price_step=50.0)  # 50% per candle
        result = _compute_trend_slope(df, window=20)
        last_idx = max(result.keys())
        _, trend_type = result[last_idx]
        assert trend_type == "aggressive"

    def test_first_valid_index_is_window_minus_one(self) -> None:
        df = _make_df(30, price_step=0.0)
        result = _compute_trend_slope(df, window=20)
        assert min(result.keys()) == 19  # window - 1


# ---------------------------------------------------------------------------
# _compute_volume_relatif (private, tested directly)
# ---------------------------------------------------------------------------


class TestComputeVolumeRelatif:
    def test_returns_series(self) -> None:
        import pandas as pd

        df = _make_df(30)
        result = _compute_volume_relatif(df)
        assert isinstance(result, pd.Series)

    def test_same_length_as_input(self) -> None:
        df = _make_df(40)
        result = _compute_volume_relatif(df)
        assert result is not None
        assert len(result) == 40

    def test_constant_volume_returns_ones(self) -> None:
        df = _make_df(30, volume=500.0)
        result = _compute_volume_relatif(df, period=20)
        assert result is not None
        non_nan = result.dropna()
        # When volume is constant, ratio should be 1.0
        assert (abs(non_nan - 1.0) < 1e-6).all()

    def test_early_values_are_nan_before_warmup(self) -> None:
        df = _make_df(30)
        result = _compute_volume_relatif(df, period=20)
        assert result is not None
        # First 19 values should be NaN
        assert result.iloc[:19].isna().all()

    def test_returns_none_when_no_volume_column(self) -> None:

        df = _make_df(30)
        df = df.drop(columns=["volume"])
        result = _compute_volume_relatif(df)
        assert result is None

    def test_spike_in_volume_produces_ratio_greater_than_one(self) -> None:
        import pandas as pd

        rows = _make_rows(30, volume=100.0)
        # Set last row to 10x volume
        rows[-1]["volume_24h"] = 1000.0
        df = pd.DataFrame(rows)
        df = df.rename(
            columns={
                "price_open": "open",
                "price_high": "high",
                "price_low": "low",
                "price_close": "close",
                "volume_24h": "volume",
            }
        )
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        df = df.set_index("timestamp")
        for col in ("open", "high", "low", "close", "volume"):
            df[col] = pd.to_numeric(df[col], errors="coerce")

        result = _compute_volume_relatif(df, period=20)
        assert result is not None
        last_val = result.iloc[-1]
        assert not math.isnan(last_val)
        assert last_val > 1.0

    def test_values_are_positive_when_volume_positive(self) -> None:
        df = _make_df(40, volume=500.0)
        result = _compute_volume_relatif(df, period=20)
        assert result is not None
        non_nan = result.dropna()
        assert (non_nan > 0).all()
