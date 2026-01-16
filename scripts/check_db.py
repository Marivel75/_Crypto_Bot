#!/usr/bin/env python3
"""
Script de vérification de l'état de la base de données.
Fournit des informations basiques sur les tables et les données collectées.
"""

import sqlite3
import sys
import os
from datetime import datetime

# Ajouter le dossier racine au path pour les imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from logger_settings import logger


def get_db_connection(db_path=None):
    """
    Établit une connexion à la base de données SQLite.
    
    Args:
        db_path: Chemin vers la base de données (optionnel)
        
    Returns:
        Connection: Objet de connexion SQLite
    """
    if db_path is None:
        # Construire le chemin absolu vers la base de données
        db_path = os.path.join(project_root, "data", "processed", "crypto_data.db")
    
    """
    Établit une connexion à la base de données SQLite.
    """
    try:
        connection = sqlite3.connect(db_path)
        connection.row_factory = sqlite3.Row  # Permet d'accéder aux colonnes par nom
        logger.info(f"✅ Connexion établie à la base de données: {db_path}")
        return connection
    except sqlite3.Error as e:
        logger.error(f"❌ Erreur de connexion à la base de données: {e}")
        raise


def get_table_info(connection, table_name):
    """
    Récupère des informations sur une table spécifique.
    """
    try:
        cursor = connection.cursor()

        # Compter le nombre de lignes
        cursor.execute(f"SELECT COUNT(*) as count FROM {table_name}")
        row_count = cursor.fetchone()[0]

        # Récupérer la structure de la table
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]

        # Récupérer la dernière mise à jour (si la table a un champ timestamp/snapshot_time)
        last_update = None
        if "timestamp" in column_names:
            cursor.execute(f"SELECT MAX(timestamp) as last_update FROM {table_name}")
        elif "snapshot_time" in column_names:
            cursor.execute(
                f"SELECT MAX(snapshot_time) as last_update FROM {table_name}"
            )
        elif "created_at" in column_names:
            cursor.execute(f"SELECT MAX(created_at) as last_update FROM {table_name}")

        result = cursor.fetchone()
        if result and result[0]:
            last_update = result[0]

        # Récupérer la taille de la table (méthode SQLite)
        # SQLite ne fournit pas directement la taille des tables, nous utilisons une estimation
        cursor.execute(f"SELECT COUNT(*) as row_count FROM {table_name}")
        row_count_result = cursor.fetchone()
        row_count_for_size = row_count_result[0] if row_count_result else 0
        
        # Estimation de la taille (1KB par ligne en moyenne)
        table_size = row_count_for_size * 1024  # 1KB par ligne

        return {
            "table_name": table_name,
            "row_count": row_count,
            "column_count": len(columns),
            "columns": column_names,
            "last_update": last_update,
            "table_size_bytes": table_size,
        }

    except sqlite3.Error as e:
        logger.error(
            f"❌ Erreur lors de la récupération des informations pour {table_name}: {e}"
        )
        return None


def get_db_stats(connection):
    """
    Récupère des statistiques globales sur la base de données.
    """
    try:
        cursor = connection.cursor()

        # Récupérer la liste des tables
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = cursor.fetchall()
        table_names = [table[0] for table in tables]

        # Récupérer des informations pour chaque table
        table_stats = {}
        total_rows = 0
        total_size = 0

        for table_name in table_names:
            if table_name.startswith("sqlite_"):
                continue  # Ignorer les tables système

            table_info = get_table_info(connection, table_name)
            if table_info:
                table_stats[table_name] = table_info
                total_rows += table_info["row_count"]
                total_size += table_info["table_size_bytes"]

        # Récupérer la taille totale de la base de données
        cursor.execute(
            "SELECT page_count * page_size as db_size FROM pragma_page_count(), pragma_page_size()"
        )
        db_size_result = cursor.fetchone()
        db_size_bytes = db_size_result[0] if db_size_result else 0

        return {
            "table_count": len(table_stats),
            "total_rows": total_rows,
            "total_size_bytes": db_size_bytes,
            "tables": table_stats,
        }

    except sqlite3.Error as e:
        logger.error(
            f"❌ Erreur lors de la récupération des statistiques de la base de données: {e}"
        )
        return None


