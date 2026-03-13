"""Test data leakage prevention in walk-forward backtester.

Validates that:
1. Indicators are computed AFTER train/test temporal split.
2. Embargo windows prevent label leakage at boundaries.
3. Each fold is temporally isolated from others.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import pytest

from src.ml.models.backtester import Backtester

logger = logging.getLogger(__name__)


class _DummyStrategy:
    """Minimal strategy for testing backtester logic."""

    def fit(self, X: pd.DataFrame, y: pd.Series) -> None:
        """Store training data shape for inspection."""
        self.X_train_shape = X.shape
        self.y_train_shape = y.shape

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Return dummy predictions (all BUY)."""
        return np.ones(len(X), dtype=int)


def _create_test_data(days: int = 300) -> pd.DataFrame:
    """Create synthetic OHLCV + labels data with proper DatetimeIndex.

    Args:
        days: Number of days of data to generate.

    Returns:
        DataFrame with DatetimeIndex, feature columns, labels, and prices.
    """
    start_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
    dates = pd.date_range(start=start_date, periods=days, freq="D")

    # Create synthetic features and labels
    data = pd.DataFrame(
        {
            "feature_1": np.random.randn(days).cumsum(),
            "feature_2": np.random.randn(days).cumsum(),
            "feature_3": np.random.randn(days).cumsum(),
            "label": np.random.randint(0, 2, days),  # Binary labels
            "price_close": 100 + np.random.randn(days).cumsum(),
        },
        index=dates,
    )
    return data


