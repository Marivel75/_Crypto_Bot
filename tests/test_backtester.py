"""Tests pour src/ml/backtesting/backtester.py."""

import sys
import os
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.ml.backtesting.backtester import (
    Backtester,
    compute_sharpe,
    compute_profit_factor,
    compute_max_drawdown,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_data(n_days: int = 400, seed: int = 42) -> pd.DataFrame:
    """DataFrame synthétique avec DatetimeIndex, features, label et price_close."""
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2023-01-01", periods=n_days, freq="D")
    prices = 30_000 + np.cumsum(rng.normal(0, 200, n_days))
    prices = np.maximum(prices, 100)
    returns = np.diff(prices, prepend=prices[0]) / prices
    labels = (returns > 0).astype(int)

    return pd.DataFrame({
        "price_close": prices,
        "feature_rsi": rng.uniform(20, 80, n_days),
        "feature_sma": rng.uniform(0.95, 1.05, n_days),
        "label": labels,
    }, index=dates)


class _AlwaysBuyStrategy:
    """Stratégie triviale : prédit toujours BUY (1)."""
    def fit(self, X, y): pass
    def predict(self, X): return np.ones(len(X), dtype=int)


class _AlwaysSellStrategy:
    """Stratégie triviale : prédit toujours SELL (0)."""
    def fit(self, X, y): pass
    def predict(self, X): return np.zeros(len(X), dtype=int)


class _PerfectStrategy:
    """Stratégie omnisciente : copie les labels de test."""
    def fit(self, X, y):
        self._last_y = y

    def predict(self, X):
        return np.ones(len(X), dtype=int)  # simplifié


class _FailingStrategy:
    """Stratégie qui lève une exception à chaque fit."""
    def fit(self, X, y): raise RuntimeError("stratégie cassée")
    def predict(self, X): return np.zeros(len(X), dtype=int)


# ---------------------------------------------------------------------------
# compute_sharpe
# ---------------------------------------------------------------------------

class TestComputeSharpe:
    def test_returns_zero_for_single_element(self):
        assert compute_sharpe([0.01]) == 0.0

    def test_returns_zero_for_empty_list(self):
        assert compute_sharpe([]) == 0.0

    def test_returns_zero_when_std_is_zero(self):
        assert compute_sharpe([0.01, 0.01, 0.01]) == 0.0

    def test_positive_returns_give_positive_sharpe(self):
        returns = [0.01] * 5 + [0.02] * 5
        assert compute_sharpe(returns) > 0

    def test_mixed_returns_can_be_negative(self):
        returns = [-0.05, -0.03, -0.04, 0.01, -0.02]
        sharpe = compute_sharpe(returns)
        assert isinstance(sharpe, float)

    def test_annualisation_scales_with_periods(self):
        returns = [0.01, 0.02, 0.015, 0.005]
        s365 = compute_sharpe(returns, periods_per_year=365)
        s252 = compute_sharpe(returns, periods_per_year=252)
        assert s365 > s252  # plus de périodes → Sharpe plus grand


# ---------------------------------------------------------------------------
# compute_profit_factor
# ---------------------------------------------------------------------------

class TestComputeProfitFactor:
    def test_all_winners_returns_inf(self):
        assert compute_profit_factor([0.01, 0.02, 0.03]) == float("inf")

    def test_all_losers_returns_zero(self):
        assert compute_profit_factor([-0.01, -0.02]) == 0.0

    def test_balanced_trades_around_one(self):
        pf = compute_profit_factor([0.1, -0.1])
        assert abs(pf - 1.0) < 1e-9

    def test_profitable_strategy_above_one(self):
        pf = compute_profit_factor([0.2, 0.1, -0.05])
        assert pf > 1.0

    def test_empty_list(self):
        assert compute_profit_factor([]) == 1.0

    def test_zero_returns_treated_as_neutral(self):
        pf = compute_profit_factor([0.0, 0.0, 0.0])
        assert pf == 1.0


# ---------------------------------------------------------------------------
# compute_max_drawdown
# ---------------------------------------------------------------------------

class TestComputeMaxDrawdown:
    def test_empty_returns_zero(self):
        assert compute_max_drawdown([]) == 0.0

    def test_all_positive_returns_zero_drawdown(self):
        assert compute_max_drawdown([0.01, 0.02, 0.03]) == 0.0

    def test_single_loss_gives_positive_drawdown(self):
        dd = compute_max_drawdown([0.1, -0.2, 0.05])
        assert dd > 0

    def test_drawdown_between_zero_and_one(self):
        dd = compute_max_drawdown([0.1, -0.5, 0.1])
        assert 0.0 <= dd <= 1.0

    def test_catastrophic_loss_near_one(self):
        dd = compute_max_drawdown([0.01, -0.99])
        assert dd > 0.9


# ---------------------------------------------------------------------------
# Backtester.__init__
# ---------------------------------------------------------------------------

class TestBacktesterInit:
    def test_default_params(self):
        b = Backtester()
        assert b.train_window == 180
        assert b.test_window == 30

    def test_custom_params(self):
        b = Backtester(train_window=90, test_window=15, purge_days=2, embargo_days=3)
        assert b.train_window == 90
        assert b.purge_days == 2

    def test_zero_train_window_raises(self):
        with pytest.raises(ValueError):
            Backtester(train_window=0)

    def test_zero_test_window_raises(self):
        with pytest.raises(ValueError):
            Backtester(test_window=0)

    def test_negative_raises(self):
        with pytest.raises(ValueError):
            Backtester(train_window=-10)


# ---------------------------------------------------------------------------
# Backtester._validate
# ---------------------------------------------------------------------------

class TestBacktesterValidate:
    def test_missing_label_raises(self):
        df = pd.DataFrame({"price_close": [1, 2]}, index=pd.date_range("2020-01-01", periods=2))
        with pytest.raises(ValueError, match="label"):
            Backtester._validate(df)

    def test_missing_price_close_raises(self):
        df = pd.DataFrame({"label": [0, 1]}, index=pd.date_range("2020-01-01", periods=2))
        with pytest.raises(ValueError, match="price_close"):
            Backtester._validate(df)

    def test_no_datetime_index_raises(self):
        df = pd.DataFrame({"label": [0], "price_close": [1]}, index=[0])
        with pytest.raises(ValueError, match="DatetimeIndex"):
            Backtester._validate(df)

    def test_valid_data_passes(self):
        df = pd.DataFrame(
            {"label": [0, 1], "price_close": [100.0, 101.0]},
            index=pd.date_range("2020-01-01", periods=2),
        )
        Backtester._validate(df)  # ne doit pas lever


# ---------------------------------------------------------------------------
# Backtester.walk_forward
# ---------------------------------------------------------------------------

class TestWalkForward:
    def test_returns_dataframe(self):
        data = _make_data(400)
        b = Backtester(train_window=180, test_window=30)
        results = b.walk_forward(data, _AlwaysBuyStrategy())
        assert isinstance(results, pd.DataFrame)

    def test_produces_at_least_one_fold(self):
        data = _make_data(400)
        b = Backtester(train_window=180, test_window=30)
        results = b.walk_forward(data, _AlwaysBuyStrategy())
        assert len(results) >= 1

    def test_columns_present(self):
        data = _make_data(400)
        b = Backtester(train_window=180, test_window=30)
        results = b.walk_forward(data, _AlwaysBuyStrategy())
        expected = {"fold", "accuracy", "win_rate", "pnl", "sharpe", "profit_factor", "max_drawdown"}
        assert expected.issubset(set(results.columns))

    def test_short_data_raises(self):
        data = _make_data(50)
        b = Backtester(train_window=180, test_window=30)
        with pytest.raises(ValueError, match="jours"):
            b.walk_forward(data, _AlwaysBuyStrategy())

    def test_missing_columns_raises(self):
        data = _make_data(400).drop(columns=["label"])
        b = Backtester(train_window=180, test_window=30)
        with pytest.raises(ValueError, match="label"):
            b.walk_forward(data, _AlwaysBuyStrategy())

    def test_accuracy_between_zero_and_one(self):
        data = _make_data(400)
        b = Backtester(train_window=180, test_window=30)
        results = b.walk_forward(data, _AlwaysBuyStrategy())
        assert (results["accuracy"] >= 0).all()
        assert (results["accuracy"] <= 1).all()

    def test_always_sell_zero_pnl(self):
        data = _make_data(400)
        b = Backtester(train_window=180, test_window=30)
        results = b.walk_forward(data, _AlwaysSellStrategy())
        # SELL prédit 0 → aucun trade BUY → PnL nul
        assert (results["pnl"] == 0.0).all()

    def test_failing_strategy_skips_fold_gracefully(self):
        data = _make_data(400)
        b = Backtester(train_window=180, test_window=30)
        results = b.walk_forward(data, _FailingStrategy())
        # Tous les folds échouent → DataFrame vide
        assert results.empty

    def test_test_windows_do_not_overlap(self):
        data = _make_data(400)
        b = Backtester(train_window=180, test_window=30)
        results = b.walk_forward(data, _AlwaysBuyStrategy())
        if len(results) > 1:
            for i in range(len(results) - 1):
                assert results.iloc[i]["test_end"] <= results.iloc[i + 1]["test_start"]

    def test_n_train_greater_than_n_test(self):
        data = _make_data(400)
        b = Backtester(train_window=180, test_window=30)
        results = b.walk_forward(data, _AlwaysBuyStrategy())
        assert (results["n_train"] >= results["n_test"]).all()


# ---------------------------------------------------------------------------
# Backtester.compute_metrics
# ---------------------------------------------------------------------------

class TestComputeMetrics:
    def test_empty_results_returns_zeros(self):
        b = Backtester()
        metrics = b.compute_metrics(pd.DataFrame())
        assert metrics["n_folds"] == 0
        assert metrics["total_pnl"] == 0.0

    def test_all_keys_present(self):
        data = _make_data(400)
        b = Backtester(train_window=180, test_window=30)
        results = b.walk_forward(data, _AlwaysBuyStrategy())
        metrics = b.compute_metrics(results)
        expected_keys = {"accuracy", "win_rate", "sharpe", "profit_factor", "max_drawdown", "total_pnl", "n_folds"}
        assert expected_keys == set(metrics.keys())

    def test_n_folds_matches_results_length(self):
        data = _make_data(400)
        b = Backtester(train_window=180, test_window=30)
        results = b.walk_forward(data, _AlwaysBuyStrategy())
        metrics = b.compute_metrics(results)
        assert metrics["n_folds"] == len(results)


# ---------------------------------------------------------------------------
# Backtester.compare_baseline
# ---------------------------------------------------------------------------

class TestCompareBaseline:
    def test_returns_dict_with_required_keys(self):
        data = _make_data(400)
        b = Backtester(train_window=180, test_window=30)
        results = b.walk_forward(data, _AlwaysBuyStrategy())
        comparison = b.compare_baseline(results, data)
        assert "strategy_pnl" in comparison
        assert "baseline_return" in comparison
        assert "excess_return" in comparison
        assert "sharpe" in comparison

    def test_empty_results_returns_zeros(self):
        data = _make_data(400)
        b = Backtester()
        comparison = b.compare_baseline(pd.DataFrame(), data)
        assert comparison["strategy_pnl"] == 0.0
        assert comparison["baseline_return"] == 0.0

    def test_excess_return_equals_strategy_minus_baseline(self):
        data = _make_data(400)
        b = Backtester(train_window=180, test_window=30)
        results = b.walk_forward(data, _AlwaysBuyStrategy())
        comp = b.compare_baseline(results, data)
        assert abs(comp["excess_return"] - (comp["strategy_pnl"] - comp["baseline_return"])) < 1e-9
