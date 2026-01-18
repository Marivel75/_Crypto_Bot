"""
Loader pour le pipeline ETL.
"""

import pandas as pd
from datetime import datetime
from typing import Optional
from sqlalchemy.exc import IntegrityError
from src.config.logger_settings import logger


class LoadingError(Exception):
    """Exception levée lors d'un échec de chargement."""

    pass


class OHLCVLoader:
    """
    Loader de données OHLCV pour le pipeline ETL, responsable de la sauvegarde des données transformées en base.
    """

    def __init__(self, engine=None, table_name: str = "ohlcv", batch_size: int = 1000):
        """
        Initialise le chargeur avec un moteur SQLAlchemy (optionnel).
        """
        self.engine = engine  # Peut être None si on utilise des context managers
        self.table_name = table_name
        self.batch_size = batch_size
        logger.info(f"Chargeur initialisé pour la table {table_name}")

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
            logger.warning("⚠️  Tentative de chargement d'un DataFrame vide")
            return 0

        try:
            logger.info(f"Chargement de {len(df)} lignes dans {self.table_name}")

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

            logger.info(f"✅ Chargement réussi: {rows_inserted} lignes insérées")
            return rows_inserted

        except IntegrityError as e:
            logger.warning(f"⚠️  Conflit de données (doublons): {e}")
            return 0

        except Exception as e:
            error_msg = f"Échec du chargement: {e}"
            logger.error(f"❌ {error_msg}")
            raise LoadingError(error_msg) from e

    def _batch_insert(self, df: pd.DataFrame, table_name: str, **kwargs) -> int:
        """
        Méthode d'insertion par batches pour les grands DataFrames.
        """
        total_inserted = 0

        # Ajouter les timestamps au DataFrame complet avant de le diviser en batches
        df = self._add_timestamps(df)

        # Traite le df par lots de taille `self.batch_size`.
        for i in range(0, len(df), self.batch_size):
            batch = df.iloc[i : i + self.batch_size]

            try:
                if self.engine:
                    # Mode ancien sans context manager
                    batch.to_sql(
                        name=table_name,
                        con=self.engine,
                        if_exists="append",
                        index=False,
                    )
                else:
                    # Mode nouveau avec context manager
                    from src.services.db_context import database_transaction

                    with database_transaction() as db_conn:
                        batch.to_sql(
                            name=table_name,
                            con=db_conn,
                            if_exists="append",
                            index=False,
                        )
                batch_size = len(batch)
                total_inserted += batch_size
                logger.debug(
                    f"Batch {i//self.batch_size + 1}: {batch_size} lignes insérées"
                )

            except IntegrityError:
                logger.warning(
                    f"⚠️  Conflit dans le batch {i//self.batch_size + 1}, ignoré"
                )
                continue

            except Exception as e:
                logger.error(f"❌ Échec du batch {i//self.batch_size + 1}: {e}")
                raise LoadingError(
                    f"Échec du batch {i//self.batch_size + 1}: {e}"
                ) from e

        return total_inserted

    def load_batch(self, df_batch: dict, if_exists: str = "append") -> dict:
        """
        Charge un batch de plusieurs DataFrames.
        """
        results = {}

        for symbol, df in df_batch.items():
            if df is not None:
                try:
                    results[symbol] = self.load(df, if_exists)
                except LoadingError as e:
                    logger.error(f"❌ Échec chargement {symbol}: {e}")
                    results[symbol] = 0
            else:
                results[symbol] = 0

        return results

    def table_exists(self) -> bool:
        """
        Vérifie si la table existe dans la base de données.
        """
        try:
            return self.engine.has_table(self.table_name)
        except Exception as e:
            logger.error(f"❌ Impossible de vérifier l'existence de la table: {e}")
            return False

    def get_table_info(self) -> Optional[dict]:
        """
        Récupère des informations sur la table.
        """
        try:
            if not self.table_exists():
                return None

            # Utiliser l'inspection SQLAlchemy
            inspector = (
                self.engine.connect().execution_options(autocommit=True).connection
            )
            columns = inspector.execute(
                f"SELECT * FROM {self.table_name} LIMIT 0"
            ).keys()

            return {"table": self.table_name, "columns": list(columns), "exists": True}

        except Exception as e:
            logger.error(
                f"❌ Impossible de récupérer les informations de la table: {e}"
            )
            return None
