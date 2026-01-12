import pandas as pd
from logger_settings import logger
from src.services.binance_client import BinanceClient
from src.services.kraken_client import KrakenClient
from src.services.db import get_engine
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
    def __init__(self, pairs: List[str], timeframes: List[str], exchange: str = "binance"):
        """
        Initialise le collecteur de données marché.
        
        Args:
            pairs: Liste des paires de trading (ex: ['BTC/USDT', 'ETH/USDT'])
            timeframes: Liste des timeframes (ex: ['1h', '4h', '1d'])
            exchange: Nom de l'exchange ('binance' ou 'kraken')
            
        Raises:
            ValueError: Si les paires, timeframes ou exchange ne sont pas valides
        """
        # Validation des entrées
        if not pairs or not timeframes:
            error_msg = "Les listes de paires et timeframes ne peuvent pas être vides"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        if not all(isinstance(pair, str) and pair.strip() for pair in pairs):
            error_msg = "Toutes les paires doivent être des chaînes de caractères non vides"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        if not all(isinstance(tf, str) and tf.strip() for tf in timeframes):
            error_msg = "Tous les timeframes doivent être des chaînes de caractères non vides"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Validation de l'exchange
        supported_exchanges = ['binance', 'kraken']
        if exchange.lower() not in supported_exchanges:
            error_msg = f"Exchange non supporté: {exchange}. Choix possibles: {supported_exchanges}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        self.pairs = pairs
        self.timeframes = timeframes
        self.exchange = exchange.lower()
        
        # Initialisation du client approprié
        if self.exchange == 'binance':
            self.client = BinanceClient()
        else:  # kraken
            self.client = KrakenClient(use_auth=False)
        
        self.engine = get_engine()

    def fetch_and_store(self) -> None:
        """
        Récupère les données OHLCV pour toutes les paires et timeframes configurés et les stocke dans la base de données.
        
        Raises:
            Exception: En cas d'erreur lors de la récupération ou du stockage des données
        """
        for pair in self.pairs:
            for tf in self.timeframes:
                try:
                    # Récupère les bougies
                    ohlcv = self.client.fetch_ohlcv(pair, tf)

                    # Convertit en DataFrame
                    df = pd.DataFrame(
                        ohlcv,
                        columns=["timestamp", "open", "high", "low", "close", "volume"],
                    )
                    df["symbol"] = pair
                    df["timeframe"] = tf

                    # Convert timestamp en datetime
                    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")

                    # Sauvegarde dans la base de données
                    df.to_sql("ohlcv", self.engine, if_exists="append", index=False)
                    logger.info(f"✅ {pair} {tf} sauvegardé")
                    
                except IntegrityError:
                    logger.warning(f"⚠️ Doublons détectés pour {pair} {tf}, ignorés")
                except Exception as e:
                    logger.error(f"❌ Erreur lors du traitement de {pair} {tf}: {e}")
                    raise
