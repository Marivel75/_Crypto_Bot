# System Architecture: CryptoBot — Phase 2

**Date:** 2026-03-15
**Architect:** Jules Willard (BMAD System Architect)
**Version:** 1.0
**Project Type:** web-app
**Project Level:** 3 (Complex — 8 features, ~25 stories)
**Status:** Draft — En attente validation Gate #2

---

## Document Overview

Architecture technique pour les 8 features manquantes (33% du cadrage).
Etend l'architecture existante (FastAPI + Streamlit + TimescaleDB + Docker Compose).

**Documents associes:**
- PRD: `docs/specs/PRD-phase2.md` (100/100)
- Cadrage: `Crypto_bot_cadrage_V2.pdf`

---

## Architectural Drivers

| Priorite | Driver | Exigence | Solution |
|----------|--------|----------|----------|
| **P0** | Scalabilite sources | Ajouter des sources sans refactor | Pattern BaseCollector generique |
| **P0** | Rate limits APIs | Binance 1200/min, Etherscan 5/sec, Mempool 10/min | Backoff exponentiel + fallback chain |
| **P1** | Latence alertes | < 5 min entre evenement et notification | Worker async APScheduler dedie |
| **P1** | Performance API | < 200ms p95 | PostgreSQL natif (indexes, materialized views) |
| **P2** | Isolation ML | Training LSTM/RL ne bloque pas l'API | Workers Docker separes |
| **P2** | Fiabilite paper trading | Zero erreur P&L | Tests 100% coverage + audit trail |

**Decision cle : pas de Redis.** PostgreSQL 16+ gere la performance nativement (partial indexes, BRIN indexes sur hypertables, connection pooling).

---

## System Overview

### Architectural Pattern

**Pattern:** Monolithe modulaire + Workers Docker isoles

**Rationale:** L'architecture existante est un monolithe modulaire (src/etl, src/ml, src/api, src/frontend, src/shared) avec Docker Compose. On etend ce pattern sans le casser. Les workers ML (LSTM training, RL training) sont des containers Docker separes pour ne pas bloquer l'API.

### High-Level Architecture

```
┌─────────────────── Sources Externes ────────────────────┐
│ Binance  CoinGecko  CCXT  RSS  Mempool  Etherscan  ESMA│
│ (exist)  (exist)  (exist) (exist) (NEW)   (NEW)    (NEW)│
└────────────────────────┬────────────────────────────────┘
                         │
         ┌───────────────▼───────────────┐
         │     ETL Worker (APScheduler)  │
         │   10 jobs existants           │
         │   + 4 nouveaux collectors     │
         │   + 2 scrapers BeautifulSoup  │
         └───────────┬──────┬────────────┘
                     │      │
          ┌──────────▼──┐ ┌─▼──────────┐
          │ TimescaleDB │ │  MinIO S3  │
          │ 9+6 tables  │ │  Models    │
          └──┬──────────┘ └────────────┘
             │
    ┌────────┼────────────────────────┐
    │        │                        │
    ▼        ▼                        ▼
┌────────┐ ┌──────────────────┐ ┌─────────────┐
│FastAPI │ │  ML Worker       │ │Alert Worker │
│8+4     │ │  (Docker separe) │ │(APScheduler)│
│routers │ │  LSTM train/pred │ │Email+Tg+App │
│        │ │  RL train        │ │             │
│        │ │  Clustering      │ │             │
└───┬────┘ └──────────────────┘ └─────────────┘
    │
    ▼
┌──────────┐
│Streamlit │
│5+1 pages │
│(Paper    │
│ Trading) │
└──────────┘
```

---

## Technology Stack

### Stack existant (inchange)

| Couche | Technologie | Rationale |
|--------|-------------|-----------|
| Frontend | Streamlit + Plotly | Rapide, natif Python, dark theme |
| Backend | FastAPI + Uvicorn | Async natif, OpenAPI auto |
| Database | TimescaleDB (PostgreSQL 16) | Hypertables, compression, JSONB |
| Object Storage | MinIO | S3-compatible, models + datasets |
| ML Tracking | MLflow | Experiment tracking, model registry |
| Containers | Docker Compose | 12 services, health checks |
| Reverse Proxy | Nginx | SSL, rate limiting, routing |
| CI/CD | GitHub Actions | Lint → Test → Build → Deploy |
| Monitoring | Prometheus + Grafana | Metriques API, DB, systeme |

