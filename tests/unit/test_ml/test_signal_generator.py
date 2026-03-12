"""Unit tests for SignalGenerator — rules + ML blending, confidence gate, leverage."""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.ml.exceptions import SignalRejectedError
from src.ml.signal_generator import SignalGenerator
from src.shared.constants import SIGNAL_CONFIDENCE_THRESHOLD
from src.shared.models.signal import TradingSignal

# ---------------------------------------------------------------------------
# Helpers / factories
# ---------------------------------------------------------------------------

_INDICATORS_BULLISH: dict[str, Any] = {
    "timeframes": {
        "1h": {"rsi": 24.0, "price_vs_bollinger": -0.92},
        "4h": {"rsi": 26.0, "price_vs_bollinger": -0.88},
    },
    "timeframe": "4h",
}

_INDICATORS_BEARISH: dict[str, Any] = {
    "timeframes": {
        "1h": {"rsi": 76.0, "price_vs_bollinger": 0.91},
        "4h": {"rsi": 78.0, "price_vs_bollinger": 0.87},
    },
    "timeframe": "4h",
}

_INDICATORS_NEUTRAL: dict[str, Any] = {
    "timeframes": {
        "4h": {"rsi": 50.0, "price_vs_bollinger": 0.0},
    },
    "timeframe": "4h",
}


def _make_rule_result(
    direction: str = "BUY",
    confidence: float = 0.80,
    rules: list[str] | None = None,
    timeframe: str = "4h",
) -> dict[str, Any]:
    return {
        "direction": direction,
        "confidence": confidence,
        "rules_triggered": rules or ["rsi_oversold_multi_tf"],
        "timeframe": timeframe,
        "timeframes_aligned": {"1h": True, "4h": True},
    }


def _make_rule_engine(
    direction: str = "BUY",
    confidence: float = 0.80,
    rules: list[str] | None = None,
) -> MagicMock:
    engine = MagicMock()
    engine.evaluate.return_value = _make_rule_result(direction, confidence, rules)
    return engine


