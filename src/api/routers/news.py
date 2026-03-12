"""News router — latest, by id, sentiment."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db
from src.api.schemas import (
    ApiResponse,
    NewsResponse,
    NewsSentimentResponse,
    PaginationMeta,
)
from src.api.services import news_service

router = APIRouter(prefix="/news", tags=["news"])


@router.get("/latest", response_model=ApiResponse[list[NewsResponse]])
async def get_latest(
    source: str | None = Query(None),
    keyword: str | None = Query(None, max_length=100),
    limit: int = Query(20, ge=1, le=100),
    page: int = Query(1, ge=1),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[NewsResponse]]:
    """Return latest news articles."""
    articles, total = await news_service.get_latest(db, source, keyword, limit, page)
    return ApiResponse(
        data=[NewsResponse.model_validate(a) for a in articles],
        meta=PaginationMeta(total=total, page=page, limit=limit),
    )


@router.get("/sentiment", response_model=ApiResponse[list[NewsSentimentResponse]])
async def get_sentiment(
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[NewsSentimentResponse]]:
    """Return aggregate sentiment by source."""
    data = await news_service.get_sentiment(db)
    return ApiResponse(data=[NewsSentimentResponse(**d) for d in data])


@router.get("/{news_id}", response_model=ApiResponse[NewsResponse])
async def get_by_id(
    news_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[NewsResponse]:
    """Return a single news article."""
    article = await news_service.get_by_id(db, str(news_id))
    return ApiResponse(data=NewsResponse.model_validate(article))
