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
        Extrait les données global_market depuis CoinGecko.
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

    def extract_top_cryptos(
        self,
        limit: int = 50,
        vs_currency: str = "usd",
        order: str = "market_cap_desc",
    ):
        """
        Extrait les données des top cryptomonnaies depuis CoinGecko.

        Args:
            limit: Nombre de cryptos à récupérer (défaut: 50)
            vs_currency: Devise de référence (défaut: "usd")
            order: Ordre de tri (défaut: "market_cap_desc")

        Returns:
            List[Dict]: Liste des cryptomonnaies avec leurs données de marché
        """
        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(
                    f"Extraction top cryptos tentative {attempt}/{self.max_retries}: "
                    f"limit={limit}, currency={vs_currency}"
                )
                raw_data = self.client.fetch_top_cryptos_by_market_cap(
                    limit=limit,
                    vs_currency=vs_currency,
                    order=order,
                    sparkline=False,
                    price_change_percentage="24h",
                )
                if not raw_data:
                    raise ExtractionErrorMarketData(
                        "Aucune donnée reçue de CoinGecko pour les top cryptos"
                    )
                logger.info(f"✅ Extraction top {len(raw_data)} cryptos réussie")
                return raw_data
            except Exception as e:
                last_error = e
                logger.warning(f"⚠️ Tentative {attempt} échouée: {e}")
        error_msg = (
            f"Échec après {self.max_retries} tentatives pour top cryptos: {last_error}"
        )
        logger.error(f"❌ {error_msg}")
        raise ExtractionErrorMarketData(error_msg)
