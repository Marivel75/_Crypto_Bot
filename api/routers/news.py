"""FastAPI router for news articles and sentiment data."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from api.dependencies import get_db
from api.schemas.news import NewsArticleResponse, NewsSentimentResponse
from src.models.news import NewsArticle

router = APIRouter(prefix="/news", tags=["news"])


@router.get("", response_model=List[NewsArticleResponse])
def get_news(
    source: Optional[str] = Query(None, description="Filtrer par source"),
    sentiment: Optional[str] = Query(None, description="positive / negative / neutral"),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Return the most recent news articles, newest first."""
    query = db.query(NewsArticle)
    if source:
        query = query.filter(NewsArticle.source == source)
    if sentiment:
        query = query.filter(NewsArticle.sentiment_label == sentiment.lower())

    articles = query.order_by(NewsArticle.collected_at.desc()).limit(limit).all()
    return articles


@router.get("/sources", response_model=List[str])
def get_news_sources(db: Session = Depends(get_db)):
    """Return distinct source names available in the database."""
    rows = db.query(NewsArticle.source).distinct().order_by(NewsArticle.source).all()
    return [r[0] for r in rows]


@router.get("/sentiment", response_model=List[NewsSentimentResponse])
def get_news_sentiment(db: Session = Depends(get_db)):
    """Return sentiment aggregates grouped by source (works with SQLite and PostgreSQL)."""
    sources = db.query(NewsArticle.source).distinct().all()
    result = []
    for (source,) in sources:
        articles = db.query(NewsArticle).filter(NewsArticle.source == source).all()
        total = len(articles)
        positive = sum(1 for a in articles if a.sentiment_label == "positive")
        negative = sum(1 for a in articles if a.sentiment_label == "negative")
        neutral = sum(1 for a in articles if a.sentiment_label == "neutral")
        scores = [a.sentiment_score for a in articles if a.sentiment_score is not None]
        avg_score = round(sum(scores) / len(scores), 4) if scores else None
        result.append(NewsSentimentResponse(
            source=source,
            total=total,
            positive=positive,
            negative=negative,
            neutral=neutral,
            avg_score=avg_score,
        ))

    return sorted(result, key=lambda x: x.total, reverse=True)
