"""User data service — portfolio and watchlist CRUD."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import desc, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.exceptions import AuthorizationError, ConflictError, NotFoundError
from src.shared.models.orm import OHLCVOrm, PortfolioEntryOrm, WatchlistEntryOrm

logger = logging.getLogger(__name__)


# --- Portfolio ---


async def get_portfolio(
    db: AsyncSession,
    user_id: str,
) -> list[PortfolioEntryOrm]:
    """Return all portfolio positions belonging to a user.

    Args:
        db: Active async database session.
        user_id: UUID string of the authenticated user.

    Returns:
        List of PortfolioEntryOrm rows (unordered).
    """
    result = await db.execute(select(PortfolioEntryOrm).where(PortfolioEntryOrm.user_id == user_id))
    return list(result.scalars().all())


async def add_portfolio_entry(
    db: AsyncSession,
    user_id: str,
    symbol: str,
    quantity: float,
    entry_price: float,
    notes: str | None = None,
) -> PortfolioEntryOrm:
    """Create and persist a new portfolio position.

    The symbol is automatically uppercased before storage.

    Args:
        db: Active async database session.
        user_id: UUID string of the authenticated user.
        symbol: Trading-pair symbol (case-insensitive).
        quantity: Number of units held (must be > 0).
        entry_price: Price per unit at acquisition (must be > 0).
        notes: Optional free-text note.

    Returns:
        Newly created and refreshed PortfolioEntryOrm instance.

    Raises:
        ConflictError: If a database constraint violation occurs.
    """
    entry = PortfolioEntryOrm(
        user_id=user_id,
        symbol=symbol.upper(),
        quantity=quantity,
        entry_price=entry_price,
        notes=notes,
    )
    db.add(entry)
    try:
        await db.flush()
    except IntegrityError as exc:
        logger.warning("Failed to add portfolio entry due to constraint violation: %s", exc)
        raise ConflictError("Portfolio entry already exists or violates a constraint") from exc
    await db.refresh(entry)
    return entry


async def update_portfolio_entry(
    db: AsyncSession,
    user_id: str,
    entry_id: str,
    quantity: float | None = None,
    entry_price: float | None = None,
    notes: str | None = None,
) -> PortfolioEntryOrm:
    """Partially update a portfolio position after verifying ownership.

    Only non-None arguments are applied. ``updated_at`` is always refreshed.

    Args:
        db: Active async database session.
        user_id: UUID string of the requesting user (for ownership check).
        entry_id: UUID string of the portfolio entry to update.
        quantity: New quantity if provided.
        entry_price: New entry price if provided.
        notes: New note if provided.

    Returns:
        Updated and refreshed PortfolioEntryOrm instance.

    Raises:
        NotFoundError: If the entry does not exist.
        AuthorizationError: If the entry belongs to a different user.
    """
    result = await db.execute(select(PortfolioEntryOrm).where(PortfolioEntryOrm.id == entry_id))
    entry = result.scalar_one_or_none()
    if entry is None:
        raise NotFoundError(f"Portfolio entry {entry_id} not found")
    if str(entry.user_id) != user_id:
        raise AuthorizationError("You do not own this portfolio entry")

    if quantity is not None:
        entry.quantity = quantity  # type: ignore[assignment]
    if entry_price is not None:
        entry.entry_price = entry_price  # type: ignore[assignment]
    if notes is not None:
        entry.notes = notes  # type: ignore[assignment]
    entry.updated_at = datetime.now(tz=timezone.utc)  # type: ignore[assignment]

    await db.flush()
    await db.refresh(entry)
    return entry


async def delete_portfolio_entry(
    db: AsyncSession,
    user_id: str,
    entry_id: str,
) -> None:
    """Delete a portfolio position after verifying ownership.

    Args:
        db: Active async database session.
        user_id: UUID string of the requesting user.
        entry_id: UUID string of the portfolio entry to delete.

    Raises:
        NotFoundError: If the entry does not exist.
        AuthorizationError: If the entry belongs to a different user.
    """
    result = await db.execute(select(PortfolioEntryOrm).where(PortfolioEntryOrm.id == entry_id))
    entry = result.scalar_one_or_none()
    if entry is None:
        raise NotFoundError(f"Portfolio entry {entry_id} not found")
    if str(entry.user_id) != user_id:
        raise AuthorizationError("You do not own this portfolio entry")

    await db.delete(entry)
    await db.flush()


# --- Watchlist ---


async def get_watchlist(
    db: AsyncSession,
    user_id: str,
) -> list[WatchlistEntryOrm]:
    """Return all watchlist symbols for a user.

    Args:
        db: Active async database session.
        user_id: UUID string of the authenticated user.

    Returns:
        List of WatchlistEntryOrm rows.
    """
    result = await db.execute(select(WatchlistEntryOrm).where(WatchlistEntryOrm.user_id == user_id))
    return list(result.scalars().all())


async def add_watchlist_symbol(
    db: AsyncSession,
    user_id: str,
    symbol: str,
) -> WatchlistEntryOrm:
    """Add a symbol to the user's watchlist, preventing duplicates.

    Performs an explicit duplicate check before inserting. If a race
    condition triggers an IntegrityError at flush time, it is caught
    and re-raised as ConflictError.

    Args:
        db: Active async database session.
        user_id: UUID string of the authenticated user.
        symbol: Trading-pair symbol to add (case-insensitive).

    Returns:
        Newly created and refreshed WatchlistEntryOrm instance.

    Raises:
        ConflictError: If the symbol is already in the user's watchlist.
    """
    existing = await db.execute(
        select(WatchlistEntryOrm).where(
            WatchlistEntryOrm.user_id == user_id,
            WatchlistEntryOrm.symbol == symbol.upper(),
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise ConflictError(f"{symbol.upper()} is already in your watchlist")

    entry = WatchlistEntryOrm(user_id=user_id, symbol=symbol.upper())
    db.add(entry)
    try:
        await db.flush()
    except IntegrityError as exc:
        logger.warning("Failed to add watchlist symbol due to constraint violation: %s", exc)
        raise ConflictError(f"{symbol.upper()} is already in your watchlist") from exc
    await db.refresh(entry)
    return entry


async def remove_watchlist_symbol(
    db: AsyncSession,
    user_id: str,
    symbol: str,
) -> None:
    """Remove a symbol from the user's watchlist.

    Args:
        db: Active async database session.
        user_id: UUID string of the authenticated user.
        symbol: Trading-pair symbol to remove (case-insensitive).

    Raises:
        NotFoundError: If the symbol is not in the user's watchlist.
    """
    result = await db.execute(
        select(WatchlistEntryOrm).where(
            WatchlistEntryOrm.user_id == user_id,
            WatchlistEntryOrm.symbol == symbol.upper(),
        )
    )
    entry = result.scalar_one_or_none()
    if entry is None:
        raise NotFoundError(f"{symbol.upper()} not in your watchlist")

    await db.delete(entry)
    await db.flush()


async def get_portfolio_summary(
    db: AsyncSession,
    user_id: str,
) -> dict[str, object]:
    """Calculate aggregated portfolio statistics.

    Returns total number of entries, total value, cost basis, unrealized P&L,
    and percentage allocation by symbol.

    Args:
        db: Active async database session.
        user_id: UUID string of the authenticated user.

    Returns:
        Dict with keys: total_entries, total_value, total_cost, unrealized_pnl, allocation.
    """
    entries = await get_portfolio(db, user_id)

    total_cost = sum(float(e.quantity) * float(e.entry_price) for e in entries)
    total_entries = len(entries)
    allocation = {}

    for entry in entries:
        position_value = float(entry.quantity) * float(entry.entry_price)
        if total_cost > 0:
            allocation[entry.symbol] = round(position_value / total_cost * 100, 2)

    return {
        "total_entries": total_entries,
        "total_value": round(total_cost, 2) if total_cost > 0 else None,
        "total_cost": round(total_cost, 2) if total_cost > 0 else None,
        "unrealized_pnl": None,
        "allocation": allocation,
    }


async def get_portfolio_history(
    db: AsyncSession,
    user_id: str,
    start: datetime | None = None,
    end: datetime | None = None,
) -> dict[str, object]:
    """Return historical portfolio value snapshots.

    Currently returns an empty history as historical tracking is not yet
    implemented. When tracking tables are available, this will return
    daily portfolio value snapshots.

    Args:
        db: Active async database session.
        user_id: UUID string of the authenticated user.
        start: Optional start date (ISO 8601).
        end: Optional end date (ISO 8601).

    Returns:
        Dict with keys: symbol (None), history (list of snapshots).
    """
    return {"symbol": None, "history": []}


async def get_watchlist_prices(
    db: AsyncSession,
    user_id: str,
) -> list[dict[str, object]]:
    """Return current prices for all watchlist symbols.

    Fetches the latest OHLCV price record for each symbol in the user's watchlist.

    Args:
        db: Active async database session.
        user_id: UUID string of the authenticated user.

    Returns:
        List of dicts with keys: symbol, current_price, timestamp.
    """
    watchlist_entries = await get_watchlist(db, user_id)

    prices: list[dict[str, object]] = []
    for entry in watchlist_entries:
        result = await db.execute(
            select(OHLCVOrm).where(OHLCVOrm.symbol == entry.symbol).order_by(desc(OHLCVOrm.timestamp)).limit(1)
        )
        ohlcv = result.scalar_one_or_none()

        prices.append(
            {
                "symbol": entry.symbol,
                "current_price": float(ohlcv.price_close) if ohlcv else None,
                "timestamp": ohlcv.timestamp if ohlcv else None,
            }
        )

    return prices