### Nouvelles dependances Phase 2

| Composant | Technologie | Pourquoi |
|-----------|-------------|----------|
| Deep Learning | TensorFlow 2.13+ | LSTM, Keras API simple, SavedModel |
| RL | Numpy + custom Q-table | Pas besoin de gym/stable-baselines pour Q-learning tabulaire |
| Clustering | scikit-learn KMeans | Deja dans les deps, stable |
| Scraping | BeautifulSoup4 + httpx | Cadrage l'exige explicitement |
| Alertes email | smtplib (stdlib) | Zero dependance externe |
| Alertes Telegram | httpx (deja present) | Telegram Bot API = HTTP POST |
| On-chain | httpx (deja present) | APIs REST standard |

### Decision : pas de nouveaux frameworks lourds

Pas de : Redis, Celery, RabbitMQ, Kubernetes, gym, stable-baselines.
PostgreSQL LISTEN/NOTIFY remplace un broker de messages pour les alertes.

---

## System Components (nouveaux)

### C1. Paper Trading Engine

**Scope:** `src/api/services/paper_trading_service.py` + `src/api/routers/paper_trading.py`

**Responsabilites:**
- CRUD comptes paper trading (solde initial configurable)
- Execution ordres BUY/SELL (market, limit)
- Calcul P&L avec frais Hyperliquid (0.04% taker defaut + funding rate)
- Auto-close positions sur SL/TP (job ETL toutes les heures)
- Journal de trades complet

**Interfaces:**
- REST API `/api/v1/paper-trading/*`
- Consomme: `crypto_prices` (prix courant), `trading_signals` (source des trades)

**FRs:** F1 (Stories 1.1, 1.2, 1.3)

---

### C2. RL Pipeline

**Scope:** `src/ml/rl/`

**Responsabilites:**
- State encoder (discretisation features → buckets)
- Agent SARSA + Q-Learning (Q-table en DB)
- Reward calculator (neutre pour HOLD)
- Experience buffer (stockage transitions)
- Trainer batch (retraining hebdomadaire)

**Interfaces:**
- Consomme: `indicators`, `paper_trades` (reward signal), `market_regime`
- Produit: Q-value adjustments sur `trading_signals.confidence`

**FRs:** F2 (Stories 2.1, 2.2)

---

### C3. LSTM Pipeline

**Scope:** `src/ml/lstm/`

**Responsabilites:**
- Data pipeline (sequences 60-step, normalisation MinMax)
- 3 modeles TensorFlow (4h, 1d, 1w)
- Trainer avec walk-forward temporal
- Predictor (inference < 10ms, cache memoire)
- Ensemble voting (2/3 consensus)

**Interfaces:**
- Consomme: `crypto_prices`, `indicators`
- Produit: predictions direction UP/DOWN + confidence
- Models stockes dans MinIO (`models/lstm/`)

**Isolation:** Docker container `ml-lstm-worker` separe de l'API

**FRs:** F3 (Stories 3.1, 3.2)

---

### C4. Clustering Pipeline

**Scope:** `src/ml/clustering/`

**Responsabilites:**
- Global regime (K-Means k=3 : BEAR/SIDEWAYS/BULL)
- Per-coin clustering (K-Means k=4 : blue-chip/smart-contract/high-vol/emerging)
- Feature engineering depuis TimescaleDB
- Mise a jour : regime quotidien, coins hebdomadaire

**Interfaces:**
- Consomme: `crypto_prices`, `indicators`, `fear_greed`, on-chain data
- Produit: `market_regime` table, `coin_clusters` table
- Alimente: RL state space (regime), signal confidence boost

**FRs:** F4 (Stories 4.1, 4.2)

---

### C5. On-Chain Collectors

**Scope:** `src/etl/collectors/onchain/`

**Responsabilites:**
- Mempool.space collector (BTC mempool, fees, whale tx)
- Blockchain.com collector (fallback: hashrate, difficulty)
- Etherscan collector (ETH gas, active addresses)
- Fallback chain automatique si une API tombe
- Detection accumulation/distribution

