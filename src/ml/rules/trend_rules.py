"""Trend rules: weekly stable vs monthly aggressive trend comparison."""

from __future__ import annotations

import logging
from decimal import Decimal

from src.ml.rules.models import RuleResult
from src.shared.models.crypto import IndicatorRecord

logger = logging.getLogger(__name__)


def _latest(records: list[IndicatorRecord]) -> IndicatorRecord | None:
    """Return the most recent record from a list, or None if empty."""
    if not records:
        return None
    return max(records, key=lambda r: r.timestamp)


def _is_stable_trend(record: IndicatorRecord, slope_threshold: float) -> bool:
    """Return True when the trend slope is within the stable threshold.

    A stable trend has a low absolute slope, meaning price is moving slowly
    and predictably.

    Args:
        record: IndicatorRecord containing trend_slope.
        slope_threshold: Maximum absolute slope considered stable.

    Returns:
        True if trend_slope is present and |slope| <= slope_threshold.
    """
    if record.trend_slope is None:
        return False
    return abs(float(record.trend_slope)) <= slope_threshold


def _is_aggressive_trend(record: IndicatorRecord, slope_threshold: float) -> bool:
    """Return True when the trend slope exceeds the aggressive threshold.

    Args:
        record: IndicatorRecord containing trend_slope.
        slope_threshold: Minimum absolute slope considered aggressive.

    Returns:
        True if trend_slope is present and |slope| >= slope_threshold.
    """
    if record.trend_slope is None:
        return False
    return abs(float(record.trend_slope)) >= slope_threshold


def _trend_direction(record: IndicatorRecord) -> str | None:
    """Return 'up' or 'down' based on sign of trend_slope, or None if missing.

    Args:
        record: IndicatorRecord containing trend_slope.

    Returns:
        "up" if slope > 0, "down" if slope < 0, None if slope is absent.
    """
    if record.trend_slope is None:
        return None
    return "up" if record.trend_slope > Decimal("0") else "down"


def _compute_trend_confidence(
    weekly_slope: Decimal,
    monthly_slope: Decimal,
    weekly_threshold: float,
    monthly_threshold: float,
) -> Decimal:
    """Compute signal confidence from trend slope magnitudes.

    The confidence is proportional to how strongly each timeframe diverges
    in the expected direction.

    Args:
        weekly_slope: Absolute slope from the weekly record.
        monthly_slope: Absolute slope from the monthly record.
        weekly_threshold: Stable slope threshold for weekly.
        monthly_threshold: Aggressive slope threshold for monthly.

    Returns:
        Confidence value clamped to [0.6, 0.95].
    """
    # Normalise: how much does weekly stay under its threshold?
    weekly_stability = Decimal("1") - min(abs(weekly_slope) / Decimal(str(weekly_threshold)), Decimal("1"))
    # Normalise: how much does monthly exceed its threshold?
    monthly_aggression = min(abs(monthly_slope) / Decimal(str(monthly_threshold * 2)), Decimal("1"))
    raw = (weekly_stability + monthly_aggression) / Decimal("2")
    # Map to [0.6, 0.95]
    return Decimal("0.6") + raw * Decimal("0.35")


