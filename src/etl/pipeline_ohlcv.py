"""
Module Pipeline pour le pipeline ETL : orchestrer le processus ETL complet en coordonnant les composants Extract, Transform et Load.
"""

import pandas as pd
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime
from src.config.logger_settings import logger
from src.etl.extractor import OHLCVExtractor, ExtractionError
from src.etl.transformer import OHLCVTransformer, TransformationError
from src.etl.loader import OHLCVLoader, LoadingError


@dataclass
class PipelineResult:
    """
    Classe pour stocker les résultats d'exécution du pipeline.
    """

    symbol: str
    timeframe: str
    success: bool = False
    extraction_time: float = 0.0
    transformation_time: float = 0.0
    loading_time: float = 0.0
    raw_rows: int = 0
    transformed_rows: int = 0
    loaded_rows: int = 0
    error: Optional[str] = None
    error_step: Optional[str] = None

    def total_time(self) -> float:
        """Calcule le temps total d'exécution."""
        return self.extraction_time + self.transformation_time + self.loading_time

    def to_dict(self) -> dict:
        """Convertit le résultat en dictionnaire."""
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "success": self.success,
            "extraction_time": self.extraction_time,
            "transformation_time": self.transformation_time,
            "loading_time": self.loading_time,
            "total_time": self.total_time(),
            "raw_rows": self.raw_rows,
            "transformed_rows": self.transformed_rows,
            "loaded_rows": self.loaded_rows,
            "error": self.error,
            "error_step": self.error_step,
        }

    def start_extraction(self):
        """Démarre le chronomètre pour l'extraction."""
        self.extraction_time = -datetime.utcnow().timestamp()

    def end_extraction(self, raw_rows: int):
        """Arrête le chronomètre pour l'extraction."""
        self.extraction_time += datetime.utcnow().timestamp()
        self.raw_rows = raw_rows

    def start_transformation(self):
        """Démarre le chronomètre pour la transformation."""
        self.transformation_time = -datetime.utcnow().timestamp()

    def end_transformation(self, transformed_rows: int):
        """Arrête le chronomètre pour la transformation."""
        self.transformation_time += datetime.utcnow().timestamp()
        self.transformed_rows = transformed_rows

    def start_loading(self):
        """Démarre le chronomètre pour le chargement."""
        self.loading_time = -datetime.utcnow().timestamp()

    def end_loading(self, loaded_rows: int):
        """Arrête le chronomètre pour le chargement."""
        self.loading_time += datetime.utcnow().timestamp()
        self.loaded_rows = loaded_rows

    def fail_extraction(self, error: str):
        """Marque l'échec à l'étape d'extraction."""
        self.error = error
        self.error_step = "extraction"
        self.success = False

    def fail_transformation(self, error: str):
        """Marque l'échec à l'étape de transformation."""
        self.error = error
        self.error_step = "transformation"
        self.success = False

    def fail_loading(self, error: str):
        """Marque l'échec à l'étape de chargement."""
        self.error = error
        self.error_step = "loading"
        self.success = False

    def fail(self, error: str):
        """Marque l'échec général du pipeline."""
        self.error = error
        self.error_step = "unknown"
        self.success = False


class PipelineError(Exception):
    """Exception levée lors d'un échec du pipeline."""

    pass


