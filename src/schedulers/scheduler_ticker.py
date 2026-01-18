"""
Module de planification dédié aux tâches de ticker en temps réel.
"""

import time
import threading
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from src.config.logger_settings import logger
from config.settings import config
from src.collectors.ticker_collector import TickerCollector


class TickerScheduler:
    """
    Classe de planification pour la collecte de ticker en temps réel. Gère la collecte et le stockage hybride des données de ticker pour plusieurs exchanges avec cache mémoire et sauvegarde périodique.
    """

    def __init__(self):
        """Initialise le scheduler de ticker avec la configuration centralisée."""
        self.pairs = config.get("pairs")
        self.exchanges = config.get("exchanges")
        self.snapshot_interval = config.get("ticker.snapshot_interval", 5)
        self.runtime_minutes = config.get("ticker.runtime", 60)
        self.cache_size = config.get("ticker.cache_size", 1000)

        self.collectors = {}  # {exchange: TickerCollector}
        self.running = False
        self.scheduler_thread = None

        logger.info(f"TickerScheduler initialisé pour {len(self.exchanges)} exchanges")
        logger.info(f"Intervalle de snapshot: {self.snapshot_interval} minutes")

    def start_collection(self) -> None:
        """
        Démarre la collecte de ticker pour tous les exchanges.
        """
        if self.running:
            logger.warning("⚠️  La collecte de ticker est déjà en cours")
            return

        try:
            logger.info(
                f"Démarrage de la collecte de ticker pour {len(self.exchanges)} exchanges"
            )
            logger.info(f"Paires surveillées: {', '.join(self.pairs)}")

            # Créer un collecteur de ticker pour chaque exchange
            for exchange in self.exchanges:
                self.collectors[exchange] = TickerCollector(
                    pairs=self.pairs,
                    exchange=exchange,
                    snapshot_interval=self.snapshot_interval,
                    cache_size=self.cache_size,
                )
                self.collectors[exchange].start_collection()
                logger.info(f"✅ Collecteur de ticker démarré pour {exchange}")

            self.running = True

            # Démarrer le thread de gestion
            self.scheduler_thread = threading.Thread(
                target=self._collection_loop, daemon=True, name="TickerScheduler"
            )
            self.scheduler_thread.start()

            logger.info("✅ Scheduler de ticker démarré avec succès")

        except Exception as e:
            logger.error(f"❌ Erreur lors du démarrage du scheduler de ticker: {e}")
            self.running = False
            raise

    def _collection_loop(self) -> None:
        """
        Boucle principale de collecte des tickers, gère la collecte périodique, les snapshots et
        le nettoyage du cache. Elle est exécutée dans un thread séparé.
        """
        try:
            start_time = time.time()
            runtime_seconds = (
                self.runtime_minutes * 60 if self.runtime_minutes > 0 else float("inf")
            )
            last_display_time = start_time
            next_snapshot = datetime.utcnow() + timedelta(
                minutes=self.snapshot_interval
            )

            while self.running and (time.time() - start_time < runtime_seconds):
                # 1. Afficher les prix actuels périodiquement
                if time.time() - last_display_time > 30:
                    self._display_current_prices()

                    # Afficher le temps restant si le runtime est limité
                    if self.runtime_minutes > 0:
                        self._display_remaining_time(start_time, runtime_seconds)

                    last_display_time = time.time()

                # 2. Sauvegarder un snapshot si nécessaire
                if datetime.utcnow() >= next_snapshot:
                    self._save_snapshots()
                    next_snapshot = datetime.utcnow() + timedelta(
                        minutes=self.snapshot_interval
                    )

                time.sleep(10)

        except KeyboardInterrupt:
            logger.info("Arrêt du scheduler de ticker demandé par l'utilisateur")
        except Exception as e:
            logger.error(f"❌ Erreur dans la boucle de collecte des tickers: {e}")
        finally:
            self.stop_collection()

    def _display_current_prices(self) -> None:
        """Affiche les prix actuels pour tous les exchanges."""
        for exchange, collector in self.collectors.items():
            current_prices = collector.get_current_prices()
            if current_prices:
                logger.info(f"Prix actuels {exchange}: {current_prices}")

    def _display_remaining_time(
        self, start_time: float, runtime_seconds: float
    ) -> None:
        """Affiche le temps restant pour l'exécution."""
        elapsed = time.time() - start_time
        remaining_seconds = max(0, runtime_seconds - elapsed)
        remaining_minutes = int(remaining_seconds // 60)
        remaining_seconds_display = int(remaining_seconds % 60)
        logger.info(
            f"Temps restant: {remaining_minutes} minutes {remaining_seconds_display} secondes"
        )

    def _save_snapshots(self) -> None:
        """Sauvegarde les snapshots pour tous les collecteurs."""
        for exchange, collector in self.collectors.items():
            try:
                collector._save_snapshot()
            except Exception as e:
                logger.error(f"❌ Échec sauvegarde snapshot pour {exchange}: {e}")

    def stop_collection(self) -> None:
        """
        Arrête la collecte de ticker pour tous les exchanges.
        """
        if not self.running:
            logger.warning("⚠️  La collecte de ticker n'est pas en cours")
            return

        try:
            logger.info("Arrêt du scheduler de ticker...")
            self.running = False

            # Arrêter tous les collecteurs
            for exchange, collector in self.collectors.items():
                collector.stop_collection()
                logger.info(f"✅ Collecteur de ticker arrêté pour {exchange}")

            # Attendre que le thread se termine
            if self.scheduler_thread and self.scheduler_thread.is_alive():
                self.scheduler_thread.join(timeout=10)

            self.collectors.clear()
            logger.info("✅ Scheduler de ticker arrêté avec succès")

        except Exception as e:
            logger.error(f"❌ Erreur lors de l'arrêt du scheduler de ticker: {e}")
            raise

    def get_current_prices(self) -> Dict[str, Dict]:
        """
        Récupère les prix actuels pour tous les exchanges dans un dict.
        """
        result = {}
        for exchange, collector in self.collectors.items():
            result[exchange] = collector.get_current_prices()
        return result

    def run_once(self, runtime_minutes: Optional[int] = None) -> None:
        """
        Exécute une collecte de ticker unique.
        """
        if runtime_minutes is not None:
            self.runtime_minutes = runtime_minutes

        self.start_collection()

        # Attendre la fin de l'exécution si le runtime est limité
        if self.runtime_minutes > 0:
            time.sleep(self.runtime_minutes * 60)
            self.stop_collection()
