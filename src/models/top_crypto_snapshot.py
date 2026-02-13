from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


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
