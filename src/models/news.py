"""SQLAlchemy model for news articles."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, JSON, String, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class NewsArticle(Base):
    __tablename__ = "news_articles"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(500), nullable=False)
    url = Column(String(1000), unique=True, nullable=False)
    source = Column(String(150), nullable=False)
    published_at = Column(DateTime, nullable=True)
    content = Column(Text, nullable=True)
    sentiment_score = Column(Float, nullable=True)   # −1 to +1 (VADER compound)
    sentiment_label = Column(String(20), nullable=True)  # positive / negative / neutral
    keywords = Column(JSON, nullable=True)           # list[str]
    collected_at = Column(DateTime, default=datetime.utcnow)
