"""Shared Pydantic models and ORM aliases used across all teams.

Import from this package to avoid deep relative imports in application code.
"""

from __future__ import annotations

from .crypto import IndicatorRecord, NewsArticle, OHLCVRecord
from .orm import (
    IndicatorOrm,
    NewsArticleOrm,
    OHLCVOrm,
    PortfolioEntryOrm,
    SignalOutcomeOrm,
    TradingSignalOrm,
    UserOrm,
    WatchlistEntryOrm,
)
from .signal import SignalOutcome, TradingSignal
from .user import UserCreate, UserRead

__all__ = [
    "OHLCVRecord",
    "IndicatorRecord",
    "NewsArticle",
    "TradingSignal",
    "SignalOutcome",
    "UserCreate",
    "UserRead",
    "UserOrm",
    "OHLCVOrm",
    "IndicatorOrm",
    "NewsArticleOrm",
    "TradingSignalOrm",
    "SignalOutcomeOrm",
    "PortfolioEntryOrm",
    "WatchlistEntryOrm",
]
