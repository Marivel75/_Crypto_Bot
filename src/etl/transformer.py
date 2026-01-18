"""
Module Transformer pour le pipeline ETL
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from datetime import datetime
from src.config.logger_settings import logger
from src.quality.validator import DataValidator0HCLV


class TransformationError(Exception):
    """Exception levée lors d'un échec de transformation."""

    pass


class OHLCVTransformer:
    """
    Transformeur de données OHLCV pour le pipeline ETL.
    Tâches :
    - Conversion des données brutes en DataFrame
    - Ajout des métadonnées (symbol, timeframe, exchange)
    - Validation des données avec DataValidator0HCLV
    - Enrichissement des données (calculs d'indicateurs)
    - Normalisation des formats
    """

    def __init__(self, validator: DataValidator0HCLV, exchange: str = "binance"):
        """
        Initialise le transformeur avec un valideur et un exchange.
        """
        self.validator = validator
        self.exchange = exchange
        logger.info(f"Transformeur initialisé pour {exchange}")

    def transform(
        self, raw_data: List[List], symbol: str, timeframe: str
    ) -> pd.DataFrame:
        """
        Transforme les données OHLCV brutes en DataFrame validé et enrichi.
        """
        try:
            # Étape 1: Conversion en DataFrame
            logger.info(
                f"Transformation de {len(raw_data)} bougies pour {symbol} {timeframe}"
            )
            df = self._to_dataframe(raw_data)

            # Étape 2: Ajout des métadonnées
            df = self._add_metadata(df, symbol, timeframe)

            # Étape 3: Conversion des timestamps
            df = self._convert_timestamps(df)

            # Étape 4: Validation des données (le validator attend un df pandas)
            is_valid, validation_report = self.validator.validate_ohlcv_values(df)

            if not is_valid:
                error_details = ", ".join(validation_report["errors"][:3])
                if len(validation_report["errors"]) > 3:
                    error_details += (
                        f", ... et {len(validation_report['errors']) - 3} autres"
                    )
                raise TransformationError(
                    f"Données invalides pour {symbol} {timeframe}: {error_details}"
                )

            # Étape 5: Enrichissement (calculs d'indicateurs)
            df = self._enrich_data(df)

            # Étape 6: Normalisation finale
            df = self._normalize_data(df)

            logger.info(f"✅ Transformation réussie: {len(df)} lignes valides")
            return df

        except Exception as e:
            logger.error(f"❌ Échec de la transformation: {e}")
            raise TransformationError(f"Échec de la transformation: {e}") from e

    def _to_dataframe(self, raw_data: List[List]) -> pd.DataFrame:
        """
        Convertit les données brutes en DataFrame pandas.
        """
        if not raw_data or len(raw_data) == 0:
            raise TransformationError("Aucune donnée à transformer")

        # Colonnes CCXT: [timestamp, open, high, low, close, volume]
        df = pd.DataFrame(
            raw_data, columns=["timestamp", "open", "high", "low", "close", "volume"]
        )

        logger.debug(f"DataFrame créé: {df.shape}")
        return df

    def _add_metadata(
        self, df: pd.DataFrame, symbol: str, timeframe: str
    ) -> pd.DataFrame:
        """
        Ajoute les métadonnées au DataFrame.
        """
        df = df.copy()

        # Générer des UUIDs uniques pour chaque ligne
        import uuid

        df["id"] = [str(uuid.uuid4()) for _ in range(len(df))]

        df["symbol"] = symbol
        df["timeframe"] = timeframe
        df["exchange"] = self.exchange

        logger.debug(f"Métadonnées ajoutées: {symbol}, {timeframe}, {self.exchange}")
        return df

    def _convert_timestamps(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Convertit les timestamps en datetime.
        """
        df = df.copy()

        # Conversion depuis millisecondes (format CCXT)
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")

        # Ajout d'une colonne de date pour facilitée les requêtes
        df["date"] = df["timestamp"].dt.date

        logger.debug(
            f"Timestamps convertis: {df['timestamp'].min()} à {df['timestamp'].max()}"
        )
        return df

    def _enrich_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Enrichit les données avec des calculs d'indicateurs techniques.
        1. Calcul de l'amplitude de prix (high - low)
        2. Calcul de la variation de prix (close - open)
        3. Calcul du pourcentage de variation de prix
        4. (Optionnel) Ajout d'indicateurs techniques avancés
        """
        df = df.copy()

        # Calculs de base
        df["price_range"] = df["high"] - df["low"]  # Amplitude de prix
        df["price_change"] = df["close"] - df["open"]  # Variation de prix
        df["price_change_pct"] = (
            df["price_change"] / df["open"]
        ) * 100  # Variation en %

        # TODO: Ajouter des indicateurs techniques avancés
        # df = self._calculate_sma(df, window=50)
        # df = self._calculate_rsi(df, window=14)
        # df = self._calculate_macd(df)

        logger.debug(f"📊 Données enrichies avec {len(df.columns)} colonnes")
        return df

    def _normalize_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalise les données pour le stockage.
        """
        df = df.copy()

        # Conversion des types pour optimiser le stockage
        float_cols = [
            "open",
            "high",
            "low",
            "close",
            "volume",
            "price_range",
            "price_change",
            "price_change_pct",
        ]
        for col in float_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        # Tri par timestamp (pour la cohérence)
        df = df.sort_values("timestamp").reset_index(drop=True)

        logger.debug(f"Données normalisées: {df.dtypes.to_dict()}")
        return df

    def transform_batch(
        self, raw_data_batch: Dict[str, List[List]], timeframe: str
    ) -> Dict[str, pd.DataFrame]:
        """
        Transforme un batch de données pour plusieurs symboles.
        """
        results = {}

        for symbol, raw_data in raw_data_batch.items():
            if raw_data is not None:
                try:
                    results[symbol] = self.transform(raw_data, symbol, timeframe)
                except TransformationError as e:
                    logger.error(f"❌ Échec transformation {symbol}: {e}")
                    results[symbol] = None
            else:
                results[symbol] = None

        return results

    # Méthodes pour les indicateurs techniques (à implémenter)
    def _calculate_sma(self, df: pd.DataFrame, window: int = 50) -> pd.DataFrame:
        """Calcule la moyenne mobile simple (à implémenter)."""
        # df[f"sma_{window}"] = df["close"].rolling(window).mean()
        return df

    def _calculate_rsi(self, df: pd.DataFrame, window: int = 14) -> pd.DataFrame:
        """Calcule le RSI (à implémenter)."""
        # Implémentation standard du RSI
        return df

    def _calculate_macd(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcule le MACD (à implémenter)."""
        # Implémentation standard du MACD
        return df