**Interfaces:**
- Produit: `onchain_metrics` table
- Rate limits: respectes avec backoff exponentiel

**FRs:** F5 (Stories 5.1, 5.2)

---

### C6. Alert System

**Scope:** `src/api/services/alert_service.py` + `src/etl/jobs/alert_worker.py`

**Responsabilites:**
- Dispatch alertes individuelles (pas de batching)
- 3 canaux : email SMTP, Telegram Bot API, in-app Streamlit
- Regles d'alertes configurables par user (seuils, symboles, types)
- Queue interne via PostgreSQL `LISTEN/NOTIFY` (pas de broker)

**Interfaces:**
- Consomme: `trading_signals`, `news_articles`, `market_regime`, `onchain_metrics`
- Produit: `alert_history` table
- Latence cible: < 5 min

**FRs:** F6 (Stories 6.1, 6.2)

---

### C7. Regulatory Collectors + Scrapers

**Scope:** `src/etl/collectors/regulatory/` + `src/etl/collectors/scraper.py`

**Responsabilites:**
- ESMA RSS feed collector
- SEC RSS feed collector (crypto task force)
- EU Blockchain Observatory RSS
- Phoenix News scraper (BeautifulSoup)
- Integration dans `news_articles` table avec `source_type = 'regulatory'`

**Interfaces:**
- Produit: `news_articles` avec tag reglementaire
- Maintenance: selecteurs CSS dans le code, fix quand ca casse

**FRs:** F7 (Stories 7.1), F8

---

## Data Architecture

### Nouvelles tables (6 tables)

```sql
-- F1: Paper Trading
CREATE TABLE paper_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    account_name VARCHAR(100) NOT NULL DEFAULT 'Default',
    initial_balance NUMERIC(20,8) NOT NULL DEFAULT 10000,
    current_balance NUMERIC(20,8) NOT NULL DEFAULT 10000,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, account_name)
);

CREATE TABLE paper_trades (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID NOT NULL REFERENCES paper_accounts(id),
    signal_id UUID REFERENCES trading_signals(id),
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(5) NOT NULL CHECK (side IN ('LONG','SHORT')),
    quantity NUMERIC(20,8) NOT NULL CHECK (quantity > 0),
    entry_price NUMERIC(20,8) NOT NULL,
    exit_price NUMERIC(20,8),
    stop_loss NUMERIC(20,8),
    take_profit NUMERIC(20,8),
    entry_fee NUMERIC(20,8) NOT NULL DEFAULT 0,
    exit_fee NUMERIC(20,8) DEFAULT 0,
    funding_cost NUMERIC(20,8) DEFAULT 0,
    realized_pnl NUMERIC(20,8),
    status VARCHAR(10) NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN','CLOSED','LIQUIDATED')),
    opened_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    closed_at TIMESTAMPTZ
);
CREATE INDEX idx_paper_trades_account ON paper_trades(account_id);
CREATE INDEX idx_paper_trades_status ON paper_trades(status);

-- F2: RL
CREATE TABLE rl_q_table (
    state_hash VARCHAR(64) NOT NULL,
    action INT NOT NULL CHECK (action BETWEEN 0 AND 5),
    q_value NUMERIC(10,6) NOT NULL DEFAULT 0,
    visits INT NOT NULL DEFAULT 0,
    last_update TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (state_hash, action)
);

-- F4: Clustering
CREATE TABLE market_regime (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    regime VARCHAR(10) NOT NULL CHECK (regime IN ('BEAR','SIDEWAYS','BULL')),
    confidence NUMERIC(4,3) NOT NULL,
    computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE coin_clusters (
    symbol VARCHAR(20) NOT NULL,
    cluster_id INT NOT NULL,
    cluster_name VARCHAR(30) NOT NULL,
    confidence NUMERIC(4,3) NOT NULL,
    computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (symbol, computed_at)
);

-- F5: On-chain
CREATE TABLE onchain_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol VARCHAR(10) NOT NULL,
    metric_name VARCHAR(50) NOT NULL,
    metric_value NUMERIC(20,8) NOT NULL,
    source VARCHAR(30) NOT NULL,
    collected_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_onchain_symbol_time ON onchain_metrics(symbol, collected_at DESC);

-- F6: Alertes
CREATE TABLE alert_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    alert_type VARCHAR(30) NOT NULL,
    channel VARCHAR(15) NOT NULL CHECK (channel IN ('email','telegram','inapp')),
    config JSONB NOT NULL DEFAULT '{}',
    enabled BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE alert_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_id UUID REFERENCES alert_rules(id),
    user_id UUID NOT NULL REFERENCES users(id),
    channel VARCHAR(15) NOT NULL,
    subject VARCHAR(200) NOT NULL,
    body TEXT NOT NULL,
    sent_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    delivered BOOLEAN NOT NULL DEFAULT false
);
CREATE INDEX idx_alert_history_user ON alert_history(user_id, sent_at DESC);
```

