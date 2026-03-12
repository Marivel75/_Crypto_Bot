"""Multi-timeframe alignment rules.

These rules aggregate directional signals across several timeframes and fire
when a majority or supermajority agrees on the same direction. Alignment
across TFs is a strong confirmation signal and carries high weight.
"""

from __future__ import annotations

import logging
from typing import Any

from src.ml.rules.base_rule import BaseRule
from src.ml.rules.models import RuleLabel, RuleResult
from src.shared.models.crypto import IndicatorRecord

logger = logging.getLogger(__name__)


def _infer_tf_direction(
    ind: IndicatorRecord,
    rsi_overbought: float,
    rsi_oversold: float,
) -> RuleLabel:
    """Infer a single timeframe's directional bias from available indicators.

    Decision hierarchy (first match wins):
    1. RSI extreme (strongest single signal)
    2. Bollinger position (price vs bands)
    3. Trend slope

    Returns ``RuleLabel.NEUTRAL`` when no clear signal exists.

    Args:
        ind: Latest indicator snapshot for one timeframe.
        rsi_overbought: RSI threshold above which the market is overbought.
        rsi_oversold: RSI threshold below which the market is oversold.

    Returns:
        :class:`RuleLabel` indicating BULL, BEAR, or NEUTRAL bias.
    """
    # RSI
    if ind.rsi is not None:
        rsi_val = float(ind.rsi)
        if rsi_val <= rsi_oversold:
            return RuleLabel.BULL
        if rsi_val >= rsi_overbought:
            return RuleLabel.BEAR

    # Bollinger position
    if ind.price_vs_bollinger is not None:
        pos = float(ind.price_vs_bollinger)
        if pos <= -0.7:
            return RuleLabel.BULL
        if pos >= 0.7:
            return RuleLabel.BEAR

    # Trend slope
    if ind.trend_slope is not None:
        slope = float(ind.trend_slope)
        if slope > 0.001:
            return RuleLabel.BULL
        if slope < -0.001:
            return RuleLabel.BEAR

    return RuleLabel.NEUTRAL


def evaluate_multi_tf_alignment(
    indicators: dict[str, IndicatorRecord | None],
    config: dict[str, Any],
) -> list[RuleResult]:
    """Check whether a majority of timeframes agree on a direction.

    A signal fires when at least ``majority_threshold`` fraction of the
    available (non-None) timeframes return the same non-neutral label.

    Args:
        indicators: Mapping from timeframe string to latest indicator snapshot.
        config: Must contain ``timeframes`` (list[str]),
            ``rsi_overbought`` (default 70), ``rsi_oversold`` (default 30),
            and optionally ``majority_threshold`` (default 0.6).

    Returns:
        A (possibly empty) list of ``RuleResult`` objects.
    """
    timeframes: list[str] = config.get("timeframes", ["1h", "2h", "3h", "4h"])
    rsi_overbought: float = config.get("rsi_overbought", 70)
    rsi_oversold: float = config.get("rsi_oversold", 30)
    majority_threshold: float = config.get("majority_threshold", 0.6)

    bull_count = 0
    bear_count = 0
    total = 0

    for tf in timeframes:
        ind = indicators.get(tf)
        if ind is None:
            continue
        total += 1
        label = _infer_tf_direction(ind, rsi_overbought, rsi_oversold)
        if label == RuleLabel.BULL:
            bull_count += 1
        elif label == RuleLabel.BEAR:
            bear_count += 1

    if total == 0:
        logger.debug("multi_tf_alignment: no indicator data available")
        return []

    results: list[RuleResult] = []
    bull_ratio = bull_count / total
    bear_ratio = bear_count / total

    if bull_ratio >= majority_threshold:
        # Scale weight with how strong the consensus is
        weight = 0.6 + 0.3 * (bull_ratio - majority_threshold) / (1 - majority_threshold)
        weight = min(weight, 0.9)
        results.append(
            RuleResult(
                rule_name="multi_tf_alignment_bull",
                label=RuleLabel.BULL,
                weight=round(weight, 3),
                detail=(f"Multi-TF bullish alignment: {bull_count}/{total} TFs ({bull_ratio:.0%}) agree on BULL"),
            )
        )
    elif bear_ratio >= majority_threshold:
        weight = 0.6 + 0.3 * (bear_ratio - majority_threshold) / (1 - majority_threshold)
        weight = min(weight, 0.9)
        results.append(
            RuleResult(
                rule_name="multi_tf_alignment_bear",
                label=RuleLabel.BEAR,
                weight=round(weight, 3),
                detail=(f"Multi-TF bearish alignment: {bear_count}/{total} TFs ({bear_ratio:.0%}) agree on BEAR"),
            )
        )
    else:
        logger.debug(
            "multi_tf_alignment: no majority (bull=%.0f%%, bear=%.0f%%)",
            bull_ratio * 100,
            bear_ratio * 100,
        )

    return results


