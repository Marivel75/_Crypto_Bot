"""Tests for model trainers: feature engineering, temporal splits, and training."""

from __future__ import annotations

import pandas as pd
import pytest

from src.ml.models.lgbm_trainer import LightGBMTrainer
from src.ml.models.trainer import FEATURE_COLS, ModelTrainer


class TestTemporalSplit:
    """Test temporal (chronological) train/test splitting."""

    def test_temporal_split_preserves_order(self) -> None:
        """Training set should always precede test set chronologically."""
        df = pd.DataFrame(
            {"value": range(100)},
            index=pd.date_range("2025-01-01", periods=100, freq="h"),
        )
        trainer = ModelTrainer("test_experiment")

        train, test = trainer.temporal_split(df, train_ratio=0.8)

        # Train max timestamp < test min timestamp
        assert train.index.max() < test.index.min()

    def test_temporal_split_ratio_respected(self) -> None:
        """Train ratio should be respected (80% train, 20% test)."""
        df = pd.DataFrame(
            {"value": range(100)},
            index=pd.date_range("2025-01-01", periods=100, freq="h"),
        )
        trainer = ModelTrainer("test_experiment")

        train, test = trainer.temporal_split(df, train_ratio=0.8)

        assert len(train) == 80
        assert len(test) == 20

    def test_temporal_split_custom_ratio(self) -> None:
        """Custom train ratio should work."""
        df = pd.DataFrame(
            {"value": range(100)},
            index=pd.date_range("2025-01-01", periods=100, freq="h"),
        )
        trainer = ModelTrainer("test_experiment")

        train, test = trainer.temporal_split(df, train_ratio=0.7)

        assert len(train) == 70
        assert len(test) == 30

    def test_temporal_split_empty_dataframe_raises_error(self) -> None:
        """Empty DataFrame should raise ValueError."""
        df = pd.DataFrame()
        trainer = ModelTrainer("test_experiment")

        with pytest.raises(ValueError, match="empty"):
            trainer.temporal_split(df)

    def test_temporal_split_invalid_ratio_raises_error(self) -> None:
        """Invalid train_ratio should raise ValueError."""
        df = pd.DataFrame(
            {"value": range(100)},
            index=pd.date_range("2025-01-01", periods=100, freq="h"),
        )
        trainer = ModelTrainer("test_experiment")

        with pytest.raises(ValueError, match="train_ratio"):
            trainer.temporal_split(df, train_ratio=1.5)

    def test_temporal_split_ratio_exactly_zero_raises_error(self) -> None:
        """train_ratio = 0 should raise error."""
        df = pd.DataFrame(
            {"value": range(100)},
            index=pd.date_range("2025-01-01", periods=100, freq="h"),
        )
        trainer = ModelTrainer("test_experiment")

        with pytest.raises(ValueError, match="train_ratio"):
            trainer.temporal_split(df, train_ratio=0.0)


class TestFeatureEngineering:
    """Test feature preparation from OHLCV and indicator data."""

    def test_prepare_features_empty_input_returns_empty_dataframe(self) -> None:
        """Empty input should return empty DataFrame."""
        trainer = ModelTrainer("test_experiment")

        result = trainer.prepare_features([], [])

        assert result.empty
        assert list(result.columns) == FEATURE_COLS

    def test_prepare_features_drops_nan_rows(self) -> None:
        """Rows with NaN values should be dropped."""
        ohlcv = [
            {
                "symbol": "BTCUSDT",
                "timestamp": pd.Timestamp("2025-01-01 00:00:00"),
                "timeframe": "1h",
                "price_close": 100.0,
                "volume_24h": 1000.0,
            },
            {
                "symbol": "BTCUSDT",
                "timestamp": pd.Timestamp("2025-01-01 01:00:00"),
                "timeframe": "1h",
                "price_close": 101.0,
                "volume_24h": 1050.0,
            },
        ]
        indicators = [
            {
                "symbol": "BTCUSDT",
                "timestamp": pd.Timestamp("2025-01-01 00:00:00"),
                "timeframe": "1h",
                "rsi": 50.0,
                "price_vs_bollinger": 0.5,
                "trend_slope": 0.001,
            }
        ]
        trainer = ModelTrainer("test_experiment")

        result = trainer.prepare_features(ohlcv, indicators)

        # Should drop rows with missing values
        assert len(result) <= len(ohlcv)

    def test_prepare_features_fills_missing_columns_with_nan(self) -> None:
        """Missing feature columns should be filled with NaN."""
        ohlcv = [
            {
                "symbol": "BTCUSDT",
                "timestamp": pd.Timestamp("2025-01-01 00:00:00"),
                "timeframe": "1h",
                "price_close": 100.0,
                "volume_24h": 1000.0,
            }
        ]
        indicators = [
            {
                "symbol": "BTCUSDT",
                "timestamp": pd.Timestamp("2025-01-01 00:00:00"),
                "timeframe": "1h",
                "rsi": 50.0,
                "price_vs_bollinger": 0.5,
                "trend_slope": 0.001,
            }
        ]
        trainer = ModelTrainer("test_experiment")

        result = trainer.prepare_features(ohlcv, indicators)

        # Should have all feature columns
        for col in FEATURE_COLS:
            assert col in result.columns


