"""Comprehensive unit tests for the ML rules engine.

Tests cover RSI, Bollinger, Harmonic, Trend rules and the RuleEngine
orchestrator, using IndicatorRecord with realistic fixed-timestamp data.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import pytest

from src.ml.rules.bollinger_rules import evaluate_bollinger
from src.ml.rules.engine import RuleEngine, _infer_primary_timeframe, _infer_rule_key
from src.ml.rules.harmonic_rules import evaluate_harmonic
from src.ml.rules.models import RuleResult
from src.ml.rules.rsi_rules import evaluate_rsi
from src.ml.rules.trend_rules import evaluate_trend
from src.shared.models.crypto import IndicatorRecord

# ---------------------------------------------------------------------------
# Fixed timestamps — never datetime.now()
# ---------------------------------------------------------------------------
_T0 = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
_T1 = datetime(2024, 1, 15, 13, 0, 0, tzinfo=timezone.utc)
_T2 = datetime(2024, 1, 15, 14, 0, 0, tzinfo=timezone.utc)
_T3 = datetime(2024, 1, 15, 15, 0, 0, tzinfo=timezone.utc)

_CONFIG_PATH = Path(__file__).parent.parent.parent / "src" / "ml" / "config" / "indicators.yaml"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_indicator(
    *,
    symbol: str = "BTCUSDT",
    timeframe: str = "4h",
    timestamp: datetime = _T0,
    rsi: float | None = None,
    bollinger_upper: float | None = None,
    bollinger_middle: float | None = None,
    bollinger_lower: float | None = None,
    price_vs_bollinger: float | None = None,
    harmonic_pattern: str | None = None,
    trend_slope: float | None = None,
    trend_type: str | None = None,
    metadata: dict | None = None,
) -> IndicatorRecord:
    """Build an IndicatorRecord with only the fields needed by each test."""
    return IndicatorRecord(
        symbol=symbol,
        timeframe=timeframe,
        timestamp=timestamp,
        rsi=Decimal(str(rsi)) if rsi is not None else None,
        bollinger_upper=Decimal(str(bollinger_upper)) if bollinger_upper is not None else None,
        bollinger_middle=Decimal(str(bollinger_middle)) if bollinger_middle is not None else None,
        bollinger_lower=Decimal(str(bollinger_lower)) if bollinger_lower is not None else None,
        price_vs_bollinger=Decimal(str(price_vs_bollinger)) if price_vs_bollinger is not None else None,
        harmonic_pattern=harmonic_pattern,
        trend_slope=Decimal(str(trend_slope)) if trend_slope is not None else None,
        trend_type=trend_type,
        metadata=metadata or {},
    )


def _rsi_config() -> dict:
    return {
        "timeframes": ["1h", "2h", "3h", "4h"],
        "overbought": 70,
        "oversold": 30,
        "convergence_threshold": 5,
    }


def _bollinger_config() -> dict:
    return {
        "timeframes": ["1h", "2h", "3h", "4h", "1D"],
        "squeeze_threshold": 0.02,
    }


def _harmonic_config() -> dict:
    return {
        "timeframes": ["4h", "1D"],
        "tolerance": 0.05,
        "patterns": {
            "gartley": {"xb": 0.618, "ac": [0.382, 0.886], "bd": [1.272, 1.618], "xd": 0.786},
            "butterfly": {"xb": 0.786, "ac": [0.382, 0.886], "bd": [1.618, 2.618], "xd": [1.272, 1.618]},
            "bat": {"xb": [0.382, 0.5], "ac": [0.382, 0.886], "bd": [1.618, 2.618], "xd": 0.886},
            "crab": {"xb": [0.382, 0.618], "ac": [0.382, 0.886], "bd": [2.618, 3.618], "xd": 1.618},
        },
    }


def _trend_config() -> dict:
    return {
        "weekly": {"slope_threshold": 0.001},
        "monthly": {"slope_threshold": 0.005},
    }


# ===========================================================================
# TestRSIRules
# ===========================================================================


class TestRSIRules:
    """Tests for evaluate_rsi() in rsi_rules.py."""

    def test_overbought_multi_tf_convergence(self) -> None:
        """All four TFs converged above overbought → SELL signal."""
        indicators: dict[str, list[IndicatorRecord]] = {
            "1h": [_make_indicator(timeframe="1h", timestamp=_T0, rsi=73.0)],
            "2h": [_make_indicator(timeframe="2h", timestamp=_T0, rsi=75.0)],
            "3h": [_make_indicator(timeframe="3h", timestamp=_T0, rsi=74.0)],
            "4h": [_make_indicator(timeframe="4h", timestamp=_T0, rsi=76.0)],
        }
        result = evaluate_rsi("BTCUSDT", indicators, _rsi_config())

        assert result is not None
        assert result.direction == "SELL"
        assert result.rule_name == "rsi_overbought_multi_tf"
        assert result.confidence >= Decimal("0.5")
        assert result.confidence <= Decimal("1.0")

    def test_overbought_confidence_scales_with_rsi(self) -> None:
        """Higher RSI above the overbought threshold → higher confidence."""
        indicators_high: dict[str, list[IndicatorRecord]] = {
            "1h": [_make_indicator(timeframe="1h", timestamp=_T0, rsi=90.0)],
            "2h": [_make_indicator(timeframe="2h", timestamp=_T0, rsi=92.0)],
            "3h": [_make_indicator(timeframe="3h", timestamp=_T0, rsi=91.0)],
            "4h": [_make_indicator(timeframe="4h", timestamp=_T0, rsi=93.0)],
        }
        indicators_low: dict[str, list[IndicatorRecord]] = {
            "1h": [_make_indicator(timeframe="1h", timestamp=_T0, rsi=71.0)],
            "2h": [_make_indicator(timeframe="2h", timestamp=_T0, rsi=73.0)],
            "3h": [_make_indicator(timeframe="3h", timestamp=_T0, rsi=72.0)],
            "4h": [_make_indicator(timeframe="4h", timestamp=_T0, rsi=74.0)],
        }
        result_high = evaluate_rsi("BTCUSDT", indicators_high, _rsi_config())
        result_low = evaluate_rsi("BTCUSDT", indicators_low, _rsi_config())

        assert result_high is not None
        assert result_low is not None
        assert result_high.confidence > result_low.confidence

    def test_oversold_multi_tf_convergence(self) -> None:
        """All TFs converged below oversold → BUY signal."""
        indicators: dict[str, list[IndicatorRecord]] = {
            "1h": [_make_indicator(timeframe="1h", timestamp=_T0, rsi=22.0)],
            "2h": [_make_indicator(timeframe="2h", timestamp=_T0, rsi=24.0)],
            "3h": [_make_indicator(timeframe="3h", timestamp=_T0, rsi=23.0)],
            "4h": [_make_indicator(timeframe="4h", timestamp=_T0, rsi=25.0)],
        }
        result = evaluate_rsi("BTCUSDT", indicators, _rsi_config())

        assert result is not None
        assert result.direction == "BUY"
        assert result.rule_name == "rsi_oversold_multi_tf"
        assert result.confidence >= Decimal("0.5")
        assert result.confidence <= Decimal("1.0")

    def test_oversold_confidence_scales_with_depth(self) -> None:
        """Deeper oversold (lower RSI) → higher confidence."""
        indicators_deep: dict[str, list[IndicatorRecord]] = {
            "1h": [_make_indicator(timeframe="1h", timestamp=_T0, rsi=5.0)],
            "2h": [_make_indicator(timeframe="2h", timestamp=_T0, rsi=7.0)],
            "3h": [_make_indicator(timeframe="3h", timestamp=_T0, rsi=6.0)],
            "4h": [_make_indicator(timeframe="4h", timestamp=_T0, rsi=8.0)],
        }
        indicators_mild: dict[str, list[IndicatorRecord]] = {
            "1h": [_make_indicator(timeframe="1h", timestamp=_T0, rsi=28.0)],
            "2h": [_make_indicator(timeframe="2h", timestamp=_T0, rsi=29.0)],
            "3h": [_make_indicator(timeframe="3h", timestamp=_T0, rsi=27.0)],
            "4h": [_make_indicator(timeframe="4h", timestamp=_T0, rsi=28.0)],
        }
        result_deep = evaluate_rsi("BTCUSDT", indicators_deep, _rsi_config())
        result_mild = evaluate_rsi("BTCUSDT", indicators_mild, _rsi_config())

        assert result_deep is not None
        assert result_mild is not None
        assert result_deep.confidence > result_mild.confidence

    def test_no_signal_neutral_rsi(self) -> None:
        """Neutral RSI across all TFs → no signal."""
        indicators: dict[str, list[IndicatorRecord]] = {
            "1h": [_make_indicator(timeframe="1h", timestamp=_T0, rsi=50.0)],
            "2h": [_make_indicator(timeframe="2h", timestamp=_T0, rsi=52.0)],
            "3h": [_make_indicator(timeframe="3h", timestamp=_T0, rsi=51.0)],
            "4h": [_make_indicator(timeframe="4h", timestamp=_T0, rsi=53.0)],
        }
        result = evaluate_rsi("BTCUSDT", indicators, _rsi_config())
        assert result is None

    def test_no_signal_when_not_converged(self) -> None:
        """RSI values diverged across TFs → no signal even if extreme."""
        indicators: dict[str, list[IndicatorRecord]] = {
            "1h": [_make_indicator(timeframe="1h", timestamp=_T0, rsi=25.0)],
            "2h": [_make_indicator(timeframe="2h", timestamp=_T0, rsi=40.0)],  # 15 point gap
            "3h": [_make_indicator(timeframe="3h", timestamp=_T0, rsi=55.0)],
            "4h": [_make_indicator(timeframe="4h", timestamp=_T0, rsi=70.0)],
        }
        result = evaluate_rsi("BTCUSDT", indicators, _rsi_config())
        assert result is None

    def test_single_tf_lower_weight(self) -> None:
        """Only one TF available — insufficient data for convergence → no signal."""
        indicators: dict[str, list[IndicatorRecord]] = {
            "4h": [_make_indicator(timeframe="4h", timestamp=_T0, rsi=20.0)],
        }
        result = evaluate_rsi("BTCUSDT", indicators, _rsi_config())
        # Single TF cannot establish convergence — must return None.
        assert result is None

    def test_two_tfs_converged_oversold_produces_signal(self) -> None:
        """Two TFs within threshold and oversold → signal is emitted."""
        indicators: dict[str, list[IndicatorRecord]] = {
            "1h": [_make_indicator(timeframe="1h", timestamp=_T0, rsi=22.0)],
            "2h": [_make_indicator(timeframe="2h", timestamp=_T0, rsi=24.0)],
        }
        result = evaluate_rsi("BTCUSDT", indicators, _rsi_config())
        assert result is not None
        assert result.direction == "BUY"

    def test_no_signal_empty_indicators(self) -> None:
        """Empty indicator dict → no signal."""
        result = evaluate_rsi("BTCUSDT", {}, _rsi_config())
        assert result is None

    def test_no_signal_missing_rsi_field(self) -> None:
        """Records present but rsi field is None across all TFs → no signal."""
        indicators: dict[str, list[IndicatorRecord]] = {
            "1h": [_make_indicator(timeframe="1h", timestamp=_T0, rsi=None)],
            "2h": [_make_indicator(timeframe="2h", timestamp=_T0, rsi=None)],
        }
        result = evaluate_rsi("BTCUSDT", indicators, _rsi_config())
        assert result is None

    def test_latest_record_selected(self) -> None:
        """When multiple records exist, the most recent one is used."""
        indicators: dict[str, list[IndicatorRecord]] = {
            "1h": [
                _make_indicator(timeframe="1h", timestamp=_T0, rsi=50.0),  # older, neutral
                _make_indicator(timeframe="1h", timestamp=_T2, rsi=22.0),  # newest, oversold
            ],
            "2h": [
                _make_indicator(timeframe="2h", timestamp=_T1, rsi=24.0),
            ],
        }
        result = evaluate_rsi("BTCUSDT", indicators, _rsi_config())
        # The latest 1h record (RSI=22) together with 2h (RSI=24) should converge and fire BUY.
        assert result is not None
        assert result.direction == "BUY"


# ===========================================================================
# TestBollingerRules
# ===========================================================================


class TestBollingerRules:
    """Tests for evaluate_bollinger() in bollinger_rules.py."""

    def test_squeeze_detection(self) -> None:
        """Narrow band width below threshold → squeeze, no signal emitted."""
        # Band width: (100.5 - 99.5) / 100.0 = 0.01 < 0.02 squeeze_threshold
        indicators: dict[str, list[IndicatorRecord]] = {
            "4h": [
                _make_indicator(
                    timeframe="4h",
                    timestamp=_T0,
                    bollinger_upper=100.5,
                    bollinger_middle=100.0,
                    bollinger_lower=99.5,
                )
            ],
        }
        result = evaluate_bollinger("BTCUSDT", indicators, _bollinger_config())
        # Squeeze alone must not produce a directional signal.
        assert result is None

    def test_breakout_above(self) -> None:
        """price_vs_bollinger > 1 → BUY breakout signal."""
        indicators: dict[str, list[IndicatorRecord]] = {
            "4h": [
                _make_indicator(
                    timeframe="4h",
                    timestamp=_T0,
                    price_vs_bollinger=1.3,
                    bollinger_upper=102.0,
                    bollinger_middle=100.0,
                    bollinger_lower=98.0,
                )
            ],
        }
        result = evaluate_bollinger("BTCUSDT", indicators, _bollinger_config())

        assert result is not None
        assert result.direction == "BUY"
        assert "breakout" in result.rule_name
        assert result.confidence >= Decimal("0.6")
        assert result.confidence <= Decimal("0.9")

    def test_breakout_below(self) -> None:
        """price_vs_bollinger < -1 → SELL breakout signal."""
        indicators: dict[str, list[IndicatorRecord]] = {
            "4h": [
                _make_indicator(
                    timeframe="4h",
                    timestamp=_T0,
                    price_vs_bollinger=-1.4,
                    bollinger_upper=102.0,
                    bollinger_middle=100.0,
                    bollinger_lower=98.0,
                )
            ],
        }
        result = evaluate_bollinger("BTCUSDT", indicators, _bollinger_config())

        assert result is not None
        assert result.direction == "SELL"
        assert "breakout" in result.rule_name
        assert result.confidence >= Decimal("0.6")

    def test_breakout_confidence_scales_with_distance(self) -> None:
        """A price further outside the band → higher breakout confidence."""

        def _make_breakout_indicators(pvb: float) -> dict[str, list[IndicatorRecord]]:
            return {
                "4h": [
                    _make_indicator(
                        timeframe="4h",
                        timestamp=_T0,
                        price_vs_bollinger=pvb,
                        bollinger_upper=102.0,
                        bollinger_middle=100.0,
                        bollinger_lower=98.0,
                    )
                ]
            }

        result_far = evaluate_bollinger("BTCUSDT", _make_breakout_indicators(1.8), _bollinger_config())
        result_near = evaluate_bollinger("BTCUSDT", _make_breakout_indicators(1.05), _bollinger_config())

        assert result_far is not None
        assert result_near is not None
        assert result_far.confidence >= result_near.confidence

    def test_band_walking_upper_buy(self) -> None:
        """Three consecutive candles with price_vs_bollinger >= 0.7 → BUY walking signal."""
        records = [
            _make_indicator(timeframe="4h", timestamp=_T0, price_vs_bollinger=0.75),
            _make_indicator(timeframe="4h", timestamp=_T1, price_vs_bollinger=0.80),
            _make_indicator(timeframe="4h", timestamp=_T2, price_vs_bollinger=0.78),
        ]
        indicators: dict[str, list[IndicatorRecord]] = {"4h": records}
        result = evaluate_bollinger("BTCUSDT", indicators, _bollinger_config())

        assert result is not None
        assert result.direction == "BUY"
        assert "band_walking" in result.rule_name

    def test_band_walking_lower_sell(self) -> None:
        """Three consecutive candles with price_vs_bollinger <= -0.7 → SELL walking signal."""
        records = [
            _make_indicator(timeframe="4h", timestamp=_T0, price_vs_bollinger=-0.75),
            _make_indicator(timeframe="4h", timestamp=_T1, price_vs_bollinger=-0.80),
            _make_indicator(timeframe="4h", timestamp=_T2, price_vs_bollinger=-0.72),
        ]
        indicators: dict[str, list[IndicatorRecord]] = {"4h": records}
        result = evaluate_bollinger("BTCUSDT", indicators, _bollinger_config())

        assert result is not None
        assert result.direction == "SELL"
        assert "band_walking" in result.rule_name

    def test_no_signal_neutral_bollinger(self) -> None:
        """Price in the middle of bands, no squeeze, no breakout → no signal."""
        indicators: dict[str, list[IndicatorRecord]] = {
            "4h": [
                _make_indicator(
                    timeframe="4h",
                    timestamp=_T0,
                    price_vs_bollinger=0.1,
                    bollinger_upper=110.0,
                    bollinger_middle=100.0,
                    bollinger_lower=90.0,
                )
            ],
        }
        result = evaluate_bollinger("BTCUSDT", indicators, _bollinger_config())
        assert result is None

    def test_no_signal_empty_indicators(self) -> None:
        """No data for any timeframe → no signal."""
        result = evaluate_bollinger("BTCUSDT", {}, _bollinger_config())
        assert result is None

    def test_rsi_bollinger_convergence(self) -> None:
        """price_vs_bollinger triggers a breakout when RSI is also present (field ignored by bollinger rule).

        This test verifies that the Bollinger rule fires independently of RSI —
        convergence across rules is handled by the engine, not within a single rule.
        """
        # RSI field is ignored by evaluate_bollinger; price_vs_bollinger drives the decision.
        indicators: dict[str, list[IndicatorRecord]] = {
            "4h": [
                _make_indicator(
                    timeframe="4h",
                    timestamp=_T0,
                    rsi=25.0,  # oversold RSI alongside a Bollinger breakout below
                    price_vs_bollinger=-1.2,
                    bollinger_upper=102.0,
                    bollinger_middle=100.0,
                    bollinger_lower=98.0,
                )
            ],
        }
        result = evaluate_bollinger("BTCUSDT", indicators, _bollinger_config())

        assert result is not None
        assert result.direction == "SELL"

    def test_primary_tf_preference_4h_over_1h(self) -> None:
        """4h is preferred as primary timeframe over 1h even when both are available."""
        indicators: dict[str, list[IndicatorRecord]] = {
            "1h": [
                _make_indicator(
                    timeframe="1h",
                    timestamp=_T0,
                    price_vs_bollinger=1.5,
                    bollinger_upper=102.0,
                    bollinger_middle=100.0,
                    bollinger_lower=98.0,
                )
            ],
            "4h": [
                _make_indicator(
                    timeframe="4h",
                    timestamp=_T0,
                    price_vs_bollinger=1.6,
                    bollinger_upper=102.0,
                    bollinger_middle=100.0,
                    bollinger_lower=98.0,
                )
            ],
        }
        result = evaluate_bollinger("BTCUSDT", indicators, _bollinger_config())

        assert result is not None
        assert "4h" in result.rule_name


# ===========================================================================
# TestHarmonicRules
# ===========================================================================


class TestHarmonicRules:
    """Tests for evaluate_harmonic() in harmonic_rules.py."""

    def test_gartley_bull(self) -> None:
        """Gartley pattern without bearish suffix → BUY direction."""
        indicators: dict[str, list[IndicatorRecord]] = {
            "4h": [
                _make_indicator(
                    timeframe="4h",
                    timestamp=_T0,
                    harmonic_pattern="gartley",
                    metadata={"xb_ratio": 0.618, "ac_ratio": 0.65, "bd_ratio": 1.4, "xd_ratio": 0.786},
                )
            ],
        }
        result = evaluate_harmonic("BTCUSDT", indicators, _harmonic_config())

        assert result is not None
        assert result.direction == "BUY"
        assert "gartley" in result.rule_name
        assert result.confidence > Decimal("0")
        assert result.confidence <= Decimal("1.0")

    def test_gartley_bear(self) -> None:
        """Gartley pattern with _bearish suffix → SELL direction."""
        indicators: dict[str, list[IndicatorRecord]] = {
            "4h": [
                _make_indicator(
                    timeframe="4h",
                    timestamp=_T0,
                    harmonic_pattern="gartley_bearish",
                    metadata={"xb_ratio": 0.618, "ac_ratio": 0.65, "bd_ratio": 1.4, "xd_ratio": 0.786},
                )
            ],
        }
        result = evaluate_harmonic("BTCUSDT", indicators, _harmonic_config())

        assert result is not None
        assert result.direction == "SELL"

    def test_butterfly_bear(self) -> None:
        """Butterfly_sell suffix → SELL direction with butterfly confidence base."""
        indicators: dict[str, list[IndicatorRecord]] = {
            "4h": [
                _make_indicator(
                    timeframe="4h",
                    timestamp=_T0,
                    harmonic_pattern="butterfly_sell",
                    metadata={"xb_ratio": 0.786, "ac_ratio": 0.60, "bd_ratio": 2.0, "xd_ratio": 1.35},
                )
            ],
        }
        result = evaluate_harmonic("BTCUSDT", indicators, _harmonic_config())

        assert result is not None
        assert result.direction == "SELL"
        assert "butterfly" in result.rule_name

    def test_butterfly_bull(self) -> None:
        """Butterfly pattern without bearish suffix → BUY."""
        indicators: dict[str, list[IndicatorRecord]] = {
            "4h": [
                _make_indicator(
                    timeframe="4h",
                    timestamp=_T0,
                    harmonic_pattern="butterfly_bullish",
                    metadata={"xb_ratio": 0.786, "ac_ratio": 0.60, "bd_ratio": 2.0, "xd_ratio": 1.35},
                )
            ],
        }
        result = evaluate_harmonic("BTCUSDT", indicators, _harmonic_config())

        assert result is not None
        assert result.direction == "BUY"

    def test_bat_pattern(self) -> None:
        """Bat pattern → BUY with correct confidence range."""
        indicators: dict[str, list[IndicatorRecord]] = {
            "4h": [
                _make_indicator(
                    timeframe="4h",
                    timestamp=_T0,
                    harmonic_pattern="bat",
                    metadata={"xb_ratio": 0.45, "ac_ratio": 0.60, "bd_ratio": 2.0, "xd_ratio": 0.886},
                )
            ],
        }
        result = evaluate_harmonic("BTCUSDT", indicators, _harmonic_config())

        assert result is not None
        assert result.direction == "BUY"
        assert result.confidence > Decimal("0.5")

    def test_crab_pattern_high_confidence(self) -> None:
        """Crab has the highest base confidence (0.75)."""
        indicators: dict[str, list[IndicatorRecord]] = {
            "4h": [
                _make_indicator(
                    timeframe="4h",
                    timestamp=_T0,
                    harmonic_pattern="crab",
                    metadata={"xb_ratio": 0.50, "ac_ratio": 0.60, "bd_ratio": 3.0, "xd_ratio": 1.618},
                )
            ],
        }
        result = evaluate_harmonic("BTCUSDT", indicators, _harmonic_config())

        assert result is not None
        # Crab base confidence is 0.75 — with ratio scoring it should remain >= 0.5
        assert result.confidence >= Decimal("0.5")

    def test_no_pattern(self) -> None:
        """No harmonic_pattern field populated → no signal."""
        indicators: dict[str, list[IndicatorRecord]] = {
            "4h": [
                _make_indicator(
                    timeframe="4h",
                    timestamp=_T0,
                    harmonic_pattern=None,
                )
            ],
        }
        result = evaluate_harmonic("BTCUSDT", indicators, _harmonic_config())
        assert result is None

    def test_unknown_pattern_skipped(self) -> None:
        """Unrecognised pattern name → no signal (logged as warning)."""
        indicators: dict[str, list[IndicatorRecord]] = {
            "4h": [
                _make_indicator(
                    timeframe="4h",
                    timestamp=_T0,
                    harmonic_pattern="dragon_fly",
                )
            ],
        }
        result = evaluate_harmonic("BTCUSDT", indicators, _harmonic_config())
        assert result is None

    def test_best_confidence_wins_across_timeframes(self) -> None:
        """When patterns found on multiple TFs, the one with higher confidence is returned."""
        indicators: dict[str, list[IndicatorRecord]] = {
            "4h": [
                _make_indicator(
                    timeframe="4h",
                    timestamp=_T0,
                    harmonic_pattern="gartley",
                    # Partial ratio match → lower score multiplier
                    metadata={},
                )
            ],
            "1D": [
                _make_indicator(
                    timeframe="1D",
                    timestamp=_T0,
                    harmonic_pattern="crab",
                    # All ratios match perfectly → high multiplier
                    metadata={"xb_ratio": 0.50, "ac_ratio": 0.60, "bd_ratio": 3.0, "xd_ratio": 1.618},
                )
            ],
        }
        result = evaluate_harmonic("BTCUSDT", indicators, _harmonic_config())

        assert result is not None
        # Crab (0.75 base) with full ratio match should beat gartley (0.72) with no metadata.
        assert "crab" in result.rule_name

    def test_no_signal_empty_indicators(self) -> None:
        """No data for any timeframe → no signal."""
        result = evaluate_harmonic("BTCUSDT", {}, _harmonic_config())
        assert result is None

    def test_ratio_validation_tolerance(self) -> None:
        """Ratios slightly outside spec but within tolerance → pattern still valid."""
        indicators: dict[str, list[IndicatorRecord]] = {
            "4h": [
                _make_indicator(
                    timeframe="4h",
                    timestamp=_T0,
                    harmonic_pattern="gartley",
                    # xb_ratio spec is 0.618 ± 0.05 → 0.66 is valid
                    metadata={"xb_ratio": 0.66, "xd_ratio": 0.80},
                )
            ],
        }
        result = evaluate_harmonic("BTCUSDT", indicators, _harmonic_config())
        assert result is not None


# ===========================================================================
# TestTrendRules
# ===========================================================================


class TestTrendRules:
    """Tests for evaluate_trend() in trend_rules.py."""

    def test_trend_alignment_bull(self) -> None:
        """Both weekly and monthly trending up, monthly aggressive → BUY signal."""
        indicators: dict[str, list[IndicatorRecord]] = {
            "1W": [
                _make_indicator(
                    timeframe="1W",
                    timestamp=_T0,
                    trend_slope=0.003,  # above weekly stable threshold (0.001) → not stable
                    trend_type="aggressive",
                )
            ],
            "1M": [
                _make_indicator(
                    timeframe="1M",
                    timestamp=_T0,
                    trend_slope=0.010,  # well above monthly threshold (0.005)
                    trend_type="aggressive",
                )
            ],
        }
        result = evaluate_trend("BTCUSDT", indicators, _trend_config())

        assert result is not None
        assert result.direction == "BUY"
        assert result.confidence >= Decimal("0.6")
        assert result.confidence <= Decimal("0.85")

    def test_trend_alignment_bear(self) -> None:
        """Both weekly and monthly trending down, monthly aggressive → SELL signal."""
        indicators: dict[str, list[IndicatorRecord]] = {
            "1W": [
                _make_indicator(
                    timeframe="1W",
                    timestamp=_T0,
                    trend_slope=-0.003,
                    trend_type="aggressive",
                )
            ],
            "1M": [
                _make_indicator(
                    timeframe="1M",
                    timestamp=_T0,
                    trend_slope=-0.010,
                    trend_type="aggressive",
                )
            ],
        }
        result = evaluate_trend("BTCUSDT", indicators, _trend_config())

        assert result is not None
        assert result.direction == "SELL"
        assert result.confidence >= Decimal("0.6")

    def test_trend_dip_signal(self) -> None:
        """Stable weekly + aggressive monthly uptrend → dip-buy BUY signal."""
        indicators: dict[str, list[IndicatorRecord]] = {
            "1W": [
                _make_indicator(
                    timeframe="1W",
                    timestamp=_T0,
                    trend_slope=0.0005,  # below stable threshold → weekly is stable
                    trend_type="stable",
                )
            ],
            "1M": [
                _make_indicator(
                    timeframe="1M",
                    timestamp=_T0,
                    trend_slope=0.010,  # above monthly aggressive threshold
                    trend_type="aggressive",
                )
            ],
        }
        result = evaluate_trend("BTCUSDT", indicators, _trend_config())

        assert result is not None
        assert result.direction == "BUY"
        assert result.rule_name == "trend_stable_weekly_aggressive_monthly_buy"
        assert result.confidence <= Decimal("0.95")

    def test_no_signal_diverging_trends(self) -> None:
        """Weekly and monthly point in opposite directions → no signal."""
        indicators: dict[str, list[IndicatorRecord]] = {
            "1W": [
                _make_indicator(
                    timeframe="1W",
                    timestamp=_T0,
                    trend_slope=0.003,  # up
                )
            ],
            "1M": [
                _make_indicator(
                    timeframe="1M",
                    timestamp=_T0,
                    trend_slope=-0.010,  # down
                )
            ],
        }
        result = evaluate_trend("BTCUSDT", indicators, _trend_config())
        assert result is None

    def test_no_signal_monthly_not_aggressive(self) -> None:
        """Monthly slope below aggressive threshold → no signal."""
        indicators: dict[str, list[IndicatorRecord]] = {
            "1W": [
                _make_indicator(
                    timeframe="1W",
                    timestamp=_T0,
                    trend_slope=0.003,
                )
            ],
            "1M": [
                _make_indicator(
                    timeframe="1M",
                    timestamp=_T0,
                    trend_slope=0.002,  # below 0.005 threshold → not aggressive
                )
            ],
        }
        result = evaluate_trend("BTCUSDT", indicators, _trend_config())
        assert result is None

    def test_no_signal_missing_weekly_data(self) -> None:
        """Missing weekly records → no signal."""
        indicators: dict[str, list[IndicatorRecord]] = {
            "1M": [
                _make_indicator(
                    timeframe="1M",
                    timestamp=_T0,
                    trend_slope=0.010,
                )
            ],
        }
        result = evaluate_trend("BTCUSDT", indicators, _trend_config())
        assert result is None

    def test_no_signal_missing_monthly_data(self) -> None:
        """Missing monthly records → no signal."""
        indicators: dict[str, list[IndicatorRecord]] = {
            "1W": [
                _make_indicator(
                    timeframe="1W",
                    timestamp=_T0,
                    trend_slope=0.003,
                )
            ],
        }
        result = evaluate_trend("BTCUSDT", indicators, _trend_config())
        assert result is None

    def test_no_signal_missing_trend_slope(self) -> None:
        """trend_slope field is None → no signal."""
        indicators: dict[str, list[IndicatorRecord]] = {
            "1W": [_make_indicator(timeframe="1W", timestamp=_T0, trend_slope=None)],
            "1M": [_make_indicator(timeframe="1M", timestamp=_T0, trend_slope=None)],
        }
        result = evaluate_trend("BTCUSDT", indicators, _trend_config())
        assert result is None

    def test_confidence_clamped_to_095(self) -> None:
        """Dip-buy confidence must not exceed 0.95."""
        indicators: dict[str, list[IndicatorRecord]] = {
            "1W": [
                _make_indicator(
                    timeframe="1W",
                    timestamp=_T0,
                    trend_slope=0.00001,  # extremely stable weekly
                )
            ],
            "1M": [
                _make_indicator(
                    timeframe="1M",
                    timestamp=_T0,
                    trend_slope=100.0,  # extremely aggressive monthly
                )
            ],
        }
        result = evaluate_trend("BTCUSDT", indicators, _trend_config())
        assert result is not None
        assert result.confidence <= Decimal("0.95")

    def test_latest_record_selected_for_trend(self) -> None:
        """Older records are ignored; only the most recent weekly/monthly record is used."""
        indicators: dict[str, list[IndicatorRecord]] = {
            "1W": [
                _make_indicator(timeframe="1W", timestamp=_T0, trend_slope=-0.010),  # old, down
                _make_indicator(timeframe="1W", timestamp=_T2, trend_slope=0.0005),  # new, stable up
            ],
            "1M": [
                _make_indicator(timeframe="1M", timestamp=_T1, trend_slope=0.010),  # aggressive up
            ],
        }
        result = evaluate_trend("BTCUSDT", indicators, _trend_config())
        assert result is not None
        assert result.direction == "BUY"


# ===========================================================================
# TestRuleEngine
# ===========================================================================


class TestRuleEngine:
    """Tests for RuleEngine in engine.py."""

    @pytest.fixture
    def engine(self) -> RuleEngine:
        return RuleEngine.from_yaml(_CONFIG_PATH)

    def test_engine_loads_yaml(self, engine: RuleEngine) -> None:
        """Engine must load config dict from the YAML file."""
        assert isinstance(engine.config, dict)
        assert "rsi" in engine.config
        assert "bollinger" in engine.config
        assert "harmonic" in engine.config
        assert "trend" in engine.config

    def test_file_not_found_raises(self) -> None:
        """Missing config file → FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            RuleEngine(Path("/nonexistent/path/indicators.yaml"))

    def test_evaluate_all_bull(self, engine: RuleEngine) -> None:
        """Strongly oversold RSI + lower Bollinger breakout + gartley + stable/aggressive trend → BUY signal."""
        indicators: dict[str, list[IndicatorRecord]] = {
            # RSI: all TFs oversold and converged
            "1h": [_make_indicator(timeframe="1h", timestamp=_T0, rsi=20.0)],
            "2h": [_make_indicator(timeframe="2h", timestamp=_T0, rsi=21.0)],
            "3h": [_make_indicator(timeframe="3h", timestamp=_T0, rsi=22.0)],
            "4h": [
                _make_indicator(
                    timeframe="4h",
                    timestamp=_T0,
                    rsi=22.0,
                    price_vs_bollinger=-1.5,  # Bollinger downward breakout → SELL
                    bollinger_upper=110.0,
                    bollinger_middle=100.0,
                    bollinger_lower=90.0,
                    harmonic_pattern="gartley",
                    metadata={"xb_ratio": 0.618, "xd_ratio": 0.786},
                )
            ],
            # Harmonic on 1D as well for extra coverage
            "1D": [
                _make_indicator(
                    timeframe="1D",
                    timestamp=_T0,
                    harmonic_pattern=None,
                )
            ],
            # Trend: dip-buy setup
            "1W": [_make_indicator(timeframe="1W", timestamp=_T0, trend_slope=0.0005)],
            "1M": [_make_indicator(timeframe="1M", timestamp=_T0, trend_slope=0.010)],
        }
        results = engine.evaluate("BTCUSDT", indicators)

        # At minimum the RSI rule must fire a BUY.
        rule_names = [r.rule_name for r in results]
        assert "rsi_oversold_multi_tf" in rule_names

        # All results must have valid direction/label and bounded confidence/weight.
        for r in results:
            if r.direction:
                assert r.direction in ("BUY", "SELL")
                assert Decimal("0") < r.confidence <= Decimal("1")
            else:
                from src.ml.rules.models import RuleLabel

                assert r.label in (RuleLabel.BULL, RuleLabel.BEAR)
                assert 0.0 < r.weight <= 1.0

    def test_evaluate_mixed_signals(self, engine: RuleEngine) -> None:
        """RSI oversold (BUY) but Bollinger upward breakout (BUY too) — engine aggregates."""
        indicators: dict[str, list[IndicatorRecord]] = {
            "1h": [_make_indicator(timeframe="1h", timestamp=_T0, rsi=22.0)],
            "2h": [_make_indicator(timeframe="2h", timestamp=_T0, rsi=24.0)],
            "3h": [_make_indicator(timeframe="3h", timestamp=_T0, rsi=23.0)],
            "4h": [
                _make_indicator(
                    timeframe="4h",
                    timestamp=_T0,
                    rsi=25.0,
                    price_vs_bollinger=1.3,  # BUY breakout
                    bollinger_upper=110.0,
                    bollinger_middle=100.0,
                    bollinger_lower=90.0,
                )
            ],
        }
        results = engine.evaluate("BTCUSDT", indicators)
        assert len(results) >= 1

        signal = engine.aggregate(results, symbol="BTCUSDT")
        # Both RSI and Bollinger say BUY → aggregated signal should be BUY (if threshold met)
        if signal is not None:
            assert signal.signal_type in ("BUY", "SELL")
            assert signal.confidence_score >= Decimal("0.6")

    def test_evaluate_no_data(self, engine: RuleEngine) -> None:
        """Empty indicator dict → no rules fire, aggregate returns None."""
        results = engine.evaluate("BTCUSDT", {})
        assert results == []

        signal = engine.aggregate(results, symbol="BTCUSDT")
        assert signal is None

    def test_aggregate_returns_none_below_threshold(self, engine: RuleEngine) -> None:
        """Low-confidence single result → aggregate returns None."""
        results = [
            RuleResult(
                direction="BUY",
                confidence=Decimal("0.3"),  # well below 0.6 threshold
                reason="test low confidence",
                rule_name="rsi_oversold_multi_tf",
            )
        ]
        signal = engine.aggregate(results, symbol="BTCUSDT")
        assert signal is None

    def test_aggregate_single_high_confidence_buy(self, engine: RuleEngine) -> None:
        """Single BUY result above threshold → signal emitted with correct symbol."""
        results = [
            RuleResult(
                direction="BUY",
                confidence=Decimal("0.80"),
                reason="RSI oversold converged across 4 TFs",
                rule_name="rsi_oversold_multi_tf",
            )
        ]
        signal = engine.aggregate(results, symbol="ETHUSDT")

        assert signal is not None
        assert signal.symbol == "ETHUSDT"
        assert signal.signal_type == "BUY"
        assert signal.confidence_score >= Decimal("0.6")
        assert "rsi_oversold_multi_tf" in signal.rules_triggered

    def test_aggregate_opposing_results_penalise_confidence(self, engine: RuleEngine) -> None:
        """BUY and SELL results partially cancel each other, lowering confidence."""
        buy_only_results = [
            RuleResult(
                direction="BUY",
                confidence=Decimal("0.80"),
                reason="RSI oversold",
                rule_name="rsi_oversold_multi_tf",
            ),
            RuleResult(
                direction="BUY",
                confidence=Decimal("0.75"),
                reason="Bollinger breakout",
                rule_name="bollinger_breakout_4h",
            ),
        ]
        mixed_results = [
            RuleResult(
                direction="BUY",
                confidence=Decimal("0.80"),
                reason="RSI oversold",
                rule_name="rsi_oversold_multi_tf",
            ),
            RuleResult(
                direction="SELL",
                confidence=Decimal("0.75"),
                reason="Bollinger downward breakout",
                rule_name="bollinger_breakout_4h",
            ),
        ]

        signal_pure = engine.aggregate(buy_only_results, symbol="BTCUSDT")
        signal_mixed = engine.aggregate(mixed_results, symbol="BTCUSDT")

        # Pure BUY signal must have higher or equal confidence than the conflicted one.
        if signal_pure is not None and signal_mixed is not None:
            assert signal_pure.confidence_score >= signal_mixed.confidence_score

    def test_aggregate_dominant_direction_wins(self, engine: RuleEngine) -> None:
        """When multiple SELL results outweigh a single BUY → SELL signal."""
        results = [
            RuleResult(
                direction="SELL",
                confidence=Decimal("0.80"),
                reason="RSI overbought",
                rule_name="rsi_overbought_multi_tf",
            ),
            RuleResult(
                direction="SELL",
                confidence=Decimal("0.75"),
                reason="Bollinger breakout",
                rule_name="bollinger_breakout_4h",
            ),
            RuleResult(
                direction="BUY",
                confidence=Decimal("0.62"),
                reason="Harmonic gartley",
                rule_name="harmonic_gartley_4h",
            ),
        ]
        signal = engine.aggregate(results, symbol="BTCUSDT")

        assert signal is not None
        assert signal.signal_type == "SELL"

    def test_aggregate_model_version(self, engine: RuleEngine) -> None:
        """Emitted TradingSignal must carry the correct model version."""
        results = [
            RuleResult(
                direction="BUY",
                confidence=Decimal("0.85"),
                reason="RSI oversold",
                rule_name="rsi_oversold_multi_tf",
            )
        ]
        signal = engine.aggregate(results, symbol="BTCUSDT")

        assert signal is not None
        assert signal.model_version == "rules_v1"

    def test_evaluate_exception_in_rule_does_not_propagate(self, engine: RuleEngine) -> None:
        """A crashing rule is skipped; engine still returns results from healthy rules."""
        indicators: dict[str, list[IndicatorRecord]] = {
            "1h": [_make_indicator(timeframe="1h", timestamp=_T0, rsi=22.0)],
            "2h": [_make_indicator(timeframe="2h", timestamp=_T0, rsi=24.0)],
            "3h": [_make_indicator(timeframe="3h", timestamp=_T0, rsi=23.0)],
            "4h": [_make_indicator(timeframe="4h", timestamp=_T0, rsi=25.0)],
        }

        def _crashing_bollinger(symbol: str, inds: dict, cfg: dict) -> RuleResult | None:
            raise RuntimeError("simulated crash")

        with patch("src.ml.rules.bollinger_rules.evaluate_bollinger", side_effect=_crashing_bollinger):
            results = engine.evaluate("BTCUSDT", indicators)

        # RSI rule should still fire.
        rule_names = [r.rule_name for r in results]
        assert any("rsi" in name for name in rule_names)

    def test_from_yaml_default_path(self) -> None:
        """RuleEngine.from_yaml() with no argument uses the bundled config."""
        engine = RuleEngine.from_yaml()
        assert "rsi" in engine.config


