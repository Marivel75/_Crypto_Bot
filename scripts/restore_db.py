#!/usr/bin/env python3
"""
Script de restauration de la base de données Crypto Bot.
Permet de restaurer à partir des différentes méthodes de sauvegarde.
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
        logging.FileHandler('logs/restore.log')
    ]
)
logger = logging.getLogger(__name__)

class DatabaseRestore:
    """Classe pour gérer la restauration de la base de données."""

    def __init__(self):
        """Initialise la connexion à la base de données."""
        from src.config import settings

        self.engine = create_engine(
            f"postgresql+psycopg2://{settings.POSTGRES_USER}:"
            f"{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:"
            f"{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
        )

        self.settings = settings
        logger.info("🔧 Initialisation du système de restauration")

    def list_backups(self):
        """Liste les sauvegardes disponibles."""
        backups = {
            'sql_dumps': [],
            'csv_backups': [],
            'essential_backups': []
        }

        backup_dir = Path("data/backups")
        if not backup_dir.exists():
            logger.warning("📁 Aucun répertoire de sauvegarde trouvé")
            return backups

        for file in backup_dir.glob('*'):
            if file.is_file():
                if 'full_backup' in file.name and file.suffix == '.sql':
                    backups['sql_dumps'].append(file.name)
                elif 'essential_backup' in file.name and file.suffix == '.json':
                    backups['essential_backups'].append(file.name)
            elif file.is_dir() and 'csv_' in file.name:
                backups['csv_backups'].append(file.name)

        logger.info("📋 Sauvegardes disponibles:")
        for backup_type, files in backups.items():
            logger.info(f"  {backup_type}: {len(files)} sauvegardes")
            for f in files:
                logger.info(f"    - {f}")

        return backups

    def restore_from_sql(self, backup_file):
        """Restaure à partir d'un dump SQL."""
        try:
            backup_path = Path("data/backups") / backup_file
            if not backup_path.exists():
                logger.error(f"❌ Fichier de sauvegarde non trouvé: {backup_file}")
                return False

            logger.info(f"🔄 Restauration SQL en cours depuis: {backup_file}")

            # Commande pg_restore
            cmd = [
                "pg_restore",
                "-h", self.settings.POSTGRES_HOST,
                "-p", self.settings.POSTGRES_PORT,
                "-U", self.settings.POSTGRES_USER,
                "-d", self.settings.POSTGRES_DB,
                "-c",  # Nettoyer avant restauration
                "-F", "c",
                str(backup_path)
            ]

            # Configuration de l'environnement
            env = os.environ.copy()
            env['PGPASSWORD'] = self.settings.POSTGRES_PASSWORD

            result = subprocess.run(cmd, env=env, capture_output=True, text=True)

            if result.returncode == 0:
                logger.info(f"✅ Restauration SQL réussie depuis: {backup_file}")
                return True
            else:
                logger.error(f"❌ Échec de la restauration SQL: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"❌ Erreur lors de la restauration SQL: {e}")
            return False

    def restore_from_csv(self, backup_dir):
        """Restaure à partir d'une sauvegarde CSV."""
        try:
            backup_path = Path("data/backups") / backup_dir
            if not backup_path.exists():
                logger.error(f"❌ Répertoire de sauvegarde non trouvé: {backup_dir}")
                return False

            logger.info(f"🔄 Restauration CSV en cours depuis: {backup_dir}")

            # Lire le fichier CSV
            csv_file = backup_path / "ohlcv.csv"
            if not csv_file.exists():
                logger.error(f"❌ Fichier CSV non trouvé: {csv_file}")
                return False

            df = pd.read_csv(csv_file)

            # Vider la table existante
            with self.engine.connect() as conn:
                conn.execute(text("TRUNCATE TABLE ohlcv"))
                conn.commit()

            # Insérer les nouvelles données
            df.to_sql('ohlcv', self.engine, if_exists='append', index=False)

            logger.info(f"✅ Restauration CSV réussie depuis: {backup_dir}")
            return True

        except Exception as e:
            logger.error(f"❌ Erreur lors de la restauration CSV: {e}")
            return False

    def verify_restore(self):
        """Vérifie l'intégrité des données après restauration."""
        try:
            with self.engine.connect() as conn:
                # Compter les enregistrements
                result = conn.execute(text("SELECT COUNT(*) FROM ohlcv"))
                count = result.scalar()

                # Vérifier les symboles
                result = conn.execute(text("SELECT DISTINCT symbol FROM ohlcv"))
                symbols = [row[0] for row in result]

                # Vérifier les timeframes
                result = conn.execute(text("SELECT DISTINCT timeframe FROM ohlcv"))
                timeframes = [row[0] for row in result]

            logger.info("🔍 Vérification de la restauration:")
            logger.info(f"  Nombre d'enregistrements: {count}")
            logger.info(f"  Symboles: {symbols}")
            logger.info(f"  Timeframes: {timeframes}")

            return count > 0

        except Exception as e:
            logger.error(f"❌ Erreur lors de la vérification: {e}")
            return False

if __name__ == "__main__":
    # Créer le répertoire de logs
    Path("logs").mkdir(parents=True, exist_ok=True)

    restore = DatabaseRestore()

    # Lister les sauvegardes disponibles
    backups = restore.list_backups()

    # Si des sauvegardes SQL existent, les utiliser en priorité
    if backups['sql_dumps']:
        latest_sql = sorted(backups['sql_dumps'])[-1]  # Dernière sauvegarde
        if restore.restore_from_sql(latest_sql):
            if restore.verify_restore():
                logger.info("✅ Restauration complète réussie")
            else:
                logger.error("❌ Vérification de la restauration échouée")
    elif backups['csv_backups']:
        latest_csv = sorted(backups['csv_backups'])[-1]  # Dernière sauvegarde
        if restore.restore_from_csv(latest_csv):
            if restore.verify_restore():
                logger.info("✅ Restauration CSV réussie")
            else:
                logger.error("❌ Vérification de la restauration échouée")
    else:
        logger.error("❌ Aucune sauvegarde disponible pour la restauration")
