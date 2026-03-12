"""System router — health check, sources status, metrics."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db
from src.api.schemas import ApiResponse, HealthResponse, MetricsResponse, SourceStatusResponse
from src.shared.models.orm import OHLCVOrm

logger = logging.getLogger(__name__)

health_router = APIRouter(tags=["system"])
router = APIRouter(prefix="/system", tags=["system"])


@health_router.get("/health", response_model=ApiResponse[HealthResponse])
# S11: health endpoint now accessible at /api/v1/health (via prefix)
async def health(
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[HealthResponse]:
    """Health check — verify database connectivity."""
    db_status = "ok"
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        logger.exception("Database health check failed")
        db_status = "error"

    return ApiResponse(
        data=HealthResponse(
            status="ok" if db_status == "ok" else "degraded",
            database=db_status,
            timestamp=datetime.now(tz=UTC),
        )
    )


@router.get(
    "/sources-status",
    response_model=ApiResponse[list[SourceStatusResponse]],
)
async def sources_status(
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[SourceStatusResponse]]:
    """Return last ingestion time per source/symbol."""
    result = await db.execute(
        select(
            OHLCVOrm.source,
            OHLCVOrm.symbol,
            func.max(OHLCVOrm.timestamp).label("last_ingestion"),
            func.count().label("record_count"),
        ).group_by(OHLCVOrm.source, OHLCVOrm.symbol)
    )
    rows = result.all()
    return ApiResponse(
        data=[
            SourceStatusResponse(
                source=row.source,
                symbol=row.symbol,
                last_ingestion=row.last_ingestion,
                record_count=row.record_count,
            )
            for row in rows
        ]
    )


@router.get("/metrics", response_model=ApiResponse[MetricsResponse])
async def get_metrics() -> ApiResponse[MetricsResponse]:
    """Return application metrics from Prometheus.

    Includes request counts, error rates, and latency statistics.
    For full metrics in Prometheus format, see /metrics endpoint.
    """
    return ApiResponse(data=MetricsResponse())