def evaluate_trend(
    symbol: str,
    indicators: dict[str, list[IndicatorRecord]],
    config: dict,
) -> RuleResult | None:
    """Evaluate weekly vs monthly trend alignment and return a signal.

    Strategy: when the weekly trend is stable (low slope) while the monthly
    trend is aggressive (high slope), and both point in the same direction,
    a high-conviction trend-following signal is generated.

    Special case (BUY opportunity): stable weekly + aggressive monthly uptrend
    with price below the weekly level suggests a dip-buy setup.

    Args:
        symbol: Trading pair symbol, e.g. "BTCUSDT".
        indicators: Mapping of timeframe -> list of IndicatorRecord.
        config: Trend section from indicators.yaml.

    Returns:
        RuleResult with direction and confidence, or None if no signal.
    """
    weekly_cfg: dict = config.get("weekly", {})
    monthly_cfg: dict = config.get("monthly", {})

    weekly_slope_threshold: float = weekly_cfg.get("slope_threshold", 0.001)
    monthly_slope_threshold: float = monthly_cfg.get("slope_threshold", 0.005)

    weekly_records = indicators.get("1W", [])
    monthly_records = indicators.get("1M", [])

    latest_weekly = _latest(weekly_records)
    latest_monthly = _latest(monthly_records)

    if latest_weekly is None:
        logger.debug("Trend rule: no weekly data for %s", symbol)
        return None
    if latest_monthly is None:
        logger.debug("Trend rule: no monthly data for %s", symbol)
        return None

    if latest_weekly.trend_slope is None:
        logger.debug("Trend rule: weekly trend_slope missing for %s", symbol)
        return None
    if latest_monthly.trend_slope is None:
        logger.debug("Trend rule: monthly trend_slope missing for %s", symbol)
        return None

    weekly_stable = _is_stable_trend(latest_weekly, weekly_slope_threshold)
    monthly_aggressive = _is_aggressive_trend(latest_monthly, monthly_slope_threshold)

    weekly_dir = _trend_direction(latest_weekly)
    monthly_dir = _trend_direction(latest_monthly)

    logger.debug(
        "Trend rule for %s: weekly_stable=%s (slope=%s), monthly_aggressive=%s (slope=%s)",
        symbol,
        weekly_stable,
        latest_weekly.trend_slope,
        monthly_aggressive,
        latest_monthly.trend_slope,
    )

    if not monthly_aggressive:
        logger.debug("Trend rule: monthly trend not aggressive enough for %s", symbol)
        return None

    if weekly_dir != monthly_dir:
        # Diverging trends — not a clean signal.
        logger.debug(
            "Trend rule: weekly/monthly directions diverge for %s (%s vs %s)",
            symbol,
            weekly_dir,
            monthly_dir,
        )
        return None

    direction = "BUY" if monthly_dir == "up" else "SELL"

    if weekly_stable and monthly_aggressive and direction == "BUY":
        # Classic dip-buy: stable weekly base with aggressive monthly uptrend.
        confidence = _compute_trend_confidence(
            abs(latest_weekly.trend_slope),
            abs(latest_monthly.trend_slope),
            weekly_slope_threshold,
            monthly_slope_threshold,
        )
        confidence = min(confidence, Decimal("0.95"))
        logger.info(
            "Trend rule: BUY dip opportunity for %s — stable weekly + aggressive monthly "
            "(weekly_slope=%s, monthly_slope=%s, confidence=%.2f)",
            symbol,
            latest_weekly.trend_slope,
            latest_monthly.trend_slope,
            confidence,
        )
        return RuleResult(
            direction="BUY",
            confidence=confidence,
            reason=(
                f"Stable weekly trend (slope={latest_weekly.trend_slope}) + "
                f"aggressive monthly uptrend (slope={latest_monthly.trend_slope}) "
                f"— dip-buy opportunity"
            ),
            rule_name="trend_stable_weekly_aggressive_monthly_buy",
        )

    if not weekly_stable and monthly_aggressive:
        # Both timeframes trending strongly in the same direction.
        confidence = _compute_trend_confidence(
            abs(latest_weekly.trend_slope),
            abs(latest_monthly.trend_slope),
            weekly_slope_threshold,
            monthly_slope_threshold,
        )
        confidence = min(confidence, Decimal("0.85"))
        logger.info(
            "Trend rule: %s trend-following signal for %s (weekly_slope=%s, monthly_slope=%s, confidence=%.2f)",
            direction,
            symbol,
            latest_weekly.trend_slope,
            latest_monthly.trend_slope,
            confidence,
        )
        return RuleResult(
            direction=direction,
            confidence=confidence,
            reason=(
                f"Aligned weekly + monthly {monthly_dir}trend "
                f"(weekly_slope={latest_weekly.trend_slope}, "
                f"monthly_slope={latest_monthly.trend_slope})"
            ),
            rule_name=f"trend_aligned_{direction.lower()}",
        )

    logger.debug("Trend rule: conditions not met for %s", symbol)
    return None
