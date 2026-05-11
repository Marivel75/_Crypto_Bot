---
type: rncp-competences-bloc
bloc: B3
source: rncp-agent-supervisor
tags: [cryptobot, rncp, competences, bloc3]
created: 2026-04-14
---

# Bloc B3 — Déployer une solution d'analyse de données massives intégrant l'IA

13 compétences. Chaque compétence liste les **livrables de preuve**, les **artefacts code/infra**, et une **phrase de justification**.

---

## C3.1 — Collecter les données structurées et non structurées

**Preuves** : `[[etl-execution-report]]` §2 Sources (6 sources), `[[etl]]`, `src/etl/collectors/`
**Artefacts** : `binance.py`, `coingecko.py`, `ccxt_collector.py`, `fear_greed.py`, `news.py` (RSS)
**Justification** : 6 collectors hétérogènes — structurées (OHLCV JSON REST, order book WebSocket) et non structurées (news RSS, sentiment texte). Auth, pagination, retry exp-backoff 5 tentatives, circuit breaker.

---

## C3.2 — Élaborer des solutions de stockage

**Preuves** : `[[db-normalization-3nf]]`, `[[db-ddl-init]]`, `[[er01-database-schema]]`, `[[db-backup-recovery]]`
**Artefacts** : TimescaleDB hypertable `crypto_prices` (compression 7j, rétention 90j), MinIO buckets `s3://raw/`, `s3://processed/`, `s3://mlflow/`, `s3://backups/`
**Justification** : 2 couches — temporelle (TimescaleDB) + objet (MinIO Parquet). Choix justifiés par volumes (~117 k records/jour), patterns d'accès (range scan par (symbol, timeframe)), coût (self-hosted S3-compatible).

---

## C3.3 — Concevoir les procédures d'extraction, de traitement et de stockage

**Preuves** : `[[etl-execution-report]]`, `[[ac01-etl-pipeline]]` (diagramme activité), `[[c02-etl-components]]`
**Artefacts** : `src/etl/main.py` + `src/etl/jobs.py` + 10 jobs APScheduler
**Justification** : pipeline formalisé en 3 étapes (extract → transform → load), 10 jobs schedulés (priority 1min, all 5min, news 15min, F&G 1h, etc.), SLA tracés. Procédures pérennes via Docker + restart policy.

---

## C3.4 — Transformer les données en un format approprié pour l'analyse

**Preuves** : `[[etl-data-quality]]`, `src/etl/transformers/`
**Artefacts** : `deduplicate.py`, `validate.py`, `indicators.py` (RSI/Bollinger/MACD), `gap_detector.py`
**Justification** : validation Pydantic v2 (CL01), calcul d'indicateurs vectorisés (Polars), dédoublonnage sur clé naturelle (symbol, timeframe, timestamp), détection de gaps avec tolérance par TF.

---

## C3.5 — Analyser les données

**Preuves** : `[[ml-justification-phase1]]`, `[[cl04-ml-rules-models]]`, `[[c03-ml-components]]`
**Artefacts** : `src/ml/rules/engine.py` (4 règles pondérées), `src/ml/signal_generator.py` (blend 60/40)
**Justification** : moteur d'analyse rules-first (RSI 0.25 + Bollinger 0.25 + Harmonic 0.30 + Trend 0.20), interprétable et auditable. Sortie = signal BUY/SELL/HOLD avec confidence ≥ 0.6.

---

## C3.6 — Automatiser les circuits de collecte, de traitement et de stockage

**Preuves** : `[[etl-execution-report]]` §6 Orchestration APScheduler (tableau 10 jobs)
**Artefacts** : `src/etl/main.py` (scheduler startup), Docker `restart: unless-stopped`
**Justification** : 100% automatisé via APScheduler dans un worker dédié, pas d'intervention manuelle. Healthcheck `import src.etl` + métriques Prometheus pour monitoring runtime.

---

## C3.7 — Développer un algorithme d'intelligence artificielle

**Preuves** : `[[ml-justification-phase1]]` (Phase 1 rules), `[[ml-phase2-scope-revise]]` (Phase 2 XGBoost+LightGBM)
**Artefacts** : `src/ml/rules/engine.py`, `src/ml/models/trainer.py`, `src/ml/models/predictor.py`, MLflow experiment `cryptobot-signals`
**Justification** : approche hybride — Phase 1 rules interprétables (confiance auditeur), Phase 2 ML supervisé (XGBoost + LightGBM classif direction) avec walk-forward + purging + embargo (anti data-leakage). Blend 60/40.

---

## C3.8 — Concevoir une interface de programmation entre les composants de la solution