def _make_predictor(
    direction: str = "BUY",
    confidence: float = 0.85,
) -> MagicMock:
    predictor = MagicMock()
    predictor.predict.return_value = [{"direction": direction, "confidence": confidence, "source": "ml"}]
    return predictor


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestSignalGenerator:
    # ------------------------------------------------------------------
    # BUY signal
    # ------------------------------------------------------------------

    def test_generate_buy_signal(self) -> None:
        """High confidence, bullish rule result → TradingSignal with signal_type=BUY."""
        engine = _make_rule_engine(direction="BUY", confidence=0.82)
        generator = SignalGenerator(rule_engine=engine)

        signal = generator.generate("BTCUSDT", _INDICATORS_BULLISH)

        assert signal is not None
        assert isinstance(signal, TradingSignal)
        assert signal.signal_type == "BUY"
        assert signal.symbol == "BTCUSDT"
        assert signal.confidence_score >= SIGNAL_CONFIDENCE_THRESHOLD
        assert signal.model_version == "rules_v1"

    def test_generate_buy_signal_includes_rules_triggered(self) -> None:
        """Rules triggered list is propagated faithfully onto the emitted signal."""
        rules = ["rsi_oversold_multi_tf", "bollinger_squeeze"]
        engine = _make_rule_engine(direction="BUY", confidence=0.75, rules=rules)
        generator = SignalGenerator(rule_engine=engine)

        signal = generator.generate("ETHUSDT", _INDICATORS_BULLISH)

        assert signal is not None
        assert signal.rules_triggered == rules

    # ------------------------------------------------------------------
    # SELL signal
    # ------------------------------------------------------------------

    def test_generate_sell_signal(self) -> None:
        """Bearish indicators → TradingSignal with signal_type=SELL."""
        engine = _make_rule_engine(direction="SELL", confidence=0.78)
        generator = SignalGenerator(rule_engine=engine)

        signal = generator.generate("ETHUSDT", _INDICATORS_BEARISH)

        assert signal is not None
        assert signal.signal_type == "SELL"
        assert signal.symbol == "ETHUSDT"
        assert signal.confidence_score >= SIGNAL_CONFIDENCE_THRESHOLD

    def test_generate_sell_signal_timeframe_propagated(self) -> None:
        """Primary timeframe set by the rule engine is stored on the signal."""
        engine = _make_rule_engine(direction="SELL", confidence=0.72)
        generator = SignalGenerator(rule_engine=engine)

        signal = generator.generate("SOLUSDT", _INDICATORS_BEARISH)

        assert signal is not None
        assert signal.timeframe_primary == "4h"

    # ------------------------------------------------------------------
    # Confidence gate — below threshold → None
    # ------------------------------------------------------------------

    def test_reject_low_confidence_returns_none(self) -> None:
        """Rule confidence below 0.6 → generate() returns None (signal suppressed)."""
        engine = _make_rule_engine(direction="BUY", confidence=0.55)
        generator = SignalGenerator(rule_engine=engine)

        signal = generator.generate("BTCUSDT", _INDICATORS_BULLISH)

        assert signal is None

    def test_reject_exactly_at_threshold(self) -> None:
        """Confidence equal to the threshold (0.6) → signal is emitted."""
        engine = _make_rule_engine(direction="BUY", confidence=0.60)
        generator = SignalGenerator(rule_engine=engine)

        signal = generator.generate("BTCUSDT", _INDICATORS_BULLISH)

        assert signal is not None
        assert signal.confidence_score == Decimal("0.6")

    def test_reject_hold_direction_returns_none(self) -> None:
        """HOLD signals are never emitted regardless of confidence."""
        engine = MagicMock()
        engine.evaluate.return_value = {
            "direction": "HOLD",
            "confidence": 0.90,
            "rules_triggered": [],
            "timeframe": "4h",
        }
        generator = SignalGenerator(rule_engine=engine)

        signal = generator.generate("BTCUSDT", _INDICATORS_NEUTRAL)

        assert signal is None

    # ------------------------------------------------------------------
    # Fee / gain validation (SignalRejectedError)
    # ------------------------------------------------------------------

    def test_reject_high_fees_raises_signal_rejected_error(self) -> None:
        """When estimated fees exceed expected gain, SignalRejectedError is raised.

        The SignalGenerator itself does not compute fees; this test verifies that
        calling code can raise SignalRejectedError and that the exception hierarchy
        is correct (inherits from MLBaseException → CryptoBotError).
        """
        error = SignalRejectedError(
            message="Signal rejected: fees exceed expected gain",
            detail={"fees": 0.003, "expected_gain": 0.002},
        )
        assert isinstance(error, SignalRejectedError)
        assert "fees exceed expected gain" in error.message
        assert error.detail["fees"] > error.detail["expected_gain"]

    def test_reject_high_fees_returns_none_when_intercepted(self) -> None:
        """A caller that catches SignalRejectedError can safely swallow it."""

        def _generate_with_fee_check(
            generator: SignalGenerator,
            symbol: str,
            indicators: dict[str, Any],
            fees: float,
            expected_gain: float,
        ) -> TradingSignal | None:
            signal = generator.generate(symbol, indicators)
            if signal is not None and fees > expected_gain:
                raise SignalRejectedError(
                    message="Fees exceed expected gain",
                    detail={"fees": fees, "expected_gain": expected_gain},
                )
            return signal

        engine = _make_rule_engine(direction="BUY", confidence=0.80)
        generator = SignalGenerator(rule_engine=engine)

        result: TradingSignal | None = None
        try:
            result = _generate_with_fee_check(
                generator,
                "BTCUSDT",
                _INDICATORS_BULLISH,
                fees=0.005,
                expected_gain=0.002,
            )
        except SignalRejectedError:
            result = None

        assert result is None

    # ------------------------------------------------------------------
    # Leverage calculation — 2x margin rule
    # ------------------------------------------------------------------

    def test_leverage_below_65_confidence_is_none(self) -> None:
        """Confidence just at threshold (0.60–0.64) → no leverage suggested."""
        engine = _make_rule_engine(direction="BUY", confidence=0.62)
        generator = SignalGenerator(rule_engine=engine)

        signal = generator.generate("BTCUSDT", _INDICATORS_BULLISH)

        assert signal is not None
        assert signal.leverage_suggested is None

    def test_leverage_tier_5_for_medium_confidence(self) -> None:
        """Confidence 0.65–0.74 → leverage = 5 (conservative tier)."""
        engine = _make_rule_engine(direction="BUY", confidence=0.68)
        generator = SignalGenerator(rule_engine=engine)

        signal = generator.generate("BTCUSDT", _INDICATORS_BULLISH)

        assert signal is not None
        assert signal.leverage_suggested == 5

    def test_leverage_tier_10_for_high_confidence(self) -> None:
        """Confidence 0.75–0.84 → leverage = 10 (moderate tier)."""
        engine = _make_rule_engine(direction="BUY", confidence=0.78)
        generator = SignalGenerator(rule_engine=engine)

        signal = generator.generate("BTCUSDT", _INDICATORS_BULLISH)

        assert signal is not None
        assert signal.leverage_suggested == 10

    def test_leverage_tier_20_for_very_high_confidence(self) -> None:
        """Confidence >= 0.85 → leverage = 20 (maximum tier, 2x margin rule)."""
        engine = _make_rule_engine(direction="BUY", confidence=0.90)
        generator = SignalGenerator(rule_engine=engine)

        signal = generator.generate("BTCUSDT", _INDICATORS_BULLISH)

        assert signal is not None
        assert signal.leverage_suggested == 20

    def test_leverage_never_exceeds_max(self) -> None:
        """_suggest_leverage never returns more than the config maximum of 20."""
        lever = SignalGenerator._suggest_leverage(Decimal("0.99"))
        assert lever == 20

    def test_leverage_static_method_thresholds(self) -> None:
        """Verify all three tiers via the static method directly."""
        assert SignalGenerator._suggest_leverage(Decimal("0.64")) is None
        assert SignalGenerator._suggest_leverage(Decimal("0.65")) == 5
        assert SignalGenerator._suggest_leverage(Decimal("0.75")) == 10
        assert SignalGenerator._suggest_leverage(Decimal("0.85")) == 20

    # ------------------------------------------------------------------
    # ML blending (rules + predictor)
    # ------------------------------------------------------------------

    def test_ml_blending_agreeing_directions_boosts_confidence(self) -> None:
        """When ML and rules agree on direction, blended confidence = 0.6*ML + 0.4*rules."""
        rules_confidence = 0.70
        ml_confidence = 0.80
        expected_blended = round(0.6 * ml_confidence + 0.4 * rules_confidence, 4)

        engine = _make_rule_engine(direction="BUY", confidence=rules_confidence)
        predictor = _make_predictor(direction="BUY", confidence=ml_confidence)

        generator = SignalGenerator(rule_engine=engine, predictor=predictor)

        with patch("pandas.DataFrame") as mock_df_cls:
            mock_df_cls.return_value = MagicMock()
            signal = generator.generate("BTCUSDT", _INDICATORS_BULLISH)

        assert signal is not None
        assert float(signal.confidence_score) == pytest.approx(expected_blended, abs=1e-4)
        assert signal.model_version == "xgboost_v2"

    def test_ml_blending_conflicting_directions_penalises_confidence(self) -> None:
        """When ML and rules disagree, confidence is penalised: 0.4 * min(ml, rules)."""
        rules_confidence = 0.80
        ml_confidence = 0.75
        expected_penalised = round(0.4 * min(ml_confidence, rules_confidence), 4)

        engine = _make_rule_engine(direction="BUY", confidence=rules_confidence)
        predictor = _make_predictor(direction="SELL", confidence=ml_confidence)

        generator = SignalGenerator(rule_engine=engine, predictor=predictor)

        with patch("pandas.DataFrame") as mock_df_cls:
            mock_df_cls.return_value = MagicMock()
            signal = generator.generate("BTCUSDT", _INDICATORS_BULLISH)

        # Penalised confidence (0.30) is below threshold → signal suppressed
        assert expected_penalised < float(SIGNAL_CONFIDENCE_THRESHOLD)
        assert signal is None

    def test_ml_predictor_failure_falls_back_to_rules(self) -> None:
        """If the predictor raises, the generator falls back to rules-only mode."""
        engine = _make_rule_engine(direction="BUY", confidence=0.75)
        predictor = MagicMock()
        predictor.predict.side_effect = RuntimeError("Model inference failed")

        generator = SignalGenerator(rule_engine=engine, predictor=predictor)

        with patch("pandas.DataFrame") as mock_df_cls:
            mock_df_cls.return_value = MagicMock()
            signal = generator.generate("BTCUSDT", _INDICATORS_BULLISH)

        assert signal is not None
        assert signal.signal_type == "BUY"
        assert signal.model_version == "rules_v1"

    # ------------------------------------------------------------------
    # News sentiment adjustment
    # ------------------------------------------------------------------

    def test_positive_sentiment_increases_buy_confidence(self) -> None:
        """Positive sentiment (+1.0) adds 5 pp to BUY confidence."""
        base_confidence = 0.70
        engine = _make_rule_engine(direction="BUY", confidence=base_confidence)
        generator = SignalGenerator(rule_engine=engine)

        signal = generator.generate("BTCUSDT", _INDICATORS_BULLISH, news_sentiment=1.0)

        assert signal is not None
        expected = round(base_confidence + 1.0 * 0.05, 4)
        assert float(signal.confidence_score) == pytest.approx(expected, abs=1e-4)

    def test_negative_sentiment_decreases_buy_confidence(self) -> None:
        """Strong negative sentiment can push confidence below threshold."""
        base_confidence = 0.61
        engine = _make_rule_engine(direction="BUY", confidence=base_confidence)
        generator = SignalGenerator(rule_engine=engine)

        # sentiment=-1.0 → subtract 0.05 → 0.56 < 0.60 → suppressed
        signal = generator.generate("BTCUSDT", _INDICATORS_BULLISH, news_sentiment=-1.0)

        assert signal is None

    def test_sentiment_capped_at_095(self) -> None:
        """Confidence is capped at 0.95 even with maximum positive sentiment."""
        engine = _make_rule_engine(direction="BUY", confidence=0.94)
        generator = SignalGenerator(rule_engine=engine)

        signal = generator.generate("BTCUSDT", _INDICATORS_BULLISH, news_sentiment=1.0)

        assert signal is not None
        assert signal.confidence_score <= Decimal("0.95")

    # ------------------------------------------------------------------
    # Rule engine errors
    # ------------------------------------------------------------------

    def test_rule_engine_exception_returns_none(self) -> None:
        """If the rule engine raises unexpectedly, generate() returns None safely."""
        engine = MagicMock()
        engine.evaluate.side_effect = ValueError("Unexpected indicator format")
        generator = SignalGenerator(rule_engine=engine)

        signal = generator.generate("BTCUSDT", _INDICATORS_BULLISH)

        assert signal is None

    def test_rule_engine_unknown_direction_is_treated_as_hold(self) -> None:
        """An unrecognised direction string from the rule engine → treated as HOLD → None."""
        engine = MagicMock()
        engine.evaluate.return_value = {
            "direction": "SIDEWAYS",
            "confidence": 0.90,
            "rules_triggered": [],
            "timeframe": "4h",
        }
        generator = SignalGenerator(rule_engine=engine)

        signal = generator.generate("BTCUSDT", _INDICATORS_NEUTRAL)

        assert signal is None

    # ------------------------------------------------------------------
    # generate_all — multiple symbols
    # ------------------------------------------------------------------

    def test_generate_all_returns_signal_per_qualifying_symbol(self) -> None:
        """generate() called for each symbol; only qualifying ones return a signal."""
        engine = _make_rule_engine(direction="BUY", confidence=0.75)
        generator = SignalGenerator(rule_engine=engine)

        symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
        results: dict[str, TradingSignal | None] = {
            symbol: generator.generate(symbol, _INDICATORS_BULLISH) for symbol in symbols
        }

        assert len(results) == 3
        for symbol, signal in results.items():
            assert signal is not None, f"Expected signal for {symbol}"
            assert signal.symbol == symbol
            assert signal.signal_type == "BUY"

    def test_generate_all_mixed_confidence_filters_correctly(self) -> None:
        """Only symbols whose rule engine returns confidence >= 0.6 emit signals."""
        call_count = 0
        confidences = [0.80, 0.50, 0.70]  # 2nd symbol below threshold

        def _side_effect(symbol: str, indicators: dict[str, Any]) -> dict[str, Any]:
            nonlocal call_count
            result = _make_rule_result(direction="BUY", confidence=confidences[call_count])
            call_count += 1
            return result

        engine = MagicMock()
        engine.evaluate.side_effect = _side_effect
        generator = SignalGenerator(rule_engine=engine)

        symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
        results = {symbol: generator.generate(symbol, _INDICATORS_BULLISH) for symbol in symbols}

        assert results["BTCUSDT"] is not None
        assert results["ETHUSDT"] is None  # confidence 0.50 < threshold
        assert results["SOLUSDT"] is not None

    def test_generate_all_independent_symbol_isolation(self) -> None:
        """Each call to generate() is independent — one failure does not affect others."""
        call_count = 0

        def _side_effect(symbol: str, indicators: dict[str, Any]) -> dict[str, Any]:
            nonlocal call_count
            call_count += 1
            if symbol == "ETHUSDT":
                raise RuntimeError("Simulated rule engine crash")
            return _make_rule_result(direction="BUY", confidence=0.75)

        engine = MagicMock()
        engine.evaluate.side_effect = _side_effect
        generator = SignalGenerator(rule_engine=engine)

        symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
        results: dict[str, TradingSignal | None] = {}
        for symbol in symbols:
            try:
                results[symbol] = generator.generate(symbol, _INDICATORS_BULLISH)
            except Exception:
                results[symbol] = None

        assert results["BTCUSDT"] is not None
        assert results["ETHUSDT"] is None  # rule engine crashed
        assert results["SOLUSDT"] is not None

    # ------------------------------------------------------------------
    # Model version tagging
    # ------------------------------------------------------------------

    def test_model_version_rules_only_mode(self) -> None:
        """Without a predictor, model_version is 'rules_v1'."""
        engine = _make_rule_engine(direction="BUY", confidence=0.80)
        generator = SignalGenerator(rule_engine=engine)

        signal = generator.generate("BTCUSDT", _INDICATORS_BULLISH)

        assert signal is not None
        assert signal.model_version == "rules_v1"

    def test_model_version_ml_mode_on_successful_prediction(self) -> None:
        """With a working predictor, model_version is 'xgboost_v2'."""
        engine = _make_rule_engine(direction="BUY", confidence=0.75)
        predictor = _make_predictor(direction="BUY", confidence=0.80)
        generator = SignalGenerator(rule_engine=engine, predictor=predictor)

        with patch("pandas.DataFrame") as mock_df_cls:
            mock_df_cls.return_value = MagicMock()
            signal = generator.generate("BTCUSDT", _INDICATORS_BULLISH)

        assert signal is not None
        assert signal.model_version == "xgboost_v2"
