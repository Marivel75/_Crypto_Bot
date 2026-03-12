"""Tests for market analytics: correlation, volatility, and regime detection."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import numpy as np
import pandas as pd
import pytest

from src.ml.analytics import (
    compute_correlation_matrix,
    compute_volatility,
    detect_market_regime,
)


class TestComputeCorrelationMatrix:
    """Test cross-symbol correlation matrix computation."""

    def test_two_symbol_perfect_positive_correlation(self) -> None:
        """Two identical price series should have correlation = 1.0."""
        prices = [100, 101, 102, 103, 104, 105]
        index = pd.date_range("2025-01-01", periods=len(prices), freq="h")
        df = pd.DataFrame({"BTCUSDT": prices, "ETHUSDT": prices}, index=index)

        result = compute_correlation_matrix(df)

        assert len(result.symbols) == 2
        assert "BTCUSDT,ETHUSDT" in result.correlations
        assert result.correlations["BTCUSDT,ETHUSDT"] == pytest.approx(1.0, abs=0.01)

    def test_inverse_price_series_negative_correlation(self) -> None:
        """Inverse price series should have correlation ≈ -1.0."""
        btc_prices = [100, 101, 102, 103, 104, 105]
        eth_prices = [105, 104, 103, 102, 101, 100]
        index = pd.date_range("2025-01-01", periods=len(btc_prices), freq="h")
        df = pd.DataFrame({"BTCUSDT": btc_prices, "ETHUSDT": eth_prices}, index=index)

        result = compute_correlation_matrix(df)

        assert result.correlations["BTCUSDT,ETHUSDT"] == pytest.approx(-1.0, abs=0.01)

    def test_three_symbols_all_pairs_computed(self) -> None:
        """Three symbols should produce 3 pairs: (0,1), (0,2), (1,2)."""
        index = pd.date_range("2025-01-01", periods=10, freq="h")
        df = pd.DataFrame(
            {
                "BTCUSDT": np.random.randn(10).cumsum(),
                "ETHUSDT": np.random.randn(10).cumsum(),
                "BNBUSDT": np.random.randn(10).cumsum(),
            },
            index=index,
        )

        result = compute_correlation_matrix(df)

        assert len(result.symbols) == 3
        assert len(result.correlations) == 3

    def test_empty_dataframe_raises_error(self) -> None:
        """Empty DataFrame should raise ValueError."""
        df = pd.DataFrame()

        with pytest.raises(ValueError, match="non-empty"):
            compute_correlation_matrix(df)

    def test_single_column_dataframe_raises_error(self) -> None:
        """Single-column DataFrame should raise ValueError."""
        df = pd.DataFrame({"BTCUSDT": [100, 101, 102]})

        with pytest.raises(ValueError, match="≥2 columns"):
            compute_correlation_matrix(df)

    def test_min_periods_parameter_filters_short_pairs(self) -> None:
        """min_periods should filter out pairs with fewer observations."""
        index = pd.date_range("2025-01-01", periods=5, freq="h")
        # First 5 rows have data for BTC, all 5 for ETH
        df = pd.DataFrame(
            {
                "BTCUSDT": [100, 101, 102, 103, 104],
                "ETHUSDT": [50, 51, 52, 53, 54],
            },
            index=index,
        )

        result = compute_correlation_matrix(df, min_periods=10)

        # Should have NaN for the pair (fewer than 10 observations)
        corr = result.correlations.get("BTCUSDT,ETHUSDT")
        assert corr is None or np.isnan(corr)


class TestComputeVolatility:
    """Test historical volatility computation."""

    def test_constant_price_series_zero_volatility(self) -> None:
        """Constant price series should have zero volatility."""
        prices = [100.0] * 30
        index = pd.date_range("2025-01-01", periods=len(prices), freq="h")
        series = pd.Series(prices, index=index, name="BTCUSDT")

        result = compute_volatility(series, window=14, periods_per_year=252)

        assert result.volatility == pytest.approx(0.0, abs=1e-6)

    def test_volatile_price_series_high_volatility(self) -> None:
        """Random walk should have non-zero volatility."""
        np.random.seed(42)
        prices = 100 + np.random.randn(100).cumsum()
        index = pd.date_range("2025-01-01", periods=len(prices), freq="h")
        series = pd.Series(prices, index=index, name="BTCUSDT")

        result = compute_volatility(series, window=14, periods_per_year=252)

        assert result.volatility > 0.0

    def test_insufficient_data_raises_error(self) -> None:
        """Series with fewer than window+1 observations should raise error."""
        prices = [100, 101, 102]
        index = pd.date_range("2025-01-01", periods=len(prices), freq="h")
        series = pd.Series(prices, index=index, name="BTCUSDT")

        with pytest.raises(ValueError, match="observations"):
            compute_volatility(series, window=20, periods_per_year=252)

    def test_dataframe_input_single_column(self) -> None:
        """Single-column DataFrame should work."""
        prices = [100, 101, 102, 103, 104, 105, 106, 107, 108, 109]
        index = pd.date_range("2025-01-01", periods=len(prices), freq="h")
        df = pd.DataFrame({"BTCUSDT": prices}, index=index)

        result = compute_volatility(df, window=5, periods_per_year=252)

        assert result.symbol == "BTCUSDT"
        assert result.volatility >= 0.0

    def test_dataframe_input_multiple_columns_raises_error(self) -> None:
        """Multi-column DataFrame should raise error."""
        index = pd.date_range("2025-01-01", periods=10, freq="h")
        df = pd.DataFrame(
            {"BTCUSDT": [100] * 10, "ETHUSDT": [50] * 10},
            index=index,
        )

        with pytest.raises(ValueError, match="single-column"):
            compute_volatility(df, window=5)

    def test_periods_per_year_affects_annualisation(self) -> None:
        """Different periods_per_year should scale volatility."""
        prices = 100 + np.random.randn(100).cumsum()
        index = pd.date_range("2025-01-01", periods=len(prices), freq="h")
        series = pd.Series(prices, index=index, name="BTCUSDT")

        result_252 = compute_volatility(series, window=14, periods_per_year=252)
        result_365 = compute_volatility(series, window=14, periods_per_year=365)

        # Higher annualisation factor should give higher volatility
        assert result_365.volatility > result_252.volatility


class TestDetectMarketRegime:
    """Test market regime classification."""

    def test_strong_uptrend_detected(self) -> None:
        """Strong uptrend should be classified as 'trending'."""
        # Monotonic uptrend
        prices = list(range(100, 200))
        index = pd.date_range("2025-01-01", periods=len(prices), freq="h")
        series = pd.Series(prices, index=index, name="BTCUSDT")

        result = detect_market_regime(series, short_window=14, long_window=50, volatility_threshold=0.02)

        assert result.regime == "trending"
        assert result.confidence > 0.5

    def test_strong_downtrend_detected(self) -> None:
        """Strong downtrend should be classified as 'trending'."""
        # Monotonic downtrend
        prices = list(range(200, 100, -1))
        index = pd.date_range("2025-01-01", periods=len(prices), freq="h")
        series = pd.Series(prices, index=index, name="BTCUSDT")

        result = detect_market_regime(series, short_window=14, long_window=50, volatility_threshold=0.02)

        assert result.regime == "trending"
        assert result.confidence > 0.5

    def test_oscillating_prices_detected_as_ranging(self) -> None:
        """Oscillating prices should be detected as 'ranging'."""
        # Oscillation around 150
        prices = [150 + 5 * np.sin(i * 0.5) for i in range(100)]
        index = pd.date_range("2025-01-01", periods=len(prices), freq="h")
        series = pd.Series(prices, index=index, name="BTCUSDT")

        result = detect_market_regime(series, short_window=14, long_window=50, volatility_threshold=0.05)

        assert result.regime in ("ranging", "volatile")

    def test_high_volatility_detected_as_volatile(self) -> None:
        """High volatility spikes should be detected as 'volatile'."""
        np.random.seed(42)
        prices = 150 + np.random.randn(100) * 20  # High volatility
        index = pd.date_range("2025-01-01", periods=len(prices), freq="h")
        series = pd.Series(prices, index=index, name="BTCUSDT")

        result = detect_market_regime(
            series, short_window=14, long_window=50, volatility_threshold=0.01
        )

        # With very high volatility and low threshold, should detect volatile
        assert result.regime == "volatile"

    def test_insufficient_data_raises_error(self) -> None:
        """Series with fewer than long_window+1 observations should raise error."""
        prices = list(range(10))
        index = pd.date_range("2025-01-01", periods=len(prices), freq="h")
        series = pd.Series(prices, index=index, name="BTCUSDT")

        with pytest.raises(ValueError, match="observations"):
            detect_market_regime(series, short_window=5, long_window=50)

    def test_dataframe_input_single_column(self) -> None:
        """Single-column DataFrame should work."""
        prices = list(range(100, 200))
        index = pd.date_range("2025-01-01", periods=len(prices), freq="h")
        df = pd.DataFrame({"BTCUSDT": prices}, index=index)

        result = detect_market_regime(df, short_window=14, long_window=50, volatility_threshold=0.02)

        assert result.regime in ("trending", "ranging", "volatile")

    def test_dataframe_input_multiple_columns_raises_error(self) -> None:
        """Multi-column DataFrame should raise error."""
        index = pd.date_range("2025-01-01", periods=100, freq="h")
        df = pd.DataFrame(
            {"BTCUSDT": list(range(100, 200)), "ETHUSDT": list(range(50, 150))},
            index=index,
        )

        with pytest.raises(ValueError, match="single-column"):
            detect_market_regime(df, short_window=14, long_window=50)

    def test_confidence_in_valid_range(self) -> None:
        """Confidence should always be in [0, 1]."""
        prices = 150 + np.random.randn(100)
        index = pd.date_range("2025-01-01", periods=len(prices), freq="h")
        series = pd.Series(prices, index=index, name="BTCUSDT")

        result = detect_market_regime(series)

        assert 0 <= result.confidence <= 1
        assert result.regime in ("trending", "ranging", "volatile")
        assert len(result.detail) > 0
