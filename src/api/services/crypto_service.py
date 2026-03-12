"""Crypto data service — prices, indicators, market overview."""

from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.config import settings
from src.shared.models.orm import IndicatorOrm, OHLCVOrm

logger = logging.getLogger(__name__)


def list_tracked() -> list[dict[str, str]]:
    """Return the list of tracked symbols from config."""
    return [{"symbol": s, "name": ""} for s in settings.tracked_symbols]


async def get_prices(
    db: AsyncSession,
    symbol: str,
    timeframe: str = "1h",
    start: datetime | None = None,
    end: datetime | None = None,
    limit: int = 100,
    page: int = 1,
) -> tuple[list[OHLCVOrm], int]:
    """Query OHLCV records for a symbol with optional date range and pagination.

    Args:
        db: Active async database session.
        symbol: Trading-pair symbol (case-insensitive).
        timeframe: Candle interval, e.g. ``1h``.
        start: Inclusive lower bound for ``timestamp``.
        end: Inclusive upper bound for ``timestamp``.
        limit: Maximum number of records to return per page.
        page: 1-based page number.

    Returns:
        Tuple of (list of OHLCVOrm rows ordered descending by timestamp, total row count).
    """
    query = select(OHLCVOrm).where(
        OHLCVOrm.symbol == symbol.upper(),
        OHLCVOrm.timeframe == timeframe,
    )
    count_query = (
        select(func.count())
        .select_from(OHLCVOrm)
        .where(
            OHLCVOrm.symbol == symbol.upper(),
            OHLCVOrm.timeframe == timeframe,
        )
    )

    if start is not None:
        query = query.where(OHLCVOrm.timestamp >= start)
        count_query = count_query.where(OHLCVOrm.timestamp >= start)
    if end is not None:
        query = query.where(OHLCVOrm.timestamp <= end)
        count_query = count_query.where(OHLCVOrm.timestamp <= end)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    offset = (page - 1) * limit
    query = query.order_by(desc(OHLCVOrm.timestamp)).offset(offset).limit(limit)

    result = await db.execute(query)
    return list(result.scalars().all()), total


async def get_indicators(
    db: AsyncSession,
    symbol: str,
    timeframe: str = "1h",
    limit: int = 100,
    page: int = 1,
) -> tuple[list[IndicatorOrm], int]:
    """Query technical indicator records for a symbol with pagination.

    Args:
        db: Active async database session.
        symbol: Trading-pair symbol (case-insensitive).
        timeframe: Candle interval filter.
        limit: Maximum number of records per page.
        page: 1-based page number.

    Returns:
        Tuple of (list of IndicatorOrm rows ordered descending by timestamp, total row count).
    """
    base_where = [
        IndicatorOrm.symbol == symbol.upper(),
        IndicatorOrm.timeframe == timeframe,
    ]
    count_query = select(func.count()).select_from(IndicatorOrm).where(*base_where)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    offset = (page - 1) * limit
    query = select(IndicatorOrm).where(*base_where).order_by(desc(IndicatorOrm.timestamp)).offset(offset).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all()), total


async def get_latest(
    db: AsyncSession,
    symbol: str,
    timeframe: str = "1h",
) -> dict[str, object]:
    """Return the most recent OHLCV candle and indicator row for a symbol.

    Args:
        db: Active async database session.
        symbol: Trading-pair symbol (case-insensitive).
        timeframe: Candle interval to filter by.

    Returns:
        Dict with keys ``symbol`` (str), ``ohlcv`` (OHLCVOrm | None),
        and ``indicators`` (IndicatorOrm | None).
    """
    upper_symbol = symbol.upper()
    ohlcv_result = await db.execute(
        select(OHLCVOrm)
        .where(OHLCVOrm.symbol == upper_symbol, OHLCVOrm.timeframe == timeframe)
        .order_by(desc(OHLCVOrm.timestamp))
        .limit(1)
    )
    ohlcv = ohlcv_result.scalar_one_or_none()

    indicator_result = await db.execute(
        select(IndicatorOrm)
        .where(IndicatorOrm.symbol == upper_symbol, IndicatorOrm.timeframe == timeframe)
        .order_by(desc(IndicatorOrm.timestamp))
        .limit(1)
    )
    indicator = indicator_result.scalar_one_or_none()

    return {"symbol": upper_symbol, "ohlcv": ohlcv, "indicators": indicator}


