"""
Module de planification pour la collecte quotidienne de données marché.
Fournit des fonctions pour exécuter la collecte de données à intervalles réguliers (quotidiennement par défaut).
"""

import schedule
import time
from logger_settings import logger
from src.collectors.market_collector import MarketCollector
from typing import List, Optional


def daily_data_collection(pairs: List[str], timeframes: List[str], exchange: str = "binance") -> None:
    """
    Fonction de collecte quotidienne de données.
    
    Args:
        pairs: Liste des paires de trading à collecter
        timeframes: Liste des timeframes à collecter
        exchange: Nom de l'exchange à utiliser ('binance' ou 'kraken')
        
    Raises:
        Exception: En cas d'erreur lors de la collecte
    """
    try:
        logger.info(f"🕒 Début de la collecte quotidienne de données ({exchange})")
        
        # Initialisation du collecteur avec l'exchange spécifié
        collector = MarketCollector(pairs, timeframes, exchange)
        
        # Exécution de la collecte
        collector.fetch_and_store()
        
        logger.info(f"✅ Collecte quotidienne {exchange} terminée avec succès")
        
    except Exception as e:
        logger.error(f"❌ Échec de la collecte quotidienne {exchange}: {e}")
        raise


def run_scheduler(
    pairs: List[str], timeframes: List[str], schedule_time: str = "09:00"
) -> None:
    """
    Exécute le planificateur pour la collecte quotidienne de données.
    
    Args:
        pairs: Liste des paires de trading à collecter
        timeframes: Liste des timeframes à collecter
        schedule_time: Heure quotidienne pour la collecte (format HH:MM)
        
    Note:
        Cette fonction bloque le thread courant et doit être exécutée dans un thread séparé pour les applications web.
    """
    try:
        logger.info(
            f"⏰ Planificateur démarré - Collecte prévue à {schedule_time} quotidiennement"
        )
        
        # Planification de la tâche quotidienne
        schedule.every().day.at(schedule_time).do(
            lambda: daily_data_collection(pairs, timeframes, "binance")
        )
        
        # Boucle principale du planificateur
        while True:
            schedule.run_pending()
            time.sleep(60)  # Vérifie toutes les minutes
            
    except KeyboardInterrupt:
        logger.info("🛑 Planificateur arrêté par l'utilisateur")
    except Exception as e:
        logger.error(f"❌ Erreur dans le planificateur: {e}")
        raise


def run_once_now(pairs: List[str], timeframes: List[str], exchange: str = "binance") -> None:
    """
    Exécute une collecte immédiate (pour les tests ou le démarrage).
    
    Args:
        pairs: Liste des paires de trading à collecter
        timeframes: Liste des timeframes à collecter
        exchange: Nom de l'exchange à utiliser ('binance' ou 'kraken')
    """
    try:
        logger.info(f"🚀 Exécution immédiate de la collecte de données ({exchange})")
        daily_data_collection(pairs, timeframes, exchange)
    except Exception as e:
        logger.error(f"❌ Échec de l'exécution immédiate {exchange}: {e}")
        raise