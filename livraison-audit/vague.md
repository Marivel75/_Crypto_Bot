# Plan d'execution par vagues — Crypto Bot Remediation & Features

**Date** : 2026-03-12
**Branche** : `roulio-mars`
**Statut** : Vague 2 COMPLETE — Vague 3 (QA) en execution

---

## Vague 1 — Phase 3 Remediation (~13h)

Objectif : Resoudre tous les findings d'audit restants (A1-A5, T4-T7, D6-D10, C3-C5, S9-S12).

### Agents paralleles (batch 1)

| Agent | Type ECC | Scope | Taches | Effort |
|-------|----------|-------|--------|--------|
| **arch-fixer** | `code` (sonnet) | `src/frontend/api_client.py`, `src/shared/`, `src/api/routers/` | A1: eliminer `type: ignore` dans api_client.py, A2: unifier ORM naming (orm.py → db_models.py), A3: ajouter `response_model` sur tous les endpoints | 3.5h |
| **ml-tester** | `python-ml` (sonnet) | `src/ml/`, `tests/ml/`, `tests/e2e/` | T4: unifier rule engine API (evaluate vs generate_signals), T5: fix data leakage backtester, T6: E2E signal generation test, T7: regression detection test | 3h |
| **infra-hardener** | `devops` (sonnet) | `docker-compose.yml`, `infra/`, `.github/` | D6: Grafana alerting rules, D7: GitHub Actions secrets docs, D8: remove obsolete version line, D9: nginx log persistence, D10: docker-compose.override.yml template | 3h |

### Agents sequentiels (batch 2, apres batch 1)

| Agent | Type ECC | Scope | Taches | Effort |
|-------|----------|-------|--------|--------|
| **doc-writer** | `code` (sonnet) | `docs/` | C3: guide migrations Alembic (07-database-migrations.md), C4: guide variables d'env (08-environment-variables.md), C5: doc rate limiting (09-rate-limiting.md) | 2h |
| **security-closer** | `code` (sonnet) | `src/api/middleware.py`, `.github/workflows/` | S9-S10: verifier headers nginx (deja fait), S11: CI check prefixe /api/v1/, S12: middleware rate limit headers (X-RateLimit-*) | 1h |

### Criteres de succes Vague 1

- [x] A1-A3 : architecture deja conforme (0 changements necessaires)
- [x] T4-T7 : 26 tests ML crees (commit `7cef935`)
- [x] D6-D10 : infra implementee (commit `b10c0f4`)
- [x] C3-C5 : 3 guides docs crees (30 KB total)
- [x] S11-S12 : middleware rate limit + versioning API (commit `e7b4bf0`)
- [x] Grafana : 8 regles d'alerte configurees
- [x] Nginx logs persistent
- [x] docker-compose.override.yml.example cree
- [x] Rate limit headers implementes (X-RateLimit-*)

---

## Vague 2 — Feature Implementation (133 RF)

Objectif : Implementer les fonctionnalites metier definies dans le CDC (133 RF + 12 RNF).

### Semaine 2 : Fondations (ETL + Infra)

| Agent | Type ECC | Scope | RF couverts | Effort |
|-------|----------|-------|-------------|--------|
| **etl-builder** | `code` + `python-ml` | `src/etl/`, `src/shared/` | 16 RF : collecteurs Binance REST/WS, CoinGecko, CCXT fallback, APScheduler jobs, deduplication OHLCV, gap detection, MinIO storage, news RSS, Fear&Greed Index | ~8h |
| **infra-deployer** | `devops` | `infra/`, `docker-compose.yml`, `.github/` | Docker Compose topology complete, Ansible VPS provisioning, CI/CD GitHub Actions (lint/test/build/deploy), Nginx HTTPS, monitoring stack | ~6h |

### Semaine 3 : API + ML (en parallele)

