import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from logger_settings import logger
from config.settings import config
from src.config.settings import ENVIRONMENT, SUPABASE_DB_URL, SQLITE_DB_PATH

# Configuration de la base de données
# Utiliser le type de base de données depuis la configuration
db_type = config.get("database.type", "sqlite")
if db_type == "postgresql":
    DATABASE_URL = SUPABASE_DB_URL
    logger.info(f"Utilisation de PostgreSQL/Supabase (Environnement: {ENVIRONMENT})")
else:
    DATABASE_URL = f"sqlite:///{SQLITE_DB_PATH}"
    logger.info(f"Utilisation de SQLite (Environnement: {ENVIRONMENT})")

Base = declarative_base()

def get_db_engine():
    """
    Crée et retourne un moteur SQLAlchemy pour la base de données.
    Crée automatiquement les dossiers et la base de données si nécessaire (SQLite).
    """
    try:
        # Créer les dossiers si nécessaire (pour SQLite)
        if DATABASE_URL.startswith("sqlite:///"):
            db_path = DATABASE_URL.replace("sqlite:///", "")
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            logger.info(f"Assure que le dossier existe: {os.path.dirname(db_path)}")

        # Paramètres spécifiques pour SQLite
        connect_args = {}
        if DATABASE_URL.startswith("sqlite:///"):
            connect_args = {"check_same_thread": False}

        # Paramètres spécifiques pour PostgreSQL (Supabase)
        engine_args = {}
        if DATABASE_URL.startswith("postgresql://"):
            engine_args = {
                "pool_size": 5,
                "max_overflow": 10,
                "pool_pre_ping": True,
            }

        engine = create_engine(DATABASE_URL, connect_args=connect_args, **engine_args)

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
