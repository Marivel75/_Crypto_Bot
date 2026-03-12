"""Bollinger Bands rules: squeeze detection, breakout, and band walking."""

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


def _band_width_pct(record: IndicatorRecord) -> Decimal | None:
    """Compute band width as a fraction of the middle band.

    Args:
        record: IndicatorRecord with Bollinger band fields populated.

    Returns:
        (upper - lower) / middle, or None if any field is missing or middle is zero.
    """
    if (
        record.bollinger_upper is None
        or record.bollinger_lower is None
        or record.bollinger_middle is None
        or record.bollinger_middle == Decimal("0")
    ):
        return None
    return (record.bollinger_upper - record.bollinger_lower) / record.bollinger_middle


def _detect_squeeze(
    indicators: dict[str, list[IndicatorRecord]],
    timeframes: list[str],
    threshold: Decimal,
) -> tuple[bool, list[str]]:
    """Return (is_squeeze, squeezing_timeframes).

    A squeeze is detected when the band width on any timeframe is below
    the threshold.

    Args:
        indicators: Mapping of timeframe -> list of IndicatorRecord.
        timeframes: Timeframes to inspect.
        threshold: Band width fraction below which a squeeze is declared.

    Returns:
        Tuple of (squeeze_detected, list_of_squeezed_timeframes).
    """
    squeezed_tfs: list[str] = []
    for tf in timeframes:
        latest = _latest(indicators.get(tf, []))
        if latest is None:
            continue
        width = _band_width_pct(latest)
        if width is None:
            continue
        if width < threshold:
            squeezed_tfs.append(tf)
    return bool(squeezed_tfs), squeezed_tfs


def _detect_breakout(
    record: IndicatorRecord,
) -> str | None:
    """Detect if price has broken out of the Bollinger Bands.

    Uses price_vs_bollinger field: >1 means above upper, <-1 means below lower.

    Args:
        record: Most recent IndicatorRecord for the primary timeframe.

    Returns:
        "BUY" for upward breakout, "SELL" for downward breakout, None otherwise.
    """
    if record.price_vs_bollinger is None:
        # Fallback: compare close price directly against bands
        if record.bollinger_upper is not None and record.bollinger_lower is not None:
            # We don't have the close price in IndicatorRecord directly;
            # rely on price_vs_bollinger for the comparison.
            return None
        return None

    if record.price_vs_bollinger > Decimal("1"):
        return "BUY"
    if record.price_vs_bollinger < Decimal("-1"):
        return "SELL"
    return None


def _detect_band_walking(
    records: list[IndicatorRecord],
    direction: str,
    min_candles: int = 3,
) -> bool:
    """Detect band walking: price staying near a band for multiple candles.

    Args:
        records: Recent IndicatorRecord list for a single timeframe, sorted by time.
        direction: "upper" or "lower" band walking to check.
        min_candles: Minimum consecutive candles required.

    Returns:
        True if price has been walking the specified band for at least min_candles.
    """
    if len(records) < min_candles:
        return False

    sorted_records = sorted(records, key=lambda r: r.timestamp, reverse=True)
    recent = sorted_records[:min_candles]

    threshold_upper = Decimal("0.7")
    threshold_lower = Decimal("-0.7")

    for record in recent:
        if record.price_vs_bollinger is None:
            return False
        if direction == "upper" and record.price_vs_bollinger < threshold_upper:
            return False
        if direction == "lower" and record.price_vs_bollinger > threshold_lower:
            return False
    return True


def evaluate_bollinger(
    symbol: str,
    indicators: dict[str, list[IndicatorRecord]],
    config: dict,
) -> RuleResult | None:
    """Evaluate Bollinger Band conditions and return a trading signal.

    Priority order:
    1. Breakout on primary timeframe (4h if available, else first available).
    2. Band walking (continuation signal).
    3. Post-squeeze directional bias (squeeze present, no breakout yet).

    Args:
        symbol: Trading pair symbol, e.g. "BTCUSDT".
        indicators: Mapping of timeframe -> list of IndicatorRecord.
        config: Bollinger section from indicators.yaml.

    Returns:
        RuleResult with direction and confidence, or None if no signal.
    """
    timeframes: list[str] = config.get("timeframes", ["1h", "2h", "3h", "4h", "1D"])
    squeeze_threshold = Decimal(str(config.get("squeeze_threshold", 0.02)))

    # Choose primary timeframe: prefer 4h, fall back to first available.
    primary_tf: str | None = None
    for preferred in ("4h", "1D", "1h", "2h", "3h"):
        if preferred in timeframes and indicators.get(preferred):
            primary_tf = preferred
            break

    if primary_tf is None:
        logger.debug("Bollinger rule: no usable timeframe data for %s", symbol)
        return None

    primary_records = indicators.get(primary_tf, [])
    latest_primary = _latest(primary_records)
    if latest_primary is None:
        logger.debug("Bollinger rule: no primary TF record for %s %s", symbol, primary_tf)
        return None

    # 1. Breakout detection (highest confidence)
    breakout_dir = _detect_breakout(latest_primary)
    if breakout_dir is not None:
        pvb = latest_primary.price_vs_bollinger or Decimal("0")
        raw_strength = min(abs(pvb) - Decimal("1"), Decimal("1"))
        confidence = Decimal("0.6") + raw_strength * Decimal("0.3")
        confidence = min(confidence, Decimal("0.9"))
        logger.info(
            "Bollinger rule: %s breakout for %s on %s (price_vs_bb=%.2f, confidence=%.2f)",
            breakout_dir,
            symbol,
            primary_tf,
            pvb,
            confidence,
        )
        return RuleResult(
            direction=breakout_dir,
            confidence=confidence,
            reason=(
                f"Bollinger {'upward' if breakout_dir == 'BUY' else 'downward'} "
                f"breakout on {primary_tf} (price_vs_bb={pvb:.2f})"
            ),
            rule_name=f"bollinger_breakout_{primary_tf}",
        )

    # 2. Band walking detection
    for walk_dir, signal_dir in (("upper", "BUY"), ("lower", "SELL")):
        if _detect_band_walking(primary_records, walk_dir):
            logger.info(
                "Bollinger rule: %s band walking for %s on %s",
                walk_dir,
                symbol,
                primary_tf,
            )
            return RuleResult(
                direction=signal_dir,
                confidence=Decimal("0.65"),
                reason=f"Bollinger band walking ({walk_dir}) on {primary_tf}",
                rule_name=f"bollinger_band_walking_{walk_dir}",
            )

    # 3. Squeeze detection (potential upcoming breakout — neutral/low confidence)
    is_squeezed, squeezed_tfs = _detect_squeeze(indicators, timeframes, squeeze_threshold)
    if is_squeezed:
        logger.info(
            "Bollinger rule: squeeze detected for %s on %s — no breakout yet",
            symbol,
            squeezed_tfs,
        )
        # Squeeze alone is not directional enough to emit a confident signal.
        # Return None and let future candles produce a breakout signal.
        return None

    logger.debug("Bollinger rule: no signal for %s", symbol)
    return None