def format_bytes(size_bytes):
    """
    Formate la taille en bytes dans une unité plus lisible
    """
    if size_bytes == 0:
        return "0 bytes"

    size_names = ["bytes", "KB", "MB", "GB", "TB"]
    i = 0
    size = float(size_bytes)

    while size >= 1024 and i < len(size_names) - 1:
        size /= 1024
        i += 1

    return f"{size:.2f} {size_names[i]}"


def print_db_summary(stats):
    """
    Affiche un résumé des statistiques de la base de données.
    """
    if not stats:
        logger.warning("⚠️  Aucune statistique disponible")
        return

    logger.info("📊 Résumé de la base de données:")
    logger.info(f"   Nombre de tables: {stats['table_count']}")
    logger.info(f"   Nombre total de lignes: {stats['total_rows']:,}")
    logger.info(
        f"   Taille totale de la base: {format_bytes(stats['total_size_bytes'])}"
    )
    logger.info("")

    for table_name, table_info in stats["tables"].items():
        logger.info(f"📋 Table: {table_name}")
        logger.info(f"   Lignes: {table_info['row_count']:,}")
        logger.info(f"   Colonnes: {table_info['column_count']}")
        logger.info(f"   Taille: {format_bytes(table_info['table_size_bytes'])}")

        if table_info["last_update"]:
            last_update_str = table_info["last_update"]
            if isinstance(last_update_str, str):
                # Convertir si c'est une chaîne
                try:
                    last_update = datetime.strptime(
                        last_update_str, "%Y-%m-%d %H:%M:%S"
                    )
                except ValueError:
                    last_update = last_update_str
            else:
                last_update = table_info["last_update"]

            logger.info(f"   Dernière mise à jour: {last_update}")
        else:
            logger.info(f"   Dernière mise à jour: Non disponible")

        logger.info("")


def check_db_health(connection):
    """
    Vérifie la santé générale de la base de données.
    """
    try:
        cursor = connection.cursor()

        # Vérifier l'intégrité de la base de données
        cursor.execute("PRAGMA integrity_check")
        integrity_result = cursor.fetchone()
        integrity_ok = integrity_result[0] == "ok" if integrity_result else False

        # Vérifier les tables spécifiques
        health_indicators = {"integrity_ok": integrity_ok, "tables_present": {}}

        # Vérifier la présence des tables principales
        required_tables = ["ohlcv_data", "ticker_snapshots"]
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = [row[0] for row in cursor.fetchall()]

        for table in required_tables:
            health_indicators["tables_present"][table] = table in existing_tables

        return health_indicators

    except sqlite3.Error as e:
        logger.error(
            f"❌ Erreur lors de la vérification de la santé de la base de données: {e}"
        )
        return None


def print_health_summary(health):
    """
    Affiche un résumé de la santé de la base de données.
    """
    if not health:
        logger.warning("⚠️  Aucune information de santé disponible")
        return

    logger.info("Santé de la base de données:")

    if health["integrity_ok"]:
        logger.info("   ✅ Intégrité de la base: OK")
    else:
        logger.error("   ❌ Intégrité de la base: PROBLÈME DÉTECTÉ")

    logger.info("   Tables principales:")
    for table, present in health["tables_present"].items():
        if present:
            logger.info(f"      ✅ {table}: Présente")
        else:
            logger.warning(f"      ⚠️  {table}: Absente")

    logger.info("")


def main():
    """
    Point d'entrée principal pour le script de vérification de la base de données.
    """
    try:
        logger.info("🔍 Démarrage de la vérification de la base de données")

        # Se connecter à la base de données
        connection = get_db_connection()

        if connection:
            # Récupérer les statistiques
            stats = get_db_stats(connection)
            # Vérifier la santé de la base
            health = check_db_health(connection)

            # Afficher les résultats
            if stats:
                print_db_summary(stats)

            if health:
                print_health_summary(health)

            # Fermer la connexion
            connection.close()
            logger.info("✅ Vérification de la base de données terminée")

    except Exception as e:
        logger.error(f"❌ Erreur fatale dans le script de vérification: {e}")
        raise


if __name__ == "__main__":
    main()
