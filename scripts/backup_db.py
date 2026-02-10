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
from pathlib import Path

# Ajouter le chemin racine au PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importer le logger centralisé
import logging
from logger_settings import logger

# Configuration
BACKUP_DIR = "data/backups"
MAX_BACKUPS = 7  # Garder les sauvegardes des 7 derniers jours


class DatabaseBackup:
    """Classe pour gérer les sauvegardes de la base de données."""

    def __init__(self):
        """Initialise la connexion à la base de données."""
        from config.settings import config

        self.db_url = config.get("database.url")
        self.engine = create_engine(self.db_url)

        # Créer le répertoire de sauvegarde
        Path(BACKUP_DIR).mkdir(parents=True, exist_ok=True)
        logger.info(f"📁 Répertoire de sauvegarde: {os.path.abspath(BACKUP_DIR)}")
        logger.info(f"🔗 Base de données: {self.db_url}")

    def backup_sql_dump(self):
        """Sauvegarde complète via dump SQL."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = f"{BACKUP_DIR}/full_backup_{timestamp}.sql"

            # Pour SQLite, utiliser .dump
            if self.db_url.startswith("sqlite:///"):
                db_path = self.db_url.replace("sqlite:///", "")
                cmd = ["sqlite3", db_path, ".dump"]

                logger.info(f"🔄 Sauvegarde SQLite en cours: {backup_file}")

                with open(backup_file, "w") as f:
                    result = subprocess.run(
                        cmd, stdout=f, stderr=subprocess.PIPE, text=True
                    )

                if result.returncode == 0:
                    logger.info(f"✅ Sauvegarde SQLite réussie: {backup_file}")
                    return backup_file
                else:
                    logger.error(f"❌ Échec de la sauvegarde SQLite: {result.stderr}")
                    return None

            # Pour PostgreSQL, utiliser pg_dump (support pour configuration future)
            elif self.db_url.startswith("postgresql://"):
                # Extraire les informations de connexion de l'URL
                import re

                pattern = r"postgresql://(?:(\w+):?(\w*)@)?([^:/]+):?(\d*)/(\w+)"
                match = re.match(pattern, self.db_url)

                if match:
                    user, password, host, port, dbname = match.groups()
                    port = port or "5432"

                    cmd = [
                        "pg_dump",
                        "-h",
                        host,
                        "-p",
                        port,
                        "-U",
                        user or os.getenv("USER"),
                        "-d",
                        dbname,
                        "-F",
                        "c",
                        "-f",
                        backup_file,
                    ]

                    env = os.environ.copy()
                    if password:
                        env["PGPASSWORD"] = password

                    logger.info(f"🔄 Sauvegarde PostgreSQL en cours: {backup_file}")
                    result = subprocess.run(
                        cmd, env=env, capture_output=True, text=True
                    )

                    if result.returncode == 0:
                        logger.info(f"✅ Sauvegarde PostgreSQL réussie: {backup_file}")
                        return backup_file
                    else:
                        logger.error(
                            f"❌ Échec de la sauvegarde PostgreSQL: {result.stderr}"
                        )
                        return None
                else:
                    logger.error("❌ Impossible de parser l'URL PostgreSQL")
                    return None

            else:
                logger.error(f"❌ Type de base de données non supporté: {self.db_url}")
                return None

        except Exception as e:
            logger.error(f"❌ Erreur lors de la sauvegarde SQL: {e}")
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

            # Vérifier si la table ohlcv existe
            with self.engine.connect() as connection:
                result = connection.execute(
                    text("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='ohlcv'
                """)
                )

                if result.fetchone():
                    # Sauvegarder la table ohlcv
                    df = pd.read_sql("SELECT * FROM ohlcv", self.engine)
                    csv_file = f"{backup_dir}/ohlcv.csv"
                    df.to_csv(csv_file, index=False)
                    logger.info(f"✅ Sauvegarde OHLCV CSV réussie: {csv_file}")

                    # Vérifier et sauvegarder la table ticker si elle existe
                    result = connection.execute(
                        text("""
                        SELECT name FROM sqlite_master 
                        WHERE type='table' AND name='ticker'
                    """)
                    )

                    if result.fetchone():
                        df_ticker = pd.read_sql("SELECT * FROM ticker", self.engine)
                        ticker_file = f"{backup_dir}/ticker.csv"
                        df_ticker.to_csv(ticker_file, index=False)
                        logger.info(f"✅ Sauvegarde Ticker CSV réussie: {ticker_file}")
                else:
                    logger.warning("⚠️ Table 'ohlcv' non trouvée")

            logger.info(f"✅ Sauvegarde CSV terminée: {backup_dir}")
            return backup_dir

        except Exception as e:
            logger.error(f"❌ Erreur lors de la sauvegarde CSV: {e}")
            return None

    def backup_essential_data(self):
        """Sauvegarde des données essentielles dans un fichier compact."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = f"{BACKUP_DIR}/essential_backup_{timestamp}.json"

            essential_data = {
                "backup_timestamp": datetime.now().isoformat(),
                "database_url": self.db_url,
                "tables_info": {},
                "ohlcv_summary": [],
                "ticker_summary": [],
            }

            with self.engine.connect() as connection:
                # Récupérer la liste des tables
                result = connection.execute(
                    text("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name NOT LIKE 'sqlite_%'
                    ORDER BY name
                """)
                )
                tables = [row[0] for row in result.fetchall()]
                essential_data["tables_info"]["tables"] = tables

                # Traiter la table ohlcv si elle existe
                if "ohlcv" in tables:
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

                    df = pd.read_sql(query, connection)
                    essential_data["ohlcv_summary"] = df.to_dict("records")

                    # Compter le total d'enregistrements
                    count_result = connection.execute(
                        text("SELECT COUNT(*) FROM ohlcv")
                    )
                    total_records = count_result.scalar()
                    essential_data["tables_info"]["ohlcv_records"] = total_records

                    logger.info(
                        f"📊 OHLCV: {total_records} enregistrements, {len(df)} paires/timeframes"
                    )

                # Traiter la table ticker si elle existe
                if "ticker" in tables:
                    query = """
                        SELECT symbol, COUNT(*) as count,
                               MIN(timestamp) as first_date,
                               MAX(timestamp) as last_date
                        FROM ticker
                        GROUP BY symbol
                        ORDER BY symbol
                    """

                    df = pd.read_sql(query, connection)
                    essential_data["ticker_summary"] = df.to_dict("records")

                    # Compter le total d'enregistrements
                    count_result = connection.execute(
                        text("SELECT COUNT(*) FROM ticker")
                    )
                    total_records = count_result.scalar()
                    essential_data["tables_info"]["ticker_records"] = total_records

                    logger.info(
                        f"📊 Ticker: {total_records} enregistrements, {len(df)} symbols"
                    )

            # Sauvegarder en JSON
            import json

            with open(backup_file, "w") as f:
                json.dump(essential_data, f, indent=2, default=str)

            logger.info(
                f"✅ Sauvegarde des données essentielles réussie: {backup_file}"
            )
            return backup_file

        except Exception as e:
            logger.error(
                f"❌ Erreur lors de la sauvegarde des données essentielles: {e}"
            )
            return None

    def cleanup_old_backups(self):
        """Nettoyage des anciennes sauvegardes."""
        try:
            # Lister tous les fichiers de sauvegarde
            backup_files = []
            backup_dirs = []

            for item in Path(BACKUP_DIR).glob("*"):
                if item.name.startswith("csv_") and item.is_dir():
                    # Traiter les dossiers CSV
                    backup_dirs.append((item, item.stat().st_mtime))
                elif item.is_file() and ("backup" in item.name):
                    # Traiter les fichiers de sauvegarde
                    backup_files.append((item, item.stat().st_mtime))

            # Trier par date (ancien en premier)
            backup_files.sort(key=lambda x: x[1])
            backup_dirs.sort(key=lambda x: x[1])

            # Supprimer les fichiers de sauvegarde excédentaires
            total_items = len(backup_files) + len(backup_dirs)
            while total_items > MAX_BACKUPS:
                # Décider s'il faut supprimer un fichier ou un dossier
                if backup_files and (
                    not backup_dirs or backup_files[0][1] < backup_dirs[0][1]
                ):
                    old_file, _ = backup_files.pop(0)
                    old_file.unlink()
                    logger.info(
                        f"🗑️ Suppression du fichier de sauvegarde: {old_file.name}"
                    )
                else:
                    old_dir, _ = backup_dirs.pop(0)
                    import shutil

                    shutil.rmtree(old_dir)
                    logger.info(
                        f"🗑️ Suppression du dossier de sauvegarde: {old_dir.name}"
                    )

                total_items -= 1

        except Exception as e:
            logger.error(f"❌ Erreur lors du nettoyage: {e}")

    def full_backup(self):
        """Exécute une sauvegarde complète avec toutes les méthodes."""
        logger.info("🚀 Début de la sauvegarde complète")

        results = {
            "sql_dump": self.backup_sql_dump(),
            "csv": self.backup_csv(),
            "essential": self.backup_essential_data(),
        }

        # Nettoyage
        self.cleanup_old_backups()

        # Résumé
        successful = sum(1 for result in results.values() if result is not None)
        logger.info(f"✅ Sauvegarde terminée: {successful}/3 méthodes réussies")

        return results


if __name__ == "__main__":
    # Créer le répertoire de logs si nécessaire (le logger_settings utilise StreamHandler par défaut)
    Path("logs").mkdir(parents=True, exist_ok=True)

    # Ajouter un handler de fichier pour les logs de sauvegarde
    file_handler = logging.FileHandler("logs/backup.log")
    file_handler.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    logger.info("🚀 Démarrage du script de sauvegarde")

    try:
        backup = DatabaseBackup()
        results = backup.full_backup()

        # Résumé final
        successful_count = sum(1 for result in results.values() if result is not None)
        total_count = len(results)

        logger.info(
            f"📋 Résumé de la sauvegarde: {successful_count}/{total_count} méthodes réussies"
        )

        for method, result in results.items():
            if result:
                logger.info(f"  ✅ {method}: {result}")
            else:
                logger.warning(f"  ❌ {method}: Échec")

        logger.info("🏁 Script de sauvegarde terminé")

    except Exception as e:
        logger.error(f"💥 Erreur critique dans le script de sauvegarde: {e}")
        sys.exit(1)
