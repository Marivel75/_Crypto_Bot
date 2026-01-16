"""
Module de planification dédié aux tâches OHLCV (données historiques).
Sépare clairement les tâches OHLCV des tâches de ticker.
"""

import schedule
import time
from typing import List
from logger_settings import logger
from config.settings import config
from src.collectors.ohlcv_collector import OHLCVCollector


def daily_ohlcv_collection(
    pairs: List[str], timeframes: List[str], exchange: str = "binance"
) -> None:
    """
    Fonction de collecte quotidienne de données OHLCV.
    """
    try:
        logger.info(f"Début de la collecte quotidienne OHLCV ({exchange})")

        # Normalisation des timeframes pour l'exchange
        normalized_timeframes = []
        for tf in timeframes:
            # Coinbase a des timeframes spécifiques
            if exchange == "coinbase":
                # Coinbase supporte: 1m, 5m, 15m, 1h, 6h, 1d
                if tf not in ["1m", "5m", "15m", "1h", "6h", "1d"]:
                    logger.warning(
                        f"Timeframe {tf} non supporté par Coinbase, utilisation de 1h"
                    )
                    normalized_timeframes.append("1h")
                else:
                    normalized_timeframes.append(tf)
            else:
                # Binance et Kraken supportent plus de timeframes
                normalized_timeframes.append(tf)

        logger.info(f"Timeframes normalisés: {normalized_timeframes}")

        # Initialisation du collecteur avec l'exchange spécifié
        collector = OHLCVCollector(pairs, normalized_timeframes, exchange)

        # Exécution de la collecte
        collector.fetch_and_store()

        logger.info(f"✅ Collecte quotidienne OHLCV {exchange} terminée avec succès")

    except Exception as e:
        logger.error(f"❌ Échec de la collecte quotidienne OHLCV {exchange}: {e}")
        raise


def run_ohlcv_scheduler() -> None:
    """
    Exécute le planificateur pour la collecte quotidienne de données OHLCV sur plusieurs exchanges.
    Utilise la configuration centralisée.
    Note:
        Cette fonction bloque le thread courant et doit être exécutée dans un thread séparé pour les applications web.
    """
    try:
        # Récupérer la configuration centralisée
        pairs = config.get("pairs")
        timeframes = config.get("timeframes")
        exchanges = config.get("exchanges")
        schedule_time = config.get("scheduler.schedule_time", "09:00")

        logger.info(
            f"Planificateur OHLCV démarré - Collecte prévue à {schedule_time} quotidiennement"
        )
        logger.info(f"Exchanges configurés: {', '.join(exchanges)}")

        # Planification de la tâche quotidienne pour chaque exchange
        for exchange in exchanges:
            schedule.every().day.at(schedule_time).do(
                lambda ex=exchange: daily_ohlcv_collection(pairs, timeframes, ex)
            )

        # Boucle principale du planificateur
        while True:
            schedule.run_pending()
            time.sleep(60)  # Vérifie toutes les minutes

    except KeyboardInterrupt:
        logger.info("Planificateur OHLCV arrêté par l'utilisateur")
    except Exception as e:
        logger.error(f"❌ Erreur dans le planificateur OHLCV: {e}")
        raise


def run_ohlcv_once(
    pairs: List[str], timeframes: List[str], exchanges: List[str] = ["binance"]
) -> None:
    """
    Exécute une collecte immédiate OHLCV (pour les tests ou le démarrage)
    """
    try:
        logger.info(f"Exécution immédiate de la collecte OHLCV")
        for exchange in exchanges:
            daily_ohlcv_collection(pairs, timeframes, exchange)
    except Exception as e:
        logger.error(f"❌ Échec de l'exécution immédiate OHLCV: {e}")
        raise
