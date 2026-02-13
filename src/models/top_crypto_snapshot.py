from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.models.market_data_base import MarketDataBase

Base = MarketDataBase


class TopCryptoSnapshot(Base):
    """
    Snapshot du Top N cryptos pour un instant donné.
    """

    __tablename__ = "top_crypto_snapshot"

    id = Column(Integer, primary_key=True, autoincrement=True)
    snapshot_time = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        comment="Timestamp du snapshot",
    )
    vs_currency = Column(
        String(10), nullable=False, comment="Devise de référence (ex: USD, EUR)"
    )

    def __repr__(self):
        return f"<TopCryptoSnapshot(id={self.id}, vs_currency={self.vs_currency}, snapshot_time={self.snapshot_time})>"
