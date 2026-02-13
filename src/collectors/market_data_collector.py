from src.services.exchanges_api.coingecko_client import CoinGeckoClient
from src.etl.market_data_pipeline.pipeline_market_data import ETLPipelineMarketData
from logger_settings import logger


class MarketDataCollector:
    """
    Collecte les données global_market depuis CoinGecko et les envoie dans le pipeline ETL.
    """

    def __init__(self):
        self.client = CoinGeckoClient()
        self.pipeline = self._create_pipeline()

    def _create_pipeline(self):
        from src.etl.market_data_pipeline.extractor import (
            MarketDataExtractor,
        )
        from src.etl.market_data_pipeline.transformer import (
            MarketDataTransformer,
        )
        from src.etl.market_data_pipeline.loader import MarketDataLoader
        from src.services.db import get_db_engine

        engine = get_db_engine()
        extractor = MarketDataExtractor(self.client)
        transformer = MarketDataTransformer()
        loader = MarketDataLoader(engine)
        return ETLPipelineMarketData(extractor, transformer, loader)

    def fetch_and_store(self):
        """
        Exécute la collecte des données global_market.
        """
        try:
            logger.info("Lancement pipeline ETL MarketData")
            result = self.pipeline.run(
                "global_market"
            )  # Pas de timeframe, juste global_market
            summary = self.pipeline.get_summary({"global_market": result})
            logger.info(f"📊 Résumé: {summary}")
        except Exception as e:
            logger.error(f"❌ Échec collecte pipeline MarketData: {e}")
