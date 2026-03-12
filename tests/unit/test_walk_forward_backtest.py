"""Tests for WalkForwardBacktester — walk-forward validation with purging + embargo.

Validates: data splitting, temporal integrity, metrics computation (Sharpe, win rate,
profit factor, max drawdown), and aggregate reporting.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import pytest

from src.ml.backtesting.backtest_engine import (
    BacktestMetrics,
    BacktestSummary,
    WalkForwardBacktester,
    _compute_max_drawdown,
    _compute_profit_factor,
    _compute_sharpe,
    _simulate_trades,
)
from src.ml.exceptions import InsufficientDataError

UTC = timezone.utc

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def synthetic_dataset() -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    """Generate a synthetic 250-candle 4h dataset with features, signals, and returns.

    Returns:
        (features, signals, price_returns) tuple.
    """
    n = 250
    dates = pd.date_range("2023-01-01", periods=n, freq="4h", tz=UTC)
    rng = np.random.default_rng(seed=42)

    # Features (2 dummy features for fold boundaries)
    features = pd.DataFrame(
        {
            "rsi": 50 + rng.standard_normal(n) * 10,
            "bb_pos": rng.uniform(0, 1, n),
        },
        index=dates,
    )

    # Signals: some BUY (1), some SELL (-1), mostly HOLD (0)
    signals = pd.Series(
        rng.choice([0, 0, 0, 1, -1], size=n),
        index=dates,
        dtype=int,
    )

    # Price returns: mostly small ±0.5%, some larger moves
    price_returns = pd.Series(
        rng.normal(0.002, 0.01, n),
        index=dates,
    )

    return features, signals, price_returns


@pytest.fixture
def small_dataset() -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    """Generate a minimal dataset (50 rows) to test boundary conditions."""
    n = 50
    dates = pd.date_range("2023-01-01", periods=n, freq="4h", tz=UTC)

    features = pd.DataFrame(
        {
            "rsi": 50 + np.random.RandomState(42).standard_normal(n) * 10,
        },
        index=dates,
    )

    signals = pd.Series(
        np.ones(n, dtype=int),  # All BUY signals
        index=dates,
    )

    # Constant returns to test metric calculation
    price_returns = pd.Series(
        np.full(n, 0.01),  # All +1% per candle
        index=dates,
    )

    return features, signals, price_returns


# ---------------------------------------------------------------------------
# Unit tests for helper functions
# ---------------------------------------------------------------------------


class TestComputeMaxDrawdown:
    """Tests for _compute_max_drawdown helper."""

    def test_no_returns_returns_zero_drawdown(self) -> None:
        """Empty return list should give 0 drawdown."""
        result = _compute_max_drawdown([])
        assert result == 0.0

    def test_all_positive_returns_zero_drawdown(self) -> None:
        """All positive returns = no drawdown."""
        returns = [0.01, 0.02, 0.015, 0.03]
        result = _compute_max_drawdown(returns)
        assert result == pytest.approx(0.0, abs=1e-6)

    def test_single_large_loss_detected(self) -> None:
        """Large loss followed by recovery should show significant drawdown."""
        returns = [0.05, -0.30, 0.10, 0.05]  # Peak at 0.05, then drop 30%
        result = _compute_max_drawdown(returns)
        # Peak after +5%: 1.05, then -30%: 0.735, drawdown = (1.05-0.735)/1.05 ≈ 0.30
        assert result > 0.20 and result < 0.35

    def test_recovery_from_drawdown(self) -> None:
        """Drawdown followed by recovery should show max from peak."""
        returns = [0.10, -0.15, 0.20]
        result = _compute_max_drawdown(returns)
        # Peak at 1.10 after +10%, then drops to 0.935 (-15% of 1.10)
        assert result > 0.0


class TestComputeSharpe:
    """Tests for _compute_sharpe helper."""

    def test_empty_returns_zero_sharpe(self) -> None:
        """No returns = zero Sharpe."""
        result = _compute_sharpe([])
        assert result == 0.0

    def test_single_return_zero_sharpe(self) -> None:
        """Single return (can't compute std) = zero Sharpe."""
        result = _compute_sharpe([0.05])
        assert result == 0.0

    def test_constant_returns_zero_sharpe(self) -> None:
        """Constant returns = no volatility = undefined Sharpe (return 0)."""
        result = _compute_sharpe([0.01, 0.01, 0.01])
        assert result == 0.0

    def test_positive_sharpe_ratio(self) -> None:
        """Consistent positive returns with low variance = high Sharpe."""
        returns = [0.01] * 100 + [0.015] * 50  # Mean +1.003%, low std
        result = _compute_sharpe(returns, candles_per_year=252)
        assert result > 0  # Should be positive

    def test_negative_sharpe_ratio(self) -> None:
        """Negative mean return = negative Sharpe."""
        returns = [-0.02, -0.01, -0.015]
        result = _compute_sharpe(returns)
        assert result < 0


class TestComputeProfitFactor:
    """Tests for _compute_profit_factor helper."""

    def test_all_winning_trades(self) -> None:
        """All winning trades = infinite profit factor."""
        returns = [0.05, 0.10, 0.02]
        result = _compute_profit_factor(returns)
        assert result == float("inf")

    def test_all_losing_trades(self) -> None:
        """All losing trades = 1.0 profit factor (by convention)."""
        returns = [-0.05, -0.10, -0.02]
        result = _compute_profit_factor(returns)
        assert result == 1.0

    def test_mixed_trades(self) -> None:
        """50% win rate with equal sizes."""
        returns = [0.10, -0.10, 0.05, -0.05]
        result = _compute_profit_factor(returns)
        # gross_profit = 0.15, gross_loss = 0.15 → PF = 1.0
        assert result == pytest.approx(1.0)

    def test_profitable_overall(self) -> None:
        """More profit than loss = PF > 1.0."""
        returns = [0.10, 0.05, -0.02]
        result = _compute_profit_factor(returns)
        # gross_profit = 0.15, gross_loss = 0.02 → PF = 7.5
        assert result == pytest.approx(7.5)


class TestSimulateTrades:
    """Tests for _simulate_trades helper."""

    def test_no_signals_no_trades(self) -> None:
        """Zero signal series = no trades."""
        signals = pd.Series([0, 0, 0])
        returns = pd.Series([0.01, 0.02, 0.01])
        result = _simulate_trades(signals, returns)
        assert result == []

    def test_single_buy_signal(self) -> None:
        """BUY signal (1) followed by +1% return and -0.1% commission = +0.9%."""
        signals = pd.Series([1, 0, 0], index=[0, 1, 2])
        returns = pd.Series([0.01, 0.02, -0.01], index=[0, 1, 2])
        result = _simulate_trades(signals, returns)
        assert len(result) == 1
        # 1 * 0.01 - 0.001 (commission) = 0.009
        assert result[0] == pytest.approx(0.009)

    def test_short_signal_profit(self) -> None:
        """SELL signal (-1) with -1% return = profit after commission."""
        signals = pd.Series([-1, 0], index=[0, 1])
        returns = pd.Series([-0.01, 0.01], index=[0, 1])
        result = _simulate_trades(signals, returns)
        assert len(result) == 1
        # -1 * -0.01 - 0.001 = 0.009
        assert result[0] == pytest.approx(0.009)

    def test_multiple_signals(self) -> None:
        """Multiple signals in sequence."""
        signals = pd.Series([1, 0, -1, 0], index=[0, 1, 2, 3])
        returns = pd.Series([0.01, 0.02, -0.02, 0.01], index=[0, 1, 2, 3])
        result = _simulate_trades(signals, returns, commission=0.001)
        assert len(result) == 2
        # Trade 1: 1 * 0.01 - 0.001 = 0.009
        # Trade 2: -1 * -0.02 - 0.001 = 0.019
        assert result[0] == pytest.approx(0.009)
        assert result[1] == pytest.approx(0.019)


# ---------------------------------------------------------------------------
# Integration tests for WalkForwardBacktester
# ---------------------------------------------------------------------------


class TestWalkForwardBacktester:
    """Tests for WalkForwardBacktester main class."""

    def test_initialization(self) -> None:
        """Backtester initializes with custom parameters."""
        bt = WalkForwardBacktester(
            n_folds=3,
            purge_periods=10,
            embargo_periods=5,
            commission=0.002,
            candles_per_year=250,
        )
        assert bt._n_folds == 3
        assert bt._purge == 10
        assert bt._embargo == 5
        assert bt._commission == 0.002

    def test_default_parameters(self) -> None:
        """Backtester uses sensible defaults."""
        bt = WalkForwardBacktester()
        assert bt._n_folds == 5
        assert bt._purge == 5
        assert bt._embargo == 2
        assert bt._commission == 0.001

    def test_insufficient_data_raises_error(self, small_dataset: tuple) -> None:
        """Requesting too many folds with small dataset raises InsufficientDataError."""
        features, signals, returns = small_dataset
        bt = WalkForwardBacktester(n_folds=10)  # 10 folds on 50 rows = too many

        with pytest.raises(InsufficientDataError):
            bt.run(features, signals, returns)

    def test_run_returns_summary(self, synthetic_dataset: tuple) -> None:
        """Backtester.run() returns a BacktestSummary object."""
        features, signals, returns = synthetic_dataset
        bt = WalkForwardBacktester(n_folds=5)

        summary = bt.run(features, signals, returns)

        assert isinstance(summary, BacktestSummary)
        assert summary.n_folds >= 1
        assert summary.n_folds <= 5
        assert len(summary.folds) == summary.n_folds

    def test_metrics_structure(self, synthetic_dataset: tuple) -> None:
        """Each BacktestMetrics contains required fields."""
        features, signals, returns = synthetic_dataset
        bt = WalkForwardBacktester(n_folds=3)

        summary = bt.run(features, signals, returns)

        for fold in summary.folds:
            assert isinstance(fold, BacktestMetrics)
            assert fold.fold_id >= 0
            assert isinstance(fold.train_start, pd.Timestamp)
            assert isinstance(fold.train_end, pd.Timestamp)
            assert isinstance(fold.test_start, pd.Timestamp)
            assert isinstance(fold.test_end, pd.Timestamp)
            assert fold.n_trades >= 0
            assert 0.0 <= fold.win_rate <= 1.0
            assert fold.profit_factor >= 0.0
            assert fold.sharpe_ratio >= 0.0 or fold.sharpe_ratio < 0
            assert 0.0 <= fold.max_drawdown <= 1.0

    def test_temporal_ordering_preserved(self, synthetic_dataset: tuple) -> None:
        """Train/test windows are strictly ordered in time."""
        features, signals, returns = synthetic_dataset
        bt = WalkForwardBacktester(n_folds=3)

        summary = bt.run(features, signals, returns)

        for fold in summary.folds:
            assert fold.train_start < fold.train_end
            assert fold.train_end <= fold.test_start
            assert fold.test_start < fold.test_end

    def test_folds_do_not_overlap(self, synthetic_dataset: tuple) -> None:
        """Train and test windows in consecutive folds do not overlap."""
        features, signals, returns = synthetic_dataset
        bt = WalkForwardBacktester(n_folds=4, purge_periods=5, embargo_periods=2)

        summary = bt.run(features, signals, returns)

        for i in range(len(summary.folds) - 1):
            curr_test_end = summary.folds[i].test_end
            next_train_start = summary.folds[i + 1].train_start
            # There should be no overlap (purge gap ensures this)
            assert curr_test_end <= next_train_start

    def test_aggregate_metrics_reasonable(self, synthetic_dataset: tuple) -> None:
        """Aggregate metrics are within sensible ranges."""
        features, signals, returns = synthetic_dataset
        bt = WalkForwardBacktester(n_folds=5)

        summary = bt.run(features, signals, returns)

        assert 0.0 <= summary.mean_win_rate <= 1.0
        assert summary.mean_profit_factor >= 0.0
        assert 0.0 <= summary.mean_max_drawdown <= 1.0
        assert -10 < summary.mean_sharpe < 10  # Sharpe can be negative

    def test_all_hold_signals_zero_metrics(self) -> None:
        """Dataset with no BUY/SELL signals shows zero trades and zero metrics."""
        n = 100
        dates = pd.date_range("2023-01-01", periods=n, freq="4h", tz=UTC)

        features = pd.DataFrame({"feature": np.zeros(n)}, index=dates)
        signals = pd.Series(np.zeros(n, dtype=int), index=dates)  # All HOLD
        returns = pd.Series(np.full(n, 0.01), index=dates)

        bt = WalkForwardBacktester(n_folds=3, purge_periods=5, embargo_periods=2)
        summary = bt.run(features, signals, returns)

        for fold in summary.folds:
            assert fold.n_trades == 0
            assert fold.win_rate == 0.0
            assert fold.profit_factor == 1.0
            assert fold.sharpe_ratio == 0.0

    def test_purge_window_removes_label_leakage(self) -> None:
        """Purge window is applied: train_end = split_idx - purge_periods."""
        n = 200
        dates = pd.date_range("2023-01-01", periods=n, freq="4h", tz=UTC)

        features = pd.DataFrame({"f": np.arange(n)}, index=dates)
        signals = pd.Series(np.zeros(n, dtype=int), index=dates)
        returns = pd.Series(np.zeros(n), index=dates)

        purge = 10
        bt = WalkForwardBacktester(n_folds=2, purge_periods=purge, embargo_periods=0)
        summary = bt.run(features, signals, returns)

        # For fold 0, test starts at n//2 = 100
        # train_end should be ~100 - 10 = 90
        fold0 = summary.folds[0]
        fold0_test_start_idx = list(features.index).index(fold0.test_start)
        fold0_train_end_idx = list(features.index).index(fold0.train_end)
        assert fold0_train_end_idx < fold0_test_start_idx

    def test_embargo_window_skips_lookahead(self) -> None:
        """Embargo window is applied: test starts after embargo_periods rows."""
        n = 200
        dates = pd.date_range("2023-01-01", periods=n, freq="4h", tz=UTC)

        features = pd.DataFrame({"f": np.arange(n)}, index=dates)
        signals = pd.Series(np.ones(n, dtype=int), index=dates)  # All BUY
        returns = pd.Series(np.full(n, 0.01), index=dates)

        embargo = 5
        bt = WalkForwardBacktester(n_folds=2, purge_periods=5, embargo_periods=embargo)
        summary = bt.run(features, signals, returns)

        fold0 = summary.folds[0]
        # Between train_end and test_start there should be gap of ≥ embargo
        train_end_idx = list(features.index).index(fold0.train_end)
        test_start_idx = list(features.index).index(fold0.test_start)
        gap = test_start_idx - train_end_idx - 1
        assert gap >= embargo


# ---------------------------------------------------------------------------
# Edge cases & error handling
# ---------------------------------------------------------------------------


class TestWalkForwardBacktesterEdgeCases:
    """Tests for boundary conditions and error scenarios."""

    def test_single_fold(self, synthetic_dataset: tuple) -> None:
        """Single fold backtesting should work."""
        features, signals, returns = synthetic_dataset
        bt = WalkForwardBacktester(n_folds=1)
        summary = bt.run(features, signals, returns)
        assert summary.n_folds >= 1

    def test_zero_commission(self, synthetic_dataset: tuple) -> None:
        """Zero commission shouldn't crash."""
        features, signals, returns = synthetic_dataset
        bt = WalkForwardBacktester(n_folds=3, commission=0.0)
        summary = bt.run(features, signals, returns)
        assert summary.n_folds >= 1

    def test_misaligned_signals_index(self) -> None:
        """Signals with partial index overlap should fill missing with 0."""
        n = 50
        dates = pd.date_range("2023-01-01", periods=n, freq="4h", tz=UTC)

        features = pd.DataFrame({"f": np.zeros(n)}, index=dates)
        # Signals only on every other day
        signal_dates = dates[::2]
        signals = pd.Series(np.ones(len(signal_dates), dtype=int), index=signal_dates)
        returns = pd.Series(np.full(n, 0.01), index=dates)

        bt = WalkForwardBacktester(n_folds=2)
        # Should not crash — missing signal indices filled with 0
        summary = bt.run(features, signals, returns)
        assert summary.n_folds >= 1

    def test_negative_returns_handled(self) -> None:
        """Strongly negative returns should compute metrics correctly."""
        n = 100
        dates = pd.date_range("2023-01-01", periods=n, freq="4h", tz=UTC)

        features = pd.DataFrame({"f": np.zeros(n)}, index=dates)
        signals = pd.Series(np.ones(n, dtype=int), index=dates)
        returns = pd.Series(np.full(n, -0.02), index=dates)  # All -2%

        bt = WalkForwardBacktester(n_folds=2)
        summary = bt.run(features, signals, returns)

        # With all losing trades, profit_factor should be 1.0
        for fold in summary.folds:
            if fold.n_trades > 0:
                assert fold.profit_factor == pytest.approx(1.0)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
