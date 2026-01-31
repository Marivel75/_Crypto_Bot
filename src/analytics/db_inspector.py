"""
Module pour inspecter et récupérer des données depuis la base de données.
Encapsule les opérations courantes dans une classe dédiée : DBInspector.
"""

from typing import Optional, Dict, Any, List
import pandas as pd
from sqlalchemy import text
from logger_settings import logger
from src.services.db_context import database_session, DatabaseConnection


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
        logger.debug("Initialisation de DBInspector")

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

        Raises:
            Exception: En cas d'erreur lors de la requête.
        """
        logger.info("Récupération des données OHLCV depuis la base de données...")

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
                logger.info(f"Données OHLCV récupérées avec succès. Forme: {df.shape}")
                return df
        except Exception as e:
            logger.error(f"❌ Erreur lors de la récupération des données OHLCV: {e}")
            raise

    def inspect_db(self) -> None:
        """
        Affiche la structure de la base de données (tables et colonnes).
        Logue les informations dans le logger configuré.
        """
        logger.info("Inspection de la structure de la base de données...")

        try:
            with DatabaseConnection() as conn:
                # Récupérer les tables
                tables_result = conn.execute(
                    text("SELECT name FROM sqlite_master WHERE type='table';")
                )
                tables = [row[0] for row in tables_result.fetchall()]
                logger.info(f"Nombre de tables dans la db : {len(tables)}")

                for table in tables:
                    # Récupérer les colonnes
                    columns_result = conn.execute(text(f"PRAGMA table_info({table})"))
                    columns = [
                        row[1] for row in columns_result.fetchall()
                    ]  # Nom de la colonne
                    logger.info(f"Colonnes de la table '{table}': {columns}")

                    # Compter les lignes
                    count_result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    count = count_result.fetchone()[0]
                    logger.info(f"Nombre de lignes de la table '{table}' : {count}")

        except Exception as e:
            logger.error(f"❌ Erreur lors de l'inspection de la base de données: {e}")
            raise

    def get_table_names(self) -> List[str]:
        """
        Retourne la liste des noms de tables dans la base de données.

        Returns:
            List[str]: Liste des noms de tables.

        Raises:
            Exception: En cas d'erreur lors de la requête.
        """
        try:
            with DatabaseConnection() as conn:
                result = conn.execute(
                    text("SELECT name FROM sqlite_master WHERE type='table';")
                )
                return [row[0] for row in result.fetchall()]
        except Exception as e:
            logger.error(f"❌ Erreur lors de la récupération des noms de tables: {e}")
            raise

    def get_table_schema(self, table_name: str) -> Dict[str, str]:
        """
        Retourne le schéma d'une table (noms des colonnes et types).

        Args:
            table_name: Nom de la table.

        Returns:
            Dict[str, str]: Dictionnaire avec les noms des colonnes et leurs types.

        Raises:
            Exception: En cas d'erreur lors de la requête.
        """
        try:
            with DatabaseConnection() as conn:
                result = conn.execute(text(f"PRAGMA table_info({table_name})"))
                schema = {
                    row[1]: row[2] for row in result.fetchall()
                }  # {nom_colonne: type}
                return schema
        except Exception as e:
            logger.error(
                f"❌ Erreur lors de la récupération du schéma de la table {table_name}: {e}"
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
            "Récupération des snapshots de tickers depuis la base de données..."
        )

        query = "SELECT * FROM ticker_snapshots"
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
                    f"Snapshots de tickers récupérés avec succès. Forme: {df.shape}"
                )
                return df
        except Exception as e:
            logger.error(
                f"❌ Erreur lors de la récupération des snapshots de tickers: {e}"
            )
            raise
