---
type: rncp-evidence
bloc: 3
certification: RNCP38919
composante: "C3.3 — Déploiement / C3.4 — Évidence d'exécution / C3.5 — Supervision"
source: "docker-compose.yml + infra/ + screenshots/ + prod/_index.md"
tags: [cryptobot, rncp, bloc3, prod, docker, compose, grafana, prometheus]
created: 2026-04-14
ingested_by: agent-L3-tests-evidence
status: partial
---

# Bloc 3 — Preuves d'exécution production (CryptoBot)

> Composantes RNCP38919 couvertes : **C3.3 déploiement**, **C3.4 évidence d'exécution**, **C3.5 supervision / observabilité**.
> Statut global : **PARTIEL** — les captures d'écran de l'environnement local sont disponibles ([[#5. Captures d'écran]]), mais l'accès SSH à la prod VPS OVH est actuellement désactivé (cf [[../../prod/_index]]).

## 1. Environnement cible

| Élément | Valeur |
|---------|--------|
| Hébergeur | OVH VPS ([[../../equipes/05-devops-infra]]) |
| OS | Ubuntu 22.04 LTS |
| Docker | 25.x (buildx v0.13+) |
| Docker Compose | v2 (plugin, pas docker-compose v1) |
| Reverse proxy | Nginx (image `nginx:alpine`) |
| SSL | Let's Encrypt (certbot sidecar, volume `/etc/letsencrypt`) |
| DNS | Cloudflare (proxy activé) |
| Orchestration | Docker Compose uniquement (pas de Kubernetes) |
| CI/CD | GitHub Actions (build + push images) + SSH deploy (`deploy.yml`) |

Conformité avec `.claude/rules/devops-prod.md` : Docker Compose unique, volumes nommés, network bridge isolé (`frontend-net` + `backend-net`), healthchecks sur chaque service, `restart: unless-stopped`, resource limits.

## 2. Procédure de démarrage

### 2.1. Setup initial

```bash
git clone git@github.com:juleswillard/cryptobot.git /opt/cryptobot
cd /opt/cryptobot
cp .env.example .env
# Remplir : POSTGRES_PASSWORD, MINIO_ROOT_PASSWORD, GF_SECURITY_ADMIN_PASSWORD,
#          JWT_SECRET_KEY, BINANCE_API_KEY (optionnel), COINGECKO_API_KEY
```

### 2.2. Démarrage des services

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml pull
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
docker compose ps
```

### 2.3. Vérification post-boot

```bash
# Attente healthchecks
until [ "$(docker compose ps --format json | jq -r '.[] | select(.Health != "healthy") | .Name' | wc -l)" = "0" ]; do
  echo "Waiting for services to become healthy…"; sleep 5
done

# Smoke test API
curl -f http://localhost:8000/health && echo "API OK"

# Smoke test frontend Streamlit
curl -f http://localhost:8501/crypto/_stcore/health && echo "Frontend OK"
```

## 3. Inventaire des services démarrés

Source : `docker-compose.yml` (services) + `docker-compose.prod.yml` (overrides prod).

| # | Service | Image | Port interne | Ports exposés (loopback) | État attendu |
|---|---------|-------|--------------|--------------------------|--------------|
| 1 | `timescaledb` | `timescale/timescaledb:latest-pg16` | 5432 | `127.0.0.1:5433:5432` | healthy |
| 2 | `minio` | `minio/minio:latest` | 9000, 9001 | `127.0.0.1:9000:9000`, `127.0.0.1:9001:9001` | healthy |
| 3 | `mlflow` | `build ./src/ml/Dockerfile.mlflow` | 5000 | `127.0.0.1:5000:5000` | healthy |
| 4 | `api` | `build src/api/Dockerfile` | 8000 | `127.0.0.1:8000:8000` | healthy |
| 5 | `frontend` | `build src/frontend/Dockerfile` | 8501 | `127.0.0.1:8501:8501` | healthy |
| 6 | `etl-worker` | `build src/etl/Dockerfile` | — | — | healthy |
| 7 | `ml-worker` | `build src/ml/Dockerfile` | — | — | healthy |
| 8 | `nginx` | `nginx:alpine` | 80, 443 | `0.0.0.0:80:80`, `0.0.0.0:443:443` | healthy |
| 9 | `prometheus` | `prom/prometheus:v2.52.0` | 9090 | `127.0.0.1:9090:9090` | healthy |
| 10 | `grafana` | `grafana/grafana:10.4.2` | 3000 | `127.0.0.1:3000:3000` | healthy |
| 11 | `postgres-exporter` | `prometheuscommunity/postgres-exporter:v0.15.0` | 9187 | — | running |
| 12 | `nginx-exporter` | `nginx/nginx-prometheus-exporter:1.1.0` | 9113 | — | running |

**node-exporter** et **cadvisor** sont commentés (Linux-only) et activés sur le VPS prod via `docker-compose.prod.yml` (ou uncomment dans `docker-compose.yml`).

Total : **12 services actifs en prod** (14 si node-exporter + cadvisor activés).

## 4. Healthchecks

Extrait de `docker-compose.yml` (conformité `.claude/rules/devops-prod.md` : tous les services ont un healthcheck).

| Service | Test | interval | timeout | retries | start_period |
|---------|------|---------:|--------:|--------:|-------------:|
| `timescaledb` | `pg_isready -U cryptobot` | 10s | 5s | 5 | 20s |
| `minio` | `curl -f http://localhost:9000/minio/health/live` | 30s | 10s | 3 | 15s |
| `mlflow` | `curl -f http://localhost:5000/` | 30s | 10s | 5 | 60s |
| `api` | `curl -f http://localhost:8000/health` | 30s | 10s | 3 | 15s |
| `frontend` | `curl -f http://localhost:8501/crypto/_stcore/health` | 30s | 10s | 3 | 15s |
| `etl-worker` | `python -c "import src.etl"` | 30s | 5s | 3 | 30s |
| `ml-worker` | `python -c "import src.ml.signal_generator"` | 60s | 10s | 3 | 30s |
| `nginx` | `wget --spider http://127.0.0.1/health` | 30s | 10s | 3 | — |
| `prometheus` | `wget --spider http://localhost:9090/-/healthy` | 30s | 10s | 3 | — |
| `grafana` | `wget --spider http://localhost:3000/api/health` | 30s | 10s | 3 | — |

Chaînage `depends_on: condition: service_healthy` :

- `mlflow` → `timescaledb` + `minio`
- `api` → `timescaledb` + `minio`
- `frontend` → `api`
- `etl-worker` → `timescaledb` + `minio`
- `ml-worker` → `timescaledb` + `minio` + `mlflow`
- `nginx` → `api` + `frontend`
- `prometheus` → `api`
- `grafana` → `prometheus`
- `postgres-exporter` → `timescaledb`

## 5. Captures d'écran

Source : `/home/jules/Documents/3-git/CryptoBot/dev/screenshots/` (capturées en local sur un déploiement Docker Compose identique à la prod).

| Fichier | Service | Contenu attendu |
|---------|---------|-----------------|
| `00-api-swagger.png` | API FastAPI | Swagger UI (`/docs`) listant les endpoints `/api/v1/{auth,crypto,signals,news,portfolio,watchlist,system,chat}` |
| `01-frontend-streamlit.png` | Frontend Streamlit | Page d'accueil `/crypto` — navigation 5 pages (dashboard, veille, portfolio, analytics, performance) |
| `01-grafana.png` | Grafana | Dashboard System overview — CPU, RAM, disk I/O |
| `02-mlflow.png` | MLflow UI | Experiments list + artifacts stockés sur MinIO (`s3://mlflow-artifacts/`) |
| `03-minio.png` | MinIO Console | Buckets `mlflow-artifacts`, `datasets`, `backups` |
| `04-prometheus.png` | Prometheus | Targets page — `api:8000/metrics`, `postgres-exporter:9187`, `nginx-exporter:9113` toutes UP |
| `05-frontend-streamlit.png` | Frontend Streamlit | Page détail (probablement dashboard avec candlestick + indicateurs) |

**Note** : le chemin décrit dans la consigne (`infra/screenshots/`) n'existe pas ; les captures réelles sont dans `CryptoBot/dev/screenshots/` (7 fichiers PNG trouvés). La capture `mlflow-experiments.png` annoncée existe sous le nom `02-mlflow.png`, et `minio-buckets.png` sous `03-minio.png`.

## 6. Logs applicatifs

### 6.1. Accès via Docker Compose

```bash
docker compose logs -f api            # logs temps réel API
docker compose logs -f --tail=100 etl-worker
docker compose logs --since 1h grafana
```

### 6.2. Agrégation Loki (prévu)

Stack de logs prévue (conformité `.claude/rules/devops-prod.md`) :

- **Loki** 2.9+ comme backend de logs.
- **Docker Loki plugin** (`loki-docker-driver`) configuré globalement dans `/etc/docker/daemon.json` — pas Promtail (EOL mars 2026).
- Rétention 30 jours.
- Dashboards Grafana "Logs by service" et "Error rate" (à ajouter, non présents dans `infra/grafana/dashboards/` aujourd'hui qui contient `api_overview.json`, `business.json`, `database.json`, `system.json`).

## 7. Métriques

Prometheus scrape sources (source : `infra/prometheus/prometheus.prod.yml`) :

| Cible | Port | Endpoint | Intervalle |
|-------|-----:|----------|-----------:|
| `api` | 8000 | `/metrics` | 15s |
| `nginx-exporter` | 9113 | `/metrics` | 15s |
| `postgres-exporter` | 9187 | `/metrics` | 30s |
| `node-exporter` | 9100 | `/metrics` | 15s |
| `cadvisor` | 8080 | `/metrics` | 30s |

Métriques d'application publiées par FastAPI via `prometheus-fastapi-instrumentator` :
- `http_requests_total{method,handler,status}`
- `http_request_duration_seconds_bucket{handler,method}` (histograme)
- `http_requests_in_progress{handler,method}`
- custom : `signals_generated_total{symbol,direction}`, `etl_collector_errors_total{source}`

## 8. Dashboards Grafana

Dashboards provisionnés (`infra/grafana/dashboards/*.json`) :

| Dashboard | Fichier | Contenu |
|-----------|---------|---------|
| **System overview** | `system.json` | CPU, RAM, disk, network (node-exporter + cadvisor) |
| **API overview** | `api_overview.json` | p50/p95/p99 latence, req/s, taux d'erreur 5xx, top endpoints |
| **Database** | `database.json` | TimescaleDB stats — connexions actives, cache hit ratio, top queries, taille des hypertables |
| **Business** | `business.json` | Signals generated/h, ETL job success rate, confidence score distribution, active users |

Dashboards prévus (non provisionnés encore) :
- **ETL pipeline** — run durations per collector, rows inserted, error ratios.
- **ML signals** — confidence distribution, rule triggers heatmap.
- **Logs** — error rate, top error messages (après déploiement Loki).

## 9. Alerting

**Choix** : Grafana Alerting natif (pas Alertmanager — conformité `.claude/rules/devops-prod.md`).

Règles configurées (8 règles — référence D6 Phase 3) :

| Alerte | Condition | Sévérité | Action |
|--------|-----------|---------:|--------|
| API 5xx error rate | `rate(http_requests_total{status=~"5.."}[5m]) > 0.01` | critical | notification Discord + email |
| API p95 latency | `histogram_quantile(0.95, http_request_duration_seconds_bucket) > 0.5` | warning | notification Discord |
| DB disk usage | `pg_database_size_bytes / (1024^3) > 0.8 * disk_total_gb` | critical | email + escalade |
| DB connections saturated | `pg_stat_activity_count / pg_settings_max_connections > 0.8` | warning | Discord |
| MLflow down | `up{job="mlflow"} == 0` | critical | email |
| ETL worker down | `up{job="etl-worker"} == 0` for 5m | warning | Discord |
| Prometheus targets down | `up == 0` | warning | Discord |
| Grafana itself unreachable | synthetic check | critical | email + SMS |

## 10. Backup verification

- **Job cron** : `03:00 UTC` quotidien, défini dans `infra/ansible/playbooks/backup.yml` (`scripts/backup-db.sh`).
- **Flux** : `pg_dump` → compression gzip → upload S3-compatible `s3://backups/db/{yyyy-mm-dd}/cryptobot-db.sql.gz` + `s3://backups/minio/{yyyy-mm-dd}/` (snapshots de bucket).
- **Rétention** : 30 jours glissants.
- **Preuve** : listing S3 attendu `aws s3 ls s3://backups/db/ --recursive | tail -30` — 30 dumps horodatés consécutifs.
- **Restore test** : procédure documentée dans `infra/ansible/playbooks/provision.yml`, recovery window ≤ 1h.

## 11. Accès prod

> Statut : **ACTUELLEMENT INACCESSIBLE** (cf [[../../prod/_index]]).

Raison : le serveur MCP `hex-ssh` est désactivé (`REMOTE_SSH_DISABLED`). Aucun alias VPS n'est configuré dans `~/.ssh/config`.

Procédure de restauration d'accès :

1. Exporter `REMOTE_SSH_MODE=safe` dans l'environnement MCP `hex-ssh`, redémarrer Claude Code.
2. Ajouter un bloc dans `~/.ssh/config` :
   ```
   Host cryptobot
     HostName <ip-ou-fqdn-ovh>
     User deploy
     IdentityFile ~/.ssh/id_cryptobot
     IdentitiesOnly yes
   ```
3. Déposer la clé publique correspondante sur le VPS (`~deploy/.ssh/authorized_keys`).
4. Relancer le pipeline `agent-09-hex-ssh` pour générer `containers.md`, `nginx.md`, `grafana.md`, `loki.md`, `vps-state.md`.

Livrables bloqués tant que l'accès n'est pas rétabli :
- [ ] `docker compose ps` output
- [ ] `docker compose logs` extraits
- [ ] `nginx -T` (vhosts, upstreams, certs)
- [ ] `systemctl status docker` + `docker info`
- [ ] Versions runtime (Python 3.11.x exact, Docker 25.x exact)

## 12. MLflow run ID

Après premier déploiement Phase 1 (rule-based), aucun modèle ML n'est encore entraîné donc aucun run MLflow persistant. Phase 2 :

- Experiment : `cryptobot-phase2-baseline`
- Run ID attendu : `runs/XXXXX` (placeholder à renseigner après premier `mlflow.log_model`).
- Stockage artefacts : `s3://mlflow-artifacts/{experiment_id}/{run_id}/artifacts/model/`.
- Métriques trackées : `precision_buy`, `precision_sell`, `recall_buy`, `recall_sell`, `f1_weighted`, `sharpe_ratio_backtest`.

## 13. Références

- [[../../equipes/05-devops-infra]] — contrat DevOps complet.
- [[../../architecture/dp01-docker-infrastructure]] — diagramme de déploiement.
- [[../../prod/_index]] — état courant de la prod (ROUGE, SSH désactivé).
- [[../../audit/remediation/phase3]] — D6 à D10 (règles Grafana, secrets GH Actions, compose v2, logs persistants, override example).
- [[../../audit/technique/ci-cd-secrets]] — secrets GitHub Actions documentés.
- `docker-compose.yml` — 364 lignes, 12 services, healthchecks + limites mémoire.
- `docker-compose.prod.yml` — overrides prod (node-exporter, cadvisor, TLS).
- `.github/workflows/{ci.yml,deploy.yml}` — CI (lint + tests + cov) + Deploy (docker build + push + SSH).
- `infra/grafana/dashboards/{api_overview,business,database,system}.json` — dashboards provisionnés.
- `infra/prometheus/prometheus.prod.yml` — scrape config prod.
- `infra/ansible/playbooks/{provision,deploy,backup,ssl}.yml` — automation VPS.
- [[CryptoBot/avril/rncp/livrables/L3-deploiement/test-coverage-report]] — tests verts (1200 passed).
- [[CryptoBot/avril/rncp/livrables/L3-deploiement/cicd-evidence]] — preuves pipeline CI (à produire).
