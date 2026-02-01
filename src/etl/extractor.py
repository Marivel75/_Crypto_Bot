"""
Module d'extraction des données OHLCV depuis les exchanges.
Fait partie du pipeline ETL pour les données de marché.
"""

import pandas as pd
from typing import List, Dict, Optional
from logger_settings import logger
from src.config.settings import ENVIRONMENT


class OHLCVExtractor:
    """
    Classe pour extraire les données OHLCV depuis les exchanges.
    Utilise un client d'exchange pour récupérer les données brutes.
    """

    def __init__(self, client):
        """
        Initialise l'extracteur avec un client d'exchange.

        Args:
            client: Client d'exchange (Binance, Kraken, Coinbase)
        """
        self.client = client
        logger.info(f"OHLCVExtractor initialisé (Environnement: {ENVIRONMENT})")

    def extract_ohlcv_data(
        self, pairs: List[str], timeframe: str, limit: int = 1000
    ) -> Dict[str, pd.DataFrame]:
        """
        Extrait les données OHLCV pour les paires et le timeframe spécifiés.

        Args:
            pairs: Liste des paires de trading (ex: ["BTC/USDT", "ETH/USDT"])
            timeframe: Timeframe (ex: "1h", "4h", "1d")
            limit: Nombre maximum de bougies à récupérer

        Returns:
            Dict[str, pd.DataFrame]: Dictionnaire avec les données OHLCV par paire
        """
        logger.info(
            f"Extraction des données OHLCV pour {len(pairs)} paires, timeframe: {timeframe} (Environnement: {ENVIRONMENT})"
        )

        ohlcv_data = {}

        for pair in pairs:
            try:
                logger.debug(f"Extraction des données pour {pair} ({timeframe})")
                data = self.client.fetch_ohlcv(pair, timeframe, limit=limit)

                if data and len(data) > 0:
                    # Convertir les données en DataFrame
                    df = pd.DataFrame(
                        data,
                        columns=[
                            "timestamp",
                            "open",
                            "high",
                            "low",
                            "close",
                            "volume",
                        ],
                    )

                    # Ajouter des métadonnées
                    df["symbol"] = pair
                    df["timeframe"] = timeframe
                    df["exchange"] = self.client.exchange_name

                    ohlcv_data[pair] = df
                    logger.debug(f"Données extraites pour {pair}: {len(df)} bougies")
                else:
                    logger.warning(
                        f"Aucune donnée disponible pour {pair} ({timeframe})"
                    )
                    ohlcv_data[pair] = pd.DataFrame()  # DataFrame vide

            except Exception as e:
                logger.error(f"Erreur lors de l'extraction pour {pair}: {e}")
                ohlcv_data[pair] = pd.DataFrame()  # DataFrame vide en cas d'erreur

        logger.info(f"Extraction terminée: {len(ohlcv_data)} paires traitées")
        return ohlcv_data

    def extract_batch(
        self, pairs: List[str], timeframes: List[str], limit: int = 1000
    ) -> Dict[str, Dict[str, pd.DataFrame]]:
        """
        Extrait les données OHLCV pour plusieurs paires et timeframes.

        Args:
            pairs: Liste des paires de trading
            timeframes: Liste des timeframes
            limit: Nombre maximum de bougies par requête

        Returns:
            Dict[str, Dict[str, pd.DataFrame]]: Dictionnaire imbriqué avec les données par timeframe et paire
        """
        logger.info(
            f"Extraction par lots pour {len(pairs)} paires et {len(timeframes)} timeframes (Environnement: {ENVIRONMENT})"
        )

        batch_data = {}

        for timeframe in timeframes:
            logger.debug(f"Traitement du timeframe: {timeframe}")
            timeframe_data = self.extract_ohlcv_data(pairs, timeframe, limit)
            batch_data[timeframe] = timeframe_data

        logger.info(
            f"Extraction par lots terminée: {len(batch_data)} timeframes traités"
        )
        return batch_data
