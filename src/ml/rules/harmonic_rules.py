"""Harmonic pattern rules based on Fibonacci ratios (Gartley, Bat, Butterfly, Crab)."""

from __future__ import annotations

import logging
from decimal import Decimal

from src.ml.rules.models import RuleResult
from src.shared.models.crypto import IndicatorRecord

logger = logging.getLogger(__name__)

# Patterns that typically signal a bullish reversal at point D.
_BULLISH_PATTERNS = {"gartley", "bat", "butterfly", "crab"}
# Patterns that typically signal a bearish reversal at point D.
_BEARISH_PATTERNS: set[str] = set()  # All listed patterns can be bullish or bearish;
# direction is inferred from the pattern name suffix if encoded, or treated as BUY by default.

# Confidence assigned per pattern (based on reliability heuristics).
_PATTERN_CONFIDENCE: dict[str, Decimal] = {
    "gartley": Decimal("0.72"),
    "butterfly": Decimal("0.68"),
    "bat": Decimal("0.70"),
    "crab": Decimal("0.75"),
}


def _latest(records: list[IndicatorRecord]) -> IndicatorRecord | None:
    """Return the most recent record from a list, or None if empty."""
    if not records:
        return None
    return max(records, key=lambda r: r.timestamp)


def _parse_pattern_name(raw: str) -> tuple[str, str]:
    """Extract base pattern name and implied direction from harmonic_pattern field.

    Convention: a pattern name ending in "_bearish" or "_sell" is a SELL signal.
    Everything else defaults to BUY.

    Args:
        raw: Value of IndicatorRecord.harmonic_pattern, e.g. "gartley_bearish".

    Returns:
        Tuple of (base_name, direction) where direction is "BUY" or "SELL".
    """
    lower = raw.lower().strip()
    direction = "BUY"
    if lower.endswith("_bearish") or lower.endswith("_sell"):
        direction = "SELL"
        base = lower.rsplit("_", 1)[0]
    elif lower.endswith("_bullish") or lower.endswith("_buy"):
        base = lower.rsplit("_", 1)[0]
    else:
        base = lower
    return base, direction


def _validate_ratio(
    value: float | Decimal,
    spec: float | list[float],
    tolerance: float,
) -> bool:
    """Check whether a ratio falls within the allowed range (with tolerance).

    Args:
        value: Observed Fibonacci ratio.
        spec: Expected ratio (scalar) or [min, max] range from config.
        tolerance: Fractional tolerance to widen the accepted range.

    Returns:
        True if value is within the accepted range.
    """
    v = float(value)
    tol = tolerance
    if isinstance(spec, list):
        lo, hi = spec[0], spec[1]
        return (lo - tol) <= v <= (hi + tol)
    return abs(v - spec) <= tol


def _score_pattern(
    pattern_name: str,
    record: IndicatorRecord,
    pattern_config: dict,
    tolerance: float,
) -> Decimal:
    """Score a detected pattern based on how well the metadata ratios match config.

    Reads Fibonacci ratios from record.metadata keys: xb_ratio, ac_ratio,
    bd_ratio, xd_ratio (floats). Returns a confidence multiplier in [0.8, 1.0]
    based on how many ratios are present and valid.

    Args:
        pattern_name: Lowercase base pattern name.
        record: IndicatorRecord containing the detected pattern.
        pattern_config: Per-pattern Fibonacci spec from config.
        tolerance: Tolerance from config.

    Returns:
        Confidence multiplier (1.0 if all ratios match, lower if partial).
    """
    spec = pattern_config.get(pattern_name, {})
    if not spec:
        return Decimal("0.9")  # pattern known but no spec to validate

    ratio_keys = {"xb": "xb_ratio", "xd": "xd_ratio", "ac": "ac_ratio", "bd": "bd_ratio"}
    total = 0
    matched = 0

    for cfg_key, meta_key in ratio_keys.items():
        if cfg_key not in spec:
            continue
        total += 1
        meta_val = record.metadata.get(meta_key)
        if meta_val is None:
            continue
        if _validate_ratio(meta_val, spec[cfg_key], tolerance):
            matched += 1

    if total == 0:
        return Decimal("0.9")

    ratio_score = matched / total
    # Scale to [0.75, 1.0] range
    return Decimal("0.75") + Decimal(str(ratio_score)) * Decimal("0.25")


def evaluate_harmonic(
    symbol: str,
    indicators: dict[str, list[IndicatorRecord]],
    config: dict,
) -> RuleResult | None:
    """Evaluate harmonic pattern detection and return a trading signal.

    Checks whether any IndicatorRecord across the configured timeframes has a
    populated harmonic_pattern field. When found, validates the Fibonacci ratios
    stored in record.metadata against the pattern spec in config, and computes
    a confidence score.

    Args:
        symbol: Trading pair symbol, e.g. "BTCUSDT".
        indicators: Mapping of timeframe -> list of IndicatorRecord.
        config: Harmonic section from indicators.yaml.

    Returns:
        RuleResult with direction and confidence, or None if no pattern found.
    """
    timeframes: list[str] = config.get("timeframes", ["4h", "1D"])
    tolerance: float = config.get("tolerance", 0.05)
    pattern_config: dict = config.get("patterns", {})

    known_patterns = set(pattern_config.keys())

    best_result: RuleResult | None = None
    best_confidence = Decimal("0")

    for tf in timeframes:
        records = indicators.get(tf, [])
        latest = _latest(records)
        if latest is None or not latest.harmonic_pattern:
            continue

        raw_pattern = latest.harmonic_pattern
        base_name, direction = _parse_pattern_name(raw_pattern)

        if base_name not in known_patterns:
            logger.warning(
                "Harmonic rule: unknown pattern '%s' for %s %s — skipping",
                raw_pattern,
                symbol,
                tf,
            )
            continue

        base_confidence = _PATTERN_CONFIDENCE.get(base_name, Decimal("0.65"))
        score_multiplier = _score_pattern(base_name, latest, pattern_config, tolerance)
        confidence = base_confidence * score_multiplier
        confidence = min(confidence, Decimal("1.0"))

        if confidence > best_confidence:
            best_confidence = confidence
            best_result = RuleResult(
                direction=direction,
                confidence=confidence,
                reason=(f"Harmonic {base_name} pattern ({direction.lower()}) detected on {tf}"),
                rule_name=f"harmonic_{base_name}_{tf}",
            )

    if best_result is not None:
        logger.info(
            "Harmonic rule: %s signal for %s — %s (confidence=%.2f)",
            best_result.direction,
            symbol,
            best_result.reason,
            best_result.confidence,
        )
    else:
        logger.debug("Harmonic rule: no pattern detected for %s", symbol)

    return best_result
