"""
Module de planification dédié aux tâches de ticker en temps réel.
Sépare clairement les tâches OHLCV (historique) des tâches de ticker (temps réel).
"""

import time
import threading
from typing import List
from logger_settings import logger
from src.services.ticker_service import TickerCollector


def run_ticker_scheduler(
    pairs: List[str],
    exchanges: List[str] = ["binance"],
    snapshot_interval: int = 5,
    runtime_minutes: int = 60
):
    """
    Exécute un planificateur dédié à la collecte de ticker en temps réel pour plusieurs exchanges.
    
    Args:
        pairs: Liste des paires de trading à surveiller
        exchanges: Liste des exchanges à utiliser
        snapshot_interval: Intervalle de sauvegarde des snapshots en minutes
        runtime_minutes: Durée d'exécution en minutes (0 pour illimité)
    """
    try:
        logger.info(f"📈 Démarrage du planificateur de ticker pour {len(exchanges)} exchanges")
        logger.info(f"Paires surveillées: {', '.join(pairs)}")
        logger.info(f"Intervalle de snapshot: {snapshot_interval} minutes")
        
        # Créer un collecteur de ticker pour chaque exchange
        collectors = {}
        for exchange in exchanges:
            collectors[exchange] = TickerCollector(
                pairs=pairs,
                exchange=exchange,
                snapshot_interval=snapshot_interval,
                cache_size=1000
            )
            collectors[exchange].start_collection()
            logger.info(f"✅ Collecteur de ticker démarré pour {exchange}")
        
        # Exécuter pendant la durée spécifiée
        start_time = time.time()
        runtime_seconds = runtime_minutes * 60 if runtime_minutes > 0 else float('inf')
        
        try:
            while time.time() - start_time < runtime_seconds:
                # Afficher les prix actuels périodiquement pour tous les exchanges
                if time.time() - start_time > 30:  # Après 30 secondes
                    for exchange, collector in collectors.items():
                        current_prices = collector.get_current_prices()
                        if current_prices:
                            logger.info(f"Prix actuels {exchange}: {current_prices}")
                    start_time = time.time()
                
                time.sleep(10)
                
        except KeyboardInterrupt:
            logger.info("🛑 Arrêt du planificateur de ticker demandé par l'utilisateur")
            
        finally:
            # Arrêter proprement tous les collecteurs
            for exchange, collector in collectors.items():
                collector.stop_collection()
                logger.info(f"✅ Collecteur de ticker arrêté pour {exchange}")
            
            logger.info("✅ Planificateur de ticker terminé")
            
    except Exception as e:
        logger.error(f"❌ Erreur fatale dans le planificateur de ticker: {e}")
        raise


def run_ticker_once(
    pairs: List[str],
    exchanges: List[str] = ["binance"],
    snapshot_interval: int = 5,
    runtime_minutes: int = 60
):
    """
    Exécute une collecte de ticker unique (pour les tests ou le démarrage).
    
    Args:
        pairs: Liste des paires de trading à surveiller
        exchanges: Liste des exchanges à utiliser
        snapshot_interval: Intervalle de sauvegarde des snapshots en minutes
        runtime_minutes: Durée d'exécution en minutes
    """
    try:
        logger.info(f"📈 Exécution unique de la collecte de ticker")
        run_ticker_scheduler(pairs, exchanges, snapshot_interval, runtime_minutes)
    except Exception as e:
        logger.error(f"❌ Échec de l'exécution unique du ticker: {e}")
        raise