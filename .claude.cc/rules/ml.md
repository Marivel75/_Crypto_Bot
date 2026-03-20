# ML / Data Science Rules

## Scope: `src/ml/`

## Modeling
- Phase 1: Rule-based engine with explicit thresholds from `config/indicators.yaml`
- Phase 2: Supervised ML (XGBoost, LightGBM, LSTM) learning patterns from Phase 1
- NEVER predict absolute prices — predict returns or direction
- Train/validation/test split MUST be temporal (not random)
- Walk-forward backtesting with purging and embargo windows

## Signals
- Every signal must include: symbol, timeframe, direction, confidence, SL, TP
- Confidence threshold for emission: >= 0.6
- Always verify leverage suggestion against 2x margin rule
- Log all generated signals with full indicator context

## MLOps
- Track ALL experiments in MLflow (params, metrics, artifacts)
- Version datasets with DVC
- Store model artifacts in MinIO (`models/` bucket)
- Monitor for concept drift (compare rolling metrics)
- Retrain trigger: weekly or on detected drift

## Indicators (multi-timeframe)
- RSI: convergence across adjacent TFs (1h, 2h, 3h, 4h)
- Bollinger Bands: squeeze detection, band walking
- Harmonic patterns: bat, gartley, butterfly, crab
- Trend lines: weekly (stable) vs monthly (aggressive)

## DO NOT
- Import from `src/api/` or `src/frontend/`
- Connect to external APIs directly (data comes from TimescaleDB)
- Use random train/test splits on time-series data
- Use deprecated RL algorithms (Monte Carlo, tabular Q-learning)
