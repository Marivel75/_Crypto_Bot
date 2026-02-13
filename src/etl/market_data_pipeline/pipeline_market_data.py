from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from logger_settings import logger


@dataclass
class PipelineResultMarketData:
    symbol: str
    success: bool = False
    extraction_time: float = 0.0
    transformation_time: float = 0.0
    loading_time: float = 0.0
    raw_rows: int = 0
    transformed_rows: int = 0
    loaded_rows: int = 0
    error: Optional[str] = None
    error_step: Optional[str] = None

    def total_time(self):
        return self.extraction_time + self.transformation_time + self.loading_time


class ETLPipelineMarketData:
    """
    Pipeline ETL pour les données global_market.
    """

    def __init__(self, extractor, transformer, loader):
        self.extractor = extractor
        self.transformer = transformer
        self.loader = loader

    def run(self, symbol: str):
        result = PipelineResultMarketData(symbol)
        try:
            # Extraction
            start = datetime.utcnow().timestamp()
            raw_data = self.extractor.extract(symbol)
            result.extraction_time = datetime.utcnow().timestamp() - start
            result.raw_rows = 1  # Une seule requête global

            # Transformation
            start = datetime.utcnow().timestamp()
            snapshot, caps, volumes, dominance = self.transformer.transform(raw_data)
            result.transformation_time = datetime.utcnow().timestamp() - start
            result.transformed_rows = len(caps) + len(volumes) + len(dominance)

            # Loading
            start = datetime.utcnow().timestamp()
            loaded_rows = self.loader.load(snapshot, caps, volumes, dominance)
            result.loading_time = datetime.utcnow().timestamp() - start
            result.loaded_rows = loaded_rows

            result.success = True
            logger.info("✅ Pipeline MarketData terminé avec succès")
        except Exception as e:
            result.error = str(e)
            result.error_step = "unknown"
            result.success = False
            logger.error(f"❌ Pipeline MarketData échoué: {e}")
        return result

    def get_summary(self, results: dict):
        r = list(results.values())[0]
        return {
            "symbol": r.symbol,
            "success": r.success,
            "raw_rows": r.raw_rows,
            "transformed_rows": r.transformed_rows,
            "loaded_rows": r.loaded_rows,
            "error": r.error,
            "total_time": r.total_time(),
        }
