# 06 — Roadmap & Planning

> **Ce document doit etre lu par TOUTES les equipes.**

---

## Planning global

| Mois | Sprint | Theme principal | Equipes impliquees |
|------|--------|----------------|-------------------|
| **Nov. 2025** | 1 | Infrastructure Docker, CI/CD | **DevOps** (lead), Data Eng |
| **Dec. 2025** | 2 | Collecte de donnees, APIs | **Data Eng** (lead), DevOps |
| | 3 | Schema BDD, MinIO | **Data Eng** (lead) |
| **Jan. 2026** | 4 | Pipeline ETL robuste | **Data Eng** (lead) |
| | 5 | Indicateurs techniques multi-TF | **Data Eng** (calcul), **ML** (definition) |
| **Fev-Mars 2026** | 6 | Regles multi-TF + ML + backtesting | **ML** (lead) |
| **Avr. 2026** | 7 | Dashboard Streamlit + API FastAPI | **Frontend** (lead), **Backend** (lead) |
| **Mai 2026** | 8 | Tests complets + CI/CD final | **Toutes** |
| | 9 | Deploy prod + securite | **DevOps** (lead), Backend |
| **Optionnel** | 10 | Alertes, chatbot avance | Frontend, Backend |

---

## Qui fait quoi par sprint

### Sprint 1 (Novembre) — Infrastructure

| Equipe | Taches |
|--------|--------|
| **DevOps** | docker-compose.yml, Dockerfiles, .env.example, Nginx (HTTP), GitHub Actions lint+test |
| **Data Eng** | Rien encore (attendre l'infra) |
| **ML** | Rien encore |
| **Backend** | Rien encore |
| **Frontend** | Rien encore |

### Sprint 2-3 (Decembre) — Donnees

| Equipe | Taches |
|--------|--------|
| **DevOps** | HTTPS, setup VPS, deploy auto, backups |
| **Data Eng** | Connecteurs Binance/CoinGecko/CCXT, schema TimescaleDB, MinIO buckets, APScheduler |
| **ML** | Rien encore (mais commencer a explorer les donnees en Jupyter) |
| **Backend** | Rien encore |
| **Frontend** | Rien encore |

### Sprint 4-5 (Janvier) — ETL + Indicateurs

| Equipe | Taches |
|--------|--------|
| **DevOps** | Support si besoin |
| **Data Eng** | Pipeline ETL robuste, validation, deduplication, scraping news, calcul indicateurs |
| **ML** | Definir la config des indicateurs (quels indicateurs, quels params, quels TF), exploration des donnees |
| **Backend** | Rien encore |
| **Frontend** | Rien encore |

### Sprint 6 (Fevrier-Mars) — ML

| Equipe | Taches |
|--------|--------|
| **DevOps** | Support si besoin |
| **Data Eng** | Export datasets vers MinIO, job d'evaluation signal_outcomes |
| **ML** | Regles multi-TF (Phase 1), ML supervise (Phase 2), backtesting, MLflow, DVC, NLP sentiment |
| **Backend** | Rien encore |
| **Frontend** | Rien encore |

### Sprint 7 (Avril) — Dashboard + API

| Equipe | Taches |
|--------|--------|
| **DevOps** | Support si besoin |
| **Data Eng** | Support requetes, optimisation |
| **ML** | Generation de signaux en temps reel, ajustements modeles |
| **Backend** | Tous les endpoints FastAPI, auth, chatbot service |
| **Frontend** | Toutes les pages Streamlit, graphiques Plotly, chatbot UI |

### Sprint 8-9 (Mai) — Tests + Deploy

| Equipe | Taches |
|--------|--------|
| **DevOps** | Deploy prod, monitoring, hardening |
| **Data Eng** | Tests unitaires + integration |
| **ML** | Tests modeles, evaluation finale |
| **Backend** | Tests unitaires + integration + fonctionnels |
| **Frontend** | Tests fonctionnels, polish UI |

### Sprint 10 (Optionnel) — Ameliorations

| Equipe | Taches |
|--------|--------|
| **Backend** | Alertes email/Telegram |
| **Frontend** | Chatbot ameliore, dark/light mode |
| **ML** | Optimisation continue des modeles |

---

## Regles inter-equipes

### Communication

1. **Ne touchez pas au code des autres equipes** — si vous avez besoin de quelque chose, demandez
2. **Models pydantic partages** dans `src/shared/models/` — toute modification doit etre communiquee a toutes les equipes
3. **Branches** : `{equipe}/{feature}` — ex: `data-eng/binance-collector`, `ml/rules-engine`, `backend/auth`, `frontend/dashboard`, `devops/ci-pipeline`
4. **PR obligatoire** pour merge sur `main` — au moins 1 review d'un membre d'une autre equipe

### Interfaces stables

| Interface | Owner | Consommateurs |
|-----------|-------|--------------|
| Schema BDD (Alembic migrations) | Data Eng | Tous |
| Models pydantic (`src/shared/`) | Data Eng (cree), Backend (enrichit) | Tous |
| Endpoints API REST | Backend | Frontend |
| Config indicateurs (`src/ml/config/`) | ML | Data Eng |
| `docker-compose.yml` | DevOps | Tous |
| `.env.example` | DevOps | Tous |

### Quand lever la main

- Si vous avez besoin d'une nouvelle table → parlez a **Data Eng**
- Si vous avez besoin d'un nouvel endpoint → parlez a **Backend**
- Si Docker ne marche pas → parlez a **DevOps**
- Si les donnees sont bizarres → parlez a **Data Eng**
- Si un indicateur manque → parlez a **ML** (definition) puis **Data Eng** (calcul)

---

## KPIs de succes

| Sprint | Critere de validation |
|--------|----------------------|
| 1 | `docker-compose up -d` lance tous les services sans erreur |
| 2-3 | 3+ sources collectent des donnees, TimescaleDB contient des OHLCV |
| 4-5 | ETL stable (>95% uptime), indicateurs calcules sur 5+ cryptos |
| 6 | Modele ML bat la baseline buy & hold en backtest |
| 7 | Dashboard fonctionnel, 3 personas peuvent naviguer |
| 8-9 | Tests > 80% couverture, deploy automatique sur VPS |
| Final | Demo fonctionnelle complete pour la soutenance |
