import os

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from config.settings import config
from src.config.logger_settings import logger

# Configuration de la base de données - Utiliser la configuration centralisée
DATABASE_URL = config.get("database.url")

Base = declarative_base()


def get_db_engine() -> Engine:
    """
    Crée et retourne un moteur SQLAlchemy pour la base de données. Crée
    automatiquement les dossiers et la base de données si nécessaire.
    """
    try:
        # Créer les dossiers si nécessaire (pour SQLite)
        if DATABASE_URL.startswith("sqlite:///"):
            db_path = DATABASE_URL.replace("sqlite:///", "")
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            logger.info(f"Assure que le dossier existe: {os.path.dirname(db_path)}")

        # Créer le moteur avec des paramètres spécifiques pour SQLite
        connect_args = {}
        if DATABASE_URL.startswith("sqlite:///"):
            connect_args = {"check_same_thread": False}

        engine = create_engine(
            DATABASE_URL,
            echo=False,  # Mettre à True pour le débogage SQL
            connect_args=connect_args,
        )

        # Créer les tables si absentes
        from src.models.ohlcv import Base as OHLCVBase
        from src.models.ticker import Base as TickerBase

        OHLCVBase.metadata.create_all(engine)
        TickerBase.metadata.create_all(engine)

        logger.info(f"Connexion à la base de données: {DATABASE_URL}")
        return engine
    except Exception as e:
        logger.error(f"❌ Erreur de connexion à la base de données: {e}")
        raise


def get_db_session() -> Session:
    """
    Crée et retourne une session de base de données.

    Returns:
        sqlalchemy.orm.session.Session: Session de base de données
    """
    engine = get_db_engine()
    Session = sessionmaker(bind=engine)
    return Session()


# Engine par défaut pour la compatibilité (lazy loading)
def get_engine() -> Engine:
    """Retourne l'engine de base de données (pour la compatibilité)"""
    return get_db_engine()