**Preuves** : `[[api-contract-v1]]` (491 L), `[[api-openapi]]` (OpenAPI 3.1), `[[c04-api-components]]`, `[[cl03-api-schemas]]`
**Artefacts** : `src/api/main.py` (8 routers : auth, crypto, signals, chat, news, portfolio, system, watchlist), JWT HS256, Swagger UI `/api/docs`, ReDoc `/api/redoc`
**Justification** : API REST versionnée `/api/v1/*`, Pydantic v2 schemas, enveloppe `ApiResponse[T]`, rate limiting Nginx (30r/s API, 5r/m auth), observabilité `X-Request-ID`.

---

## C3.9 — Conteneuriser les composants de l'architecture

**Preuves** : `[[container-images]]`, `[[dp01-docker-infrastructure]]`
**Artefacts** : 4 Dockerfiles applicatifs (api, etl, frontend, ml) + Dockerfile.mlflow, multi-stage (builder → runtime slim), USER non-root, HEALTHCHECK, EXPOSE
**Justification** : conteneurs slim, scan Trivy intégré CI, cap_drop ALL, no-new-privileges. 12 services Docker, 2 networks (frontend-net / backend-net), 4 volumes persistants, ~5.8 GB RAM.

---

## C3.10 — Déployer le modèle dans un environnement de production

**Preuves** : `[[cicd-evidence]]`, `[[prod-run-evidence]]`, `.github/workflows/deploy.yml`
**Artefacts** : Ansible playbooks (`deploy.yml`, `provision.yml`, `backup.yml`, `ssl.yml`), script `scripts/deploy.sh`, VPS OVH + Nginx + Let's Encrypt + Cloudflare
**Justification** : déploiement reproductible (Ansible idempotent), 3 environnements (dev local / staging / prod VPS). Rollback automatique si healthcheck KO 120s.

---

## C3.11 — Orchestrer les services de la solution

**Preuves** : `[[dp01-docker-infrastructure]]`, `[[infra/ansible/README]]`
**Artefacts** : `docker-compose.yml` (364 L, 12 services), `docker-compose.prod.yml` (memory limits 256-768MB), dépendances `depends_on` + `condition: service_healthy`
**Justification** : orchestration déclarative Docker Compose (pas K8s pour V1, ADR justifiée). Séparation réseaux, volumes nommés, healthchecks obligatoires sur tous les services.

---

## C3.12 — Contrôler la mise en production de la solution

**Preuves** : `[[test-coverage-report]]` (1200 tests, ~81.5% couverture), `[[prod-run-evidence]]`
**Artefacts** : `tests/unit/`, `tests/integration/`, `tests/e2e/`, `pyproject.toml` `fail_under=78`, Grafana Alerting, Prometheus alerts (API 5xx > 1%, p95 > 500ms, DB disk > 80%)
**Justification** : contrôle multi-niveaux — tests automatiques en CI, healthchecks Docker, monitoring Grafana + Loki logs, alerting Grafana natif (pas Alertmanager). Go/No-Go par checklist sprint.

---

## C3.13 — Automatiser le déploiement de nouvelles versions de la solution et son monitoring

**Preuves** : `[[cicd-evidence]]`, `.github/workflows/ci.yml` + `deploy.yml`, `.gitlab-ci.yml`
**Artefacts** : GitHub Actions (lint → test → build → push GHCR → SSH deploy → healthcheck → rollback), GitLab CI mirror (école), Vector.dev → Loki (remplace Promtail EOL mars 2026)
**Justification** : pipeline CD complet avec tag SHA systématique, concurrency lock anti-deploys concurrents, notifications Slack, artifacts HTML coverage publiés. Monitoring observabilité triple : metrics (Prometheus), logs (Loki), traces (OpenTelemetry roadmap S14).

---

## Matrice compétences × livrables RNCP

| Compétence | L2 | L3 | L4 | L5 | Soutenance |
|------------|----|----|----|----|-----------:|
| C3.1 Collecter | ✅ | — | — | — | ✅ |
| C3.2 Stocker | ✅ | — | — | — | ✅ |
| C3.3 Procédures ETL | ✅ | — | — | — | ✅ |
| C3.4 Transformer | ✅ | — | — | — | ✅ |
| C3.5 Analyser | ✅ | — | — | — | ✅ |
| C3.6 Automatiser ETL | ✅ | — | — | — | ✅ |
| C3.7 Algo IA | ✅ | — | — | — | ✅ |
| C3.8 API | — | ✅ | — | — | ✅ |
| C3.9 Conteneuriser | — | ✅ | — | — | ✅ |
| C3.10 Déployer | — | ✅ | — | — | ✅ |
| C3.11 Orchestrer | — | ✅ | — | — | ✅ |
| C3.12 Contrôler MEP | — | ✅ | — | — | ✅ |
| C3.13 CI/CD + monitoring | — | ✅ | — | — | ✅ |
