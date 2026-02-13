# models/global_market_dominance.py

from sqlalchemy import Column, Integer, Float, String, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.models.market_data_base import MarketDataBase

Base = MarketDataBase


class GlobalMarketDominance(Base):
    """
    Stocke la dominance du market cap par crypto (BTC, ETH, etc.).
    """

    __tablename__ = "global_market_dominance"

    id = Column(Integer, primary_key=True)
    snapshot_id = Column(
        Integer, ForeignKey("global_market_snapshot.id"), nullable=False, index=True
    )
    asset = Column(String(10), nullable=False, index=True)
    percentage = Column(Float, nullable=False)

    __table_args__ = (Index("idx_dominance_snapshot_asset", "snapshot_id", "asset"),)