class ETLPipelineOHLCV:
    """
    Pipeline ETL complet pour le traitement des données OHLCV. Orchestrateur de l'ensemble du processus ETL en coordonnant les extracteurs, transformeurs et chargeurs.

    Attributs:
        extractor: Extracteur de données
        transformer: Transformeur de données
        loader: Chargeur de données
    """

    def __init__(
        self,
        extractor: OHLCVExtractor,
        transformer: OHLCVTransformer,
        loader: OHLCVLoader,
    ):
        """
        Initialise le pipeline avec les composants ETL.
        """
        self.extractor = extractor
        self.transformer = transformer
        self.loader = loader
        logger.info("Pipeline ETL initialisé et prêt")

    def run(self, symbol: str, timeframe: str, limit: int = 100) -> PipelineResult:
        """
        Exécute le pipeline ETL complet pour une paire/timeframe.

        Arguments:
            symbol: Paire de trading (ex: 'BTC/USDT')
            timeframe: Timeframe (ex: '1h', '4h', '1d')
            limit: Nombre de bougies à extraire (défaut: 100)
        """
        result = PipelineResult(symbol, timeframe)

        try:
            # Étape 1: Extraction
            result.start_extraction()
            raw_data = self._extract_data(symbol, timeframe, limit)
            result.end_extraction(len(raw_data))

            # Étape 2: Transformation
            result.start_transformation()
            df = self._transform_data(raw_data, symbol, timeframe)
            result.end_transformation(len(df))

            # Étape 3: Chargement
            result.start_loading()
            rows_inserted = self._load_data(df)
            result.end_loading(rows_inserted)

            result.success = True
            logger.info(
                f"✅ Pipeline ETL terminé avec succès pour {symbol} {timeframe}"
            )

        except ExtractionError as e:
            result.fail_extraction(str(e))
        except TransformationError as e:
            result.fail_transformation(str(e))
        except LoadingError as e:
            result.fail_loading(str(e))
        except Exception as e:
            result.fail(str(e))

        return result

    def _extract_data(self, symbol: str, timeframe: str, limit: int) -> List[List]:
        """Extrait les données brutes."""
        logger.info(f"Extraction: {symbol} {timeframe}")
        return self.extractor.extract(symbol, timeframe, limit)

    def _transform_data(
        self, raw_data: List[List], symbol: str, timeframe: str
    ) -> pd.DataFrame:
        """Transforme les données brutes."""
        logger.info(f"Transformation: {symbol} {timeframe}")
        return self.transformer.transform(raw_data, symbol, timeframe)

    def _load_data(self, df: pd.DataFrame) -> int:
        """Charge les données transformées."""
        logger.info(f"Chargement: {len(df)} lignes")
        return self.loader.load(df)

    def run_batch(
        self, symbols: List[str], timeframe: str, limit: int = 100
    ) -> Dict[str, PipelineResult]:
        """
        Exécute le pipeline ETL pour plusieurs symboles.

        Arguments:
            symbols: Liste de paires de trading
            timeframe: Timeframe commun
            limit: Nombre de bougies par symbole
        """
        results = {}

        for symbol in symbols:
            try:
                results[symbol] = self.run(symbol, timeframe, limit)
            except Exception as e:
                error_result = PipelineResult(symbol, timeframe)
                error_result.fail(str(e))
                results[symbol] = error_result
                logger.error(f"❌ Échec du pipeline pour {symbol}: {e}")

        return results

    def run_extract_transform_batch(
        self, symbols: List[str], timeframe: str, limit: int = 100
    ) -> Dict[str, pd.DataFrame]:
        """
        Exécute uniquement les étapes Extract et Transform pour plusieurs symboles.

        Arguments:
            symbols: Liste de paires de trading
            timeframe: Timeframe commun
            limit: Nombre de bougies par symbole
        """
        results = {}

        for symbol in symbols:
            try:
                # Extraction
                raw_data = self._extract_data(symbol, timeframe, limit)

                # Transformation
                df = self._transform_data(raw_data, symbol, timeframe)

                results[symbol] = df
                logger.info(f"✅ Extract+Transform réussi pour {symbol} {timeframe}")

            except Exception as e:
                logger.error(f"❌ Échec Extract+Transform pour {symbol}: {e}")
                results[symbol] = None

        return results

    def get_summary(self, results: Dict[str, PipelineResult]) -> dict:
        """
        Génère un dict résumé des résultats du pipeline.
        """
        total_symbols = len(results)
        successful = sum(1 for r in results.values() if r.success)
        failed = total_symbols - successful

        total_raw_rows = sum(r.raw_rows for r in results.values())
        total_transformed = sum(r.transformed_rows for r in results.values())
        total_loaded = sum(r.loaded_rows for r in results.values())

        total_time = sum(r.total_time() for r in results.values())
        avg_time = total_time / total_symbols if total_symbols > 0 else 0

        return {
            "total_symbols": total_symbols,
            "successful": successful,
            "failed": failed,
            "success_rate": successful / total_symbols if total_symbols > 0 else 0,
            "total_raw_rows": total_raw_rows,
            "total_transformed_rows": total_transformed,
            "total_loaded_rows": total_loaded,
            "total_time": total_time,
            "average_time": avg_time,
            "timestamp": datetime.utcnow().isoformat(),
        }
