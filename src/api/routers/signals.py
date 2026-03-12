"""Signals router — active, by symbol, detail, performance, history."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db
from src.api.schemas import (
    ApiResponse,
    PaginationMeta,
    PerformanceResponse,
    SignalDetailResponse,
    SignalOutcomeResponse,
    SignalResponse,
)
from src.api.services import signal_service
from src.shared.models import constants

router = APIRouter(prefix="/signals", tags=["signals"])


@router.get("/active", response_model=ApiResponse[list[SignalResponse]])
async def get_active(
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[SignalResponse]]:
    """Return signals from the last 24 hours."""
    signals = await signal_service.get_active(db)
    return ApiResponse(data=[SignalResponse.model_validate(s) for s in signals])


@router.get("/performance", response_model=ApiResponse[PerformanceResponse])
async def get_performance(
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[PerformanceResponse]:
    """Return aggregate signal performance stats."""
    data = await signal_service.get_performance(db)
    return ApiResponse(data=PerformanceResponse(**data))


@router.get("/{signal_id}/detail", response_model=ApiResponse[SignalDetailResponse])
async def get_detail(
    signal_id: UUID = Path(..., description="Signal UUID"),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[SignalDetailResponse]:
    """Return detailed signal info with outcome."""
    data = await signal_service.get_detail(db, str(signal_id))
    signal_resp = SignalResponse.model_validate(data["signal"])
    outcome_resp = (
        SignalOutcomeResponse.model_validate(data["outcome"])
        if data["outcome"]
        else None
    )
    return ApiResponse(data=SignalDetailResponse(signal=signal_resp, outcome=outcome_resp))


@router.get(
    "/{symbol}",
    response_model=ApiResponse[list[SignalResponse]],
    responses={400: {"description": "Invalid symbol or timeframe format"}},
)
async def get_by_symbol(
    symbol: str = Path(
        ...,
        min_length=1,
        max_length=20,
        pattern=r"^[A-Za-z0-9]+$",
        description="Trading symbol (e.g., BTCUSDT)",
    ),
    timeframe: str = Query(
        None,
        min_length=1,
        max_length=5,
        pattern=r"^[0-9]{1,4}[mhDWM]$",
        description="Timeframe (e.g., 1h, 4h, 1D)",
    ),
    limit: int = Query(50, ge=1, le=500, description="Max results per page"),
    page: int = Query(1, ge=1, description="Page number"),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[SignalResponse]]:
    """Return signals for a specific symbol.

    Parameters
    ----------
    symbol : str
        Trading symbol (uppercase, alphanumeric only).
    timeframe : str, optional
        OHLCV timeframe (e.g., 1h, 4h, 1D). Must match: 1-4 digits + m/h/D/W/M.
    limit : int
        Pagination limit (1-500).
    page : int
        Page number (starting at 1).

    Returns
    -------
    ApiResponse[list[SignalResponse]]
        Paginated list of signals with metadata.

    Raises
    ------
    HTTPException
        If symbol or timeframe format is invalid.
    """
    signals, total = await signal_service.get_by_symbol(db, symbol, timeframe, limit, page)
    return ApiResponse(
        data=[SignalResponse.model_validate(s) for s in signals],
        meta=PaginationMeta(total=total, page=page, limit=limit),
    )


@router.get("/history", response_model=ApiResponse[list[SignalResponse]])
async def get_history(
    start: datetime | None = Query(None, description="Start date (ISO 8601)"),
    end: datetime | None = Query(None, description="End date (ISO 8601)"),
    limit: int = Query(100, ge=1, le=500, description="Max results per page"),
    page: int = Query(1, ge=1, description="Page number"),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[SignalResponse]]:
    """Return paginated signal history with optional date range filtering.

    Parameters
    ----------
    start : datetime, optional
        Inclusive lower bound for signal creation time.
    end : datetime, optional
        Inclusive upper bound for signal creation time.
    limit : int
        Pagination limit (1-500).
    page : int
        Page number (starting at 1).

    Returns
    -------
    ApiResponse[list[SignalResponse]]
        Paginated historical signals with metadata.
    """
    signals, total = await signal_service.get_history(db, start, end, limit, page)
    return ApiResponse(
        data=[SignalResponse.model_validate(s) for s in signals],
        meta=PaginationMeta(total=total, page=page, limit=limit),
    )
