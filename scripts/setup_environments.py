#!/usr/bin/env python3
"""
Script pour initialiser les environnements de base de données.
Crée les bases production et testing avec vérification.
"""

import sys
import os
from pathlib import Path

# Ajouter le dossier racine au path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from src.services.db_environment import db_env
from src.services.db import get_db_engine
from src.analytics.db_inspector import DBInspector
from logger_settings import logger


def setup_initial_environments():
    """
    Configure les environnements initiaux pour un nouveau projet.
    """
    logger.info("🚀 Configuration initiale des environnements Crypto Bot")

    try:
        # 1. Créer les répertoires
        logger.info("1️⃣ Création des répertoires...")
        db_env.ensure_directories()
        logger.info("✅ Répertoires créés")

        # 2. Créer la base de production
        logger.info("\n2️⃣ Configuration de l'environnement de production...")
        production_engine = get_db_engine("production")
        logger.info("✅ Base de production créée")

        # 3. Créer la base de test
        logger.info("\n3️⃣ Configuration de l'environnement de test...")
        testing_engine = get_db_engine("testing")
        logger.info("✅ Base de test créée")

        # 4. Vérification
        logger.info("\n4️⃣ Vérification des environnements...")

        # Vérifier production
        old_env = db_env.current_env
        db_env.set_environment("production")
        inspector_prod = DBInspector()
        inspector_prod.inspect_db()

        # Vérifier testing
        db_env.set_environment("testing")
        inspector_test = DBInspector()
        inspector_test.inspect_db()

        # Restaurer l'environnement original
        db_env.set_environment(old_env)

        # 5. Afficher le résumé
        logger.info("\n📊 Résumé de la configuration:")
        info = db_env.get_database_info()
        databases = db_env.list_databases()

        logger.info(f"Environnement actuel: {info['current_environment']}")
        logger.info(f"Base de production: {info['production_url']}")
        logger.info(f"Base de test: {info['testing_url']}")

        for env, db_info in databases.items():
            status = "✅ Créée" if db_info["exists"] else "❌ Manquante"
            logger.info(f"  {env.capitalize()}: {status} ({db_info['size_formatted']})")

        logger.info("\n🎯 Prochaines étapes:")
        logger.info("1. Pour la collecte quotidienne:")
        logger.info("   export CRYPTO_BOT_ENV=production")
        logger.info("   python main.py --schedule")
        logger.info("")
        logger.info("2. Pour exécuter les tests:")
        logger.info("   python scripts/run_isolated_tests.py test")
        logger.info("")
        logger.info("3. Pour vérifier les environnements:")
        logger.info("   python scripts/manage_environments.py info")

        logger.info("\n✅ Configuration initiale terminée avec succès!")

    except Exception as e:
        logger.error(f"❌ Erreur lors de la configuration initiale: {e}")
        raise


if __name__ == "__main__":
    setup_initial_environments()