def evaluate_supermajority_tf_alignment(
    indicators: dict[str, IndicatorRecord | None],
    config: dict[str, Any],
) -> list[RuleResult]:
    """Fire a high-weight signal when ALL available timeframes agree.

    This is the strongest alignment signal. It requires unanimity (or near
    unanimity) and emits a weight of 1.0 when all TFs agree.

    Args:
        indicators: Multi-TF indicator snapshot.
        config: Same keys as :func:`evaluate_multi_tf_alignment` plus
            ``supermajority_threshold`` (default 1.0 = unanimous).

    Returns:
        A (possibly empty) list of ``RuleResult`` objects.
    """
    timeframes: list[str] = config.get("timeframes", ["1h", "2h", "3h", "4h"])
    rsi_overbought: float = config.get("rsi_overbought", 70)
    rsi_oversold: float = config.get("rsi_oversold", 30)
    supermajority: float = config.get("supermajority_threshold", 1.0)

    labels: list[RuleLabel] = []
    for tf in timeframes:
        ind = indicators.get(tf)
        if ind is None:
            continue
        labels.append(_infer_tf_direction(ind, rsi_overbought, rsi_oversold))

    if not labels:
        return []

    non_neutral = [lb for lb in labels if lb != RuleLabel.NEUTRAL]
    if not non_neutral:
        return []

    total_non_neutral = len(non_neutral)
    bull_count = non_neutral.count(RuleLabel.BULL)
    bear_count = non_neutral.count(RuleLabel.BEAR)

    results: list[RuleResult] = []

    if bull_count / total_non_neutral >= supermajority:
        results.append(
            RuleResult(
                rule_name="multi_tf_supermajority_bull",
                label=RuleLabel.BULL,
                weight=1.0,
                detail=(f"All {bull_count} non-neutral TFs agree: BULL (supermajority={supermajority:.0%})"),
            )
        )
    elif bear_count / total_non_neutral >= supermajority:
        results.append(
            RuleResult(
                rule_name="multi_tf_supermajority_bear",
                label=RuleLabel.BEAR,
                weight=1.0,
                detail=(f"All {bear_count} non-neutral TFs agree: BEAR (supermajority={supermajority:.0%})"),
            )
        )

    return results


# ---- Class-based wrappers ----


class MultiTfAlignment(BaseRule):
    """Class wrapper for :func:`evaluate_multi_tf_alignment`."""

    def evaluate(
        self,
        indicators: dict[str, IndicatorRecord | None],
    ) -> list[RuleResult]:
        """Delegate to the standalone multi-TF alignment function."""
        return evaluate_multi_tf_alignment(indicators, self._config)


class SupermajorityTfAlignment(BaseRule):
    """Class wrapper for :func:`evaluate_supermajority_tf_alignment`."""

    def evaluate(
        self,
        indicators: dict[str, IndicatorRecord | None],
    ) -> list[RuleResult]:
        """Delegate to the standalone supermajority alignment function."""
        return evaluate_supermajority_tf_alignment(indicators, self._config)
