"""Crypto router — prices, indicators, market overview."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db
from src.api.schemas import (
    ApiResponse,
    CryptoListItem,
    IndicatorResponse,
    LatestResponse,
    MarketOverviewResponse,
    OHLCVResponse,
    PaginationMeta,
)
from src.api.services import crypto_service

router = APIRouter(prefix="/crypto", tags=["crypto"])


@router.get("/list", response_model=ApiResponse[list[CryptoListItem]])
async def list_tracked() -> ApiResponse[list[CryptoListItem]]:
    """Return the list of tracked crypto symbols."""
    items = crypto_service.list_tracked()
    return ApiResponse(data=[CryptoListItem(**i) for i in items])


@router.get("/market-overview", response_model=ApiResponse[MarketOverviewResponse])
async def market_overview(
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[MarketOverviewResponse]:
    """Return market overview with top movers."""
    data = await crypto_service.get_market_overview(db)
    return ApiResponse(data=MarketOverviewResponse(**data))


@router.get("/{symbol}/prices", response_model=ApiResponse[list[OHLCVResponse]])
async def get_prices(
    symbol: str = Path(..., pattern=r"^[A-Z0-9]+$"),
    timeframe: str = Query("1h", pattern=r"^\d+[mhDWM]$"),
    start: datetime | None = Query(None),
    end: datetime | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    page: int = Query(1, ge=1),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[OHLCVResponse]]:
    """Return OHLCV data for a symbol."""
    records, total = await crypto_service.get_prices(db, symbol, timeframe, start, end, limit, page)
    return ApiResponse(
        data=[OHLCVResponse.model_validate(r) for r in records],
        meta=PaginationMeta(total=total, page=page, limit=limit),
    )


@router.get(
    "/{symbol}/indicators",
    response_model=ApiResponse[list[IndicatorResponse]],
)
async def get_indicators(
    symbol: str = Path(..., pattern=r"^[A-Z0-9]+$"),
    timeframe: str = Query("1h", pattern=r"^\d+[mhDWM]$"),
    limit: int = Query(100, ge=1, le=1000),
    page: int = Query(1, ge=1),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[IndicatorResponse]]:
    """Return technical indicators for a symbol."""
    records, total = await crypto_service.get_indicators(db, symbol, timeframe, limit, page)
    return ApiResponse(
        data=[IndicatorResponse.model_validate(r) for r in records],
        meta=PaginationMeta(total=total, page=page, limit=limit),
    )


@router.get("/{symbol}/latest", response_model=ApiResponse[LatestResponse])
async def get_latest(
    symbol: str = Path(..., pattern=r"^[A-Z0-9]+$"),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[LatestResponse]:
    """Return the latest price and indicators for a symbol."""
    data = await crypto_service.get_latest(db, symbol)
    ohlcv = OHLCVResponse.model_validate(data["ohlcv"]) if data["ohlcv"] else None
    indicators = IndicatorResponse.model_validate(data["indicators"]) if data["indicators"] else None
    return ApiResponse(data=LatestResponse(symbol=data["symbol"], ohlcv=ohlcv, indicators=indicators))
