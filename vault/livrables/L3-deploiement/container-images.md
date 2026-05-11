---
type: rncp
bloc: 3
competence: C3.1-C3.2
source: docker-compose.yml + src/{api,etl,frontend,ml}/Dockerfile*
tags: [cryptobot, rncp, bloc3, containers, docker, securite]
created: 2026-04-14
ingested_by: L3-Containers-Sec
certif: RNCP38919
---

# Container Images — Inventaire, Durcissement, Empreintes

Livrable Bloc 3 — Deployer et securiser une application (RNCP38919). Reference : [[../../architecture/dp01-docker-infrastructure]], [[../../audit/remediation/phase1]], [[../../audit/remediation/phase2]].

## 1. Vue globale — 12 services Docker

Deploiement `docker-compose.yml` + overlay `docker-compose.prod.yml`. Deux reseaux bridge isoles (`frontend-net`, `backend-net`). Quatre volumes persistes. Memoire totale ~5.8 GB en dev, reduite a ~4.3 GB en prod VPS.

| # | Service | Image base | Role | Port interne | Healthcheck | Memoire limit prod |
|---|---------|-----------|------|--------------|-------------|--------------------|
| 1 | `timescaledb` | `timescale/timescaledb:latest-pg16` | DB time-series (hypertables, compression) | 5432 | `pg_isready -U cryptobot` (10s) | 768M |
| 2 | `minio` | `minio/minio:latest` | Stockage objet S3 (artifacts MLflow, datasets) | 9000 / 9001 | `curl /minio/health/live` (30s) | 256M |
| 3 | `mlflow` | Custom (`src/ml/Dockerfile.mlflow`) | Tracking ML, registry modeles | 5000 | `curl /` (30s, start 60s) | 1G |
| 4 | `api` | Custom (`src/api/Dockerfile`) | FastAPI REST + auth JWT | 8000 | `curl /health` (30s, start 15s) | 384M |
| 5 | `frontend` | Custom (`src/frontend/Dockerfile`) | Streamlit dashboard | 8501 | `curl /crypto/_stcore/health` (30s) | 384M |
| 6 | `etl-worker` | Custom (`src/etl/Dockerfile`) | Collecteurs Binance/CoinGecko + APScheduler | 8080 (interne) | `python -c "import src.etl"` (30s) | 512M |
| 7 | `ml-worker` | Custom (`src/ml/Dockerfile`) | Generateur signaux (rule engine Phase 1) | n/a | `python -c "import src.ml.signal_generator"` (60s) | 512M |
| 8 | `nginx` | `nginx:alpine` | Reverse proxy, TLS, rate limit | 80 / 443 | `wget /health` (30s) | dev only (disabled prod, host nginx) |
| 9 | `prometheus` | `prom/prometheus:v2.52.0` | Metriques TSDB 15j retention | 9090 | `wget /-/healthy` (30s) | 256M |
| 10 | `grafana` | `grafana/grafana:10.4.2` | Dashboards + alerting natif | 3000 | `wget /api/health` (30s) | 384M |
| 11 | `postgres-exporter` | `prometheuscommunity/postgres-exporter:v0.15.0` | Metriques PG | 9187 | implicite | 64M |
| 12 | `nginx-exporter` | `nginx/nginx-prometheus-exporter:1.1.0` | Metriques nginx stub_status | 9113 | implicite | 32M |

Services supplementaires prod (`docker-compose.prod.yml`) :
- `node-exporter` (`prom/node-exporter:v1.8.0`) — metriques host VPS, 64M, Linux only
- `cadvisor` (`gcr.io/cadvisor/cadvisor:v0.49.1`) — metriques containers, privileged, 256M

## 2. Dockerfiles applicatifs (4)

Pattern commun : builder `python:3.11-slim` → runtime `python:3.11-slim`. Choix `slim` (Debian) plutot qu'`alpine` pour eviter les problemes de compilation des wheels `numpy/pandas/polars` contre `musl libc`. `uv` non utilise ici (pip direct) mais cache mount prevu pour la remediation Phase 2 (pinning `python:3.11.8-slim`).

