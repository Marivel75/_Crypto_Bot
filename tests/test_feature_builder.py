"""
Tests unitaires pour FeatureBuilder.
"""

import numpy as np
import pandas as pd
import pytest

from src.ml.feature_engineering.feature_builder import FeatureBuilder, _MIN_ROWS


# ---------------------------------------------------------------------------
# Fixture : DataFrame OHLCV minimal valide
# ---------------------------------------------------------------------------

@pytest.fixture
def ohlcv_df():
    """
    DataFrame OHLCV synthétique avec 100 bougies OHLCV cohérentes :
    high >= max(open, close) >= min(open, close) >= low.
    """
    n = 100
    rng = np.random.default_rng(42)
    close = 30_000 + np.cumsum(rng.normal(0, 200, n))
    open_ = close * (1 + rng.uniform(-0.01, 0.01, n))

    candle_high = np.maximum(open_, close)
    candle_low = np.minimum(open_, close)

    high = candle_high + rng.uniform(10, 200, n)
    low = candle_low - rng.uniform(10, 200, n)

    return pd.DataFrame(
        {
            "timestamp": pd.date_range("2024-01-01", periods=n, freq="1h"),
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": rng.uniform(100, 1000, n),
            "symbol": "BTC/USDT",
            "timeframe": "1h",
            "exchange": "binance",
        }
    )


@pytest.fixture
def builder():
    return FeatureBuilder()


# ---------------------------------------------------------------------------
# Tests de validation d'entrée
# ---------------------------------------------------------------------------

class TestFeatureBuilderValidation:
    def test_missing_column_raises(self, builder):
        df = pd.DataFrame({"timestamp": [], "open": [], "high": [], "low": [], "close": []})
        with pytest.raises(ValueError, match="volume"):
            builder.build(df)

    def test_too_few_rows_raises(self, builder):
        n = 10
        rng = np.random.default_rng(0)
        df = pd.DataFrame(
            {
                "timestamp": pd.date_range("2024-01-01", periods=n, freq="1h"),
                "open": rng.uniform(100, 200, n),
                "high": rng.uniform(200, 300, n),
                "low": rng.uniform(50, 100, n),
                "close": rng.uniform(100, 200, n),
                "volume": rng.uniform(1, 10, n),
            }
        )
        with pytest.raises(ValueError, match="insuffisantes"):
            builder.build(df)


# ---------------------------------------------------------------------------
# Tests de sortie globale
# ---------------------------------------------------------------------------

class TestFeatureBuilderOutput:
    def test_returns_dataframe(self, builder, ohlcv_df):
        result = builder.build(ohlcv_df)
        assert isinstance(result, pd.DataFrame)

    def test_row_count_preserved(self, builder, ohlcv_df):
        result = builder.build(ohlcv_df)
        assert len(result) == len(ohlcv_df)

    def test_no_column_lost(self, builder, ohlcv_df):
        result = builder.build(ohlcv_df)
        for col in ohlcv_df.columns:
            assert col in result.columns

    def test_more_columns_than_input(self, builder, ohlcv_df):
        result = builder.build(ohlcv_df)
        assert len(result.columns) > len(ohlcv_df.columns)

    def test_input_not_mutated(self, builder, ohlcv_df):
        original_cols = list(ohlcv_df.columns)
        builder.build(ohlcv_df)
        assert list(ohlcv_df.columns) == original_cols


# ---------------------------------------------------------------------------
# Tests par catégorie de features
# ---------------------------------------------------------------------------

class TestReturnFeatures:
    def test_log_return_1_exists(self, builder, ohlcv_df):
        result = builder.build(ohlcv_df)
        assert "log_return_1" in result.columns

    def test_return_4_exists(self, builder, ohlcv_df):
        result = builder.build(ohlcv_df)
        assert "return_4" in result.columns

    def test_return_24_exists(self, builder, ohlcv_df):
        result = builder.build(ohlcv_df)
        assert "return_24" in result.columns

    def test_log_return_1_correct_value(self, builder, ohlcv_df):
        result = builder.build(ohlcv_df)
        # log_return_1[i] = log(close[i] / close[i-1])
        close = ohlcv_df["close"].values
        expected = np.log(close[5] / close[4])
        assert result["log_return_1"].iloc[5] == pytest.approx(expected, rel=1e-6)

    def test_return_4_nan_first_rows(self, builder, ohlcv_df):
        result = builder.build(ohlcv_df)
        assert result["return_4"].iloc[:4].isna().all()


