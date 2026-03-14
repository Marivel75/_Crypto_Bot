"""Signal service — active signals, detail, performance."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import case, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.api.services.crypto_service import _resolve_db_symbol
from src.shared.exceptions import NotFoundError
from src.shared.models.orm import SignalOutcomeOrm, TradingSignalOrm

logger = logging.getLogger(__name__)


async def get_active(db: AsyncSession) -> list[TradingSignalOrm]:
    """Return all trading signals created within the last 24 hours.

    Args:
        db: Active async database session.

    Returns:
        List of TradingSignalOrm rows ordered by creation time descending.
    """
    cutoff = datetime.now(tz=UTC) - timedelta(hours=24)
    result = await db.execute(
        select(TradingSignalOrm)
        .options(joinedload(TradingSignalOrm.outcome))
        .where(TradingSignalOrm.created_at >= cutoff)
        .order_by(desc(TradingSignalOrm.created_at))
    )
    return list(result.unique().scalars().all())


async def get_by_symbol(
    db: AsyncSession,
    symbol: str,
    timeframe: str | None = None,
    limit: int = 50,
    page: int = 1,
) -> tuple[list[TradingSignalOrm], int]:
    """Return trading signals for a specific symbol with optional timeframe filter.

    Args:
        db: Active async database session.
        symbol: Trading-pair symbol (case-insensitive).
        timeframe: Optional primary timeframe filter.
        limit: Maximum number of records per page.
        page: 1-based page number.

    Returns:
        Tuple of (list of TradingSignalOrm rows, total matching row count).
    """
    conditions = [TradingSignalOrm.symbol == _resolve_db_symbol(symbol)]
    if timeframe is not None:
        conditions.append(TradingSignalOrm.timeframe_primary == timeframe)

    count_query = select(func.count()).select_from(TradingSignalOrm).where(*conditions)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    offset = (page - 1) * limit
    query = (
        select(TradingSignalOrm)
        .options(joinedload(TradingSignalOrm.outcome))
        .where(*conditions)
        .order_by(desc(TradingSignalOrm.created_at))
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(query)
    return list(result.unique().scalars().all()), total


async def get_detail(
    db: AsyncSession,
    signal_id: str,
) -> dict[str, object]:
    """Return a single signal with its eagerly-loaded outcome.

    Args:
        db: Active async database session.
        signal_id: UUID string of the target signal.

    Returns:
        Dict with keys ``signal`` (TradingSignalOrm) and
        ``outcome`` (SignalOutcomeOrm | None).

    Raises:
        NotFoundError: If no signal with the given ID exists.
    """
    result = await db.execute(
        select(TradingSignalOrm).options(joinedload(TradingSignalOrm.outcome)).where(TradingSignalOrm.id == signal_id)
    )
    signal = result.unique().scalar_one_or_none()
    if signal is None:
        raise NotFoundError(f"Signal {signal_id} not found")
    return {"signal": signal, "outcome": signal.outcome}


async def get_performance(db: AsyncSession) -> dict[str, object]:
    """Return aggregate signal performance statistics in a single query.

    Uses a LEFT OUTER JOIN between signals and outcomes to compute all
    metrics in one database round-trip.

    Args:
        db: Active async database session.

    Returns:
        Dict with keys ``total_signals``, ``evaluated_signals``,
        ``correct_signals``, ``win_rate`` (float | None), and
        ``total_pnl`` (float | None).
    """
    stmt = (
        select(
            func.count(TradingSignalOrm.id).label("total"),
            func.count(SignalOutcomeOrm.id).label("evaluated"),
            func.count(case((SignalOutcomeOrm.was_correct.is_(True), 1))).label("correct"),
            func.sum(
                case(
                    (SignalOutcomeOrm.pnl_simulated.isnot(None), SignalOutcomeOrm.pnl_simulated),
                    else_=0,
                )
            ).label("pnl"),
        )
        .select_from(TradingSignalOrm)
        .outerjoin(SignalOutcomeOrm, TradingSignalOrm.id == SignalOutcomeOrm.signal_id)
    )
    result = await db.execute(stmt)
    row = result.one()

    total_signals = int(row.total or 0)
    evaluated_signals = int(row.evaluated or 0)
    correct_signals = int(row.correct or 0)

    win_rate = None
    if evaluated_signals > 0:
        win_rate = round(correct_signals / evaluated_signals * 100, 2)

    total_pnl_raw = row.pnl
    total_pnl = round(float(total_pnl_raw), 4) if total_pnl_raw is not None and total_pnl_raw != 0 else None

    return {
        "total_signals": total_signals,
        "evaluated_signals": evaluated_signals,
        "correct_signals": correct_signals,
        "win_rate": win_rate,
        "total_pnl": total_pnl,
    }
