import argparse
from logger_settings import logger
from src.collectors.market_collector import MarketCollector
from src.scheduler import run_scheduler, run_once_now


def main():
    """Point d'entrée principal pour le collecteur de données marché."""
    try:
        logger.info("🚀 Démarrage du collecteur de données marché")

        # Définir les paires et timeframes à collecter
        pairs = ["BTC/USDT", "ETH/USDT"]
        timeframes = ["1h", "4h"]

        logger.info(f"Configuration: {len(pairs)} paires, {len(timeframes)} timeframes")

        # Exécution immédiate (comportement par défaut)
        run_once_now(pairs, timeframes, "binance")

        logger.info("✅ Collecte de données terminée avec succès")

    except Exception as e:
        logger.error(f"❌ Erreur fatale dans le programme principal: {e}")
        raise


def main_with_scheduling():
    """Point d'entrée avec planification quotidienne."""
    try:
        logger.info("🚀 Démarrage du collecteur de données marché avec planification")

        # Définir les paires et timeframes à collecter
        pairs = ["BTC/USDT", "ETH/USDT"]
        timeframes = ["1h", "4h"]
        schedule_time = "09:00"  # Heure quotidienne pour la collecte

        logger.info(f"Configuration: {len(pairs)} paires, {len(timeframes)} timeframes")
        logger.info(f"Planification: Collecte quotidienne à {schedule_time}")

        # Exécution immédiate au démarrage
        run_once_now(pairs, timeframes, "binance")
        
        # Puis planification quotidienne
        run_scheduler(pairs, timeframes, schedule_time)

    except Exception as e:
        logger.error(f"❌ Erreur fatale dans le programme principal: {e}")
        raise


def parse_arguments():
    """Parse les arguments de ligne de commande."""
    parser = argparse.ArgumentParser(
        description="Collecteur de données marché Crypto Bot"
    )
    parser.add_argument(
        "--schedule",
        action="store_true",
        help="Activer la planification quotidienne (par défaut: exécution unique)"
    )
    parser.add_argument(
        "--exchange",
        choices=["binance", "kraken"],
        default="binance",
        help="Exchange à utiliser (par défaut: binance)"
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()
    
    if args.schedule:
        main_with_scheduling()
    else:
        main()
