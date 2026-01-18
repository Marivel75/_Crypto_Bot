#!/usr/bin/env python3
"""
Script de planification des sauvegardes automatiques.
Utilise le scheduler pour exécuter des sauvegardes régulières.
"""

import schedule
import time
import subprocess
import logging
from pathlib import Path
from datetime import datetime

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/schedule_backups.log')
    ]
)
logger = logging.getLogger(__name__)

def run_backup():
    """Exécute le script de sauvegarde."""
    try:
        logger.info("🕒 Début de la sauvegarde planifiée")

        # Exécuter le script de sauvegarde
        result = subprocess.run(
            ["python", "scripts/backup_db.py"],
            capture_output=True,
            text=True,
            cwd="."
        )

        if result.returncode == 0:
            logger.info("✅ Sauvegarde planifiée réussie")
            logger.info(result.stdout)
        else:
            logger.error("❌ Échec de la sauvegarde planifiée")
            logger.error(result.stderr)

    except Exception as e:
        logger.error(f"❌ Erreur lors de la sauvegarde planifiée: {e}")

def main():
    """Point d'entrée principal pour la planification."""

    # Créer les répertoires nécessaires
    Path("logs").mkdir(parents=True, exist_ok=True)
    Path("backups").mkdir(parents=True, exist_ok=True)

    logger.info("🚀 Démarrage du planificateur de sauvegardes")

    # Planifier les sauvegardes
    # 1. Sauvegarde quotidienne à minuit
    schedule.every().day.at("00:00").do(run_backup)

    # 2. Sauvegarde toutes les 6 heures (pour les données critiques)
    schedule.every(6).hours.do(run_backup)

    logger.info("⏰ Planification configurée:")
    logger.info("  - Sauvegarde quotidienne à 00:00")
    logger.info("  - Sauvegarde toutes les 6 heures")

    # Exécuter une sauvegarde immédiate au démarrage
    run_backup()

    # Boucle principale
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Vérifier toutes les minutes

    except KeyboardInterrupt:
        logger.info("🛑 Planificateur arrêté par l'utilisateur")
    except Exception as e:
        logger.error(f"❌ Erreur dans le planificateur: {e}")
        raise

if __name__ == "__main__":
    main()