| Agent | Type ECC | Scope | RF couverts | Effort |
|-------|----------|-------|-------------|--------|
| **api-builder** | `code` | `src/api/` | 26 RF : auth JWT (register/login/refresh), CRUD portfolio, CRUD watchlist, signals endpoint (filtres, pagination), news aggregation, chat endpoint, system health, OpenAPI docs | ~10h |
| **ml-engine** | `python-ml` + `crypto` | `src/ml/` | 23 RF + 3 analytics : RSI multi-TF convergence, Bollinger squeeze, harmonics (bat/gartley/butterfly/crab), trend lines, config YAML, XGBoost/LightGBM phase 2, walk-forward backtesting, MLflow tracking, DVC versioning | ~10h |

### Semaine 4 : Frontend

| Agent | Type ECC | Scope | RF couverts | Effort |
|-------|----------|-------|-------------|--------|
| **frontend-builder** | `code` | `src/frontend/` | 53 RF : 5 pages Streamlit — Dashboard/Noah (bougies, indicateurs, signaux), Veille/Sarah (news, sentiment, alertes), Portfolio/Aleksandar (suivi, chatbot), Analytics (heatmap, correlations), Performance (historique signaux, metriques). Plotly charts, api_client, dark theme | ~12h |

### Criteres de succes Vague 2

- [x] 16 RF ETL implementes et testes (commits `c80a283`, `460aa0c`, `00542a7`)
- [x] Infra deployer : Docker Compose, Ansible, CI/CD, Nginx, monitoring (commit `c80a283`)
- [x] 26 RF API implementes avec tests d'integration (commit `f37225c`)
- [x] 23 RF ML + backtesting fonctionnel (commit `da839b6`)
- [x] 53 RF Frontend : 5 pages navigables (commit `d223673`)
- [ ] Docker Compose : tous les services demarrent proprement
- [ ] CI/CD : pipeline complet (lint → test → build → deploy)
- [ ] Coverage >= 80% par module

---

## Vague 3 — Validation & QA

Objectif : Revue globale, tests de bout en bout, validation securite.

| Agent | Type ECC | Tache | Effort |
|-------|----------|-------|--------|
| **qa-reviewer** | `code-reviewer` + `security-reviewer` | Review code complet, OWASP Top 10, team boundary violations, Pydantic boundaries | 2h |
| **test-runner** | `python-ml` | pytest full suite, mypy --strict, ruff check, E2E stack complet (ETL → ML → API → Frontend) | 2h |
| **db-reviewer** | `database-reviewer` | Schema TimescaleDB, indexes FK, hypertables, compression policies, retention policies, query performance | 1h |

### Criteres de succes Vague 3

- [ ] 0 vulnerabilites CRITICAL/HIGH
- [ ] Coverage globale >= 80%
- [ ] mypy --strict : 0 erreurs
- [ ] E2E : signal generation pipeline end-to-end passe
- [ ] Tous les services Docker healthy
- [ ] Documentation complete (7+ guides)

---

## Scores d'audit attendus

| Categorie | Avant | Apres Vague 1 | Apres Vague 2+3 |
|-----------|-------|---------------|-----------------|
| Architecture | B- | A- | A |
| Securite | B+ | A- | A |
| DevOps | A- | A | A+ |
| Testing | B- | A- | A |
| Documentation | 90% | 95% | 98% |
| **Global** | **B+** | **A-** | **A** |

---

## Dependances entre vagues

```
Vague 1 (remediation)
  └─→ Vague 2 (features)
        ├─ ETL + Infra (fondations, semaine 2)
        │   └─→ API + ML (semaine 3, dependant des donnees ETL)
        │         └─→ Frontend (semaine 4, dependant de l'API)
        └─→ Vague 3 (QA, apres toutes les features)
```

---

## Commandes de lancement

```bash
# Vague 1 — batch 1 (parallele)
# arch-fixer:     Agent code → A1, A2, A3
# ml-tester:      Agent python-ml → T4, T5, T6, T7
# infra-hardener: Agent devops → D6, D7, D8, D9, D10

# Vague 1 — batch 2 (sequentiel)
# doc-writer:     Agent code → C3, C4, C5
# security-closer: Agent code → S11, S12
```

---

*En attente du GO pour lancer la Vague 1.*
