"""Watchlist router — add, list, remove symbols."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user, get_db
from src.api.schemas import (
    ApiResponse,
    WatchlistAddRequest,
    WatchlistEntryResponse,
    WatchlistPriceResponse,
)
from src.api.services import user_data_service
from src.shared.models.orm import UserOrm

router = APIRouter(prefix="/watchlist", tags=["watchlist"])


@router.get("", response_model=ApiResponse[list[WatchlistEntryResponse]])
async def get_watchlist(
    db: AsyncSession = Depends(get_db),
    current_user: UserOrm = Depends(get_current_user),
) -> ApiResponse[list[WatchlistEntryResponse]]:
    """Return the user's watchlist."""
    entries = await user_data_service.get_watchlist(db, str(current_user.id))
    return ApiResponse(
        data=[WatchlistEntryResponse.model_validate(e) for e in entries]
    )


@router.post(
    "",
    response_model=ApiResponse[WatchlistEntryResponse],
    status_code=status.HTTP_201_CREATED,
    responses={400: {"description": "Invalid symbol format"}},
)
async def add_symbol(
    body: WatchlistAddRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserOrm = Depends(get_current_user),
) -> ApiResponse[WatchlistEntryResponse]:
    """Add a symbol to the watchlist.

    Parameters
    ----------
    body : WatchlistAddRequest
        Symbol to add (alphanumeric, 1-20 chars).

    Returns
    -------
    ApiResponse[WatchlistEntryResponse]
        The newly added watchlist entry.

    Raises
    ------
    HTTPException
        If symbol format is invalid or already exists.
    """
    entry = await user_data_service.add_watchlist_symbol(
        db, str(current_user.id), body.symbol
    )
    return ApiResponse(data=WatchlistEntryResponse.model_validate(entry))


@router.delete(
    "/{symbol}",
    response_model=ApiResponse[None],
    responses={400: {"description": "Invalid symbol format"}},
)
async def remove_symbol(
    symbol: str = Path(
        ...,
        min_length=1,
        max_length=20,
        pattern=r"^[A-Za-z0-9]+$",
        description="Trading symbol (e.g., BTCUSDT)",
    ),
    db: AsyncSession = Depends(get_db),
    current_user: UserOrm = Depends(get_current_user),
) -> ApiResponse[None]:
    """Remove a symbol from the watchlist.

    Parameters
    ----------
    symbol : str
        Symbol to remove (alphanumeric, uppercase).

    Returns
    -------
    ApiResponse[None]
        Success response.

    Raises
    ------
    HTTPException
        If symbol is invalid or not found.
    """
    await user_data_service.remove_watchlist_symbol(
        db, str(current_user.id), symbol
    )
    return ApiResponse(data=None)


@router.get("/prices", response_model=ApiResponse[list[WatchlistPriceResponse]])
async def get_watchlist_prices(
    db: AsyncSession = Depends(get_db),
    current_user: UserOrm = Depends(get_current_user),
) -> ApiResponse[list[WatchlistPriceResponse]]:
    """Return current prices for all symbols in the user's watchlist."""
    prices = await user_data_service.get_watchlist_prices(db, str(current_user.id))
    return ApiResponse(data=[WatchlistPriceResponse(**p) for p in prices])
