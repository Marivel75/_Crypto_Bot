# Spécification CDC — Infrastructure & Architecture Données

## Vue d'ensemble

Ce dossier contient la spécification complète du Cahier des Charges (CDC) pour l'infrastructure et l'architecture des données du projet Crypto Bot.

### Fichiers

- **`01-requirements.md`** (1173 lignes) — Spécification exhaustive couvrant :
  - Architecture Infrastructure (Docker Compose, réseaux, services)
  - Architecture Données (TimescaleDB hypertables, MinIO buckets, flux)
  - 25 Exigences Fonctionnelles Infrastructure (RF-INFRA-001 à RF-INFRA-025)
  - 16 Exigences Fonctionnelles Données (RF-DATA-001 à RF-DATA-016)
  - Plan de remédiation des 8 issues critiques audit
  - Matrice de traçabilité Audit → Exigences
  - Plan d'implémentation Phase 1-3

## Périmètre & Responsabilités

### Infrastructure (Architect 3)

- **Docker Compose** : Services, volumes, networks, health checks, resource limits
- **Nginx** : Reverse proxy, TLS/HTTPS, rate limiting, security headers
- **CI/CD** : GitHub Actions pipeline (lint → test → build → deploy)
- **Ansible** : VPS provisioning, deployments, rollback, backups
- **Monitoring** : Prometheus, Grafana, alertes

### Architecture Données (Architect 1)

- **TimescaleDB** : Hypertables OHLCV, compression, retention, indexes, migrations Alembic
- **MinIO** : Buckets S3-compatibles, structure, lifecycle rules, versioning
- **Indicateurs** : RSI, Bollinger Bands, harmonic patterns, trend lines
- **Qualité** : Validation Pydantic, deduplication, reconciliation gaps

## Exigences Critiques (Audit 2026-03-12)

### Phase 1 (Bloquants) — Semaine 1

| # | Issue | Effort | Status |
|---|-------|--------|--------|
| S1 | Secrets hardcodés `config.py` | 30 min | À faire |
| S2 | MLflow credentials exposées | 20 min | À faire |
| S3 | MinIO defaults insécures | 45 min | À faire |
| D1 | Images Docker unpinnées | 30 min | À faire |
| D2 | Ansible `delete: true` destructif | 15 min | À faire |
| T1 | Code ML exclu couverture | 1h | À faire |
| T2 | WalkForwardBacktester non testé | 15 min | À faire |
| T3 | Test E2E pipeline absent | 2h | À faire |

**Effort total Phase 1 :** ~5h

### Phase 2 (Avant Production) — Semaine 2-3

- HTTPS/TLS Let's Encrypt (1h)
- Playbook rollback (2h)
- Backup MinIO (1h)
- Migrations Alembic finalisées (2h)
- Runbook production (2h)

**Effort total Phase 2 :** ~8h

### Phase 3 (Optionnel) — Semaine 4+

- Alertes Grafana (1h)
- Harmonic patterns (2h)
- Trend lines (1h)
- Reconciliation job (1h)
- DVC datasets (1h)

**Effort total Phase 3 :** ~6h

## Contenu Détaillé 01-requirements.md

### Section 1 — Architecture Infrastructure

- **1.1** : Topologie ASCII Docker Compose (9 services + exporters)
- **1.2** : Réseaux Docker segmentés (frontend-net vs backend-net)
- **1.3** : Services avec images, ports, health checks, resource limits
- **1.4** : Volumes nommés (4 volumes persistants)
- **1.5** : Policies redémarrage

### Section 2 — Architecture Données

- **2.1** : Schéma TimescaleDB complet (6 tables + hypertable)
  - `crypto_prices` : OHLCV partitionnée, compression 7j, retention 90j
  - `indicators` : RSI, Bollinger, harmonic patterns, trend lines
  - `trading_signals` : Signaux BUY/SELL/HOLD avec metadata
  - `signal_outcomes` : Évaluation a posteriori rendements
  - `users` : Auth + watchlist + preferences
  - `news_articles` : Sentiment, keywords, reliability

- **2.2** : MinIO structure (buckets raw, datasets, models, mlflow-artifacts, backups)
- **2.3** : Flux données global (ETL → TimescaleDB → ML → API)
- **2.4** : Compression & retention policies

### Section 3 — Exigences Fonctionnelles Infrastructure (25 RFs)

#### Docker (RF-INFRA-001 à 010)
- RF-INFRA-001 : Images pinnées (CRITICAL, audit D1)
- RF-INFRA-002 : Multi-stage Dockerfiles
- RF-INFRA-003 : Health checks tous services
- RF-INFRA-004 : Resource limits (mem)
- RF-INFRA-005 : Volumes nommés uniquement
- RF-INFRA-006 : Réseaux segmentés
- RF-INFRA-007 : Dependencies avec health checks
- RF-INFRA-008 : Restart policy
- RF-INFRA-009 : .dockerignore
- RF-INFRA-010 : Ports localhost

#### Nginx & TLS (RF-INFRA-011 à 015)
- RF-INFRA-011 : Reverse proxy API + Frontend
- RF-INFRA-012 : Rate limiting (30 req/s API, 5 req/min auth)
- RF-INFRA-013 : Headers sécurité
- RF-INFRA-014 : HTTPS/TLS Let's Encrypt (CRITICAL, audit S6)
- RF-INFRA-015 : CORS restrictif

