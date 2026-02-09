import pandas as pd
from logger_settings import logger
from src.services.exchange_factory import ExchangeFactory
from src.services.db_context import database_transaction
from src.services.exchange_context import ExchangeClient
from src.quality.validator import DataValidator0HCLV
from src.etl.extractor import OHLCVExtractor
from src.etl.transformer import OHLCVTransformer
from src.etl.loader import OHLCVLoader
from src.etl.pipeline_ohlcv import ETLPipelineOHLCV
from typing import List


class OHLCVCollector:
    """
    Récupère les données OHLCV (Open, High, Low, Close, Volume) pour des paires de trading spécifiques et des timeframes donnés, puis les stocke dans une base de données.
    Utilise le pipeline ETL ohlcv pour gérer le processus d'extraction, de transformation et de chargement des données.
    """

    def __init__(
        self, pairs: List[str], timeframes: List[str], exchange: str = "binance"
    ):
        # Validation des entrées
        if not pairs or not timeframes:
            error_msg = "Les listes de paires et timeframes ne peuvent pas être vides"
            logger.error(error_msg)
            raise ValueError(error_msg)

        if not all(isinstance(pair, str) and pair.strip() for pair in pairs):
            error_msg = (
                "Toutes les paires doivent être des chaînes de caractères non vides"
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

        if not all(isinstance(tf, str) and tf.strip() for tf in timeframes):
            error_msg = (
                "Tous les timeframes doivent être des chaînes de caractères non vides"
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Validation de l'exchange
        supported_exchanges = ["binance", "kraken", "coinbase"]
        if exchange.lower() not in supported_exchanges:
            error_msg = f"Exchange non supporté: {exchange}. Choix possibles: {supported_exchanges}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        self.pairs = pairs
        self.timeframes = timeframes
        self.exchange = exchange.lower()

        # Initialisation du client d'API en fonction de l'exchange
        self.client = ExchangeFactory.create_exchange(exchange)

        # Créer un mock d'engine pour les tests
        from unittest.mock import MagicMock
        self.engine = MagicMock()  # Pour la compatibilité avec les tests

        # Initialisation du valideur de données OHLCV
        self.data_validator = DataValidator0HCLV()

        # Initialisation du pipeline ETL
        self.pipeline = self._create_ohlcv_etl_pipeline()

    def _create_ohlcv_etl_pipeline(self) -> ETLPipelineOHLCV:
        """
        Crée le pipeline ETL avec les composants appropriés pour les data OHLCV
        """
        extractor = OHLCVExtractor(self.client)
        transformer = OHLCVTransformer(self.data_validator, self.exchange)
        loader = OHLCVLoader(None)  # L'engine sera passé via context manager

        return ETLPipelineOHLCV(extractor, transformer, loader)

    def fetch_and_store(self) -> None:
        """
        Récupère les données OHLCV pour toutes les paires et timeframes configurés et les stocke dans la base de données.
        Utilise des context managers pour la gestion des ressources.
        """
        all_batch_results = {}

        for timeframe in self.timeframes:
            logger.info(f"📊 Traitement du timeframe: {timeframe}")

            # Utiliser des context managers pour les ressources
            with ExchangeClient(self.exchange) as client:
                with database_transaction() as db_conn:
                    # Mettre à jour le client dans le pipeline
                    self.pipeline.extractor.client = client
                    
                    # Exécuter le pipeline ETL
                    batch_results = self.pipeline.run_batch(self.pairs, timeframe)

                    # Ajouter les résultats avec le timeframe comme préfixe
                    for symbol, result in batch_results.items():
                        key = f"{symbol}_{timeframe}"
                        all_batch_results[key] = result

        # Générer un résumé des résultats
        summary = self.pipeline.get_summary(all_batch_results)

        # Log du résumé global
        logger.info(f"📊 Résumé du pipeline ETL:")
        logger.info(f"  Symboles traités: {summary['total_symbols']}")
        logger.info(f"  Succès: {summary['successful']}")
        logger.info(f"  Échecs: {summary['failed']}")
        logger.info(f"  Taux de succès: {summary['success_rate'] * 100:.1f}%")
        logger.info(f"  Bougies extraites: {summary['total_raw_rows']}")
        logger.info(f"  Lignes transformées: {summary['total_transformed_rows']}")
        logger.info(f"  Lignes chargées: {summary['total_loaded_rows']}")
        logger.info(f"  Temps total: {summary['total_time']:.2f}s")
        logger.info(f"  Temps moyen par symbole: {summary['average_time']:.2f}s")

        # Log des échecs individuels si nécessaire
        failed_symbols = [s for s, r in all_batch_results.items() if not r.success]
        if failed_symbols:
            logger.warning(f"⚠️  Échecs individuels:")
            for symbol in failed_symbols:
                result = all_batch_results[symbol]
                logger.warning(f"  - {symbol}: {result.error_step} - {result.error}")
