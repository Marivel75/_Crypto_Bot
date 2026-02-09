#!/usr/bin/env python3
"""
Script pour exécuter les tests du projet Crypto Bot avec base de données isolée.
Ce script garantit que les tests n'affectent jamais la base de production.
"""

import subprocess
import sys
import os
import argparse
from datetime import datetime

# Ajouter le dossier racine au path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

import logger_settings

logger = logger_settings.logger

def setup_test_environment():
    """
    Configure l'environnement de test isolé.
    """
    logger.info("🧪 Configuration de l'environnement de test isolé")
    os.environ["CRYPTO_BOT_ENV"] = "testing"
    logger.info("✅ CRYPTO_BOT_ENV forcé à 'testing'")
    return True

def run_tests(
    test_type="all", verbose=False, coverage=False, report=False, ignore_warnings=True
):
    """
    Exécute les tests avec les options spécifiées.

    Args:
        test_type: Type de tests à exécuter (all, unit, validation, etl, integration)
        verbose: Mode verbeux
        coverage: Générer un rapport de couverture
        report: Générer un rapport HTML
        ignore_warnings: Ignorer les warnings
    """
    # Commande de base
    cmd = [sys.executable, "-m", "pytest"]

    # Ajouter les options
    if verbose:
        cmd.append("-v")
    else:
        cmd.append("-q")  # Mode silencieux par défaut pour CI/CD

    if coverage:
        cmd.extend(["--cov=src", "--cov-report=term-missing"])
    else:
        cmd.append("--disable-warnings")

    if report and coverage:
        cmd.append("--cov-report=html")

    # Sélectionner les tests
    if test_type == "all":
        cmd.append("tests/")
    elif test_type == "unit":
        unit_files = [
            "tests/test_data_validator.py",
            "tests/test_ohlcv_collector.py",
            "tests/test_etl_extractor.py",
            "tests/test_etl_transformer.py",
            "tests/test_etl_loader.py",
            "tests/test_etl_pipeline.py",
        ]
        existing_unit_files = [f for f in unit_files if os.path.exists(f)]
        if existing_unit_files:
            cmd.extend(existing_unit_files)
        else:
            logger.info("💡 Aucun test unitaire trouvé, exécution de tous les tests")
            cmd.append("tests/")
    elif test_type == "validation":
        validation_files = ["tests/test_data_validator.py"]
        existing_files = [f for f in validation_files if os.path.exists(f)]
        if existing_files:
            cmd.extend(existing_files)
        else:
            logger.info("💡 Aucun test de validation trouvé, exécution de tous les tests")
            cmd.append("tests/")
    elif test_type == "etl":
        etl_files = [
            "tests/test_etl_extractor.py",
            "tests/test_etl_transformer.py",
            "tests/test_etl_loader.py",
            "tests/test_etl_pipeline.py",
        ]
        existing_etl_files = [f for f in etl_files if os.path.exists(f)]
        if existing_etl_files:
            cmd.extend(existing_etl_files)
        else:
            logger.info("💡 Aucun test ETL trouvé, exécution de tous les tests")
            cmd.append("tests/")
    elif test_type == "integration":
        integration_files = [
            "tests/test_scheduler_integration.py",
            "tests/test_ticker_service.py",
        ]
        existing_files = [f for f in integration_files if os.path.exists(f)]
        if existing_files:
            cmd.extend(existing_files)
        else:
            logger.info("💡 Aucun test d'intégration spécifique trouvé, exécution de tous les tests")
            cmd.append("tests/")
    else:
        cmd.append("tests/")

    # Forcer l'environnement avant d'exécuter les tests
    env = os.environ.copy()
    env["CRYPTO_BOT_ENV"] = "testing"

    logger.info(f"🚀 Exécution des tests: {' '.join(cmd)}")
    logger.info(f"🔒 Base de test isolée activée")

    try:
        # Exécuter directement pytest avec l'environnement forcé
        result = subprocess.run(cmd, env=env, cwd=project_root)
        return result.returncode == 0
    except Exception as e:
        logger.error(f"❌ Erreur lors de l'exécution des tests: {e}")
        return False

def main():
    """Point d'entrée principal."""
    parser = argparse.ArgumentParser(
        description="Script pour exécuter les tests Crypto Bot (base de test isolée)"
    )

    parser.add_argument(
        "--type",
        choices=["all", "unit", "validation", "etl", "integration"],
        default="all",
        help="Type de tests à exécuter (défaut: all)",
    )

    parser.add_argument("--verbose", action="store_true", help="Mode verbeux")
    parser.add_argument(
        "--coverage", action="store_true", help="Générer un rapport de couverture"
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Générer un rapport HTML (nécessite --coverage)",
    )

    args = parser.parse_args()

    print("🧪 Crypto Bot - Exécution des Tests (Base Isolée)")
    print("=" * 60)

    try:
        # 1. Configurer l'environnement de test
        setup_test_environment()

        # 2. Exécuter les tests
        success = run_tests(
            test_type=args.type,
            verbose=args.verbose,
            coverage=args.coverage,
            report=args.report,
        )

        # 3. Afficher le résumé final
        print("\n" + "=" * 60)

        if success:
            print("✅ Tous les tests ont passé avec succès !")
        else:
            print("❌ Certains tests ont échoué")
            sys.exit(1)

    except Exception as e:
        logger.error(f"❌ Erreur fatale lors de l'exécution: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
