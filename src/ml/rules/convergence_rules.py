"""Convergence rules: fire when multiple independent indicators align.

These rules carry higher weight than single-indicator rules because
simultaneous agreement across indicator families reduces false-positive rates.
"""

from __future__ import annotations

import logging
from typing import Any

from src.ml.rules.base_rule import BaseRule
from src.ml.rules.models import RuleLabel, RuleResult
from src.shared.models.crypto import IndicatorRecord

logger = logging.getLogger(__name__)

# ---- Standalone pure-function API (used by RuleEngine directly) ----


def evaluate_rsi_bollinger_convergence(
    indicators: dict[str, IndicatorRecord | None],
    config: dict[str, Any],
) -> list[RuleResult]:
    """RSI + Bollinger Band convergence across timeframes.

    A strong BULL signal fires when RSI is oversold **and** price sits near
    the lower Bollinger band on the same timeframe.  The mirror produces a
    BEAR signal.  Convergence across multiple TFs increases the weight.

    Args:
        indicators: Mapping from timeframe to latest indicator snapshot.
        config: Must contain ``rsi_oversold``, ``rsi_overbought``,
            ``bb_lower_threshold`` (default -0.7), ``bb_upper_threshold``
            (default 0.7), and ``timeframes``.

    Returns:
        List of ``RuleResult`` objects (may be empty).
    """
    overbought: float = config.get("rsi_overbought", 70)
    oversold: float = config.get("rsi_oversold", 30)
    bb_lower: float = config.get("bb_lower_threshold", -0.7)
    bb_upper: float = config.get("bb_upper_threshold", 0.7)
    timeframes: list[str] = config.get("timeframes", ["1h", "2h", "3h", "4h"])

    bull_tfs: list[str] = []
    bear_tfs: list[str] = []

    for tf in timeframes:
        ind = indicators.get(tf)
        if ind is None or ind.rsi is None or ind.price_vs_bollinger is None:
            continue
        rsi_val = float(ind.rsi)
        pos = float(ind.price_vs_bollinger)

        if rsi_val <= oversold and pos <= bb_lower:
            bull_tfs.append(tf)
        elif rsi_val >= overbought and pos >= bb_upper:
            bear_tfs.append(tf)

    results: list[RuleResult] = []

    if len(bull_tfs) >= 2:
        results.append(
            RuleResult(
                rule_name="rsi_bb_convergence_bull_multi_tf",
                label=RuleLabel.BULL,
                weight=0.95,
                detail=f"RSI oversold + lower band on {len(bull_tfs)} TFs: {bull_tfs}",
            )
        )
    elif len(bull_tfs) == 1:
        results.append(
            RuleResult(
                rule_name="rsi_bb_convergence_bull",
                label=RuleLabel.BULL,
                weight=0.75,
                detail=f"RSI oversold + lower band on {bull_tfs[0]}",
            )
        )

    if len(bear_tfs) >= 2:
        results.append(
            RuleResult(
                rule_name="rsi_bb_convergence_bear_multi_tf",
                label=RuleLabel.BEAR,
                weight=0.95,
                detail=f"RSI overbought + upper band on {len(bear_tfs)} TFs: {bear_tfs}",
            )
        )
    elif len(bear_tfs) == 1:
        results.append(
            RuleResult(
                rule_name="rsi_bb_convergence_bear",
                label=RuleLabel.BEAR,
                weight=0.75,
                detail=f"RSI overbought + upper band on {bear_tfs[0]}",
            )
        )

    return results


def evaluate_trend_rsi_convergence(
    indicators: dict[str, IndicatorRecord | None],
    config: dict[str, Any],
) -> list[RuleResult]:
    """Trend slope + RSI convergence.

    A BULL signal fires when the higher-TF trend slope is positive and a
    lower TF RSI is oversold (dip into uptrend).  A BEAR signal fires for
    the mirror case.

    Args:
        indicators: Multi-TF indicator snapshot.
        config: May contain ``rsi_oversold``, ``rsi_overbought``,
            ``trend_tf`` (default ``"1W"``), and ``rsi_tfs``.

    Returns:
        List of ``RuleResult`` objects (may be empty).
    """
    overbought: float = config.get("rsi_overbought", 70)
    oversold: float = config.get("rsi_oversold", 30)
    trend_tf: str = config.get("trend_tf", "1W")
    rsi_tfs: list[str] = config.get("rsi_tfs", ["1h", "4h"])

    results: list[RuleResult] = []

    trend_ind = indicators.get(trend_tf)
    if trend_ind is None or trend_ind.trend_slope is None:
        return results

    trend_slope = float(trend_ind.trend_slope)

    for tf in rsi_tfs:
        ind = indicators.get(tf)
        if ind is None or ind.rsi is None:
            continue
        rsi_val = float(ind.rsi)

        if trend_slope > 0 and rsi_val <= oversold:
            results.append(
                RuleResult(
                    rule_name=f"trend_rsi_dip_bull_{tf}",
                    label=RuleLabel.BULL,
                    weight=0.8,
                    detail=(f"Uptrend ({trend_tf} slope={trend_slope:.4f}) + RSI oversold on {tf} ({rsi_val:.1f})"),
                )
            )
        elif trend_slope < 0 and rsi_val >= overbought:
            results.append(
                RuleResult(
                    rule_name=f"trend_rsi_rally_bear_{tf}",
                    label=RuleLabel.BEAR,
                    weight=0.8,
                    detail=(f"Downtrend ({trend_tf} slope={trend_slope:.4f}) + RSI overbought on {tf} ({rsi_val:.1f})"),
                )
            )

    return results


# ---- Class-based API (conforms to BaseRule ABC) ----


class RsiBollingerConvergence(BaseRule):
    """Class wrapper for :func:`evaluate_rsi_bollinger_convergence`.

    Conforms to the ``BaseRule`` ABC so it can be used in any pipeline that
    works with rule objects instead of bare functions.
    """

    def evaluate(
        self,
        indicators: dict[str, IndicatorRecord | None],
    ) -> list[RuleResult]:
        """Delegate to the standalone convergence function."""
        return evaluate_rsi_bollinger_convergence(indicators, self._config)


class TrendRsiConvergence(BaseRule):
    """Class wrapper for :func:`evaluate_trend_rsi_convergence`."""

    def evaluate(
        self,
        indicators: dict[str, IndicatorRecord | None],
    ) -> list[RuleResult]:
        """Delegate to the standalone trend+RSI convergence function."""
        return evaluate_trend_rsi_convergence(indicators, self._config)
