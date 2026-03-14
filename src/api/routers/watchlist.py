"""Watchlist router — add, list, remove symbols."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user, get_db
from src.api.schemas import (
    ApiResponse,
    WatchlistAddRequest,
    WatchlistEntryResponse,
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
    return ApiResponse(data=[WatchlistEntryResponse.model_validate(e) for e in entries])


@router.post(
    "",
    response_model=ApiResponse[WatchlistEntryResponse],
    status_code=status.HTTP_201_CREATED,
)
async def add_symbol(
    body: WatchlistAddRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserOrm = Depends(get_current_user),
) -> ApiResponse[WatchlistEntryResponse]:
    """Add a symbol to the watchlist."""
    entry = await user_data_service.add_watchlist_symbol(db, str(current_user.id), body.symbol)
    return ApiResponse(data=WatchlistEntryResponse.model_validate(entry))


@router.delete("/{symbol}", response_model=ApiResponse[None])
async def remove_symbol(
    symbol: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserOrm = Depends(get_current_user),
) -> ApiResponse[None]:
    """Remove a symbol from the watchlist."""
    await user_data_service.remove_watchlist_symbol(db, str(current_user.id), symbol)
    return ApiResponse(data=None)
