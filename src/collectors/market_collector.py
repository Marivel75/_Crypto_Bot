import pandas as pd
from logger_settings import logger
from src.services.exchanges_api.binance_client import BinanceClient
from src.services.exchanges_api.kraken_client import KrakenClient
from src.services.exchanges_api.coinbase_client import CoinbaseClient
from src.services.db import get_engine
from src.quality.validator import DataValidator0HCLV
from src.etl.extractor import OHLCVExtractor
from src.etl.transformer import OHLCVTransformer
from src.etl.loader import OHLCVLoader
from src.etl.pipeline import ETLPipeline
from typing import List

class MarketCollector:
    """
    Collecteur de données marché pour plusieurs exchanges.

    Récupère les données OHLCV (Open, High, Low, Close, Volume) pour des paires de trading spécifiques et des timeframes donnés, puis les stocke dans une base de données.

    Attributs:
        pairs (List[str]): Liste des paires de trading à surveiller
        timeframes (List[str]): Liste des timeframes pour l'analyse
        exchange (str): Nom de l'exchange à utiliser
        client: Client pour interagir avec l'API de l'exchange
        engine: Moteur SQLAlchemy pour la connexion à la base de données
    """

    def __init__(
        self, pairs: List[str], timeframes: List[str], exchange: str = "binance"
    ):
        """
        Initialise le collecteur de données marché.

        Args:
            pairs: Liste des paires de trading (ex: ['BTC/USDT', 'ETH/USDT'])
            timeframes: Liste des timeframes (ex: ['1h', '4h', '1d'])
            exchange: Nom de l'exchange ('binance', 'kraken', 'coinbase')

        Raises:
            ValueError: Si les paires, timeframes ou exchange ne sont pas valides
        """
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

        # Initialisation du client approprié
        if self.exchange == "binance":
            self.client = BinanceClient()
        elif self.exchange == "kraken":
            self.client = KrakenClient(use_auth=False)
        elif self.exchange == "coinbase":
            self.client = CoinbaseClient(use_auth=False)
        else:
            logger.warning(
                f"Exchange '{self.exchange}' non reconnu. Utilisation de Binance par défaut."
            )
            self.exchange = "binance"
            self.client = BinanceClient()

        self.engine = get_engine()
        
        # Initialisation du valideur de données OHLCV
        self.data_validator = DataValidator0HCLV()
        
        # Initialisation du pipeline ETL
        self.etl_pipeline = self._create_etl_pipeline()

    def _create_etl_pipeline(self) -> ETLPipeline:
        """
        Crée le pipeline ETL avec les composants appropriés.
        """
        extractor = OHLCVExtractor(self.client)
        transformer = OHLCVTransformer(self.data_validator, self.exchange)
        loader = OHLCVLoader(self.engine)

        return ETLPipeline(extractor, transformer, loader)

    def fetch_and_store(self) -> None:
        """
        Récupère les données OHLCV pour toutes les paires et timeframes configurés et les stocke dans la base de données. Utilise le pipeline ETL.
        
        Raises:
            Exception: En cas d'erreur lors de la récupération ou du stockage des données
        """
        # Exécuter le pipeline ETL pour toutes les paires et timeframes
        batch_results = self.etl_pipeline.run_batch(self.pairs, self.timeframes)
        
        # Générer un résumé des résultats
        summary = self.etl_pipeline.get_summary(batch_results)
        
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
        failed_symbols = [s for s, r in batch_results.items() if not r.success]
        if failed_symbols:
            logger.warning(f"⚠️  Échecs individuels:")
            for symbol in failed_symbols:
                result = batch_results[symbol]
                logger.warning(f"  - {symbol}: {result.error_step} - {result.error}")