### 2.1 API — `src/api/Dockerfile` (50 lignes)

```dockerfile
FROM python:3.11-slim AS builder
# pip install --prefix=/install requirements.txt (shared puis api)

FROM python:3.11-slim
# Installe curl + Node.js 20 (CLI @anthropic-ai/claude-code pour chat LLM)
RUN useradd --uid 1000 --create-home appuser   # UID aligne host pour ~/.claude/ mount
WORKDIR /app
COPY --from=builder /install /usr/local
COPY --chown=appuser:appuser src/shared/ /app/src/shared/
COPY --chown=appuser:appuser src/api/ /app/src/api/
COPY --chown=appuser:appuser src/etl/migrations/ /app/src/etl/migrations/
COPY --chown=appuser:appuser alembic.ini /app/alembic.ini
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Specificite : UID **1000** (non 1001) pour permettre le bind mount `${HOME}/.claude/:/home/appuser/.claude/` en lecture des tokens OAuth utilisateur host. Point d'attention securitaire documente dans [[../../audit/domaine/infra]].

### 2.2 ETL — `src/etl/Dockerfile` (34 lignes)

```dockerfile
FROM python:3.11-slim AS builder
# pip install (shared + etl) dans /install

FROM python:3.11-slim
RUN useradd --uid 1001 --create-home appuser
COPY --from=builder /install /usr/local
COPY --chown=appuser:appuser src/shared/ /app/src/shared/
COPY --chown=appuser:appuser src/etl/ /app/src/etl/
USER appuser
HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')"
EXPOSE 8080
CMD ["python", "-m", "src.etl.main"]
```

Pas de `curl` installe — healthcheck via `urllib.request` stdlib → reduit surface d'attaque. UID **1001**.

### 2.3 Frontend — `src/frontend/Dockerfile` (43 lignes)

```dockerfile
FROM python:3.11-slim AS builder
# pip install (shared + frontend)

FROM python:3.11-slim
RUN apt-get install -y --no-install-recommends curl
RUN useradd --uid 1001 --create-home appuser
ENV STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
USER appuser
EXPOSE 8501
HEALTHCHECK CMD curl -f http://localhost:8501/_stcore/health
CMD ["streamlit", "run", "src/frontend/app.py",
     "--server.maxUploadSize=5",
     "--server.enableXsrfProtection=true"]
```

`STREAMLIT_BROWSER_GATHER_USAGE_STATS=false` → no telemetrie tiers (conformite RGPD, cf [[CryptoBot/avril/rncp/livrables/L3-deploiement/rgpd-compliance]]). XSRF protection active. Upload limite 5 MB.

### 2.4 ML Worker — `src/ml/Dockerfile` (32 lignes)

```dockerfile
FROM python:3.11-slim AS builder
# pip install (shared + ml)

FROM python:3.11-slim
RUN useradd --uid 1001 --create-home appuser
USER appuser
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import src.ml.signal_generator" || exit 1
CMD ["python", "-m", "src.ml"]
```

Healthcheck via import Python (pas de serveur HTTP expose). Pas d'`EXPOSE`.

## 3. Image MLflow — `src/ml/Dockerfile.mlflow` (32 lignes)

```dockerfile
FROM python:3.11-slim AS builder
COPY requirements.mlflow.txt /tmp/requirements.txt
RUN pip install --upgrade pip && pip install --prefix=/install -r /tmp/requirements.txt

FROM python:3.11-slim
RUN apt-get install -y --no-install-recommends curl
RUN useradd --uid 1001 --create-home appuser
USER appuser
EXPOSE 5000
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=5 \
    CMD curl -f http://localhost:5000/ || exit 1
CMD ["mlflow", "server", "--host", "0.0.0.0", "--port", "5000"]
```

Commande surchargee dans compose :
```
mlflow db upgrade postgresql://...@timescaledb:5432/cryptobot || true &&
mlflow server --workers 2
  --backend-store-uri postgresql://...@timescaledb:5432/cryptobot
  --default-artifact-root s3://mlflow-artifacts/
