"""News service — latest articles, detail, sentiment."""

from __future__ import annotations

import logging

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.exceptions import NotFoundError
from src.shared.models.orm import NewsArticleOrm

logger = logging.getLogger(__name__)


async def get_latest(
    db: AsyncSession,
    source: str | None = None,
    keyword: str | None = None,
    limit: int = 20,
    page: int = 1,
) -> tuple[list[NewsArticleOrm], int]:
    """Return the latest news articles with optional source/keyword filters.

    Args:
        db: Active async database session.
        source: Optional exact match on the ``source`` column.
        keyword: Optional case-insensitive substring search on the ``title`` column.
        limit: Maximum number of records per page.
        page: 1-based page number.

    Returns:
        Tuple of (list of NewsArticleOrm rows ordered by published_at descending, total count).
    """
    conditions: list = []
    if source is not None:
        conditions.append(NewsArticleOrm.source == source)
    if keyword is not None:
        escaped = keyword.replace("\\", "\\\\").replace("%", r"\%").replace("_", r"\_")
        conditions.append(NewsArticleOrm.title.ilike(f"%{escaped}%"))

    count_query = select(func.count()).select_from(NewsArticleOrm)
    if conditions:
        count_query = count_query.where(*conditions)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    offset = (page - 1) * limit
    query = select(NewsArticleOrm)
    if conditions:
        query = query.where(*conditions)
    query = query.order_by(desc(NewsArticleOrm.published_at)).offset(offset).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all()), total


async def get_by_id(db: AsyncSession, news_id: str) -> NewsArticleOrm:
    """Return a single news article by its UUID.

    Args:
        db: Active async database session.
        news_id: UUID string of the article.

    Returns:
        The matching NewsArticleOrm instance.

    Raises:
        NotFoundError: If no article with the given ID exists.
    """
    result = await db.execute(select(NewsArticleOrm).where(NewsArticleOrm.id == news_id))
    article = result.scalar_one_or_none()
    if article is None:
        raise NotFoundError(f"News article {news_id} not found")
    return article


async def get_sentiment(db: AsyncSession) -> list[dict[str, object]]:
    """Return average sentiment score and article count grouped by source.

    Only articles with a non-null ``sentiment_score`` are included.

    Args:
        db: Active async database session.

    Returns:
        List of dicts with keys ``symbol`` (source name), ``sentiment_score``
        (rounded float | None), and ``article_count`` (int).
    """
    result = await db.execute(
        select(
            NewsArticleOrm.source,
            func.avg(NewsArticleOrm.sentiment_score).label("avg_sentiment"),
            func.count().label("article_count"),
        )
        .where(NewsArticleOrm.sentiment_score.isnot(None))
        .group_by(NewsArticleOrm.source)
    )
    rows = result.all()
    return [
        {
            "symbol": row.source,
            "sentiment_score": round(float(row.avg_sentiment), 4) if row.avg_sentiment else None,
            "article_count": row.article_count,
        }
        for row in rows
    ]
