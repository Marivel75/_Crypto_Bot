from sqlalchemy import Column, Integer, String, DateTime, JSON
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.models.market_data_base import MarketDataBase

Base = MarketDataBase


class CryptoDetailSnapshot(Base):
    """
    Snapshot des détails des cryptomonnaies pour un instant donné.
    """

    __tablename__ = "crypto_detail_snapshot"

    id = Column(Integer, primary_key=True, autoincrement=True)
    snapshot_time = Column(
        DateTime,
        nullable=False,
        comment="Timestamp du snapshot",
    )
    cryptos_count = Column(
        Integer,
        nullable=False,
        comment="Nombre de cryptos dont les détails ont été collectés",
    )

    def __repr__(self):
        return f"<CryptoDetailSnapshot(id={self.id}, snapshot_time={self.snapshot_time}, cryptos_count={self.cryptos_count})>"
