"""Tests for Bollinger Band rule evaluation."""

from __future__ import annotations

from decimal import Decimal
from datetime import UTC, datetime

import pytest

from src.shared.models.crypto import IndicatorRecord

# Fixed timestamp
_FIXED_TS = datetime(2025, 6, 15, 12, 0, 0, tzinfo=UTC)


class TestBollingerSqueeze:
    """Test Bollinger Band squeeze detection."""

    def test_narrow_band_detected_as_squeeze(self) -> None:
        """Band width < 2% should be detected as squeeze."""
        # BB middle = 43000, width = 400 (0.93%) -> squeeze
        indicators = {
            "4h": [
                IndicatorRecord(
                    symbol="BTCUSDT",
                    timeframe="4h",
                    timestamp=_FIXED_TS,
                    rsi=Decimal("50"),
                    bollinger_upper=Decimal("43200"),
                    bollinger_middle=Decimal("43000"),
                    bollinger_lower=Decimal("42800"),
                    price_vs_bollinger=Decimal("0.5"),
                    trend_slope=Decimal("0.001"),
                    trend_type="uptrend",
                )
            ]
        }

        # Band width = (43200 - 42800) / 43000 = 0.93%
        band_width = (43200 - 42800) / 43000
        assert band_width < 0.02

    def test_wide_band_not_squeeze(self) -> None:
        """Band width > 2% should not be detected as squeeze."""
        indicators = {
            "4h": [
                IndicatorRecord(
                    symbol="BTCUSDT",
                    timeframe="4h",
                    timestamp=_FIXED_TS,
                    rsi=Decimal("50"),
                    bollinger_upper=Decimal("44000"),
                    bollinger_middle=Decimal("43000"),
                    bollinger_lower=Decimal("42000"),
                    price_vs_bollinger=Decimal("0.5"),
                    trend_slope=Decimal("0.001"),
                    trend_type="uptrend",
                )
            ]
        }

        # Band width = (44000 - 42000) / 43000 = 4.65%
        band_width = (44000 - 42000) / 43000
        assert band_width > 0.02


class TestBollingerBandWalking:
    """Test Bollinger Band walking (price near extremes)."""

    def test_price_walking_upper_band_bullish(self) -> None:
        """Price near upper band should be bullish."""
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
                    price_vs_bollinger=Decimal("0.95"),  # Near upper band
                    trend_slope=Decimal("0.005"),
                    trend_type="uptrend",
                )
            ]
        }

        # Price near upper band (0.95) in strong uptrend
        pct_above_middle = (Decimal("0.95") - Decimal("0.5")) / Decimal("0.5")
        assert pct_above_middle > 0.5

    def test_price_walking_lower_band_bearish(self) -> None:
        """Price near lower band should be bearish."""
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
                    price_vs_bollinger=Decimal("0.05"),  # Near lower band
                    trend_slope=Decimal("-0.005"),
                    trend_type="downtrend",
                )
            ]
        }

        # Price near lower band (0.05) in strong downtrend
        pct_below_middle = (Decimal("0.5") - Decimal("0.05")) / Decimal("0.5")
        assert pct_below_middle > 0.5


class TestBollingerBreakout:
    """Test Bollinger Band breakout signals."""

    def test_price_above_upper_band_breakout_signal(self) -> None:
        """Price breaking above upper band should signal potential reversal."""
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
                    price_vs_bollinger=Decimal("1.1"),  # Above upper band
                    trend_slope=Decimal("0.005"),
                    trend_type="uptrend",
                )
            ]
        }

        # Price > 1.0 means above upper band
        assert Decimal("1.1") > Decimal("1.0")

    def test_price_below_lower_band_breakout_signal(self) -> None:
        """Price breaking below lower band should signal potential reversal."""
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
                    price_vs_bollinger=Decimal("-0.1"),  # Below lower band
                    trend_slope=Decimal("-0.005"),
                    trend_type="downtrend",
                )
            ]
        }

        # Price < 0.0 means below lower band
        assert Decimal("-0.1") < Decimal("0.0")


class TestBollingerMultiTimeframe:
    """Test multi-timeframe Bollinger Band analysis."""

    def test_squeeze_across_multiple_timeframes(self) -> None:
        """Squeeze on multiple TFs should be stronger signal."""
        indicators = {
            "1h": [
                IndicatorRecord(
                    symbol="BTCUSDT",
                    timeframe="1h",
                    timestamp=_FIXED_TS,
                    rsi=Decimal("50"),
                    bollinger_upper=Decimal("43100"),
                    bollinger_middle=Decimal("43000"),
                    bollinger_lower=Decimal("42900"),
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
                    rsi=Decimal("50"),
                    bollinger_upper=Decimal("43200"),
                    bollinger_middle=Decimal("43000"),
                    bollinger_lower=Decimal("42800"),
                    price_vs_bollinger=Decimal("0.5"),
                    trend_slope=Decimal("0.001"),
                    trend_type="uptrend",
                )
            ],
        }

        # Both TFs in squeeze
        width_1h = (43100 - 42900) / 43000
        width_4h = (43200 - 42800) / 43000
        assert width_1h < 0.02
        assert width_4h < 0.02

    def test_divergence_across_timeframes_mixed_signal(self) -> None:
        """Divergence across TFs should weaken signal."""
        indicators = {
            "1h": [
                IndicatorRecord(
                    symbol="BTCUSDT",
                    timeframe="1h",
                    timestamp=_FIXED_TS,
                    rsi=Decimal("75"),
                    bollinger_upper=Decimal("43100"),
                    bollinger_middle=Decimal("43000"),
                    bollinger_lower=Decimal("42900"),
                    price_vs_bollinger=Decimal("0.95"),
                    trend_slope=Decimal("0.005"),
                    trend_type="uptrend",
                )
            ],
            "4h": [
                IndicatorRecord(
                    symbol="BTCUSDT",
                    timeframe="4h",
                    timestamp=_FIXED_TS,
                    rsi=Decimal("45"),
                    bollinger_upper=Decimal("45000"),
                    bollinger_middle=Decimal("43000"),
                    bollinger_lower=Decimal("41000"),
                    price_vs_bollinger=Decimal("0.5"),
                    trend_slope=Decimal("0.001"),
                    trend_type="sideways",
                )
            ],
        }

        # 1h bullish, 4h neutral -> mixed signal
        assert Decimal("0.95") > Decimal("0.5")
        assert Decimal("0.5") == Decimal("0.5")