#### CI/CD (RF-INFRA-016 à 020)
- RF-INFRA-016 : Pipeline GitHub Actions (lint → test → build → deploy)
- RF-INFRA-017 : Secrets GitHub (VPS_IP, SSH_KEY)
- RF-INFRA-018 : Coverage gate 80%
- RF-INFRA-019 : Artifacts CI
- RF-INFRA-020 : Branch protection main

#### Ansible (RF-INFRA-021 à 025)
- RF-INFRA-021 : Playbook provision VPS
- RF-INFRA-022 : Playbook deploy application
- RF-INFRA-023 : Stratégie rollback (CRITICAL, audit D3)
- RF-INFRA-024 : Monitoring Prometheus + Grafana
- RF-INFRA-025 : Backups TimescaleDB + MinIO (CRITICAL)

### Section 4 — Exigences Fonctionnelles Données (16 RFs)

#### TimescaleDB (RF-DATA-001 à 005)
- RF-DATA-001 : Hypertable `crypto_prices`
- RF-DATA-002 : Compression automatique (7j)
- RF-DATA-003 : Retention policy (90j)
- RF-DATA-004 : Indexes appropriés
- RF-DATA-005 : Migrations Alembic versionnées

#### Indicateurs (RF-DATA-006 à 010)
- RF-DATA-006 : Table `indicators`
- RF-DATA-007 : RSI multi-timeframe (1h, 2h, 4h, 1D, 1W)
- RF-DATA-008 : Bollinger Bands squeeze
- RF-DATA-009 : Harmonic patterns (Gartley, Butterfly, Crab, Bat)
- RF-DATA-010 : Trend lines + support/resistance

#### MinIO (RF-DATA-011 à 013)
- RF-DATA-011 : Structure MinIO organisée
- RF-DATA-012 : Lifecycle rules (expiration auto)
- RF-DATA-013 : Versioning datasets ML

#### Qualité (RF-DATA-014 à 016)
- RF-DATA-014 : Validation Pydantic
- RF-DATA-015 : Deduplication OHLCV
- RF-DATA-016 : Reconciliation gaps horaire

### Section 5 — Remédiation Audit

Mapping direct des 8 issues critiques audit vers exigences :

| Audit | Sévérité | Remédiation | Phase |
|-------|----------|-----------|-------|
| S1 | CRITICAL | RF-INFRA-001 + .env | P1 |
| S2 | CRITICAL | RF-INFRA-022 + MLflow env vars | P1 |
| S3 | CRITICAL | RF-INFRA-022 + MinIO validation | P1 |
| D1 | CRITICAL | RF-INFRA-001 + Docker pinning | P1 |
| D2 | CRITICAL | RF-INFRA-022 + Ansible fixes | P1 |
| D5 | HIGH | RF-INFRA-025 + RF-DATA-011 | P2 |
| C1 | HIGH | RF-INFRA-022 + Runbook | P2 |
| C2 | HIGH | RF-DATA-001 + pg16 harmony | P2 |

### Section 6 — Matrice de Traçabilité

Table audit → RF mappings, composantes infra vs données.

### Section 7 — Plan d'Implémentation

**Phase 1** (Bloquants, 1 semaine) :
- Secrets sécurité (S1-S3)
- Images pinnées (D1)
- Ansible sûr (D2)
- Tests couverts (T1-T3)

**Phase 2** (Avant prod, 2-3 semaines) :
- HTTPS (S6)
- Backups (D5)
- Rollback (D3)
- Runbook (C1)

**Phase 3** (Optionnel) :
- Monitoring avancé
- Indicateurs avancés
- Optimisations

## Annexes

- **Annexe A** : `.env.example` complet avec descriptions
- **Annexe B** : Checklist déploiement production (20 items)
- **Annexe C** : Références fichiers (12 fichiers clés)

## Utilisation

1. Lire cette section README en entier (~5 min)
2. Naviguer vers `01-requirements.md` pour détails spécifiques
3. Chercher par :
   - **RF-INFRA-XXX** pour requirements infrastructure
   - **RF-DATA-XXX** pour requirements données
   - **Audit SX**, **DX**, **CX** pour remédiation audit
4. Implémenter par phase (P1 → P2 → P3)

## Livrables Attendus

- [ ] Phase 1 (P1) : Secrets sécurisés + images pinnées + tests 80%
- [ ] Phase 2 (P2) : HTTPS active + backups operationnels + runbook
- [ ] Phase 3 (P3) : Monitoring + indicateurs + optimisations

## Notes Importantes

- **Produit par :** Architecte Infrastructure + Architecte Données (2026-03-12)
- **Basé sur :** Audit complet 5 agents spécialisés
- **Applicable immédiatement** après remédiation P1-P2
- **Lien audit :** `/home/jules/Documents/3-git/DTSC/amau/cryptobot/audit.md`
- **Commandes utiles :**
  ```bash
  docker compose up -d
  docker compose logs -f api
  ansible-playbook -i infra/ansible/inventories/production.ini infra/ansible/playbooks/provision.yml
  ```

---

**Spécification v2.1 — Prête pour implémentation**
