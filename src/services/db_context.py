"""
Module de gestion des connexions à la base de données avec context managers. Fournit des classes pour gérer les ressources de base de données.
"""

from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from src.config.logger_settings import logger
from config.settings import config
from typing import Generator, Any


class DatabaseConnection:
    """
    Context manager pour la gestion des connexions database, garantit que les connexions à la base de données sont correctement ouvertes et fermées, même en cas d'erreur.
    """

    def __init__(self):
        self.engine = None
        self.connection = None
        self.db_url = config.get("database.url")

    def __enter__(self):
        """
        Ouvre la connexion à la base de données.
        Returns:
            sqlalchemy.engine.Connection: Connexion à la base de données
        """
        try:
            self.engine = create_engine(self.db_url)
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
    Context manager pour les sessions de base de données, utilise SQLAlchemy's sessionmaker pour créer une session et s'assure qu'elle est correctement fermée.

    Yields:
        sqlalchemy.orm.session.Session: Session de base de données
    """
    from sqlalchemy.orm import sessionmaker

    Session = sessionmaker(bind=create_engine(config.get("database.url")))
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
    Context manager pour les transactions de base de données, gère les transactions avec commit/rollback automatique.

    Yields:
        sqlalchemy.engine.Connection: Connexion avec gestion des transactions
    """
    engine = create_engine(config.get("database.url"))
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