```

Backend store PostgreSQL (tables `experiments`, `runs`, `metrics` dans la meme DB TimescaleDB). Artifact store S3 via MinIO (bucket `mlflow-artifacts`, credentials `AWS_ACCESS_KEY_ID/SECRET` = `MINIO_ROOT_USER/PASSWORD`).

## 4. Images tierces (pinning)

| Service | Image pinnee | SemVer | Justification |
|---------|-------------|--------|---------------|
| timescaledb | `timescale/timescaledb:latest-pg16` | floating (a fixer `2.14.2-pg16` cf D1) | PG16 = LTS 2028 |
| minio | `minio/minio:latest` | floating (a fixer `RELEASE.2025-01-01`) | issue D1 tracee |
| mlflow | build local | n/a | contenu `requirements.mlflow.txt` pinne |
| prometheus | `prom/prometheus:v2.52.0` | pinne | remediation Phase 1 |
| grafana | `grafana/grafana:10.4.2` | pinne | remediation Phase 1 |
| nginx | `nginx:alpine` | floating (a fixer `1.27.1-alpine`) | remediation Phase 1 |
| postgres-exporter | `prometheuscommunity/postgres-exporter:v0.15.0` | pinne | OK |
| nginx-exporter | `nginx/nginx-prometheus-exporter:1.1.0` | pinne | OK |
| node-exporter | `prom/node-exporter:v1.8.0` | pinne | prod only |
| cadvisor | `gcr.io/cadvisor/cadvisor:v0.49.1` | pinne | prod only |

Regle interdite CLAUDE.md : **pas de `:latest` en prod**. Les 3 floating tags restants (`timescaledb`, `minio`, `nginx`) sont trackes dans [[../../audit/remediation/phase1]] issue D1 — remediation livree mais pas encore mergee dans la branche `dev` audited.

## 5. Reseaux Docker

```
frontend-net (bridge)                 backend-net (bridge)
  nginx (80, 443) ──────────┐            ┌─ timescaledb (5432)
  frontend (8501) ──────────┤            ├─ minio (9000, 9001)
  api (8000) ──────── (2 NIC) ──────────┤─ mlflow (5000)
  nginx-exporter (9113) ────┘            ├─ api (2e NIC)
                                         ├─ etl-worker
                                         ├─ ml-worker
                                         ├─ prometheus (9090)
                                         ├─ grafana (3000)
                                         ├─ postgres-exporter (9187)
                                         ├─ nginx-exporter (2e NIC)
                                         ├─ node-exporter (9100) [prod]
                                         └─ cadvisor (8080) [prod]
