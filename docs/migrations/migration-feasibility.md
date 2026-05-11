# Migration DB V2 — Feasibility SQLite → PostgreSQL

**Date** : 2026-05-11
**Auteur** : Agent W6 (analyse documentaire)
**Statut** : Draft — en attente confirmation état prod V1 (SSH audit W2)

---

## État actuel

### DEV (local / docker-compose.yml)

- **DB** : SQLite `data/processed/crypto_data.db`
- **docker-compose.yml** : aucun service PostgreSQL — seuls `mlflow`, `api`, `frontend`, `collector`
- **DB URL** par défaut : `sqlite:///data/processed/crypto_data.db` (`config/settings.py:58`)
- **Surcharge** : via env `CRYPTO_BOT_DB_URL` (`config/settings.py:119`)
- `src/config/settings.py` déclare `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_HOST`, `POSTGRES_PORT` mais ces variables **ne sont pas utilisées** par `db.py` / `db_context.py` (ils lisent `config.get("database.url")`)

### PROD V1 (Ansible)

- `_v1/infra/ansible/group_vars/vps.yml` : liste `timescaledb` dans `app_services` → image Docker TimescaleDB en prod (= PostgreSQL + extension)
- `_v1/infra/ansible/playbooks/provision.yml` : **aucune tâche** d'installation DB native → la DB tourne exclusivement dans un container Docker
- `_v1/infra/ansible/playbooks/backup.yml` : utilise `docker compose exec -T timescaledb pg_dump -U cryptobot -d cryptobot --format=custom --compress=9` → stratégie backup **fonctionnelle** avec rétention (30j) + upload MinIO
- **État réel du serveur prod** : à confirmer post W2 SSH audit

### migrate_to_postgres.py (150 lignes)

Le script fait :
1. Crée les tables PG via `Base.metadata.create_all(bind=pg_engine)` pour 6 bases : `OHLCVBase`, `TickerBase`, `MarketDataBase`, `NewsBase`, `AlertBase`, `PaperTradeBase`
2. Lit les tables SQLite dans l'ordre FK (`sorted_tables`)
3. Insère par batch de 500 avec `on_conflict_do_nothing()`
4. Gère la désérialisation JSON (colonnes JSONB côté PG)

Le script est **fonctionnel** pour une migration SQLite → PostgreSQL classique. Il couvre toutes les tables.

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

| Table | Couverte ? | Index time existant ? | Manquant |
|---|---|---|---|
| `ohlcv` | Oui | `idx_ohlcv_timestamp` (ASC) | Index DESC recommandé |
| `ticker_snapshots` | Oui | `idx_ticker_snapshot_time` (ASC) | Index DESC recommandé |
| `news_articles` | Oui | — | — |
| `paper_portfolios` | Oui | — | — |
| `paper_trades` | Oui | — | — |
| `alert_subscribers` | Oui | — | — |
| `global_market_snapshot` | Oui | `timestamp` unique+index | — |
| `global_market_cap` | Oui | — | — |
| `global_market_dominance` | Oui | — | — |
| `global_market_volume` | Oui | — | — |
| `top_crypto_snapshot` | Oui | — | Index sur `snapshot_time` recommandé |
| `top_crypto` | Oui | — | — |
| `crypto_detail_snapshot` | Oui | — | Index sur `snapshot_time` recommandé |
| `crypto_detail` | Oui | — | — |

---

## Gaps identifiés (priorisés)

### 1. HAUTE — docker-compose.yml DEV sans PostgreSQL

Le `docker-compose.yml` n'a pas de service PostgreSQL. Tout tourne sur SQLite. Pour tester la migration en local, il faut ajouter un service `postgres` et mettre à jour `CRYPTO_BOT_DB_URL`.

### 2. MOYENNE — Index time-descending manquants

Les index existants sur `timestamp` / `snapshot_time` sont ASC (défaut SQLAlchemy). Pour les requêtes time-series typiques (dernières N bougies), un index `DESC` améliore les performances. Impact faible au volume actuel, mais bonne pratique PG.

### 3. MOYENNE — Index manquants sur tables snapshot

`top_crypto_snapshot` et `crypto_detail_snapshot` n'ont pas d'index sur `snapshot_time`. À ajouter dans les modèles.

### 4. BASSE — Variables PG inutilisées

`src/config/settings.py` déclare `POSTGRES_USER` etc. mais rien ne les consomme. Le code utilise `CRYPTO_BOT_DB_URL` via `config.get("database.url")`. Code mort à nettoyer.

---

## Plan one-shot ordonné

### Prérequis

- Service PostgreSQL opérationnel (Docker ou natif)
- URL PostgreSQL accessible : `postgresql://user:pw@host:5432/cryptobot`

### Étapes

