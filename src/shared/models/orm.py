"""ORM model re-exports with names expected by service layer.

This module provides stable import names used across src/api/services/.
The canonical ORM definitions live in src/shared/db_models.py.
"""

from __future__ import annotations

from src.shared.db_models import (
    Base,
    CryptoPriceOrm,
    IndicatorOrm,
    NewsArticleOrm,
    PortfolioOrm,
    SignalOutcomeOrm,
    TextMiningResultOrm,
    TradingSignalOrm,
    UserOrm,
    WatchlistOrm,
)

# Aliases expected by service layer
OHLCVOrm = CryptoPriceOrm
PortfolioEntryOrm = PortfolioOrm
WatchlistEntryOrm = WatchlistOrm

__all__ = [
    "Base",
    "UserOrm",
    "OHLCVOrm",
    "CryptoPriceOrm",
    "IndicatorOrm",
    "TradingSignalOrm",
    "SignalOutcomeOrm",
    "PortfolioOrm",
    "PortfolioEntryOrm",
    "WatchlistOrm",
    "WatchlistEntryOrm",
    "NewsArticleOrm",
    "TextMiningResultOrm",
]
