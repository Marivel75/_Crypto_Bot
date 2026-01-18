"""
Module ETL pour le projet Crypto Bot.

Ce module fournit un pipeline ETL (Extract, Transform, Load) pour le traitement
des données OHLCV avec une architecture modulaire et extensible.

Composants principaux:
- Extractor: Récupération des données depuis les exchanges
- Transformer: Nettoyage, validation et enrichissement des données (à implémenter)
- Loader: Sauvegarde des données dans la base de données (à implémenter)
- Pipeline: Orchestration du processus ETL complet (à implémenter)
"""

# Import des composants disponibles
from .extractor import ExtractionError, OHLCVExtractor
from .loader import LoadingError, OHLCVLoader
from .pipeline_ohlcv import ETLPipelineOHLCV, PipelineResult
from .transformer import OHLCVTransformer, TransformationError

__all__ = [
    "OHLCVExtractor",
    "ExtractionError",
    "OHLCVTransformer",
    "TransformationError",
    "OHLCVLoader",
    "LoadingError",
    "ETLPipelineOHLCV",
    "PipelineResult",
]
