"""Abstract repository interfaces for the ML module.

Business logic depends on these interfaces — never on concrete DB drivers.
Tests inject ``AsyncMock`` implementations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from src.shared.models.crypto import IndicatorRecord, NewsArticle, OHLCVRecord
from src.shared.models.signal import TradingSignal


class OHLCVRepository(ABC):
    """Read-only access to OHLCV candle data."""

    @abstractmethod
    async def find_by_symbol(
        self,
        symbol: str,
        timeframe: str,
        *,
        limit: int = 500,
        since: datetime | None = None,
    ) -> list[OHLCVRecord]: ...

    @abstractmethod
    async def get_latest(self, symbol: str, timeframe: str) -> OHLCVRecord | None: ...


class IndicatorRepository(ABC):
    """Read-only access to pre-computed technical indicators."""

    @abstractmethod
    async def find_by_symbol(
        self,
        symbol: str,
        timeframe: str,
        *,
        limit: int = 500,
        since: datetime | None = None,
    ) -> list[IndicatorRecord]: ...

    @abstractmethod
    async def get_latest(self, symbol: str, timeframe: str) -> IndicatorRecord | None: ...

    @abstractmethod
    async def get_multi_timeframe(self, symbol: str, timeframes: list[str]) -> dict[str, IndicatorRecord | None]: ...


class NewsRepository(ABC):
    """Read-only access to collected news articles."""

    @abstractmethod
    async def find_recent(
        self,
        *,
        symbol: str | None = None,
        limit: int = 50,
        since: datetime | None = None,
    ) -> list[NewsArticle]: ...


class SignalRepository(ABC):
    """Write access for generated trading signals."""

    @abstractmethod
    async def save(self, signal: TradingSignal) -> None: ...

    @abstractmethod
    async def bulk_save(self, signals: list[TradingSignal]) -> int: ...

    @abstractmethod
    async def find_recent(self, symbol: str, *, limit: int = 20) -> list[TradingSignal]: ...
