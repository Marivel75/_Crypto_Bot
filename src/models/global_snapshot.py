# models/global_snapshot.py

from sqlalchemy import Column, Integer, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.models.market_data_base import MarketDataBase

Base = MarketDataBase


class GlobalMarketSnapshot(Base):
    """
    Table principale des snapshots globaux du marché crypto.
    Une ligne = un snapshot à un instant T.
    """

    __tablename__ = "global_market_snapshot"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, unique=True, index=True)

    # Statistiques globales
    active_cryptocurrencies = Column(Integer)
    upcoming_icos = Column(Integer)
    ongoing_icos = Column(Integer)
    ended_icos = Column(Integer)
    markets = Column(Integer)

    # Changes 24h
    market_cap_change_24h = Column(Float)
    volume_change_24h = Column(Float)

    # timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