```

Isolation : les services data (`timescaledb`, `minio`, `mlflow`) n'ont aucune interface reseau sur `frontend-net`. Seule l'API est multi-homed. Tous les bind ports exposes sur host sont en `127.0.0.1:PORT` (jamais `0.0.0.0`) sauf nginx 80/443.

## 6. Volumes persistants (4)

| Volume | Contenu | Taille attendue | Backup |
|--------|---------|-----------------|--------|
| `timescaledb-data` | PostgreSQL + hypertables OHLCV, signals, users | 5-20 GB | `pg_dump` quotidien, `infra/scripts/rollback.sh` |
| `minio-data` | Buckets `mlflow-artifacts`, `raw-data`, `backups` | 10-50 GB | `infra/scripts/backup-minio.sh` (mirror S3 externe) |
| `prometheus-data` | TSDB metriques retention 15j | ~2 GB | non critique, regenerable |
| `grafana-data` | Dashboards + alerting state | <100 MB | provisioning in `infra/grafana/` versionned |

## 7. Empreintes images — build reproductible

Post-build sur CI/CD, ces empreintes sont capturees pour tracabilite RNCP C3.1. Commandes :

```bash
# 1. Build
docker compose build
# 2. Inspection
docker images --format "{{.Repository}}:{{.Tag}} {{.ID}} {{.Size}}"
# 3. Digest (SHA256)
docker inspect --format '{{.Id}}' cryptobot-api:$(git rev-parse --short HEAD)
```

| Service | Tag cible | SHA256 (Id) | Taille |
|---------|-----------|-------------|--------|
| cryptobot-api | `$(git rev-parse --short HEAD)` | `[A MESURER post-build]` | ~380 MB (estime) |
| cryptobot-etl | `$(git rev-parse --short HEAD)` | `[A MESURER post-build]` | ~320 MB (estime) |
| cryptobot-frontend | `$(git rev-parse --short HEAD)` | `[A MESURER post-build]` | ~280 MB (estime) |
| cryptobot-ml | `$(git rev-parse --short HEAD)` | `[A MESURER post-build]` | ~450 MB (estime, sklearn+lightgbm) |
| cryptobot-mlflow | `$(git rev-parse --short HEAD)` | `[A MESURER post-build]` | ~260 MB (estime) |
| timescale/timescaledb | `latest-pg16` | `sha256:...[docker pull output]` | ~380 MB |
| minio/minio | `latest` | `sha256:...[docker pull output]` | ~180 MB |
| prom/prometheus | `v2.52.0` | `sha256:...[docker pull output]` | ~295 MB |
| grafana/grafana | `10.4.2` | `sha256:...[docker pull output]` | ~410 MB |
| nginx | `alpine` | `sha256:...[docker pull output]` | ~45 MB |

Ces valeurs sont materialisees en CI via `docker inspect` et archivees dans l'artifact GitLab/GitHub Actions du run de deploiement.

## 8. Scan de vulnerabilites Trivy

Integration CI/CD bloquante sur HIGH/CRITICAL :

```yaml
# .github/workflows/security-scan.yml (extrait)
- name: Trivy scan
  run: |
    trivy image cryptobot-api:${{ github.sha }} \
      --severity HIGH,CRITICAL \
      --exit-code 1 \
      --ignore-unfixed \
      --format sarif \
      --output trivy-api.sarif
- uses: github/codeql-action/upload-sarif@v3
  with:
    sarif_file: trivy-api.sarif
```

Procedure manuelle avant release :
```bash
for svc in api etl frontend ml mlflow; do
  trivy image cryptobot-${svc}:$(git rev-parse --short HEAD) \
    --severity HIGH,CRITICAL --exit-code 1
