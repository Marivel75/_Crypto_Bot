#!/usr/bin/env python3
"""
Script pour exécuter les tests du projet Crypto Bot et générer des rapports.
"""

import subprocess
import sys
import argparse
from datetime import datetime


def run_tests(test_type="all", verbose=False, coverage=False, report=False):
    """
    Exécute les tests avec les options spécifiées.
    
    Args:
        test_type: Type de tests à exécuter (all, unit, validation, etl, integration)
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
        cmd.extend(["--cov=src", "--cov-report=term"])
    
    if report:
        cmd.append("--cov-report=html")
    
    # Sélectionner les tests
    if test_type == "unit":
        cmd.append("tests/test_market_collector.py")
    elif test_type == "validation":
        cmd.append("tests/test_data_validator.py")
    elif test_type == "etl":
        cmd.append("tests/test_etl_extractor.py")
        cmd.append("tests/test_etl_transformer.py")
        cmd.append("tests/test_etl_loader.py")
        cmd.append("tests/test_etl_pipeline.py")
    elif test_type == "integration":
        # Ajouter les tests d'intégration quand ils seront créés
        cmd.append("tests/integration/")
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
        choices=["all", "unit", "validation", "etl", "integration"],
        default="all",
        help="Type de tests à exécuter (défaut: all)"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Mode verbeux"
    )
    
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Générer un rapport de couverture"
    )
    
    parser.add_argument(
        "--report",
        action="store_true",
        help="Générer un rapport HTML (nécessite --coverage)"
    )
    
    args = parser.parse_args()
    
    print("🧪 Crypto Bot - Exécution des Tests")
    print("=" * 50)
    
    # Exécuter les tests
    success = run_tests(
        test_type=args.type,
        verbose=args.verbose,
        coverage=args.coverage,
        report=args.report
    )
    
    # Message final
    if success:
        print("\n✅ Tous les tests ont passé avec succès !")
    else:
        print("\n❌ Certains tests ont échoué")
        sys.exit(1)


if __name__ == "__main__":
    main()