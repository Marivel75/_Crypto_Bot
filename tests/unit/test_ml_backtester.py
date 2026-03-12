"""Unit tests for Backtester: temporal split, metrics, walk-forward."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.ml.models.backtester import EMBARGO_DAYS, PURGE_DAYS, Backtester

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class DummyStrategy:
    """Always predicts BUY (1)."""

    def fit(self, X: pd.DataFrame, y: pd.Series) -> None:
        pass

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        return np.ones(len(X), dtype=int)


class AlternatingStrategy:
    """Alternates 0/1 predictions."""

    def fit(self, X: pd.DataFrame, y: pd.Series) -> None:
        pass

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        return np.array([i % 2 for i in range(len(X))], dtype=int)


def _make_dataset(n_days: int = 250, start: str = "2023-01-01") -> pd.DataFrame:
    """Create a synthetic time-indexed feature+label DataFrame."""
    dates = pd.date_range(start, periods=n_days, freq="D")
    rng = np.random.default_rng(42)
    prices = 100.0 + np.cumsum(rng.normal(0, 1, n_days))
    labels = rng.integers(0, 2, n_days)
    return pd.DataFrame(
        {
            "feature_a": rng.standard_normal(n_days),
            "feature_b": rng.standard_normal(n_days),
            "label": labels,
            "price_close": prices,
        },
        index=dates,
    )


# ---------------------------------------------------------------------------
# Tests: initialisation
# ---------------------------------------------------------------------------


class TestInit:
    def test_raises_on_invalid_windows(self) -> None:
        with pytest.raises(ValueError):
            Backtester(train_window=0, test_window=30)

    def test_raises_on_negative_test_window(self) -> None:
        with pytest.raises(ValueError):
            Backtester(train_window=180, test_window=-1)

    def test_valid_init(self) -> None:
        bt = Backtester(train_window=90, test_window=15)
        assert bt.train_window == 90
        assert bt.test_window == 15


# ---------------------------------------------------------------------------
# Tests: temporal split never leaks
# ---------------------------------------------------------------------------


class TestTemporalIntegrity:
    def test_purge_gap_between_train_and_test(self) -> None:
        data = _make_dataset(300)
        bt = Backtester(train_window=180, test_window=30)
        results = bt.walk_forward(data, DummyStrategy())
        assert not results.empty

        for _, row in results.iterrows():
            gap = (row["test_start"] - row["train_end"]).days
            assert gap >= PURGE_DAYS, f"Purge gap violated: {gap} < {PURGE_DAYS}"

    def test_embargo_gap_between_folds(self) -> None:
        data = _make_dataset(400)
        bt = Backtester(train_window=120, test_window=30)
        results = bt.walk_forward(data, DummyStrategy())

        if len(results) >= 2:
            for i in range(len(results) - 1):
                current_test_end = results.iloc[i]["test_end"]
                next_train_start = results.iloc[i + 1]["train_start"]
                gap = (next_train_start - current_test_end).days
                assert gap >= EMBARGO_DAYS

    def test_train_end_before_test_start(self) -> None:
        data = _make_dataset(300)
        bt = Backtester(train_window=180, test_window=30)
        results = bt.walk_forward(data, DummyStrategy())

        for _, row in results.iterrows():
            assert row["train_end"] < row["test_start"]

    def test_dataset_too_short_raises(self) -> None:
        data = _make_dataset(50)
        bt = Backtester(train_window=180, test_window=30)
        with pytest.raises(ValueError, match="need at least"):
            bt.walk_forward(data, DummyStrategy())


# ---------------------------------------------------------------------------
# Tests: compute_metrics math
# ---------------------------------------------------------------------------


class TestComputeMetrics:
    def test_empty_results_returns_zeros(self) -> None:
        bt = Backtester()
        metrics = bt.compute_metrics(pd.DataFrame())
        assert metrics["accuracy"] == 0.0
        assert metrics["sharpe"] == 0.0
        assert metrics["n_folds"] == 0

    def test_all_positive_pnl_gives_infinite_profit_factor(self) -> None:
        bt = Backtester()
        results = pd.DataFrame(
            {
                "accuracy": [0.7, 0.8],
                "win_rate": [0.6, 0.7],
                "pnl": [0.05, 0.03],
            }
        )
        metrics = bt.compute_metrics(results)
        assert metrics["profit_factor"] == float("inf")
        assert metrics["total_pnl"] == pytest.approx(0.08)

    def test_mixed_pnl_computes_profit_factor(self) -> None:
        bt = Backtester()
        results = pd.DataFrame(
            {
                "accuracy": [0.6, 0.5],
                "win_rate": [0.5, 0.4],
                "pnl": [0.10, -0.04],
            }
        )
        metrics = bt.compute_metrics(results)
        assert metrics["profit_factor"] == pytest.approx(0.10 / 0.04)
        assert metrics["total_pnl"] == pytest.approx(0.06)

    def test_sharpe_is_mean_over_std(self) -> None:
        bt = Backtester()
        pnl_values = [0.05, 0.03, -0.02, 0.04]
        results = pd.DataFrame(
            {
                "accuracy": [0.5] * 4,
                "win_rate": [0.5] * 4,
                "pnl": pnl_values,
            }
        )
        metrics = bt.compute_metrics(results)
        s = pd.Series(pnl_values)
        expected_sharpe = float(s.mean()) / float(s.std())
        assert metrics["sharpe"] == pytest.approx(expected_sharpe, rel=1e-4)


# ---------------------------------------------------------------------------
# Tests: compare_baseline
# ---------------------------------------------------------------------------


class TestCompareBaseline:
    def test_baseline_return_matches_buy_hold(self) -> None:
        bt = Backtester()
        prices = pd.DataFrame(
            {"price_close": [100.0, 110.0, 120.0]},
            index=pd.date_range("2023-01-01", periods=3, freq="D"),
        )
        results = pd.DataFrame(
            {
                "accuracy": [0.7],
                "win_rate": [0.6],
                "pnl": [0.15],
            }
        )
        comparison = bt.compare_baseline(results, prices)
        assert comparison["baseline_return"] == pytest.approx(0.2)
        assert comparison["excess_return"] == pytest.approx(0.15 - 0.2)

    def test_empty_inputs_return_zeros(self) -> None:
        bt = Backtester()
        comparison = bt.compare_baseline(pd.DataFrame(), pd.DataFrame())
        assert comparison["strategy_total_pnl"] == 0.0
        assert comparison["baseline_return"] == 0.0


# ---------------------------------------------------------------------------
# Tests: walk-forward produces reasonable output
# ---------------------------------------------------------------------------


class TestWalkForward:
    def test_walk_forward_produces_folds(self) -> None:
        data = _make_dataset(300)
        bt = Backtester(train_window=180, test_window=30)
        results = bt.walk_forward(data, DummyStrategy())
        assert len(results) >= 1
        assert "fold" in results.columns
        assert "accuracy" in results.columns

    def test_missing_columns_raises(self) -> None:
        data = pd.DataFrame(
            {"feature": [1, 2, 3]},
            index=pd.date_range("2023-01-01", periods=3, freq="D"),
        )
        bt = Backtester(train_window=1, test_window=1)
        with pytest.raises(ValueError, match="missing required columns"):
            bt.walk_forward(data, DummyStrategy())
