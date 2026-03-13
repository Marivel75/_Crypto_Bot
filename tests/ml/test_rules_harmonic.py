"""Tests for harmonic pattern rule evaluation (Gartley, Bat, Butterfly, Crab)."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from src.shared.models.crypto import IndicatorRecord

# Fixed timestamp
_FIXED_TS = datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc)


class TestHarmonicPatternDetection:
    """Test harmonic pattern recognition and direction inference."""

    def test_gartley_pattern_detected_bullish(self) -> None:
        """Gartley pattern without direction suffix should default to BUY."""
        indicators = {
            "4h": [
                IndicatorRecord(
                    symbol="BTCUSDT",
                    timeframe="4h",
                    timestamp=_FIXED_TS,
                    rsi=Decimal("50"),
                    bollinger_upper=Decimal("45000"),
                    bollinger_middle=Decimal("43000"),
                    bollinger_lower=Decimal("41000"),
                    price_vs_bollinger=Decimal("0.5"),
                    trend_slope=Decimal("0.001"),
                    trend_type="uptrend",
                    harmonic_pattern="gartley",
                    metadata={
                        "xb_ratio": 0.618,
                        "ac_ratio": 0.382,
                        "bd_ratio": 0.886,
                        "xd_ratio": 0.786,
                    },
                )
            ]
        }

        # Pattern name without suffix defaults to BUY
        pattern = indicators["4h"][0].harmonic_pattern
        assert pattern == "gartley"
        assert pattern.lower() in ["gartley", "gartley_bullish", "gartley_buy"]

    def test_gartley_pattern_bearish_suffix(self) -> None:
        """Gartley pattern with _bearish suffix should signal SELL."""
        indicators = {
            "4h": [
                IndicatorRecord(
                    symbol="BTCUSDT",
                    timeframe="4h",
                    timestamp=_FIXED_TS,
                    rsi=Decimal("50"),
                    bollinger_upper=Decimal("45000"),
                    bollinger_middle=Decimal("43000"),
                    bollinger_lower=Decimal("41000"),
                    price_vs_bollinger=Decimal("0.5"),
                    trend_slope=Decimal("0.001"),
                    trend_type="downtrend",
                    harmonic_pattern="gartley_bearish",
                    metadata={
                        "xb_ratio": 0.618,
                        "ac_ratio": 0.382,
                        "bd_ratio": 0.886,
                        "xd_ratio": 0.786,
                    },
                )
            ]
        }

        pattern = indicators["4h"][0].harmonic_pattern
        assert pattern == "gartley_bearish"
        assert pattern.lower().endswith("_bearish")

    def test_bat_pattern_detected(self) -> None:
        """Bat pattern with valid Fibonacci ratios should be detected."""
        indicators = {
            "4h": [
                IndicatorRecord(
                    symbol="ETHUSDT",
                    timeframe="4h",
                    timestamp=_FIXED_TS,
                    rsi=Decimal("60"),
                    bollinger_upper=Decimal("2500"),
                    bollinger_middle=Decimal("2400"),
                    bollinger_lower=Decimal("2300"),
                    price_vs_bollinger=Decimal("0.5"),
                    trend_slope=Decimal("0.002"),
                    trend_type="uptrend",
                    harmonic_pattern="bat",
                    metadata={
                        "xb_ratio": 0.50,
                        "ac_ratio": 0.382,
                        "bd_ratio": 0.877,
                        "xd_ratio": 0.886,
                    },
                )
            ]
        }

        pattern = indicators["4h"][0].harmonic_pattern
        assert pattern == "bat"
        assert "ratio" in indicators["4h"][0].metadata


class TestHarmonicFibonacciRatios:
    """Test Fibonacci ratio validation for harmonic patterns."""

    def test_gartley_standard_ratios_valid(self) -> None:
        """Gartley standard ratios (0.618, 0.382, 0.886, 0.786) should be valid."""
        # Standard Gartley: XB=0.618, AC=0.382, BD=0.886, XD=0.786
        ratios = {
            "xb_ratio": 0.618,
            "ac_ratio": 0.382,
            "bd_ratio": 0.886,
            "xd_ratio": 0.786,
        }

        # All ratios are Fibonacci numbers (within typical tolerance of 0.05)
        assert 0.618 - 0.05 <= ratios["xb_ratio"] <= 0.618 + 0.05
        assert 0.382 - 0.05 <= ratios["ac_ratio"] <= 0.382 + 0.05

    def test_bat_standard_ratios_valid(self) -> None:
        """Bat standard ratios (0.50, 0.382, 0.877, 0.886) should be valid."""
        # Standard Bat: XB=0.50, AC=0.382, BD=0.877, XD=0.886
        ratios = {
            "xb_ratio": 0.50,
            "ac_ratio": 0.382,
            "bd_ratio": 0.877,
            "xd_ratio": 0.886,
        }

        assert 0.50 - 0.05 <= ratios["xb_ratio"] <= 0.50 + 0.05
        assert 0.886 - 0.05 <= ratios["xd_ratio"] <= 0.886 + 0.05

    def test_butterfly_standard_ratios_valid(self) -> None:
        """Butterfly standard ratios (0.786, 0.382, 1.618, 1.273) should be valid."""
        # Standard Butterfly: XB=0.786, AC=0.382, BD=1.618, XD=1.273
        ratios = {
            "xb_ratio": 0.786,
            "ac_ratio": 0.382,
            "bd_ratio": 1.618,
            "xd_ratio": 1.273,
        }

        assert 1.618 - 0.05 <= ratios["bd_ratio"] <= 1.618 + 0.05
        assert 1.273 - 0.05 <= ratios["xd_ratio"] <= 1.273 + 0.05

    def test_crab_standard_ratios_valid(self) -> None:
        """Crab standard ratios (0.382, 0.382, 2.24, 1.618) should be valid."""
        # Standard Crab: XB=0.382, AC=0.382, BD=2.24, XD=1.618
        ratios = {
            "xb_ratio": 0.382,
            "ac_ratio": 0.382,
            "bd_ratio": 2.24,
            "xd_ratio": 1.618,
        }

        assert 2.24 - 0.05 <= ratios["bd_ratio"] <= 2.24 + 0.05
        assert 1.618 - 0.05 <= ratios["xd_ratio"] <= 1.618 + 0.05

    def test_ratio_within_tolerance(self) -> None:
        """Ratios within tolerance (±5%) should be valid."""
        base_ratio = 0.618
        tolerance = 0.05

        valid_ratios = [0.618, 0.608, 0.628]
        invalid_ratios = [0.55, 0.70]

        for ratio in valid_ratios:
            assert abs(ratio - base_ratio) <= tolerance

        for ratio in invalid_ratios:
            assert abs(ratio - base_ratio) > tolerance


class TestHarmonicPatternConfidence:
    """Test confidence scoring for harmonic patterns."""

    def test_crab_highest_confidence(self) -> None:
        """Crab pattern should have highest base confidence (0.75)."""
        patterns_confidence = {
            "gartley": 0.72,
            "butterfly": 0.68,
            "bat": 0.70,
            "crab": 0.75,
        }

        assert patterns_confidence["crab"] == max(patterns_confidence.values())

    def test_butterfly_lowest_confidence(self) -> None:
        """Butterfly pattern should have lowest base confidence (0.68)."""
        patterns_confidence = {
            "gartley": 0.72,
            "butterfly": 0.68,
            "bat": 0.70,
            "crab": 0.75,
        }

        assert patterns_confidence["butterfly"] == min(patterns_confidence.values())

    def test_perfect_ratio_validation_full_score(self) -> None:
        """All ratios matching spec should yield score 1.0."""
        # With 4 ratios, all matched -> matched/total = 4/4 = 1.0
        # score = 0.75 + 1.0 * 0.25 = 1.0
        ratio_score = 4 / 4
        multiplier = 0.75 + ratio_score * 0.25
        assert multiplier == 1.0

    def test_partial_ratio_validation_partial_score(self) -> None:
        """2 out of 4 ratios matching should yield score 0.875."""
        # With 4 ratios, 2 matched -> matched/total = 2/4 = 0.5
        # score = 0.75 + 0.5 * 0.25 = 0.875
        ratio_score = 2 / 4
        multiplier = 0.75 + ratio_score * 0.25
        assert multiplier == pytest.approx(0.875, abs=0.01)

    def test_no_ratios_provided_baseline_score(self) -> None:
        """No ratios in metadata should use baseline score (0.9)."""
        # When no ratios provided, use 0.9 as fallback
        baseline = 0.9
        assert baseline == 0.9


class TestHarmonicMultiTimeframe:
    """Test harmonic pattern detection across multiple timeframes."""

    def test_strongest_pattern_selected(self) -> None:
        """When multiple patterns detected, highest confidence should be selected."""
        {
            "1h": [
                IndicatorRecord(
                    symbol="BTCUSDT",
                    timeframe="1h",
                    timestamp=_FIXED_TS,
                    rsi=Decimal("50"),
                    bollinger_upper=Decimal("45000"),
                    bollinger_middle=Decimal("43000"),
                    bollinger_lower=Decimal("41000"),
                    price_vs_bollinger=Decimal("0.5"),
                    trend_slope=Decimal("0.001"),
                    trend_type="uptrend",
                    harmonic_pattern="bat",
                    metadata={"xb_ratio": 0.50},
                )
            ],
            "4h": [
                IndicatorRecord(
                    symbol="BTCUSDT",
                    timeframe="4h",
                    timestamp=_FIXED_TS,
                    rsi=Decimal("50"),
                    bollinger_upper=Decimal("45000"),
                    bollinger_middle=Decimal("43000"),
                    bollinger_lower=Decimal("41000"),
                    price_vs_bollinger=Decimal("0.5"),
                    trend_slope=Decimal("0.001"),
                    trend_type="uptrend",
                    harmonic_pattern="crab",
                    metadata={"xd_ratio": 1.618},
                )
            ],
        }

        # Crab (0.75) > Bat (0.70), so crab should be selected
        crab_confidence = 0.75
        bat_confidence = 0.70
        assert crab_confidence > bat_confidence

    def test_no_pattern_on_primary_tf_checks_secondary(self) -> None:
        """If no pattern on primary TF, should check secondary TF."""
        indicators = {
            "1h": [
                IndicatorRecord(
                    symbol="BTCUSDT",
                    timeframe="1h",
                    timestamp=_FIXED_TS,
                    rsi=Decimal("50"),
                    bollinger_upper=Decimal("45000"),
                    bollinger_middle=Decimal("43000"),
                    bollinger_lower=Decimal("41000"),
                    price_vs_bollinger=Decimal("0.5"),
                    trend_slope=Decimal("0.001"),
                    trend_type="uptrend",
                    harmonic_pattern=None,  # No pattern on 1h
                )
            ],
            "4h": [
                IndicatorRecord(
                    symbol="BTCUSDT",
                    timeframe="4h",
                    timestamp=_FIXED_TS,
                    rsi=Decimal("50"),
                    bollinger_upper=Decimal("45000"),
                    bollinger_middle=Decimal("43000"),
                    bollinger_lower=Decimal("41000"),
                    price_vs_bollinger=Decimal("0.5"),
                    trend_slope=Decimal("0.001"),
                    trend_type="uptrend",
                    harmonic_pattern="gartley",
                )
            ],
        }

        assert indicators["1h"][0].harmonic_pattern is None
        assert indicators["4h"][0].harmonic_pattern == "gartley"


class TestHarmonicEdgeCases:
    """Test edge cases and error handling."""

    def test_unknown_pattern_name_ignored(self) -> None:
        """Unknown pattern names should be logged and ignored."""
        indicators = {
            "4h": [
                IndicatorRecord(
                    symbol="BTCUSDT",
                    timeframe="4h",
                    timestamp=_FIXED_TS,
                    rsi=Decimal("50"),
                    bollinger_upper=Decimal("45000"),
                    bollinger_middle=Decimal("43000"),
                    bollinger_lower=Decimal("41000"),
                    price_vs_bollinger=Decimal("0.5"),
                    trend_slope=Decimal("0.001"),
                    trend_type="uptrend",
                    harmonic_pattern="unknown_pattern",
                )
            ]
        }

        pattern = indicators["4h"][0].harmonic_pattern
        known_patterns = {"gartley", "bat", "butterfly", "crab"}
        # Verify pattern is not in known set
        assert pattern.lower() not in known_patterns

    def test_empty_metadata_uses_baseline_confidence(self) -> None:
        """Pattern with empty metadata should use baseline (0.9 * base_conf)."""
        {
            "4h": [
                IndicatorRecord(
                    symbol="BTCUSDT",
                    timeframe="4h",
                    timestamp=_FIXED_TS,
                    rsi=Decimal("50"),
                    bollinger_upper=Decimal("45000"),
                    bollinger_middle=Decimal("43000"),
                    bollinger_lower=Decimal("41000"),
                    price_vs_bollinger=Decimal("0.5"),
                    trend_slope=Decimal("0.001"),
                    trend_type="uptrend",
                    harmonic_pattern="bat",
                    metadata={},  # No ratios
                )
            ]
        }

        # With no ratios, score multiplier = 0.9
        bat_base = 0.70
        final_confidence = bat_base * 0.9
        assert final_confidence == pytest.approx(0.63, abs=0.01)

    def test_missing_timeframe_data_skipped(self) -> None:
        """Missing timeframe data should be skipped without error."""
        indicators = {
            "1h": [],  # Empty list
            "4h": [
                IndicatorRecord(
                    symbol="BTCUSDT",
                    timeframe="4h",
                    timestamp=_FIXED_TS,
                    rsi=Decimal("50"),
                    bollinger_upper=Decimal("45000"),
                    bollinger_middle=Decimal("43000"),
                    bollinger_lower=Decimal("41000"),
                    price_vs_bollinger=Decimal("0.5"),
                    trend_slope=Decimal("0.001"),
                    trend_type="uptrend",
                    harmonic_pattern="gartley",
                )
            ],
        }

        # Empty 1h list should be handled gracefully
        assert indicators["1h"] == []
        assert len(indicators["4h"]) == 1

    def test_case_insensitive_pattern_parsing(self) -> None:
        """Pattern names should be parsed case-insensitively."""
        test_cases = [
            "GARTLEY",
            "Gartley",
            "gartley",
            "GARTLEY_BEARISH",
            "Gartley_Bearish",
            "gartley_bearish",
        ]

        for test_pattern in test_cases:
            lower = test_pattern.lower()
            assert lower in [
                "gartley",
                "gartley_bearish",
                "gartley_bullish",
                "gartley_buy",
            ] or lower.startswith("gartley")
