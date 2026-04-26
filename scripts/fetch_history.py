#!/usr/bin/env python3
"""Collecte de l'historique OHLCV complet (jusqu'à 1000 bougies par paire).

Binance retourne jusqu'à 1000 bougies par requête :
  - timeframe 1d  → ~2.7 ans
  - timeframe 4h  → ~166 jours
  - timeframe 1h  → ~42 jours

Usage:
    python scripts/fetch_history.py                         # toutes les paires du config
    python scripts/fetch_history.py --limit 500             # 500 bougies
    python scripts/fetch_history.py --exchange binance      # un seul exchange
    python scripts/fetch_history.py --timeframes 1d 4h      # timeframes spécifiques
"""

import sys
import time
import argparse
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config.settings import config
from src.quality.validator import DataValidator0HCLV
from src.services.exchange_factory import ExchangeFactory
from src.services.exchange_context import ExchangeClient
from src.services.db_context import database_transaction
from src.etl.ohlcv_pipeline.extractor import OHLCVExtractor
from src.etl.ohlcv_pipeline.transformer import OHLCVTransformer
from src.etl.ohlcv_pipeline.loader import OHLCVLoader
from src.etl.ohlcv_pipeline.pipeline_ohlcv import ETLPipelineOHLCV

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


def fetch_history(
    pairs: list[str],
    timeframes: list[str],
    exchanges: list[str],
    limit: int,
) -> None:
    total = len(pairs) * len(timeframes) * len(exchanges)
    done = 0

    for exchange in exchanges:
        for timeframe in timeframes:
            logger.info("Exchange=%s  timeframe=%s  limit=%d", exchange, timeframe, limit)
            try:
                validator = DataValidator0HCLV()
                client_obj = ExchangeFactory.create_exchange(exchange)
                extractor = OHLCVExtractor(client_obj)
                transformer = OHLCVTransformer(validator, exchange)
                loader = OHLCVLoader(None)
                pipeline = ETLPipelineOHLCV(extractor, transformer, loader)

                with ExchangeClient(exchange) as client:
                    with database_transaction():
                        pipeline.extractor.client = client
                        results = pipeline.run_batch(pairs, timeframe, limit=limit)

                for symbol, result in results.items():
                    done += 1
                    status = "OK" if result.success else f"ERREUR: {result.error}"
                    logger.info(
                        "[%d/%d] %s/%s/%s → %s (%d bougies)",
                        done, total, exchange, symbol, timeframe,
                        status, result.loaded_rows if result.success else 0,
                    )

            except Exception as exc:
                logger.error("Échec exchange=%s timeframe=%s : %s", exchange, timeframe, exc)

            time.sleep(1)

    logger.info("Collecte historique terminée.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Collecte historique OHLCV")
    parser.add_argument(
        "--limit", type=int, default=1000,
        help="Nombre de bougies par paire (max 1000 sur Binance, défaut: 1000)",
    )
    parser.add_argument(
        "--exchange", nargs="+", default=None,
        help="Exchange(s) à utiliser (défaut: ceux du config)",
    )
    parser.add_argument(
        "--timeframes", nargs="+", default=None,
        help="Timeframes à collecter (défaut: ceux du config)",
    )
    parser.add_argument(
        "--pairs", nargs="+", default=None,
        help="Paires à collecter (défaut: celles du config)",
    )
    args = parser.parse_args()

    pairs = args.pairs or config.get("pairs")
    timeframes = args.timeframes or config.get("timeframes")
    exchanges = args.exchange or config.get("exchanges")

    logger.info(
        "Démarrage collecte historique | exchanges=%s | paires=%s | timeframes=%s | limit=%d",
        exchanges, pairs, timeframes, args.limit,
    )

    fetch_history(pairs, timeframes, exchanges, args.limit)


if __name__ == "__main__":
    main()
