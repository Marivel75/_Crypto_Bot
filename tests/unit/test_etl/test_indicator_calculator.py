"""Unit tests for indicator calculator — deterministic OHLCV data."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.etl.transformers.indicators import (
    compute_bollinger_bands,
    compute_price_vs_bollinger,
    compute_rsi,
    compute_trend,
)


@pytest.fixture
def ohlcv_df() -> pd.DataFrame:
    """Generate deterministic OHLCV data with an upward trend."""
    np.random.seed(42)
    n = 50
    base_price = 50000.0
    prices = base_price + np.cumsum(np.random.randn(n) * 100)

    return pd.DataFrame(
        {
            "price_open": prices - 50,
            "price_high": prices + 200,
            "price_low": prices - 200,
            "price_close": prices,
            "volume_24h": np.random.uniform(1000, 10000, n),
        }
    )


class TestComputeRSI:
    def test_rsi_range(self, ohlcv_df: pd.DataFrame) -> None:
        rsi = compute_rsi(ohlcv_df["price_close"], period=14)
        valid_rsi = rsi.dropna()
        assert len(valid_rsi) > 0
        assert all(0 <= v <= 100 for v in valid_rsi)

    def test_rsi_period_larger_than_data(self) -> None:
        small = pd.Series([100.0, 101.0, 99.0])
        rsi = compute_rsi(small, period=14)
        assert rsi.dropna().empty

    def test_rsi_all_gains(self) -> None:
        prices = pd.Series([float(i) for i in range(1, 30)])
        rsi = compute_rsi(prices, period=14)
        valid = rsi.dropna()
        assert all(v > 90 for v in valid)

    def test_rsi_all_losses(self) -> None:
        prices = pd.Series([float(30 - i) for i in range(30)])
        rsi = compute_rsi(prices, period=14)
        valid = rsi.dropna()
        assert all(v < 10 for v in valid)


class TestComputeBollingerBands:
    def test_bands_order(self, ohlcv_df: pd.DataFrame) -> None:
        upper, middle, lower = compute_bollinger_bands(ohlcv_df["price_close"], period=20, std_dev=2.0)
        valid_idx = upper.dropna().index
        for i in valid_idx:
            assert upper[i] >= middle[i] >= lower[i]

    def test_middle_is_sma(self, ohlcv_df: pd.DataFrame) -> None:
        _, middle, _ = compute_bollinger_bands(ohlcv_df["price_close"], period=20, std_dev=2.0)
        sma = ohlcv_df["price_close"].rolling(20).mean()
        valid = middle.dropna()
        np.testing.assert_array_almost_equal(valid.values, sma.dropna().values)


class TestComputePriceVsBollinger:
    def test_within_bands(self) -> None:
        result = compute_price_vs_bollinger(price=50.0, upper=60.0, lower=40.0)
        assert -1 <= result <= 1
        assert abs(result - 0.0) < 0.01

    def test_at_upper_band(self) -> None:
        result = compute_price_vs_bollinger(price=60.0, upper=60.0, lower=40.0)
        assert abs(result - 1.0) < 0.01

    def test_at_lower_band(self) -> None:
        result = compute_price_vs_bollinger(price=40.0, upper=60.0, lower=40.0)
        assert abs(result - (-1.0)) < 0.01

    def test_zero_bandwidth(self) -> None:
        result = compute_price_vs_bollinger(price=50.0, upper=50.0, lower=50.0)
        assert result == 0.0


class TestComputeTrend:
    def test_upward_trend(self) -> None:
        prices = pd.Series([float(i) for i in range(30)])
        slope, trend_type = compute_trend(prices, period=20)
        assert slope > 0
        assert trend_type in ("stable", "aggressive")

    def test_downward_trend(self) -> None:
        prices = pd.Series([float(30 - i) for i in range(30)])
        slope, trend_type = compute_trend(prices, period=20)
        assert slope < 0

    def test_flat_trend(self) -> None:
        prices = pd.Series([50.0] * 30)
        slope, trend_type = compute_trend(prices, period=20)
        assert abs(slope) < 0.01
        assert trend_type == "stable"
