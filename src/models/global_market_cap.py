# models/global_market_cap.py

from sqlalchemy import Column, Integer, Float, String, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.models.market_data_base import MarketDataBase

Base = MarketDataBase


class GlobalMarketCap(Base):
    """
    Stocke le total market cap par devise (USD, EUR, BTC, etc.).
    """

    __tablename__ = "global_market_cap"

    id = Column(Integer, primary_key=True)
    snapshot_id = Column(
        Integer, ForeignKey("global_market_snapshot.id"), nullable=False, index=True
    )
    currency = Column(String(10), nullable=False, index=True)
    value = Column(Float, nullable=False)

    __table_args__ = (
        Index("idx_marketcap_snapshot_currency", "snapshot_id", "currency"),
    )
