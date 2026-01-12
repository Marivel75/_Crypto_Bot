"""
Client pour l'exchange Kraken.
Ce module fournit une interface pour interagir avec l'API Kraken. Pas besoin de clef API puor les données publiques sur Kraken.
"""

import ccxt
from logger_settings import logger


class KrakenClient:
    """
    Client pour interagir avec l'API Kraken. Pour les données de marché publiques, aucune clé API n'est nécessaire.
    
    Attributes:
        exchange: Instance ccxt de l'exchange Kraken
    """
    
    def __init__(self, use_auth=False, api_key=None, api_secret=None):
        """
        Initialise le client Kraken.
        
        Args:
            use_auth: Si True, utilise l'authentification (pour le trading)
            api_key: Clé API Kraken (requise si use_auth=True)
            api_secret: Secret API Kraken (requis si use_auth=True)
            
        Raises:
            ValueError: Si use_auth=True mais les clés API ne sont pas fournies
        """
        if use_auth:
            if not api_key or not api_secret:
                error_msg = "Les clés API Kraken sont requises pour les opérations authentifiées"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            # Initialisation avec authentification pour le trading
            self.exchange = ccxt.kraken({
                "apiKey": api_key,
                "secret": api_secret,
                "enableRateLimit": True,
                "options": {"defaultType": "spot"},
            })
        else:
            # Initialisation sans authentification pour les données publiques
            self.exchange = ccxt.kraken({
                "enableRateLimit": True,
                "options": {"defaultType": "spot"},
            })
        
        # Synchronisation du temps
        self._sync_time()
        
        # Vérification de l'initialisation
        self._check_exchange_initialization()

    def _sync_time(self):
        """
        Synchro horloge locale avec Kraken.
        """
        try:
            server_time = self.exchange.fetch_time()
            self.exchange.options["timeDifference"] = (
                server_time - self.exchange.milliseconds()
            )
            logger.info("Synchro de l'heure Kraken réussie")
        except Exception as e:
            logger.warning(f"Échec de la synchro de l'heure Kraken: {e}")

    def _check_exchange_initialization(self):
        """
        Vérifie que l'exchange Kraken est correctement initialisé et accessible.
        
        Raises:
            RuntimeError: Si l'initialisation échoue
        """
        try:
            # Test simple pour vérifier que l'exchange répond
            self.exchange.fetch_status()
            logger.info("Initialisation de l'exchange Kraken réussie")
        except Exception as e:
            logger.error(f"Échec de la vérification de l'initialisation de Kraken: {e}")
            raise RuntimeError(f"Échec de l'initialisation de l'exchange Kraken: {e}")

    def fetch_ticker(self, symbol: str) -> dict:
        """
        Récupère le ticker pour une paire de trading.
        
        Args:
            symbol: Paire de trading (ex: 'BTC/USD')
            
        Returns:
            dict: Informations du ticker
            
        Raises:
            Exception: En cas d'erreur lors de la récupération
        """
        try:
            return self.exchange.fetch_ticker(symbol)
        except Exception as e:
            logger.error(f"Échec de la récupération du ticker Kraken pour {symbol}: {e}")
            raise

    def fetch_ohlcv(self, symbol: str, timeframe: str = "1h", limit: int = 100) -> list:
        """
        Récupère les données OHLCV pour une paire.
        
        Args:
            symbol: Paire de trading (ex: 'BTC/USD')
            timeframe: Timeframe (ex: '1h', '4h', '1d')
            limit: Nombre de bougies à récupérer
            
        Returns:
            list: Liste des bougies OHLCV
            
        Raises:
            Exception: En cas d'erreur lors de la récupération
        """
        try:
            return self.exchange.fetch_ohlcv(
                symbol=symbol, timeframe=timeframe, limit=limit
            )
        except Exception as e:
            logger.error(f"Échec de la récupération des OHLCV Kraken pour {symbol} ({timeframe}): {e}")
            raise