# models/global_snapshot.py

from sqlalchemy import Column, Integer, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


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
