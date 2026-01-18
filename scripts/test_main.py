#!/usr/bin/env python3
"""
Script complet pour tester toutes les fonctionnalités de main.py.
Teste la collecte OHLCV, les tickers, les multi-exchanges et les différents modes.
"""

import sys
import os
import time
import subprocess
from datetime import datetime

# Ajouter le dossier racine au chemin Python
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.config.logger_settings import logger
def test_ohlcv_collection():
    """Teste la collecte OHLCV comme dans le script original"""
    try:
        logger.info("🔍 Test de la collecte OHLCV")

        from src.collectors.ohlcv_collector import OHLCVCollector
        from src.services.db import get_db_engine
        from sqlalchemy import text

        # Configuration pour test local
        config = {
            "exchange": "binance",
            "pairs": ["BTCUSDT", "ETHUSDT"],
            "timeframes": ["1h", "4h"],
        }

        logger.info(f"Configuration OHLCV: {config}")

        # Initialiser et exécuter le collecteur
        collector = OHLCVCollector(
            pairs=config["pairs"],
            timeframes=config["timeframes"],
            exchange=config["exchange"],
        )

        start_time = datetime.now()
        collector.fetch_and_store()
        duration = (datetime.now() - start_time).total_seconds()

        logger.info(f"✅ Collecte OHLCV terminée en {duration:.2f} secondes")

        # Vérifier les résultats
        engine = get_db_engine()
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM ohlcv"))
            count = result.scalar()
            logger.info(f"📊 OHLCV - {count} enregistrements dans la base")

            if count > 0:
                sample = conn.execute(text("SELECT * FROM ohlcv LIMIT 2")).fetchall()
                logger.info("Échantillon OHLCV:")
                for row in sample:
                    logger.info(f"  {row}")

        return True

    except Exception as e:
        logger.error(f"❌ Erreur test OHLCV: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_ticker_collection():
    """Teste la collecte de ticker en temps réel"""
    try:
        logger.info("🔍 Test de la collecte de ticker")

        from src.collectors.ticker_collector import TickerCollector
        from src.services.db import get_db_engine
        from sqlalchemy import text

        # Configuration pour test local
        config = {
            "exchange": "binance",
            "pairs": ["BTC/USDT", "ETH/USDT"],
            "runtime_minutes": 2,  # Court pour le test
            "snapshot_interval": 1,
        }

        logger.info(f"Configuration Ticker: {config}")

        # Initialiser le collecteur de ticker
        collector = TickerCollector(
            pairs=config["pairs"],
            exchange=config["exchange"],
            snapshot_interval=config["snapshot_interval"],
            cache_size=100,
        )

        # Démarrer la collecte
        collector.start_collection()
        logger.info("✅ Collecteur de ticker démarré")

        # Laisser tourner pendant la durée spécifiée
        start_time = time.time()
        while time.time() - start_time < config["runtime_minutes"] * 60:
            # Afficher les prix actuels
            current_prices = collector.get_current_prices()
            if current_prices:
                logger.info(f"Prix actuels: {current_prices}")
            time.sleep(10)

        # Arrêter le collecteur
        collector.stop_collection()
        logger.info("✅ Collecteur de ticker arrêté")

        # Vérifier les résultats
        engine = get_db_engine()
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM ticker_snapshots"))
            count = result.scalar()
            logger.info(f"📊 Ticker - {count} snapshots dans la base")

            if count > 0:
                sample = conn.execute(
                    text("SELECT * FROM ticker_snapshots LIMIT 2")
                ).fetchall()
                logger.info("Échantillon Ticker:")
                for row in sample:
                    logger.info(f"  {row}")

        return True

    except Exception as e:
        logger.error(f"❌ Erreur test Ticker: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_multi_exchange():
    """Teste la collecte multi-exchanges"""
    try:
        logger.info("🔍 Test multi-exchanges")

        from src.collectors.ohlcv_collector import OHLCVCollector
        from src.services.db import get_db_engine
        from sqlalchemy import text

        # Tester plusieurs exchanges
        exchanges = ["binance", "kraken"]
        config = {
            "pairs": ["BTC/USDT"],
            "timeframes": ["1h"],
        }

        total_records = 0

        for exchange in exchanges:
            logger.info(f"Test {exchange}...")

            try:
                collector = OHLCVCollector(
                    pairs=config["pairs"],
                    timeframes=config["timeframes"],
                    exchange=exchange,
                )
                collector.fetch_and_store()

                # Compter les enregistrements pour cet exchange
                engine = get_db_engine()
                with engine.connect() as conn:
                    result = conn.execute(
                        text("SELECT COUNT(*) FROM ohlcv WHERE exchange = :exchange"),
                        {"exchange": exchange},
                    )
                    count = result.scalar()
                    logger.info(f"  {exchange}: {count} enregistrements")
                    total_records += count

            except Exception as e:
                logger.warning(f"  {exchange}: Échec - {e}")

        logger.info(f"✅ Multi-exchange: {total_records} enregistrements totaux")
        return True

    except Exception as e:
        logger.error(f"❌ Erreur test multi-exchange: {e}")
        return False


def analyze_database():
    """Analyse complète de la base de données"""
    try:
        from src.services.db import get_db_engine
        from sqlalchemy import text

        engine = get_db_engine()
        with engine.connect() as connection:
            # Statistiques OHLCV
            ohlcv_stats = connection.execute(
                text(
                    """
                    SELECT
                        COUNT(*) as total_records,
                        COUNT(DISTINCT symbol) as unique_symbols,
                        COUNT(DISTINCT timeframe) as unique_timeframes,
                        COUNT(DISTINCT exchange) as unique_exchanges,
                        MIN(timestamp) as first_timestamp,
                        MAX(timestamp) as last_timestamp
                    FROM ohlcv
                """
                )
            ).fetchone()

            # Statistiques Ticker
            ticker_stats = connection.execute(
                text(
                    """
                    SELECT
                        COUNT(*) as total_snapshots,
                        COUNT(DISTINCT symbol) as unique_symbols,
                        COUNT(DISTINCT exchange) as unique_exchanges,
                        MIN(snapshot_time) as first_snapshot,
                        MAX(snapshot_time) as last_snapshot
                    FROM ticker_snapshots
                """
                )
            ).fetchone()

            # Qualité des données OHLCV
            ohlcv_quality = connection.execute(
                text(
                    """
                    SELECT
                        SUM(CASE WHEN open <= 0 THEN 1 ELSE 0 END) as invalid_prices,
                        SUM(CASE WHEN volume < 0 THEN 1 ELSE 0 END) as negative_volumes,
                        COUNT(*) - (
                            SELECT COUNT(*)
                            FROM (SELECT DISTINCT symbol, timeframe, timestamp, exchange FROM ohlcv)
                        ) as duplicate_timestamps
                    FROM ohlcv
                """
                )
            ).fetchone()

            logger.info("\n📊 Analyse complète de la base de données:")
            logger.info("\nOHLCV Data:")
            logger.info(f"  Total enregistrements: {ohlcv_stats[0]:,}")
            logger.info(f"  Symboles uniques: {ohlcv_stats[1]}")
            logger.info(f"  Timeframes uniques: {ohlcv_stats[2]}")
            logger.info(f"  Exchanges uniques: {ohlcv_stats[3]}")
            logger.info(f"  Première donnée: {ohlcv_stats[4]}")
            logger.info(f"  Dernière donnée: {ohlcv_stats[5]}")

            logger.info("\nTicker Snapshots:")
            logger.info(f"  Total snapshots: {ticker_stats[0]:,}")
            logger.info(f"  Symboles uniques: {ticker_stats[1]}")
            logger.info(f"  Exchanges uniques: {ticker_stats[2]}")
            logger.info(f"  Premier snapshot: {ticker_stats[3]}")
            logger.info(f"  Dernier snapshot: {ticker_stats[4]}")

            # Rapport de qualité
            issues = []
            if ohlcv_quality[0] > 0:
                issues.append(f"Prix invalides: {ohlcv_quality[0]}")
            if ohlcv_quality[1] > 0:
                issues.append(f"Volumes négatifs: {ohlcv_quality[1]}")
            if ohlcv_quality[2] > 0:
                issues.append(f"Timestamps dupliqués: {ohlcv_quality[2]}")

            if issues:
                logger.warning("\n⚠️ Problèmes de qualité OHLCV:")
                for issue in issues:
                    logger.warning(f"  - {issue}")
            else:
                logger.info("\n✅ Qualité des données OHLCV: Parfaite!")

    except Exception as e:
        logger.error(f"❌ Erreur analyse base: {e}")


def main():
    """Point d'entrée principal"""
    logger.info("🧪 Test Main - Crypto Bot")
    logger.info("=" * 50)

    # Exécuter tous les tests
    tests = [
        ("Collecte OHLCV", test_ohlcv_collection),
        ("Collecte Ticker", test_ticker_collection),
        ("Multi-Exchange", test_multi_exchange),
    ]

    results = {}

    for test_name, test_func in tests:
        logger.info(f"\n{'='*50}")
        logger.info(f"📋 {test_name}")
        logger.info("=" * 50)

        try:
            success = test_func()
            results[test_name] = success
        except Exception as e:
            logger.error(f"❌ {test_name} a échoué: {e}")
            results[test_name] = False

    # Analyse finale
    logger.info(f"\n{'='*50}")
    logger.info("📊 Résumé des tests")
    logger.info("=" * 50)

    for test_name, success in results.items():
        status = "✅ PASSÉ" if success else "❌ ÉCHOUE"
        logger.info(f"{status}: {test_name}")

    # Analyse de la base de données
    analyze_database()

    # Résumé final
    passed = sum(1 for success in results.values() if success)
    total = len(results)

    logger.info(f"\n{'='*50}")
    logger.info(f"Résultat final: {passed}/{total} tests passés")

    if passed == total:
        logger.info("✅ Tous les tests ont réussi !")
        return True
    else:
        logger.error("❌ Certains tests ont échoué")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