```
1. BACKUP PRÉ-MIGRATION (si données PG existantes en prod)
   pg_dump -Fc -f /var/backups/cryptobot/pre-mig-$(date +%Y%m%d_%H%M%S).dump \
     -U cryptobot -h localhost cryptobot

2. CRÉATION DU SCHÉMA + MIGRATION DES DONNÉES
   python scripts/migrate_to_postgres.py --postgres-url $POSTGRES_URL
   # Le script crée les tables (idempotent) puis migre les données SQLite

3. INDEX TIME-DESCENDING (optionnel, recommandé)
   CREATE INDEX CONCURRENTLY idx_ohlcv_timestamp_desc
     ON ohlcv (timestamp DESC);
   CREATE INDEX CONCURRENTLY idx_ohlcv_symbol_timestamp_desc
     ON ohlcv (symbol, timestamp DESC);
   CREATE INDEX CONCURRENTLY idx_ticker_snapshot_time_desc
     ON ticker_snapshots (snapshot_time DESC);

4. VALIDATION
   -- Comparer counts SQLite vs PostgreSQL
   SELECT 'ohlcv' AS t, COUNT(*) FROM ohlcv
   UNION ALL SELECT 'ticker_snapshots', COUNT(*) FROM ticker_snapshots
   UNION ALL SELECT 'news_articles', COUNT(*) FROM news_articles
   UNION ALL SELECT 'paper_portfolios', COUNT(*) FROM paper_portfolios
   UNION ALL SELECT 'paper_trades', COUNT(*) FROM paper_trades
   UNION ALL SELECT 'alert_subscribers', COUNT(*) FROM alert_subscribers
   UNION ALL SELECT 'global_market_snapshot', COUNT(*) FROM global_market_snapshot
   UNION ALL SELECT 'top_crypto_snapshot', COUNT(*) FROM top_crypto_snapshot
   UNION ALL SELECT 'crypto_detail_snapshot', COUNT(*) FROM crypto_detail_snapshot;

5. BASCULER L'URL
   # .env ou docker-compose env
   CRYPTO_BOT_DB_URL=postgresql://cryptobot:pw@postgres:5432/cryptobot
```

---

## Rollback

```bash
# Option A : Restaurer PG depuis dump
docker compose stop api frontend collector
docker compose exec -T postgres dropdb -U cryptobot cryptobot
docker compose exec -T postgres createdb -U cryptobot cryptobot
docker compose exec -T postgres pg_restore \
  -U cryptobot -d cryptobot \
  /var/backups/cryptobot/pre-mig-<date>.dump
docker compose start api frontend collector

# Option B : Retour à SQLite (plus simple)
# La DB SQLite n'est jamais modifiée par le script de migration.
# Remettre l'URL SQLite dans .env et redémarrer :
CRYPTO_BOT_DB_URL=sqlite:///data/processed/crypto_data.db
docker compose restart api frontend collector
```

---

## Recommandation finale

### PostgreSQL classique suffit

Au volume actuel du projet (quelques paires × quelques timeframes × 1-2 collectes/jour), **PostgreSQL classique couvre largement le besoin**. Le script `migrate_to_postgres.py` existant est fonctionnel et couvre les 14 tables.

Les gains immédiats de passer de SQLite à PostgreSQL :
- Accès concurrent (multi-service : API + collector + frontend)
- Vraies transactions ACID avec isolation
- Types natifs JSONB avec indexation
- `pg_dump` / `pg_restore` pour les backups (déjà configuré dans `backup.yml`)
- Prêt pour la prod multi-container

### TimescaleDB — option future, pas nécessaire maintenant

Si le volume OHLCV dépasse plusieurs millions de rows (ex: ajout de timeframes 1m/5m, ajout de dizaines de paires), TimescaleDB apporterait :
- Partitionnement automatique par chunks temporels
- Compression native (90%+ sur données OHLCV)
- Continuous aggregates (1h → 4h → 1d)
- Retention policies automatiques

**Mais** cela implique des modifications non triviales :
- `CREATE EXTENSION timescaledb` + `create_hypertable()`
- PK composites `(id, timestamp)` sur `ohlcv` et `ticker_snapshots`
- Image Docker `timescale/timescaledb` au lieu de `postgres`

**Verdict** : YAGNI. Migrer vers PG classique maintenant. Réévaluer TimescaleDB quand le volume le justifie. L'image `timescale/timescaledb` en prod V1 est compatible PG classique (c'est un superset) — pas de blocage pour activer l'extension plus tard.

### Prochaines étapes

1. **Patch docker-compose.yml DEV** : ajouter service `postgres` + mettre à jour env vars
2. **Test migration DEV** : `python scripts/migrate_to_postgres.py`, valider counts
3. **W2 SSH audit** : confirmer l'état réel de la prod
4. **Cleanup** : supprimer les variables PG inutilisées dans `src/config/settings.py`
5. **Index DESC** : ajouter dans les modèles SQLAlchemy pour `ohlcv` et `ticker_snapshots`
