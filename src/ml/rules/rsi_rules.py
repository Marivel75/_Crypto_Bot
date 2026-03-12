"""RSI multi-timeframe convergence rules for trading signal generation."""

from __future__ import annotations

import logging
from decimal import Decimal

from src.ml.rules.models import RuleResult
from src.shared.models.crypto import IndicatorRecord

logger = logging.getLogger(__name__)

_ADJACENT_PAIRS = [("1h", "2h"), ("2h", "3h"), ("3h", "4h")]


def _latest(records: list[IndicatorRecord]) -> IndicatorRecord | None:
    """Return the most recent record from a list, or None if empty."""
    if not records:
        return None
    return max(records, key=lambda r: r.timestamp)


def _check_convergence(
    rsi_by_tf: dict[str, Decimal],
    threshold: int,
    timeframes: list[str],
) -> bool:
    """Return True when all adjacent timeframe RSI values are within threshold.

    Args:
        rsi_by_tf: Mapping of timeframe -> RSI value.
        threshold: Maximum allowed difference between adjacent TF values.
        timeframes: Ordered list of timeframes to check adjacency for.

    Returns:
        True if all adjacent pairs in timeframes are within threshold.
    """
    ordered = [tf for tf in timeframes if tf in rsi_by_tf]
    if len(ordered) < 2:
        return False

    for i in range(len(ordered) - 1):
        tf_a, tf_b = ordered[i], ordered[i + 1]
        diff = abs(rsi_by_tf[tf_a] - rsi_by_tf[tf_b])
        if diff > Decimal(str(threshold)):
            return False
    return True


def evaluate_rsi(
    symbol: str,
    indicators: dict[str, list[IndicatorRecord]],
    config: dict,
) -> RuleResult | None:
    """Evaluate RSI convergence across multiple timeframes and return a signal.

    Checks whether RSI values converge across 1h/2h/3h/4h timeframes and
    whether they indicate an overbought (SELL) or oversold (BUY) condition.
    A signal is only returned when all adjacent timeframes are within
    `convergence_threshold` of each other AND the averaged RSI crosses a
    threshold.

    Args:
        symbol: Trading pair symbol, e.g. "BTCUSDT".
        indicators: Mapping of timeframe -> list of IndicatorRecord.
        config: RSI section from indicators.yaml.

    Returns:
        RuleResult with direction and confidence, or None if no signal.
    """
    timeframes: list[str] = config.get("timeframes", ["1h", "2h", "3h", "4h"])
    overbought: int = config.get("overbought", 70)
    oversold: int = config.get("oversold", 30)
    convergence_threshold: int = config.get("convergence_threshold", 5)

    rsi_by_tf: dict[str, Decimal] = {}
    for tf in timeframes:
        records = indicators.get(tf, [])
        latest = _latest(records)
        if latest is None or latest.rsi is None:
            logger.debug("RSI rule: no data for %s %s — skipping", symbol, tf)
            continue
        rsi_by_tf[tf] = latest.rsi

    if len(rsi_by_tf) < 2:
        logger.debug("RSI rule: insufficient timeframe data for %s", symbol)
        return None

    converged = _check_convergence(rsi_by_tf, convergence_threshold, timeframes)
    if not converged:
        logger.debug(
            "RSI rule: timeframes not converged for %s — values: %s",
            symbol,
            rsi_by_tf,
        )
        return None

    avg_rsi = sum(rsi_by_tf.values()) / Decimal(str(len(rsi_by_tf)))
    covered_tfs = list(rsi_by_tf.keys())

    if avg_rsi >= Decimal(str(overbought)):
        # Confidence scales from 0.5 at the threshold up toward 1.0 at RSI=100
        raw = (avg_rsi - Decimal(str(overbought))) / Decimal(str(100 - overbought))
        confidence = Decimal("0.5") + raw * Decimal("0.5")
        confidence = min(confidence, Decimal("1.0"))
        logger.info(
            "RSI rule: SELL signal for %s — avg RSI %.2f across %s (confidence %.2f)",
            symbol,
            avg_rsi,
            covered_tfs,
            confidence,
        )
        return RuleResult(
            direction="SELL",
            confidence=confidence,
            reason=(f"RSI overbought (avg={avg_rsi:.1f}) converged across {covered_tfs}"),
            rule_name="rsi_overbought_multi_tf",
        )

    if avg_rsi <= Decimal(str(oversold)):
        # Confidence scales from 0.5 at the threshold up toward 1.0 at RSI=0
        raw = (Decimal(str(oversold)) - avg_rsi) / Decimal(str(oversold))
        confidence = Decimal("0.5") + raw * Decimal("0.5")
        confidence = min(confidence, Decimal("1.0"))
        logger.info(
            "RSI rule: BUY signal for %s — avg RSI %.2f across %s (confidence %.2f)",
            symbol,
            avg_rsi,
            covered_tfs,
            confidence,
        )
        return RuleResult(
            direction="BUY",
            confidence=confidence,
            reason=(f"RSI oversold (avg={avg_rsi:.1f}) converged across {covered_tfs}"),
            rule_name="rsi_oversold_multi_tf",
        )

    logger.debug("RSI rule: no extreme condition for %s — avg RSI %.2f", symbol, avg_rsi)
    return None
