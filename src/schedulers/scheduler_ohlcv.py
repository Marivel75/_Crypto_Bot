"""
Module de planification dédié aux tâches OHLCV (données historiques).
"""

import schedule
import time
import threading
from typing import List, Optional
from logger_settings import logger
from config.settings import config
from src.collectors.ohlcv_collector import OHLCVCollector
from src.notifications.notifier import notify_collect_start, notify_collect_end, notify_collect_error


class OHLCVScheduler:
    """
    Classe de planification pour la collecte quotidienne de données OHLCV. Utilise une configuration centralisée.
    """

    def __init__(self):
        """Initialise le scheduler OHLCV avec la configuration centralisée."""
        self.pairs = config.get("pairs")
        self.timeframes = config.get("timeframes")
        self.exchanges = config.get("exchanges")
        self.schedule_time = config.get("scheduler.schedule_time", "09:00")
        self.running = False
        self.scheduler_thread = None

        logger.info(f"OHLCVScheduler initialisé pour {len(self.exchanges)} exchanges")
        logger.info(f"Planification quotidienne à {self.schedule_time}")

    def _ohlcv_collection(self, exchange: str) -> dict:
        """Collecte OHLCV pour un exchange. Retourne le résumé ETL."""
        normalized_timeframes = []
        for tf in self.timeframes:
            if exchange == "coinbase" and tf not in ["1m", "5m", "15m", "1h", "6h", "1d"]:
                logger.warning(f"Timeframe {tf} non supporté par Coinbase, utilisation de 1h")
                normalized_timeframes.append("1h")
            else:
                normalized_timeframes.append(tf)

        collector = OHLCVCollector(self.pairs, normalized_timeframes, exchange)
        return collector.fetch_and_store() or {}

    def _ohlcv_collection_with_alerts(self, exchange: str, trigger: str = "planifié") -> None:
        """Collecte OHLCV avec alertes email début/fin/erreur."""
        import time as _time
        notify_collect_start([exchange], trigger=trigger)
        t0 = _time.monotonic()
        try:
            logger.info(f"Début de la collecte OHLCV — {exchange} ({trigger})")
            summary = self._ohlcv_collection(exchange)
            duration = _time.monotonic() - t0
            logger.info(f"✅ Collecte OHLCV {exchange} terminée en {duration:.0f}s")
            notify_collect_end([exchange], summary, duration)
        except Exception as e:
            logger.error(f"❌ Échec de la collecte OHLCV {exchange}: {e}")
            notify_collect_error(str(e))
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
                    lambda ex=exchange: self._ohlcv_collection_with_alerts(ex, trigger=f"planifié ({self.schedule_time})")
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
        """Exécute une collecte immédiate OHLCV — 1 email start + 1 email end pour tous les exchanges."""
        import time as _time
        notify_collect_start(self.exchanges, trigger="manuel")
        t0 = _time.monotonic()
        combined: dict = {"total_raw_rows": 0, "total_loaded_rows": 0,
                          "total_symbols": 0, "successful": 0, "failed": 0}
        last_error: str = ""
        for exchange in self.exchanges:
            try:
                summary = self._ohlcv_collection(exchange)
                for key in ("total_raw_rows", "total_loaded_rows", "total_symbols"):
                    combined[key] += summary.get(key, 0)
                combined["successful"] += 1
            except Exception as e:
                logger.error(f"❌ Échec collecte OHLCV {exchange}: {e}")
                combined["failed"] += 1
                last_error = str(e)
        if combined["failed"] == len(self.exchanges) and last_error:
            notify_collect_error(last_error)
        else:
            notify_collect_end(self.exchanges, combined, _time.monotonic() - t0)
