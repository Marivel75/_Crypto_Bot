"""ML rule engine for crypto trading signal generation.

Phase 1: Rule-based engine using RSI, Bollinger Bands, harmonic patterns, and trend analysis.
Phase 2: Supervised ML models (XGBoost, LightGBM, LSTM) learning from Phase 1 patterns.
"""

from __future__ import annotations

from src.ml.rules.engine import RuleEngine
from src.ml.signal_generator import SignalGenerator

__all__ = [
    "RuleEngine",
    "SignalGenerator",
]
