import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from logger_settings import logger
from config.settings import config
from src.services.db_environment import db_env

# Configuration de la base de données - Utiliser l'environnement actuel
DATABASE_URL = db_env.get_current_db_url()

Base = declarative_base()


def get_db_engine(environment=None):
    """
    Crée et retourne un moteur SQLAlchemy pour la base de données.
    Crée automatiquement les dossiers et la base de données si nécessaire.

    Args:
        environment: Environnement cible (production/testing, None utilise l'env actuel)
    """
    try:
        # Obtenir l'URL de base de données appropriée
        if environment:
            db_url = db_env.get_db_url(environment)
        else:
            db_url = db_env.get_current_db_url()

        logger.info(f"Configuration DB - Environnement: {db_env.current_env}")
        logger.info(f"Configuration DB - URL: {db_url}")

        # S'assurer que les répertoires existent
        db_env.ensure_directories()

        # Créer le moteur avec des paramètres spécifiques pour SQLite
        connect_args = {}
        if db_url.startswith("sqlite:///"):
            connect_args = {"check_same_thread": False}

        engine = create_engine(
            db_url,
            echo=False,  # Mettre à True pour le débogage SQL
            connect_args=connect_args,
        )

        # Créer les tables si absentes
        from src.models.ohlcv import Base as OHLCVBase
        from src.models.ticker import Base as TickerBase

        OHLCVBase.metadata.create_all(engine)
        TickerBase.metadata.create_all(engine)

        logger.info(f"✅ Connexion réussie à la base de données: {db_url}")
        return engine
    except Exception as e:
        logger.error(f"❌ Erreur de connexion à la base de données: {e}")
        raise


def get_db_session():
    """
    Crée et retourne une session de base de données.

    Returns:
        sqlalchemy.orm.session.Session: Session de base de données
    """
    engine = get_db_engine()
    Session = sessionmaker(bind=engine)
    return Session()


# Engine par défaut pour la compatibilité (lazy loading)
def get_engine():
    """Retourne l'engine de base de données (pour la compatibilité)"""
    return get_db_engine()
