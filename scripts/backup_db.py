#!/usr/bin/env python3
"""
Script de sauvegarde automatique de la base de données Crypto Bot.
Propose plusieurs méthodes de sauvegarde : SQL dump, CSV, et sauvegarde des données essentielles.
"""

import sys
import os
import subprocess
from datetime import datetime
import pandas as pd
from sqlalchemy import create_engine, text
import logging
from pathlib import Path

# Ajouter le chemin racine au PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/backup.log')
    ]
)
logger = logging.getLogger(__name__)

# Configuration
BACKUP_DIR = "data/backups"
MAX_BACKUPS = 7  # Garder les sauvegardes des 7 derniers jours

class DatabaseBackup:
    """Classe pour gérer les sauvegardes de la base de données."""

    def __init__(self):
        """Initialise la connexion à la base de données."""
        from src.config import settings

        self.engine = create_engine(
            f"postgresql+psycopg2://{settings.POSTGRES_USER}:"
            f"{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:"
            f"{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
        )

        # Créer le répertoire de sauvegarde
        Path(BACKUP_DIR).mkdir(parents=True, exist_ok=True)
        logger.info(f"📁 Répertoire de sauvegarde: {os.path.abspath(BACKUP_DIR)}")

    def backup_sql_dump(self):
        """Sauvegarde complète via pg_dump (méthode la plus fiable)."""
        from src.config import settings

        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = f"{BACKUP_DIR}/full_backup_{timestamp}.sql"

            # Commande pg_dump
            cmd = [
                "pg_dump",
                "-h", settings.POSTGRES_HOST,
                "-p", settings.POSTGRES_PORT,
                "-U", settings.POSTGRES_USER,
                "-d", settings.POSTGRES_DB,
                "-F", "c",
                "-f", backup_file
            ]

            # Configuration de l'environnement pour pg_dump
            env = os.environ.copy()
            env['PGPASSWORD'] = settings.POSTGRES_PASSWORD

            logger.info(f"🔄 Sauvegarde SQL en cours: {backup_file}")
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)

            if result.returncode == 0:
                logger.info(f"✅ Sauvegarde SQL réussie: {backup_file}")
                return backup_file
            else:
                logger.error(f"❌ Échec de la sauvegarde SQL: {result.stderr}")
                return None

        except Exception as e:
            logger.error(f"❌ Erreur lors de la sauvegarde SQL: {e}")
            return None

    def backup_csv(self):
        """Sauvegarde des données essentielles en CSV."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = f"{BACKUP_DIR}/csv_{timestamp}"
            Path(backup_dir).mkdir(parents=True, exist_ok=True)

            logger.info(f"🔄 Sauvegarde CSV en cours: {backup_dir}")

            # Sauvegarder la table ohlcv
            df = pd.read_sql('SELECT * FROM ohlcv', self.engine)
            csv_file = f"{backup_dir}/ohlcv.csv"
            df.to_csv(csv_file, index=False)

            logger.info(f"✅ Sauvegarde CSV réussie: {csv_file}")
            return backup_dir

        except Exception as e:
            logger.error(f"❌ Erreur lors de la sauvegarde CSV: {e}")
            return None

    def backup_essential_data(self):
        """Sauvegarde des données essentielles dans un fichier compact."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = f"{BACKUP_DIR}/essential_backup_{timestamp}.json"

            # Récupérer les données essentielles
            query = """
                SELECT symbol, timeframe, COUNT(*) as count,
                       MIN(timestamp) as first_date,
                       MAX(timestamp) as last_date,
                       AVG(close) as avg_price,
                       SUM(volume) as total_volume
                FROM ohlcv
                GROUP BY symbol, timeframe
                ORDER BY symbol, timeframe
            """

            df = pd.read_sql(query, self.engine)
            df.to_json(backup_file, orient='records', indent=2)

            logger.info(f"✅ Sauvegarde des données essentielles réussie: {backup_file}")
            return backup_file

        except Exception as e:
            logger.error(f"❌ Erreur lors de la sauvegarde des données essentielles: {e}")
            return None

    def cleanup_old_backups(self):
        """Nettoyage des anciennes sauvegardes."""
        try:
            # Lister tous les fichiers de sauvegarde
            backup_files = []
            for file in Path(BACKUP_DIR).glob('*'):
                if file.is_file() and 'backup' in file.name:
                    backup_files.append((file, file.stat().st_mtime))

            # Trier par date (ancien en premier)
            backup_files.sort(key=lambda x: x[1])

            # Supprimer les sauvegardes excédentaires
            while len(backup_files) > MAX_BACKUPS:
                old_file, _ = backup_files.pop(0)
                old_file.unlink()
                logger.info(f"🗑️ Suppression de l'ancienne sauvegarde: {old_file.name}")

        except Exception as e:
            logger.error(f"❌ Erreur lors du nettoyage: {e}")

    def full_backup(self):
        """Exécute une sauvegarde complète avec toutes les méthodes."""
        logger.info("🚀 Début de la sauvegarde complète")

        results = {
            'sql_dump': self.backup_sql_dump(),
            'csv': self.backup_csv(),
            'essential': self.backup_essential_data()
        }

        # Nettoyage
        self.cleanup_old_backups()

        # Résumé
        successful = sum(1 for result in results.values() if result is not None)
        logger.info(f"✅ Sauvegarde terminée: {successful}/3 méthodes réussies")

        return results

if __name__ == "__main__":
    # Créer le répertoire de logs
    Path("logs").mkdir(parents=True, exist_ok=True)

    backup = DatabaseBackup()
    backup.full_backup()
