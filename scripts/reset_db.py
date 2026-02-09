#!/usr/bin/env python3
"""
Script pour réinitialiser complètement la base de données SQLite.
Supporte maintenant les environnements de test et de production.
"""

import os
import sys
import shutil
import argparse

# Ajouter le dossier racine au chemin Python
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Importer les modules nécessaires
import logger_settings
from src.services.db_environment import db_env

logger = logger_settings.logger


def reset_database(environment=None):
    """
    Réinitialise complètement la base de données SQLite pour l'environnement spécifié.

    Args:
        environment: Environnement à réinitialiser (production/testing, None utilise l'env actuel)
    """
    try:
        if environment:
            target_env = environment
            logger.info(f"Réinitialisation de la base de données '{environment}'")
        else:
            target_env = db_env.current_env
            logger.info(
                f"Réinitialisation de la base de données '{db_env.current_env}'"
            )

        # Obtenir l'URL et le chemin pour l'environnement cible
        db_url = db_env.get_db_url(target_env)
        if db_url.startswith("sqlite:///"):
            db_path = db_url.replace("sqlite:///", "")
        else:
            logger.error("❌ Seul SQLite est supporté pour la réinitialisation")
            return False

        # Supprimer l'ancien fichier de base de données
        if os.path.exists(db_path):
            os.remove(db_path)
            logger.info(f"✅ Ancienne base de données supprimée: {db_path}")

        # S'assurer que le répertoire existe
        db_dir = os.path.dirname(db_path)
        os.makedirs(db_dir, exist_ok=True)
        logger.info(f"Répertoire assuré: {db_dir}")

        # Recréer la base de données avec les tables
        # Importer ici pour éviter l'exécution au niveau du module
        from src.services.db import get_db_engine

        engine = get_db_engine(environment=target_env)
        logger.info(f"✅ Nouvelle base de données créée pour {target_env}: {db_url}")

        return True

    except Exception as e:
        logger.error(f"❌ Erreur lors de la réinitialisation: {e}")
        import traceback

        traceback.print_exc()
        return False


def reset_all_databases():
    """Réinitialise toutes les bases de données (production et testing)."""
    logger.info("🔄 Réinitialisation de toutes les bases de données...")

    results = {}

    # Réinitialiser la base de production
    logger.info("\n1️⃣ Réinitialisation de la base de production:")
    results["production"] = reset_database("production")

    # Réinitialiser la base de test
    logger.info("\n2️⃣ Réinitialisation de la base de test:")
    results["testing"] = reset_database("testing")

    # Résumé
    logger.info("\n📊 Résumé de la réinitialisation:")
    for env, success in results.items():
        status = "✅ Succès" if success else "❌ Échec"
        logger.info(f"  {env.capitalize()}: {status}")

    return all(results.values())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Réinitialiser la base de données Crypto Bot"
    )
    parser.add_argument(
        "--env",
        choices=["production", "testing", "all"],
        help="Environnement à réinitialiser (défaut: actuel)",
    )
    parser.add_argument(
        "--all", action="store_true", help="Réinitialiser toutes les bases de données"
    )

    args = parser.parse_args()

    try:
        if args.all or args.env == "all":
            success = reset_all_databases()
        elif args.env:
            success = reset_database(args.env)
        else:
            success = reset_database()  # Utilise l'environnement actuel

        if success:
            logger.info("✅ Réinitialisation terminée avec succès!")
        else:
            logger.error("❌ Échec de la réinitialisation")
            exit(1)

    except Exception as e:
        logger.error(f"❌ Erreur lors de la réinitialisation: {e}")
        exit(1)
