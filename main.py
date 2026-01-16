import argparse
import time
import threading
import subprocess
from logger_settings import logger
from config.settings import config
from src.schedulers.scheduler_ohlcv import run_ohlcv_scheduler, run_ohlcv_once
from src.schedulers.scheduler_ticker import run_ticker_scheduler, run_ticker_once


def run_collection_once():
    """
    Exécute une collecte unique de données OHLCV et optionnellement de ticker.
    Utilise la configuration centralisée.
    """
    try:
        logger.info("Démarrage de la collecte unique de données")

        # Récupérer la configuration centralisée
        pairs = config.get("pairs")
        timeframes = config.get("timeframes")
        exchanges = config.get("exchanges")
        include_ticker = config.get("ticker.enabled", False)
        ticker_pairs = config.get("ticker.pairs")
        snapshot_interval = config.get("ticker.snapshot_interval", 5)
        runtime_minutes = config.get("ticker.runtime", 60)

        # Utiliser les mêmes paires pour le ticker si non spécifié
        if ticker_pairs is None:
            ticker_pairs = pairs

        logger.info(
            f"Configuration OHLCV: {len(pairs)} paires, {len(timeframes)} timeframes"
        )
        logger.info(f"Exchanges: {', '.join(exchanges)}")

        if include_ticker:
            logger.info(
                f"Configuration Ticker: {len(ticker_pairs)} paires, snapshot toutes les {snapshot_interval} minutes"
            )

        # 1. Exécuter la collecte OHLCV pour tous les exchanges
        logger.info("📊 Exécution de la collecte OHLCV...")
        run_ohlcv_once(pairs, timeframes, exchanges)

        # 2. Démarrer la collecte de ticker si activée
        if include_ticker:
            logger.info("Démarrage de la collecte de ticker en temps réel...")
            run_ticker_once(ticker_pairs, exchanges, snapshot_interval, runtime_minutes)
        else:
            logger.info("✅ Collecte OHLCV terminée avec succès")

    except Exception as e:
        logger.error(f"❌ Erreur fatale dans la collecte unique: {e}")
        raise
    finally:
        # Exécuter le script de vérification de la base de données
        try:
            logger.info("Exécution du script de vérification de la base de données...")
            subprocess.run(["python", "scripts/check_db.py"], check=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Échec de l'exécution du script de vérification: {e}")
        except Exception as e:
            logger.error(
                f"❌ Erreur lors de l'exécution du script de vérification: {e}"
            )


def run_scheduled_collection():
    """
    Exécute une collecte planifiée quotidienne de données OHLCV et optionnellement de ticker.
    Utilise la configuration centralisée.
    """
    try:
        logger.info("Démarrage du collecteur de données avec planification")

        # Récupérer la configuration centralisée
        pairs = config.get("pairs")
        timeframes = config.get("timeframes")
        exchanges = config.get("exchanges")
        schedule_time = config.get("scheduler.schedule_time", "09:00")
        include_ticker = config.get("ticker.enabled", False)
        ticker_pairs = config.get("ticker.pairs")
        snapshot_interval = config.get("ticker.snapshot_interval", 5)
        runtime_minutes = config.get("ticker.runtime", 60)

        # Utiliser les mêmes paires pour le ticker si non spécifié
        if ticker_pairs is None:
            ticker_pairs = pairs

        logger.info(
            f"Configuration OHLCV: {len(pairs)} paires, {len(timeframes)} timeframes"
        )
        logger.info(f"Planification: Collecte quotidienne à {schedule_time}")
        logger.info(f"Exchanges: {', '.join(exchanges)}")

        if include_ticker:
            logger.info(
                f"Configuration Ticker: {len(ticker_pairs)} paires, snapshot toutes les {snapshot_interval} minutes"
            )

        # 1. Exécution immédiate au démarrage pour chaque exchange
        logger.info("📊 Exécution de la collecte OHLCV initiale...")
        run_ohlcv_once(pairs, timeframes, exchanges)

        # 2. Démarrer la collecte de ticker si activée
        if include_ticker:
            logger.info("📈 Démarrage de la collecte de ticker en temps réel...")
            # Démarrer le ticker dans un thread séparé pour ne pas bloquer le scheduler
            ticker_thread = threading.Thread(
                target=run_ticker_scheduler,
                args=(ticker_pairs, exchanges, snapshot_interval, runtime_minutes),
                daemon=True,
            )
            ticker_thread.start()

        # 3. Puis planification quotidienne pour tous les exchanges
        logger.info("Démarrage du planificateur quotidien...")
        run_ohlcv_scheduler(pairs, timeframes, exchanges, schedule_time)

    except Exception as e:
        logger.error(f"❌ Erreur fatale dans la collecte planifiée: {e}")
        raise
    finally:
        # Exécuter le script de vérification de la base de données
        try:
            logger.info("Exécution du script de vérification de la base de données...")
            subprocess.run(["python", "scripts/check_db.py"], check=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Échec de l'exécution du script de vérification: {e}")
        except Exception as e:
            logger.error(
                f"❌ Erreur lors de l'exécution du script de vérification: {e}"
            )


def parse_arguments():
    """Parse les arguments de ligne de commande."""
    parser = argparse.ArgumentParser(
        description="Collecteur de données marché Crypto Bot"
    )
    parser.add_argument(
        "--schedule",
        action="store_true",
        help="Activer la planification quotidienne (par défaut: exécution unique)",
    )
    parser.add_argument(
        "--ticker",
        action="store_true",
        help="Activer la collecte de ticker en temps réel",
    )
    parser.add_argument(
        "--ticker-pairs",
        nargs="+",
        default=None,
        help="Liste des paires pour le ticker (par défaut: mêmes que les paires principales)",
    )
    parser.add_argument(
        "--snapshot-interval",
        type=int,
        default=5,
        help="Intervalle de sauvegarde des snapshots de ticker en minutes (par défaut: 5)",
    )
    parser.add_argument(
        "--runtime",
        type=int,
        default=60,
        help="Durée d'exécution en minutes (0 pour illimité, par défaut: 60)",
    )
    parser.add_argument(
        "--exchanges",
        nargs="+",
        default=["binance"],
        help="Liste des exchanges à utiliser (par défaut: binance)",
    )
    parser.add_argument(
        "--schedule-time",
        type=str,
        default="09:00",
        help="Heure de planification quotidienne (format HH:MM, par défaut: 09:00)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()

    # Mettre à jour la configuration avec les arguments de ligne de commande
    config.update_from_args(args)

    if args.schedule:
        # Mode planifié avec OHLCV et optionnellement ticker
        run_scheduled_collection()
    else:
        # Mode exécution unique avec OHLCV et optionnellement ticker
        run_collection_once()
