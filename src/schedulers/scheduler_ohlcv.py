"""
Module de planification dédié aux tâches OHLCV (données historiques).
"""

import schedule
import time
import threading
from typing import List, Optional
from src.config.logger_settings import logger
from config.settings import config
from src.collectors.ohlcv_collector import OHLCVCollector


def _normalize_list(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return [item for item in value if item is not None]
    return [value]


def _normalize_exchanges(value):
    exchanges = _normalize_list(value)
    return [str(item).lower() for item in exchanges if item]


class OHLCVScheduler:
    """
    Classe de planification pour la collecte quotidienne de données OHLCV. Utilise une configuration centralisée.
    """

    def __init__(
        self,
        pairs: Optional[List[str]] = None,
        timeframes: Optional[List[str]] = None,
        exchanges: Optional[List[str]] = None,
        schedule_time: Optional[str] = None,
    ):
        """Initialise le scheduler OHLCV avec la configuration centralisée."""
        self.pairs = _normalize_list(pairs) or _normalize_list(config.get("pairs"))
        self.timeframes = _normalize_list(timeframes) or _normalize_list(
            config.get("timeframes")
        )
        self.exchanges = _normalize_exchanges(exchanges or config.get("exchanges"))
        if not self.exchanges:
            default_exchange = config.get("default_exchange")
            if default_exchange:
                self.exchanges = [str(default_exchange).lower()]
        self.schedule_time = schedule_time or config.get(
            "scheduler.schedule_time", "09:00"
        )
        self.running = False
        self.scheduler_thread = None

        if not self.pairs:
            raise ValueError("Aucune paire configuree pour le scheduler OHLCV.")
        if not self.timeframes:
            raise ValueError("Aucun timeframe configure pour le scheduler OHLCV.")
        if not self.exchanges:
            raise ValueError("Aucun exchange configure pour le scheduler OHLCV.")

        logger.info(f"OHLCVScheduler initialisé pour {len(self.exchanges)} exchanges")
        logger.info(f"Planification quotidienne à {self.schedule_time}")

    def _ohlcv_collection(self, exchange: str) -> None:
        """
        Fonction de collecte quotidienne de données OHLCV pour un exchange spécifique.
        """
        try:
            logger.info(
                f"Début de la collecte quotidienne OHLCV sur l'exchange : {exchange}"
            )

            # Normalisation des timeframes pour l'exchange
            normalized_timeframes = []
            for tf in self.timeframes:
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
                    # Binance et Kraken
                    normalized_timeframes.append(tf)

            logger.info(f"Timeframes normalisés: {normalized_timeframes}")

            # Initialisation du collecteur avec l'exchange spécifié
            collector = OHLCVCollector(self.pairs, normalized_timeframes, exchange)

            # Exécution de la collecte
            collector.fetch_and_store()

            logger.info(
                f"✅ Collecte quotidienne OHLCV {exchange} terminée avec succès"
            )

        except Exception as e:
            logger.error(f"❌ Échec de la collecte quotidienne OHLCV {exchange}: {e}")
            raise

    def start(self) -> None:
        """
        Démarre le planificateur OHLCV, planifie les tâches quotidiennes et lance le threadde planification.
        """
        if self.running:
            logger.warning("⚠️  Le scheduler OHLCV est déjà en cours d'exécution")
            return

        try:
            logger.info(
                f"Démarrage du planificateur OHLCV - Collecte prévue à {self.schedule_time} quotidiennement"
            )
            logger.info(f"Exchanges configurés: {', '.join(self.exchanges)}")

            # Planification de la tâche quotidienne pour chaque exchange
            for exchange in self.exchanges:
                schedule.every().day.at(self.schedule_time).do(
                    lambda ex=exchange: self._ohlcv_collection(ex)
                )

            self.running = True

            # Démarrer le thread de planification
            self.scheduler_thread = threading.Thread(
                target=self._run_scheduler_loop, daemon=True, name="OHLCVScheduler"
            )
            self.scheduler_thread.start()

            logger.info("✅ Planificateur OHLCV démarré avec succès")

        except Exception as e:
            logger.error(f"❌ Erreur lors du démarrage du planificateur OHLCV: {e}")
            self.running = False
            raise

    def _run_scheduler_loop(self) -> None:
        """
        Boucle principale du planificateur, exécutée dans un thread séparé et vérifie
        périodiquement les tâches planifiées.
        """
        try:
            while self.running:
                schedule.run_pending()
                time.sleep(60)  # Vérificatiob toutes les minutes
        except KeyboardInterrupt:
            logger.info("Planificateur OHLCV arrêté par l'utilisateur")
        except Exception as e:
            logger.error(f"❌ Erreur dans la boucle du planificateur OHLCV: {e}")
            raise

    def stop(self) -> None:
        """
        Arrête le planificateur OHLCV.
        """
        if not self.running:
            logger.warning("⚠️  Le scheduler OHLCV n'est pas en cours d'exécution")
            return

        try:
            logger.info("Arrêt du planificateur OHLCV...")
            self.running = False

            # Attendre que le thread se termine
            if self.scheduler_thread and self.scheduler_thread.is_alive():
                self.scheduler_thread.join(timeout=10)

            logger.info("✅ Planificateur OHLCV arrêté avec succès")

        except Exception as e:
            logger.error(f"❌ Erreur lors de l'arrêt du planificateur OHLCV: {e}")
            raise

    def run_once(self) -> None:
        """
        Exécute une collecte immédiate OHLCV pour les tests ou le démarrage.
        """
        try:
            logger.info(f"Exécution immédiate de la collecte OHLCV")
            for exchange in self.exchanges:
                self._ohlcv_collection(exchange)
        except Exception as e:
            logger.error(f"❌ Échec de l'exécution immédiate OHLCV: {e}")
            raise
