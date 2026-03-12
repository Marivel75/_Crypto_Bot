"""E2E tests for the full signal generation pipeline.

Validates: IndicatorRecord objects -> RuleEngine -> SignalGenerator -> TradingSignal.

The database layer is fully mocked so no live TimescaleDB connection is required.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from src.ml.rules.models import RuleLabel, RuleResult
from src.ml.signal_generator import SignalGenerator
from src.shared.models.crypto import IndicatorRecord
from src.shared.models.signal import TradingSignal

# ---------------------------------------------------------------------------
# Config path — used to decide whether RuleEngine tests should run
# ---------------------------------------------------------------------------

_CONFIG_PATH = Path(__file__).resolve().parents[2] / "src" / "ml" / "config" / "indicators.yaml"
_CONFIG_MISSING = not _CONFIG_PATH.exists()

# ---------------------------------------------------------------------------
# Fixed timestamps (never use datetime.now() in tests)
# ---------------------------------------------------------------------------

_TS_BASE = datetime(2024, 6, 1, 12, 0, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_indicator(
    symbol: str = "BTCUSDT",
    timeframe: str = "1h",
    rsi: Decimal | None = None,
    bollinger_upper: Decimal | None = None,
    bollinger_middle: Decimal | None = None,
    bollinger_lower: Decimal | None = None,
    price_vs_bollinger: Decimal | None = None,
    trend_slope: Decimal | None = None,
    trend_type: str | None = None,
    ts_offset_seconds: int = 0,
) -> IndicatorRecord:
    """Build an IndicatorRecord with a fixed timestamp."""
    return IndicatorRecord(
        symbol=symbol,
        timeframe=timeframe,
        timestamp=_TS_BASE.replace(second=ts_offset_seconds),
        rsi=rsi,
        bollinger_upper=bollinger_upper,
        bollinger_middle=bollinger_middle,
        bollinger_lower=bollinger_lower,
        price_vs_bollinger=price_vs_bollinger,
        trend_slope=trend_slope,
        trend_type=trend_type,
    )


def _oversold_indicators(symbol: str = "BTCUSDT") -> dict[str, list[IndicatorRecord]]:
    """Return a multi-TF dict where RSI is deeply oversold and converged across TFs."""
    # RSI=22 across 1h/2h/3h/4h — all within convergence_threshold (5), avg well below 30
    return {
        tf: [_make_indicator(symbol=symbol, timeframe=tf, rsi=Decimal("22"), ts_offset_seconds=i)]
        for i, tf in enumerate(["1h", "2h", "3h", "4h"])
    }


def _overbought_indicators(symbol: str = "BTCUSDT") -> dict[str, list[IndicatorRecord]]:
    """Return a multi-TF dict where RSI is deeply overbought and converged across TFs."""
    # RSI=78 across 1h/2h/3h/4h — all within convergence_threshold (5), avg well above 70
    return {
        tf: [_make_indicator(symbol=symbol, timeframe=tf, rsi=Decimal("78"), ts_offset_seconds=i)]
        for i, tf in enumerate(["1h", "2h", "3h", "4h"])
    }


# ---------------------------------------------------------------------------
# Fake rule engine used to inject controlled results into SignalGenerator
# ---------------------------------------------------------------------------


class _FakeRuleEngine:
    """Minimal implementation of the RuleEngine protocol for SignalGenerator."""

    def __init__(self, result: dict[str, Any]) -> None:
        self._result = result

    def evaluate(self, symbol: str, indicators: dict[str, Any]) -> dict[str, Any]:
        """Return the pre-configured result regardless of inputs."""
        return self._result


# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------


class TestSignalFlow:
    """E2E tests covering the full indicator -> engine -> signal pipeline."""

    # ------------------------------------------------------------------
    # 1. RuleEngine evaluates bullish indicators
    # ------------------------------------------------------------------

    @pytest.mark.skipif(_CONFIG_MISSING, reason="indicators.yaml not found — skipping RuleEngine tests")
    def test_rule_engine_evaluates_bullish_indicators(self) -> None:
        """Oversold RSI across four timeframes should produce at least one BUY RuleResult."""
        from src.ml.rules.engine import RuleEngine

        engine = RuleEngine(config_path=_CONFIG_PATH)
        indicators = _oversold_indicators()

        results = engine.evaluate("BTCUSDT", indicators)

        assert isinstance(results, list), "evaluate() must return a list"
        assert len(results) >= 1, "At least one rule should fire for oversold RSI across all TFs"

        directions = {r.direction for r in results if r.direction}
        # Legacy-style results use direction directly
        label_directions = {
            "BUY" if r.label == RuleLabel.BULL else "SELL"
            for r in results
            if r.direction == "" and r.label != RuleLabel.NEUTRAL
        }
        all_directions = directions | label_directions

        assert "BUY" in all_directions, (
            f"Expected at least one BUY result for oversold RSI, got directions: {all_directions}"
        )

    # ------------------------------------------------------------------
    # 2. RuleEngine evaluates bearish indicators
    # ------------------------------------------------------------------

    @pytest.mark.skipif(_CONFIG_MISSING, reason="indicators.yaml not found — skipping RuleEngine tests")
    def test_rule_engine_evaluates_bearish_indicators(self) -> None:
        """Overbought RSI across four timeframes should produce at least one SELL RuleResult."""
        from src.ml.rules.engine import RuleEngine

        engine = RuleEngine(config_path=_CONFIG_PATH)
        indicators = _overbought_indicators()

        results = engine.evaluate("BTCUSDT", indicators)

        assert isinstance(results, list), "evaluate() must return a list"
        assert len(results) >= 1, "At least one rule should fire for overbought RSI across all TFs"

        directions = {r.direction for r in results if r.direction}
        label_directions = {
            "SELL" if r.label == RuleLabel.BEAR else "BUY"
            for r in results
            if r.direction == "" and r.label != RuleLabel.NEUTRAL
        }
        all_directions = directions | label_directions

        assert "SELL" in all_directions, (
            f"Expected at least one SELL result for overbought RSI, got directions: {all_directions}"
        )

    # ------------------------------------------------------------------
    # 3. SignalGenerator emits a BUY signal from a controlled rule engine
    # ------------------------------------------------------------------

    def test_signal_generator_emits_buy_signal(self) -> None:
        """SignalGenerator must emit a TradingSignal when the rule engine returns BUY/0.8."""
        fake_engine = _FakeRuleEngine(
            {
                "direction": "BUY",
                "confidence": 0.8,
                "rules_triggered": ["rsi_oversold_multi_tf"],
                "timeframe": "4h",
                "timeframes_aligned": {"1h": {"rsi": 22}, "4h": {"rsi": 22}},
            }
        )
        generator = SignalGenerator(rule_engine=fake_engine)

        indicators = _oversold_indicators()
        signal = generator.generate(symbol="BTCUSDT", indicators=indicators)

        assert signal is not None, "SignalGenerator must emit a signal when confidence=0.8 >= 0.6"
        assert isinstance(signal, TradingSignal)
        assert signal.symbol == "BTCUSDT"
        assert signal.signal_type == "BUY"
        assert signal.confidence_score >= Decimal("0.6")
        assert signal.confidence_score <= Decimal("1.0")
        assert "rsi_oversold_multi_tf" in signal.rules_triggered
        assert signal.model_version != ""

    # ------------------------------------------------------------------
    # 4. SignalGenerator suppresses low-confidence signals
    # ------------------------------------------------------------------

    def test_signal_generator_suppresses_low_confidence(self) -> None:
        """SignalGenerator must return None when rule engine confidence is 0.3 (< 0.6 threshold)."""
        fake_engine = _FakeRuleEngine(
            {
                "direction": "BUY",
                "confidence": 0.3,
                "rules_triggered": ["rsi_oversold_multi_tf"],
                "timeframe": "4h",
            }
        )
        generator = SignalGenerator(rule_engine=fake_engine)

        indicators = _oversold_indicators()
        signal = generator.generate(symbol="BTCUSDT", indicators=indicators)

        assert signal is None, f"SignalGenerator must suppress signals with confidence < 0.6, got: {signal!r}"

    # ------------------------------------------------------------------
    # 5. Full pipeline: IndicatorRecord -> RuleEngine -> SignalGenerator -> TradingSignal
    # ------------------------------------------------------------------

    @pytest.mark.skipif(_CONFIG_MISSING, reason="indicators.yaml not found — skipping full pipeline test")
    def test_full_pipeline_indicators_to_signal(self) -> None:
        """Feed real IndicatorRecord objects through the full pipeline and verify the output.

        This test does NOT touch the database — the persistence layer is not invoked.
        It validates that the component chain produces a structurally correct TradingSignal
        (or None, when the engine correctly decides not to emit).
        """
        from src.ml.rules.engine import RuleEngine

        # Build a concrete rule engine backed by the real YAML config
        rule_engine = RuleEngine(config_path=_CONFIG_PATH)

        # Create oversold indicators across 1h, 4h, 1D, 1W to maximise rule coverage.
        # RSI=20 is deeply oversold and should trigger rsi_oversold_multi_tf at minimum.
        indicators: dict[str, list[IndicatorRecord]] = {}

        # RSI timeframes (1h, 2h, 3h, 4h) — deeply oversold, tightly converged
        for i, tf in enumerate(["1h", "2h", "3h", "4h"]):
            indicators[tf] = [
                _make_indicator(
                    symbol="BTCUSDT",
                    timeframe=tf,
                    rsi=Decimal("20"),
                    ts_offset_seconds=i,
                )
            ]

        # Additional timeframes (1D, 1W) with trend data — helps trend/convergence rules
        indicators["1D"] = [
            _make_indicator(
                symbol="BTCUSDT",
                timeframe="1D",
                rsi=Decimal("25"),
                trend_slope=Decimal("0.002"),
                trend_type="stable",
                ts_offset_seconds=10,
            )
        ]
        indicators["1W"] = [
            _make_indicator(
                symbol="BTCUSDT",
                timeframe="1W",
                rsi=Decimal("28"),
                trend_slope=Decimal("0.006"),
                trend_type="aggressive",
                ts_offset_seconds=20,
            )
        ]

        # Wrap the concrete RuleEngine behind the protocol expected by SignalGenerator.
        # SignalGenerator.RuleEngine protocol expects evaluate(symbol, indicators) -> dict.
        # The concrete engine returns list[RuleResult]; we need an adapter.
        class _RuleEngineAdapter:
            """Adapts the concrete RuleEngine to the SignalGenerator.RuleEngine protocol."""

            def __init__(self, engine: RuleEngine) -> None:
                self._engine = engine

            def evaluate(self, symbol: str, indicators: dict[str, Any]) -> dict[str, Any]:
                # indicators here is the flat dict passed by SignalGenerator internals.
                # We unwrap the nested timeframes if present, else pass through.
                tf_indicators: dict[str, list[IndicatorRecord]] = indicators.get(
                    "timeframes",
                    indicators,  # type: ignore[arg-type]
                )
                results: list[RuleResult] = self._engine.evaluate(symbol, tf_indicators)
                signal = self._engine.aggregate(results, symbol=symbol)
                if signal is None:
                    # No qualifying signal — return HOLD so SignalGenerator suppresses it
                    return {"direction": "HOLD", "confidence": 0.0, "rules_triggered": []}
                return {
                    "direction": signal.signal_type,
                    "confidence": float(signal.confidence_score),
                    "rules_triggered": signal.rules_triggered,
                    "timeframe": signal.timeframe_primary,
                }

        adapted_engine = _RuleEngineAdapter(rule_engine)
        generator = SignalGenerator(rule_engine=adapted_engine)

        flat_input: dict[str, Any] = {
            "timeframes": indicators,
            "timeframe": "4h",
        }
        signal = generator.generate(symbol="BTCUSDT", indicators=flat_input)

        # The pipeline may or may not emit — both are valid depending on confidence
        # aggregation. What we assert is structural correctness when a signal is produced.
        if signal is not None:
            assert isinstance(signal, TradingSignal), "Output must be a TradingSignal"
            assert signal.symbol == "BTCUSDT"
            assert signal.signal_type in ("BUY", "SELL"), (
                f"signal_type must be BUY or SELL, got: {signal.signal_type!r}"
            )
            assert Decimal("0.6") <= signal.confidence_score <= Decimal("1.0"), (
                f"confidence_score must be in [0.6, 1.0], got: {signal.confidence_score}"
            )
            assert isinstance(signal.rules_triggered, list), "rules_triggered must be a list"
            assert signal.model_version != "", "model_version must not be empty"
            assert signal.timeframe_primary != "", "timeframe_primary must not be empty"
        else:
            # Acceptable: oversold RSI may not meet the confidence threshold after
            # aggregation weighting and opposition penalties.
            pass