async def get_market_overview(db: AsyncSession) -> dict[str, object]:
    """Return market-wide overview: top gainers, losers, and heatmap data.

    Uses a single SQL window query (ROW_NUMBER) to avoid N+1 queries across
    all tracked symbols.

    Args:
        db: Active async database session.

    Returns:
        Dict with keys ``total_symbols``, ``total_market_cap``,
        ``btc_dominance``, ``fear_greed``, ``top_gainers``,
        ``top_losers``, and ``heatmap``.
    """
    symbols = settings.tracked_symbols
    gainers: list[dict] = []
    losers: list[dict] = []

    # Single query: fetch the 2 most recent rows per symbol using ROW_NUMBER()
    ranked = (
        select(
            OHLCVOrm.symbol,
            OHLCVOrm.price_close,
            OHLCVOrm.timestamp,
            func.row_number().over(partition_by=OHLCVOrm.symbol, order_by=desc(OHLCVOrm.timestamp)).label("rn"),
        )
        .where(OHLCVOrm.symbol.in_(symbols))
        .subquery()
    )
    result = await db.execute(
        select(ranked.c.symbol, ranked.c.price_close, ranked.c.rn)
        .where(ranked.c.rn <= 2)
        .order_by(ranked.c.symbol, ranked.c.rn)
    )
    rows = result.all()

    # Group by symbol: rn=1 is latest, rn=2 is previous
    per_symbol: dict[str, dict[int, float]] = {}
    for row in rows:
        sym, price, rn = str(row[0]), float(row[1]), int(row[2])
        per_symbol.setdefault(sym, {})[rn] = price

    for sym, prices in per_symbol.items():
        if 1 in prices and 2 in prices and prices[2] > 0:
            change_pct = (prices[1] - prices[2]) / prices[2] * 100
            entry = {
                "symbol": sym,
                "price": prices[1],
                "change_pct": round(change_pct, 2),
            }
            if change_pct >= 0:
                gainers.append(entry)
            else:
                losers.append(entry)

    gainers.sort(key=lambda x: x["change_pct"], reverse=True)
    losers.sort(key=lambda x: x["change_pct"])

    # Build heatmap data from gainers + losers
    heatmap = [{"symbol": e["symbol"], "change_pct": e["change_pct"]} for e in gainers + losers]

    # Fetch Fear & Greed value from pseudo-OHLCV record
    fg_result = await db.execute(
        select(OHLCVOrm.price_close)
        .where(OHLCVOrm.symbol == "FEAR_GREED")
        .order_by(desc(OHLCVOrm.timestamp))
        .limit(1)
    )
    fg_row = fg_result.scalar_one_or_none()
    fear_greed = int(fg_row) if fg_row is not None else None

    # Fetch market cap + BTC dominance from MARKET_DATA pseudo-OHLCV
    md_result = await db.execute(
        select(OHLCVOrm.volume_24h, OHLCVOrm.price_close)
        .where(OHLCVOrm.symbol == "MARKET_DATA")
        .order_by(desc(OHLCVOrm.timestamp))
        .limit(1)
    )
    md_row = md_result.one_or_none()
    total_market_cap = float(md_row[0]) if md_row is not None else None
    btc_dominance = round(float(md_row[1]), 2) if md_row is not None else None

    return {
        "total_symbols": len(symbols),
        "total_market_cap": total_market_cap,
        "btc_dominance": btc_dominance,
        "fear_greed": fear_greed,
        "top_gainers": gainers[:5],
        "top_losers": losers[:5],
        "heatmap": heatmap,
    }