# ===========================================================================
# TestPrivateHelpers
# ===========================================================================


class TestPrivateHelpers:
    """Tests for module-level helpers in engine.py."""

    def test_infer_rule_key_rsi(self) -> None:
        assert _infer_rule_key("rsi_oversold_multi_tf") == "rsi"

    def test_infer_rule_key_bollinger(self) -> None:
        assert _infer_rule_key("bollinger_breakout_4h") == "bollinger"

    def test_infer_rule_key_harmonic(self) -> None:
        assert _infer_rule_key("harmonic_gartley_4h") == "harmonic"

    def test_infer_rule_key_trend(self) -> None:
        assert _infer_rule_key("trend_aligned_buy") == "trend"

    def test_infer_rule_key_unknown_fallback(self) -> None:
        assert _infer_rule_key("unknown_rule_xyz") == "rsi"

    def test_infer_primary_timeframe_prefers_4h(self) -> None:
        results = [
            RuleResult(
                direction="BUY", confidence=Decimal("0.8"), reason="RSI 4h signal", rule_name="rsi_oversold_multi_tf"
            ),
        ]
        tf = _infer_primary_timeframe(results)
        assert tf == "4h"

    def test_infer_primary_timeframe_reason_match(self) -> None:
        """Primary TF extracted from rule reason string when not in rule_name."""
        results = [
            RuleResult(
                direction="BUY",
                confidence=Decimal("0.8"),
                reason="Bollinger upward breakout on 1D (price_vs_bb=1.30)",
                rule_name="bollinger_breakout_something",
            )
        ]
        tf = _infer_primary_timeframe(results)
        assert tf == "1D"

    def test_infer_primary_timeframe_default(self) -> None:
        """No recognisable TF in results → default to 4h."""
        results = [
            RuleResult(
                direction="BUY",
                confidence=Decimal("0.8"),
                reason="Some generic reason with no TF hint",
                rule_name="some_generic_rule",
            )
        ]
        tf = _infer_primary_timeframe(results)
        assert tf == "4h"
