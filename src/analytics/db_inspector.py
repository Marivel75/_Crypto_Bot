"""
Module pour inspecter et récupérer des données depuis la base de données.
Encapsule les opérations courantes dans une classe dédiée : DBInspector.
Compatible avec SQLite (développement) et PostgreSQL (Supabase, production).
"""

from typing import Optional, Dict, Any, List
import pandas as pd
from sqlalchemy import text, inspect
from logger_settings import logger
from src.services.db_context import database_session, DatabaseConnection
from src.config.settings import ENVIRONMENT


class DBInspector:
    """
    Classe utilitaire pour inspecter et récupérer des données depuis la base de données.
    Fournit des méthodes pour :
    - Récupérer des données OHLCV ou des snapshots de tickers.
    - Inspecter la structure de la base (tables, colonnes, schémas).
    - Obtenir des métadonnées sur les tables.
    """

    def __init__(self):
        """Initialise l'inspecteur de base de données."""
        logger.info(f"DBInspector initialisé (Environnement: {ENVIRONMENT})")

    def get_ohlcv_data(
        self,
        limit: Optional[int] = None,
        symbol: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Récupère les données OHLCV depuis la base de données.

        Args:
            limit: Limite le nombre de résultats.
            symbol: Filtre par symbole (ex: 'BTC/USDT').
            start_date: Date de début (format: 'YYYY-MM-DD').
            end_date: Date de fin (format: 'YYYY-MM-DD').

        Returns:
            pd.DataFrame: DataFrame contenant les données OHLCV.
        """
        logger.info(f"Récupération des données OHLCV (Environnement: {ENVIRONMENT})")

        query = "SELECT * FROM ohlcv"
        conditions = []
        params: Dict[str, Any] = {}

        if symbol:
            conditions.append("symbol = :symbol")
            params["symbol"] = symbol
        if start_date:
            conditions.append("timestamp >= :start_date")
            params["start_date"] = start_date
        if end_date:
            conditions.append("timestamp <= :end_date")
            params["end_date"] = end_date

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        if limit:
            query += f" LIMIT {limit}"

        try:
            with database_session() as session:
                result = session.execute(text(query), params)
                df = pd.DataFrame(result.fetchall(), columns=result.keys())
                logger.info(
                    f"Données OHLCV récupérées avec succès. Forme: {df.shape} (Environnement: {ENVIRONMENT})"
                )
                return df
        except Exception as e:
            logger.error(
                f"❌ Erreur lors de la récupération des données OHLCV (Environnement: {ENVIRONMENT}): {e}"
            )
            raise

    def inspect_db(self) -> None:
        """
        Affiche la structure de la base de données (tables et colonnes).
        Logue les informations dans le logger configuré.
        """
        logger.info(
            f"Inspection de la structure de la base de données (Environnement: {ENVIRONMENT})"
        )

        try:
            with DatabaseConnection() as conn:
                if ENVIRONMENT == "development":
                    # SQLite
                    self._inspect_sqlite_db(conn)
                else:
                    # PostgreSQL (Supabase)
                    self._inspect_postgresql_db(conn)
        except Exception as e:
            logger.error(
                f"❌ Erreur lors de l'inspection de la base de données (Environnement: {ENVIRONMENT}): {e}"
            )
            raise

    def _inspect_sqlite_db(self, conn):
        """Inspecte une base de données SQLite."""
        # Récupérer les tables
        tables_result = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table';")
        )
        tables = [row[0] for row in tables_result.fetchall()]
        logger.info(
            f"Nombre de tables dans la db : {len(tables)} (Environnement: {ENVIRONMENT})"
        )

        for table in tables:
            # Récupérer les colonnes
            columns_result = conn.execute(text(f"PRAGMA table_info({table})"))
            columns = [row[1] for row in columns_result.fetchall()]  # Nom de la colonne
            logger.info(
                f"Colonnes de la table '{table}': {columns} (Environnement: {ENVIRONMENT})"
            )

            # Compter les lignes
            count_result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
            count = count_result.fetchone()[0]
            logger.info(
                f"Nombre de lignes de la table '{table}' : {count} (Environnement: {ENVIRONMENT})"
            )

    def _inspect_postgresql_db(self, conn):
        """Inspecte une base de données PostgreSQL."""
        inspector = inspect(conn)

        # Récupérer les tables
        tables = inspector.get_table_names()
        logger.info(
            f"Nombre de tables dans la db : {len(tables)} (Environnement: {ENVIRONMENT})"
        )

        for table in tables:
            # Récupérer les colonnes
            columns = inspector.get_columns(table)
            column_names = [col["name"] for col in columns]
            logger.info(
                f"Colonnes de la table '{table}': {column_names} (Environnement: {ENVIRONMENT})"
            )

            # Compter les lignes
            count_result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
            count = count_result.fetchone()[0]
            logger.info(
                f"Nombre de lignes de la table '{table}' : {count} (Environnement: {ENVIRONMENT})"
            )

    def get_table_names(self) -> List[str]:
        """
        Retourne la liste des noms de tables dans la base de données.

        Returns:
            List[str]: Liste des noms de tables.
        """
        try:
            with DatabaseConnection() as conn:
                if ENVIRONMENT == "development":
                    # SQLite
                    result = conn.execute(
                        text("SELECT name FROM sqlite_master WHERE type='table';")
                    )
                else:
                    # PostgreSQL
                    inspector = inspect(conn)
                    result = inspector.get_table_names()

                return (
                    list(result)
                    if ENVIRONMENT != "development"
                    else [row[0] for row in result.fetchall()]
                )
        except Exception as e:
            logger.error(
                f"❌ Erreur lors de la récupération des noms de tables (Environnement: {ENVIRONMENT}): {e}"
            )
            raise

    def get_table_schema(self, table_name: str) -> Dict[str, str]:
        """
        Retourne le schéma d'une table (noms des colonnes et types).

        Args:
            table_name: Nom de la table.

        Returns:
            Dict[str, str]: Dictionnaire avec les noms des colonnes et leurs types.
        """
        try:
            with DatabaseConnection() as conn:
                if ENVIRONMENT == "development":
                    # SQLite
                    result = conn.execute(text(f"PRAGMA table_info({table_name})"))
                    schema = {
                        row[1]: row[2] for row in result.fetchall()
                    }  # {nom_colonne: type}
                else:
                    # PostgreSQL
                    inspector = inspect(conn)
                    columns = inspector.get_columns(table_name)
                    schema = {col["name"]: str(col["type"]) for col in columns}

                logger.info(
                    f"Schéma de la table '{table_name}' récupéré (Environnement: {ENVIRONMENT})"
                )
                return schema
        except Exception as e:
            logger.error(
                f"❌ Erreur lors de la récupération du schéma de la table {table_name} (Environnement: {ENVIRONMENT}): {e}"
            )
            raise

    def get_ticker_snapshots(
        self,
        limit: Optional[int] = None,
        symbol: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Récupère les snapshots de tickers depuis la base de données.

        Args:
            limit: Limite le nombre de résultats.
            symbol: Filtre par symbole (ex: 'BTC/USDT').
            start_date: Date de début (format: 'YYYY-MM-DD').
            end_date: Date de fin (format: 'YYYY-MM-DD').

        Returns:
            pd.DataFrame: DataFrame contenant les snapshots de tickers.
        """
        logger.info(
            f"Récupération des snapshots de tickers (Environnement: {ENVIRONMENT})"
        )

        query = "SELECT * FROM ticker_snapshots"
        conditions = []
        params: Dict[str, Any] = {}

        if symbol:
            conditions.append("symbol = :symbol")
            params["symbol"] = symbol
        if start_date:
            conditions.append("snapshot_time >= :start_date")
            params["start_date"] = start_date
        if end_date:
            conditions.append("snapshot_time <= :end_date")
            params["end_date"] = end_date

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        if limit:
            query += f" LIMIT {limit}"

        try:
            with database_session() as session:
                result = session.execute(text(query), params)
                df = pd.DataFrame(result.fetchall(), columns=result.keys())
                logger.info(
                    f"Snapshots de tickers récupérés avec succès. Forme: {df.shape} (Environnement: {ENVIRONMENT})"
                )
                return df
        except Exception as e:
            logger.error(
                f"❌ Erreur lors de la récupération des snapshots de tickers (Environnement: {ENVIRONMENT}): {e}"
            )
            raise
