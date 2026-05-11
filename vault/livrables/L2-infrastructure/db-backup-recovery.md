---
type: rncp
bloc: 2
competence: C2.2.3
title: Sauvegarde et reprise d'activite base de donnees
project: cryptobot
tags: [rncp38919, bloc2, backup, recovery, timescaledb, disaster-recovery]
created: 2026-04-14
source_of_truth: infra/backups/pg_backup.sh
related: [[equipes/05-devops-infra]], [[bloc2-infrastructure/db-normalization-3nf]], [[bloc2-infrastructure/db-ddl-init]]
---

# Sauvegarde et reprise d'activite -- Base de donnees CryptoBot

## Contexte RNCP

Ce document couvre la competence **C2.2.3 (Assurer la perennite des donnees)** du Bloc 2 du RNCP38919. Il decrit :

1. La strategie de sauvegarde quotidienne
2. Les specificites TimescaleDB (hypertables, chunks compresses)
3. La procedure de restauration
4. Les engagements RPO / RTO
5. Le protocole de test mensuel
6. La couche objet (MinIO) et la replication externe
7. Le chiffrement au repos des backups

Ces processus sont operes par l'equipe DevOps (cf [[CryptoBot/avril/equipes/05-devops-infra]]) et documentes ici comme livrable RNCP.

## 1. Strategie de sauvegarde

### 1.1. Cadence et support

| Parametre | Valeur |
|-----------|--------|
| Frequence | Quotidienne, 03:00 UTC (creux de trafic crypto US/EU) |
| Declencheur | Cron Docker sidecar (`docker/backup/crontab`) |
| Moteur de dump | `pg_dump --format=custom` (format binaire compresse) |
| Retention locale (VPS OVH) | 7 jours |
| Retention distante (MinIO) | 30 jours |
| Chemin local | `/var/backups/cryptobot/db/YYYY-MM-DD.dump` |
| Chemin MinIO | `s3://backups/db/YYYY-MM-DD/cryptobot-YYYY-MM-DD.dump.enc` |
| Chiffrement | AES-256-CBC via `openssl enc -aes-256-cbc -pbkdf2` |

### 1.2. Script de backup

Emplacement : `infra/backups/pg_backup.sh` (execute par un conteneur sidecar `backup-runner`).

```bash
#!/usr/bin/env bash
set -euo pipefail

DATE=$(date -u +%Y-%m-%d)
DUMP_LOCAL="/var/backups/cryptobot/db/${DATE}.dump"
DUMP_ENC="${DUMP_LOCAL}.enc"
S3_TARGET="s3://backups/db/${DATE}/cryptobot-${DATE}.dump.enc"

# 1. Dump custom-format avec exclusion des chunks TimescaleDB compresses
#    (on sauvegarde seulement la table logique + le schema ; les chunks
#     compresses sont reconstruits au restore via timescaledb_post_restore)
pg_dump \
    --host="${PG_HOST}" --port="${PG_PORT}" \
    --username="${PG_USER}" --dbname="${PG_DB}" \
    --format=custom --compress=9 \
    --file="${DUMP_LOCAL}"

# 2. Chiffrement AES-256
openssl enc -aes-256-cbc -pbkdf2 -salt \
    -in  "${DUMP_LOCAL}" \
    -out "${DUMP_ENC}" \
    -pass "env:BACKUP_PASSPHRASE"

# 3. Upload MinIO
mc cp "${DUMP_ENC}" "minio/${S3_TARGET}"

# 4. Nettoyage local > 7 jours
find /var/backups/cryptobot/db -name "*.dump*" -mtime +7 -delete

# 5. Notification Grafana (alerting natif sur failure)
curl -sf -X POST "${GRAFANA_WEBHOOK_URL}" \
    -H "Content-Type: application/json" \
    -d "{\"status\":\"ok\",\"date\":\"${DATE}\",\"size\":\"$(stat -c%s ${DUMP_ENC})\"}"
```

