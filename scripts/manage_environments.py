#!/usr/bin/env python3
"""
Script pour gérer les environnements de base de données.
Permet de créer, tester et basculer entre les environnements production et testing.
"""

import sys
import os
from pathlib import Path

# Ajouter le dossier racine au path pour les imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from src.services.db_environment import db_env, DatabaseEnvironment
from src.services.db import get_db_engine
from src.analytics.db_inspector import DBInspector
from logger_settings import logger


def show_environment_info():
    """Affiche des informations détaillées sur les environnements."""
    logger.info("📊 Information sur les environnements de base de données:")

    info = db_env.get_database_info()
    logger.info(f"Environnement actuel: {info['current_environment']}")
    logger.info(f"URL actuelle: {info['current_url']}")
    logger.info(f"Mode Production: {info['is_production']}")
    logger.info(f"Mode Testing: {info['is_testing']}")

    logger.info("\n📂 Configuration des environnements:")
    logger.info(f"Production: {info['production_url']}")
    logger.info(f"Testing: {info['testing_url']}")

    logger.info("\n💾 Bases de données existantes:")
    databases = db_env.list_databases()
    for env, db_info in databases.items():
        status = "✅ Existe" if db_info["exists"] else "❌ Absente"
        logger.info(f"{env.capitalize()}: {status} ({db_info['size_formatted']})")


def create_test_database():
    """Crée et initialise la base de données de test."""
    logger.info("🔧 Création de la base de données de test...")

    try:
        # Créer le moteur pour l'environnement de test
        engine = get_db_engine(environment="testing")

        # Initialiser l'inspecteur pour vérifier
        inspector = DBInspector()

        # Temporairement basculer vers testing pour inspection
        old_env = db_env.current_env
        db_env.set_environment("testing")

        logger.info("📋 Inspection de la base de test:")
        inspector.inspect_db()

        # Restaurer l'environnement original
        db_env.set_environment(old_env)

        logger.info("✅ Base de données de test créée avec succès")

    except Exception as e:
        logger.error(f"❌ Erreur lors de la création de la base de test: {e}")
        raise


def create_production_database():
    """Crée et initialise la base de données de production."""
    logger.info("🏭 Création de la base de données de production...")

    try:
        # Créer le moteur pour l'environnement de production
        engine = get_db_engine(environment="production")

        # Initialiser l'inspecteur pour vérifier
        inspector = DBInspector()

        # Temporairement basculer vers production pour inspection
        old_env = db_env.current_env
        db_env.set_environment("production")

        logger.info("📋 Inspection de la base de production:")
        inspector.inspect_db()

        # Restaurer l'environnement original
        db_env.set_environment(old_env)

        logger.info("✅ Base de données de production créée avec succès")

    except Exception as e:
        logger.error(f"❌ Erreur lors de la création de la base de production: {e}")
        raise


def switch_to_testing():
    """Bascule vers l'environnement de test."""
    logger.info("🔄 Basculement vers l'environnement de test...")
    db_env.set_environment("testing")
    logger.info(f"✅ Maintenant en mode testing: {db_env.get_current_db_url()}")


def switch_to_production():
    """Bascule vers l'environnement de production."""
    logger.info("🔄 Basculement vers l'environnement de production...")
    db_env.set_environment("production")
    logger.info(f"✅ Maintenant en mode production: {db_env.get_current_db_url()}")


def test_environments():
    """Teste les deux environnements."""
    logger.info("🧪 Test des environnements de base de données...")

    # Tester l'environnement de test
    logger.info("\n1️⃣ Test de l'environnement TESTING:")
    try:
        engine_test = get_db_engine("testing")
        inspector_test = DBInspector()

        # Temporairement basculer
        old_env = db_env.current_env
        db_env.set_environment("testing")
        inspector_test.inspect_db()
        db_env.set_environment(old_env)

        logger.info("✅ Environnement testing fonctionnel")
    except Exception as e:
        logger.error(f"❌ Erreur environnement testing: {e}")

    # Tester l'environnement de production
    logger.info("\n2️⃣ Test de l'environnement PRODUCTION:")
    try:
        engine_prod = get_db_engine("production")
        inspector_prod = DBInspector()

        # Temporairement basculer
        old_env = db_env.current_env
        db_env.set_environment("production")
        inspector_prod.inspect_db()
        db_env.set_environment(old_env)

        logger.info("✅ Environnement production fonctionnel")
    except Exception as e:
        logger.error(f"❌ Erreur environnement production: {e}")


def clean_test_database():
    """Nettoie (supprime) la base de données de test."""
    logger.info("🧹 Nettoyage de la base de données de test...")

    databases = db_env.list_databases()
    test_db_info = databases.get("testing")

    if not test_db_info or not test_db_info["exists"]:
        logger.warning("⚠️ Aucune base de données de test à supprimer")
        return

    try:
        os.remove(test_db_info["path"])
        logger.info(f"✅ Base de test supprimée: {test_db_info['path']}")
    except Exception as e:
        logger.error(f"❌ Erreur lors de la suppression: {e}")


def main():
    """Point d'entrée principal."""
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nUsage:")
        print("  python scripts/manage_environments.py <command>")
        print("\nCommandes disponibles:")
        print("  info           - Afficher les informations sur les environnements")
        print("  create-test    - Créer la base de données de test")
        print("  create-prod    - Créer la base de données de production")
        print("  switch-test    - Basculer vers l'environnement de test")
        print("  switch-prod    - Basculer vers l'environnement de production")
        print("  test           - Tester les deux environnements")
        print("  clean-test     - Supprimer la base de données de test")
        print("\nVariables d'environnement:")
        print("  CRYPTO_BOT_ENV=testing  - Force le mode testing")
        print("  CRYPTO_BOT_TEST=true   - Force le mode testing (alternative)")
        return

    command = sys.argv[1].lower()

    try:
        if command == "info":
            show_environment_info()
        elif command == "create-test":
            create_test_database()
        elif command == "create-prod":
            create_production_database()
        elif command == "switch-test":
            switch_to_testing()
        elif command == "switch-prod":
            switch_to_production()
        elif command == "test":
            test_environments()
        elif command == "clean-test":
            clean_test_database()
        else:
            logger.error(f"❌ Commande inconnue: {command}")
            sys.exit(1)

    except Exception as e:
        logger.error(f"❌ Erreur lors de l'exécution: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
