"""Tests for RSI rule evaluation and multi-timeframe convergence."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from src.ml.rules.models import RuleLabel, RuleResult
from src.ml.rules.rsi_rules import (
    evaluate_rsi_multi_tf_convergence,
    evaluate_rsi_overbought,
    evaluate_rsi_oversold,
)
from src.shared.models.crypto import IndicatorRecord

# Fixed timestamp for reproducibility
_FIXED_TS = datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc)


class TestRSIOverbought:
    """Test RSI overbought detection (RSI > 70)."""

    def test_rsi_above_threshold_returns_sell_signal(self) -> None:
        """RSI = 75 should trigger SELL."""
        indicators = {
            "4h": [
                IndicatorRecord(
                    symbol="BTCUSDT",
                    timeframe="4h",
                    timestamp=_FIXED_TS,
                    rsi=Decimal("75"),
                    bollinger_upper=Decimal("45000"),
                    bollinger_middle=Decimal("43000"),
                    bollinger_lower=Decimal("41000"),
                    price_vs_bollinger=Decimal("0.5"),
                    trend_slope=Decimal("0.001"),
                    trend_type="uptrend",
                )
            ]
        }

        result = evaluate_rsi_overbought(indicators)
        assert result is not None
        assert result.direction == "SELL"
        assert result.confidence >= Decimal("0.6")

    def test_rsi_at_threshold_boundary_triggers_signal(self) -> None:
        """RSI = 70 (boundary) should trigger signal."""
        indicators = {
            "4h": [
                IndicatorRecord(
                    symbol="BTCUSDT",
                    timeframe="4h",
                    timestamp=_FIXED_TS,
                    rsi=Decimal("70"),
                    bollinger_upper=Decimal("45000"),
                    bollinger_middle=Decimal("43000"),
                    bollinger_lower=Decimal("41000"),
                    price_vs_bollinger=Decimal("0.5"),
                    trend_slope=Decimal("0.001"),
                    trend_type="uptrend",
                )
            ]
        }

        result = evaluate_rsi_overbought(indicators)
        assert result is not None
        assert result.direction == "SELL"

    def test_rsi_below_threshold_no_signal(self) -> None:
        """RSI = 65 should NOT trigger overbought signal."""
        indicators = {
            "4h": [
                IndicatorRecord(
                    symbol="BTCUSDT",
                    timeframe="4h",
                    timestamp=_FIXED_TS,
                    rsi=Decimal("65"),
                    bollinger_upper=Decimal("45000"),
                    bollinger_middle=Decimal("43000"),
                    bollinger_lower=Decimal("41000"),
                    price_vs_bollinger=Decimal("0.5"),
                    trend_slope=Decimal("0.001"),
                    trend_type="uptrend",
                )
            ]
        }

        result = evaluate_rsi_overbought(indicators)
        # Should return None or a neutral result
        assert result is None or result.direction != "SELL"

    def test_rsi_extremely_overbought_high_confidence(self) -> None:
        """RSI = 90 should have high confidence."""
        indicators = {
            "4h": [
                IndicatorRecord(
                    symbol="BTCUSDT",
                    timeframe="4h",
                    timestamp=_FIXED_TS,
                    rsi=Decimal("90"),
                    bollinger_upper=Decimal("45000"),
                    bollinger_middle=Decimal("43000"),
                    bollinger_lower=Decimal("41000"),
                    price_vs_bollinger=Decimal("0.5"),
                    trend_slope=Decimal("0.001"),
                    trend_type="uptrend",
                )
            ]
        }

        result = evaluate_rsi_overbought(indicators)
        assert result is not None
        assert result.confidence > Decimal("0.7")


class TestRSIOversold:
    """Test RSI oversold detection (RSI < 30)."""

    def test_rsi_below_threshold_returns_buy_signal(self) -> None:
        """RSI = 25 should trigger BUY."""
        indicators = {
            "4h": [
                IndicatorRecord(
                    symbol="BTCUSDT",
                    timeframe="4h",
                    timestamp=_FIXED_TS,
                    rsi=Decimal("25"),
                    bollinger_upper=Decimal("45000"),
                    bollinger_middle=Decimal("43000"),
                    bollinger_lower=Decimal("41000"),
                    price_vs_bollinger=Decimal("0.5"),
                    trend_slope=Decimal("0.001"),
                    trend_type="uptrend",
                )
            ]
        }

        result = evaluate_rsi_oversold(indicators)
        assert result is not None
        assert result.direction == "BUY"
        assert result.confidence >= Decimal("0.6")

    def test_rsi_at_threshold_boundary_triggers_signal(self) -> None:
        """RSI = 30 (boundary) should trigger signal."""
        indicators = {
            "4h": [
                IndicatorRecord(
                    symbol="BTCUSDT",
                    timeframe="4h",
                    timestamp=_FIXED_TS,
                    rsi=Decimal("30"),
                    bollinger_upper=Decimal("45000"),
                    bollinger_middle=Decimal("43000"),
                    bollinger_lower=Decimal("41000"),
                    price_vs_bollinger=Decimal("0.5"),
                    trend_slope=Decimal("0.001"),
                    trend_type="uptrend",
                )
            ]
        }

        result = evaluate_rsi_oversold(indicators)
        assert result is not None
        assert result.direction == "BUY"

    def test_rsi_above_threshold_no_signal(self) -> None:
        """RSI = 35 should NOT trigger oversold signal."""
        indicators = {
            "4h": [
                IndicatorRecord(
                    symbol="BTCUSDT",
                    timeframe="4h",
                    timestamp=_FIXED_TS,
                    rsi=Decimal("35"),
                    bollinger_upper=Decimal("45000"),
                    bollinger_middle=Decimal("43000"),
                    bollinger_lower=Decimal("41000"),
                    price_vs_bollinger=Decimal("0.5"),
                    trend_slope=Decimal("0.001"),
                    trend_type="uptrend",
                )
            ]
        }

        result = evaluate_rsi_oversold(indicators)
        assert result is None or result.direction != "BUY"

    def test_rsi_extremely_oversold_high_confidence(self) -> None:
        """RSI = 10 should have high confidence."""
        indicators = {
            "4h": [
                IndicatorRecord(
                    symbol="BTCUSDT",
                    timeframe="4h",
                    timestamp=_FIXED_TS,
                    rsi=Decimal("10"),
                    bollinger_upper=Decimal("45000"),
                    bollinger_middle=Decimal("43000"),
                    bollinger_lower=Decimal("41000"),
                    price_vs_bollinger=Decimal("0.5"),
                    trend_slope=Decimal("0.001"),
                    trend_type="uptrend",
                )
            ]
        }

        result = evaluate_rsi_oversold(indicators)
        assert result is not None
        assert result.confidence > Decimal("0.7")


class TestRSIMultiTFConvergence:
    """Test multi-timeframe RSI convergence."""

    def test_all_timeframes_oversold_triggers_buy(self) -> None:
        """All TFs with RSI < 30 should trigger BUY."""
        indicators = {
            "1h": [
                IndicatorRecord(
                    symbol="BTCUSDT",
                    timeframe="1h",
                    timestamp=_FIXED_TS,
                    rsi=Decimal("25"),
                    bollinger_upper=Decimal("45000"),
                    bollinger_middle=Decimal("43000"),
                    bollinger_lower=Decimal("41000"),
                    price_vs_bollinger=Decimal("0.5"),
                    trend_slope=Decimal("0.001"),
                    trend_type="uptrend",
                )
            ],
            "2h": [
                IndicatorRecord(
                    symbol="BTCUSDT",
                    timeframe="2h",
                    timestamp=_FIXED_TS,
                    rsi=Decimal("22"),
                    bollinger_upper=Decimal("45000"),
                    bollinger_middle=Decimal("43000"),
                    bollinger_lower=Decimal("41000"),
                    price_vs_bollinger=Decimal("0.5"),
                    trend_slope=Decimal("0.001"),
                    trend_type="uptrend",
                )
            ],
            "3h": [
                IndicatorRecord(
                    symbol="BTCUSDT",
                    timeframe="3h",
                    timestamp=_FIXED_TS,
                    rsi=Decimal("28"),
                    bollinger_upper=Decimal("45000"),
                    bollinger_middle=Decimal("43000"),
                    bollinger_lower=Decimal("41000"),
                    price_vs_bollinger=Decimal("0.5"),
                    trend_slope=Decimal("0.001"),
                    trend_type="uptrend",
                )
            ],
            "4h": [
                IndicatorRecord(
                    symbol="BTCUSDT",
                    timeframe="4h",
                    timestamp=_FIXED_TS,
                    rsi=Decimal("20"),
                    bollinger_upper=Decimal("45000"),
                    bollinger_middle=Decimal("43000"),
                    bollinger_lower=Decimal("41000"),
                    price_vs_bollinger=Decimal("0.5"),
                    trend_slope=Decimal("0.001"),
                    trend_type="uptrend",
                )
            ],
        }

        result = evaluate_rsi_multi_tf_convergence(indicators)
        assert result is not None
        assert result.label == RuleLabel.BULL

    def test_all_timeframes_overbought_triggers_sell(self) -> None:
        """All TFs with RSI > 70 should trigger SELL."""
        indicators = {
            "1h": [
                IndicatorRecord(
                    symbol="BTCUSDT",
                    timeframe="1h",
                    timestamp=_FIXED_TS,
                    rsi=Decimal("78"),
                    bollinger_upper=Decimal("45000"),
                    bollinger_middle=Decimal("43000"),
                    bollinger_lower=Decimal("41000"),
                    price_vs_bollinger=Decimal("0.5"),
                    trend_slope=Decimal("0.001"),
                    trend_type="uptrend",
                )
            ],
            "2h": [
                IndicatorRecord(
                    symbol="BTCUSDT",
                    timeframe="2h",
                    timestamp=_FIXED_TS,
                    rsi=Decimal("80"),
                    bollinger_upper=Decimal("45000"),
                    bollinger_middle=Decimal("43000"),
                    bollinger_lower=Decimal("41000"),
                    price_vs_bollinger=Decimal("0.5"),
                    trend_slope=Decimal("0.001"),
                    trend_type="uptrend",
                )
            ],
            "3h": [
                IndicatorRecord(
                    symbol="BTCUSDT",
                    timeframe="3h",
                    timestamp=_FIXED_TS,
                    rsi=Decimal("75"),
                    bollinger_upper=Decimal("45000"),
                    bollinger_middle=Decimal("43000"),
                    bollinger_lower=Decimal("41000"),
                    price_vs_bollinger=Decimal("0.5"),
                    trend_slope=Decimal("0.001"),
                    trend_type="uptrend",
                )
            ],
            "4h": [
                IndicatorRecord(
                    symbol="BTCUSDT",
                    timeframe="4h",
                    timestamp=_FIXED_TS,
                    rsi=Decimal("82"),
                    bollinger_upper=Decimal("45000"),
                    bollinger_middle=Decimal("43000"),
                    bollinger_lower=Decimal("41000"),
                    price_vs_bollinger=Decimal("0.5"),
                    trend_slope=Decimal("0.001"),
                    trend_type="uptrend",
                )
            ],
        }

        result = evaluate_rsi_multi_tf_convergence(indicators)
        assert result is not None
        assert result.label == RuleLabel.BEAR

    def test_mixed_timeframes_no_clear_signal(self) -> None:
        """Mixed RSI values should return NEUTRAL."""
        indicators = {
            "1h": [
                IndicatorRecord(
                    symbol="BTCUSDT",
                    timeframe="1h",
                    timestamp=_FIXED_TS,
                    rsi=Decimal("25"),
                    bollinger_upper=Decimal("45000"),
                    bollinger_middle=Decimal("43000"),
                    bollinger_lower=Decimal("41000"),
                    price_vs_bollinger=Decimal("0.5"),
                    trend_slope=Decimal("0.001"),
                    trend_type="uptrend",
                )
            ],
            "4h": [
                IndicatorRecord(
                    symbol="BTCUSDT",
                    timeframe="4h",
                    timestamp=_FIXED_TS,
                    rsi=Decimal("78"),
                    bollinger_upper=Decimal("45000"),
                    bollinger_middle=Decimal("43000"),
                    bollinger_lower=Decimal("41000"),
                    price_vs_bollinger=Decimal("0.5"),
                    trend_slope=Decimal("0.001"),
                    trend_type="uptrend",
                )
            ],
        }

        result = evaluate_rsi_multi_tf_convergence(indicators)
        assert result is None or result.label == RuleLabel.NEUTRAL

    def test_empty_indicators_returns_none(self) -> None:
        """Empty indicators dict should return None."""
        result = evaluate_rsi_multi_tf_convergence({})
        assert result is None

    def test_missing_timeframe_no_crash(self) -> None:
        """Missing timeframe in indicators should not crash."""
        indicators = {
            "1h": [
                IndicatorRecord(
                    symbol="BTCUSDT",
                    timeframe="1h",
                    timestamp=_FIXED_TS,
                    rsi=Decimal("25"),
                    bollinger_upper=Decimal("45000"),
                    bollinger_middle=Decimal("43000"),
                    bollinger_lower=Decimal("41000"),
                    price_vs_bollinger=Decimal("0.5"),
                    trend_slope=Decimal("0.001"),
                    trend_type="uptrend",
                )
            ],
            # "2h", "3h", "4h" missing
        }

        result = evaluate_rsi_multi_tf_convergence(indicators)
        # Should handle gracefully without error
        assert result is None or isinstance(result, RuleResult)