### Data Flow (nouvelles features)

```
Mempool/Etherscan/Blockchain.com
    → onchain_metrics (every 10min)
    → coin_clusters + market_regime (daily/weekly)

ESMA/SEC/PhoenixNews RSS+Scraping
    → news_articles (source_type='regulatory', every 15min)

Signal Generator (enrichi)
    → trading_signals (confidence ajustee par RL Q-values + LSTM + regime boost)

Paper Trading
    → paper_trades (user action) → rl_q_table (reward feedback)

Alert Worker (every 1min)
    → scan: new signals, new regulatory news, SL/TP triggers
    → alert_history → dispatch email/telegram/inapp
```

---

## API Design (nouveaux endpoints)

### Paper Trading (`/api/v1/paper-trading/`)
```
POST   /accounts                    → Creer compte paper (solde initial)
GET    /accounts                    → Lister comptes user
POST   /orders                      → Executer ordre BUY/SELL
GET    /trades                      → Historique trades (pagine, filtrable)
PUT    /trades/{id}/close           → Fermer position manuellement
GET    /portfolio                   → Stats aggregees (balance, P&L, win rate)
```

### ML Endpoints (`/api/v1/ml/`)
```
GET    /regime                      → Regime marche actuel (BEAR/SIDEWAYS/BULL)
GET    /clusters                    → Clusters coins (blue-chip, high-vol...)
GET    /lstm/{symbol}/prediction    → Prediction LSTM (4h/1d/1w + ensemble)
GET    /rl/status                   → Stats Q-table (convergence, coverage)
```

### On-Chain (`/api/v1/onchain/`)
```
GET    /metrics/{symbol}            → Metriques on-chain (whale tx, flows)
GET    /flow-signal/{symbol}        → Phase accumulation/distribution
```

### Alertes (`/api/v1/alerts/`)
```
GET    /rules                       → Regles alertes user
POST   /rules                       → Creer regle alerte
PUT    /rules/{id}                  → Modifier regle
DELETE /rules/{id}                  → Supprimer regle
GET    /history                     → Historique alertes envoyees
POST   /test                        → Envoyer alerte test
```

### Auth existante
Tous les nouveaux endpoints : `@Depends(get_current_user)` (JWT Bearer)

---

## NFR Coverage

### NFR-001: Scalabilite Sources

**Exigence:** Ajouter des sources sans refactor du pipeline ETL

**Solution:**
- Abstract class `BaseCollector` avec interface commune : `collect() → list[CollectedRecord]`
- Tous les collectors (existants + nouveaux) heritent de `BaseCollector`
- Registration dans `jobs.py` via config (pas de hardcoding)
- Chaque collector gere son propre rate limiting et retry

**Validation:** Ajouter un collector en < 50 lignes de code

---

### NFR-002: Rate Limits APIs

**Exigence:** Respecter les rate limits sans perte de donnees

**Solution:**
- `RateLimiter` class dans `src/shared/utils.py` (token bucket)
- Backoff exponentiel avec jitter (base=1s, max=60s, factor=2)
- Fallback chain configurable : Mempool → Blockchain.com → skip
- Metriques : compteur de rate limit hits dans Prometheus

**Validation:** Zero HTTP 429 en production sur 24h

---

### NFR-003: Latence Alertes < 5 min

**Exigence:** Max 5 minutes entre evenement et reception notification

