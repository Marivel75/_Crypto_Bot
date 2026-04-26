#!/usr/bin/env python3
"""
Script pour exécuter les tests du projet Crypto Bot et générer des rapports.
"""

import subprocess
import sys
import argparse
from datetime import datetime


def run_tests(
    test_type="all", verbose=False, coverage=False, report=False, ignore_warnings=True
):
    """
    Exécute les tests avec les options spécifiées.

    Args:
        test_type: Type de tests à exécuter (all, unit, validation, etl, ml, api, frontend)
        verbose: Mode verbeux
        coverage: Générer un rapport de couverture
        report: Générer un rapport HTML
    """

    # Commande de base
    cmd = [sys.executable, "-m", "pytest"]

    # Ajouter les options
    if verbose:
        cmd.append("-v")

    if coverage:
        cmd.extend(["--cov=src", "--cov=api", "--cov=frontend", "--cov-report=term"])

    if report:
        cmd.append("--cov-report=html")

    if ignore_warnings:
        cmd.append("--disable-pytest-warnings")

    # Sélectionner les tests
    if test_type == "unit":
        cmd.append("tests/test_ohlcv_collector.py")
        cmd.append("tests/test_ticker_service.py")
    elif test_type == "validation":
        cmd.append("tests/test_data_validator.py")
    elif test_type == "etl":
        cmd.append("tests/test_etl_extractor.py")
        cmd.append("tests/test_etl_transformer.py")
        cmd.append("tests/test_etl_loader.py")
        cmd.append("tests/test_etl_pipeline.py")
    elif test_type == "ml":
        cmd.append("tests/test_feature_builder.py")
        cmd.append("tests/test_dataset_builder.py")
        cmd.append("tests/test_baseline.py")
        cmd.append("tests/test_evaluator.py")
        cmd.append("tests/test_backtester.py")
    elif test_type == "api":
        cmd.append("tests/test_api.py")
    elif test_type == "frontend":
        cmd.append("tests/test_frontend_utils.py")
        cmd.append("tests/test_frontend_api_client.py")
        cmd.append("tests/test_frontend_components.py")
    elif test_type == "news":
        cmd.append("tests/test_news_collector.py")
    elif test_type == "fear":
        cmd.append("tests/test_fear_greed_collector.py")
    else:
        cmd.append("tests/")

    # Exécuter la commande
    print(f"🚀 Exécution des tests: {' '.join(cmd)}")
    result = subprocess.run(cmd)

    return result.returncode == 0


def main():
    """Point d'entrée principal."""

    parser = argparse.ArgumentParser(
        description="Script pour exécuter les tests Crypto Bot"
    )

    parser.add_argument(
        "--type",
        choices=["all", "unit", "validation", "etl", "ml", "api", "frontend", "news", "fear"],
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

    print("🧪 Crypto Bot - Exécution des Tests")
    print("=" * 50)

    # Exécuter les tests
    success = run_tests(
        test_type=args.type,
        verbose=args.verbose,
        coverage=args.coverage,
        report=args.report,
    )

    # Message final
    if success:
        print("\n✅ Tous les tests ont passé avec succès !")
    else:
        print("\n❌ Certains tests ont échoué")
        sys.exit(1)


if __name__ == "__main__":
    main()
