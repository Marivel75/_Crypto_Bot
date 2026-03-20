# ML / Data Science Team Context

You are working as the ML/Data Science agent for crypto-bot.

## Your Scope

- **Code**: `src/ml/`
- **Doc**: `docs/02-ml-data-science.md`
- **Commit scope**: `ml`
- **Do NOT touch**: `src/api/`, `src/etl/`, `src/frontend/`

## Architecture

```
src/ml/
  rules/               # rule_engine.py, rsi.py, bollinger.py, harmonics.py, trends.py
  models/              # xgboost_model.py, lgbm_model.py, lstm_model.py
  backtesting/         # walk_forward.py (with purging + embargo)
  signals/             # signal_generator.py, signal_validator.py
  mlflow_tracking.py   # experiment tracking utilities
  feature_store.py     # feature engineering pipeline
```

## Phase 1 — Rule Engine

- RSI multi-TF convergence: check RSI on 1h, 2h, 3h, 4h simultaneously
- Bollinger Bands: squeeze detection, band-walking signals
- Harmonic patterns: bat, gartley, butterfly, crab (Fibonacci ratios)
- Trend lines: weekly (stable) and monthly (aggressive)
- Emit signal only if `confidence >= 0.6`

## Phase 2 — Supervised ML

- Models: XGBoost, LightGBM, LSTM
- Target: predict direction/returns — NEVER absolute prices
- Features: technical indicators + cross-asset correlations
- Train/val/test split: temporal (chronological), never random
- Walk-forward backtesting with purging and embargo windows

## MLOps Rules

- Track ALL experiments in MLflow (params, metrics, artifacts)
- Version ALL datasets with DVC
- Store model artifacts in MinIO `models/` bucket
- Monitor for concept drift (rolling metric comparison)
- Retrain trigger: weekly schedule OR detected drift

## Signal Format

```python
Signal(
    symbol="BTCUSDT",
    timeframe="4h",
    direction="BUY",        # BUY | SELL | HOLD
    confidence=0.75,        # float 0.0-1.0, emit only >= 0.6
    entry_price=65000.0,
    stop_loss=62000.0,
    take_profit=[68000.0, 72000.0],
    leverage_suggested=2,   # always verify 2x margin rule
    indicators_used=["RSI_1h", "RSI_4h", "BB_squeeze"],
    timestamp=datetime.utcnow(),
)
```

## Backtesting Rules

- Walk-forward with purging: drop overlap between train/test
- Embargo: skip N bars after train period ends before test starts
- Metrics: Sharpe ratio, max drawdown, win rate, profit factor
- No lookahead bias — features must only use past data

## Workflow

1. Read `docs/02-ml-data-science.md` for full ML spec
2. Read `src/shared/models/Signal` to understand the signal contract
3. Data comes from TimescaleDB via repository — never call external APIs directly
4. Write tests with fixed timestamps and synthetic OHLCV data
5. Run: `ruff check src/ml/ && mypy src/ml/ && pytest tests/unit/test_ml/ -v`
