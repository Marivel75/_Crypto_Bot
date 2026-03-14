"""Unit tests for ML rules — each rule tested with BUY/SELL/NEUTRAL cases."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from src.ml.rules.bollinger_rules import evaluate_bollinger
from src.ml.rules.convergence_rules import evaluate_rsi_bollinger_convergence
from src.ml.rules.harmonic_rules import evaluate_harmonic
from src.ml.rules.models import RuleLabel
from src.ml.rules.multi_tf_rules import evaluate_multi_tf_alignment
from src.ml.rules.rsi_rules import evaluate_rsi
from src.ml.rules.trend_rules import evaluate_trend
from src.shared.models.crypto import IndicatorRecord

FIXED_TS = datetime(2025, 6, 1, 12, 0, tzinfo=UTC)


def _make_indicator(
    timeframe: str = "4h",
    rsi: Decimal | None = None,
    bollinger_upper: Decimal | None = None,
    bollinger_middle: Decimal | None = None,
    bollinger_lower: Decimal | None = None,
    price_vs_bollinger: Decimal | None = None,
    harmonic_pattern: str | None = None,
    trend_slope: Decimal | None = None,
    trend_type: str | None = None,
    metadata: dict | None = None,
) -> IndicatorRecord:
    """Helper to build an IndicatorRecord with sensible defaults."""
    return IndicatorRecord(
        symbol="BTCUSDT",
        timeframe=timeframe,
        timestamp=FIXED_TS,
        rsi=rsi,
        bollinger_upper=bollinger_upper,
        bollinger_middle=bollinger_middle,
        bollinger_lower=bollinger_lower,
        price_vs_bollinger=price_vs_bollinger,
        harmonic_pattern=harmonic_pattern,
        trend_slope=trend_slope,
        trend_type=trend_type,
        metadata=metadata or {},
    )


# ---------------------------------------------------------------------------
# RSI rules
# ---------------------------------------------------------------------------


class TestEvaluateRsi:
    def test_oversold_triggers_buy(self) -> None:
        indicators = {
            "1h": [_make_indicator("1h", rsi=Decimal("25"))],
            "2h": [_make_indicator("2h", rsi=Decimal("28"))],
            "4h": [_make_indicator("4h", rsi=Decimal("22"))],
        }
        config = {"timeframes": ["1h", "2h", "4h"], "oversold": 30, "overbought": 70, "convergence_threshold": 10}
        result = evaluate_rsi("BTCUSDT", indicators, config)
        assert result is not None
        assert result.direction == "BUY"
        assert result.confidence >= Decimal("0.5")

    def test_overbought_triggers_sell(self) -> None:
        indicators = {
            "1h": [_make_indicator("1h", rsi=Decimal("75"))],
            "2h": [_make_indicator("2h", rsi=Decimal("78"))],
            "4h": [_make_indicator("4h", rsi=Decimal("80"))],
        }
        config = {"timeframes": ["1h", "2h", "4h"], "oversold": 30, "overbought": 70, "convergence_threshold": 10}
        result = evaluate_rsi("BTCUSDT", indicators, config)
        assert result is not None
        assert result.direction == "SELL"

    def test_normal_rsi_no_signal(self) -> None:
        indicators = {
            "1h": [_make_indicator("1h", rsi=Decimal("50"))],
            "4h": [_make_indicator("4h", rsi=Decimal("55"))],
        }
        config = {"timeframes": ["1h", "4h"], "oversold": 30, "overbought": 70, "convergence_threshold": 10}
        result = evaluate_rsi("BTCUSDT", indicators, config)
        assert result is None

    def test_no_data_returns_none(self) -> None:
        result = evaluate_rsi("BTCUSDT", {}, {"timeframes": ["1h", "4h"]})
        assert result is None

    def test_divergent_tfs_no_convergence(self) -> None:
        indicators = {
            "1h": [_make_indicator("1h", rsi=Decimal("20"))],
            "4h": [_make_indicator("4h", rsi=Decimal("50"))],
        }
        config = {"timeframes": ["1h", "4h"], "oversold": 30, "overbought": 70, "convergence_threshold": 5}
        result = evaluate_rsi("BTCUSDT", indicators, config)
        assert result is None


# ---------------------------------------------------------------------------
# Bollinger rules
# ---------------------------------------------------------------------------


class TestEvaluateBollinger:
    def test_upward_breakout_buy(self) -> None:
        indicators = {
            "4h": [
                _make_indicator(
                    "4h",
                    bollinger_upper=Decimal("100"),
                    bollinger_lower=Decimal("90"),
                    bollinger_middle=Decimal("95"),
                    price_vs_bollinger=Decimal("1.5"),
                )
            ],
        }
        config = {"timeframes": ["4h"], "squeeze_threshold": 0.02}
        result = evaluate_bollinger("BTCUSDT", indicators, config)
        assert result is not None
        assert result.direction == "BUY"

    def test_downward_breakout_sell(self) -> None:
        indicators = {
            "4h": [
                _make_indicator(
                    "4h",
                    bollinger_upper=Decimal("100"),
                    bollinger_lower=Decimal("90"),
                    bollinger_middle=Decimal("95"),
                    price_vs_bollinger=Decimal("-1.5"),
                )
            ],
        }
        config = {"timeframes": ["4h"], "squeeze_threshold": 0.02}
        result = evaluate_bollinger("BTCUSDT", indicators, config)
        assert result is not None
        assert result.direction == "SELL"

    def test_no_signal_mid_band(self) -> None:
        indicators = {
            "4h": [
                _make_indicator(
                    "4h",
                    bollinger_upper=Decimal("110"),
                    bollinger_lower=Decimal("90"),
                    bollinger_middle=Decimal("100"),
                    price_vs_bollinger=Decimal("0.0"),
                )
            ],
        }
        config = {"timeframes": ["4h"], "squeeze_threshold": 0.02}
        result = evaluate_bollinger("BTCUSDT", indicators, config)
        assert result is None

    def test_no_data_returns_none(self) -> None:
        result = evaluate_bollinger("BTCUSDT", {}, {"timeframes": ["4h"]})
        assert result is None


# ---------------------------------------------------------------------------
# Harmonic rules
# ---------------------------------------------------------------------------


class TestEvaluateHarmonic:
    def test_gartley_pattern_detected(self) -> None:
        indicators = {
            "4h": [_make_indicator("4h", harmonic_pattern="gartley")],
        }
        config = {
            "timeframes": ["4h"],
            "tolerance": 0.05,
            "patterns": {"gartley": {"xb": 0.618, "xd": 0.786}},
        }
        result = evaluate_harmonic("BTCUSDT", indicators, config)
        assert result is not None
        assert result.direction == "BUY"
        assert "gartley" in result.reason.lower()

    def test_no_pattern_returns_none(self) -> None:
        indicators = {
            "4h": [_make_indicator("4h", harmonic_pattern=None)],
        }
        config = {"timeframes": ["4h"], "tolerance": 0.05, "patterns": {"gartley": {}}}
        result = evaluate_harmonic("BTCUSDT", indicators, config)
        assert result is None


# ---------------------------------------------------------------------------
# Trend rules
# ---------------------------------------------------------------------------


class TestEvaluateTrend:
    def test_stable_weekly_aggressive_monthly_buy(self) -> None:
        indicators = {
            "1W": [_make_indicator("1W", trend_slope=Decimal("0.0005"))],
            "1M": [_make_indicator("1M", trend_slope=Decimal("0.01"))],
        }
        config = {
            "weekly": {"slope_threshold": 0.001},
            "monthly": {"slope_threshold": 0.005},
        }
        result = evaluate_trend("BTCUSDT", indicators, config)
        assert result is not None
        assert result.direction == "BUY"

    def test_no_monthly_data_returns_none(self) -> None:
        indicators = {
            "1W": [_make_indicator("1W", trend_slope=Decimal("0.0005"))],
        }
        config = {
            "weekly": {"slope_threshold": 0.001},
            "monthly": {"slope_threshold": 0.005},
        }
        result = evaluate_trend("BTCUSDT", indicators, config)
        assert result is None

    def test_divergent_directions_returns_none(self) -> None:
        indicators = {
            "1W": [_make_indicator("1W", trend_slope=Decimal("0.002"))],
            "1M": [_make_indicator("1M", trend_slope=Decimal("-0.01"))],
        }
        config = {
            "weekly": {"slope_threshold": 0.001},
            "monthly": {"slope_threshold": 0.005},
        }
        result = evaluate_trend("BTCUSDT", indicators, config)
        assert result is None


# ---------------------------------------------------------------------------
# Convergence rules (RSI + Bollinger)
# ---------------------------------------------------------------------------


class TestRsiBollingerConvergence:
    def test_bull_convergence_multi_tf(self) -> None:
        indicators = {
            "1h": _make_indicator("1h", rsi=Decimal("25"), price_vs_bollinger=Decimal("-0.8")),
            "4h": _make_indicator("4h", rsi=Decimal("28"), price_vs_bollinger=Decimal("-0.9")),
        }
        config = {
            "rsi_oversold": 30,
            "rsi_overbought": 70,
            "bb_lower_threshold": -0.7,
            "bb_upper_threshold": 0.7,
            "timeframes": ["1h", "4h"],
        }
        results = evaluate_rsi_bollinger_convergence(indicators, config)
        assert len(results) >= 1
        assert results[0].label == RuleLabel.BULL

    def test_no_convergence(self) -> None:
        indicators = {
            "4h": _make_indicator("4h", rsi=Decimal("50"), price_vs_bollinger=Decimal("0.0")),
        }
        config = {
            "rsi_oversold": 30,
            "rsi_overbought": 70,
            "timeframes": ["4h"],
        }
        results = evaluate_rsi_bollinger_convergence(indicators, config)
        assert results == []


# ---------------------------------------------------------------------------
# Multi-TF alignment
# ---------------------------------------------------------------------------


class TestMultiTfAlignment:
    def test_all_bullish(self) -> None:
        indicators = {
            "1h": _make_indicator("1h", rsi=Decimal("25"), price_vs_bollinger=Decimal("-0.8")),
            "2h": _make_indicator("2h", rsi=Decimal("28"), price_vs_bollinger=Decimal("-0.7")),
            "4h": _make_indicator("4h", rsi=Decimal("22"), price_vs_bollinger=Decimal("-0.9")),
        }
        config = {
            "timeframes": ["1h", "2h", "4h"],
            "rsi_overbought": 70,
            "rsi_oversold": 30,
            "majority_threshold": 0.6,
        }
        results = evaluate_multi_tf_alignment(indicators, config)
        assert len(results) >= 1
        assert results[0].label == RuleLabel.BULL

    def test_mixed_signals_no_alignment(self) -> None:
        indicators = {
            "1h": _make_indicator("1h", rsi=Decimal("25")),
            "2h": _make_indicator("2h", rsi=Decimal("75")),
            "4h": _make_indicator("4h", rsi=Decimal("50")),
        }
        config = {
            "timeframes": ["1h", "2h", "4h"],
            "rsi_overbought": 70,
            "rsi_oversold": 30,
            "majority_threshold": 0.6,
        }
        results = evaluate_multi_tf_alignment(indicators, config)
        assert results == []
