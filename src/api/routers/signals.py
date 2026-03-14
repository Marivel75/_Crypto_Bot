"""Signals router — active, by symbol, detail, performance."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
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

router = APIRouter(prefix="/signals", tags=["signals"])


def _signal_to_response(s: object) -> SignalResponse:
    """Convert a TradingSignalOrm (with eagerly-loaded outcome) to a response."""
    resp = SignalResponse.model_validate(s)
    outcome = getattr(s, "outcome", None)
    if outcome is not None:
        resp = resp.model_copy(
            update={
                "pnl_simulated": float(outcome.pnl_simulated) if outcome.pnl_simulated is not None else None,
                "was_correct": outcome.was_correct,
            }
        )
    return resp


@router.get("/active", response_model=ApiResponse[list[SignalResponse]])
async def get_active(
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[SignalResponse]]:
    """Return signals from the last 24 hours."""
    signals = await signal_service.get_active(db)
    return ApiResponse(data=[_signal_to_response(s) for s in signals])


@router.get("/performance", response_model=ApiResponse[PerformanceResponse])
async def get_performance(
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[PerformanceResponse]:
    """Return aggregate signal performance stats."""
    data = await signal_service.get_performance(db)
    return ApiResponse(data=PerformanceResponse(**data))  # type: ignore[arg-type]


@router.get("/{signal_id}/detail", response_model=ApiResponse[SignalDetailResponse])
async def get_detail(
    signal_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[SignalDetailResponse]:
    """Return detailed signal info with outcome."""
    data = await signal_service.get_detail(db, str(signal_id))
    signal_resp = SignalResponse.model_validate(data["signal"])
    outcome_resp = SignalOutcomeResponse.model_validate(data["outcome"]) if data["outcome"] else None
    return ApiResponse(data=SignalDetailResponse(signal=signal_resp, outcome=outcome_resp))


@router.get("/{symbol}", response_model=ApiResponse[list[SignalResponse]])
async def get_by_symbol(
    symbol: str,
    timeframe: str | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    page: int = Query(1, ge=1),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[SignalResponse]]:
    """Return signals for a specific symbol."""
    signals, total = await signal_service.get_by_symbol(db, symbol, timeframe, limit, page)
    return ApiResponse(
        data=[_signal_to_response(s) for s in signals],
        meta=PaginationMeta(total=total, page=page, limit=limit),
    )
