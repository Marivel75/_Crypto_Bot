"""Unit tests for rule engine — evaluation and aggregation."""

from __future__ import annotations

from datetime import datetime, timezone

UTC = timezone.utc
from decimal import Decimal
from pathlib import Path

from src.ml.rules.engine import RuleEngine
from src.ml.rules.models import RuleResult
from src.shared.models.crypto import IndicatorRecord

FIXED_TS = datetime(2025, 6, 1, 12, 0, tzinfo=UTC)
CONFIG_PATH = Path(__file__).resolve().parents[3] / "src" / "ml" / "config" / "indicators.yaml"


def _make_indicator(
    timeframe: str = "4h",
    rsi: Decimal | None = None,
    bollinger_upper: Decimal | None = None,
    bollinger_middle: Decimal | None = None,
    bollinger_lower: Decimal | None = None,
    price_vs_bollinger: Decimal | None = None,
    trend_slope: Decimal | None = None,
    trend_type: str | None = None,
    harmonic_pattern: str | None = None,
) -> IndicatorRecord:
    return IndicatorRecord(
        symbol="BTCUSDT",
        timeframe=timeframe,
        timestamp=FIXED_TS,
        rsi=rsi,
        bollinger_upper=bollinger_upper,
        bollinger_middle=bollinger_middle,
        bollinger_lower=bollinger_lower,
        price_vs_bollinger=price_vs_bollinger,
        trend_slope=trend_slope,
        trend_type=trend_type,
        harmonic_pattern=harmonic_pattern,
    )


class TestRuleEngine:
    def test_engine_loads_from_yaml(self) -> None:
        engine = RuleEngine.from_yaml(CONFIG_PATH)
        assert engine.config is not None
        assert "rsi" in engine.config

    def test_evaluate_oversold_returns_results(self) -> None:
        engine = RuleEngine.from_yaml(CONFIG_PATH)
        indicators: dict[str, list[IndicatorRecord]] = {
            "1h": [_make_indicator("1h", rsi=Decimal("20"))],
            "2h": [_make_indicator("2h", rsi=Decimal("22"))],
            "3h": [_make_indicator("3h", rsi=Decimal("24"))],
            "4h": [_make_indicator("4h", rsi=Decimal("25"))],
        }
        results = engine.evaluate("BTCUSDT", indicators)
        # RSI oversold with convergence should produce at least one result
        assert len(results) >= 1
        buy_results = [r for r in results if r.direction == "BUY"]
        assert len(buy_results) >= 1

    def test_evaluate_neutral_returns_empty(self) -> None:
        engine = RuleEngine.from_yaml(CONFIG_PATH)
        indicators: dict[str, list[IndicatorRecord]] = {
            "4h": [
                _make_indicator(
                    "4h",
                    rsi=Decimal("50"),
                    bollinger_upper=Decimal("110"),
                    bollinger_lower=Decimal("90"),
                    bollinger_middle=Decimal("100"),
                    price_vs_bollinger=Decimal("0.0"),
                )
            ],
        }
        results = engine.evaluate("BTCUSDT", indicators)
        # Neutral conditions should produce no results from legacy evaluators
        legacy_results = [r for r in results if r.direction in ("BUY", "SELL")]
        assert len(legacy_results) == 0

    def test_aggregate_buy_signal(self) -> None:
        engine = RuleEngine.from_yaml(CONFIG_PATH)
        results = [
            RuleResult(
                direction="BUY",
                confidence=Decimal("0.8"),
                reason="RSI oversold",
                rule_name="rsi_oversold_multi_tf",
            ),
            RuleResult(
                direction="BUY",
                confidence=Decimal("0.7"),
                reason="Bollinger breakout",
                rule_name="bollinger_breakout_4h",
            ),
        ]
        signal = engine.aggregate(results, symbol="BTCUSDT")
        assert signal is not None
        assert signal.signal_type == "BUY"
        assert signal.confidence_score >= Decimal("0.6")
        assert signal.symbol == "BTCUSDT"

    def test_aggregate_empty_returns_none(self) -> None:
        engine = RuleEngine.from_yaml(CONFIG_PATH)
        signal = engine.aggregate([], symbol="BTCUSDT")
        assert signal is None

    def test_aggregate_low_confidence_returns_none(self) -> None:
        engine = RuleEngine.from_yaml(CONFIG_PATH)
        results = [
            RuleResult(
                direction="BUY",
                confidence=Decimal("0.3"),
                reason="Weak signal",
                rule_name="rsi_oversold_multi_tf",
            ),
        ]
        signal = engine.aggregate(results, symbol="BTCUSDT")
        # 0.3 confidence is below the 0.6 threshold
        assert signal is None
