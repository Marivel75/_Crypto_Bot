from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class AlertSubscriber(Base):
    __tablename__ = "alert_subscribers"

    id         = Column(Integer, primary_key=True, index=True)
    email      = Column(String, unique=True, nullable=False, index=True)
    active     = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
