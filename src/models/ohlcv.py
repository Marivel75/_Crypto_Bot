"""
Schéma de la table OHLCV (Open, High, Low, Close, Volume) pour la base de données.
Open : Prix d'ouverture
High : Prix le plus haut
Low : Prix le plus bas
Close : Prix de clôture
Volume : Volume échangé
"""

from sqlalchemy import Column, String, Float, DateTime, Index
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class OHLCV(Base):
    """
    Structure de la table ohlcv dans PostgreSQL avec SQLAlchemy.
    Comprend :
    - Types de données appropriés
    - Contraintes de non-nullité
    - Index pour les performances
    - Métadonnées pour le suivi
    """

    __tablename__ = "ohlcv"

    # Clé primaire unique
    id = Column(String(36), primary_key=True, nullable=False)

    # Données de marché essentielles
    timestamp = Column(DateTime, nullable=False, comment="Timestamp de la bougie")
    symbol = Column(
        String(20), nullable=False, comment="Paire de trading (ex: BTC/USDT)"
    )
    timeframe = Column(String(10), nullable=False, comment="Timeframe (ex: 1h, 4h, 1d)")
    open = Column(Float, nullable=False, comment="Prix d'ouverture")
    high = Column(Float, nullable=False, comment="Prix le plus haut")
    low = Column(Float, nullable=False, comment="Prix le plus bas")
    close = Column(Float, nullable=False, comment="Prix de clôture")
    volume = Column(Float, nullable=False, comment="Volume échangé")

    # Enrichissement
    price_range = Column(Float, comment="Amplitude de prix (high - low)")
    price_change = Column(Float, comment="Variation de prix (close - open)")
    price_change_pct = Column(Float, comment="Variation en pourcentage")
    date = Column(String(10), comment="Date au format YYYY-MM-DD")

    # Métadonnées
    exchange = Column(
        String(20),
        nullable=False,
        comment="Source des données (binance, kraken, coinbase)",
    )
    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        comment="Date de création de l'enregistrement",
    )
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        comment="Date de dernière mise à jour",
    )

    # Index pour optimiser les requêtes fréquentes
    __table_args__ = (
        # Index pour les requêtes par paire et timeframe
        Index("idx_ohlcv_symbol_timeframe", "symbol", "timeframe"),
        # Index pour les requêtes temporelles
        Index("idx_ohlcv_timestamp", "timestamp"),
        # Index composite pour les requêtes combinées
        Index("idx_ohlcv_symbol_timestamp", "symbol", "timestamp"),
    )

    def __repr__(self):
        return (
            f"<OHLCV(id={self.id}, symbol={self.symbol}, "
            f"timeframe={self.timeframe}, timestamp={self.timestamp})>"
        )
