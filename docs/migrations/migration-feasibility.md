# Migration DB V2 — Feasibility SQLite → TimescaleDB

**Date** : 2026-05-11
**Auteur** : Agent W6 (analyse documentaire)
**Statut** : Draft — en attente confirmation état prod V1 (SSH audit W2)

---

## État actuel

### DEV (local / docker-compose.yml)

- **DB** : SQLite `data/processed/crypto_data.db`
- **docker-compose.yml** : aucun service `timescaledb` — seuls `mlflow`, `api`, `frontend`, `collector`
- **DB URL** par défaut : `sqlite:///data/processed/crypto_data.db` (`config/settings.py:58`)
- **Surcharge** : via env `CRYPTO_BOT_DB_URL` (`config/settings.py:119`)
- `src/config/settings.py` déclare `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_HOST`, `POSTGRES_PORT` mais ces variables **ne sont pas utilisées** par `db.py` / `db_context.py` (ils lisent `config.get("database.url")`)

### PROD V1 (Ansible)

- `_v1/infra/ansible/group_vars/vps.yml` : liste `timescaledb` dans `app_services` → service prévu en prod via Docker
- `_v1/infra/ansible/playbooks/provision.yml` : **aucune tâche** d'installation TimescaleDB native (ni `CREATE EXTENSION`, ni apt package) → TimescaleDB tourne exclusivement dans un container Docker
- `_v1/infra/ansible/playbooks/backup.yml` : utilise `docker compose exec -T timescaledb pg_dump -U cryptobot -d cryptobot --format=custom --compress=9` → stratégie backup **fonctionnelle** avec rétention (30j) + upload MinIO
- **État réel du serveur prod** : à confirmer post W2 SSH audit

### migrate_to_postgres.py (150 lignes)

Le script fait :
1. Crée les tables PG via `Base.metadata.create_all(bind=pg_engine)` pour 6 bases : `OHLCVBase`, `TickerBase`, `MarketDataBase`, `NewsBase`, `AlertBase`, `PaperTradeBase`
2. Lit les tables SQLite dans l'ordre FK (`sorted_tables`)
3. Insère par batch de 500 avec `on_conflict_do_nothing()`
4. Gère la désérialisation JSON (colonnes JSONB côté PG)

Le script **ne fait PAS** :
- `CREATE EXTENSION IF NOT EXISTS timescaledb`
- `SELECT create_hypertable(...)`
- Création d'index time-descending
- Configuration de continuous aggregates, compression, ou retention policies

---

## Inventaire des modèles SQLAlchemy

| Fichier | Table | PK | Colonne temps | FK entrantes | Base |
|---|---|---|---|---|---|
| `ohlcv.py` | `ohlcv` | `id` (String UUID) | `timestamp` (DateTime) | — | `OHLCVBase` |
| `ticker.py` | `ticker_snapshots` | `id` (String UUID) | `snapshot_time` (DateTime) | — | `TickerBase` |
| `news.py` | `news_articles` | `id` (String UUID) | `published_at`, `collected_at` | — | `NewsBase` |
| `paper_trade.py` | `paper_portfolios` | `id` (String UUID) | `created_at` | `paper_trades.portfolio_id` | `PaperTradeBase` |
| `paper_trade.py` | `paper_trades` | `id` (String UUID) | `entry_time` | — | `PaperTradeBase` |
| `alert_subscriber.py` | `alert_subscribers` | `id` (Integer) | `created_at` | — | `AlertBase` |
| `global_snapshot.py` | `global_market_snapshot` | `id` (Integer auto) | `timestamp` (DateTime) | `global_market_cap`, `global_market_dominance`, `global_market_volume` | `MarketDataBase` |
| `global_market_cap.py` | `global_market_cap` | `id` (Integer) | — | — | `MarketDataBase` |
| `global_market_dominance.py` | `global_market_dominance` | `id` (Integer) | — | — | `MarketDataBase` |
| `global_market_volume.py` | `global_market_volume` | `id` (Integer) | — | — | `MarketDataBase` |
| `top_crypto_snapshot.py` | `top_crypto_snapshot` | `id` (Integer auto) | `snapshot_time` (DateTime) | `top_crypto` | `MarketDataBase` |
| `top_crypto.py` | `top_crypto` | `id` (Integer auto) | — | — | `MarketDataBase` |
| `crypto_detail_snapshot.py` | `crypto_detail_snapshot` | `id` (Integer auto) | `snapshot_time` (DateTime) | `crypto_detail` | `MarketDataBase` |
| `crypto_detail.py` | `crypto_detail` | `id` (Integer auto) | `last_updated` | — | `MarketDataBase` |

