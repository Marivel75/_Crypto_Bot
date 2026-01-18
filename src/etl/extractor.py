"""
Gère l'extraction des données OHLCV depuis les exchanges.
"""

from typing import Any, Dict, List, Optional, cast

from src.config.logger_settings import logger


class ExtractionError(Exception):
    """Exception levée lors d'un échec d'extraction."""

    pass


class OHLCVExtractor:
    """
    Extracteur de données OHLCV depuis les exchanges, responsable de la
    récupération des données brutes depuis les APIs des exchanges.
    """

    def __init__(self, client: Any, max_retries: int = 3) -> None:
        """
        Initialise l'extracteur avec un client d'exchange.
        """
        self.client = client
        self.max_retries = max_retries
        logger.info(f"Extracteur initialisé pour {client.__class__.__name__}")

    def extract(self, symbol: str, timeframe: str, limit: int = 100) -> List[List[Any]]:
        """
        Extrait les données OHLCV brutes depuis l'exchange.
        """
        last_error = None

        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(
                    f"Extraction tentative {attempt}/{self.max_retries}: {symbol} {timeframe}"
                )

                raw_data = self.client.fetch_ohlcv(symbol, timeframe, limit)

                if not raw_data or len(raw_data) == 0:
                    raise ExtractionError(f"Aucune donnée retournée pour {symbol} {timeframe}")

                logger.info(
                    f"✅ Extraction réussie: {len(raw_data)} bougies pour {symbol} {timeframe}"
                )
                return cast(List[List[Any]], raw_data)

            except Exception as e:
                last_error = e
                logger.warning(f"⚠️ Échec tentative {attempt}/{self.max_retries}: {e}")

                # Attendre avant de réessayer (sauf dernière tentative)
                if attempt < self.max_retries:
                    import time

                    time.sleep(2**attempt)

        # Toutes les tentatives ont échoué
        error_msg = f"Échec d'extraction après {self.max_retries} tentatives: {last_error}"
        logger.error(f"❌ {error_msg}")
        raise ExtractionError(error_msg)

    def extract_multiple(
        self, symbols: List[str], timeframe: str, limit: int = 100
    ) -> Dict[str, Optional[List[List[Any]]]]:
        """
        Extrait les données pour plusieurs symboles.
        """
        results: Dict[str, Optional[List[List[Any]]]] = {}

        for symbol in symbols:
            try:
                results[symbol] = self.extract(symbol, timeframe, limit)
            except ExtractionError as e:
                logger.error(f"❌ Échec extraction {symbol}: {e}")
                results[symbol] = None

        return results
