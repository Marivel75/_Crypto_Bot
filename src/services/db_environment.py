"""
Module de configuration pour gérer plusieurs environnements de base de données.
Permet de séparer la base de production de la base de tests.
"""

import os
from typing import Optional
from pathlib import Path
from logger_settings import logger


class DatabaseEnvironment:
    """
    Gestionnaire d'environnements de base de données.
    Permet de basculer entre production et tests.
    """

    # Types d'environnements
    PRODUCTION = "production"
    TESTING = "testing"

    def __init__(self):
        """Initialise le gestionnaire d'environnements."""
        self.current_env = self._detect_environment()
        self.db_urls = self._get_database_urls()
        logger.info(f"Environnement DB actuel: {self.current_env}")

    def _detect_environment(self) -> str:
        """
        Détecte l'environnement actuel depuis les variables d'environnement.

        Priority:
        1. Variable d'environnement CRYPTO_BOT_ENV
        2. Argument de ligne de commande --test-env
        3. Par défaut: PRODUCTION

        Returns:
            str: Type d'environnement (PRODUCTION ou TESTING)
        """
        # 1. Variable d'environnement
        env_var = os.getenv("CRYPTO_BOT_ENV", "").lower()
        if env_var in [self.PRODUCTION, self.TESTING]:
            logger.info(f"Environnement détecté depuis CRYPTO_BOT_ENV: {env_var}")
            return env_var

        # 2. Variable d'environnement alternative
        test_var = os.getenv("CRYPTO_BOT_TEST", "false").lower()
        if test_var in ["true", "1", "yes"]:
            logger.info("Mode testing détecté depuis CRYPTO_BOT_TEST")
            return self.TESTING

        # 3. Par défaut: production
        logger.info("Environnement par défaut: PRODUCTION")
        return self.PRODUCTION

    def _get_database_urls(self) -> dict:
        """
        Configure les URLs de base de données pour chaque environnement.

        Returns:
            dict: Mapping environnement -> URL de base de données
        """
        base_path = Path("data")

        return {
            self.PRODUCTION: f"sqlite:///{base_path}/production/crypto_data.db",
            self.TESTING: f"sqlite:///{base_path}/testing/crypto_data_test.db",
        }

    def get_current_db_url(self) -> str:
        """
        Retourne l'URL de base de données pour l'environnement actuel.

        Returns:
            str: URL de base de données SQLAlchemy
        """
        return self.db_urls[self.current_env]

    def get_db_url(self, environment: Optional[str] = None) -> str:
        """
        Retourne l'URL de base de données pour un environnement spécifié.

        Args:
            environment: Environnement cible (si None, utilise l'environnement actuel)

        Returns:
            str: URL de base de données SQLAlchemy
        """
        if environment is None:
            environment = self.current_env

        if environment not in self.db_urls:
            raise ValueError(f"Environnement non valide: {environment}")

        return self.db_urls[environment]

    def set_environment(self, environment: str) -> None:
        """
        Change l'environnement actuel.

        Args:
            environment: Nouvel environnement (PRODUCTION ou TESTING)
        """
        if environment not in [self.PRODUCTION, self.TESTING]:
            raise ValueError(f"Environnement non valide: {environment}")

        old_env = self.current_env
        self.current_env = environment
        logger.info(f"Environnement changé: {old_env} -> {environment}")

    def ensure_directories(self) -> None:
        """
        Crée les répertoires nécessaires pour toutes les bases de données.
        """
        for url in self.db_urls.values():
            if url.startswith("sqlite:///"):
                db_path = url.replace("sqlite:///", "")
                db_dir = os.path.dirname(db_path)
                os.makedirs(db_dir, exist_ok=True)
                logger.debug(f"Répertoire assuré: {db_dir}")

    def get_database_info(self) -> dict:
        """
        Retourne des informations sur la configuration actuelle.

        Returns:
            dict: Informations détaillées
        """
        return {
            "current_environment": self.current_env,
            "current_url": self.get_current_db_url(),
            "production_url": self.db_urls[self.PRODUCTION],
            "testing_url": self.db_urls[self.TESTING],
            "is_production": self.current_env == self.PRODUCTION,
            "is_testing": self.current_env == self.TESTING,
        }

    def list_databases(self) -> dict:
        """
        Liste les fichiers de base de données existants.

        Returns:
            dict: Informations sur les bases existantes
        """
        databases = {}

        for env, url in self.db_urls.items():
            if url.startswith("sqlite:///"):
                db_path = url.replace("sqlite:///", "")
                exists = os.path.exists(db_path)
                size = 0

                if exists:
                    try:
                        size = os.path.getsize(db_path)
                    except OSError:
                        size = 0

                databases[env] = {
                    "path": db_path,
                    "exists": exists,
                    "size_bytes": size,
                    "size_formatted": self._format_bytes(size),
                }

        return databases

    def _format_bytes(self, size_bytes: int) -> str:
        """
        Formate la taille en bytes dans une unité lisible.

        Args:
            size_bytes: Taille en bytes

        Returns:
            str: Taille formatée
        """
        if size_bytes == 0:
            return "0 bytes"

        size_names = ["bytes", "KB", "MB", "GB", "TB"]
        i = 0
        size = float(size_bytes)

        while size >= 1024 and i < len(size_names) - 1:
            size /= 1024
            i += 1

        return f"{size:.2f} {size_names[i]}"


# Singleton global pour l'environnement de base de données
db_env = DatabaseEnvironment()
