"""TimescaleDB loader — bulk insert OHLCV, indicators, and news data."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from src.shared.database import async_engine, async_session_factory
from src.shared.models.crypto import IndicatorRecord, NewsArticle, OHLCVRecord

logger = logging.getLogger(__name__)


def get_engine() -> AsyncEngine:
    """Return the shared async engine singleton."""
    return async_engine


async def insert_ohlcv_batch(records: list[OHLCVRecord]) -> int:
    """Insert OHLCV records with ON CONFLICT DO NOTHING on (symbol, timeframe, timestamp).

    Returns number of rows inserted.
    """
    if not records:
        return 0

    params = [
        {
            "symbol": record.symbol,
            "timeframe": record.timeframe,
            "timestamp": record.timestamp,
            "price_open": float(record.price_open),
            "price_high": float(record.price_high),
            "price_low": float(record.price_low),
            "price_close": float(record.price_close),
            "volume_24h": float(record.volume_24h),
            "market_cap": float(record.market_cap) if record.market_cap else None,
            "source": record.source,
        }
        for record in records
    ]

    stmt = text("""
        INSERT INTO crypto_prices
            (symbol, timeframe, timestamp, price_open, price_high,
             price_low, price_close, volume_24h, market_cap, source)
        VALUES
            (:symbol, :timeframe, :timestamp, :price_open, :price_high,
             :price_low, :price_close, :volume_24h, :market_cap, :source)
        ON CONFLICT (symbol, timeframe, timestamp) DO NOTHING
    """)

    async with async_session_factory() as session:
        try:
            result = await session.execute(stmt, params)
            inserted = result.rowcount  # type: ignore[attr-defined]
            await session.commit()
        except Exception:
            logger.exception("OHLCV batch insert failed for %d records", len(records))
            raise
        logger.info("OHLCV batch insert: %d/%d rows inserted", inserted, len(records))
        return inserted


async def insert_indicators_batch(records: list[IndicatorRecord]) -> int:
    """Upsert indicator records on (symbol, timeframe, timestamp).

    Returns number of rows affected.
    """
    if not records:
        return 0

    params = [
        {
            "symbol": record.symbol,
            "timeframe": record.timeframe,
            "timestamp": record.timestamp,
            "rsi": float(record.rsi) if record.rsi is not None else None,
            "bollinger_upper": float(record.bollinger_upper) if record.bollinger_upper is not None else None,
            "bollinger_middle": float(record.bollinger_middle) if record.bollinger_middle is not None else None,
            "bollinger_lower": float(record.bollinger_lower) if record.bollinger_lower is not None else None,
            "price_vs_bollinger": float(record.price_vs_bollinger) if record.price_vs_bollinger is not None else None,
            "harmonic_pattern": record.harmonic_pattern,
            "trend_slope": float(record.trend_slope) if record.trend_slope is not None else None,
            "trend_type": record.trend_type,
            "metadata": json.dumps(record.metadata if record.metadata else {}),
        }
        for record in records
    ]

    stmt = text("""
        INSERT INTO indicators
            (symbol, timeframe, timestamp, rsi, bollinger_upper,
             bollinger_middle, bollinger_lower, price_vs_bollinger,
             harmonic_pattern, trend_slope, trend_type, metadata)
        VALUES
            (:symbol, :timeframe, :timestamp, :rsi, :bollinger_upper,
             :bollinger_middle, :bollinger_lower, :price_vs_bollinger,
             :harmonic_pattern, :trend_slope, :trend_type, :metadata)
        ON CONFLICT (symbol, timeframe, timestamp)
        DO UPDATE SET
            rsi = EXCLUDED.rsi,
            bollinger_upper = EXCLUDED.bollinger_upper,
            bollinger_middle = EXCLUDED.bollinger_middle,
            bollinger_lower = EXCLUDED.bollinger_lower,
            price_vs_bollinger = EXCLUDED.price_vs_bollinger,
            harmonic_pattern = EXCLUDED.harmonic_pattern,
            trend_slope = EXCLUDED.trend_slope,
            trend_type = EXCLUDED.trend_type,
            metadata = EXCLUDED.metadata
    """)

    async with async_session_factory() as session:
        try:
            result = await session.execute(stmt, params)
            affected = result.rowcount  # type: ignore[attr-defined]
            await session.commit()
        except Exception:
            logger.exception("Indicators batch upsert failed for %d records", len(records))
            raise
        logger.info("Indicators batch upsert: %d/%d rows affected", affected, len(records))
        return affected


async def insert_news_batch(articles: list[NewsArticle]) -> int:
    """Insert news articles with ON CONFLICT (url) DO NOTHING.

    Returns number of rows inserted.
    """
    if not articles:
        return 0

    params = [
        {
            "title": article.title,
            "content": article.content,
            "source": article.source,
            "url": article.url,
            "published_at": article.published_at,
            "sentiment_score": float(article.sentiment_score) if article.sentiment_score is not None else None,
            "keywords": json.dumps(list(article.keywords)) if article.keywords else "[]",
            "reliability_score": float(article.reliability_score) if article.reliability_score is not None else None,
        }
        for article in articles
    ]

    stmt = text("""
        INSERT INTO news_articles
            (title, content, source, url, published_at,
             sentiment_score, keywords, reliability_score)
        VALUES
            (:title, :content, :source, :url, :published_at,
             :sentiment_score, :keywords::jsonb, :reliability_score)
        ON CONFLICT (url) DO NOTHING
    """)

    async with async_session_factory() as session:
        try:
            result = await session.execute(stmt, params)
            inserted = result.rowcount  # type: ignore[attr-defined]
            await session.commit()
        except Exception:
            logger.exception("News batch insert failed for %d articles", len(articles))
            raise
        logger.info("News batch insert: %d/%d articles inserted", inserted, len(articles))
        return inserted


async def fetch_ohlcv_for_indicators(
    symbol: str,
    timeframe: str,
    limit: int = 500,
) -> list[dict[str, object]]:
    """Fetch recent OHLCV rows for indicator computation.

    Returns rows as list of dicts with keys: timestamp, price_open, price_high,
    price_low, price_close, volume_24h.
    """
    async with async_session_factory() as session:
        result = await session.execute(
            text("""
                SELECT timestamp, price_open, price_high, price_low,
                       price_close, volume_24h
                FROM crypto_prices
                WHERE symbol = :symbol AND timeframe = :timeframe
                ORDER BY timestamp DESC
                LIMIT :limit
            """),
            {"symbol": symbol, "timeframe": timeframe, "limit": limit},
        )
        rows = result.mappings().all()
        # Reverse to chronological order (oldest first)
        return [dict(row) for row in reversed(rows)]


async def detect_gaps(
    symbol: str,
    timeframe: str,
    expected_interval_seconds: int,
    since: datetime,
) -> list[datetime]:
    """Detect missing timestamps in an OHLCV series.

    Returns list of expected timestamps that are missing.
    """
    async with async_session_factory() as session:
        result = await session.execute(
            text("""
                SELECT timestamp
                FROM crypto_prices
                WHERE symbol = :symbol
                  AND timeframe = :timeframe
                  AND timestamp >= :since
                ORDER BY timestamp ASC
            """),
            {"symbol": symbol, "timeframe": timeframe, "since": since},
        )
        timestamps = [row[0] for row in result.fetchall()]

    if len(timestamps) < 2:
        return []

    from datetime import timedelta

    interval = timedelta(seconds=expected_interval_seconds)
    gaps: list[datetime] = []
    for i in range(1, len(timestamps)):
        expected = timestamps[i - 1] + interval
        while expected < timestamps[i]:
            gaps.append(expected)
            expected += interval

    if gaps:
        logger.warning(
            "Detected %d gaps for %s/%s since %s",
            len(gaps),
            symbol,
            timeframe,
            since,
        )
    return gaps


async def fetch_unevaluated_signals() -> list[dict[str, object]]:
    """Fetch trading signals that have no outcome record yet.

    Only returns signals older than 1 hour (so at least price_after_1h
    can be computed).
    """
    from datetime import timedelta

    cutoff = datetime.now(tz=UTC) - timedelta(hours=1)

    async with async_session_factory() as session:
        result = await session.execute(
            text("""
                SELECT ts.id, ts.symbol, ts.signal_type, ts.created_at
                FROM trading_signals ts
                LEFT JOIN signal_outcomes so ON so.signal_id = ts.id
                WHERE so.id IS NULL
                  AND ts.created_at <= :cutoff
                ORDER BY ts.created_at ASC
                LIMIT 100
            """),
            {"cutoff": cutoff},
        )
        return [dict(row) for row in result.mappings().all()]


async def fetch_price_at_time(
    symbol: str,
    target_time: datetime,
) -> float | None:
    """Fetch the closest price_close for a symbol near a target time."""
    async with async_session_factory() as session:
        result = await session.execute(
            text("""
                SELECT price_close
                FROM crypto_prices
                WHERE symbol = :symbol
                  AND timeframe IN ('1m', '5m', '1h')
                ORDER BY ABS(EXTRACT(EPOCH FROM timestamp - :target_time))
                LIMIT 1
            """),
            {"symbol": symbol, "target_time": target_time},
        )
        row = result.scalar_one_or_none()
        return float(row) if row is not None else None


async def insert_signal_outcome(
    signal_id: str,
    price_at_signal: float | None,
    price_after_1h: float | None,
    price_after_4h: float | None,
    price_after_1d: float | None,
    pnl_simulated: float | None,
    was_correct: bool | None,
) -> int:
    """Insert a signal outcome record."""
    stmt = text("""
        INSERT INTO signal_outcomes
            (id, signal_id, price_at_signal, price_after_1h,
             price_after_4h, price_after_1d, pnl_simulated, was_correct)
        SELECT
            gen_random_uuid(), :signal_id, :price_at_signal, :price_after_1h,
            :price_after_4h, :price_after_1d, :pnl_simulated, :was_correct
        WHERE NOT EXISTS (
            SELECT 1 FROM signal_outcomes WHERE signal_id = :signal_id
        )
    """)
    async with async_session_factory() as session:
        try:
            result = await session.execute(
                stmt,
                {
                    "signal_id": signal_id,
                    "price_at_signal": price_at_signal,
                    "price_after_1h": price_after_1h,
                    "price_after_4h": price_after_4h,
                    "price_after_1d": price_after_1d,
                    "pnl_simulated": pnl_simulated,
                    "was_correct": was_correct,
                },
            )
            await session.commit()
            return result.rowcount  # type: ignore[attr-defined]
        except Exception:
            logger.exception("Signal outcome insert failed for signal %s", signal_id)
            raise
