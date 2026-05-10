"""
Migre toutes les données de la base SQLite vers PostgreSQL.

Usage :
    python scripts/migrate_to_postgres.py --postgres-url postgresql://user:pw@host/db
    python scripts/migrate_to_postgres.py  # lit POSTGRES_URL dans l'environnement
"""

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from src.models.alert_subscriber import Base as AlertBase
from src.models.market_data_base import MarketDataBase
from src.models.news import Base as NewsBase
from src.models.ohlcv import Base as OHLCVBase
from src.models.paper_trade import Base as PaperTradeBase
from src.models.ticker import Base as TickerBase

_ALL_BASES = [OHLCVBase, TickerBase, MarketDataBase, NewsBase, AlertBase, PaperTradeBase]

SQLITE_URL = "sqlite:///data/processed/crypto_data.db"
BATCH_SIZE = 500


def _json_cols_for(pg_engine, table_name: str) -> set[str]:
    """Renvoie les noms des colonnes JSON/JSONB de la table dans PostgreSQL."""
    from sqlalchemy import MetaData
    meta = MetaData()
    meta.reflect(bind=pg_engine, only=[table_name])
    if table_name not in meta.tables:
        return set()
    return {
        col.name
        for col in meta.tables[table_name].columns
        if str(col.type) in ("JSON", "JSONB")
    }


def _migrate_table(sqlite_engine, pg_engine, table_name: str) -> None:
    # --- lecture SQLite ---
    with sqlite_engine.connect() as src:
        count = src.execute(text(f'SELECT COUNT(*) FROM "{table_name}"')).scalar()
        if count == 0:
            print(f"  {table_name}: vide, ignorée.")
            return
        result = src.execute(text(f'SELECT * FROM "{table_name}"'))
        col_names = list(result.keys())
        rows = result.fetchall()

    print(f"  {table_name}: {count} lignes...", end=" ", flush=True)

    json_cols = _json_cols_for(pg_engine, table_name)

    # Conversion des lignes en dicts, désérialisation JSON
    records = []
    for row in rows:
        d = dict(zip(col_names, row))
        for col in json_cols:
            if col in d and isinstance(d[col], str):
                try:
                    d[col] = json.loads(d[col])
                except (json.JSONDecodeError, ValueError):
                    d[col] = None
        records.append(d)

    # --- écriture PostgreSQL par batch ---
    from sqlalchemy import MetaData, Table
    meta = MetaData()
    meta.reflect(bind=pg_engine, only=[table_name])
    if table_name not in meta.tables:
        print(f"table absente de PostgreSQL, ignorée.")
        return
    pg_table = meta.tables[table_name]

    inserted = skipped = 0
    with pg_engine.connect() as dst:
        for i in range(0, len(records), BATCH_SIZE):
            batch = records[i : i + BATCH_SIZE]
            stmt = pg_insert(pg_table).values(batch).on_conflict_do_nothing()
            result = dst.execute(stmt)
            inserted += result.rowcount
            skipped += len(batch) - result.rowcount
        dst.commit()

    print(f"OK  ({inserted} insérées, {skipped} ignorées — doublons)")


def migrate(postgres_url: str) -> None:
    print(f"\nSource  : {SQLITE_URL}")
    print(f"Cible   : {postgres_url}\n")

    sqlite_engine = create_engine(
        SQLITE_URL, connect_args={"check_same_thread": False}
    )
    pg_engine = create_engine(postgres_url)

    # Création de toutes les tables dans PostgreSQL (idempotent)
    print("Création des tables PostgreSQL si absentes…")
    for base in _ALL_BASES:
        base.metadata.create_all(bind=pg_engine)

    # Ordre d'insertion respectant les foreign keys : sorted_tables renvoie
    # l'ordre de suppression (enfants d'abord), on le renverse pour l'insertion.
    from sqlalchemy import MetaData
    pg_meta = MetaData()
    pg_meta.reflect(bind=pg_engine)
    ordered_tables = [t.name for t in pg_meta.sorted_tables]

    # On ne migre que les tables présentes dans SQLite
    sqlite_tables = set(inspect(sqlite_engine).get_table_names())
    tables = [t for t in ordered_tables if t in sqlite_tables]
    print(f"Tables à migrer (ordre FK) : {', '.join(tables)}\n")

    for table in tables:
        _migrate_table(sqlite_engine, pg_engine, table)

    print("\nMigration terminée.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Migre SQLite → PostgreSQL")
    parser.add_argument(
        "--postgres-url",
        default=os.environ.get("POSTGRES_URL"),
        help="URL PostgreSQL (ex: postgresql://user:pw@host:5432/db). "
             "Peut aussi être définie via la variable d'environnement POSTGRES_URL.",
    )
    args = parser.parse_args()

    if not args.postgres_url:
        print(
            "Erreur : URL PostgreSQL manquante.\n"
            "  Fournir --postgres-url ou définir POSTGRES_URL dans l'environnement / .env"
        )
        sys.exit(1)

    migrate(args.postgres_url)


if __name__ == "__main__":
    main()
