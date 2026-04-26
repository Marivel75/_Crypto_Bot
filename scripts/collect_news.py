#!/usr/bin/env python3
"""Collecte des articles de news RSS et stockage en base.

Usage:
    python scripts/collect_news.py              # sources par défaut
    python scripts/collect_news.py --once       # une seule passe (pas de boucle)
    python scripts/collect_news.py --interval 30  # toutes les 30 minutes
"""

import sys
import time
import argparse
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.dependencies import SessionLocal, engine
from src.collectors.news_collector import NewsCollector
from src.models.news import Base as NewsBase

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

# Crée la table si elle n'existe pas encore
NewsBase.metadata.create_all(bind=engine)


def collect_once() -> dict:
    db = SessionLocal()
    try:
        with NewsCollector() as collector:
            result = collector.fetch_and_store(db)
        logger.info("Collecte terminée : %s", result)
        return result
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Collecteur de news crypto")
    parser.add_argument(
        "--once", action="store_true",
        help="Une seule passe puis quitte (défaut: boucle infinie)",
    )
    parser.add_argument(
        "--interval", type=int, default=60,
        help="Intervalle en minutes entre deux collectes (défaut: 60)",
    )
    args = parser.parse_args()

    if args.once:
        collect_once()
        return

    logger.info("Démarrage de la collecte en boucle (intervalle: %d min)", args.interval)
    while True:
        try:
            collect_once()
        except Exception as exc:
            logger.error("Erreur lors de la collecte : %s", exc, exc_info=True)
        logger.info("Prochaine collecte dans %d minutes…", args.interval)
        time.sleep(args.interval * 60)


if __name__ == "__main__":
    main()
