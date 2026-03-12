"""Unit tests for evaluate_bollinger from src.ml.rules.bollinger_rules."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from src.ml.rules.bollinger_rules import evaluate_bollinger
from src.ml.rules.models import RuleResult
from src.shared.models.crypto import IndicatorRecord

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config(
    squeeze_threshold: float = 0.02,
    timeframes: list[str] | None = None,
) -> dict:
    return {
        "timeframes": timeframes or ["1h", "2h", "3h", "4h", "1D"],
        "squeeze_threshold": squeeze_threshold,
    }


def _indicator(
    symbol: str = "BTCUSDT",
    timeframe: str = "4h",
    price_vs_bollinger: Decimal | None = None,
    bollinger_upper: Decimal | None = None,
    bollinger_middle: Decimal | None = None,
    bollinger_lower: Decimal | None = None,
    offset_seconds: int = 0,
) -> IndicatorRecord:
    return IndicatorRecord(
        symbol=symbol,
        timeframe=timeframe,
        timestamp=datetime(2024, 6, 1, 12, 0, offset_seconds, tzinfo=UTC),
        price_vs_bollinger=price_vs_bollinger,
        bollinger_upper=bollinger_upper,
        bollinger_middle=bollinger_middle,
        bollinger_lower=bollinger_lower,
    )


# ---------------------------------------------------------------------------
# Tests: no data — returns None
# ---------------------------------------------------------------------------


class TestNoData:
    def test_returns_none_when_indicators_empty(self) -> None:
        result = evaluate_bollinger("BTCUSDT", {}, _make_config())
        assert result is None

    def test_returns_none_when_all_lists_are_empty(self) -> None:
        indicators: dict[str, list[IndicatorRecord]] = {
            "4h": [],
            "1h": [],
        }
        result = evaluate_bollinger("BTCUSDT", indicators, _make_config())
        assert result is None

    def test_returns_none_when_no_configured_timeframes_present(self) -> None:
        indicators = {
            "5m": [_indicator(timeframe="5m")],
        }
        result = evaluate_bollinger("BTCUSDT", indicators, _make_config(timeframes=["4h"]))
        assert result is None


# ---------------------------------------------------------------------------
# Tests: breakout detection
# ---------------------------------------------------------------------------


class TestBreakout:
    def test_upward_breakout_returns_buy(self) -> None:
        # price_vs_bollinger > 1 => upward breakout => BUY
        indicators = {
            "4h": [_indicator(price_vs_bollinger=Decimal("1.2"))],
        }
        result = evaluate_bollinger("BTCUSDT", indicators, _make_config())
        assert result is not None
        assert isinstance(result, RuleResult)
        assert result.direction == "BUY"

    def test_downward_breakout_returns_sell(self) -> None:
        # price_vs_bollinger < -1 => downward breakout => SELL
        indicators = {
            "4h": [_indicator(price_vs_bollinger=Decimal("-1.3"))],
        }
        result = evaluate_bollinger("BTCUSDT", indicators, _make_config())
        assert result is not None
        assert result.direction == "SELL"

    def test_breakout_confidence_at_least_0_6(self) -> None:
        indicators = {
            "4h": [_indicator(price_vs_bollinger=Decimal("1.05"))],
        }
        result = evaluate_bollinger("BTCUSDT", indicators, _make_config())
        assert result is not None
        assert result.confidence >= Decimal("0.6")

    def test_breakout_confidence_capped_at_0_9(self) -> None:
        # Very extreme breakout should not exceed 0.9
        indicators = {
            "4h": [_indicator(price_vs_bollinger=Decimal("10.0"))],
        }
        result = evaluate_bollinger("BTCUSDT", indicators, _make_config())
        assert result is not None
        assert result.confidence <= Decimal("0.9")

    def test_breakout_stronger_when_further_from_band(self) -> None:
        indicators_mild = {
            "4h": [_indicator(price_vs_bollinger=Decimal("1.05"))],
        }
        indicators_strong = {
            "4h": [_indicator(price_vs_bollinger=Decimal("1.8"))],
        }
        result_mild = evaluate_bollinger("BTCUSDT", indicators_mild, _make_config())
        result_strong = evaluate_bollinger("BTCUSDT", indicators_strong, _make_config())
        assert result_mild is not None
        assert result_strong is not None
        assert result_strong.confidence >= result_mild.confidence

    def test_breakout_uses_4h_as_primary_timeframe_when_available(self) -> None:
        # 1h has no breakout; 4h has upward breakout — should fire BUY
        indicators = {
            "1h": [_indicator(timeframe="1h", price_vs_bollinger=Decimal("0.3"))],
            "4h": [_indicator(timeframe="4h", price_vs_bollinger=Decimal("1.5"))],
        }
        result = evaluate_bollinger("BTCUSDT", indicators, _make_config())
        assert result is not None
        assert result.direction == "BUY"
        assert "4h" in result.rule_name

    def test_no_breakout_when_price_vs_bollinger_is_one_exactly(self) -> None:
        # price_vs_bollinger == 1 does not trigger (must be strictly > 1)
        indicators = {
            "4h": [_indicator(price_vs_bollinger=Decimal("1.0"))],
        }
        result = evaluate_bollinger("BTCUSDT", indicators, _make_config())
        # No breakout, no band walking, no squeeze → None
        assert result is None

    def test_no_breakout_when_price_vs_bollinger_is_within_bands(self) -> None:
        indicators = {
            "4h": [_indicator(price_vs_bollinger=Decimal("0.5"))],
        }
        result = evaluate_bollinger("BTCUSDT", indicators, _make_config())
        assert result is None

    def test_no_breakout_when_price_vs_bollinger_is_none_and_no_bands(self) -> None:
        indicators = {
            "4h": [_indicator(price_vs_bollinger=None)],
        }
        result = evaluate_bollinger("BTCUSDT", indicators, _make_config())
        assert result is None


# ---------------------------------------------------------------------------
# Tests: band walking detection (takes priority over squeeze, after breakout)
# ---------------------------------------------------------------------------


class TestBandWalking:
    def _upper_walk_records(self, n: int = 3) -> list[IndicatorRecord]:
        return [
            _indicator(
                timeframe="4h",
                price_vs_bollinger=Decimal("0.8"),
                offset_seconds=i,
            )
            for i in range(n)
        ]

    def _lower_walk_records(self, n: int = 3) -> list[IndicatorRecord]:
        return [
            _indicator(
                timeframe="4h",
                price_vs_bollinger=Decimal("-0.8"),
                offset_seconds=i,
            )
            for i in range(n)
        ]

    def test_upper_band_walking_returns_buy(self) -> None:
        indicators = {"4h": self._upper_walk_records()}
        result = evaluate_bollinger("BTCUSDT", indicators, _make_config())
        assert result is not None
        assert result.direction == "BUY"

    def test_lower_band_walking_returns_sell(self) -> None:
        indicators = {"4h": self._lower_walk_records()}
        result = evaluate_bollinger("BTCUSDT", indicators, _make_config())
        assert result is not None
        assert result.direction == "SELL"

    def test_band_walking_confidence_is_0_65(self) -> None:
        indicators = {"4h": self._upper_walk_records()}
        result = evaluate_bollinger("BTCUSDT", indicators, _make_config())
        assert result is not None
        assert result.confidence == Decimal("0.65")

    def test_no_band_walking_when_fewer_than_3_candles(self) -> None:
        indicators = {"4h": self._upper_walk_records(n=2)}
        result = evaluate_bollinger("BTCUSDT", indicators, _make_config())
        # Not enough candles for band walking; no breakout or squeeze either
        assert result is None

    def test_no_band_walking_when_one_candle_drops_below_threshold(self) -> None:
        # Mix of near-upper and neutral — should not qualify as band walking
        records = [
            _indicator(timeframe="4h", price_vs_bollinger=Decimal("0.8"), offset_seconds=0),
            _indicator(timeframe="4h", price_vs_bollinger=Decimal("0.8"), offset_seconds=1),
            _indicator(timeframe="4h", price_vs_bollinger=Decimal("0.3"), offset_seconds=2),
        ]
        indicators = {"4h": records}
        result = evaluate_bollinger("BTCUSDT", indicators, _make_config())
        assert result is None

    def test_band_walking_rule_name_contains_direction(self) -> None:
        indicators = {"4h": self._upper_walk_records()}
        result = evaluate_bollinger("BTCUSDT", indicators, _make_config())
        assert result is not None
        assert "upper" in result.rule_name


# ---------------------------------------------------------------------------
# Tests: squeeze detection (returns None — no directional signal yet)
# ---------------------------------------------------------------------------


class TestSqueeze:
    def _squeeze_indicator(self, timeframe: str = "4h") -> IndicatorRecord:
        # band_width = (upper - lower) / middle = (100.5 - 99.5) / 100 = 0.01 < 0.02
        return _indicator(
            timeframe=timeframe,
            bollinger_upper=Decimal("100.5"),
            bollinger_middle=Decimal("100"),
            bollinger_lower=Decimal("99.5"),
        )

    def test_squeeze_alone_returns_none(self) -> None:
        indicators = {"4h": [self._squeeze_indicator()]}
        result = evaluate_bollinger("BTCUSDT", indicators, _make_config())
        assert result is None

    def test_no_squeeze_when_bands_are_wide(self) -> None:
        # band_width = (110 - 90) / 100 = 0.20 > 0.02 => not a squeeze
        wide_indicator = _indicator(
            timeframe="4h",
            bollinger_upper=Decimal("110"),
            bollinger_middle=Decimal("100"),
            bollinger_lower=Decimal("90"),
        )
        indicators = {"4h": [wide_indicator]}
        result = evaluate_bollinger("BTCUSDT", indicators, _make_config())
        assert result is None  # no breakout, no walking, no squeeze — just wide

    def test_squeeze_does_not_override_breakout(self) -> None:
        # Even during a squeeze, if breakout fires it takes priority.
        records = [
            _indicator(
                timeframe="4h",
                price_vs_bollinger=Decimal("1.5"),
                bollinger_upper=Decimal("100.5"),
                bollinger_middle=Decimal("100"),
                bollinger_lower=Decimal("99.5"),
            )
        ]
        indicators = {"4h": records}
        result = evaluate_bollinger("BTCUSDT", indicators, _make_config())
        assert result is not None
        assert result.direction == "BUY"


# ---------------------------------------------------------------------------
# Tests: no signal — neutral conditions
# ---------------------------------------------------------------------------


class TestNoSignal:
    def test_returns_none_for_neutral_price_vs_bollinger(self) -> None:
        indicators = {
            "4h": [_indicator(price_vs_bollinger=Decimal("0.0"))],
        }
        result = evaluate_bollinger("BTCUSDT", indicators, _make_config())
        assert result is None

    def test_returns_none_when_only_two_walk_records(self) -> None:
        records = [
            _indicator(timeframe="4h", price_vs_bollinger=Decimal("0.9"), offset_seconds=0),
            _indicator(timeframe="4h", price_vs_bollinger=Decimal("0.9"), offset_seconds=1),
        ]
        indicators = {"4h": records}
        result = evaluate_bollinger("BTCUSDT", indicators, _make_config())
        assert result is None
