from sqlalchemy import Column, Integer, String, Float, ForeignKey, Index
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.models.market_data_base import MarketDataBase

Base = MarketDataBase


class TopCrypto(Base):
    """
    Crypto appartenant à un snapshot TopCryptoSnapshot.
    """

    __tablename__ = "top_crypto"

    id = Column(Integer, primary_key=True, autoincrement=True)
    snapshot_id = Column(
        Integer,
        ForeignKey("top_crypto_snapshot.id"),
        nullable=False,
        comment="Lien vers le snapshot",
    )
    rank = Column(
        Integer, nullable=True, comment="Classement par capitalisation boursière"
    )
    crypto_id = Column(String(50), nullable=False, comment="ID CoinGecko de la crypto")
    symbol = Column(
        String(20), nullable=False, comment="Symbole de la crypto (ex: BTC)"
    )
    name = Column(String(50), nullable=False, comment="Nom de la crypto (ex: Bitcoin)")
    market_cap = Column(Float, nullable=True, comment="Capitalisation boursière")
    price = Column(Float, nullable=True, comment="Prix actuel")
    volume_24h = Column(Float, nullable=True, comment="Volume échangé sur 24h")
    price_change_pct_24h = Column(
        Float, nullable=True, comment="Variation du prix en % sur 24h"
    )

    # Index pour requêtes fréquentes
    __table_args__ = (
        Index("idx_top_crypto_snapshot_id", "snapshot_id"),
        Index("idx_top_crypto_rank", "rank"),
        Index("idx_top_crypto_symbol", "symbol"),
    )

    def __repr__(self):
        return f"<TopCrypto(symbol={self.symbol}, rank={self.rank}, price={self.price}, market_cap={self.market_cap})>"
