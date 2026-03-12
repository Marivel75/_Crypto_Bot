"""Concrete TimescaleDB repository implementations using SQLAlchemy 2.0 async."""

from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from typing import Literal, cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.ml.repositories.base import (
    IndicatorRepository,
    NewsRepository,
    OHLCVRepository,
    SignalRepository,
)
from src.shared.models.crypto import IndicatorRecord, NewsArticle, OHLCVRecord
from src.shared.models.orm import (
    IndicatorOrm,
    NewsArticleOrm,
    OHLCVOrm,
    TradingSignalOrm,
)
from src.shared.models.signal import TradingSignal

logger = logging.getLogger(__name__)


def _orm_to_ohlcv(row: OHLCVOrm) -> OHLCVRecord:
    """Map an OHLCVOrm row to an OHLCVRecord domain model.

    Args:
        row: SQLAlchemy ORM instance from the ``crypto_prices`` table.

    Returns:
        Corresponding :class:`OHLCVRecord` with Decimal price fields.
    """
    return OHLCVRecord(
        symbol=str(row.symbol),
        price_open=Decimal(str(row.price_open)),
        price_high=Decimal(str(row.price_high)),
        price_low=Decimal(str(row.price_low)),
        price_close=Decimal(str(row.price_close)),
        volume_24h=Decimal(str(row.volume_24h)),
        market_cap=Decimal(str(row.market_cap)) if row.market_cap else None,
        timestamp=row.timestamp,  # type: ignore[arg-type]
        source=str(row.source),
        timeframe=str(row.timeframe),
    )


def _orm_to_indicator(row: IndicatorOrm) -> IndicatorRecord:
    """Map an IndicatorOrm row to an IndicatorRecord domain model.

    Args:
        row: SQLAlchemy ORM instance from the ``indicators`` table.

    Returns:
        Corresponding :class:`IndicatorRecord` with nullable Decimal fields.
    """
    return IndicatorRecord(
        symbol=str(row.symbol),
        timeframe=str(row.timeframe),
        timestamp=row.timestamp,  # type: ignore[arg-type]
        rsi=Decimal(str(row.rsi)) if row.rsi is not None else None,
        bollinger_upper=Decimal(str(row.bollinger_upper)) if row.bollinger_upper is not None else None,
        bollinger_middle=Decimal(str(row.bollinger_middle)) if row.bollinger_middle is not None else None,
        bollinger_lower=Decimal(str(row.bollinger_lower)) if row.bollinger_lower is not None else None,
        price_vs_bollinger=Decimal(str(row.price_vs_bollinger)) if row.price_vs_bollinger is not None else None,
        harmonic_pattern=str(row.harmonic_pattern) if row.harmonic_pattern else None,
        trend_slope=Decimal(str(row.trend_slope)) if row.trend_slope is not None else None,
        trend_type=str(row.trend_type) if row.trend_type else None,
        metadata=dict(row.metadata) if row.metadata else {},  # type: ignore[call-overload]
    )


def _orm_to_news(row: NewsArticleOrm) -> NewsArticle:
    """Map a NewsArticleOrm row to a NewsArticle domain model.

    Args:
        row: SQLAlchemy ORM instance from the ``news_articles`` table.

    Returns:
        Corresponding :class:`NewsArticle` with nullable Decimal fields.
    """
    return NewsArticle(
        title=str(row.title),
        content=str(row.content) if row.content else None,
        source=str(row.source),
        url=str(row.url),
        published_at=row.published_at,  # type: ignore[arg-type]
        sentiment_score=Decimal(str(row.sentiment_score)) if row.sentiment_score is not None else None,
        keywords=list(row.keywords) if row.keywords else [],
        reliability_score=Decimal(str(row.reliability_score)) if row.reliability_score is not None else None,
    )


