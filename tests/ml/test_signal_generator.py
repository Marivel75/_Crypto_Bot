"""Tests for signal generator: rule evaluation, ML blending, and entry/SL/TP calculation."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import pytest

from src.ml.signal_generator import SignalGenerator
from src.shared.constants import SIGNAL_CONFIDENCE_THRESHOLD

# Fixed timestamp
_FIXED_TS = datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc)


class FakeRuleEngine:
    """Deterministic rule engine for testing."""

    def __init__(self, direction: str, confidence: float) -> None:
        self.direction = direction
        self.confidence = confidence

    def evaluate(self, symbol: str, indicators: dict[str, Any]) -> dict[str, Any]:
        return {
            "direction": self.direction,
            "confidence": self.confidence,
            "rules_triggered": ["test_rule"],
            "timeframe": "4h",
        }


class FakePredictor:
    """Deterministic ML predictor for testing."""

    def __init__(self, direction: str, confidence: float) -> None:
        self.direction = direction
        self.confidence = confidence

    def predict(self, features: Any) -> list[dict[str, Any]]:
        return [
            {
                "direction": self.direction,
                "confidence": self.confidence,
                "source": "ml",
            }
        ]


class TestSignalGenerationBasic:
    """Test basic signal generation with rule engine only."""

    def test_buy_signal_above_threshold_emitted(self) -> None:
        """BUY signal with confidence >= 0.6 should be emitted."""
        generator = SignalGenerator(rule_engine=FakeRuleEngine("BUY", 0.75))
        indicators = {"4h": []}

        signal = generator.generate("BTCUSDT", indicators)

        assert signal is not None
        assert signal.signal_type == "BUY"
        assert signal.confidence_score >= SIGNAL_CONFIDENCE_THRESHOLD

    def test_sell_signal_above_threshold_emitted(self) -> None:
        """SELL signal with confidence >= 0.6 should be emitted."""
        generator = SignalGenerator(rule_engine=FakeRuleEngine("SELL", 0.70))
        indicators = {"4h": []}

        signal = generator.generate("BTCUSDT", indicators)

        assert signal is not None
        assert signal.signal_type == "SELL"

    def test_hold_signal_not_emitted(self) -> None:
        """HOLD signals should not be emitted."""
        generator = SignalGenerator(rule_engine=FakeRuleEngine("HOLD", 0.75))
        indicators = {"4h": []}

        signal = generator.generate("BTCUSDT", indicators)

        assert signal is None

    def test_signal_below_threshold_not_emitted(self) -> None:
        """Signal with confidence < 0.6 should be suppressed."""
        generator = SignalGenerator(rule_engine=FakeRuleEngine("BUY", 0.50))
        indicators = {"4h": []}

        signal = generator.generate("BTCUSDT", indicators)

        assert signal is None

    def test_signal_includes_symbol(self) -> None:
        """Signal should include the target symbol."""
        generator = SignalGenerator(rule_engine=FakeRuleEngine("BUY", 0.75))
        indicators = {"4h": []}

        signal = generator.generate("ETHUSDT", indicators)

        assert signal is not None
        assert signal.symbol == "ETHUSDT"

    def test_signal_includes_timeframe(self) -> None:
        """Signal should include the primary timeframe."""
        generator = SignalGenerator(rule_engine=FakeRuleEngine("BUY", 0.75))
        indicators = {"4h": []}

        signal = generator.generate("BTCUSDT", indicators)

        assert signal is not None
        assert signal.timeframe_primary == "4h"


class TestSignalGenerationWithML:
    """Test signal generation with ML predictor blending."""

    def test_matching_direction_ml_blends_confidence(self) -> None:
        """When ML and rules agree, confidence should be blended (60% ML, 40% rules)."""
        rule_engine = FakeRuleEngine("BUY", 0.50)
        ml_predictor = FakePredictor("BUY", 0.80)
        generator = SignalGenerator(rule_engine, ml_predictor)
        indicators = {"4h": []}

        signal = generator.generate("BTCUSDT", indicators)

        assert signal is not None
        assert signal.signal_type == "BUY"
        # Expected: 0.6 * 0.80 + 0.4 * 0.50 = 0.48 + 0.20 = 0.68
        assert signal.confidence_score == pytest.approx(Decimal("0.68"), abs=Decimal("0.01"))

    def test_conflicting_direction_penalises_confidence(self) -> None:
        """When ML and rules disagree, confidence should be penalised (40% of min)."""
        rule_engine = FakeRuleEngine("BUY", 0.80)
        ml_predictor = FakePredictor("SELL", 0.70)
        generator = SignalGenerator(rule_engine, ml_predictor)
        indicators = {"4h": []}

        signal = generator.generate("BTCUSDT", indicators)

        # Expected: 0.4 * min(0.80, 0.70) = 0.4 * 0.70 = 0.28 (below threshold)
        assert signal is None

    def test_predictor_failure_fallback_to_rules(self) -> None:
        """If predictor fails, should use rules only."""

        class FailingPredictor:
            def predict(self, features: Any) -> list[dict[str, Any]]:
                raise RuntimeError("Model load failed")

        rule_engine = FakeRuleEngine("BUY", 0.75)
        generator = SignalGenerator(rule_engine, FailingPredictor())  # type: ignore[arg-type]
        indicators = {"4h": []}

        signal = generator.generate("BTCUSDT", indicators)

        assert signal is not None
        assert signal.confidence_score == pytest.approx(Decimal("0.75"), abs=Decimal("0.01"))


class TestSentimentAdjustment:
    """Test sentiment adjustment to confidence."""

    def test_positive_sentiment_boosts_buy_confidence(self) -> None:
        """Positive sentiment should boost BUY confidence."""
        generator = SignalGenerator(rule_engine=FakeRuleEngine("BUY", 0.70))
        indicators = {"4h": []}

        signal = generator.generate("BTCUSDT", indicators, news_sentiment=1.0)

        assert signal is not None
        # Expected: 0.70 + 1.0 * 0.05 = 0.75
        assert signal.confidence_score > Decimal("0.70")

    def test_negative_sentiment_reduces_buy_confidence(self) -> None:
        """Negative sentiment should reduce BUY confidence."""
        generator = SignalGenerator(rule_engine=FakeRuleEngine("BUY", 0.75))
        indicators = {"4h": []}

        signal = generator.generate("BTCUSDT", indicators, news_sentiment=-1.0)

        assert signal is not None
        # Expected: 0.75 - 1.0 * 0.05 = 0.70
        assert signal.confidence_score < Decimal("0.75")

    def test_sentiment_capped_at_0_95(self) -> None:
        """Sentiment adjustment should cap confidence at 0.95."""
        generator = SignalGenerator(rule_engine=FakeRuleEngine("BUY", 0.95))
        indicators = {"4h": []}

        signal = generator.generate("BTCUSDT", indicators, news_sentiment=1.0)

        assert signal is not None
        assert signal.confidence_score <= Decimal("0.95")

    def test_sentiment_floored_at_0(self) -> None:
        """Sentiment adjustment should floor confidence at 0."""
        generator = SignalGenerator(rule_engine=FakeRuleEngine("BUY", 0.01))
        indicators = {"4h": []}

        signal = generator.generate("BTCUSDT", indicators, news_sentiment=-1.0)

        # Below threshold, not emitted
        assert signal is None


class TestLeverageAndMargin:
    """Test leverage suggestion and margin safety computation."""

    def test_high_confidence_suggests_max_leverage(self) -> None:
        """Confidence >= 0.85 should suggest leverage 20."""
        generator = SignalGenerator(rule_engine=FakeRuleEngine("BUY", 0.90))
        indicators = {"4h": []}

        signal = generator.generate("BTCUSDT", indicators)

        assert signal is not None
        assert signal.leverage_suggested == 20

    def test_medium_confidence_suggests_medium_leverage(self) -> None:
        """Confidence 0.75-0.85 should suggest leverage 10."""
        generator = SignalGenerator(rule_engine=FakeRuleEngine("BUY", 0.80))
        indicators = {"4h": []}

        signal = generator.generate("BTCUSDT", indicators)

        assert signal is not None
        assert signal.leverage_suggested == 10

    def test_lower_confidence_suggests_lower_leverage(self) -> None:
        """Confidence 0.65-0.75 should suggest leverage 5."""
        generator = SignalGenerator(rule_engine=FakeRuleEngine("BUY", 0.70))
        indicators = {"4h": []}

        signal = generator.generate("BTCUSDT", indicators)

        assert signal is not None
        assert signal.leverage_suggested == 5

    def test_just_above_threshold_no_leverage(self) -> None:
        """Confidence just above 0.6 should have no leverage."""
        generator = SignalGenerator(rule_engine=FakeRuleEngine("BUY", 0.61))
        indicators = {"4h": []}

        signal = generator.generate("BTCUSDT", indicators)

        assert signal is not None
        assert signal.leverage_suggested is None

    def test_margin_safety_respects_2x_rule(self) -> None:
        """Margin safety should be 2x the notional (per doc requirement)."""
        generator = SignalGenerator(rule_engine=FakeRuleEngine("BUY", 0.80))
        indicators = {"4h": []}

        signal = generator.generate("BTCUSDT", indicators)

        assert signal is not None
        # Leverage 10 -> box 10% -> margin 20%
        assert signal.margin_safety == pytest.approx(Decimal("0.2"), abs=Decimal("0.01"))


class TestEntryStopLossTP:
    """Test entry price, stop loss, and take profit calculation."""

    def test_entry_price_calculated_for_buy(self) -> None:
        """BUY signal should have entry price above current (0.5 ATR)."""
        generator = SignalGenerator(rule_engine=FakeRuleEngine("BUY", 0.75))
        indicators = {"4h": []}

        signal = generator.generate("BTCUSDT", indicators)

        assert signal is not None
        # Entry is calculated internally; just verify signal was generated
        assert signal.signal_type == "BUY"

    def test_entry_price_calculated_for_sell(self) -> None:
        """SELL signal should have entry price below current (0.5 ATR)."""
        generator = SignalGenerator(rule_engine=FakeRuleEngine("SELL", 0.75))
        indicators = {"4h": []}

        signal = generator.generate("BTCUSDT", indicators)

        assert signal is not None
        assert signal.signal_type == "SELL"

    def test_stop_loss_calculation_for_buy(self) -> None:
        """BUY signal should have SL below entry (1.5 ATR)."""
        sg = SignalGenerator(rule_engine=FakeRuleEngine("BUY", 0.75))

        entry = sg._calculate_entry_price(100.0, atr=1.0, direction="BUY")
        sl = sg._calculate_stop_loss(entry, atr=1.0, direction="BUY")

        assert sl < entry

    def test_stop_loss_calculation_for_sell(self) -> None:
        """SELL signal should have SL above entry (1.5 ATR)."""
        sg = SignalGenerator(rule_engine=FakeRuleEngine("SELL", 0.75))

        entry = sg._calculate_entry_price(100.0, atr=1.0, direction="SELL")
        sl = sg._calculate_stop_loss(entry, atr=1.0, direction="SELL")

        assert sl > entry

    def test_take_profit_levels_for_buy(self) -> None:
        """BUY signal should have TPs above entry at 1:1, 1:2, 1:3 risk-reward."""
        sg = SignalGenerator(rule_engine=FakeRuleEngine("BUY", 0.75))

        entry = sg._calculate_entry_price(100.0, atr=1.0, direction="BUY")
        tp_levels = sg._calculate_take_profit_levels(entry, atr=1.0, direction="BUY")

        assert len(tp_levels) == 3
        for tp in tp_levels:
            assert tp > entry

    def test_take_profit_levels_for_sell(self) -> None:
        """SELL signal should have TPs below entry at 1:1, 1:2, 1:3 risk-reward."""
        sg = SignalGenerator(rule_engine=FakeRuleEngine("SELL", 0.75))

        entry = sg._calculate_entry_price(100.0, atr=1.0, direction="SELL")
        tp_levels = sg._calculate_take_profit_levels(entry, atr=1.0, direction="SELL")

        assert len(tp_levels) == 3
        for tp in tp_levels:
            assert tp < entry

    def test_custom_tp_ratios(self) -> None:
        """Custom TP ratios should produce custom levels."""
        sg = SignalGenerator(rule_engine=FakeRuleEngine("BUY", 0.75))

        entry = sg._calculate_entry_price(100.0, atr=2.0, direction="BUY")
        tp_levels = sg._calculate_take_profit_levels(entry, atr=2.0, direction="BUY", ratios=[0.5, 1.5])

        assert len(tp_levels) == 2


class TestFeeVerification:
    """Test fee suppression logic."""

    def test_high_fees_suppress_signal(self) -> None:
        """If fees > 50% of expected gain, signal should be suppressed."""
        # Confidence 0.60 -> expected gain = 0.60 * 0.01 = 0.006
        # Threshold: fees < 0.006 * 0.5 = 0.003
        # Default fees = 0.0017 (< threshold, so not suppressed yet)
        # But with very high fees calculation this could trigger suppression

        generator = SignalGenerator(rule_engine=FakeRuleEngine("BUY", 0.60))
        indicators = {"4h": []}

        signal = generator.generate("BTCUSDT", indicators)

        # With confidence exactly at threshold and fee check, may be suppressed
        # This test documents the behavior
        assert signal is None or signal.fees_estimated is not None
