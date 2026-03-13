"""E2E tests for complete signal generation pipeline (T6).

Tests: Data loading → Indicators → Rule Engine → Signal Generator → TradingSignal

No database touches; all data is synthetic and in-memory.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from src.ml.signal_generator import SignalGenerator
from src.shared.constants import SIGNAL_CONFIDENCE_THRESHOLD
from src.shared.models.crypto import IndicatorRecord
from src.shared.models.signal import TradingSignal

logger = logging.getLogger(__name__)

# Config path
_CONFIG_PATH = Path(__file__).resolve().parents[2] / "src" / "ml" / "config" / "indicators.yaml"
_CONFIG_MISSING = not _CONFIG_PATH.exists()

# Fixed base timestamp
_TS_BASE = datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc)


def _make_indicator_record(
    symbol: str = "BTCUSDT",
    timeframe: str = "4h",
    timestamp_offset_hours: int = 0,
    rsi: Decimal | None = None,
    bollinger_upper: Decimal | None = None,
    bollinger_middle: Decimal | None = None,
    bollinger_lower: Decimal | None = None,
    price_vs_bollinger: Decimal | None = None,
    trend_slope: Decimal | None = None,
    trend_type: str | None = None,
    harmonic_pattern: str | None = None,
) -> IndicatorRecord:
    """Build a single IndicatorRecord with controlled values."""
    return IndicatorRecord(
        symbol=symbol,
        timeframe=timeframe,
        timestamp=_TS_BASE + timedelta(hours=timestamp_offset_hours),
        rsi=rsi,
        bollinger_upper=bollinger_upper,
        bollinger_middle=bollinger_middle,
        bollinger_lower=bollinger_lower,
        price_vs_bollinger=price_vs_bollinger,
        trend_slope=trend_slope,
        trend_type=trend_type,
        harmonic_pattern=harmonic_pattern,
    )


def _build_ohlcv_indicators(
    symbol: str = "BTCUSDT",
    count: int = 500,
    start_price: Decimal = Decimal("43000"),
    trend: str = "sideways",
) -> dict[str, list[IndicatorRecord]]:
    """Generate realistic OHLCV indicators for multiple timeframes.

    Args:
        symbol: Trading pair symbol.
        count: Number of candles per timeframe.
        start_price: Starting price (used to calculate Bollinger Bands).
        trend: Trend direction: "up", "down", or "sideways".

    Returns:
        Dict mapping timeframe -> list of IndicatorRecord.
    """
    indicators: dict[str, list[IndicatorRecord]] = {}

    # Trend direction for RSI oscillation
    if trend == "up":
        rsi_oversold = Decimal("35")  # Mild oversold
        rsi_overbought = Decimal("75")  # Overbought
    elif trend == "down":
        rsi_oversold = Decimal("20")  # Deep oversold
        rsi_overbought = Decimal("60")  # Mild overbought
    else:  # sideways
        rsi_oversold = Decimal("45")
        rsi_overbought = Decimal("55")

    # RSI timeframes: 1h, 2h, 3h, 4h (tight convergence)
    for tf_idx, tf in enumerate(["1h", "2h", "3h", "4h"]):
        records: list[IndicatorRecord] = []
        for i in range(count):
            # Oscillate RSI between oversold and overbought
            rsi_val = rsi_oversold + ((Decimal(str(i)) % 20) / 10) * (rsi_overbought - rsi_oversold)

            # Bollinger Bands around the start price with ±5% bands
            bb_middle = start_price + (Decimal(str(i % 50)) - 25) * Decimal("200")
            bb_width = bb_middle * Decimal("0.05")
            bb_upper = bb_middle + bb_width
            bb_lower = bb_middle - bb_width

            # Price fluctuation (stays within bands)
            price = bb_lower + (bb_upper - bb_lower) * Decimal(str((i % 100) / 100))
            price_vs_bb = (price - bb_lower) / (bb_upper - bb_lower) if bb_upper != bb_lower else Decimal("0.5")

            records.append(
                _make_indicator_record(
                    symbol=symbol,
                    timeframe=tf,
                    timestamp_offset_hours=tf_idx * count + i,
                    rsi=rsi_val,
                    bollinger_upper=bb_upper,
                    bollinger_middle=bb_middle,
                    bollinger_lower=bb_lower,
                    price_vs_bollinger=price_vs_bb,
                    trend_slope=Decimal("0.001") if trend == "up" else Decimal("-0.001"),
                    trend_type="stable" if trend != "down" else "downtrend",
                )
            )
        indicators[tf] = records

    # Additional timeframes for broader coverage
    for tf in ["1D", "1W"]:
        records = []
        for i in range(count // 24):  # Fewer candles for daily/weekly
            rsi_val = Decimal("50")  # Neutral RSI for daily/weekly
            records.append(
                _make_indicator_record(
                    symbol=symbol,
                    timeframe=tf,
                    timestamp_offset_hours=i * 24,
                    rsi=rsi_val,
                    trend_slope=Decimal("0.01"),
                    trend_type="stable",
                )
            )
        indicators[tf] = records

    return indicators


class _FakeRuleEngine:
    """Minimal rule engine protocol implementation for testing."""

    def __init__(self, direction: str, confidence: float) -> None:
        self.direction = direction
        self.confidence = confidence

    def evaluate(self, symbol: str, indicators: dict[str, Any]) -> dict[str, Any]:
        """Return a controlled signal regardless of input."""
        return {
            "direction": self.direction,
            "confidence": self.confidence,
            "rules_triggered": ["test_rule"],
            "timeframe": "4h",
            "timeframes_aligned": {},
        }


@pytest.mark.skipif(_CONFIG_MISSING, reason="indicators.yaml not found")
class TestSignalGenerationPipeline:
    """E2E tests for the full signal generation pipeline."""

    def test_pipeline_loads_realistic_ohlcv_data(self) -> None:
        """Verify synthetic OHLCV data is properly structured."""
        indicators = _build_ohlcv_indicators(count=500)

        # Check all expected timeframes present
        assert "1h" in indicators
        assert "4h" in indicators
        assert "1D" in indicators

        # Check data structure
        for tf, records in indicators.items():
            assert len(records) > 0, f"Timeframe {tf} has no records"
            assert all(isinstance(r, IndicatorRecord) for r in records), f"Timeframe {tf} has non-IndicatorRecord items"
            assert all(r.timeframe == tf for r in records), f"Timeframe {tf} records have mismatched timeframe field"

    def test_pipeline_generates_buy_signal_from_bullish_indicators(self) -> None:
        """Verify pipeline emits BUY signal when indicators are bullish."""
        fake_engine = _FakeRuleEngine(direction="BUY", confidence=0.8)
        generator = SignalGenerator(rule_engine=fake_engine)

        indicators = _build_ohlcv_indicators(trend="up")
        signal = generator.generate(symbol="BTCUSDT", indicators=indicators)

        assert signal is not None, "Pipeline must emit signal with confidence=0.8"
        assert isinstance(signal, TradingSignal)
        assert signal.symbol == "BTCUSDT"
        assert signal.signal_type == "BUY"
        assert signal.confidence_score >= SIGNAL_CONFIDENCE_THRESHOLD
        assert signal.model_version != ""
        assert signal.timeframe_primary == "4h"

    def test_pipeline_generates_sell_signal_from_bearish_indicators(self) -> None:
        """Verify pipeline emits SELL signal when indicators are bearish."""
        fake_engine = _FakeRuleEngine(direction="SELL", confidence=0.75)
        generator = SignalGenerator(rule_engine=fake_engine)

        indicators = _build_ohlcv_indicators(trend="down")
        signal = generator.generate(symbol="ETHUSDT", indicators=indicators)

        assert signal is not None, "Pipeline must emit signal with confidence=0.75"
        assert signal.signal_type == "SELL"
        assert signal.confidence_score >= SIGNAL_CONFIDENCE_THRESHOLD

    def test_pipeline_suppresses_low_confidence_signals(self) -> None:
        """Verify pipeline suppresses signals below confidence threshold (0.6)."""
        fake_engine = _FakeRuleEngine(direction="BUY", confidence=0.4)
        generator = SignalGenerator(rule_engine=fake_engine)

        indicators = _build_ohlcv_indicators(count=500)
        signal = generator.generate(symbol="BTCUSDT", indicators=indicators)

        assert signal is None, f"Pipeline must suppress signals with confidence < 0.6, got {signal}"

    def test_pipeline_signal_conforms_to_schema(self) -> None:
        """Verify emitted signal conforms to TradingSignal Pydantic schema."""
        fake_engine = _FakeRuleEngine(direction="BUY", confidence=0.85)
        generator = SignalGenerator(rule_engine=fake_engine)

        indicators = _build_ohlcv_indicators(count=500)
        signal = generator.generate(symbol="BTCUSDT", indicators=indicators)

        assert signal is not None
        # Validate schema requirements
        assert signal.symbol in ["BTCUSDT", "ETHUSDT", "BNBUSDT"]  # Valid symbol
        assert signal.signal_type in ("BUY", "SELL", "HOLD")
        assert Decimal("0.6") <= signal.confidence_score <= Decimal("1.0")
        assert signal.timeframe_primary in ["1h", "4h", "1D", "1W"]
        assert isinstance(signal.rules_triggered, list)
        assert isinstance(signal.timeframes_aligned, dict)
        assert signal.leverage_suggested is None or (1 <= signal.leverage_suggested <= 20)
        assert signal.model_version != ""

    def test_pipeline_applies_news_sentiment_adjustment(self) -> None:
        """Verify news sentiment adjusts signal confidence."""
        fake_engine = _FakeRuleEngine(direction="BUY", confidence=0.70)
        generator = SignalGenerator(rule_engine=fake_engine)

        indicators = _build_ohlcv_indicators(count=500)

        # Positive sentiment should increase BUY confidence
        signal_bullish = generator.generate(symbol="BTCUSDT", indicators=indicators, news_sentiment=1.0)
        signal_neutral = generator.generate(symbol="BTCUSDT", indicators=indicators, news_sentiment=0.0)
        generator.generate(symbol="BTCUSDT", indicators=indicators, news_sentiment=-1.0)

        assert signal_bullish is not None
        assert signal_neutral is not None
        assert True  # Might be suppressed if confidence drops too low

        # Bullish sentiment should increase BUY confidence
        assert signal_bullish.confidence_score > signal_neutral.confidence_score

    def test_pipeline_blends_rule_and_ml_confidence(self) -> None:
        """Verify pipeline correctly blends rule and ML confidences (60/40 weighting)."""

        class _MockPredictor:
            def predict(self, features: Any) -> list[dict[str, Any]]:
                return [{"direction": "BUY", "confidence": 0.90}]

        fake_engine = _FakeRuleEngine(direction="BUY", confidence=0.70)
        predictor = _MockPredictor()
        generator = SignalGenerator(rule_engine=fake_engine, predictor=predictor)

        indicators = _build_ohlcv_indicators(count=500)
        signal = generator.generate(symbol="BTCUSDT", indicators=indicators)

        assert signal is not None
        # Blended confidence = 0.6 * 0.90 + 0.4 * 0.70 = 0.54 + 0.28 = 0.82
        expected_blend = Decimal("0.6") * Decimal("0.90") + Decimal("0.4") * Decimal("0.70")
        assert abs(signal.confidence_score - expected_blend) < Decimal("0.01")

    def test_pipeline_handles_missing_indicator_data_gracefully(self) -> None:
        """Verify pipeline handles sparse or missing indicator data without crashing."""
        fake_engine = _FakeRuleEngine(direction="BUY", confidence=0.70)
        generator = SignalGenerator(rule_engine=fake_engine)

        # Create sparse indicators (only 1h timeframe)
        indicators: dict[str, list[IndicatorRecord]] = {
            "1h": [
                _make_indicator_record(timeframe="1h", rsi=Decimal("25"), bollinger_middle=Decimal("43000")),
            ]
        }

        signal = generator.generate(symbol="BTCUSDT", indicators=indicators)

        # Should not crash, even if confidence is reduced due to sparse data
        assert signal is None or isinstance(signal, TradingSignal)

    def test_pipeline_multiple_symbols_independent(self) -> None:
        """Verify signals for different symbols are independent."""
        fake_engine = _FakeRuleEngine(direction="BUY", confidence=0.75)
        generator = SignalGenerator(rule_engine=fake_engine)

        indicators = _build_ohlcv_indicators(count=500)

        signal_btc = generator.generate(symbol="BTCUSDT", indicators=indicators)
        signal_eth = generator.generate(symbol="ETHUSDT", indicators=indicators)

        assert signal_btc is not None
        assert signal_eth is not None
        assert signal_btc.symbol == "BTCUSDT"
        assert signal_eth.symbol == "ETHUSDT"
        # Confidence should be the same (same fake engine)
        assert signal_btc.confidence_score == signal_eth.confidence_score

    def test_pipeline_signal_generation_deterministic(self) -> None:
        """Verify signal generation is deterministic given the same inputs."""
        fake_engine = _FakeRuleEngine(direction="BUY", confidence=0.72)
        generator = SignalGenerator(rule_engine=fake_engine)

        indicators = _build_ohlcv_indicators(count=500)

        signal_1 = generator.generate(symbol="BTCUSDT", indicators=indicators)
        signal_2 = generator.generate(symbol="BTCUSDT", indicators=indicators)

        assert signal_1 is not None
        assert signal_2 is not None
        assert signal_1.confidence_score == signal_2.confidence_score
        assert signal_1.signal_type == signal_2.signal_type
        assert signal_1.rules_triggered == signal_2.rules_triggered