### 1.3. Integration docker-compose

```yaml
services:
  backup-runner:
    image: cryptobot/backup-runner:latest  # pg_dump 16 + openssl + mc
    restart: unless-stopped
    env_file: .env.backup
    volumes:
      - ./infra/backups:/scripts:ro
      - backup_data:/var/backups/cryptobot
    depends_on:
      - timescaledb
    command: ["cron", "-f"]
    healthcheck:
      test: ["CMD", "pgrep", "cron"]
      interval: 1m
```

## 2. Specificites TimescaleDB

### 2.1. Probleme

Une hypertable TimescaleDB est une table logique (`crypto_prices`) partitionnee en N chunks physiques (`_timescaledb_internal._hyper_1_N_chunk`). Un `pg_dump` naif sauvegarde *tous* les chunks, y compris ceux deja compresses -- la restauration peut alors diverger de la configuration originale (perte des policies, des index locaux).

### 2.2. Protocole recommande (TimescaleDB docs)

**Backup :**
```bash
# Dump full, incluant l'extension et les chunks internes
pg_dump -Fc -d cryptobot -f cryptobot.dump
```

**Restore :**
```bash
# 1. Base fraiche
psql -c "CREATE DATABASE cryptobot;"

# 2. Pre-restore : extension + fonction timescaledb_pre_restore
psql -d cryptobot -c "CREATE EXTENSION timescaledb;"
psql -d cryptobot -c "SELECT timescaledb_pre_restore();"

# 3. Restore
pg_restore -d cryptobot --no-owner cryptobot.dump

# 4. Post-restore : reconfiguration jobs, policies, continuous aggregates
psql -d cryptobot -c "SELECT timescaledb_post_restore();"
```

**`timescaledb_post_restore()` est obligatoire** : sans lui, les jobs de retention / compression ne sont pas ratachees au nouveau cluster.

### 2.3. Alternative : `timescaledb-backup` (outil officiel)

Si disponible dans l'environnement (licence TSL), `timescaledb-backup` offre :
- Dump parallelise des chunks
- Exclusion automatique des chunks compresses (economie disque)
- Restore incremental

Non utilise en phase 1 (ecole) -- on reste sur `pg_dump --format=custom` + `timescaledb_post_restore`.

## 3. Procedure de restauration

### 3.1. Scenario : corruption / perte de donnees

**Pre-requis** : acces SSH au VPS OVH + passphrase `BACKUP_PASSPHRASE`.

```bash
# 0. Constat + communication
#    -> alerter sur canal Grafana, notifier utilisateurs via statut

# 1. Arret des ecrivains
docker compose stop api etl-worker
#    On LAISSE timescaledb et nginx tourner (lecture seule via statut degrade)

# 2. Recuperation du backup
DATE="2026-04-13"
cd /tmp && mkdir restore && cd restore
mc cp "minio/backups/db/${DATE}/cryptobot-${DATE}.dump.enc" .

# 3. Dechiffrement
openssl enc -d -aes-256-cbc -pbkdf2 \
    -in  "cryptobot-${DATE}.dump.enc" \
    -out "cryptobot-${DATE}.dump" \
    -pass "env:BACKUP_PASSPHRASE"

# 4. Preparation base cible
docker compose exec timescaledb psql -U postgres -c "DROP DATABASE IF EXISTS cryptobot_restore;"
docker compose exec timescaledb psql -U postgres -c "CREATE DATABASE cryptobot_restore;"
docker compose exec timescaledb psql -U postgres -d cryptobot_restore \
    -c "CREATE EXTENSION timescaledb;"
docker compose exec timescaledb psql -U postgres -d cryptobot_restore \
    -c "SELECT timescaledb_pre_restore();"

# 5. Restore
docker compose exec -T timescaledb pg_restore \
    -U postgres -d cryptobot_restore --no-owner \
    < "cryptobot-${DATE}.dump"

# 6. Finalisation TimescaleDB
docker compose exec timescaledb psql -U postgres -d cryptobot_restore \
    -c "SELECT timescaledb_post_restore();"

# 7. Bascule atomique (rename swap)
docker compose exec timescaledb psql -U postgres -c "
    ALTER DATABASE cryptobot          RENAME TO cryptobot_old;
    ALTER DATABASE cryptobot_restore  RENAME TO cryptobot;
"

# 8. Redemarrage ecrivains
docker compose start api etl-worker

# 9. Verification
curl -sf https://cryptobot.example.com/api/health
docker compose logs -f api | grep -i error

# 10. Conservation cryptobot_old (7 jours) puis drop
```

