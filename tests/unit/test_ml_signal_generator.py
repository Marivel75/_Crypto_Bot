"""Unit tests for SignalGenerator."""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.ml.signal_generator import SignalGenerator
from src.shared.models.signal import TradingSignal

# ---------------------------------------------------------------------------
# Fake rule engine and predictor
# ---------------------------------------------------------------------------


class FakeRuleEngine:
    """Fake rule engine returning a configurable result dict."""

    def __init__(self, result: dict[str, Any] | None = None) -> None:
        self._result = result or {}

    def evaluate(self, symbol: str, indicators: dict[str, Any]) -> dict[str, Any]:
        return self._result


class FakePredictor:
    """Fake ML predictor."""

    def __init__(self, direction: str = "BUY", confidence: float = 0.85) -> None:
        self._direction = direction
        self._confidence = confidence

    def predict(self, features: Any) -> list[dict[str, Any]]:
        return [{"direction": self._direction, "confidence": self._confidence}]


# ---------------------------------------------------------------------------
# Confidence gate tests
# ---------------------------------------------------------------------------


class TestConfidenceGate:
    def test_signal_emitted_when_confidence_above_threshold(self) -> None:
        engine = FakeRuleEngine(
            {
                "direction": "BUY",
                "confidence": 0.75,
                "rules_triggered": ["rsi_oversold"],
                "timeframe": "4h",
            }
        )
        gen = SignalGenerator(rule_engine=engine)
        signal = gen.generate("BTCUSDT", {})
        assert signal is not None
        assert isinstance(signal, TradingSignal)
        assert signal.signal_type == "BUY"
        assert signal.confidence_score >= Decimal("0.6")

    def test_signal_suppressed_when_confidence_below_threshold(self) -> None:
        engine = FakeRuleEngine({"direction": "BUY", "confidence": 0.3, "rules_triggered": []})
        gen = SignalGenerator(rule_engine=engine)
        signal = gen.generate("BTCUSDT", {})
        assert signal is None

    def test_hold_direction_returns_none(self) -> None:
        engine = FakeRuleEngine({"direction": "HOLD", "confidence": 0.9})
        gen = SignalGenerator(rule_engine=engine)
        signal = gen.generate("BTCUSDT", {})
        assert signal is None

    def test_empty_rule_result_returns_none(self) -> None:
        engine = FakeRuleEngine({})
        gen = SignalGenerator(rule_engine=engine)
        signal = gen.generate("BTCUSDT", {})
        assert signal is None


# ---------------------------------------------------------------------------
# ML blending tests
# ---------------------------------------------------------------------------


class TestMLBlending:
    def test_ml_agreement_boosts_confidence(self) -> None:
        engine = FakeRuleEngine(
            {
                "direction": "BUY",
                "confidence": 0.7,
                "rules_triggered": ["rsi_oversold"],
                "timeframe": "4h",
            }
        )
        predictor = FakePredictor(direction="BUY", confidence=0.9)
        gen = SignalGenerator(rule_engine=engine, predictor=predictor)
        signal = gen.generate("BTCUSDT", {"rsi_4h": 25.0})
        assert signal is not None
        # Blended: 0.6*0.9 + 0.4*0.7 = 0.82
        assert signal.confidence_score >= Decimal("0.7")

    def test_ml_disagreement_penalises(self) -> None:
        engine = FakeRuleEngine(
            {
                "direction": "BUY",
                "confidence": 0.7,
                "rules_triggered": ["rsi_oversold"],
                "timeframe": "4h",
            }
        )
        predictor = FakePredictor(direction="SELL", confidence=0.8)
        gen = SignalGenerator(rule_engine=engine, predictor=predictor)
        signal = gen.generate("BTCUSDT", {"rsi_4h": 25.0})
        # Conflicting signals → heavy penalty → likely below threshold
        assert signal is None


# ---------------------------------------------------------------------------
# Leverage suggestion tests
# ---------------------------------------------------------------------------


class TestLeverageSuggestion:
    def test_high_confidence_suggests_leverage_20(self) -> None:
        engine = FakeRuleEngine(
            {
                "direction": "BUY",
                "confidence": 0.92,
                "rules_triggered": ["rsi_oversold"],
            }
        )
        gen = SignalGenerator(rule_engine=engine)
        signal = gen.generate("BTCUSDT", {})
        assert signal is not None
        assert signal.leverage_suggested == 20

    def test_medium_confidence_suggests_leverage_10(self) -> None:
        engine = FakeRuleEngine(
            {
                "direction": "BUY",
                "confidence": 0.78,
                "rules_triggered": ["rsi_oversold"],
            }
        )
        gen = SignalGenerator(rule_engine=engine)
        signal = gen.generate("BTCUSDT", {})
        assert signal is not None
        assert signal.leverage_suggested == 10

    def test_low_confidence_suggests_leverage_5(self) -> None:
        engine = FakeRuleEngine(
            {
                "direction": "SELL",
                "confidence": 0.68,
                "rules_triggered": ["bollinger_breakout"],
            }
        )
        gen = SignalGenerator(rule_engine=engine)
        signal = gen.generate("BTCUSDT", {})
        assert signal is not None
        assert signal.leverage_suggested == 5

    def test_borderline_confidence_no_leverage(self) -> None:
        engine = FakeRuleEngine(
            {
                "direction": "BUY",
                "confidence": 0.62,
                "rules_triggered": ["rsi_oversold"],
            }
        )
        gen = SignalGenerator(rule_engine=engine)
        signal = gen.generate("BTCUSDT", {})
        assert signal is not None
        assert signal.leverage_suggested is None


