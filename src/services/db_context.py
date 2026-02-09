"""
Module de gestion des connexions à la base de données avec context managers.
Fournit des classes pour gérer les ressources de base de données.
"""

from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from logger_settings import logger
from config.settings import config
from src.config.settings import ENVIRONMENT, SUPABASE_DB_URL, SQLITE_DB_PATH
from typing import Generator, Any

# Configuration de la base de données
# Utiliser le type de base de données depuis la configuration
db_type = config.get("database.type", "sqlite")
if db_type == "postgresql":
    DATABASE_URL = SUPABASE_DB_URL
    logger.info(
        f"db_context: Utilisation de PostgreSQL/Supabase (Environnement: {ENVIRONMENT})"
    )
else:
    DATABASE_URL = f"sqlite:///{SQLITE_DB_PATH}"
    logger.info(f"db_context: Utilisation de SQLite (Environnement: {ENVIRONMENT})")


class DatabaseConnection:
    """
    Context manager pour la gestion des connexions à la base de données.
    Garantit que les connexions sont correctement ouvertes et fermées, même en cas d'erreur.
    """

    def __init__(self):
        self.engine = None
        self.connection = None

    def __enter__(self):
        """
        Ouvre une connexion à la base de données en utilisant l'URL définie dans `DATABASE_URL`.
        Configure automatiquement les paramètres spécifiques pour PostgreSQL (comme Supabase)
        et gère les erreurs de connexion.

        Returns:
            sqlalchemy.engine.Connection: Une connexion active à la base de données.
                                        Doit être utilisée dans un bloc `with` pour garantir
                                        la fermeture automatique.

        Raises:
            ValueError: Si `DATABASE_URL` n'est pas définie (variable d'environnement manquante).
            SQLAlchemyError: En cas d'échec de la connexion (ex: URL invalide, serveur inaccessible,
                            authentification échouée). L'erreur est loggée avant d'être relancée.

        Notes:
            - Pour Supabase (PostgreSQL), les paramètres de pool sont optimisés :
            `pool_size=5`, `max_overflow=10`, `pool_pre_ping=True`.
            - Les logs sont écrits via `logger` pour le débogage (niveau DEBUG pour les succès,
            ERROR pour les échecs).
        """
        try:
            # Paramètres spécifiques pour PostgreSQL (Supabase)
            engine_args = {}
            if DATABASE_URL is None:
                raise ValueError(
                    "DATABASE_URL is not set. Please configure your database connection."
                )
            if DATABASE_URL.startswith("postgresql://"):
                engine_args = {
                    "pool_size": 5,
                    "max_overflow": 10,
                    "pool_pre_ping": True,
                }

            self.engine = create_engine(DATABASE_URL, **engine_args)
            self.connection = self.engine.connect()
            logger.debug("✅ Connexion à la base de données ouverte")
            return self.connection
        except SQLAlchemyError as e:
            logger.error(f"❌ Échec de l'ouverture de la connexion: {e}")
            raise

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Fermeture propre de la connexion, même en cas d'erreur.

        Args:
            exc_type: Type de l'exception si une erreur s'est produite
            exc_val: Valeur de l'exception
            exc_tb: Traceback de l'exception
        Returns:
            bool: False pour propager les exceptions, True pour les supprimer
        """
        try:
            if self.connection:
                self.connection.close()
                logger.debug("✅ Connexion à la base de données fermée")
            if self.engine:
                self.engine.dispose()
        except SQLAlchemyError as e:
            logger.error(f"❌ Échec de la fermeture de la connexion: {e}")
            # En cas d'erreur à la fermeture, ne pas masquer l'erreur originale
            if exc_type is not None:
                return False
        return True


@contextmanager
def database_session() -> Generator[Any, None, None]:
    """
    Context manager pour les sessions de base de données.
    Utilise SQLAlchemy's sessionmaker pour créer une session et s'assure qu'elle est correctement fermée.

    Yields:
        sqlalchemy.orm.session.Session: Session de base de données
    """
    # Paramètres spécifiques pour PostgreSQL (Supabase)
    engine_args = {}
    if DATABASE_URL.startswith("postgresql://"):
        engine_args = {
            "pool_size": 5,
            "max_overflow": 10,
            "pool_pre_ping": True,
        }

    Session = sessionmaker(bind=create_engine(DATABASE_URL, **engine_args))
    session = Session()

    try:
        logger.debug("✅ Session de base de données ouverte")
        yield session
        session.commit()
        logger.debug("✅ Transactions validées")
    except Exception as e:
        session.rollback()
        logger.error(f"❌ Échec de la session, rollback effectué: {e}")
        raise
    finally:
        session.close()
        logger.debug("✅ Session de base de données fermée")


@contextmanager
def database_transaction() -> Generator[Any, None, None]:
    """
    Context manager pour les transactions de base de données.
    Gère les transactions avec commit/rollback automatique.

    Yields:
        sqlalchemy.engine.Connection: Connexion avec gestion des transactions
    """
    # Paramètres spécifiques pour PostgreSQL (Supabase)
    engine_args = {}
    if DATABASE_URL.startswith("postgresql://"):
        engine_args = {
            "pool_size": 5,
            "max_overflow": 10,
            "pool_pre_ping": True,
        }

    engine = create_engine(DATABASE_URL, **engine_args)
    connection = engine.connect()
    transaction = connection.begin()

    try:
        logger.debug("✅ Transaction de base de données démarrée")
        yield connection
        transaction.commit()
        logger.debug("✅ Transaction validée")
    except Exception as e:
        transaction.rollback()
        logger.error(f"❌ Échec de la transaction, rollback effectué: {e}")
        raise
    finally:
        connection.close()
        engine.dispose()
        logger.debug("✅ Transaction de base de données fermée")
