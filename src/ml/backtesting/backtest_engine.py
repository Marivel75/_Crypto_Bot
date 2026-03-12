"""Walk-forward backtesting engine with purging and embargo windows.

This module evaluates a trading signal strategy (rule-based or ML) using
strict temporal splitting.  Random train/test splits are explicitly
forbidden on time-series data.

Metrics computed:
- Sharpe ratio (annualised)
- Win rate
- Profit factor
- Maximum drawdown
- Total return
- Number of trades
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from src.ml.exceptions import InsufficientDataError

logger = logging.getLogger(__name__)

# Annualisation constant: 4h candles → 6 per day × 365 days
_CANDLES_PER_YEAR_4H: int = 6 * 365


@dataclass(frozen=True, slots=True)
class BacktestMetrics:
    """Immutable result of one walk-forward fold.

    Attributes:
        fold_id: Zero-based index of this fold.
        train_start: Start timestamp of the training window.
        train_end: End timestamp of the training window.
        test_start: Start timestamp of the test window.
        test_end: End timestamp of the test window.
        n_trades: Number of signal-triggered simulated trades.
        win_rate: Fraction of winning trades [0, 1].
        profit_factor: Gross profit / gross loss (> 1 is profitable).
        sharpe_ratio: Annualised Sharpe ratio.
        max_drawdown: Maximum peak-to-trough portfolio drawdown [0, 1].
        total_return: Cumulative return over the test window.
        trades: Tuple of individual trade return values.
    """

    fold_id: int
    train_start: pd.Timestamp
    train_end: pd.Timestamp
    test_start: pd.Timestamp
    test_end: pd.Timestamp
    n_trades: int
    win_rate: float
    profit_factor: float
    sharpe_ratio: float
    max_drawdown: float
    total_return: float
    trades: tuple[float, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class BacktestSummary:
    """Aggregate metrics across all walk-forward folds.

    Attributes:
        n_folds: Number of folds evaluated.
        mean_sharpe: Mean Sharpe ratio across folds.
        mean_win_rate: Mean win rate across folds.
        mean_profit_factor: Mean profit factor across folds.
        mean_max_drawdown: Mean maximum drawdown across folds.
        mean_total_return: Mean total return across folds.
        folds: Tuple of individual fold results.
    """

    n_folds: int
    mean_sharpe: float
    mean_win_rate: float
    mean_profit_factor: float
    mean_max_drawdown: float
    mean_total_return: float
    folds: tuple[BacktestMetrics, ...]


def _compute_max_drawdown(returns: list[float]) -> float:
    """Compute maximum peak-to-trough drawdown from a list of period returns.

    Args:
        returns: List of per-trade (or per-period) returns.

    Returns:
        Maximum drawdown as a positive fraction (e.g. 0.25 = 25% drawdown).
    """
    if not returns:
        return 0.0
    cumulative = np.cumprod([1 + r for r in returns])
    peak = np.maximum.accumulate(cumulative)
    drawdown = (peak - cumulative) / peak
    return float(np.max(drawdown))


def _compute_sharpe(returns: list[float], candles_per_year: int = _CANDLES_PER_YEAR_4H) -> float:
    """Compute annualised Sharpe ratio (risk-free rate = 0).

    Args:
        returns: List of per-trade returns.
        candles_per_year: Annualisation factor.

    Returns:
        Annualised Sharpe ratio, or 0.0 if std is zero.
    """
    if len(returns) < 2:
        return 0.0
    arr = np.array(returns, dtype=float)
    mean = float(np.mean(arr))
    std = float(np.std(arr, ddof=1))
    if std == 0:
        return 0.0
    return float((mean / std) * math.sqrt(candles_per_year))


def _compute_profit_factor(returns: list[float]) -> float:
    """Compute gross profit / gross loss ratio.

    Args:
        returns: List of per-trade returns.

    Returns:
        Profit factor (> 1.0 = profitable overall). Returns 0.0 when all
        trades are losers with no gross profit.
    """
    gross_profit = sum(r for r in returns if r > 0)
    gross_loss = abs(sum(r for r in returns if r < 0))
    if gross_loss == 0:
        return float("inf") if gross_profit > 0 else 1.0
    return gross_profit / gross_loss


def _simulate_trades(
    signals: pd.Series,
    returns: pd.Series,
    commission: float = 0.001,
) -> list[float]:
    """Simulate trade outcomes given a signal series and future returns.

    For each non-zero signal we take a position proportional to the signal
    direction (1=long, -1=short) and compute the net return after commission.

    Args:
        signals: Series of integer signals (1=BUY, -1=SELL, 0=HOLD),
            indexed identically to ``returns``.
        returns: Series of per-candle forward returns.
        commission: Round-trip commission fraction deducted from each trade.

    Returns:
        List of net trade returns (empty if no signals).
    """
    trade_returns: list[float] = []
    for idx in signals.index:
        sig = int(signals.loc[idx])
        if sig == 0:
            continue
        ret = float(returns.loc[idx]) if idx in returns.index else 0.0
        # Long: profit when price rises; short: profit when price falls
        net_ret = sig * ret - commission
        trade_returns.append(net_ret)
    return trade_returns


class WalkForwardBacktester:
    """Walk-forward backtester with purging and embargo windows.

    The dataset is split into ``n_folds`` sequential folds.  In each fold:
    1. **Training window**: rows 0 .. split_idx (exclusive)
    2. **Purge gap**: ``purge_periods`` rows before the split are excluded
       from training to prevent leakage from overlapping labels.
    3. **Embargo gap**: ``embargo_periods`` rows after the split are
       skipped before the test window begins.
    4. **Test window**: the remaining rows after the embargo.

    Args:
        n_folds: Number of walk-forward folds (default 5).
        purge_periods: Rows to drop from the end of training (label leakage
            prevention). Default 5.
        embargo_periods: Rows to skip at the start of each test window
            (prevents lookahead from overlapping candles). Default 2.
        commission: Round-trip trade commission. Default 0.001 (0.1%).
        candles_per_year: Used for Sharpe annualisation. Default 4h candles.
    """

    def __init__(
        self,
        n_folds: int = 5,
        purge_periods: int = 5,
        embargo_periods: int = 2,
        commission: float = 0.001,
        candles_per_year: int = _CANDLES_PER_YEAR_4H,
    ) -> None:
        self._n_folds = n_folds
        self._purge = purge_periods
        self._embargo = embargo_periods
        self._commission = commission
        self._candles_per_year = candles_per_year

    def run(
        self,
        features: pd.DataFrame,
        signals: pd.Series,
        price_returns: pd.Series,
    ) -> BacktestSummary:
        """Execute walk-forward backtesting.

        Args:
            features: Feature matrix with DatetimeIndex sorted ascending.
                Used to derive fold boundaries (not passed to any model here —
                signal generation is assumed to have already occurred).
            signals: Integer signal series (1=BUY, -1=SELL, 0=HOLD)
                aligned to ``features`` index.
            price_returns: Per-candle forward returns aligned to ``features``
                index (e.g. ``(close.shift(-1) - close) / close``).

        Returns:
            :class:`BacktestSummary` with aggregate metrics and per-fold details.

        Raises:
            InsufficientDataError: If the dataset is too small for the
                requested number of folds.
        """
        n = len(features)
        min_required = self._n_folds * (self._purge + self._embargo + 10)
        if n < min_required:
            raise InsufficientDataError(
                f"Need at least {min_required} rows for {self._n_folds} folds "
                f"(purge={self._purge}, embargo={self._embargo}), got {n}",
                detail={"n_rows": n, "n_folds": self._n_folds},
            )

        fold_size = n // self._n_folds
        fold_results: list[BacktestMetrics] = []

        for fold_id in range(self._n_folds):
            # Determine boundaries
            test_start_idx = (fold_id + 1) * fold_size
            test_end_idx = min(test_start_idx + fold_size, n)

            if test_end_idx <= test_start_idx:
                logger.debug("Fold %d: empty test window — skipping", fold_id)
                continue

            # Training: all rows before the test window minus the purge gap
            train_end_idx = test_start_idx - self._purge
            if train_end_idx <= 0:
                logger.debug("Fold %d: no training data after purge — skipping", fold_id)
                continue

            # Embargo: skip rows immediately after training
            actual_test_start_idx = test_start_idx + self._embargo
            if actual_test_start_idx >= test_end_idx:
                logger.debug("Fold %d: embargo covers full test window — skipping", fold_id)
                continue

            train_idx = features.index[:train_end_idx]
            test_idx = features.index[actual_test_start_idx:test_end_idx]

            test_signals = signals.reindex(test_idx).fillna(0)
            test_returns = price_returns.reindex(test_idx).fillna(0.0)

            trades = _simulate_trades(test_signals, test_returns, self._commission)

            if not trades:
                # No signals fired — record zero-trade fold
                fold_results.append(
                    BacktestMetrics(
                        fold_id=fold_id,
                        train_start=train_idx[0],
                        train_end=train_idx[-1],
                        test_start=test_idx[0],
                        test_end=test_idx[-1],
                        n_trades=0,
                        win_rate=0.0,
                        profit_factor=1.0,
                        sharpe_ratio=0.0,
                        max_drawdown=0.0,
                        total_return=0.0,
                        trades=(),
                    )
                )
                continue

            wins = [t for t in trades if t > 0]
            win_rate = len(wins) / len(trades) if trades else 0.0
            profit_factor = _compute_profit_factor(trades)
            sharpe = _compute_sharpe(trades, self._candles_per_year)
            max_dd = _compute_max_drawdown(trades)
            total_ret = float(np.prod([1 + r for r in trades]) - 1)

            fold_results.append(
                BacktestMetrics(
                    fold_id=fold_id,
                    train_start=train_idx[0],
                    train_end=train_idx[-1],
                    test_start=test_idx[0],
                    test_end=test_idx[-1],
                    n_trades=len(trades),
                    win_rate=win_rate,
                    profit_factor=profit_factor,
                    sharpe_ratio=sharpe,
                    max_drawdown=max_dd,
                    total_return=total_ret,
                    trades=tuple(trades),
                )
            )

            logger.info(
                "Fold %d: n_trades=%d win_rate=%.2f pf=%.2f sharpe=%.2f mdd=%.2f ret=%.2f",
                fold_id,
                len(trades),
                win_rate,
                profit_factor,
                sharpe,
                max_dd,
                total_ret,
            )

        if not fold_results:
            raise InsufficientDataError(
                "No valid folds produced during walk-forward backtest",
                detail={"n_folds": self._n_folds, "n_rows": n},
            )

        summary = self._aggregate(fold_results)
        logger.info(
            "Backtest complete: %d folds — mean_sharpe=%.3f mean_win_rate=%.2f "
            "mean_pf=%.2f mean_mdd=%.2f mean_ret=%.2f",
            summary.n_folds,
            summary.mean_sharpe,
            summary.mean_win_rate,
            summary.mean_profit_factor,
            summary.mean_max_drawdown,
            summary.mean_total_return,
        )
        return summary

    @staticmethod
    def _aggregate(folds: list[BacktestMetrics]) -> BacktestSummary:
        """Compute aggregate statistics across all walk-forward folds.

        Args:
            folds: Non-empty list of per-fold :class:`BacktestMetrics`.

        Returns:
            :class:`BacktestSummary` with mean metrics and the full folds tuple.
        """
        return BacktestSummary(
            n_folds=len(folds),
            mean_sharpe=float(np.mean([f.sharpe_ratio for f in folds])),
            mean_win_rate=float(np.mean([f.win_rate for f in folds])),
            mean_profit_factor=float(np.mean([f.profit_factor for f in folds])),
            mean_max_drawdown=float(np.mean([f.max_drawdown for f in folds])),
            mean_total_return=float(np.mean([f.total_return for f in folds])),
            folds=tuple(folds),
        )
