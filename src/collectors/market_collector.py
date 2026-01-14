import pandas as pd
from logger_settings import logger
from src.services.exchanges_api.binance_client import BinanceClient
from src.services.exchanges_api.kraken_client import KrakenClient
from src.services.exchanges_api.coinbase_client import CoinbaseClient
from src.services.db import get_engine
from src.quality.validator import DataValidator0HCLV
from sqlalchemy.exc import IntegrityError
from typing import List, Optional, Union


class MarketCollector:
    """
    Collecteur de données marché pour plusieurs exchanges.

    Ce collecteur récupère les données OHLCV (Open, High, Low, Close, Volume)
    pour des paires de trading spécifiques et des timeframes donnés,
    puis les stocke dans une base de données.

    Attributes:
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

    def fetch_and_store(self) -> None:
        """
        Récupère les données OHLCV pour toutes les paires et timeframes configurés et les stocke dans la base de données.

        Raises:
            Exception: En cas d'erreur lors de la récupération ou du stockage des données
        """
        for pair in self.pairs:
            for tf in self.timeframes:
                try:
                    # Conversion du timeframe en chaîne de caractères pour éviter les erreurs
                    timeframe_str = str(tf)

                    # Récupère les bougies
                    ohlcv = self.client.fetch_ohlcv(pair, timeframe_str)

                    # Convertit en DataFrame
                    df = pd.DataFrame(
                        ohlcv,
                        columns=["timestamp", "open", "high", "low", "close", "volume"],
                    )
                    df["symbol"] = pair
                    df["timeframe"] = tf

                    # Convert timestamp en datetime
                    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")

                    # Validation des données avant sauvegarde
                    is_valid, validation_report = self.data_validator.validate_ohlcv_values(df)
                    
                    # Log des résultats de validation
                    if is_valid:
                        logger.info(f"✅ Validation réussie pour {pair} {tf}: {validation_report['valid_rows']}/{validation_report['total_rows']} lignes valides")
                    else:
                        logger.warning(f"⚠️ Problèmes de validation pour {pair} {tf}: {len(validation_report['errors'])} erreurs, {len(validation_report['warnings'])} warnings")
                        
                        # Log des erreurs détaillées
                        if validation_report['errors']:
                            for error in validation_report['errors'][:3]:  # Limiter à 3 erreurs pour la lisibilité
                                logger.warning(f"  - {error}")
                            if len(validation_report['errors']) > 3:
                                logger.warning(f"  - ... et {len(validation_report['errors']) - 3} autres erreurs")
                    
                    # Sauvegarde dans la base de données seulement si les données sont valides
                    if is_valid:
                        df.to_sql("ohlcv", self.engine, if_exists="append", index=False)
                        logger.info(f"✅ {pair} {tf} sauvegardé")
                    else:
                        logger.error(f"❌ {pair} {tf} non sauvegardé en raison d'erreurs de validation")
                        continue  # Passer à la paire/timeframe suivant

                except IntegrityError:
                    logger.warning(f"⚠️ Doublons détectés pour {pair} {tf}, ignorés")
                except Exception as e:
                    logger.error(f"❌ Erreur lors du traitement de {pair} {tf}: {e}")
                    raise
