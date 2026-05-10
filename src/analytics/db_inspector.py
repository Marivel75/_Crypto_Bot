"""
Module pour inspecter et récupérer des données depuis la base de données.
Encapsule les opérations courantes dans une classe dédiée : DBInspector.
"""

from typing import Optional, Dict, Any, List
import pandas as pd
from datetime import datetime
from sqlalchemy import create_engine, inspect as sa_inspect, text
from logger_settings import logger
from config.settings import config
from src.services.db_context import database_session, DatabaseConnection, _engine_kwargs


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
        _url = config.get("database.url")
        self._engine = create_engine(_url, **_engine_kwargs(_url))
        self._inspector = sa_inspect(self._engine)

    def _build_ohlcv_query(
        self,
        symbol: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> tuple[str, Dict[str, Any]]:
        """
        Construit la requête SQL et les paramètres pour récupérer les données OHLCV.

        Args:
            symbol: Filtre par symbole (ex: 'BTC/USDT')
            start_date: Date de début (format: 'YYYY-MM-DD')
            end_date: Date de fin (format: 'YYYY-MM-DD')
            limit: Limite le nombre de résultats

        Returns:
            tuple: (requête SQL, dictionnaire des paramètres)
        """
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

        return query, params

    def _execute_ohlcv_query(self, query: str, params: Dict[str, Any]) -> pd.DataFrame:
        """
        Exécute une requête OHLCV et retourne les résultats sous forme de DataFrame.

        Args:
            query: Requête SQL à exécuter
            params: Paramètres de la requête

        Returns:
            pd.DataFrame: Résultats de la requête

        Raises:
            Exception: En cas d'erreur lors de la requête
        """
        try:
            with database_session() as session:
                result = session.execute(text(query), params)
                df = pd.DataFrame(result.fetchall(), columns=result.keys())
                logger.info(f"Données OHLCV récupérées avec succès. Forme: {df.shape}")
                return df
        except Exception as e:
            logger.error(f"❌ Erreur lors de la récupération des données OHLCV: {e}")
            raise

    def get_ohlcv_data_for_symbol(
        self,
        symbol: str,
        limit: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Récupère les données OHLCV pour un symbole spécifique.

        Args:
            symbol: Symbole à récupérer (ex: 'BTC/USDT')
            limit: Limite le nombre de résultats
            start_date: Date de début (format: 'YYYY-MM-DD')
            end_date: Date de fin (format: 'YYYY-MM-DD')

        Returns:
            pd.DataFrame: DataFrame contenant les données OHLCV pour le symbole

        Raises:
            Exception: En cas d'erreur lors de la requête
        """
        logger.info(f"Récupération des données OHLCV pour le symbole {symbol}...")

        query, params = self._build_ohlcv_query(
            symbol=symbol, start_date=start_date, end_date=end_date, limit=limit
        )

        return self._execute_ohlcv_query(query, params)

    def get_all_ohlcv_data(
        self,
        limit: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Récupère toutes les données OHLCV de la base de données.

        Args:
            limit: Limite le nombre de résultats
            start_date: Date de début (format: 'YYYY-MM-DD')
            end_date: Date de fin (format: 'YYYY-MM-DD')

        Returns:
            pd.DataFrame: DataFrame contenant toutes les données OHLCV

        Raises:
            Exception: En cas d'erreur lors de la requête
        """
        logger.info("Récupération de toutes les données OHLCV...")

        query, params = self._build_ohlcv_query(
            start_date=start_date, end_date=end_date, limit=limit
        )

        return self._execute_ohlcv_query(query, params)

    def inspect_db(self) -> None:
        """
        Affiche la structure de la base de données (tables et colonnes).
        Logue les informations dans le logger configuré.
        """
        logger.info("Inspection de la structure de la base de données...")

        try:
            tables = self._inspector.get_table_names()
            logger.info(f"Nombre de tables dans la db : {len(tables)}")

            with self._engine.connect() as conn:
                for table in tables:
                    columns = [col["name"] for col in self._inspector.get_columns(table)]
                    logger.info(f"Colonnes de la table '{table}': {columns}")
                    count = conn.execute(text(f'SELECT COUNT(*) FROM "{table}"')).scalar()
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
            return self._inspector.get_table_names()
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
            return {
                col["name"]: str(col["type"])
                for col in self._inspector.get_columns(table_name)
            }
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

    def get_db_stats(self) -> Optional[Dict[str, Any]]:
        """
        Récupère des statistiques globales sur la base de données.

        Returns:
            Dict[str, Any]: Statistiques complètes de la base de données
        """
        try:
            tables = self._inspector.get_table_names()
            table_stats = {}
            total_rows = 0

            for table_name in tables:
                table_info = self._get_table_info_detailed(table_name)
                if table_info:
                    table_stats[table_name] = table_info
                    total_rows += table_info["row_count"]

            return {
                "table_count": len(table_stats),
                "total_rows": total_rows,
                "total_size_bytes": total_rows * 1024,  # estimation
                "tables": table_stats,
            }

        except Exception as e:
            logger.error(
                f"❌ Erreur lors de la récupération des statistiques de la base de données: {e}"
            )
            return None

    def _get_table_info_detailed(self, table_name: str) -> Optional[Dict[str, Any]]:
        """
        Récupère des informations détaillées sur une table spécifique.

        Args:
            table_name: Nom de la table

        Returns:
            Dict[str, Any]: Informations détaillées sur la table
        """
        try:
            with DatabaseConnection() as conn:
                # Compter le nombre de lignes
                result = conn.execute(
                    text(f"SELECT COUNT(*) as count FROM {table_name}")
                )
                row_count = result.fetchone()[0]

                # Récupérer la structure de la table
                col_defs = self._inspector.get_columns(table_name)
                column_names = [col["name"] for col in col_defs]
                columns = col_defs  # pour len()

                # Récupérer la dernière mise à jour
                last_update = None
                if "timestamp" in column_names:
                    result = conn.execute(
                        text(f"SELECT MAX(timestamp) as last_update FROM {table_name}")
                    )
                elif "snapshot_time" in column_names:
                    result = conn.execute(
                        text(
                            f"SELECT MAX(snapshot_time) as last_update FROM {table_name}"
                        )
                    )
                elif "created_at" in column_names:
                    result = conn.execute(
                        text(f"SELECT MAX(created_at) as last_update FROM {table_name}")
                    )

                result_row = result.fetchone()
                if result_row and result_row[0]:
                    last_update = result_row[0]

                # Estimation de la taille (1KB par ligne en moyenne)
                table_size = row_count * 1024

                return {
                    "table_name": table_name,
                    "row_count": row_count,
                    "column_count": len(columns),
                    "columns": column_names,
                    "last_update": last_update,
                    "table_size_bytes": table_size,
                }

        except Exception as e:
            logger.error(
                f"❌ Erreur lors de la récupération des informations pour {table_name}: {e}"
            )
            return None

    def format_bytes(self, size_bytes: int) -> str:
        """
        Formate la taille en bytes dans une unité plus lisible.

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

    def print_db_summary(self, stats: Optional[Dict[str, Any]] = None) -> None:
        """
        Affiche un résumé des statistiques de la base de données.

        Args:
            stats: Statistiques (si None, les récupère automatiquement)
        """
        if not stats:
            stats = self.get_db_stats()

        if not stats:
            logger.warning("⚠️  Aucune statistique disponible")
            return

        logger.info("📊 Résumé de la base de données:")
        logger.info(f"   Nombre de tables: {stats['table_count']}")
        logger.info(f"   Nombre total de lignes: {stats['total_rows']:,}")
        logger.info(
            f"   Taille totale de la base: {self.format_bytes(stats['total_size_bytes'])}"
        )
        logger.info("")

        for table_name, table_info in stats["tables"].items():
            logger.info(f"📋 Table: {table_name}")
            logger.info(f"   Lignes: {table_info['row_count']:,}")
            logger.info(f"   Colonnes: {table_info['column_count']}")
            logger.info(
                f"   Taille: {self.format_bytes(table_info['table_size_bytes'])}"
            )

            if table_info["last_update"]:
                last_update_str = table_info["last_update"]
                if isinstance(last_update_str, str):
                    try:
                        last_update = datetime.strptime(
                            last_update_str, "%Y-%m-%d %H:%M:%S"
                        )
                    except ValueError:
                        last_update = last_update_str
                else:
                    last_update = table_info["last_update"]

                logger.info(f"   Dernière mise à jour: {last_update}")
            else:
                logger.info(f"   Dernière mise à jour: Non disponible")

            logger.info("")

    def check_db_health(self) -> Optional[Dict[str, Any]]:
        """
        Vérifie la santé générale de la base de données.

        Returns:
            Dict[str, Any]: Indicateurs de santé de la base de données
        """
        try:
            # Vérification de la connexion (portable SQLite + PostgreSQL)
            with self._engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            integrity_ok = True

            existing_tables = set(self._inspector.get_table_names())
            required_tables = ["ohlcv", "ticker_snapshots"]

            return {
                "integrity_ok": integrity_ok,
                "tables_present": {t: t in existing_tables for t in required_tables},
            }

        except Exception as e:
            logger.error(
                f"❌ Erreur lors de la vérification de la santé de la base de données: {e}"
            )
            return None

    def print_health_summary(self, health: Optional[Dict[str, Any]] = None) -> None:
        """
        Affiche un résumé de la santé de la base de données.

        Args:
            health: Indicateurs de santé (si None, les récupère automatiquement)
        """
        if not health:
            health = self.check_db_health()

        if not health:
            logger.warning("⚠️  Aucune information de santé disponible")
            return

        logger.info("Santé de la base de données:")

        if health["integrity_ok"]:
            logger.info("   ✅ Intégrité de la base: OK")
        else:
            logger.error("   ❌ Intégrité de la base: PROBLÈME DÉTECTÉ")

        logger.info("   Tables principales:")
        for table, present in health["tables_present"].items():
            if present:
                logger.info(f"      ✅ {table}: Présente")
            else:
                logger.warning(f"      ⚠️  {table}: Absente")

        logger.info("")

    def run_complete_check(self) -> None:
        """
        Exécute une vérification complète de la base de données.
        Combine inspection, statistiques et vérification de santé.
        """
        try:
            logger.info(
                "🔍 Démarrage de la vérification complète de la base de données"
            )

            # Inspection de la structure
            self.inspect_db()

            # Statistiques détaillées
            stats = self.get_db_stats()
            if stats:
                self.print_db_summary(stats)

            # Vérification de la santé
            health = self.check_db_health()
            if health:
                self.print_health_summary(health)

            logger.info("✅ Vérification complète de la base de données terminée")

        except Exception as e:
            logger.error(f"❌ Erreur lors de la vérification complète: {e}")
            raise
