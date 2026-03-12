"""Abstract base class for all trading rules.

Every rule receives a dict of indicators keyed by timeframe and returns
a list of ``RuleResult`` values. Rules must be stateless pure functions
or lightweight stateless classes.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from src.ml.rules.models import RuleResult
from src.shared.models.crypto import IndicatorRecord


class BaseRule(ABC):
    """Abstract base for all rule evaluators.

    Subclasses implement ``evaluate`` as a pure function: given a snapshot of
    multi-timeframe indicators plus a config dict, return zero or more
    ``RuleResult`` objects.

    Args:
        config: Rule-specific configuration loaded from ``indicators.yaml``.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        self._config = config

    @property
    def config(self) -> dict[str, Any]:
        """Return the rule configuration dict."""
        return self._config

    @abstractmethod
    def evaluate(
        self,
        indicators: dict[str, IndicatorRecord | None],
    ) -> list[RuleResult]:
        """Evaluate this rule against the provided multi-TF indicator snapshot.

        Args:
            indicators: Mapping from timeframe string (e.g. ``"4h"``) to the
                latest ``IndicatorRecord`` for that timeframe, or ``None`` if no
                data is available.

        Returns:
            A (possibly empty) list of ``RuleResult`` objects describing what
            was found. An empty list means the rule did not trigger.
        """
        ...

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(config={self._config!r})"
