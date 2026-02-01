"""
Loader pour le pipeline ETL.
"""

import pandas as pd
from datetime import datetime
from typing import Optional, Dict
from sqlalchemy.exc import IntegrityError
from logger_settings import logger
from src.config.settings import ENVIRONMENT


class LoadingError(Exception):
    """Exception levée lors d'un échec de chargement."""

    pass


class OHLCVLoader:
    """
    Loader de données OHLCV pour le pipeline ETL, responsable de la sauvegarde des données transformées en base.
    Compatible avec SQLite et PostgreSQL (Supabase).
    """

    def __init__(self, engine=None, table_name: str = "ohlcv", batch_size: int = 1000):
        """
        Initialise le chargeur avec un moteur SQLAlchemy (optionnel).
        """
        self.engine = engine  # Peut être None si on utilise des context managers
        self.table_name = table_name
        self.batch_size = batch_size
        logger.info(
            f"Chargeur OHLCVLoader initialisé pour la table {table_name} (Environnement: {ENVIRONMENT})"
        )

    def _add_timestamps(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Ajoute les timestamps created_at et updated_at au DataFrame.
        """
        if "created_at" not in df.columns:
            df["created_at"] = datetime.utcnow()
        if "updated_at" not in df.columns:
            df["updated_at"] = datetime.utcnow()
        return df

    def load(self, df: pd.DataFrame, if_exists: str = "append") -> int:
        """
        Charge un DataFrame dans la base de données.
        """
        if df.empty:
            logger.warning(
                "⚠️ Tentative de chargement d'un DataFrame vide (Environnement: {ENVIRONMENT})"
            )
            return 0

        try:
            logger.info(
                f"Chargement de {len(df)} lignes dans {self.table_name} (Environnement: {ENVIRONMENT})"
            )

            # Ajouter les timestamps si nécessaire
            df = self._add_timestamps(df)

            # Utiliser un context manager pour la base de données
            if self.engine:
                # Mode ancien sans context manager
                rows_inserted = df.to_sql(
                    name=self.table_name,
                    con=self.engine,
                    if_exists=if_exists,
                    index=False,
                    method=self._batch_insert if len(df) > self.batch_size else None,
                )
            else:
                # Mode nouveau avec context manager
                from src.services.db_context import database_transaction

                with database_transaction() as db_conn:
                    rows_inserted = df.to_sql(
                        name=self.table_name,
                        con=db_conn,
                        if_exists=if_exists,
                        index=False,
                        method=(
                            self._batch_insert if len(df) > self.batch_size else None
                        ),
                    )

            logger.info(
                f"✅ Chargement réussi: {rows_inserted} lignes insérées (Environnement: {ENVIRONMENT})"
            )
            return rows_inserted

        except IntegrityError as e:
            logger.warning(
                f"⚠️ Conflit de données (doublons) (Environnement: {ENVIRONMENT}): {e}"
            )
            return 0

        except Exception as e:
            error_msg = f"Échec du chargement (Environnement: {ENVIRONMENT}): {e}"
            logger.error(f"❌ {error_msg}")
            raise LoadingError(error_msg) from e

    def _batch_insert(self, table, conn, keys, data_iter):
        """
        Méthode d'insertion par batches pour les grands DataFrames.
        """
        # Utiliser un context manager pour la base de données
        from src.services.db_context import database_transaction

        # Convertir les données en DataFrame
        df = pd.DataFrame(data_iter, columns=keys)

        # Ajouter les timestamps
        df = self._add_timestamps(df)

        # Insérer les données par lots
        total_inserted = 0
        for i in range(0, len(df), self.batch_size):
            batch = df.iloc[i : i + self.batch_size]

            try:
                batch.to_sql(
                    name=table.name,
                    con=conn,
                    if_exists="append",
                    index=False,
                )
                batch_size = len(batch)
                total_inserted += batch_size
                logger.debug(
                    f"Batch {i//self.batch_size + 1}: {batch_size} lignes insérées (Environnement: {ENVIRONMENT})"
                )

            except IntegrityError:
                logger.warning(
                    f"⚠️ Conflit dans le batch {i//self.batch_size + 1} (Environnement: {ENVIRONMENT}), ignoré"
                )
                continue

            except Exception as e:
                logger.error(
                    f"❌ Échec du batch {i//self.batch_size + 1} (Environnement: {ENVIRONMENT}): {e}"
                )
                raise LoadingError(
                    f"Échec du batch {i//self.batch_size + 1} (Environnement: {ENVIRONMENT}): {e}"
                ) from e

        return total_inserted

    def load_batch(
        self, df_batch: Dict[str, pd.DataFrame], if_exists: str = "append"
    ) -> Dict[str, int]:
        """
        Charge un batch de plusieurs DataFrames.
        """
        results = {}

        for symbol, df in df_batch.items():
            if df is not None and not df.empty:
                try:
                    results[symbol] = self.load(df, if_exists)
                except LoadingError as e:
                    logger.error(
                        f"❌ Échec chargement {symbol} (Environnement: {ENVIRONMENT}): {e}"
                    )
                    results[symbol] = 0
            else:
                results[symbol] = 0

        logger.info(f"Chargement par lots terminé (Environnement: {ENVIRONMENT})")
        return results

    def table_exists(self) -> bool:
        """
        Vérifie si la table existe dans la base de données.
        """
        try:
            if self.engine:
                return self.engine.has_table(self.table_name)
            else:
                from src.services.db_context import database_transaction

                with database_transaction() as db_conn:
                    return db_conn.dialect.has_table(db_conn, self.table_name)
        except Exception as e:
            logger.error(
                f"❌ Impossible de vérifier l'existence de la table (Environnement: {ENVIRONMENT}): {e}"
            )
            return False

    def get_table_info(self) -> Optional[dict]:
        """
        Récupère des informations sur la table.
        """
        try:
            if not self.table_exists():
                return None

            if self.engine:
                # Utiliser l'inspection SQLAlchemy
                inspector = (
                    self.engine.connect().execution_options(autocommit=True).connection
                )
                columns = inspector.execute(
                    f"SELECT * FROM {self.table_name} LIMIT 0"
                ).keys()
            else:
                from src.services.db_context import database_transaction

                with database_transaction() as db_conn:
                    inspector = (
                        db_conn.connect().execution_options(autocommit=True).connection
                    )
                    columns = inspector.execute(
                        f"SELECT * FROM {self.table_name} LIMIT 0"
                    ).keys()

            return {"table": self.table_name, "columns": list(columns), "exists": True}

        except Exception as e:
            logger.error(
                f"❌ Impossible de récupérer les informations de la table (Environnement: {ENVIRONMENT}): {e}"
            )
            return None
