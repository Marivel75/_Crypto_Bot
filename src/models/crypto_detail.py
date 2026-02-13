from sqlalchemy import Column, Integer, String, Float, ForeignKey, Index, JSON, DateTime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.models.market_data_base import MarketDataBase

Base = MarketDataBase


class CryptoDetail(Base):
    """
    Détails d'une cryptomonnaie collectés depuis CoinGecko.
    Métadonnées, liens, community data, developer data.
    """

    __tablename__ = "crypto_detail"

    id = Column(Integer, primary_key=True, autoincrement=True)
    snapshot_id = Column(
        Integer,
        ForeignKey("crypto_detail_snapshot.id"),
        nullable=False,
        comment="Lien vers le snapshot",
    )

    # Identifiants
    crypto_id = Column(String(50), nullable=False, comment="ID CoinGecko (ex: bitcoin)")
    symbol = Column(String(20), nullable=False, comment="Symbole (ex: BTC)")
    name = Column(String(100), nullable=False, comment="Nom complet (ex: Bitcoin)")

    # Métadonnées de base
    rank = Column(Integer, nullable=True, comment="Classement par market cap")
    categories = Column(String(500), nullable=True, comment="Catégories (JSON array)")
    genesis_date = Column(String(20), nullable=True, comment="Date de création")
    hashing_algorithm = Column(String(100), nullable=True, comment="Algorithme de hash")
    block_time_minutes = Column(Integer, nullable=True, comment="Block time en minutes")

    # Image
    image_large = Column(String(500), nullable=True, comment="URL image grande")
    image_small = Column(String(500), nullable=True, comment="URL image petite")

    # Liens (stockés en JSON)
    links_homepage = Column(
        String(1000), nullable=True, comment="Homepages (JSON array)"
    )
    links_blockchain_site = Column(
        String(2000), nullable=True, comment="Blockchain sites (JSON)"
    )
    links_whitepaper = Column(String(500), nullable=True, comment="URL whitepaper")
    links_reddit = Column(String(500), nullable=True, comment="URL Reddit")
    links_twitter = Column(String(100), nullable=True, comment="Twitter handle")

    # Community data
    community_twitter = Column(Integer, nullable=True, comment="Followers Twitter")
    community_reddit = Column(Integer, nullable=True, comment="Abonnés Reddit")
    community_facebook = Column(Integer, nullable=True, comment="Likes Facebook")

    # Developer data
    developer_stars = Column(Integer, nullable=True, comment="Stars GitHub")
    developer_forks = Column(Integer, nullable=True, comment="Forks GitHub")
    developer_subscribers = Column(Integer, nullable=True, comment="Subscribers GitHub")
    developer_issues = Column(Integer, nullable=True, comment="Open issues GitHub")
    developer_pull_requests = Column(Integer, nullable=True, comment="Pull requests")

    # Market data (répétitif avec top_crypto mais intégrable ici)
    market_cap_rank = Column(Integer, nullable=True, comment="Market cap rank")
    market_cap = Column(Float, nullable=True, comment="Market cap USD")
    total_volume = Column(Float, nullable=True, comment="Volume 24h USD")
    high_24h = Column(Float, nullable=True, comment="Plus haut 24h USD")
    low_24h = Column(Float, nullable=True, comment="Plus bas 24h USD")
    price_change_24h = Column(Float, nullable=True, comment="Prix change 24h USD")
    price_change_pct_24h = Column(Float, nullable=True, comment="Prix change 24h %")

    # ATH/ATL
    ath_price = Column(Float, nullable=True, comment="ATH prix USD")
    ath_date = Column(String(20), nullable=True, comment="Date ATH")
    ath_change_pct = Column(Float, nullable=True, comment="ATH change %")
    atl_price = Column(Float, nullable=True, comment="ATL prix USD")
    atl_date = Column(String(20), nullable=True, comment="Date ATL")
    atl_change_pct = Column(Float, nullable=True, comment="ATL change %")

    # Supply
    circulating_supply = Column(Float, nullable=True, comment="Circulating supply")
    total_supply = Column(Float, nullable=True, comment="Total supply")
    max_supply = Column(Float, nullable=True, comment="Max supply")

    # Timestamp
    last_updated = Column(
        DateTime, nullable=True, comment="Dernière mise à jour CoinGecko"
    )

    # Index
    __table_args__ = (
        Index("idx_crypto_detail_snapshot_id", "snapshot_id"),
        Index("idx_crypto_detail_crypto_id", "crypto_id"),
        Index("idx_crypto_detail_symbol", "symbol"),
        Index("idx_crypto_detail_rank", "rank"),
    )

    def __repr__(self):
        return f"<CryptoDetail(crypto_id={self.crypto_id}, name={self.name}, rank={self.rank})>"
