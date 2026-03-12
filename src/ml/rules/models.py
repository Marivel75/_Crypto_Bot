"""Data models for the rules engine.

All models are frozen dataclasses — immutable value objects.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from decimal import Decimal


class RuleLabel(enum.Enum):
    """Directional label used by multi-TF and convergence rules."""

    BULL = "BULL"
    BEAR = "BEAR"
    NEUTRAL = "NEUTRAL"


@dataclass(frozen=True, slots=True)
class RuleResult:
    """Output of a single rule evaluation.

    Legacy rules populate ``direction`` / ``confidence`` / ``reason``.
    Newer rules (convergence, multi-TF) populate ``label`` / ``weight`` / ``detail``.

    Attributes:
        rule_name: Unique identifier (e.g. ``rsi_overbought_multi_tf``).
        direction: Suggested direction (``BUY`` or ``SELL``).  Legacy API.
        confidence: Confidence score in [0, 1] as Decimal.  Legacy API.
        reason: Human-readable explanation.  Legacy API.
        label: Directional label (BULL/BEAR/NEUTRAL).  New API.
        weight: Signal weight in [0, 1].  New API.
        detail: Human-readable detail string.  New API.
    """

    rule_name: str
    direction: str = ""
    confidence: Decimal = Decimal("0")
    reason: str = ""
    label: RuleLabel = field(default=RuleLabel.NEUTRAL)
    weight: float = 0.0
    detail: str = ""


@dataclass(frozen=True, slots=True)
class EngineOutput:
    """Aggregated output of the full rules engine.

    Attributes:
        direction: Final direction (``BUY`` / ``SELL`` / ``HOLD``).
        confidence: Aggregated confidence score in [0, 1].
        results: Individual rule results that contributed.
        rules_triggered: Names of rules that fired.
    """

    direction: str
    confidence: Decimal
    results: tuple[RuleResult, ...]
    rules_triggered: tuple[str, ...]
