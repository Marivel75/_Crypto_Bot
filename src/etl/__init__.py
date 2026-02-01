"""
Module ETL pour le projet Crypto Bot.

Ce module fournit un pipeline ETL (Extract, Transform, Load) pour le traitement
des données OHLCV avec une architecture modulaire et extensible.
Compatible avec SQLite (développement) et Supabase (production).

Composants principaux:
- Extractor: Récupération des données depuis les exchanges
- Transformer: Nettoyage, validation et enrichissement des données
- Loader: Sauvegarde des données dans la base de données
- Pipeline: Orchestration du processus ETL complet
"""

from .extractor import OHLCVExtractor, ExtractionError

# Import des composants transform et load avec gestion des erreurs
try:
    from .transformer import OHLCVTransformer, TransformationError
    from .loader import OHLCVLoader, LoadingError
    from .pipeline_ohlcv import ETLPipelineOHLCV, PipelineResult
except ImportError as e:
    raise ImportError(f"Erreur lors de l'import des modules ETL: {e}")

# Import de la configuration pour les logs
from logger_settings import logger
from src.config.settings import ENVIRONMENT

# Message de log pour indiquer l'initialisation du module ETL
logger.info(f"Module ETL initialisé (Environnement: {ENVIRONMENT})")

__all__ = [
    'OHLCVExtractor', 'ExtractionError',
    'OHLCVTransformer', 'TransformationError',
    'OHLCVLoader', 'LoadingError',
    'ETLPipelineOHLCV', 'PipelineResult'
]