**Solution:**
- Alert Worker dans le job APScheduler (scan toutes les 60 secondes)
- PostgreSQL `LISTEN/NOTIFY` pour les evenements critiques (nouveau signal confidence > 0.8)
- Dispatch async : email via smtplib, Telegram via httpx POST
- Pas de queue externe (PostgreSQL suffit pour le volume)

**Validation:** Timer dans alert_history (sent_at - event_at < 5min)

---

### NFR-004: Performance API < 200ms

**Exigence:** p95 response time < 200ms

**Solution:**
- PostgreSQL : indexes partiels sur `status='OPEN'`, BRIN sur timestamps
- Materialized view `mv_portfolio_stats` refresh toutes les 5 min
- Connection pooling asyncpg (pool_size=20)
- Pas de Redis — PostgreSQL 16 gere seul

**Validation:** Prometheus histogram p95 < 200ms

---

### NFR-005: Isolation ML Training

**Exigence:** Training LSTM/RL ne bloque pas l'API

**Solution:**
- Container Docker `ml-training-worker` separe
- Training declenche par APScheduler (LSTM weekly, RL weekly, clustering daily)
- Models sauves dans MinIO, charges par l'API au demarrage + hot-reload
- API sert les predictions depuis un cache memoire (modeles pre-charges)

**Validation:** API response time inchange pendant training (benchmark)

---

### NFR-006: Fiabilite Paper Trading

**Exigence:** Zero erreur calcul P&L et liquidation

**Solution:**
- Pessimistic locking (`SELECT FOR UPDATE`) sur paper_accounts lors d'un trade
- Audit trail : chaque modification = new row dans paper_trades
- Calcul P&L : formule Hyperliquid documentee et testee unitairement
- Tests : 50+ scenarios edge (liquidation, funding negatif, position nulle)

**Validation:** 100% test coverage sur paper_trading_service.py

---

## Security Architecture

### Authentication
- JWT HS256 existant (bcrypt + python-jose), inchange
- Nouveaux endpoints protege par `@Depends(get_current_user)`
- Token Telegram Bot : stocke dans `.env` uniquement

### Authorization
- Paper trading : user_id scoped (un user ne voit que ses trades)
- Alert rules : user_id scoped
- ML endpoints : publics (pas de donnees sensibles)