done
trivy image timescale/timescaledb:latest-pg16 --severity HIGH,CRITICAL
trivy image minio/minio:latest --severity HIGH,CRITICAL
```

Resultats CI (placeholders a remplir apres run) :

| Image | CRITICAL | HIGH | MEDIUM | Statut |
|-------|----------|------|--------|--------|
| cryptobot-api | `[A MESURER]` | `[A MESURER]` | `[A MESURER]` | ? |
| cryptobot-etl | `[A MESURER]` | `[A MESURER]` | `[A MESURER]` | ? |
| cryptobot-frontend | `[A MESURER]` | `[A MESURER]` | `[A MESURER]` | ? |
| cryptobot-ml | `[A MESURER]` | `[A MESURER]` | `[A MESURER]` | ? |
| timescaledb | `[A MESURER]` | `[A MESURER]` | `[A MESURER]` | ? |

SLA : 0 CRITICAL tolere, HIGH toleres 72h avec ticket ouvert, MEDIUM : rotation trimestrielle.

## 9. Optimisations de build

- **`.dockerignore`** : exclut `.git`, `tests/`, `docs/`, `*.md`, `.venv/`, `__pycache__`, `.env*` — reduit contexte de ~200 MB a ~5 MB.
- **Multi-stage** : builder `/install` copie dans runtime → elimine `gcc`, headers, caches pip du final image (gain ~150 MB par image Python).
- **Slim base** : `python:3.11-slim` (~45 MB) vs `python:3.11` (~1 GB). Pas d'`alpine` (glibc requis pour wheels `numpy/pandas/polars/scipy/lightgbm`).
- **Cache mount uv** (prevu remediation) : `RUN --mount=type=cache,target=/root/.cache/uv uv pip install` → reconstruction ~5s vs 60s si requirements inchangees.
- **Layer ordering** : `requirements.txt` avant code → hit cache tant que deps inchangees (99% des rebuilds).
- **Pas d'install inutile** : uniquement `curl` la ou necessaire (frontend, mlflow, api). ETL utilise stdlib `urllib.request`.

## 10. Securite conteneur — hardening

Applique :
- **Non-root USER** : tous les containers applicatifs tournent en UID 1000 (api) ou 1001 (etl/frontend/ml/mlflow). Verifiable : `docker exec cryptobot-api id` → `uid=1000(appuser)`.
- **Pas de `privileged`** sauf `cadvisor` (requis pour instrumentation kernel).
- **`no-new-privileges`** : a ajouter via `security_opt: [no-new-privileges:true]` (remediation a tracer).
- **`cap_drop: [ALL]`** : a ajouter sur api/etl/frontend/ml (aucune capability requise). Remediation planifiee [[../../audit/remediation/phase3]].
- **tmpfs `/tmp`** : `tmpfs: [/tmp:size=64M,noexec]` pour eviter ecriture persistante — a ajouter.
- **read-only rootfs** : compatible pour api/etl/ml/mlflow (pas pour streamlit qui ecrit `.streamlit/`) — a tester en staging.
- **seccomp** : profil default Docker applique (blocage ptrace, mount, reboot, 44 syscalls dangereux). Pas de profil custom necessaire.
- **PID limits** : `pids_limit: 100` conseille en prod pour prevenir fork bombs.

Extrait hardening cible `docker-compose.prod.yml` :
```yaml
api:
  security_opt:
    - no-new-privileges:true
  cap_drop: [ALL]
  read_only: true
  tmpfs:
    - /tmp:size=64m,noexec,nosuid
  pids_limit: 100
```

## 11. Resource limits — prod VPS (7.6 GB RAM)

Reference `docker-compose.prod.yml` (lignes 1-72) :

| Service | Limit memoire prod | vs dev |
|---------|--------------------|--------|
| timescaledb | 768M | -232 MB |
| minio | 256M | -256 MB |
| mlflow | 1G | +512 MB (workers=2) |
| api | 384M | -128 MB |
| frontend | 384M | -128 MB |
| etl-worker | 512M | -512 MB |
| ml-worker | 512M | -512 MB |
| prometheus | 256M | -256 MB |
| grafana | 384M | +128 MB (dashboards chargees) |
| node-exporter | 64M | n/a (prod only) |
| cadvisor | 256M | n/a (prod only) |
| nginx | disabled | host nginx gere SSL/routing |
| nginx-exporter | disabled | n/a |

**Total prod ≈ 4.7 GB** sur VPS 7.6 GB — marge confort 2.9 GB pour OS + buffer cache. Conforme a la recommandation Phase 1 ([[../../audit/remediation/phase1]]).

## Sources

- `/home/jules/Documents/3-git/CryptoBot/dev/docker-compose.yml` (364 l)
- `/home/jules/Documents/3-git/CryptoBot/dev/docker-compose.prod.yml` (107 l)
- `/home/jules/Documents/3-git/CryptoBot/dev/src/api/Dockerfile` (50 l)
- `/home/jules/Documents/3-git/CryptoBot/dev/src/etl/Dockerfile` (34 l)
- `/home/jules/Documents/3-git/CryptoBot/dev/src/frontend/Dockerfile` (43 l)
- `/home/jules/Documents/3-git/CryptoBot/dev/src/ml/Dockerfile` (32 l)
- `/home/jules/Documents/3-git/CryptoBot/dev/src/ml/Dockerfile.mlflow` (32 l)

Diagrammes lies : [[../../architecture/dp01-docker-infrastructure]] | [[../../architecture/c01-macro]].

Documents lies bloc 3 : [[CryptoBot/avril/rncp/livrables/L3-deploiement/rgpd-compliance]] | [[CryptoBot/avril/rncp/livrables/L3-deploiement/secrets-rotation]].
