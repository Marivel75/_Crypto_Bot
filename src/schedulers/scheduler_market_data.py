import schedule
import time
import threading
from logger_settings import logger
from config.settings import config
from src.collectors.market_data_collector import MarketDataCollector


class MarketDataScheduler:
    """
    Scheduler pour la collecte quotidienne de données global_market depuis CoinGecko.
    """

    def __init__(self):
        self.schedule_time = config.get("scheduler.market_data_time", "10:00")
        self.running = False
        self.scheduler_thread = None

        logger.info(f"MarketDataScheduler initialisé, collecte prévue à {self.schedule_time}")

    def _market_data_collection(self):
        """
        Exécute la collecte quotidienne de données global_market.
        """
        try:
            logger.info("Début de la collecte MarketData")
            collector = MarketDataCollector()
            collector.fetch_and_store()
            logger.info("✅ Collecte MarketData terminée")
        except Exception as e:
            logger.error(f"❌ Échec de la collecte MarketData: {e}")

    def start(self):
        if self.running:
            logger.warning("⚠️ Scheduler MarketData déjà en cours")
            return

        schedule.every().day.at(self.schedule_time).do(self._market_data_collection)
        self.running = True

        self.scheduler_thread = threading.Thread(
            target=self._run_scheduler_loop, daemon=True, name="MarketDataScheduler"
        )
        self.scheduler_thread.start()
        logger.info("✅ Scheduler MarketData démarré")

    def _run_scheduler_loop(self):
        try:
            while self.running:
                schedule.run_pending()
                time.sleep(60)
        except Exception as e:
            logger.error(f"❌ Erreur dans la boucle scheduler MarketData: {e}")

    def stop(self):
        if not self.running:
            logger.warning("⚠️ Scheduler MarketData pas en cours")
            return
        self.running = False
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=10)
        logger.info("✅ Scheduler MarketData arrêté")

    def run_once(self):
        logger.info("Exécution immédiate MarketData")
        self._market_data_collection()
