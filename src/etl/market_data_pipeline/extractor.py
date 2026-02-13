from logger_settings import logger


class ExtractionErrorMarketData(Exception):
    """Exception levée lors d'un échec d'extraction MarketData."""

    pass


class MarketDataExtractor:
    """
    Récupère les données global_market depuis CoinGecko.
    """

    def __init__(self, client, max_retries: int = 3):
        self.client = client
        self.max_retries = max_retries
        logger.info(f"MarketDataExtractor initialisé pour {client.__class__.__name__}")

    def extract(self, symbol: str):
        """
        Extrait les données depuis CoinGecko.
        """
        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(
                    f"Extraction tentative {attempt}/{self.max_retries}: {symbol}"
                )
                raw_data = self.client.fetch_global_market_data()
                if not raw_data:
                    raise ExtractionErrorMarketData("Aucune donnée reçue de CoinGecko")
                logger.info("✅ Extraction réussie")
                return raw_data
            except Exception as e:
                last_error = e
                logger.warning(f"⚠️ Tentative {attempt} échouée: {e}")
        error_msg = f"Échec après {self.max_retries} tentatives: {last_error}"
        logger.error(f"❌ {error_msg}")
        raise ExtractionErrorMarketData(error_msg)