# ---------------------------------------------------------------------------
# News sentiment adjustment tests
# ---------------------------------------------------------------------------


class TestNewsSentiment:
    def test_positive_sentiment_boosts_buy_signal(self) -> None:
        engine = FakeRuleEngine(
            {
                "direction": "BUY",
                "confidence": 0.7,
                "rules_triggered": ["rsi_oversold"],
            }
        )
        gen = SignalGenerator(rule_engine=engine)
        signal_no_news = gen.generate("BTCUSDT", {})
        signal_with_news = gen.generate("BTCUSDT", {}, news_sentiment=1.0)
        assert signal_no_news is not None
        assert signal_with_news is not None
        assert signal_with_news.confidence_score >= signal_no_news.confidence_score

    def test_negative_sentiment_reduces_buy_signal(self) -> None:
        engine = FakeRuleEngine(
            {
                "direction": "BUY",
                "confidence": 0.7,
                "rules_triggered": ["rsi_oversold"],
            }
        )
        gen = SignalGenerator(rule_engine=engine)
        signal_no_news = gen.generate("BTCUSDT", {})
        signal_with_news = gen.generate("BTCUSDT", {}, news_sentiment=-1.0)
        assert signal_no_news is not None
        assert signal_with_news is not None
        assert signal_with_news.confidence_score <= signal_no_news.confidence_score

    def test_sentiment_adjustment_capped_at_095(self) -> None:
        engine = FakeRuleEngine(
            {
                "direction": "BUY",
                "confidence": 0.94,
                "rules_triggered": ["rsi_oversold"],
            }
        )
        gen = SignalGenerator(rule_engine=engine)
        signal = gen.generate("BTCUSDT", {}, news_sentiment=1.0)
        assert signal is not None
        assert signal.confidence_score <= Decimal("0.95")


# ---------------------------------------------------------------------------
# save_signal (async) test
# ---------------------------------------------------------------------------


class TestFeeVerification:
    def test_estimate_fees_returns_base_rate(self) -> None:
        # 0.02% + 0.05% + 0.10% = 0.17%
        fees = SignalGenerator._estimate_fees(leverage=10)
        assert fees == Decimal("0.0017")

    def test_estimate_fees_same_regardless_of_leverage(self) -> None:
        assert SignalGenerator._estimate_fees(5) == SignalGenerator._estimate_fees(20)

    def test_verify_fees_passes_at_high_confidence(self) -> None:
        fees = Decimal("0.0017")
        assert SignalGenerator._verify_fees(Decimal("0.8"), fees) is True

    def test_verify_fees_fails_at_very_low_confidence(self) -> None:
        fees = Decimal("0.0017")
        # expected gain = 0.2 * 0.01 = 0.002; 50% = 0.001 < 0.0017 → fail
        assert SignalGenerator._verify_fees(Decimal("0.2"), fees) is False

    def test_signal_includes_fees_estimated(self) -> None:
        engine = FakeRuleEngine(
            {
                "direction": "BUY",
                "confidence": 0.75,
                "rules_triggered": ["rsi_oversold"],
            }
        )
        gen = SignalGenerator(rule_engine=engine)
        signal = gen.generate("BTCUSDT", {})
        assert signal is not None
        assert signal.fees_estimated is not None
        assert signal.fees_estimated > Decimal("0")


# ---------------------------------------------------------------------------
# Margin safety tests
# ---------------------------------------------------------------------------


class TestMarginSafety:
    def test_margin_safety_5x_leverage(self) -> None:
        # 5x → box 20% → margin = 2 * 20% = 40%
        margin = SignalGenerator._compute_margin_safety(5)
        assert margin == Decimal("0.4")

    def test_margin_safety_10x_leverage(self) -> None:
        margin = SignalGenerator._compute_margin_safety(10)
        assert margin == Decimal("0.2")

    def test_margin_safety_20x_leverage(self) -> None:
        margin = SignalGenerator._compute_margin_safety(20)
        assert margin == Decimal("0.1")

    def test_margin_safety_none_without_leverage(self) -> None:
        assert SignalGenerator._compute_margin_safety(None) is None

    def test_signal_includes_margin_safety(self) -> None:
        engine = FakeRuleEngine(
            {
                "direction": "BUY",
                "confidence": 0.78,
                "rules_triggered": ["rsi_oversold"],
            }
        )
        gen = SignalGenerator(rule_engine=engine)
        signal = gen.generate("BTCUSDT", {})
        assert signal is not None
        assert signal.leverage_suggested == 10
        assert signal.margin_safety == Decimal("0.2")


# ---------------------------------------------------------------------------
# save_signal (async) test
# ---------------------------------------------------------------------------


class TestSaveSignal:
    @pytest.mark.asyncio
    async def test_save_signal_calls_session_add(self) -> None:
        engine = FakeRuleEngine(
            {
                "direction": "BUY",
                "confidence": 0.8,
                "rules_triggered": ["rsi_oversold"],
            }
        )
        gen = SignalGenerator(rule_engine=engine)
        signal = gen.generate("BTCUSDT", {})
        assert signal is not None

        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.flush = AsyncMock()

        await gen.save_signal(mock_session, signal)
        mock_session.add.assert_called_once()
        mock_session.flush.assert_awaited_once()
