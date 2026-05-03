"""Pydantic schemas for news article responses."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class NewsArticleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    url: str
    source: str
    published_at: datetime | None = None
    content: str | None = None
    sentiment_score: float | None = None
    sentiment_label: str | None = None
    keywords: list[str] | None = None
    entities: dict | None = None
    topics: list[str] | None = None
    collected_at: datetime | None = None


class NewsSentimentResponse(BaseModel):
    source: str
    total: int
    positive: int
    negative: int
    neutral: int
    avg_score: float | None = None