class TestVolatilityFeatures:
    def test_all_windows_present(self, builder, ohlcv_df):
        result = builder.build(ohlcv_df)
        for w in [5, 10, 20]:
            assert f"volatility_{w}" in result.columns

    def test_volatility_non_negative(self, builder, ohlcv_df):
        result = builder.build(ohlcv_df)
        for w in [5, 10, 20]:
            col = result[f"volatility_{w}"].dropna()
            assert (col >= 0).all()


class TestTechnicalFeatures:
    def test_rsi_present(self, builder, ohlcv_df):
        result = builder.build(ohlcv_df)
        assert "rsi_14" in result.columns

    def test_rsi_range(self, builder, ohlcv_df):
        result = builder.build(ohlcv_df)
        rsi = result["rsi_14"].dropna()
        assert (rsi >= 0).all() and (rsi <= 100).all()

    def test_macd_columns_present(self, builder, ohlcv_df):
        result = builder.build(ohlcv_df)
        for col in ["macd", "macd_signal", "macd_hist"]:
            assert col in result.columns

    def test_bb_columns_present(self, builder, ohlcv_df):
        result = builder.build(ohlcv_df)
        assert "bb_position" in result.columns
        assert "bb_width" in result.columns

    def test_sma_ratios_present(self, builder, ohlcv_df):
        result = builder.build(ohlcv_df)
        for w in [7, 20, 50]:
            assert f"sma_{w}_ratio" in result.columns

    def test_ema_ratios_present(self, builder, ohlcv_df):
        result = builder.build(ohlcv_df)
        for w in [9, 21]:
            assert f"ema_{w}_ratio" in result.columns

    def test_sma_ratio_near_one(self, builder, ohlcv_df):
        """Le ratio close/SMA doit rester dans un ordre de grandeur raisonnable."""
        result = builder.build(ohlcv_df)
        ratio = result["sma_7_ratio"].dropna()
        assert ((ratio > 0.5) & (ratio < 2.0)).all()


class TestCandleStructureFeatures:
    def test_all_candle_features_present(self, builder, ohlcv_df):
        result = builder.build(ohlcv_df)
        for col in ["hl_spread", "body_ratio", "upper_wick_ratio", "lower_wick_ratio"]:
            assert col in result.columns

    def test_body_ratio_between_0_and_1(self, builder, ohlcv_df):
        result = builder.build(ohlcv_df)
        ratio = result["body_ratio"].dropna()
        assert (ratio >= 0).all() and (ratio <= 1).all()

    def test_wick_ratios_non_negative(self, builder, ohlcv_df):
        result = builder.build(ohlcv_df)
        for col in ["upper_wick_ratio", "lower_wick_ratio"]:
            assert (result[col].dropna() >= 0).all()


class TestVolumeFeatures:
    def test_volume_features_present(self, builder, ohlcv_df):
        result = builder.build(ohlcv_df)
        assert "volume_ma_ratio" in result.columns
        assert "volume_change" in result.columns

    def test_volume_ma_ratio_positive(self, builder, ohlcv_df):
        result = builder.build(ohlcv_df)
        ratio = result["volume_ma_ratio"].dropna()
        assert (ratio > 0).all()


class TestTemporalFeatures:
    def test_all_temporal_features_present(self, builder, ohlcv_df):
        result = builder.build(ohlcv_df)
        for col in ["hour", "day_of_week", "day_of_month", "month", "is_weekend"]:
            assert col in result.columns

    def test_hour_range(self, builder, ohlcv_df):
        result = builder.build(ohlcv_df)
        assert result["hour"].between(0, 23).all()

    def test_day_of_week_range(self, builder, ohlcv_df):
        result = builder.build(ohlcv_df)
        assert result["day_of_week"].between(0, 6).all()

    def test_is_weekend_binary(self, builder, ohlcv_df):
        result = builder.build(ohlcv_df)
        assert set(result["is_weekend"].unique()).issubset({0, 1})