### 3.2. Scenario : perte complete du VPS

Le backup MinIO est la seule source de recuperation. Procedure :

1. Provisionner un nouveau VPS via Ansible (`infra/ansible/playbooks/provision.yml`)
2. Restaurer `.env` et `docker-compose.yml` depuis le repo Git
3. `docker compose up -d timescaledb`
4. Appliquer la procedure 3.1 etapes 2-8 avec `cryptobot_restore` renomme directement `cryptobot`

Temps estime : 45-60 minutes (DNS inclus via Cloudflare).

## 4. RPO / RTO

### 4.1. Definitions

- **RPO (Recovery Point Objective)** : pertes de donnees maximales acceptables en temps
- **RTO (Recovery Time Objective)** : delai maximal de retablissement du service

### 4.2. Engagements CryptoBot

| Metrique | Valeur | Justification |
|----------|--------|---------------|
| RPO | 24 heures | Backup quotidien 03:00 UTC |
| RTO (corruption, backup local) | < 1 heure | Procedure 3.1, restore depuis `/var/backups` |
| RTO (perte VPS, backup MinIO) | < 4 heures | Provisioning Ansible + restore + DNS propagation |

### 4.3. Impact metier

Le projet est **informationnel** (pas d'execution de trade). Les donnees perdues sur une fenetre de 24h sont :
- Les bougies OHLCV : **reconstructibles via re-fetch Binance / CoinGecko / CCXT** (les APIs exposent l'historique)
- Les signaux generes : reconstructibles par re-execution du moteur de regles
- Les articles scrapes : partiellement re-fetchables par republication RSS
- Les utilisateurs / portefeuille / watchlist : **non reconstructibles** -- perte tolere 24h max

Pour abaisser le RPO < 24h, l'option est **WAL archiving** (PITR) : continuer a streamer les WAL vers MinIO toutes les 15 minutes. Non implemente en phase 1, documente en roadmap Bloc 3.

## 5. Test de restauration mensuel

### 5.1. Cadence et environnement

| Parametre | Valeur |
|-----------|--------|
| Frequence | 1er lundi de chaque mois, 10:00 UTC |
| Environnement cible | `staging` (VPS separe, meme topologie que prod) |
| Responsable | Equipe DevOps |
| Tracabilite | Issue GitHub cloture `backup-test-YYYY-MM` |

### 5.2. Protocole

```bash
# 1. Telecharger le backup prod le plus recent
LATEST=$(mc ls minio/backups/db | tail -1 | awk '{print $NF}')
mc cp "minio/backups/db/${LATEST}" /tmp/

# 2. Restaurer sur staging (procedure 3.1, DB = cryptobot_test)

# 3. Executer les requetes de verification
docker compose -f staging exec timescaledb psql -U postgres -d cryptobot_test <<SQL
-- 3.1 Comptage des tables
SELECT COUNT(*) FROM users;
SELECT COUNT(*) FROM trading_signals;
SELECT hypertable_name, num_chunks
    FROM timescaledb_information.hypertables;

-- 3.2 Verification policies
SELECT proc_name, config
    FROM timescaledb_information.jobs
    WHERE hypertable_name = 'crypto_prices';

-- 3.3 Sample data
SELECT symbol, timeframe, MAX("timestamp") AS latest
    FROM crypto_prices
    GROUP BY symbol, timeframe
    ORDER BY symbol;
SQL

# 4. Rapport : ecrire dans l'issue GitHub
#    - taille du dump
#    - duree du restore
#    - nombre de chunks, de lignes
#    - ecarts avec le snapshot prod (le cas echeant)

# 5. Destruction de l'environnement de test
docker compose -f staging down -v
```

### 5.3. Criteres de succes

- Restore termine en < 1 heure
- Aucun echec `pg_restore` (exit code 0)
- `timescaledb_post_restore()` reussi
- Ecart de comptage vs prod < 0.1% (attendu, car backup est J-1)
- Continuous aggregates et policies operationnelles

Un echec declenche un ticket P1 et une revue de la strategie.

## 6. Object store MinIO

### 6.1. Configuration bucket

| Parametre | Valeur |
|-----------|--------|
| Bucket | `backups` |
| Versioning | Active (immutabilite 30 j) |
| Lifecycle | Transition vers tier cold apres 7 j, expiration apres 30 j |
| Replication | Bucket-to-bucket vers Backblaze B2 (offsite geographique) |
| Acces | IAM policy dedied `backup-writer` (PUT only), `backup-reader` (GET only) |
| Chiffrement serveur | SSE-S3 (AES-256 gere par MinIO) |

### 6.2. Lifecycle rule (extrait)

```json
{
  "Rules": [
    {
      "ID": "transition-cold-after-7d",
      "Status": "Enabled",
      "Filter": {"Prefix": "db/"},
      "Transitions": [{"Days": 7, "StorageClass": "COLD"}],
      "Expiration": {"Days": 30}
    }
  ]
}
```

### 6.3. Replication externe

```
MinIO (VPS OVH, Strasbourg)
        v site-to-site replication (mc replicate)
Backblaze B2 (US-West)
```

Justification : la defaillance concurrente de deux providers (OVH + Backblaze) est un evenement de type "extinction niveau projet ecole", acceptable.

## 7. Chiffrement

### 7.1. Chiffrement au repos

- **Avant upload MinIO** : `openssl enc -aes-256-cbc -pbkdf2 -salt` avec passphrase issue de la variable d'env `BACKUP_PASSPHRASE` (stockee dans le secret manager Ansible Vault).
- **Sur MinIO** : SSE-S3 active (AES-256 gere par MinIO).
- **Sur Backblaze** : SSE-B2 active.

Double couche : si MinIO est compromis, les dumps restent chiffres via OpenSSL.

### 7.2. Rotation des cles

| Cle | Cadence | Procedure |
|-----|---------|-----------|
| `BACKUP_PASSPHRASE` | 90 jours | Ansible Vault rotate + re-chiffrement des 30 derniers dumps |
| SSE-S3 MinIO | 180 jours | `mc admin config set myminio kms ...` |

### 7.3. Chiffrement en transit

- VPS -> MinIO : TLS 1.3 (Nginx sidecar avec cert Let's Encrypt)
- MinIO -> Backblaze : TLS 1.3 (natif)
- Application -> TimescaleDB : TLS optionnel en local (socket), obligatoire en reseau

## 8. References

- [[CryptoBot/avril/equipes/05-devops-infra]] -- operations DevOps prod
- [[bloc2-infrastructure/db-normalization-3nf]] -- conception schema
- [[bloc2-infrastructure/db-ddl-init]] -- DDL reconstruit
- TimescaleDB docs : https://docs.timescale.com/self-hosted/latest/backup-and-restore/
- PostgreSQL 16 docs : https://www.postgresql.org/docs/16/backup-dump.html
- `infra/backups/pg_backup.sh` -- script de backup (a implementer)
- `docker-compose.yml` -- service `backup-runner` (a ajouter)
