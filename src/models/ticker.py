"""
Modèles de données pour les tickers et snapshots.
"""

from sqlalchemy import Column, String, Float, DateTime, Index
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import uuid

# Base pour les modèles de tickers
Base = declarative_base()


class TickerSnapshot(Base):
    """
    Table pour stocker les snapshots périodiques des données de tickers.
    Stocke des instantanés des prix et volumes à intervalles réguliers plutôt que chaque mise à jour,
    pour éviter la surcharge de la base de données.
    Compatible avec SQLite et PostgreSQL (Supabase).
    """

    __tablename__ = "ticker_snapshots"

    # Clé primaire unique avec génération automatique
    id = Column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4()), nullable=False
    )
    snapshot_time = Column(DateTime, nullable=False, comment="Heure du snapshot")
    symbol = Column(String(20), nullable=False, comment="Paire de trading")
    exchange = Column(String(20), nullable=False, comment="Exchange source")

    # Données du ticker
    price = Column(Float, comment="Prix actuel")
    volume_24h = Column(Float, comment="Volume sur 24h")
    price_change_24h = Column(Float, comment="Variation de prix sur 24h")
    price_change_pct_24h = Column(Float, comment="Variation en pourcentage sur 24h")
    high_24h = Column(Float, comment="Plus haut sur 24h")
    low_24h = Column(Float, comment="Plus bas sur 24h")

    # Métadonnées
    created_at = Column(DateTime, default=datetime.utcnow, comment="Date de création")

    # Index pour optimiser les requêtes fréquentes
    __table_args__ = (
        Index("idx_ticker_snapshot_time", "snapshot_time"),
        Index("idx_ticker_symbol_time", "symbol", "snapshot_time"),
    )

    def __repr__(self):
        return (
            f"<TickerSnapshot(id={self.id}, symbol={self.symbol}, "
            f"price={self.price}, snapshot_time={self.snapshot_time})>"
        )

    @classmethod
    def create_table(cls, engine):
        """
        Crée la table dans la base de données si elle n'existe pas.
        Args:
            engine: SQLAlchemy engine
        """
        Base.metadata.create_all(engine)
