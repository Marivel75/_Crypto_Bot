"""ML repositories — data access interfaces and implementations."""

from __future__ import annotations

from src.ml.repositories.base import (
    IndicatorRepository,
    NewsRepository,
    OHLCVRepository,
    SignalRepository,
)
from src.ml.repositories.timescale import (
    TimescaleIndicatorRepository,
    TimescaleNewsRepository,
    TimescaleOHLCVRepository,
    TimescaleSignalRepository,
)

__all__ = [
    "IndicatorRepository",
    "NewsRepository",
    "OHLCVRepository",
    "SignalRepository",
    "TimescaleIndicatorRepository",
    "TimescaleNewsRepository",
    "TimescaleOHLCVRepository",
    "TimescaleSignalRepository",
]
