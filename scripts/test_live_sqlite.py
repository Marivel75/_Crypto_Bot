#!/usr/bin/env python3
"""
Script pour tester le pipeline ETL avec des données réelles et SQLite.
"""

import sys
import os
from datetime import datetime

# Ajouter le dossier racine au chemin Python
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.collectors.market_collector import MarketCollector
# Ne pas importer get_db_engine ici pour éviter l'exécution au niveau du module
import logger_settings
logger = logger_settings.logger


def test_live_collection():
    """Teste la collecte de données réelles avec SQLite"""
    try:
        logger.info("Démarrage du test live avec SQLite")

        # Configuration pour test local
        config = {
            "exchange": "binance",  # Commencer avec Binance (le plus fiable)
            "pairs": ["BTCUSDT", "ETHUSDT"],  # 2 paires principales
            "timeframes": ["1h", "4h"],  # Timeframes raisonnables
        }

        logger.info(f"Configuration: {config}")

        # Initialiser le collecteur
        collector = MarketCollector(
            pairs=config["pairs"],
            timeframes=config["timeframes"],
            exchange=config["exchange"],
        )

        # Exécuter la collecte et le stockage
        logger.info("Début de la collecte des données...")
        start_time = datetime.now()

        collector.fetch_and_store()

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        logger.info(f"✅ Collecte terminée en {duration:.2f} secondes")

        # Vérifier les résultats
        # Importer ici pour éviter l'exécution au niveau du module
        from src.services.db import get_db_engine
        engine = get_db_engine()
        with engine.connect() as conn:
            from sqlalchemy import text

            result = conn.execute(text("SELECT COUNT(*) FROM ohlcv"))
            count = result.scalar()
            logger.info(f"📊 {count} enregistrements dans la base de données")

            if count > 0:
                # Afficher un échantillon
                sample = conn.execute(text("SELECT * FROM ohlcv LIMIT 3")).fetchall()
                logger.info("Échantillon de données:")
                for row in sample:
                    logger.info(f"  {row}")

        return True

    except Exception as e:
        logger.error(f"❌ Erreur lors du test live: {e}")
        import traceback

        traceback.print_exc()
        return False


def analyze_database():
    """Analyse la base de données SQLite"""
    try:
        # Importer ici pour éviter l'exécution au niveau du module
        from src.services.db import get_db_engine
        engine = get_db_engine()
        from sqlalchemy import text

        with engine.connect() as connection:
            # Statistiques de base
            stats = connection.execute(
                text(
                    """
                SELECT
                    COUNT(*) as total_records,
                    COUNT(DISTINCT symbol) as unique_symbols,
                    COUNT(DISTINCT timeframe) as unique_timeframes,
                    MIN(timestamp) as first_timestamp,
                    MAX(timestamp) as last_timestamp
                FROM ohlcv
            """
                )
            ).fetchone()

            if stats[0] > 0:
                logger.info("\n📊 Analyse de la base de données:")
                logger.info(f"  Total enregistrements: {stats[0]:,}")
                logger.info(f"  Symboles uniques: {stats[1]}")
                logger.info(f"  ⏱Timeframes uniques: {stats[2]}")
                logger.info(f"  Première donnée: {stats[3]}")
                logger.info(f"  Dernière donnée: {stats[4]}")

                # Vérification de la qualité des données
                # SQLite ne supporte pas COUNT(DISTINCT col1, col2, col3), donc nous utilisons une sous-requête
                quality = connection.execute(
                    text(
                        """
                    SELECT
                        SUM(CASE WHEN open <= 0 THEN 1 ELSE 0 END) as invalid_prices,
                        SUM(CASE WHEN volume < 0 THEN 1 ELSE 0 END) as negative_volumes,
                        COUNT(*) - (
                            SELECT COUNT(*)
                            FROM (
                                SELECT DISTINCT symbol, timeframe, timestamp
                                FROM ohlcv
                            )
                        ) as duplicate_timestamps
                    FROM ohlcv
                """
                    )
                ).fetchone()

                issues = []
                if quality[0] > 0:
                    issues.append(f"Prix invalides: {quality[0]}")
                if quality[1] > 0:
                    issues.append(f"Volumes négatifs: {quality[1]}")
                if quality[2] > 0:
                    issues.append(f"Timestamps dupliqués: {quality[2]}")

                if issues:
                    logger.warning(f"⚠️ Problèmes de qualité des données:")
                    for issue in issues:
                        logger.warning(f"  - {issue}")
                else:
                    logger.info("✅ Qualité des données: Parfaite!")

            else:
                logger.warning("⚠️ Aucune donnée dans la base de données")

    except Exception as e:
        logger.error(f"❌ Erreur lors de l'analyse: {e}")


if __name__ == "__main__":
    logger.info("🧪 Test Live SQLite - Crypto Bot")
    logger.info("=" * 50)

    # Exécuter le test live
    success = test_live_collection()

    if success:
        # Analyser les résultats
        analyze_database()
        logger.info("\nTest live terminé avec succès!")
    else:
        logger.error("\n❌ Test live échoué")
        sys.exit(1)