---

## Couverture migrate_to_postgres.py

| Table | Couverte par script ? | Hypertable candidate ? | Index time existant ? | Manquant |
|---|---|---|---|---|
| `ohlcv` | Oui | **Oui** (time-series OHLCV) | `idx_ohlcv_timestamp` ASC | `create_hypertable`, index DESC, `timestamp` dans PK |
| `ticker_snapshots` | Oui | **Oui** (time-series ticker) | `idx_ticker_snapshot_time` ASC | `create_hypertable`, index DESC, `snapshot_time` dans PK |
| `news_articles` | Oui | Non (lookup, pas time-series) | — | — |
| `paper_portfolios` | Oui | Non (relationnelle) | — | — |
| `paper_trades` | Oui | Non (FK vers portfolios) | — | — |
| `alert_subscribers` | Oui | Non (relationnelle) | — | — |
| `global_market_snapshot` | Oui | **Oui** (snapshot temporel) | `timestamp` unique+index | `create_hypertable`, mais **FK entrantes** bloquent (voir ci-dessous) |
| `global_market_cap` | Oui | Non (child FK) | — | — |
| `global_market_dominance` | Oui | Non (child FK) | — | — |
| `global_market_volume` | Oui | Non (child FK) | — | — |
| `top_crypto_snapshot` | Oui | **Oui** (snapshot temporel) | — (pas d'index time) | `create_hypertable`, mais **FK entrantes** bloquent |
| `top_crypto` | Oui | Non (child FK) | — | — |
| `crypto_detail_snapshot` | Oui | **Oui** (snapshot temporel) | — (pas d'index time) | `create_hypertable`, mais **FK entrantes** bloquent |
| `crypto_detail` | Oui | Non (child FK) | — | — |

---

## Gaps identifiés (priorisés)

### 1. CRITIQUE — Aucun appel `CREATE EXTENSION timescaledb` ni `create_hypertable()`

Le script `migrate_to_postgres.py` crée des **tables PostgreSQL classiques**. TimescaleDB n'est jamais activé. Les tables time-series n'ont aucun partitionnement temporel automatique.

**Impact** : Pas de chunk-based storage, pas d'optimisation des requêtes temporelles, pas de compression native. Performances dégradées sur gros volumes OHLCV.

### 2. CRITIQUE — Contrainte PK incompatible avec hypertables

TimescaleDB **exige** que la colonne de partitionnement temporel soit incluse dans toute contrainte UNIQUE ou PRIMARY KEY. Actuellement :

- `ohlcv` : PK = `id` (UUID seul) → doit devenir `PrimaryKeyConstraint('id', 'timestamp')`
- `ticker_snapshots` : PK = `id` (UUID seul) → doit devenir `PrimaryKeyConstraint('id', 'snapshot_time')`
- Snapshot parents (Integer auto PK) : plus complexe car FK targets

### 3. HAUTE — FK entrantes bloquent la conversion des snapshot parents

Les tables `global_market_snapshot`, `top_crypto_snapshot`, `crypto_detail_snapshot` sont des **cibles FK** depuis leurs tables enfants (`global_market_cap`, `top_crypto`, `crypto_detail`). TimescaleDB ne supporte **pas** les FK référençant une hypertable.

**Options** :
- **Option A** : Ne pas convertir les snapshot parents en hypertables. Les garder en tables PG classiques. Volume faible (1 row/snapshot), impact perf négligeable.
- **Option B** : Dénormaliser — copier `snapshot_time` dans les tables enfants, supprimer FK, convertir enfants + parents en hypertables. Plus complexe, gain marginal.

**Recommandation** : Option A — seuls `ohlcv` et `ticker_snapshots` deviennent des hypertables.

### 4. HAUTE — docker-compose.yml DEV sans TimescaleDB

Le `docker-compose.yml` actuel n'a pas de service `timescaledb`. Les développeurs travaillent sur SQLite. Pour tester la migration, il faut ajouter un service TimescaleDB et mettre à jour `CRYPTO_BOT_DB_URL`.

### 5. MOYENNE — Pas d'index time-descending

Les index existants sur `timestamp` / `snapshot_time` sont ASC (défaut SQLAlchemy). Pour des requêtes time-series typiques (dernières N bougies, dernier snapshot), un index `DESC` est critique pour les performances.

### 6. MOYENNE — Pas de continuous aggregates

Aucun materialized view pour les agrégats temporels courants (ex: OHLCV 1h → 4h → 1d, volume moyen par jour). Utile pour le dashboard et le feature engineering ML.

### 7. BASSE — Pas de compression policy

TimescaleDB peut compresser automatiquement les chunks > N jours. Pas configuré. Pertinent quand le volume OHLCV dépasse quelques GB.

### 8. BASSE — Pas de retention policy

Pas de politique de suppression automatique des données anciennes. À définir selon les besoins (ex: garder 2 ans d'OHLCV, 6 mois de tickers).

---

## Plan one-shot ordonné

### Prérequis

- Service TimescaleDB opérationnel (Docker ou natif)
- URL PostgreSQL accessible : `postgresql://user:pw@host:5432/cryptobot`

### Étapes

```
1. BACKUP PRÉ-MIGRATION
   pg_dump -Fc -f /var/backups/cryptobot/pre-mig-$(date +%Y%m%d_%H%M%S).dump \
     -U cryptobot -h localhost cryptobot

2. EXTENSION TIMESCALEDB
   psql -U cryptobot -d cryptobot -c "CREATE EXTENSION IF NOT EXISTS timescaledb;"

3. CRÉATION DU SCHÉMA
   # Via migrate_to_postgres.py existant (crée les tables PG classiques)
   python scripts/migrate_to_postgres.py --postgres-url $POSTGRES_URL
   # OU via Base.metadata.create_all() dans le code applicatif

4. MODIFICATION DES PK POUR HYPERTABLES
   # Avant create_hypertable, la colonne time doit être dans la PK
   ALTER TABLE ohlcv DROP CONSTRAINT ohlcv_pkey;
   ALTER TABLE ohlcv ADD PRIMARY KEY (id, timestamp);

   ALTER TABLE ticker_snapshots DROP CONSTRAINT ticker_snapshots_pkey;
   ALTER TABLE ticker_snapshots ADD PRIMARY KEY (id, snapshot_time);

5. CONVERSION EN HYPERTABLES
   SELECT create_hypertable('ohlcv', 'timestamp',
     chunk_time_interval => INTERVAL '7 days',
     migrate_data => true);

   SELECT create_hypertable('ticker_snapshots', 'snapshot_time',
     chunk_time_interval => INTERVAL '7 days',
     migrate_data => true);

6. INDEX TIME-DESCENDING
   CREATE INDEX idx_ohlcv_timestamp_desc
     ON ohlcv (timestamp DESC);
   CREATE INDEX idx_ohlcv_symbol_timestamp_desc
     ON ohlcv (symbol, timestamp DESC);

   CREATE INDEX idx_ticker_snapshot_time_desc
     ON ticker_snapshots (snapshot_time DESC);
   CREATE INDEX idx_ticker_symbol_time_desc
     ON ticker_snapshots (symbol, snapshot_time DESC);

7. VALIDATION
   SELECT COUNT(*) FROM ohlcv;
   SELECT COUNT(*) FROM ticker_snapshots;
   -- Comparer avec les counts pré-migration (SQLite source)

   -- Vérifier les hypertables
   SELECT * FROM timescaledb_information.hypertables;
   SELECT * FROM timescaledb_information.chunks
     ORDER BY range_start DESC LIMIT 5;

8. OPTIONNEL — CONTINUOUS AGGREGATES
   CREATE MATERIALIZED VIEW ohlcv_daily
   WITH (timescaledb.continuous) AS
   SELECT
     time_bucket('1 day', timestamp) AS bucket,
     symbol,
     FIRST(open, timestamp) AS open,
     MAX(high) AS high,
     MIN(low) AS low,
     LAST(close, timestamp) AS close,
     SUM(volume) AS volume
   FROM ohlcv
   WHERE timeframe = '1h'
   GROUP BY bucket, symbol;

9. OPTIONNEL — COMPRESSION (après stabilisation, ex: chunks > 30 jours)
   ALTER TABLE ohlcv SET (
     timescaledb.compress,
     timescaledb.compress_segmentby = 'symbol',
     timescaledb.compress_orderby = 'timestamp DESC'
   );
   SELECT add_compression_policy('ohlcv', INTERVAL '30 days');

10. OPTIONNEL — RETENTION (selon besoins)
    SELECT add_retention_policy('ohlcv', INTERVAL '730 days');
    SELECT add_retention_policy('ticker_snapshots', INTERVAL '365 days');
```

---

## Rollback

```bash
# 1. Arrêter les services applicatifs
docker compose stop api frontend collector

# 2. Supprimer et recréer la base
docker compose exec -T timescaledb dropdb -U cryptobot cryptobot
docker compose exec -T timescaledb createdb -U cryptobot cryptobot

# 3. Restaurer depuis le dump pré-migration
docker compose exec -T timescaledb pg_restore \
  -U cryptobot -d cryptobot \
  /var/backups/cryptobot/pre-mig-<date>.dump

# 4. Redémarrer
docker compose start api frontend collector

# 5. Valider
docker compose exec -T timescaledb psql -U cryptobot -d cryptobot \
  -c "SELECT tablename FROM pg_tables WHERE schemaname='public';"
```

**Note** : Si le rollback vise un retour à SQLite (et non juste une restauration PG), il suffit de remettre `CRYPTO_BOT_DB_URL=sqlite:///data/processed/crypto_data.db` dans le `.env` et redémarrer. La DB SQLite locale est intacte (jamais modifiée par le script de migration).

---

## Recommandation finale

### Approche recommandée : Patcher `migrate_to_postgres.py`

Ajouter au script existant, **après** `base.metadata.create_all()` et **avant** la migration des données :

1. `CREATE EXTENSION IF NOT EXISTS timescaledb`
2. `ALTER TABLE ... DROP/ADD PK` pour `ohlcv` et `ticker_snapshots`
3. `SELECT create_hypertable(...)` pour ces 2 tables
4. `CREATE INDEX ... DESC` pour les index temporels

**Pourquoi pas un script séparé ?**
Le script actuel est déjà le point d'entrée unique de la migration. Fragmenter la logique en plusieurs scripts ajoute de la complexité opérationnelle sans gain.

**Pourquoi pas un rôle Ansible ?**
L'extension TimescaleDB et les hypertables sont de la configuration DB applicative, pas de l'infrastructure. Le provisioning Ansible gère le container Docker ; la configuration interne de la DB appartient au code applicatif.

### Tables à convertir en hypertables

| Table | Chunk interval | Justification |
|---|---|---|
| `ohlcv` | 7 jours | Volume le plus élevé (multi-paires × multi-timeframes × multi-exchanges). Requêtes time-range systématiques. |
| `ticker_snapshots` | 7 jours | Snapshots fréquents (toutes les 5 min). Volume croissant. |

### Tables à NE PAS convertir

- `global_market_snapshot`, `top_crypto_snapshot`, `crypto_detail_snapshot` : FK entrantes incompatibles avec hypertables. Volume faible (1 row/snapshot/jour). Pas de gain.
- `news_articles`, `paper_*`, `alert_subscribers` : tables relationnelles / lookup. Pas de caractéristique time-series.

### Prochaines étapes

1. **W2 SSH audit** : confirmer l'état réel de la prod (TimescaleDB container tourne ? extension activée ? hypertables existantes ?)
2. **Patch docker-compose.yml DEV** : ajouter service `timescaledb` + mettre à jour env vars
3. **Patch migrate_to_postgres.py** : ajouter les étapes 2-6 du plan ci-dessus
4. **Patch modèles SQLAlchemy** : modifier `__table_args__` de `ohlcv` et `ticker_snapshots` pour PK composite `(id, timestamp/snapshot_time)`
5. **Test en DEV** : migration SQLite → TimescaleDB locale, valider counts + hypertable status