class TestWalkForwardNoLeakage:
    """Verify temporal integrity and no data leakage in walk-forward backtester."""

    def test_backtester_respects_train_test_temporal_boundary(self) -> None:
        """Ensure test data comes strictly after train data (with embargo gap)."""
        data = _create_test_data(days=300)
        backtester = Backtester(train_window=90, test_window=30)
        strategy = _DummyStrategy()

        results = backtester.walk_forward(data, strategy)

        assert not results.empty, "walk_forward should produce at least one fold"

        # Check that train_end < test_start for every fold
        for _, row in results.iterrows():
            train_end: pd.Timestamp = row["train_end"]
            test_start: pd.Timestamp = row["test_start"]

            # test_start should be AFTER train_end (by at least PURGE_DAYS)
            gap_days = (test_start - train_end).days
            assert gap_days > 0, (
                f"Fold {int(row['fold'])}: test_start ({test_start}) must come after "
                f"train_end ({train_end}), gap={gap_days} days"
            )

    def test_backtester_enforces_embargo_window(self) -> None:
        """Verify embargo gap prevents label leakage between folds."""
        data = _create_test_data(days=300)
        backtester = Backtester(train_window=90, test_window=30)
        strategy = _DummyStrategy()

        results = backtester.walk_forward(data, strategy)
        assert not results.empty

        # Check that embargo gap exists between test_end of fold N and train_start of fold N+1
        for i in range(len(results) - 1):
            current_test_end: pd.Timestamp = results.iloc[i]["test_end"]
            next_train_start: pd.Timestamp = results.iloc[i + 1]["train_start"]

            embargo_gap = (next_train_start - current_test_end).days
            assert embargo_gap > 0, (
                f"Embargo gap between fold {i} and {i + 1} must be > 0, got {embargo_gap} days. "
                f"test_end={current_test_end}, next_train_start={next_train_start}"
            )

    def test_backtester_no_overlap_between_folds(self) -> None:
        """Verify no temporal overlap between any train and test windows across all folds."""
        data = _create_test_data(days=300)
        backtester = Backtester(train_window=90, test_window=30)
        strategy = _DummyStrategy()

        results = backtester.walk_forward(data, strategy)
        assert not results.empty

        for i, row_i in results.iterrows():
            train_start_i: pd.Timestamp = row_i["train_start"]
            train_end_i: pd.Timestamp = row_i["train_end"]
            test_start_i: pd.Timestamp = row_i["test_start"]
            test_end_i: pd.Timestamp = row_i["test_end"]

            for j, row_j in results.iterrows():
                if i == j:
                    continue

                train_start_j: pd.Timestamp = row_j["train_start"]
                train_end_j: pd.Timestamp = row_j["train_end"]
                test_start_j: pd.Timestamp = row_j["test_start"]
                test_end_j: pd.Timestamp = row_j["test_end"]

                # Check that test_i doesn't overlap with train_j
                overlaps_train = not (test_end_i <= train_start_j or test_start_i >= train_end_j)
                assert not overlaps_train, (
                    f"Fold {int(i)} test overlaps with fold {int(j)} train: "
                    f"test_i=[{test_start_i}, {test_end_i}], "
                    f"train_j=[{train_start_j}, {train_end_j}]"
                )

                # Check that train_i doesn't overlap with test_j
                overlaps_test = not (train_end_i <= test_start_j or train_start_i >= test_end_j)
                assert not overlaps_test, (
                    f"Fold {int(i)} train overlaps with fold {int(j)} test: "
                    f"train_i=[{train_start_i}, {train_end_i}], "
                    f"test_j=[{test_start_j}, {test_end_j}]"
                )

    def test_backtester_sufficient_data_per_fold(self) -> None:
        """Ensure each fold has n_train >= expected and n_test >= expected."""
        data = _create_test_data(days=300)
        train_window = 90
        test_window = 30
        backtester = Backtester(train_window=train_window, test_window=test_window)
        strategy = _DummyStrategy()

        results = backtester.walk_forward(data, strategy)
        assert not results.empty

        for _, row in results.iterrows():
            # Each fold should have train records corresponding to ~90 days
            # (exact count depends on data frequency; we allow ±10% tolerance)
            n_train = int(row["n_train"])
            n_test = int(row["n_test"])

            # For daily data, 90 days should give ~90 records (allow 10% slack)
            assert n_train >= train_window * 0.9, (
                f"Fold {int(row['fold'])}: n_train={n_train} is too low (expected ~{train_window})"
            )
            assert n_test >= test_window * 0.9, (
                f"Fold {int(row['fold'])}: n_test={n_test} is too low (expected ~{test_window})"
            )

    def test_backtester_metrics_consistency(self) -> None:
        """Verify backtest metrics are computed without NaN or infinite values."""
        data = _create_test_data(days=300)
        backtester = Backtester(train_window=90, test_window=30)
        strategy = _DummyStrategy()

        results = backtester.walk_forward(data, strategy)
        assert not results.empty

        # Check that metrics are finite
        for _, row in results.iterrows():
            accuracy = float(row["accuracy"])
            win_rate = float(row["win_rate"])
            pnl = float(row["pnl"])

            assert 0 <= accuracy <= 1, f"accuracy {accuracy} out of [0, 1]"
            assert 0 <= win_rate <= 1, f"win_rate {win_rate} out of [0, 1]"
            assert np.isfinite(pnl), f"pnl {pnl} is not finite"

    def test_walk_forward_raises_on_insufficient_data(self) -> None:
        """Verify walk_forward raises ValueError when dataset is too short."""
        # Create data for only 50 days; minimum is train(90) + purge(1) + test(30) + embargo(1)
        short_data = _create_test_data(days=50)
        backtester = Backtester(train_window=90, test_window=30)
        strategy = _DummyStrategy()

        with pytest.raises(ValueError, match="Dataset spans only .* days"):
            backtester.walk_forward(short_data, strategy)

    def test_walk_forward_raises_on_missing_columns(self) -> None:
        """Verify walk_forward raises ValueError if required columns are missing."""
        data = _create_test_data(days=300)
        # Drop the 'label' column
        data_missing_label = data.drop(columns=["label"])

        backtester = Backtester(train_window=90, test_window=30)
        strategy = _DummyStrategy()

        with pytest.raises(ValueError, match="missing required columns"):
            backtester.walk_forward(data_missing_label, strategy)

    def test_backtester_compute_metrics(self) -> None:
        """Test the metrics aggregation function."""
        fold_results = pd.DataFrame(
            {
                "fold": [0, 1, 2],
                "accuracy": [0.75, 0.80, 0.70],
                "win_rate": [0.60, 0.65, 0.55],
                "pnl": [0.05, 0.08, -0.02],
            }
        )
        backtester = Backtester()

        metrics = backtester.compute_metrics(fold_results)

        assert metrics["n_folds"] == 3
        assert 0.7 <= metrics["accuracy"] <= 0.8
        assert 0.55 <= metrics["win_rate"] <= 0.65
        assert isinstance(metrics["sharpe"], float)
        assert np.isfinite(metrics["total_pnl"])

    def test_backtester_compare_baseline(self) -> None:
        """Test comparison against buy-and-hold baseline."""
        fold_results = pd.DataFrame(
            {
                "fold": [0, 1],
                "accuracy": [0.70, 0.75],
                "win_rate": [0.60, 0.65],
                "pnl": [0.10, 0.15],
            }
        )

        prices = pd.DataFrame(
            {
                "price_close": [100, 102, 104, 106, 108],
            },
            index=pd.date_range("2025-01-01", periods=5, freq="D", tz=timezone.utc),
        )

        backtester = Backtester()
        comparison = backtester.compare_baseline(fold_results, prices)

        assert "strategy_total_pnl" in comparison
        assert "baseline_return" in comparison
        assert "excess_return" in comparison
        assert comparison["baseline_return"] > 0  # Prices went up
