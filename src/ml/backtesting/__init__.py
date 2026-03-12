"""Backtesting sub-package for walk-forward evaluation of trading signals.

Two implementations are available:

- :class:`Backtester` (``src.ml.models.backtester``) — strategy-protocol API;
  accepts an arbitrary ``Strategy`` object and drives fit/predict calls.
- :class:`WalkForwardBacktester` (``src.ml.backtesting.backtest_engine``) —
  signal-series API; accepts pre-computed signal and return series and
  computes Sharpe, max drawdown, win rate, and profit factor per fold.

Both enforce strict temporal splitting with purging and embargo windows.
"""

from __future__ import annotations

from src.ml.backtesting.backtest_engine import (
    BacktestMetrics,
    BacktestSummary,
    WalkForwardBacktester,
)
from src.ml.models.backtester import Backtester

__all__ = [
    "Backtester",
    "WalkForwardBacktester",
    "BacktestMetrics",
    "BacktestSummary",
]