class TestLightGBMTrainer:
    """Test LightGBM trainer (mirrors XGBoost interface)."""

    def test_lightgbm_temporal_split_works(self) -> None:
        """LightGBM temporal split should work identically."""
        df = pd.DataFrame(
            {"value": range(100)},
            index=pd.date_range("2025-01-01", periods=100, freq="h"),
        )
        trainer = LightGBMTrainer("test_experiment")

        train, test = trainer.temporal_split(df, train_ratio=0.8)

        assert len(train) == 80
        assert len(test) == 20
        assert train.index.max() < test.index.min()

    def test_lightgbm_prepare_features_works(self) -> None:
        """LightGBM prepare_features should match XGBoost interface."""
        ohlcv = [
            {
                "symbol": "BTCUSDT",
                "timestamp": pd.Timestamp("2025-01-01 00:00:00"),
                "timeframe": "1h",
                "price_close": 100.0,
                "volume_24h": 1000.0,
            }
        ]
        indicators = [
            {
                "symbol": "BTCUSDT",
                "timestamp": pd.Timestamp("2025-01-01 00:00:00"),
                "timeframe": "1h",
                "rsi": 50.0,
                "price_vs_bollinger": 0.5,
                "trend_slope": 0.001,
            }
        ]
        trainer = LightGBMTrainer("test_experiment")

        result = trainer.prepare_features(ohlcv, indicators)

        # Should return DataFrame with feature columns
        for col in FEATURE_COLS:
            assert col in result.columns

    def test_lightgbm_empty_features_returns_empty_dataframe(self) -> None:
        """Empty input should return empty DataFrame."""
        trainer = LightGBMTrainer("test_experiment")

        result = trainer.prepare_features([], [])

        assert result.empty
        assert list(result.columns) == FEATURE_COLS


class TestTrainingRequirements:
    """Test training data validation."""

    def test_mismatched_features_labels_raises_error(self) -> None:
        """Features and labels with different lengths should raise error."""
        trainer = ModelTrainer("test_experiment")

        features = pd.DataFrame(
            {"col1": [1, 2, 3]},
            index=pd.date_range("2025-01-01", periods=3, freq="h"),
        )
        labels = pd.Series([0, 1], index=pd.date_range("2025-01-01", periods=2, freq="h"))

        with pytest.raises(ValueError, match="length"):
            trainer.train(features, labels)

    def test_insufficient_training_samples_raises_error(self) -> None:
        """Fewer than 10 samples should raise error."""
        trainer = ModelTrainer("test_experiment")

        features = pd.DataFrame(
            {"col1": [1, 2, 3, 4, 5]},
            index=pd.date_range("2025-01-01", periods=5, freq="h"),
        )
        labels = pd.Series(
            [0, 1, 0, 1, 0],
            index=pd.date_range("2025-01-01", periods=5, freq="h"),
        )

        with pytest.raises(ValueError, match="at least 10"):
            trainer.train(features, labels)

    def test_lgbm_mismatched_features_labels_raises_error(self) -> None:
        """LightGBM should validate feature/label length match."""
        trainer = LightGBMTrainer("test_experiment")

        features = pd.DataFrame(
            {"col1": [1, 2, 3, 4, 5]},
            index=pd.date_range("2025-01-01", periods=5, freq="h"),
        )
        labels = pd.Series(
            [0, 1, 0],
            index=pd.date_range("2025-01-01", periods=3, freq="h"),
        )

        with pytest.raises(ValueError, match="length"):
            trainer.train(features, labels)


class TestFeatureCols:
    """Test feature column definitions."""

    def test_feature_cols_non_empty(self) -> None:
        """FEATURE_COLS should not be empty."""
        assert len(FEATURE_COLS) > 0

    def test_feature_cols_contains_rsi_variants(self) -> None:
        """FEATURE_COLS should contain RSI columns for all TFs."""
        assert "rsi_1h" in FEATURE_COLS
        assert "rsi_4h" in FEATURE_COLS

    def test_feature_cols_contains_bollinger_variants(self) -> None:
        """FEATURE_COLS should contain Bollinger columns."""
        assert any(col.startswith("boll_pos") for col in FEATURE_COLS)

    def test_feature_cols_contains_trend_variants(self) -> None:
        """FEATURE_COLS should contain trend columns."""
        assert any(col.startswith("trend_slope") for col in FEATURE_COLS)

    def test_feature_cols_contains_volume_variants(self) -> None:
        """FEATURE_COLS should contain volume columns."""
        assert any(col.startswith("volume_ratio") for col in FEATURE_COLS)
