import ccxt
from logger_settings import logger
from src.config.settings import BINANCE_API_KEY, BINANCE_API_SECRET


class BinanceClient:
    def __init__(self):
        self.exchange = ccxt.binance(
            {
                "apiKey": BINANCE_API_KEY,
                "secret": BINANCE_API_SECRET,
                "enableRateLimit": True,
                "options": {"defaultType": "spot"},
            }
        )

        # Fonction privée pour synchroniser l'heure local avec l'heure serveur de Binance
        self._sync_time()

    def _sync_time(self):
        """
        Synchronisation horloge locale avec Binance
        """
        try:
            server_time = self.exchange.fetch_time()
            self.exchange.options["timeDifference"] = (
                server_time - self.exchange.milliseconds()
            )
            logger.info("Binance time synchronized")
        except Exception as e:
            logger.warning(f"Time sync failed: {e}")

    def fetch_ticker(self, symbol: str):
        """
        Méthode ccxt de la classe Exchange pour récupérer le ticker d'une paire (résumé rapide de l’état actuel du marché pour une paire de trading).
        Récupère le dernier prix et infos marché pour une paire (BTC/USDT, ETH/USDT, etc.), renvoie un dictionnaire contenant :
        - last (dernier prix)
        high / low / open
        - volume
        - bid / ask
        - timestamp
        """
        return self.exchange.fetch_ticker(symbol)

    def fetch_ohlcv(self, symbol: str, timeframe="1h", limit=100):
        """
        Méthode ccxt de la classe Exchange
        Récupère les bougies OHLCV (Open, High, Low, Close, Volume)
        timeframe : "1m", "5m", "1h", "1d", etc.
        limit : nombre de bougies à récupérer
        Retourne une liste de listes
        """
        return self.exchange.fetch_ohlcv(
            symbol=symbol, timeframe=timeframe, limit=limit
        )