class TimescaleOHLCVRepository(OHLCVRepository):
    """TimescaleDB-backed OHLCV repository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_symbol(
        self,
        symbol: str,
        timeframe: str,
        *,
        limit: int = 500,
        since: datetime | None = None,
    ) -> list[OHLCVRecord]:
        """Fetch OHLCV records for a symbol/timeframe, newest first.

        Args:
            symbol: Trading pair, e.g. ``"BTCUSDT"``.
            timeframe: Candle interval, e.g. ``"4h"``.
            limit: Maximum rows to return. Default 500.
            since: Optional lower bound on timestamp (inclusive).

        Returns:
            List of :class:`OHLCVRecord` instances ordered newest-first.
        """
        base = select(OHLCVOrm).where(OHLCVOrm.symbol == symbol, OHLCVOrm.timeframe == timeframe)
        if since is not None:
            base = base.where(OHLCVOrm.timestamp >= since)
        stmt = base.order_by(OHLCVOrm.timestamp.desc()).limit(limit)
        result = await self._session.execute(stmt)
        return [_orm_to_ohlcv(row) for row in result.scalars().all()]

    async def get_latest(self, symbol: str, timeframe: str) -> OHLCVRecord | None:
        """Return the single most recent OHLCV record, or None if absent.

        Args:
            symbol: Trading pair, e.g. ``"BTCUSDT"``.
            timeframe: Candle interval, e.g. ``"4h"``.

        Returns:
            Most recent :class:`OHLCVRecord`, or ``None``.
        """
        stmt = (
            select(OHLCVOrm)
            .where(OHLCVOrm.symbol == symbol, OHLCVOrm.timeframe == timeframe)
            .order_by(OHLCVOrm.timestamp.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        row = result.scalars().first()
        return _orm_to_ohlcv(row) if row else None


class TimescaleIndicatorRepository(IndicatorRepository):
    """TimescaleDB-backed indicator repository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_symbol(
        self,
        symbol: str,
        timeframe: str,
        *,
        limit: int = 500,
        since: datetime | None = None,
    ) -> list[IndicatorRecord]:
        """Fetch indicator records for a symbol/timeframe, newest first.

        Args:
            symbol: Trading pair, e.g. ``"BTCUSDT"``.
            timeframe: Candle interval, e.g. ``"4h"``.
            limit: Maximum rows to return. Default 500.
            since: Optional lower bound on timestamp (inclusive).

        Returns:
            List of :class:`IndicatorRecord` instances ordered newest-first.
        """
        base = select(IndicatorOrm).where(IndicatorOrm.symbol == symbol, IndicatorOrm.timeframe == timeframe)
        if since is not None:
            base = base.where(IndicatorOrm.timestamp >= since)
        stmt = base.order_by(IndicatorOrm.timestamp.desc()).limit(limit)
        result = await self._session.execute(stmt)
        return [_orm_to_indicator(row) for row in result.scalars().all()]

    async def get_latest(self, symbol: str, timeframe: str) -> IndicatorRecord | None:
        """Return the single most recent indicator record, or None if absent.

        Args:
            symbol: Trading pair, e.g. ``"BTCUSDT"``.
            timeframe: Candle interval, e.g. ``"4h"``.

        Returns:
            Most recent :class:`IndicatorRecord`, or ``None``.
        """
        stmt = (
            select(IndicatorOrm)
            .where(IndicatorOrm.symbol == symbol, IndicatorOrm.timeframe == timeframe)
            .order_by(IndicatorOrm.timestamp.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        row = result.scalars().first()
        return _orm_to_indicator(row) if row else None

    async def get_multi_timeframe(self, symbol: str, timeframes: list[str]) -> dict[str, IndicatorRecord | None]:
        """Fetch the latest indicator snapshot for each requested timeframe.

        Args:
            symbol: Trading pair, e.g. ``"BTCUSDT"``.
            timeframes: List of timeframe strings to query.

        Returns:
            Dict mapping each timeframe to its latest :class:`IndicatorRecord`
            (or ``None`` if no data exists for that timeframe).
        """
        if not timeframes:
            return {}

        # Single query using DISTINCT ON to get latest per timeframe
        stmt = (
            select(IndicatorOrm)
            .where(IndicatorOrm.symbol == symbol, IndicatorOrm.timeframe.in_(timeframes))
            .distinct(IndicatorOrm.timeframe)
            .order_by(IndicatorOrm.timeframe, IndicatorOrm.timestamp.desc())
        )
        result = await self._session.execute(stmt)
        rows_by_tf = {str(row.timeframe): _orm_to_indicator(row) for row in result.scalars().all()}
        return {tf: rows_by_tf.get(tf) for tf in timeframes}


class TimescaleNewsRepository(NewsRepository):
    """TimescaleDB-backed news repository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_recent(
        self,
        *,
        symbol: str | None = None,
        limit: int = 50,
        since: datetime | None = None,
    ) -> list[NewsArticle]:
        """Fetch recent news articles, optionally filtered by symbol mention.

        Args:
            symbol: Optional symbol to filter articles by title keyword match.
            limit: Maximum number of articles to return. Default 50.
            since: Optional lower bound on ``published_at`` (inclusive).

        Returns:
            List of :class:`NewsArticle` instances ordered newest-first.
        """
        stmt = select(NewsArticleOrm).order_by(NewsArticleOrm.published_at.desc()).limit(limit)
        if since is not None:
            stmt = stmt.where(NewsArticleOrm.published_at >= since)
        # Symbol filtering uses keyword match in title
        if symbol is not None:
            stmt = stmt.where(NewsArticleOrm.title.ilike(f"%{symbol}%"))
        result = await self._session.execute(stmt)
        return [_orm_to_news(row) for row in result.scalars().all()]


class TimescaleSignalRepository(SignalRepository):
    """TimescaleDB-backed signal repository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, signal: TradingSignal) -> None:
        """Persist a single trading signal and flush to the session.

        Args:
            signal: :class:`TradingSignal` to write to ``trading_signals``.
        """
        orm = TradingSignalOrm(
            symbol=signal.symbol,
            signal_type=signal.signal_type,
            confidence_score=float(signal.confidence_score),
            timeframe_primary=signal.timeframe_primary,
            timeframes_aligned=signal.timeframes_aligned,
            rules_triggered=signal.rules_triggered,
            leverage_suggested=signal.leverage_suggested,
            margin_safety=float(signal.margin_safety) if signal.margin_safety else None,
            fees_estimated=float(signal.fees_estimated) if signal.fees_estimated else None,
            model_version=signal.model_version,
        )
        self._session.add(orm)
        await self._session.flush()
        logger.info(
            "Saved signal for %s: %s (confidence=%.2f)", signal.symbol, signal.signal_type, signal.confidence_score
        )

    async def bulk_save(self, signals: list[TradingSignal]) -> int:
        """Persist multiple trading signals sequentially.

        Args:
            signals: List of :class:`TradingSignal` instances to persist.

        Returns:
            Number of signals successfully persisted.
        """
        for signal in signals:
            orm = TradingSignalOrm(
                symbol=signal.symbol,
                signal_type=signal.signal_type,
                confidence_score=float(signal.confidence_score),
                timeframe_primary=signal.timeframe_primary,
                timeframes_aligned=signal.timeframes_aligned,
                rules_triggered=signal.rules_triggered,
                leverage_suggested=signal.leverage_suggested,
                margin_safety=float(signal.margin_safety) if signal.margin_safety else None,
                fees_estimated=float(signal.fees_estimated) if signal.fees_estimated else None,
                model_version=signal.model_version,
            )
            self._session.add(orm)
        await self._session.flush()
        logger.info("Bulk saved %d signals", len(signals))
        return len(signals)

    async def find_recent(self, symbol: str, *, limit: int = 20) -> list[TradingSignal]:
        """Fetch recent trading signals for a symbol, newest first.

        Args:
            symbol: Trading pair to filter by, e.g. ``"BTCUSDT"``.
            limit: Maximum number of signals to return. Default 20.

        Returns:
            List of :class:`TradingSignal` instances ordered newest-first.
        """
        stmt = (
            select(TradingSignalOrm)
            .where(TradingSignalOrm.symbol == symbol)
            .order_by(TradingSignalOrm.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [
            TradingSignal(
                symbol=str(row.symbol),
                signal_type=cast("Literal['BUY', 'SELL', 'HOLD']", str(row.signal_type)),
                confidence_score=Decimal(str(row.confidence_score)),
                timeframe_primary=str(row.timeframe_primary),
                timeframes_aligned=dict(row.timeframes_aligned) if row.timeframes_aligned else {},
                rules_triggered=list(row.rules_triggered) if row.rules_triggered else [],
                leverage_suggested=int(row.leverage_suggested) if row.leverage_suggested else None,
                margin_safety=Decimal(str(row.margin_safety)) if row.margin_safety else None,
                fees_estimated=Decimal(str(row.fees_estimated)) if row.fees_estimated else None,
                model_version=str(row.model_version),
            )
            for row in result.scalars().all()
        ]
