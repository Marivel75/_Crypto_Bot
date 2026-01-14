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
from .extractor import OHLCVExtractor, ExtractionError

# Composants à implémenter (imports conditionnels pour éviter les erreurs)
try:
    from .transformer import OHLCVTransformer, TransformationError
    from .loader import OHLCVLoader, LoadingError
    from .pipeline import ETLPipeline, PipelineResult
except ImportError:
    # Ces modules seront disponibles lors de l'implémentation complète
    OHLCVTransformer = None
    TransformationError = None
    OHLCVLoader = None
    LoadingError = None
    ETLPipeline = None
    PipelineResult = None

__all__ = [
    'OHLCVExtractor', 'ExtractionError',
    'OHLCVTransformer', 'TransformationError',
    'OHLCVLoader', 'LoadingError',
    'ETLPipeline', 'PipelineResult'
]