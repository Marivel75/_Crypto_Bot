"""Unit tests for SignalGenerator — rules-only mode, ML blend, news sentiment."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from src.ml.signal_generator import SignalGenerator
from src.shared.constants import SIGNAL_CONFIDENCE_THRESHOLD

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_rule_engine(
    direction: str = "BUY",
    confidence: float = 0.80,
    rules: list[str] | None = None,
    timeframe: str = "4h",
) -> MagicMock:
    """Return a mock rule engine that returns a fixed evaluate dict."""
    engine = MagicMock()
    engine.evaluate.return_value = {
        "direction": direction,
        "confidence": confidence,
        "rules_triggered": rules or ["rsi_oversold_multi_tf"],
        "timeframe": timeframe,
        "timeframes_aligned": {},
    }
    return engine


def _make_hold_engine() -> MagicMock:
    engine = MagicMock()
    engine.evaluate.return_value = {
        "direction": "HOLD",
        "confidence": 0.5,
        "rules_triggered": [],
        "timeframe": "4h",
        "timeframes_aligned": {},
    }
    return engine


def _make_low_confidence_engine() -> MagicMock:
    engine = MagicMock()
    engine.evaluate.return_value = {
        "direction": "BUY",
        "confidence": 0.3,  # below threshold
        "rules_triggered": ["rsi_weak"],
        "timeframe": "1h",
        "timeframes_aligned": {},
    }
    return engine


# ---------------------------------------------------------------------------
# Rules-only mode
# ---------------------------------------------------------------------------


class TestSignalGeneratorRulesOnly:
    def test_strong_buy_signal_emitted(self) -> None:
        engine = _make_rule_engine(direction="BUY", confidence=0.80)
        gen = SignalGenerator(rule_engine=engine)

        signal = gen.generate("BTCUSDT", indicators={})

        assert signal is not None
        assert signal.signal_type == "BUY"
        assert signal.confidence_score >= SIGNAL_CONFIDENCE_THRESHOLD

    def test_strong_sell_signal_emitted(self) -> None:
        engine = _make_rule_engine(direction="SELL", confidence=0.75)
        gen = SignalGenerator(rule_engine=engine)

        signal = gen.generate("ETHUSDT", indicators={})

        assert signal is not None
        assert signal.signal_type == "SELL"

    def test_hold_direction_suppressed(self) -> None:
        gen = SignalGenerator(rule_engine=_make_hold_engine())
        signal = gen.generate("BTCUSDT", indicators={})
        assert signal is None

    def test_low_confidence_returns_none(self) -> None:
        gen = SignalGenerator(rule_engine=_make_low_confidence_engine())
        signal = gen.generate("BTCUSDT", indicators={})
        assert signal is None

    def test_signal_has_correct_symbol(self) -> None:
        engine = _make_rule_engine(direction="BUY", confidence=0.85)
        gen = SignalGenerator(rule_engine=engine)
        signal = gen.generate("SOLUSDT", indicators={})
        assert signal is not None
        assert signal.symbol == "SOLUSDT"

    def test_signal_model_version_is_rules_v1(self) -> None:
        engine = _make_rule_engine(direction="BUY", confidence=0.85)
        gen = SignalGenerator(rule_engine=engine)
        signal = gen.generate("BTCUSDT", indicators={})
        assert signal is not None
        assert signal.model_version == "rules_v1"

    def test_signal_timeframe_primary_from_engine(self) -> None:
        engine = _make_rule_engine(direction="BUY", confidence=0.80, timeframe="4h")
        gen = SignalGenerator(rule_engine=engine)
        signal = gen.generate("BTCUSDT", indicators={})
        assert signal is not None
        assert signal.timeframe_primary == "4h"

    def test_confidence_exactly_at_threshold_is_emitted(self) -> None:
        engine = _make_rule_engine(direction="BUY", confidence=0.60)
        gen = SignalGenerator(rule_engine=engine)
        signal = gen.generate("BTCUSDT", indicators={})
        assert signal is not None

    def test_confidence_just_below_threshold_returns_none(self) -> None:
        engine = _make_rule_engine(direction="BUY", confidence=0.5999)
        gen = SignalGenerator(rule_engine=engine)
        signal = gen.generate("BTCUSDT", indicators={})
        assert signal is None

    def test_rules_triggered_propagated(self) -> None:
        rules = ["rsi_oversold_multi_tf", "bollinger_lower_bounce"]
        engine = _make_rule_engine(direction="BUY", confidence=0.80, rules=rules)
        gen = SignalGenerator(rule_engine=engine)
        signal = gen.generate("BTCUSDT", indicators={})
        assert signal is not None
        assert signal.rules_triggered == rules

    def test_rule_engine_exception_returns_none(self) -> None:
        engine = MagicMock()
        engine.evaluate.side_effect = RuntimeError("engine crashed")
        gen = SignalGenerator(rule_engine=engine)
        signal = gen.generate("BTCUSDT", indicators={})
        assert signal is None


# ---------------------------------------------------------------------------
# Leverage suggestion
# ---------------------------------------------------------------------------


class TestSuggestLeverage:
    def test_confidence_85_suggests_20x(self) -> None:
        engine = _make_rule_engine(direction="BUY", confidence=0.85)
        gen = SignalGenerator(rule_engine=engine)
        signal = gen.generate("BTCUSDT", indicators={})
        assert signal is not None
        assert signal.leverage_suggested == 20

    def test_confidence_75_suggests_10x(self) -> None:
        engine = _make_rule_engine(direction="BUY", confidence=0.75)
        gen = SignalGenerator(rule_engine=engine)
        signal = gen.generate("BTCUSDT", indicators={})
        assert signal is not None
        assert signal.leverage_suggested == 10

    def test_confidence_65_suggests_5x(self) -> None:
        engine = _make_rule_engine(direction="BUY", confidence=0.65)
        gen = SignalGenerator(rule_engine=engine)
        signal = gen.generate("BTCUSDT", indicators={})
        assert signal is not None
        assert signal.leverage_suggested == 5

    def test_confidence_exactly_60_no_leverage(self) -> None:
        engine = _make_rule_engine(direction="BUY", confidence=0.60)
        gen = SignalGenerator(rule_engine=engine)
        signal = gen.generate("BTCUSDT", indicators={})
        assert signal is not None
        assert signal.leverage_suggested is None


# ---------------------------------------------------------------------------
# News sentiment adjustment
# ---------------------------------------------------------------------------


class TestNewsSentimentAdjustment:
    def test_positive_sentiment_increases_buy_confidence(self) -> None:
        base_confidence = 0.70
        engine = _make_rule_engine(direction="BUY", confidence=base_confidence)
        gen = SignalGenerator(rule_engine=engine)

        signal_no_sentiment = gen.generate("BTCUSDT", indicators={})
        signal_with_sentiment = gen.generate("BTCUSDT", indicators={}, news_sentiment=1.0)

        assert signal_no_sentiment is not None
        assert signal_with_sentiment is not None
        assert signal_with_sentiment.confidence_score >= signal_no_sentiment.confidence_score

    def test_negative_sentiment_decreases_buy_confidence(self) -> None:
        base_confidence = 0.80
        engine = _make_rule_engine(direction="BUY", confidence=base_confidence)
        gen = SignalGenerator(rule_engine=engine)

        signal_no_sentiment = gen.generate("BTCUSDT", indicators={})
        signal_neg_sentiment = gen.generate("BTCUSDT", indicators={}, news_sentiment=-1.0)

        assert signal_no_sentiment is not None
        if signal_neg_sentiment is not None:
            assert signal_neg_sentiment.confidence_score <= signal_no_sentiment.confidence_score

    def test_sentiment_adjustment_capped_at_095(self) -> None:
        engine = _make_rule_engine(direction="BUY", confidence=0.95)
        gen = SignalGenerator(rule_engine=engine)
        signal = gen.generate("BTCUSDT", indicators={}, news_sentiment=1.0)
        assert signal is not None
        assert signal.confidence_score <= Decimal("0.95")

    def test_none_sentiment_has_no_effect(self) -> None:
        base_confidence = 0.75
        engine1 = _make_rule_engine(direction="BUY", confidence=base_confidence)
        engine2 = _make_rule_engine(direction="BUY", confidence=base_confidence)
        gen1 = SignalGenerator(rule_engine=engine1)
        gen2 = SignalGenerator(rule_engine=engine2)

        sig1 = gen1.generate("BTCUSDT", indicators={})
        sig2 = gen2.generate("BTCUSDT", indicators={}, news_sentiment=None)

        assert sig1 is not None
        assert sig2 is not None
        assert sig1.confidence_score == sig2.confidence_score


# ---------------------------------------------------------------------------
# ML blend mode
# ---------------------------------------------------------------------------


class TestSignalGeneratorMLBlend:
    def _make_predictor(self, direction: str, confidence: float) -> MagicMock:
        predictor = MagicMock()
        predictor.predict.return_value = [{"direction": direction, "confidence": confidence}]
        return predictor

    def test_ml_agreeing_blends_confidence(self) -> None:
        engine = _make_rule_engine(direction="BUY", confidence=0.70)
        predictor = self._make_predictor(direction="BUY", confidence=0.80)
        gen = SignalGenerator(rule_engine=engine, predictor=predictor)

        signal = gen.generate("BTCUSDT", indicators={"rsi": 25.0})
        assert signal is not None
        # Blended = 0.6*0.80 + 0.4*0.70 = 0.48 + 0.28 = 0.76
        assert signal.confidence_score == pytest.approx(Decimal("0.76"), abs=Decimal("0.01"))

    def test_ml_conflicting_penalises_confidence(self) -> None:
        engine = _make_rule_engine(direction="BUY", confidence=0.80)
        predictor = self._make_predictor(direction="SELL", confidence=0.80)
        gen = SignalGenerator(rule_engine=engine, predictor=predictor)

        signal = gen.generate("BTCUSDT", indicators={"rsi": 25.0})
        # Penalised: 0.4 * min(0.80, 0.80) = 0.32 → below threshold → None
        assert signal is None

    def test_ml_model_version_used_when_predictor_available(self) -> None:
        engine = _make_rule_engine(direction="BUY", confidence=0.80)
        predictor = self._make_predictor(direction="BUY", confidence=0.85)
        gen = SignalGenerator(rule_engine=engine, predictor=predictor)

        signal = gen.generate("BTCUSDT", indicators={"rsi": 25.0})
        assert signal is not None
        assert signal.model_version == "xgboost_v2"
