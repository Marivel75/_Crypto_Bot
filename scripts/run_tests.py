#!/usr/bin/env python3
"""
Script pour exécuter les tests en utilisant une base de données isolée.
Ce script garantit que les tests n'affectent pas la base de production.
"""

import sys
import os
import subprocess
from pathlib import Path

# Ajouter le dossier racine au path pour les imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from src.services.db_environment import db_env
import logger_settings

logger = logger_settings.logger


def setup_test_environment():
    """
    Configure l'environnement de test avant d'exécuter les tests.
    """
    logger.info("🧪 Configuration de l'environnement de test")

    # Forcer l'environnement de test
    db_env.set_environment("testing")

    # S'assurer que la base de test existe
    from src.services.db import get_db_engine

    try:
        engine = get_db_engine("testing")
        logger.info("✅ Base de données de test prête")
    except Exception as e:
        logger.error(f"❌ Erreur lors de la préparation de la base de test: {e}")
        raise

    # Afficher les informations sur l'environnement
    info = db_env.get_database_info()
    logger.info(f"📊 Tests utiliseront: {info['current_url']}")
    logger.info(f"🔒 Base de production protégée: {info['production_url']}")


def run_pytest_tests(test_args=None):
    """
    Exécute les tests pytest avec l'environnement de test configuré.

    Args:
        test_args: Arguments supplémentaires pour pytest
    """
    if test_args is None:
        test_args = []

    # Arguments par défaut pour pytest
    default_args = [
        "tests/",
        "-v",
        "--tb=short",
        "--strict-markers",
    ]

    # Combiner les arguments
    all_args = default_args + test_args

    logger.info(f"🚀 Exécution des tests avec: {' '.join(all_args)}")

    try:
        # Exécuter pytest avec l'environnement configuré
        env = os.environ.copy()
        env["CRYPTO_BOT_ENV"] = "testing"  # Force l'environnement de test

        result = subprocess.run(
            [sys.executable, "-m", "pytest"] + all_args,
            cwd=project_root,
            env=env,
            capture_output=False,
        )

        return result.returncode == 0

    except Exception as e:
        logger.error(f"❌ Erreur lors de l'exécution des tests: {e}")
        return False


def run_coverage_tests():
    """
    Exécute les tests avec génération de rapport de couverture.
    """
    logger.info("📊 Exécution des tests avec rapport de couverture")

    coverage_args = [
        "--cov=src",
        "--cov-report=html",
        "--cov-report=term-missing",
        "--cov-fail-under=80",
    ]

    return run_pytest_tests(coverage_args)


def run_unit_tests_only():
    """
    Exécute uniquement les tests unitaires.
    """
    logger.info("🧪 Exécution des tests unitaires uniquement")

    unit_args = ["-m", "not integration", "tests/test_*"]

    return run_pytest_tests(unit_args)


def run_integration_tests_only():
    """
    Exécute uniquement les tests d'intégration.
    """
    logger.info("🔗 Exécution des tests d'intégration uniquement")

    integration_args = ["-m", "integration", "tests/test_*"]

    return run_pytest_tests(integration_args)


def show_test_environment_info():
    """Affiche des informations sur l'environnement de test."""
    logger.info("📊 Information sur l'environnement de test:")

    info = db_env.get_database_info()
    databases = db_env.list_databases()

    logger.info(f"Environnement actuel: {info['current_environment']}")
    logger.info(f"Base de test: {info['testing_url']}")
    logger.info(f"Base de test existe: {databases['testing']['exists']}")
    logger.info(f"Taille base de test: {databases['testing']['size_formatted']}")
    logger.info(f"Base de production: {info['production_url']}")
    logger.info(f"Base de production protégée: {databases['production']['exists']}")


def main():
    """Point d'entrée principal."""
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nUsage:")
        print("  python scripts/run_isolated_tests.py <command> [options]")
        print("\nCommandes disponibles:")
        print("  test           - Exécuter tous les tests")
        print("  coverage       - Exécuter les tests avec couverture")
        print("  unit           - Exécuter uniquement les tests unitaires")
        print("  integration    - Exécuter uniquement les tests d'intégration")
        print("  info           - Afficher les informations sur l'environnement")
        print("  setup          - Préparer uniquement l'environnement de test")
        print("\nExemples:")
        print("  python scripts/run_isolated_tests.py test")
        print("  python scripts/run_isolated_tests.py coverage")
        print("  python scripts/run_isolated_tests.py unit")
        print("  CRYPTO_BOT_ENV=testing python scripts/run_isolated_tests.py test")
        return

    command = sys.argv[1].lower()

    try:
        # Toujours configurer l'environnement de test
        if command != "info":
            setup_test_environment()

        success = False

        if command == "test":
            success = run_pytest_tests()
        elif command == "coverage":
            success = run_coverage_tests()
        elif command == "unit":
            success = run_unit_tests_only()
        elif command == "integration":
            success = run_integration_tests_only()
        elif command == "info":
            show_test_environment_info()
            return
        elif command == "setup":
            logger.info("✅ Environnement de test configuré")
            return
        else:
            logger.error(f"❌ Commande inconnue: {command}")
            sys.exit(1)

        if success:
            logger.info("✅ Tests terminés avec succès!")

            # Afficher l'état final des bases de données
            databases = db_env.list_databases()
            test_db = databases.get("testing", {})

            if test_db.get("exists"):
                logger.info(f"📊 Base de test utilisée: {test_db['size_formatted']}")

            production_db = databases.get("production", {})
            if production_db.get("exists"):
                logger.info(
                    f"🏭 Base de production intacte: {production_db['size_formatted']}"
                )

        else:
            logger.error("❌ Échec des tests")
            sys.exit(1)

    except Exception as e:
        logger.error(f"❌ Erreur lors de l'exécution: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
