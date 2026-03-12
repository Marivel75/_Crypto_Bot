"""Rule engine: orchestrates all rule evaluators and aggregates results into a TradingSignal."""

from __future__ import annotations

import logging
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal, cast

import yaml  # type: ignore[import-untyped]

from src.ml.rules.models import RuleLabel, RuleResult
from src.shared.constants import SIGNAL_CONFIDENCE_THRESHOLD
from src.shared.models.crypto import IndicatorRecord
from src.shared.models.signal import TradingSignal

logger = logging.getLogger(__name__)

# Rule weights must sum to 1.0.
_RULE_WEIGHTS: dict[str, Decimal] = {
    "rsi": Decimal("0.25"),
    "bollinger": Decimal("0.25"),
    "harmonic": Decimal("0.30"),
    "trend": Decimal("0.20"),
}

_MODEL_VERSION = "rules_v1"


class RuleEngine:
    """Orchestrates all rule modules and aggregates results into a TradingSignal.

    Usage::

        engine = RuleEngine(config_path=Path("src/ml/config/indicators.yaml"))
        results = engine.evaluate("BTCUSDT", indicators_by_tf)
        signal = engine.aggregate(results, symbol="BTCUSDT")

    Attributes:
        config: Full parsed indicators.yaml config dict.
    """

    def __init__(self, config_path: Path) -> None:
        """Load indicator configuration from a YAML file.

        Args:
            config_path: Absolute or relative path to indicators.yaml.

        Raises:
            FileNotFoundError: If config_path does not exist.
            yaml.YAMLError: If the file is not valid YAML.
        """
        if not config_path.exists():
            raise FileNotFoundError(f"Indicator config not found: {config_path}")

        with config_path.open("r", encoding="utf-8") as fh:
            self.config: dict = yaml.safe_load(fh)

        logger.info("RuleEngine loaded config from %s", config_path)

    @classmethod
    def from_yaml(cls, config_path: Path | None = None) -> RuleEngine:
        """Construct a RuleEngine from the default indicators.yaml config.

        Args:
            config_path: Optional override path to a YAML config file.
                Defaults to ``src/ml/config/indicators.yaml`` relative to
                this file's location.

        Returns:
            Initialised :class:`RuleEngine` instance.
        """
        if config_path is None:
            # Resolve sibling config directory relative to this source file
            config_path = Path(__file__).parent.parent / "config" / "indicators.yaml"
        return cls(config_path)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def evaluate(
        self,
        symbol: str,
        indicators: dict[str, list[IndicatorRecord]],
    ) -> list[RuleResult]:
        """Run all rule evaluators and return their individual results.

        Evaluators are imported lazily here to avoid circular import issues
        (rsi_rules, bollinger_rules, etc. import RuleResult from this module).

        Args:
            symbol: Trading pair symbol, e.g. "BTCUSDT".
            indicators: Mapping of timeframe -> list of IndicatorRecord.

        Returns:
            List of RuleResult items (may be empty if no rules fire).
        """
        # Local imports to break the circular dependency: rule modules import
        # RuleResult from this file, so we cannot import them at module level.
        from src.ml.rules.bollinger_rules import evaluate_bollinger
        from src.ml.rules.convergence_rules import (
            evaluate_rsi_bollinger_convergence,
            evaluate_trend_rsi_convergence,
        )
        from src.ml.rules.harmonic_rules import evaluate_harmonic
        from src.ml.rules.multi_tf_rules import (
            evaluate_multi_tf_alignment,
            evaluate_supermajority_tf_alignment,
        )
        from src.ml.rules.rsi_rules import evaluate_rsi
        from src.ml.rules.trend_rules import evaluate_trend

        rsi_cfg = self.config.get("rsi", {})
        bollinger_cfg = self.config.get("bollinger", {})
        harmonic_cfg = self.config.get("harmonic", {})
        trend_cfg = self.config.get("trend", {})
        multi_tf_cfg = self.config.get("multi_tf", {})

        # Build combined config for convergence rules
        convergence_cfg: dict = {
            **bollinger_cfg,
            "timeframes": rsi_cfg.get("timeframes", ["1h", "2h", "3h", "4h"]),
            "rsi_overbought": rsi_cfg.get("overbought", 70),
            "rsi_oversold": rsi_cfg.get("oversold", 30),
        }
        trend_rsi_cfg: dict = {
            **trend_cfg,
            "rsi_overbought": rsi_cfg.get("overbought", 70),
            "rsi_oversold": rsi_cfg.get("oversold", 30),
            "rsi_tfs": rsi_cfg.get("timeframes", ["1h", "4h"]),
        }
        alignment_cfg: dict = {
            **multi_tf_cfg,
            "rsi_overbought": rsi_cfg.get("overbought", 70),
            "rsi_oversold": rsi_cfg.get("oversold", 30),
        }

        # These evaluators accept (symbol, indicators, cfg) -> RuleResult | None
        legacy_evaluators = [
            ("rsi", evaluate_rsi, rsi_cfg),
            ("bollinger", evaluate_bollinger, bollinger_cfg),
            ("harmonic", evaluate_harmonic, harmonic_cfg),
            ("trend", evaluate_trend, trend_cfg),
        ]

        results: list[RuleResult] = []

        # Legacy evaluators (return single RuleResult | None)
        for rule_key, fn, cfg in legacy_evaluators:
            try:
                result = fn(symbol, indicators, cfg)
                if result is not None:
                    results.append(result)
                    logger.debug(
                        "Rule '%s' fired for %s: %s (confidence=%.2f)",
                        rule_key,
                        symbol,
                        result.direction,
                        result.confidence,
                    )
            except Exception:
                logger.exception(
                    "Rule '%s' raised an unexpected error for %s — skipping",
                    rule_key,
                    symbol,
                )

        # New multi-result evaluators (return list[RuleResult])
        # These accept (indicators_by_tf_snapshot, cfg) where the snapshot is
        # the latest IndicatorRecord per TF, not a list.
        # We extract the latest record per TF from the list-based indicators.
        latest_by_tf: dict[str, Any] = {tf: records[0] if records else None for tf, records in indicators.items()}

        list_evaluators: list[tuple[str, Any, dict[str, Any]]] = [
            ("convergence_rsi_bb", evaluate_rsi_bollinger_convergence, convergence_cfg),
            ("convergence_trend_rsi", evaluate_trend_rsi_convergence, trend_rsi_cfg),
            ("multi_tf_alignment", evaluate_multi_tf_alignment, alignment_cfg),
            ("multi_tf_supermajority", evaluate_supermajority_tf_alignment, alignment_cfg),
        ]
        for rule_key, list_fn, cfg in list_evaluators:
            try:
                rule_list: list[RuleResult] = list_fn(latest_by_tf, cfg)
                for r in rule_list:
                    results.append(r)
                    logger.debug(
                        "Rule '%s' fired for %s: label=%s weight=%.2f",
                        r.rule_name,
                        symbol,
                        r.label,
                        r.weight,
                    )
            except Exception:
                logger.exception(
                    "List-rule '%s' raised an unexpected error for %s — skipping",
                    rule_key,
                    symbol,
                )

        return results

    def aggregate(
        self,
        results: list[RuleResult],
        symbol: str = "UNKNOWN",
    ) -> TradingSignal | None:
        """Aggregate individual rule results into a single TradingSignal.

        Computes a direction-weighted average confidence:
        - Only results sharing the majority direction contribute positively.
        - Results in the opposite direction reduce the weighted score.
        - Emits a signal only when the final score >= SIGNAL_CONFIDENCE_THRESHOLD.

        Args:
            results: List of RuleResult items from evaluate().
            symbol: Trading pair symbol to embed in the resulting TradingSignal.

        Returns:
            A TradingSignal if confidence threshold is met, otherwise None.
        """
        if not results:
            logger.debug("aggregate: no rule results to aggregate")
            return None

        # Tally weighted votes per direction.
        direction_scores: dict[str, Decimal] = {"BUY": Decimal("0"), "SELL": Decimal("0")}
        direction_weights: dict[str, Decimal] = {"BUY": Decimal("0"), "SELL": Decimal("0")}
        triggered_rules: list[str] = []

        for result in results:
            # Resolve direction from either legacy or new-style API.
            dir_val = result.direction
            conf_val = result.confidence
            if not dir_val and result.label != RuleLabel.NEUTRAL:
                dir_val = "BUY" if result.label == RuleLabel.BULL else "SELL"
                conf_val = Decimal(str(result.weight))

            if dir_val not in direction_scores:
                logger.warning(
                    "aggregate: unknown direction '%s' in rule '%s' — skipping",
                    dir_val,
                    result.rule_name,
                )
                continue

            rule_key = _infer_rule_key(result.rule_name)
            weight = _RULE_WEIGHTS.get(rule_key, Decimal("0.25"))
            direction_scores[dir_val] += conf_val * weight
            direction_weights[dir_val] += weight
            triggered_rules.append(result.rule_name)

        # Pick the dominant direction.
        dominant = "BUY" if direction_scores["BUY"] >= direction_scores["SELL"] else "SELL"

        total_weight = direction_weights[dominant]
        if total_weight == Decimal("0"):
            logger.debug("aggregate: no weight accumulated for dominant direction")
            return None

        # Weighted average confidence for the dominant direction.
        raw_confidence = direction_scores[dominant] / total_weight

        # Penalise when opposing direction also has votes.
        opposing = "SELL" if dominant == "BUY" else "BUY"
        if direction_weights[opposing] > Decimal("0"):
            opposition_ratio = direction_scores[opposing] / (direction_scores[dominant] + direction_scores[opposing])
            raw_confidence = raw_confidence * (Decimal("1") - opposition_ratio * Decimal("0.5"))

        final_confidence = min(raw_confidence, Decimal("1.0"))

        if final_confidence < SIGNAL_CONFIDENCE_THRESHOLD:
            logger.info(
                "aggregate: confidence %.2f below threshold %.2f for direction %s — no signal",
                final_confidence,
                SIGNAL_CONFIDENCE_THRESHOLD,
                dominant,
            )
            return None

        # Determine primary timeframe from triggered rules (prefer 4h).
        primary_tf = _infer_primary_timeframe(results)

        signal = TradingSignal(
            symbol=symbol,
            signal_type=cast("Literal['BUY', 'SELL', 'HOLD']", dominant),
            confidence_score=final_confidence,
            timeframe_primary=primary_tf,
            timeframes_aligned={},
            rules_triggered=triggered_rules,
            leverage_suggested=None,
            margin_safety=None,
            fees_estimated=None,
            model_version=_MODEL_VERSION,
        )

        logger.info(
            "aggregate: emitting %s signal (confidence=%.2f, rules=%s)",
            dominant,
            final_confidence,
            triggered_rules,
        )
        return signal


