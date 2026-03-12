"""Unit tests for evaluate_rsi from src.ml.rules.rsi_rules."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from src.ml.rules.models import RuleResult
from src.ml.rules.rsi_rules import evaluate_rsi
from src.shared.models.crypto import IndicatorRecord

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

_FIXED_TS_BASE = datetime(2024, 6, 1, 12, 0, 0, tzinfo=UTC)


def _make_rsi_config(
    overbought: int = 70,
    oversold: int = 30,
    convergence_threshold: int = 5,
    timeframes: list[str] | None = None,
) -> dict:
    return {
        "timeframes": timeframes or ["1h", "2h", "3h", "4h"],
        "overbought": overbought,
        "oversold": oversold,
        "convergence_threshold": convergence_threshold,
    }


def _indicator(
    symbol: str,
    timeframe: str,
    rsi: Decimal | None,
    offset_seconds: int = 0,
) -> IndicatorRecord:
    return IndicatorRecord(
        symbol=symbol,
        timeframe=timeframe,
        timestamp=datetime(2024, 6, 1, 12, 0, offset_seconds, tzinfo=UTC),
        rsi=rsi,
    )


# ---------------------------------------------------------------------------
# Tests: insufficient data
# ---------------------------------------------------------------------------


class TestInsufficientData:
    def test_returns_none_when_no_timeframes_provided(self) -> None:
        result = evaluate_rsi("BTCUSDT", {}, _make_rsi_config())
        assert result is None

    def test_returns_none_when_only_one_timeframe_has_data(self) -> None:
        indicators = {
            "1h": [_indicator("BTCUSDT", "1h", Decimal("25"))],
        }
        result = evaluate_rsi("BTCUSDT", indicators, _make_rsi_config())
        assert result is None

    def test_returns_none_when_rsi_field_is_none(self) -> None:
        indicators = {
            "1h": [_indicator("BTCUSDT", "1h", None)],
            "2h": [_indicator("BTCUSDT", "2h", None)],
        }
        result = evaluate_rsi("BTCUSDT", indicators, _make_rsi_config())
        assert result is None

    def test_returns_none_when_lists_are_empty(self) -> None:
        indicators: dict[str, list[IndicatorRecord]] = {
            "1h": [],
            "2h": [],
        }
        result = evaluate_rsi("BTCUSDT", indicators, _make_rsi_config())
        assert result is None

    def test_picks_most_recent_record_per_timeframe(self) -> None:
        """Only the latest record matters; older records are ignored."""
        # Provide two records for 1h: one oversold (old), one neutral (new).
        indicators = {
            "1h": [
                _indicator("BTCUSDT", "1h", Decimal("15"), offset_seconds=0),
                _indicator("BTCUSDT", "1h", Decimal("55"), offset_seconds=1),
            ],
            "2h": [_indicator("BTCUSDT", "2h", Decimal("55"))],
            "3h": [_indicator("BTCUSDT", "3h", Decimal("55"))],
            "4h": [_indicator("BTCUSDT", "4h", Decimal("55"))],
        }
        # avg RSI will be neutral (~55), no signal expected
        result = evaluate_rsi("BTCUSDT", indicators, _make_rsi_config())
        assert result is None


# ---------------------------------------------------------------------------
# Tests: BUY signal (oversold + converged)
# ---------------------------------------------------------------------------


class TestBuySignal:
    def test_returns_buy_when_all_tfs_oversold_and_converged(self) -> None:
        indicators = {
            "1h": [_indicator("BTCUSDT", "1h", Decimal("27"))],
            "2h": [_indicator("BTCUSDT", "2h", Decimal("25"))],
            "3h": [_indicator("BTCUSDT", "3h", Decimal("28"))],
            "4h": [_indicator("BTCUSDT", "4h", Decimal("26"))],
        }
        result = evaluate_rsi("BTCUSDT", indicators, _make_rsi_config())
        assert result is not None
        assert isinstance(result, RuleResult)
        assert result.direction == "BUY"

    def test_buy_confidence_is_at_least_0_5(self) -> None:
        indicators = {
            "1h": [_indicator("BTCUSDT", "1h", Decimal("30"))],
            "2h": [_indicator("BTCUSDT", "2h", Decimal("30"))],
            "3h": [_indicator("BTCUSDT", "3h", Decimal("30"))],
            "4h": [_indicator("BTCUSDT", "4h", Decimal("30"))],
        }
        result = evaluate_rsi("BTCUSDT", indicators, _make_rsi_config())
        assert result is not None
        assert result.confidence >= Decimal("0.5")

    def test_buy_confidence_increases_as_rsi_approaches_zero(self) -> None:
        indicators_moderate = {
            "1h": [_indicator("BTCUSDT", "1h", Decimal("28"))],
            "2h": [_indicator("BTCUSDT", "2h", Decimal("28"))],
            "3h": [_indicator("BTCUSDT", "3h", Decimal("28"))],
            "4h": [_indicator("BTCUSDT", "4h", Decimal("28"))],
        }
        indicators_extreme = {
            "1h": [_indicator("BTCUSDT", "1h", Decimal("5"))],
            "2h": [_indicator("BTCUSDT", "2h", Decimal("5"))],
            "3h": [_indicator("BTCUSDT", "3h", Decimal("5"))],
            "4h": [_indicator("BTCUSDT", "4h", Decimal("5"))],
        }
        result_moderate = evaluate_rsi("BTCUSDT", indicators_moderate, _make_rsi_config())
        result_extreme = evaluate_rsi("BTCUSDT", indicators_extreme, _make_rsi_config())
        assert result_moderate is not None
        assert result_extreme is not None
        assert result_extreme.confidence > result_moderate.confidence

    def test_buy_confidence_capped_at_1(self) -> None:
        indicators = {
            "1h": [_indicator("BTCUSDT", "1h", Decimal("0"))],
            "2h": [_indicator("BTCUSDT", "2h", Decimal("0"))],
            "3h": [_indicator("BTCUSDT", "3h", Decimal("0"))],
            "4h": [_indicator("BTCUSDT", "4h", Decimal("0"))],
        }
        result = evaluate_rsi("BTCUSDT", indicators, _make_rsi_config())
        assert result is not None
        assert result.confidence <= Decimal("1.0")

    def test_buy_rule_name_contains_oversold(self) -> None:
        indicators = {
            "1h": [_indicator("BTCUSDT", "1h", Decimal("25"))],
            "2h": [_indicator("BTCUSDT", "2h", Decimal("25"))],
            "3h": [_indicator("BTCUSDT", "3h", Decimal("25"))],
            "4h": [_indicator("BTCUSDT", "4h", Decimal("25"))],
        }
        result = evaluate_rsi("BTCUSDT", indicators, _make_rsi_config())
        assert result is not None
        assert "oversold" in result.rule_name


# ---------------------------------------------------------------------------
# Tests: SELL signal (overbought + converged)
# ---------------------------------------------------------------------------


class TestSellSignal:
    def test_returns_sell_when_all_tfs_overbought_and_converged(self) -> None:
        indicators = {
            "1h": [_indicator("BTCUSDT", "1h", Decimal("73"))],
            "2h": [_indicator("BTCUSDT", "2h", Decimal("75"))],
            "3h": [_indicator("BTCUSDT", "3h", Decimal("72"))],
            "4h": [_indicator("BTCUSDT", "4h", Decimal("74"))],
        }
        result = evaluate_rsi("BTCUSDT", indicators, _make_rsi_config())
        assert result is not None
        assert isinstance(result, RuleResult)
        assert result.direction == "SELL"

    def test_sell_confidence_is_at_least_0_5(self) -> None:
        indicators = {
            "1h": [_indicator("BTCUSDT", "1h", Decimal("70"))],
            "2h": [_indicator("BTCUSDT", "2h", Decimal("70"))],
            "3h": [_indicator("BTCUSDT", "3h", Decimal("70"))],
            "4h": [_indicator("BTCUSDT", "4h", Decimal("70"))],
        }
        result = evaluate_rsi("BTCUSDT", indicators, _make_rsi_config())
        assert result is not None
        assert result.confidence >= Decimal("0.5")

    def test_sell_confidence_increases_as_rsi_approaches_100(self) -> None:
        indicators_moderate = {
            "1h": [_indicator("BTCUSDT", "1h", Decimal("72"))],
            "2h": [_indicator("BTCUSDT", "2h", Decimal("72"))],
            "3h": [_indicator("BTCUSDT", "3h", Decimal("72"))],
            "4h": [_indicator("BTCUSDT", "4h", Decimal("72"))],
        }
        indicators_extreme = {
            "1h": [_indicator("BTCUSDT", "1h", Decimal("95"))],
            "2h": [_indicator("BTCUSDT", "2h", Decimal("95"))],
            "3h": [_indicator("BTCUSDT", "3h", Decimal("95"))],
            "4h": [_indicator("BTCUSDT", "4h", Decimal("95"))],
        }
        result_moderate = evaluate_rsi("BTCUSDT", indicators_moderate, _make_rsi_config())
        result_extreme = evaluate_rsi("BTCUSDT", indicators_extreme, _make_rsi_config())
        assert result_moderate is not None
        assert result_extreme is not None
        assert result_extreme.confidence > result_moderate.confidence

    def test_sell_confidence_capped_at_1(self) -> None:
        indicators = {
            "1h": [_indicator("BTCUSDT", "1h", Decimal("100"))],
            "2h": [_indicator("BTCUSDT", "2h", Decimal("100"))],
            "3h": [_indicator("BTCUSDT", "3h", Decimal("100"))],
            "4h": [_indicator("BTCUSDT", "4h", Decimal("100"))],
        }
        result = evaluate_rsi("BTCUSDT", indicators, _make_rsi_config())
        assert result is not None
        assert result.confidence <= Decimal("1.0")

    def test_sell_rule_name_contains_overbought(self) -> None:
        indicators = {
            "1h": [_indicator("BTCUSDT", "1h", Decimal("75"))],
            "2h": [_indicator("BTCUSDT", "2h", Decimal("75"))],
            "3h": [_indicator("BTCUSDT", "3h", Decimal("75"))],
            "4h": [_indicator("BTCUSDT", "4h", Decimal("75"))],
        }
        result = evaluate_rsi("BTCUSDT", indicators, _make_rsi_config())
        assert result is not None
        assert "overbought" in result.rule_name


# ---------------------------------------------------------------------------
# Tests: no signal when TFs don't converge
# ---------------------------------------------------------------------------


class TestNoConvergence:
    def test_returns_none_when_adjacent_tfs_differ_too_much(self) -> None:
        # 1h is oversold but 2h is overbought — large divergence
        indicators = {
            "1h": [_indicator("BTCUSDT", "1h", Decimal("20"))],
            "2h": [_indicator("BTCUSDT", "2h", Decimal("80"))],
            "3h": [_indicator("BTCUSDT", "3h", Decimal("20"))],
            "4h": [_indicator("BTCUSDT", "4h", Decimal("80"))],
        }
        result = evaluate_rsi("BTCUSDT", indicators, _make_rsi_config())
        assert result is None

    def test_returns_none_when_spread_exceeds_threshold(self) -> None:
        # Adjacent pair 1h/2h differ by 10, threshold is 5
        indicators = {
            "1h": [_indicator("BTCUSDT", "1h", Decimal("20"))],
            "2h": [_indicator("BTCUSDT", "2h", Decimal("30"))],
            "3h": [_indicator("BTCUSDT", "3h", Decimal("30"))],
            "4h": [_indicator("BTCUSDT", "4h", Decimal("30"))],
        }
        result = evaluate_rsi("BTCUSDT", indicators, _make_rsi_config())
        assert result is None

    def test_converges_when_spread_equals_threshold(self) -> None:
        # Adjacent pairs all differ by exactly 5 (the threshold limit).
        # avg RSI = 25 => oversold => should fire
        indicators = {
            "1h": [_indicator("BTCUSDT", "1h", Decimal("22"))],
            "2h": [_indicator("BTCUSDT", "2h", Decimal("27"))],
            "3h": [_indicator("BTCUSDT", "3h", Decimal("25"))],
            "4h": [_indicator("BTCUSDT", "4h", Decimal("27"))],
        }
        result = evaluate_rsi("BTCUSDT", indicators, _make_rsi_config())
        # avg RSI = (22+27+25+27)/4 = 25.25 => oversold => BUY
        assert result is not None
        assert result.direction == "BUY"


# ---------------------------------------------------------------------------
# Tests: neutral zone — no signal
# ---------------------------------------------------------------------------


class TestNeutralZone:
    def test_returns_none_when_rsi_between_oversold_and_overbought(self) -> None:
        indicators = {
            "1h": [_indicator("BTCUSDT", "1h", Decimal("50"))],
            "2h": [_indicator("BTCUSDT", "2h", Decimal("52"))],
            "3h": [_indicator("BTCUSDT", "3h", Decimal("51"))],
            "4h": [_indicator("BTCUSDT", "4h", Decimal("50"))],
        }
        result = evaluate_rsi("BTCUSDT", indicators, _make_rsi_config())
        assert result is None

    def test_returns_none_when_rsi_at_exactly_50(self) -> None:
        indicators = {
            "1h": [_indicator("BTCUSDT", "1h", Decimal("50"))],
            "2h": [_indicator("BTCUSDT", "2h", Decimal("50"))],
            "3h": [_indicator("BTCUSDT", "3h", Decimal("50"))],
            "4h": [_indicator("BTCUSDT", "4h", Decimal("50"))],
        }
        result = evaluate_rsi("BTCUSDT", indicators, _make_rsi_config())
        assert result is None

    def test_returns_none_just_below_overbought_threshold(self) -> None:
        # avg RSI = 69 — just below overbought threshold of 70
        indicators = {
            "1h": [_indicator("BTCUSDT", "1h", Decimal("69"))],
            "2h": [_indicator("BTCUSDT", "2h", Decimal("69"))],
            "3h": [_indicator("BTCUSDT", "3h", Decimal("69"))],
            "4h": [_indicator("BTCUSDT", "4h", Decimal("69"))],
        }
        result = evaluate_rsi("BTCUSDT", indicators, _make_rsi_config())
        assert result is None

    def test_returns_none_just_above_oversold_threshold(self) -> None:
        # avg RSI = 31 — just above oversold threshold of 30
        indicators = {
            "1h": [_indicator("BTCUSDT", "1h", Decimal("31"))],
            "2h": [_indicator("BTCUSDT", "2h", Decimal("31"))],
            "3h": [_indicator("BTCUSDT", "3h", Decimal("31"))],
            "4h": [_indicator("BTCUSDT", "4h", Decimal("31"))],
        }
        result = evaluate_rsi("BTCUSDT", indicators, _make_rsi_config())
        assert result is None


# ---------------------------------------------------------------------------
# Tests: symbol propagation
# ---------------------------------------------------------------------------


class TestSymbolPropagation:
    def test_reason_contains_symbol_info(self) -> None:
        indicators = {
            "1h": [_indicator("ETHUSDT", "1h", Decimal("25"))],
            "2h": [_indicator("ETHUSDT", "2h", Decimal("25"))],
            "3h": [_indicator("ETHUSDT", "3h", Decimal("25"))],
            "4h": [_indicator("ETHUSDT", "4h", Decimal("25"))],
        }
        result = evaluate_rsi("ETHUSDT", indicators, _make_rsi_config())
        assert result is not None
        # The reason field should mention the avg RSI
        assert "RSI" in result.reason
