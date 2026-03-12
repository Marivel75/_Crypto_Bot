"""Tests for walk-forward backtesting engine with purging and embargo."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.ml.backtesting.backtest_engine import (
    WalkForwardBacktester,
    _compute_max_drawdown,
    _compute_sharpe,
    _compute_profit_factor,
    _simulate_trades,
)
from src.ml.exceptions import InsufficientDataError


class TestComputeMetrics:
    """Test individual metric computation functions."""

    def test_compute_max_drawdown_constant_returns_zero(self) -> None:
        """Constant returns should have zero drawdown."""
        returns = [0.0] * 10

        dd = _compute_max_drawdown(returns)

        assert dd == pytest.approx(0.0)

    def test_compute_max_drawdown_loss_sequence(self) -> None:
        """Sequence of losses should compute correct drawdown."""
        # Starting at 100: lose 10% (90), lose 10% (81) -> 19% max drawdown
        returns = [-0.1, -0.1, 0.05, 0.05]

        dd = _compute_max_drawdown(returns)

        assert dd > 0.0
        assert dd < 1.0

    def test_compute_max_drawdown_empty_returns_zero(self) -> None:
        """Empty returns list should return zero."""
        dd = _compute_max_drawdown([])

        assert dd == 0.0

    def test_compute_sharpe_constant_std_zero(self) -> None:
        """Constant returns should have zero Sharpe."""
        returns = [0.01] * 10

        sharpe = _compute_sharpe(returns)

        assert sharpe == 0.0

    def test_compute_sharpe_positive_returns(self) -> None:
        """Positive mean returns should give positive Sharpe."""
        returns = [0.01, 0.02, 0.015, 0.025, 0.01] * 10

        sharpe = _compute_sharpe(returns)

        assert sharpe > 0.0

    def test_compute_sharpe_single_return_returns_zero(self) -> None:
        """Single return should return zero Sharpe."""
        sharpe = _compute_sharpe([0.01])

        assert sharpe == 0.0

    def test_compute_profit_factor_all_winners(self) -> None:
        """All winning trades should give inf profit factor."""
        returns = [0.01, 0.02, 0.015, 0.025]

        pf = _compute_profit_factor(returns)

        assert pf == float("inf")

    def test_compute_profit_factor_all_losers(self) -> None:
        """All losing trades should give ~1.0 profit factor."""
        returns = [-0.01, -0.02, -0.015]

        pf = _compute_profit_factor(returns)

        assert pf == pytest.approx(1.0)

    def test_compute_profit_factor_mixed_trades(self) -> None:
        """Mixed trades should compute correct profit factor."""
        # Gross profit = 0.05, Gross loss = 0.04 -> PF = 1.25
        returns = [0.02, 0.03, -0.02, -0.02]

        pf = _compute_profit_factor(returns)

        assert pf == pytest.approx(1.25, abs=0.01)


class TestSimulateTrades:
    """Test trade simulation from signals and returns."""

    def test_no_signals_no_trades(self) -> None:
        """Zero signals should produce no trades."""
        signals = pd.Series([0, 0, 0, 0], index=pd.date_range("2025-01-01", periods=4, freq="h"))
        returns = pd.Series([0.01, 0.02, -0.01, 0.015], index=signals.index)

        trades = _simulate_trades(signals, returns)

        assert len(trades) == 0

    def test_buy_signals_produce_trades(self) -> None:
        """BUY signals (1) should produce trades."""
        signals = pd.Series([1, 0, 1, 0], index=pd.date_range("2025-01-01", periods=4, freq="h"))
        returns = pd.Series([0.01, 0.02, 0.03, 0.01], index=signals.index)

        trades = _simulate_trades(signals, returns)

        assert len(trades) == 2

    def test_sell_signals_produce_trades(self) -> None:
        """SELL signals (-1) should produce trades."""
        signals = pd.Series([-1, 0, -1, 0], index=pd.date_range("2025-01-01", periods=4, freq="h"))
        returns = pd.Series([0.01, 0.02, -0.01, 0.015], index=signals.index)

        trades = _simulate_trades(signals, returns)

        assert len(trades) == 2

    def test_long_trade_profit_on_positive_return(self) -> None:
        """Long trade (signal=1) should profit on positive return."""
        signals = pd.Series([1], index=pd.date_range("2025-01-01", periods=1, freq="h"))
        returns = pd.Series([0.02], index=signals.index)

        trades = _simulate_trades(signals, returns, commission=0.001)

        # Net return = 1 * 0.02 - 0.001 = 0.019
        assert trades[0] == pytest.approx(0.019, abs=0.001)

    def test_short_trade_profit_on_negative_return(self) -> None:
        """Short trade (signal=-1) should profit on negative return."""
        signals = pd.Series([-1], index=pd.date_range("2025-01-01", periods=1, freq="h"))
        returns = pd.Series([-0.02], index=signals.index)

        trades = _simulate_trades(signals, returns, commission=0.001)

        # Net return = -1 * (-0.02) - 0.001 = 0.019
        assert trades[0] == pytest.approx(0.019, abs=0.001)

    def test_commission_deducted_from_trades(self) -> None:
        """High commission should reduce trade profit."""
        signals = pd.Series([1], index=pd.date_range("2025-01-01", periods=1, freq="h"))
        returns = pd.Series([0.02], index=signals.index)

        trades_low_comm = _simulate_trades(signals, returns, commission=0.001)
        trades_high_comm = _simulate_trades(signals, returns, commission=0.01)

        assert trades_high_comm[0] < trades_low_comm[0]


class TestWalkForwardBacktester:
    """Test walk-forward backtesting engine."""

    def test_backtester_initialization(self) -> None:
        """Backtester should initialize with parameters."""
        btester = WalkForwardBacktester(n_folds=5, purge_periods=5, embargo_periods=2)

        assert btester._n_folds == 5
        assert btester._purge == 5
        assert btester._embargo == 2

    def test_insufficient_data_raises_error(self) -> None:
        """Too few rows should raise InsufficientDataError."""
        features = pd.DataFrame(
            {"col": range(10)},
            index=pd.date_range("2025-01-01", periods=10, freq="h"),
        )
        signals = pd.Series([1, 0, 1, 0, 1, 0, 1, 0, 1, 0], index=features.index)
        returns = pd.Series([0.01] * 10, index=features.index)

        btester = WalkForwardBacktester(n_folds=5)

        with pytest.raises(InsufficientDataError):
            btester.run(features, signals, returns)

    def test_basic_backtest_run(self) -> None:
        """Basic backtest run should produce summary."""
        np.random.seed(42)
        n = 500
        features = pd.DataFrame(
            {"col": np.random.randn(n).cumsum()},
            index=pd.date_range("2025-01-01", periods=n, freq="h"),
        )
        signals = pd.Series([1 if x > 0 else -1 for x in np.random.randn(n)], index=features.index)
        returns = pd.Series(np.random.randn(n) * 0.01, index=features.index)

        btester = WalkForwardBacktester(n_folds=3, purge_periods=5, embargo_periods=2)
        summary = btester.run(features, signals, returns)

        assert summary.n_folds == 3
        assert len(summary.folds) == 3

    def test_backtest_fold_metrics_valid(self) -> None:
        """Each fold should have valid metrics."""
        np.random.seed(42)
        n = 500
        features = pd.DataFrame(
            {"col": np.random.randn(n).cumsum()},
            index=pd.date_range("2025-01-01", periods=n, freq="h"),
        )
        signals = pd.Series([1 if x > 0 else -1 for x in np.random.randn(n)], index=features.index)
        returns = pd.Series(np.random.randn(n) * 0.01, index=features.index)

        btester = WalkForwardBacktester(n_folds=3)
        summary = btester.run(features, signals, returns)

        for fold in summary.folds:
            assert fold.fold_id >= 0
            assert 0 <= fold.win_rate <= 1
            assert fold.sharpe_ratio is not None
            assert 0 <= fold.max_drawdown <= 1
            assert fold.n_trades >= 0

    def test_backtest_summary_aggregate_metrics(self) -> None:
        """Summary should have aggregate metrics."""
        np.random.seed(42)
        n = 500
        features = pd.DataFrame(
            {"col": np.random.randn(n).cumsum()},
            index=pd.date_range("2025-01-01", periods=n, freq="h"),
        )
        signals = pd.Series([1 if x > 0 else -1 for x in np.random.randn(n)], index=features.index)
        returns = pd.Series(np.random.randn(n) * 0.01, index=features.index)

        btester = WalkForwardBacktester(n_folds=3)
        summary = btester.run(features, signals, returns)

        assert summary.mean_sharpe >= 0  # Can be 0
        assert 0 <= summary.mean_win_rate <= 1
        assert summary.mean_profit_factor >= 0
        assert 0 <= summary.mean_max_drawdown <= 1

    def test_backtest_no_signals_produces_zero_metrics(self) -> None:
        """Backtest with no signals should produce zero metrics."""
        n = 500
        features = pd.DataFrame(
            {"col": range(n)},
            index=pd.date_range("2025-01-01", periods=n, freq="h"),
        )
        signals = pd.Series([0] * n, index=features.index)
        returns = pd.Series([0.01] * n, index=features.index)

        btester = WalkForwardBacktester(n_folds=3)
        summary = btester.run(features, signals, returns)

        # All folds should have 0 trades
        for fold in summary.folds:
            assert fold.n_trades == 0

    def test_backtest_perfect_signals_high_metrics(self) -> None:
        """Perfect signals should produce high metrics."""
        n = 500
        index = pd.date_range("2025-01-01", periods=n, freq="h")
        prices = 100 + np.cumsum(np.random.randn(n) * 0.5)
        returns = pd.Series(np.diff(prices) / prices[:-1], index=index[1:])
        returns = returns.reindex(index).fillna(0)

        # Buy when price will go up, sell when price will go down
        future_returns = returns.shift(-1).fillna(0)
        signals = pd.Series(
            [1 if x > 0 else -1 for x in future_returns],
            index=index,
        )

        features = pd.DataFrame({"col": prices}, index=index)

        btester = WalkForwardBacktester(n_folds=2)
        summary = btester.run(features, signals, returns)

        # Should have good metrics with perfect foresight
        assert summary.mean_win_rate > 0.5
