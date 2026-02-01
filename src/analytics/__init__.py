"""
Module d'analytics pour les indicateurs techniques et les visualisations.

Ce module fournit des outils pour :
- Calculer des indicateurs techniques (SMA, EMA, RSI, MACD, etc.)
- Visualiser les données financières (graphiques OHLCV, indicateurs, etc.)
- Inspecter et préparer les données pour l'analyse

Compatible avec les environnements de développement (SQLite) et de production (Supabase).

Exemple d'utilisation :
    from src.analytics import calculate_sma, PlotManager, DBInspector
    sma_data = calculate_sma(data, window=20)
    plot_manager = PlotManager()
    plot_manager.plot_with_sma(data, sma_data, window=20)
"""

# Imports des indicateurs techniques
from .indicators import calculate_sma

# Imports commentés pour les indicateurs à implémenter plus tard
# from .indicators import calculate_ema, calculate_rsi, calculate_macd

# Imports des outils de visualisation
from .plot_manager import PlotManager

# Imports des utilitaires de base de données
from .db_inspector import DBInspector

# Import de la configuration pour les logs
from logger_settings import logger
from src.config.settings import ENVIRONMENT

# Message de log pour indiquer l'initialisation du module analytics
logger.info(f"Module Analytics initialisé (Environnement: {ENVIRONMENT})")

# Liste des éléments publics du module
__all__ = [
    # Indicateurs techniques
    "calculate_sma",
    # "calculate_ema",
    # "calculate_rsi",
    # "calculate_macd",
    # Outils de visualisation
    "PlotManager",
    # Utilitaires de base de données
    "DBInspector",
]
