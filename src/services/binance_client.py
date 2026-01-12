import ccxt
from logger_settings import logger
from src.config.settings import BINANCE_API_KEY, BINANCE_API_SECRET


class BinanceClient:
    def __init__(self):
        # Validation des clés API avant initialisation
        self._validate_api_keys()

        self.exchange = ccxt.binance(
            {
                "apiKey": BINANCE_API_KEY,
                "secret": BINANCE_API_SECRET,
                "enableRateLimit": True,
                "options": {"defaultType": "spot"},
            }
        )

        # Fonction privée pour synchroniser l'heure locale avec l'heure serveur de Binance
        self._sync_time()

        # Vérification que l'échange est correctement initialisé
        self._check_exchange_initialization()

    def _sync_time(self):
        """
        Synchronisation horloge locale avec Binance
        """
        try:
            server_time = self.exchange.fetch_time()
            self.exchange.options["timeDifference"] = (
                server_time - self.exchange.milliseconds()
            )
            logger.info("Synchro de l'heure Binance réussie")
        except Exception as e:
            logger.warning(f"Échec de la synchro de l'heure: {e}")

    def _validate_api_keys(self):
        """
        Valide que les clés API sont définies avant d'initialiser l'échange
        """
        if not BINANCE_API_KEY or not BINANCE_API_SECRET:
            error_msg = "La clé API Binance ou le secret n'est pas configuré"
            logger.error(error_msg)
            raise ValueError(error_msg)

        if not isinstance(BINANCE_API_KEY, str) or not isinstance(
            BINANCE_API_SECRET, str
        ):
            error_msg = (
                "La clé API Binance et le secret doivent être des chaînes de caractères (str)"
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

        if not BINANCE_API_KEY.strip() or not BINANCE_API_SECRET.strip():
            error_msg = "La clé API Binance ou le secret est vide"
            logger.error(error_msg)
            raise ValueError(error_msg)

    def _check_exchange_initialization(self):
        """
        Vérifie que l'exchange est correctement initialisé et accessible
        """
        try:
            # Test simple pour vérifier que l'échange répond
            self.exchange.fetch_status()
            logger.info("Initialisation de l'exchange réussie")
        except Exception as e:
            logger.error(
                f"Échec de la vérification de l'initialisation de l'exchange: {e}"
            )
            raise RuntimeError(f"Échec de l'initialisation de l'exchange Binance: {e}")

    def fetch_ticker(self, symbol: str) -> dict:
        """
        Méthode ccxt de la classe Exchange pour récupérer le ticker d'une paire (résumé rapide de l’état actuel du marché pour une paire de trading).
        Récupère le dernier prix et infos marché pour une paire (BTC/USDT, ETH/USDT, etc.), renvoie un dictionnaire contenant :
        - last (dernier prix)
        high / low / open
        - volume
        - bid / ask
        - timestamp

        Returns:
            dict: Informations du ticker

        Raises:
            Exception: En cas d'erreur lors de la récupération du ticker
        """
        try:
            return self.exchange.fetch_ticker(symbol)
        except Exception as e:
            logger.error(f"Échec de la récupération du ticker pour {symbol}: {e}")
            raise

    def fetch_ohlcv(self, symbol: str, timeframe: str = "1h", limit: int = 100) -> list:
        """
        Méthode ccxt de la classe Exchange
        Récupère les bougies OHLCV (Open, High, Low, Close, Volume)
        timeframe : "1m", "5m", "1h", "1d", etc.
        limit : nombre de bougies à récupérer
        Retourne une liste de listes

        Returns:
            list: Liste des bougies OHLCV

        Raises:
            Exception: En cas d'erreur lors de la récupération des données OHLCV
        """
        try:
            return self.exchange.fetch_ohlcv(
                symbol=symbol, timeframe=timeframe, limit=limit
            )
        except Exception as e:
            logger.error(
                f"Échec de la récupération des OHLCV pour {symbol} avec timeframe {timeframe}: {e}"
            )
            raise
