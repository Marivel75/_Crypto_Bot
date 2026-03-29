"""
Tests unitaires pour DatasetBuilder.
"""

import numpy as np
import pandas as pd
import pytest

from src.ml.feature_engineering.dataset_builder import DatasetBuilder
from src.ml.feature_engineering.feature_builder import FeatureBuilder


# ---------------------------------------------------------------------------
# Fixture : dataset enrichi par FeatureBuilder
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def features_df():
    """DataFrame OHLCV synthétique passé dans FeatureBuilder (100 bougies)."""
    n = 150
    rng = np.random.default_rng(7)
    close = 30_000 + np.cumsum(rng.normal(0, 200, n))
    high = close + rng.uniform(50, 300, n)
    low = close - rng.uniform(50, 300, n)
    open_ = close + rng.normal(0, 100, n)

    df = pd.DataFrame(
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
    return FeatureBuilder().build(df)


# ---------------------------------------------------------------------------
# Tests de validation des arguments
# ---------------------------------------------------------------------------

class TestDatasetBuilderInit:
    def test_invalid_mode_raises(self):
        with pytest.raises(ValueError, match="mode"):
            DatasetBuilder(mode="invalid")

    def test_invalid_horizon_raises(self):
        with pytest.raises(ValueError, match="horizon"):
            DatasetBuilder(horizon=0)

    def test_valid_modes(self):
        DatasetBuilder(mode="direction")
        DatasetBuilder(mode="return")


# ---------------------------------------------------------------------------
# Tests de build() — mode direction
# ---------------------------------------------------------------------------

class TestBuildDirection:
    def test_returns_tuple(self, features_df):
        X, y = DatasetBuilder(horizon=1, mode="direction").build(features_df)
        assert isinstance(X, pd.DataFrame)
        assert isinstance(y, pd.Series)

    def test_no_nan_in_X(self, features_df):
        X, _ = DatasetBuilder(horizon=1, mode="direction").build(features_df)
        assert not X.isna().any().any()

    def test_no_nan_in_y(self, features_df):
        _, y = DatasetBuilder(horizon=1, mode="direction").build(features_df)
        assert not y.isna().any()

    def test_y_is_binary(self, features_df):
        _, y = DatasetBuilder(horizon=1, mode="direction").build(features_df)
        assert set(y.unique()).issubset({0.0, 1.0})

    def test_X_y_same_length(self, features_df):
        X, y = DatasetBuilder(horizon=1, mode="direction").build(features_df)
        assert len(X) == len(y)

    def test_meta_columns_excluded(self, features_df):
        X, _ = DatasetBuilder(horizon=1, mode="direction").build(features_df)
        for col in ["timestamp", "symbol", "exchange", "open", "high", "low", "close", "volume"]:
            assert col not in X.columns

    def test_fewer_rows_than_input(self, features_df):
        """NaN du warm-up + horizon supprimés."""
        X, _ = DatasetBuilder(horizon=1, mode="direction").build(features_df)
        assert len(X) < len(features_df)

    def test_larger_horizon_fewer_rows(self, features_df):
        X1, _ = DatasetBuilder(horizon=1).build(features_df)
        X4, _ = DatasetBuilder(horizon=4).build(features_df)
        assert len(X4) <= len(X1)


# ---------------------------------------------------------------------------
# Tests de build() — mode return
# ---------------------------------------------------------------------------

class TestBuildReturn:
    def test_y_is_float(self, features_df):
        _, y = DatasetBuilder(horizon=1, mode="return").build(features_df)
        assert y.dtype == float

    def test_y_return_value_correct(self, features_df):
        """Le return doit être (close_t+1 - close_t) / close_t."""
        X, y = DatasetBuilder(horizon=1, mode="return").build(features_df)
        # Vérification que les valeurs sont dans un ordre de grandeur réaliste (< 50%)
        assert (y.abs() < 0.5).all()


# ---------------------------------------------------------------------------
# Tests de time_series_split()
# ---------------------------------------------------------------------------

class TestTimeSeriesSplit:
    @pytest.fixture
    def X_y(self, features_df):
        return DatasetBuilder(horizon=1).build(features_df)

    def test_correct_number_of_splits(self, X_y):
        X, y = X_y
        splits = DatasetBuilder().time_series_split(X, y, n_splits=3)
        assert len(splits) == 3

    def test_split_tuple_structure(self, X_y):
        X, y = X_y
        splits = DatasetBuilder().time_series_split(X, y, n_splits=3)
        X_tr, X_val, y_tr, y_val = splits[0]
        assert isinstance(X_tr, pd.DataFrame)
        assert isinstance(X_val, pd.DataFrame)

    def test_train_before_val(self, X_y):
        """L'indice max du train doit être inférieur à l'indice min du val."""
        X, y = X_y
        splits = DatasetBuilder().time_series_split(X, y, n_splits=3)
        for X_tr, X_val, _, _ in splits:
            assert X_tr.index.max() < X_val.index.min()

    def test_no_overlap_between_train_and_val(self, X_y):
        X, y = X_y
        splits = DatasetBuilder().time_series_split(X, y, n_splits=3)
        for X_tr, X_val, _, _ in splits:
            assert len(set(X_tr.index) & set(X_val.index)) == 0


# ---------------------------------------------------------------------------
# Tests de train_test_split_temporal()
# ---------------------------------------------------------------------------

class TestTrainTestSplitTemporal:
    @pytest.fixture
    def X_y(self, features_df):
        return DatasetBuilder(horizon=1).build(features_df)

    def test_ratio_respected(self, X_y):
        X, y = X_y
        X_tr, X_te, _, _ = DatasetBuilder().train_test_split_temporal(X, y, test_ratio=0.2)
        assert len(X_te) == pytest.approx(len(X) * 0.2, abs=1)

    def test_no_overlap(self, X_y):
        X, y = X_y
        X_tr, X_te, _, _ = DatasetBuilder().train_test_split_temporal(X, y, test_ratio=0.2)
        assert len(set(X_tr.index) & set(X_te.index)) == 0

    def test_train_before_test(self, X_y):
        X, y = X_y
        X_tr, X_te, _, _ = DatasetBuilder().train_test_split_temporal(X, y, test_ratio=0.2)
        assert X_tr.index.max() < X_te.index.min()

    def test_total_rows_preserved(self, X_y):
        X, y = X_y
        X_tr, X_te, y_tr, y_te = DatasetBuilder().train_test_split_temporal(X, y)
        assert len(X_tr) + len(X_te) == len(X)
        assert len(y_tr) + len(y_te) == len(y)

    def test_invalid_ratio_raises(self, X_y):
        X, y = X_y
        with pytest.raises(ValueError, match="test_ratio"):
            DatasetBuilder().train_test_split_temporal(X, y, test_ratio=1.5)