# ------------------------------------------------------------------
# Private helpers
# ------------------------------------------------------------------


def _infer_rule_key(rule_name: str) -> str:
    """Map a rule_name back to its top-level config key for weight lookup.

    Handles both legacy names (``rsi_overbought_multi_tf``) and new-style names
    (``multi_tf_alignment``, ``convergence_rsi_bb``).

    Args:
        rule_name: Rule identifier string.

    Returns:
        One of "rsi", "bollinger", "harmonic", "trend".
    """
    # Direct prefix match against known weight keys
    for key in _RULE_WEIGHTS:
        if rule_name.startswith(key):
            return key

    # New-style rule names containing indicator keywords
    name_lower = rule_name.lower()
    if "bollinger" in name_lower or "bb" in name_lower or "squeeze" in name_lower:
        return "bollinger"
    if "harmonic" in name_lower:
        return "harmonic"
    if "trend" in name_lower:
        return "trend"
    if "rsi" in name_lower:
        return "rsi"

    # Multi-TF / convergence rules default to RSI weight
    if name_lower.startswith(("multi_tf", "convergence")):
        return "rsi"

    return "rsi"  # fallback


def _infer_primary_timeframe(results: list[RuleResult]) -> str:
    """Pick the most significant timeframe from the triggered rule names.

    Preference order: 4h > 1D > 1h > 2h > 3h > 1W > 1M > unknown.

    Args:
        results: Aggregated rule results.

    Returns:
        Best-guess primary timeframe string.
    """
    preference = ["4h", "1D", "1h", "2h", "3h", "1W", "1M"]
    for tf in preference:
        for result in results:
            if tf in result.rule_name or tf in result.reason:
                return tf
    return "4h"  # sensible default for crypto rule engines
