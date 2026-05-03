"""Schémas Pydantic pour les endpoints ML."""

from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel


class BacktestFoldResult(BaseModel):
    fold: int
    train_start: datetime
    train_end: datetime
    test_start: datetime
    test_end: datetime
    n_train: int
    n_test: int
    accuracy: float
    win_rate: float
    pnl: float
    sharpe: float
    profit_factor: float
    max_drawdown: float


class BacktestSummary(BaseModel):
    accuracy: float
    win_rate: float
    sharpe: float
    profit_factor: float
    max_drawdown: float
    total_pnl: float
    n_folds: int


class BacktestBaseline(BaseModel):
    strategy_pnl: float
    baseline_return: float
    excess_return: float
    sharpe: float


class BacktestResponse(BaseModel):
    symbol: str
    timeframe: str
    model_type: str
    train_window: int
    test_window: int
    n_candles: int
    folds: list[BacktestFoldResult]
    summary: BacktestSummary
    baseline: BacktestBaseline
