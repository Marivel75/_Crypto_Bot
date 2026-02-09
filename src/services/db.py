import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from logger_settings import logger
from config.settings import config
from src.services.db_environment import db_env

# Importer les bases de modèles ici pour éviter les erreurs tardives
from src.models.ohlcv import Base as OHLCVBase
from src.models.ticker import Base as TickerBase

Base = declarative_base()


def get_db_engine(environment=None):
    """
    Crée et retourne un moteur SQLAlchemy pour la base de données.
    Crée automatiquement les dossiers et la base de données si nécessaire.

    Args:
        environment: Environnement cible (production/testing, None utilise l'env actuel)

    Raises:
        ValueError: Si l'environnement est invalide
    """
    try:
        # Vérifier la validité de l'environnement
        if environment and environment not in ["production", "testing"]:
            logger.error(f"Environnement invalide: {environment}")
            raise ValueError(
                f"Environnement invalide: {environment}. Utilisez 'production' ou 'testing'."
            )

        # Obtenir l'URL de base de données appropriée
        if environment:
            db_url = db_env.get_db_url(environment)
            db_env.set_environment(environment)
            logger.info(f"Configuration DB - Environnement forcé: {environment}")
        else:
            db_url = db_env.get_current_db_url()
            logger.info(
                f"Configuration DB - Environnement actuel: {db_env.current_env}"
            )

        logger.info(f"Configuration DB - URL: {db_url}")

        # S'assurer que les répertoires existent
        db_env.ensure_directories()

        logger.info(f"🔒 Environnement final: {db_env.current_env}")
        logger.info(f"📂 Base de données cible: {db_url}")

        # Créer le moteur avec des paramètres spécifiques pour SQLite
        connect_args = {}
        if db_url.startswith("sqlite:///"):
            connect_args = {"check_same_thread": False}

        engine = create_engine(
            db_url,
            echo=False,  # Mettre à True pour le débogage SQL
            connect_args=connect_args,
        )

        # Créer les tables si absentes (checkfirst=True pour éviter les erreurs)
        OHLCVBase.metadata.create_all(engine, checkfirst=True)
        TickerBase.metadata.create_all(engine, checkfirst=True)

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
    """
    Retourne l'engine de base de données (pour la compatibilité).
    Alias de get_db_engine().
    """
    return get_db_engine()
