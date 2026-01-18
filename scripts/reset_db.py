#!/usr/bin/env python3
"""
Script pour réinitialiser complètement la base de données SQLite.
"""

import os
import sys
import shutil

# Ajouter le dossier racine au chemin Python
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Ne pas importer get_db_engine ici pour éviter l'exécution au niveau du module
from src.config.logger_settings import logger
def reset_database():
    """Réinitialise complètement la base de données"""
    try:
        logger.info("Réinitialisation de la base de données SQLite")

        # Supprimer l'ancien fichier de base de données
        db_path = "data/processed/crypto_data.db"
        if os.path.exists(db_path):
            os.remove(db_path)
            logger.info(f"✅ Ancienne base de données supprimée: {db_path}")

        # Supprimer et recréer les dossiers
        if os.path.exists("data/processed"):
            shutil.rmtree("data/processed")
        if os.path.exists("data/raw"):
            shutil.rmtree("data/raw")

        os.makedirs("data/processed", exist_ok=True)
        os.makedirs("data/raw", exist_ok=True)

        logger.info("Dossiers recréés")

        # Recréer la base de données avec les tables
        # Importer ici pour éviter l'exécution au niveau du module
        from src.services.db import get_db_engine
        engine = get_db_engine()
        logger.info("Nouvelle base de données SQLite créée")

        return True

    except Exception as e:
        logger.error(f"❌ Erreur lors de la réinitialisation: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    if reset_database():
        logger.info("Réinitialisation terminée avec succès!")
    else:
        logger.error("❌ Échec de la réinitialisation")
        exit(1)
