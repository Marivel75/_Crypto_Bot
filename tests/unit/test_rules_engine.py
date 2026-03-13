"""Unit tests for the ML rules engine — aggregation and RSI rule evaluation."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from src.ml.rules.engine import RuleEngine, _infer_rule_key
from src.ml.rules.models import RuleResult
from src.ml.rules.rsi_rules import evaluate_rsi
from src.shared.models.crypto import IndicatorRecord

# Path to the real indicators.yaml used by the application
_CONFIG_PATH = Path(__file__).parents[2] / "src" / "ml" / "config" / "indicators.yaml"

_TS = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_indicator(
    rsi: float | None = None,
    symbol: str = "BTCUSDT",
    timeframe: str = "1h",
    ts: datetime = _TS,
) -> IndicatorRecord:
    return IndicatorRecord(
        symbol=symbol,
        timeframe=timeframe,
        timestamp=ts,
        rsi=Decimal(str(rsi)) if rsi is not None else None,
    )


def _make_rsi_result(direction: str, confidence: float, rule: str = "rsi_rule") -> RuleResult:
    return RuleResult(
        direction=direction,
        confidence=Decimal(str(confidence)),
        reason=f"{rule} fired",
        rule_name=rule,
    )


# ---------------------------------------------------------------------------
# _infer_rule_key
# ---------------------------------------------------------------------------


class TestInferRuleKey:
    def test_rsi_prefix(self) -> None:
        assert _infer_rule_key("rsi_overbought_multi_tf") == "rsi"

    def test_bollinger_prefix(self) -> None:
        assert _infer_rule_key("bollinger_squeeze") == "bollinger"

    def test_harmonic_prefix(self) -> None:
        assert _infer_rule_key("harmonic_gartley") == "harmonic"

    def test_trend_prefix(self) -> None:
        assert _infer_rule_key("trend_uptrend") == "trend"

    def test_unknown_falls_back_to_rsi(self) -> None:
        assert _infer_rule_key("unknown_rule_xyz") == "rsi"


# ---------------------------------------------------------------------------
# RuleEngine.aggregate
# ---------------------------------------------------------------------------


class TestRuleEngineAggregate:
    @pytest.fixture
    def engine(self) -> RuleEngine:
        return RuleEngine(config_path=_CONFIG_PATH)

    def test_aggregate_empty_returns_none(self, engine: RuleEngine) -> None:
        result = engine.aggregate([])
        assert result is None

    def test_aggregate_single_strong_buy_above_threshold(self, engine: RuleEngine) -> None:
        results = [_make_rsi_result("BUY", 0.85, "rsi_oversold_multi_tf")]
        signal = engine.aggregate(results, symbol="BTCUSDT")
        assert signal is not None
        assert signal.signal_type == "BUY"
        assert signal.confidence_score >= Decimal("0.6")

    def test_aggregate_single_strong_sell_above_threshold(self, engine: RuleEngine) -> None:
        results = [_make_rsi_result("SELL", 0.85, "rsi_overbought_multi_tf")]
        signal = engine.aggregate(results, symbol="BTCUSDT")
        assert signal is not None
        assert signal.signal_type == "SELL"

    def test_aggregate_low_confidence_below_threshold_returns_none(self, engine: RuleEngine) -> None:
        results = [_make_rsi_result("BUY", 0.3, "rsi_oversold_multi_tf")]
        signal = engine.aggregate(results, symbol="BTCUSDT")
        assert signal is None

    def test_aggregate_conflicting_signals_reduces_confidence(self, engine: RuleEngine) -> None:
        """Opposite-direction rules should penalise the final confidence."""
        results = [
            _make_rsi_result("BUY", 0.80, "rsi_oversold_multi_tf"),
            _make_rsi_result("SELL", 0.75, "bollinger_upper_breakout"),
        ]
        signal = engine.aggregate(results, symbol="BTCUSDT")
        # If emitted, confidence should be lower than 0.80 due to opposition
        if signal is not None:
            assert signal.confidence_score < Decimal("0.80")

    def test_aggregate_dominant_direction_wins(self, engine: RuleEngine) -> None:
        results = [
            _make_rsi_result("BUY", 0.80, "rsi_oversold_multi_tf"),
            _make_rsi_result("BUY", 0.75, "bollinger_lower_bounce"),
            _make_rsi_result("SELL", 0.60, "trend_downtrend"),
        ]
        signal = engine.aggregate(results, symbol="BTCUSDT")
        if signal is not None:
            assert signal.signal_type == "BUY"

    def test_aggregate_signal_contains_model_version(self, engine: RuleEngine) -> None:
        results = [_make_rsi_result("BUY", 0.85, "rsi_oversold_multi_tf")]
        signal = engine.aggregate(results, symbol="BTCUSDT")
        assert signal is not None
        assert signal.model_version == "rules_v1"

    def test_aggregate_signal_has_symbol(self, engine: RuleEngine) -> None:
        results = [_make_rsi_result("BUY", 0.85, "rsi_oversold_multi_tf")]
        signal = engine.aggregate(results, symbol="ETHUSDT")
        assert signal is not None
        assert signal.symbol == "ETHUSDT"

    def test_aggregate_rules_triggered_list_populated(self, engine: RuleEngine) -> None:
        results = [
            _make_rsi_result("BUY", 0.85, "rsi_oversold_multi_tf"),
            _make_rsi_result("BUY", 0.70, "bollinger_lower_bounce"),
        ]
        signal = engine.aggregate(results, symbol="BTCUSDT")
        assert signal is not None
        assert "rsi_oversold_multi_tf" in signal.rules_triggered
        assert "bollinger_lower_bounce" in signal.rules_triggered


# ---------------------------------------------------------------------------
# evaluate_rsi (unit test of the RSI rule function directly)
# ---------------------------------------------------------------------------


class TestEvaluateRSI:
    def _indicators_with_rsi(
        self,
        rsi_1h: float,
        rsi_2h: float,
        rsi_3h: float,
        rsi_4h: float,
    ) -> dict[str, list[IndicatorRecord]]:
        return {
            "1h": [_make_indicator(rsi=rsi_1h, timeframe="1h")],
            "2h": [_make_indicator(rsi=rsi_2h, timeframe="2h")],
            "3h": [_make_indicator(rsi=rsi_3h, timeframe="3h")],
            "4h": [_make_indicator(rsi=rsi_4h, timeframe="4h")],
        }

    def test_overbought_rsi_returns_sell(self) -> None:
        # All RSI values >= 70, within 5 of each other → SELL
        indicators = self._indicators_with_rsi(72.0, 73.0, 74.0, 75.0)
        config = {"timeframes": ["1h", "2h", "3h", "4h"], "overbought": 70, "oversold": 30, "convergence_threshold": 5}
        result = evaluate_rsi("BTCUSDT", indicators, config)
        assert result is not None
        assert result.direction == "SELL"
        assert result.confidence >= Decimal("0.5")

    def test_oversold_rsi_returns_buy(self) -> None:
        # All RSI values <= 30, within 5 → BUY
        indicators = self._indicators_with_rsi(22.0, 23.0, 24.0, 25.0)
        config = {"timeframes": ["1h", "2h", "3h", "4h"], "overbought": 70, "oversold": 30, "convergence_threshold": 5}
        result = evaluate_rsi("BTCUSDT", indicators, config)
        assert result is not None
        assert result.direction == "BUY"
        assert result.confidence >= Decimal("0.5")

    def test_neutral_rsi_returns_none(self) -> None:
        indicators = self._indicators_with_rsi(50.0, 51.0, 52.0, 53.0)
        config = {"timeframes": ["1h", "2h", "3h", "4h"], "overbought": 70, "oversold": 30, "convergence_threshold": 5}
        result = evaluate_rsi("BTCUSDT", indicators, config)
        assert result is None

    def test_non_converged_rsi_returns_none(self) -> None:
        # 1h=20, 4h=80 → spread > convergence_threshold → no signal
        indicators = self._indicators_with_rsi(20.0, 40.0, 60.0, 80.0)
        config = {"timeframes": ["1h", "2h", "3h", "4h"], "overbought": 70, "oversold": 30, "convergence_threshold": 5}
        result = evaluate_rsi("BTCUSDT", indicators, config)
        assert result is None

    def test_insufficient_timeframes_returns_none(self) -> None:
        # Only 1 timeframe available
        indicators = {"1h": [_make_indicator(rsi=25.0, timeframe="1h")]}
        config = {"timeframes": ["1h", "2h", "3h", "4h"], "overbought": 70, "oversold": 30, "convergence_threshold": 5}
        result = evaluate_rsi("BTCUSDT", indicators, config)
        assert result is None

    def test_confidence_scales_with_extremity(self) -> None:
        """RSI=30 should yield lower confidence than RSI=10 for a BUY signal."""
        config = {"timeframes": ["1h", "2h", "3h", "4h"], "overbought": 70, "oversold": 30, "convergence_threshold": 5}

        mild_indicators = self._indicators_with_rsi(29.0, 30.0, 30.0, 31.0)
        extreme_indicators = self._indicators_with_rsi(8.0, 9.0, 10.0, 11.0)

        mild = evaluate_rsi("BTCUSDT", mild_indicators, config)
        extreme = evaluate_rsi("BTCUSDT", extreme_indicators, config)

        assert mild is not None
        assert extreme is not None
        assert extreme.confidence > mild.confidence


# ---------------------------------------------------------------------------
# RuleEngine.evaluate — smoke test (mocks individual rule functions)
# ---------------------------------------------------------------------------


class TestRuleEngineEvaluate:
    def test_evaluate_returns_list(self) -> None:
        engine = RuleEngine(config_path=_CONFIG_PATH)
        indicators: dict[str, list[IndicatorRecord]] = {}
        results = engine.evaluate("BTCUSDT", indicators)
        assert isinstance(results, list)

    def test_evaluate_skips_failed_rules_gracefully(self) -> None:
        """A rule that raises must not crash the whole evaluate call."""
        engine = RuleEngine(config_path=_CONFIG_PATH)
        # Provide nonsense data — rule functions should handle it gracefully
        indicators: dict[str, list[IndicatorRecord]] = {
            "1h": [],
            "4h": [],
        }
        results = engine.evaluate("BADDATA", indicators)
        assert isinstance(results, list)