### Donnees sensibles
- Email SMTP credentials dans `.env`
- Telegram bot token dans `.env`
- Etherscan API key dans `.env` (free tier)
- Jamais en dur dans le code (ruff S105/S106 l'empeche)

---

## Docker Services (3 nouveaux)

```yaml
# docker-compose.yml additions

ml-training-worker:
  build: src/ml/Dockerfile
  command: python -m src.ml.training_scheduler
  depends_on:
    timescaledb: { condition: service_healthy }
    minio: { condition: service_healthy }
  environment:
    - DATABASE_URL=${DATABASE_URL}
    - MLFLOW_TRACKING_URI=${MLFLOW_TRACKING_URI}
  deploy:
    resources:
      limits: { memory: 2G }  # LSTM training needs RAM

alert-worker:
  build: src/etl/Dockerfile
  command: python -m src.etl.alert_worker
  depends_on:
    timescaledb: { condition: service_healthy }
  environment:
    - DATABASE_URL=${DATABASE_URL}
    - SMTP_HOST=${SMTP_HOST}
    - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}

# onchain-collector integre dans etl-worker (pas de service separe)
```

---

## Code Organization (nouveaux modules)

```
src/
  etl/
    collectors/
      onchain/
        mempool.py          # Mempool.space collector
        blockchain_com.py   # Fallback collector
        etherscan.py        # ETH on-chain
      regulatory/
        esma.py             # ESMA RSS
        sec.py              # SEC RSS
        phoenix_news.py     # BeautifulSoup scraper
      base_collector.py     # Abstract class (NEW)
    alert_worker.py         # Alert dispatch service (NEW)

  ml/
    rl/
      agent.py              # SARSA + Q-Learning
      state_encoder.py      # Feature discretization
      reward_calculator.py  # Neutral reward
      trainer.py            # Batch retraining
    lstm/
      model.py              # TensorFlow 2-layer LSTM
      data_pipeline.py      # Sequence creation
      trainer.py            # Walk-forward training
      predictor.py          # Inference + cache
      ensemble.py           # 3-model voting
    clustering/
      global_regime.py      # K-Means k=3
      coin_clustering.py    # K-Means k=4
    training_scheduler.py   # APScheduler pour ML (NEW)

  api/
    routers/
      paper_trading.py      # CRUD paper trades
      ml_endpoints.py       # Regime, clusters, LSTM predictions
      onchain.py            # On-chain metrics
      alerts.py             # Alert rules CRUD
    services/
      paper_trading_service.py
      alert_service.py
      onchain_service.py

  shared/
    models/
      paper_trading.py      # Pydantic models
      alerts.py             # Alert models
      onchain.py            # On-chain models
      clustering.py         # Regime/cluster models
    utils.py                # + RateLimiter, BaseCollector
```

---

## Testing Strategy

| Couche | Scope | Coverage cible |
|--------|-------|----------------|
| Unit | P&L calculation, Q-update, state encoding, sequence creation | 100% |
| Unit | Alert dispatch, regime detection, collector parsing | 90% |
| Integration | Paper trading flow (order → P&L → close) | 100% |
| Integration | Alert dispatch (email mock, Telegram mock) | 90% |
| Integration | LSTM train → predict → ensemble | 80% |
| E2E | Signal → paper trade → P&L → alert | 1 scenario |

**Mocks obligatoires:** Mempool API, Etherscan API, SMTP server, Telegram Bot API
**Pas de mocks:** TimescaleDB (utiliser Docker test container)

---

## Requirements Traceability

| Feature | Components | Tables | Endpoints | Owner |
|---------|------------|--------|-----------|-------|
| F1 Paper Trading | C1 | paper_accounts, paper_trades | 6 endpoints | Jules |
| F2 RL | C2 | rl_q_table | 3 endpoints | Mikael |
| F3 LSTM | C3 | (MinIO models) | 4 endpoints | Mikael |
| F4 Clustering | C4 | market_regime, coin_clusters | 3 endpoints | Mikael |
| F5 On-Chain | C5 | onchain_metrics | 2 endpoints | Jules |
| F6 Alertes | C6 | alert_rules, alert_history | 5 endpoints | Jules |
| F7 Regulatory | C7 | news_articles (extended) | 0 (reuse /news) | Jules |
| F8 Scraping | C7 | news_articles (extended) | 0 (reuse /news) | Jules |

---

## Trade-offs

| Decision | Gain | Perte | Rationale |
|----------|------|-------|-----------|
| PostgreSQL sans Redis | Zero complexity operationnelle | Pas de cache distribue | PG16 suffit pour notre volume |
| Q-table en DB (pas numpy) | Persistence, query, audit | Lookup 1ms au lieu de 0.1ms | 1ms est negligeable |
| TensorFlow (pas PyTorch) | Keras API simple, SavedModel | Ecosysteme recherche plus petit | Projet scolaire, pas recherche |
| smtplib (pas SendGrid) | Zero cout, zero dependance | Deliverabilite moins bonne | Projet scolaire, pas SaaS |
| LISTEN/NOTIFY (pas Celery) | Zero broker a maintenir | Pas de retry automatique | Volume faible (< 100 alertes/jour) |
| BeautifulSoup (pas Scrapy) | Simple, le cadrage l'exige | Pas de crawling distribue | On scrape 3 sites max |

---

## Assumptions & Constraints

- Equipe de 2 personnes, 12 semaines restantes
- APIs gratuites uniquement (Mempool, Blockchain.com, Etherscan free tier)
- Pas de trading reel (paper trading simulation uniquement)
- Docker Compose (pas Kubernetes)
- TensorFlow 2.13+ (pas PyTorch)
- PostgreSQL 16 (TimescaleDB) pour tout le stockage

---

## Revision History

| Version | Date | Auteur | Changements |
|---------|------|--------|-------------|
| 1.0 | 2026-03-15 | Jules (BMAD Architect) | Architecture initiale Phase 2 |

---

**This document was created using BMAD Method v6 — Phase 3 (Solutioning)**

*Next: Run `/bmad:sprint-planning` pour Phase 4*
