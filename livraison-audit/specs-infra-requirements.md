# CDC Infrastructure & Architecture Données — Crypto Bot
## Spécification Complète (Architecte Infrastructure + Architecture Données)

**Version:** 2.1  
**Date:** 2026-03-12  
**Auteurs:** Architecte Infrastructure (Architect 3), Architecte Données (Architect 1)  
**Statut:** REMÉDIATION AUDIT — Phase 1-2  
**Applicable à:** Déploiement Production + Architecture codebase

---

## TABLE DES MATIÈRES

1. [Architecture Infrastructure](#1-architecture-infrastructure)
2. [Architecture Données](#2-architecture-données)
3. [Exigences Fonctionnelles Infrastructure (RF-INFRA)](#3-exigences-fonctionnelles-infrastructure)
4. [Exigences Fonctionnelles Données (RF-DATA)](#4-exigences-fonctionnelles-données)
5. [Remédiation Audit](#5-remédiation-audit)
6. [Matrice de Traçabilité](#6-matrice-de-traçabilité)
7. [Plan d'Implémentation](#7-plan-dimplémentation)

---

## 1. ARCHITECTURE INFRASTRUCTURE

### 1.1 Topologie Globale Docker Compose

```
┌─────────────────────────────────────────────────────────────┐
│                         INTERNET                             │
│                      (HTTPS/80→443)                          │
└────────────────────────────┬────────────────────────────────┘
                             │
                    ┌────────▼────────┐
                    │    NGINX        │  (reverse proxy)
                    │  (Alpine 1.27+) │  port 80, 443
                    └────────┬────────┘
                             │
                ┌────────────┼────────────┐
                │                         │
         ┌──────▼──────┐          ┌──────▼──────┐
         │   FRONTEND  │          │    API      │
         │ (Streamlit) │          │  (FastAPI)  │
         │  :8501      │          │   :8000     │
         └──────┬──────┘          └──────┬──────┘
                │                        │
                │ (frontend-net)         │ (frontend-net)
                └────────────┬───────────┘
                             │
                             │ (backend-net) — ISOLÉ du frontend
                ┌────────────┼─────────────────────────┐
                │            │                         │
         ┌──────▼────┐ ┌──────▼──────┐ ┌──────────────▼──┐
         │ TimescaleDB│ │   MinIO     │ │    MLflow       │
         │   :5432    │ │   :9000     │ │     :5000       │
         │  (pg16)    │ │ (S3-compat) │ │  (experiments)  │
         └───────┬────┘ └──────┬──────┘ └────────┬────────┘
                 │             │                 │
    ┌────────────┴─────────────┴─────────────────┘
    │
    └────────────┬──────────────┬──────────────┐
                 │              │              │
         ┌──────▼────┐ ┌───────▼───┐ ┌───────▼────┐
         │ETL Worker │ │ML Worker  │ │Prometheus  │
         │  (APSched)│ │ (trainer) │ │ (metrics)  │
         │  :varies  │ │  :varies  │ │   :9090    │
         └───────────┘ └───────────┘ └─────┬──────┘
                                            │
                                    ┌───────▼──────┐
                                    │   Grafana    │
                                    │   :3000      │
                                    └──────────────┘

Exporters supplémentaires :
  • postgres-exporter :9187 — Métriques TimescaleDB
  • nginx-exporter    :9113 — Métriques Nginx
```

### 1.2 Réseaux Docker

| Réseau | Services | Visibilité | Justification |
|--------|----------|-----------|--------------|
| `frontend-net` | nginx, api, frontend | Expose (80, 443) | Utilisateurs externes |
| `backend-net` | api, timescaledb, minio, mlflow, etl-worker, ml-worker, prometheus, grafana, exporters | Interne uniquement | Sécurité data |

**Sécurité réseau :** Le frontend ET nginx ne peuvent **PAS** accéder directement à TimescaleDB ou MinIO. Tout passe par l'API FastAPI.

### 1.3 Services Docker Compose

**Fichier source :** `docker-compose.yml` (version 3.8+)

| Service | Image | Port (dev) | Health Check | Limites Mem | Dépend de |
|---------|-------|-----------|------|--------|-----------|
| **timescaledb** | `timescale/timescaledb:2.14.2-pg16` | 127.0.0.1:5433 | pg_isready (10s) | 1 GB | — |
| **minio** | `minio/minio:RELEASE.2024-03-30` | 127.0.0.1:9000 | health/live (30s) | 512 MB | — |
| **mlflow** | `ghcr.io/mlflow/mlflow:v2.10.2` | 127.0.0.1:5000 | http:5000/ (30s) | 512 MB | timescaledb, minio |
| **api** | Local Dockerfile (`src/api/Dockerfile`) | 127.0.0.1:8000 | /health (30s) | 512 MB | timescaledb, minio |
| **frontend** | Local Dockerfile (`src/frontend/Dockerfile`) | 127.0.0.1:8501 | /_stcore/health (30s) | 512 MB | api |
| **etl-worker** | Local Dockerfile (`src/etl/Dockerfile`) | N/A | Python import (30s) | 1 GB | timescaledb, minio |
| **ml-worker** | Local Dockerfile (`src/ml/Dockerfile`) | N/A | Python import (30s) | 1 GB | timescaledb, minio, mlflow |
| **nginx** | `nginx:1.27-alpine` | 0.0.0.0:80, 443 | wget /health (30s) | — | api, frontend |
| **prometheus** | `prom/prometheus:v2.52.0` | 127.0.0.1:9090 | /-/healthy (30s) | 512 MB | — |
| **grafana** | `grafana/grafana:10.4.2` | 127.0.0.1:3000 | /api/health (30s) | 256 MB | prometheus |
| **postgres-exporter** | `prometheuscommunity/postgres-exporter:v0.15.0` | N/A | — | 64 MB | timescaledb |
| **nginx-exporter** | `nginx/nginx-prometheus-exporter:1.1.0` | N/A | — | 32 MB | nginx |

### 1.4 Volumes Nommés

| Volume | Service | Point de montage | Persistance |
|--------|---------|-----------------|-------------|
| `timescaledb-data` | timescaledb | `/var/lib/postgresql/data` | Permanente |
| `minio-data` | minio | `/data` | Permanente |
| `prometheus-data` | prometheus | `/prometheus` | Permanente (15j) |
| `grafana-data` | grafana | `/var/lib/grafana` | Permanente |

**Convention :** Toujours utiliser des **volumes nommés**, jamais de bind mounts en production.

### 1.5 Politique de Redémarrage

**Tous les services :** `restart: unless-stopped`

Raison : survit aux redémarrages Docker, sauf arrêt explicite.

---

## 2. ARCHITECTURE DONNÉES

### 2.1 Schéma TimescaleDB

**Source de vérité :** Migrations Alembic dans `src/etl/migrations/` (à générer)

#### 2.1.1 Hypertable `crypto_prices` (Séries temporelles OHLCV)

```sql
CREATE TABLE crypto_prices (
    symbol          VARCHAR(20) NOT NULL,
    timeframe       VARCHAR(10) NOT NULL,  -- 1m, 5m, 15m, 1h, 4h, 1D, 1W
    timestamp       TIMESTAMPTZ NOT NULL,  -- PRIMARY PARTITION
    price_open      DECIMAL(20, 8) NOT NULL,
    price_high      DECIMAL(20, 8) NOT NULL,
    price_low       DECIMAL(20, 8) NOT NULL,
    price_close     DECIMAL(20, 8) NOT NULL,
    volume_24h      DECIMAL(20, 8) NOT NULL DEFAULT 0,
    market_cap      DECIMAL(20, 2),
    source          VARCHAR(50) NOT NULL,  -- binance, coingecko, ccxt
    collected_at    TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (symbol, timeframe, timestamp, source)
);

SELECT create_hypertable('crypto_prices', 'timestamp', if_not_exists => true);

-- Indexes
CREATE INDEX idx_prices_symbol_tf_ts 
    ON crypto_prices (symbol, timeframe, timestamp DESC);
CREATE INDEX idx_prices_timestamp 
    ON crypto_prices (timestamp DESC);

-- Compression (données > 7j)
ALTER TABLE crypto_prices SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'symbol, timeframe',
    timescaledb.compress_orderby = 'timestamp DESC'
);
SELECT add_compression_policy('crypto_prices', INTERVAL '7 days', if_not_exists => true);

-- Retention (données > 90j supprimées)
SELECT add_retention_policy('crypto_prices', INTERVAL '90 days', if_not_exists => true);
```

**Ratios compressibilité :** ~80% reduction taille (OHLCV statique, nombreuses valeurs répétées).

#### 2.1.2 Table `indicators` (Indicateurs techniques)

```sql
CREATE TABLE indicators (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol              VARCHAR(20) NOT NULL,
    timeframe           VARCHAR(10) NOT NULL,
    timestamp           TIMESTAMPTZ NOT NULL,
    
    -- Indicateurs
    rsi_14              DECIMAL(10, 4),                      -- RSI période 14
    bollinger_upper     DECIMAL(20, 8),
    bollinger_middle    DECIMAL(20, 8),
    bollinger_lower     DECIMAL(20, 8),
    bb_position         DECIMAL(10, 6),                      -- Position [0,1] dans les bandes
    
    -- Patterns
    harmonic_pattern    VARCHAR(50),                         -- Gartley, Butterfly, Crab, Bat
    harmonic_confidence DECIMAL(5, 4),
    
    -- Trends
    trend_type          VARCHAR(20),                         -- stable, aggressive, reversal
    trend_slope         DECIMAL(10, 6),                      -- Pente linéaire
    support_level       DECIMAL(20, 8),
    resistance_level    DECIMAL(20, 8),
    
    -- Volumes
    volume_ma_ratio     DECIMAL(10, 6),                      -- Vol / MA(20 vol)
    
    -- Métadonnées
    calculated_at       TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (symbol, timeframe, timestamp)
);

CREATE INDEX idx_indicators_symbol_tf_ts 
    ON indicators (symbol, timeframe, timestamp DESC);
```

#### 2.1.3 Table `trading_signals` (Signaux de trading)

```sql
CREATE TABLE trading_signals (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol              VARCHAR(20) NOT NULL,
    signal_type         VARCHAR(10) NOT NULL,  -- BUY, SELL, HOLD
    confidence_score    DECIMAL(5, 4) NOT NULL CHECK (confidence_score >= 0 AND confidence_score <= 1),
    
    -- Contexte
    timeframe_primary   VARCHAR(10) NOT NULL,
    timeframes_aligned  JSONB DEFAULT '[]',                  -- [1h, 2h, 4h] si convergence
    
    -- Règles appliquées
    rules_triggered     JSONB DEFAULT '{}',                  -- {"rsi_oversold": true, ...}
    indicators_snapshot JSONB DEFAULT '{}',                  -- Snapshot des indicateurs
    
    -- Avis de trading (informatif uniquement)
    entry_price         DECIMAL(20, 8) NOT NULL,
    stop_loss           DECIMAL(20, 8),
    take_profit_1       DECIMAL(20, 8),
    take_profit_2       DECIMAL(20, 8),
    leverage_suggested  INTEGER DEFAULT 1 CHECK (leverage_suggested >= 1 AND leverage_suggested <= 2),
    
    -- Frais estimés
    entry_fee_pct       DECIMAL(5, 4) DEFAULT 0.001,
    exit_fee_pct        DECIMAL(5, 4) DEFAULT 0.001,
    
    -- Modèle
    model_version       VARCHAR(50),                         -- v1.0_rule_engine, v1.1_rsi, ...
    model_type          VARCHAR(20) DEFAULT 'rule-based',    -- rule-based, supervised-ml, ensemble
    
    -- Timestamps
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    expires_at          TIMESTAMPTZ,
    
    -- Audit
    created_by          VARCHAR(50),                         -- signal_generator_v1
    notes               TEXT
);

CREATE INDEX idx_signals_symbol_created 
    ON trading_signals (symbol, created_at DESC);
CREATE INDEX idx_signals_confidence 
    ON trading_signals (confidence_score DESC);
```

#### 2.1.4 Table `signal_outcomes` (Évaluation a posteriori)

```sql
CREATE TABLE signal_outcomes (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    signal_id        UUID REFERENCES trading_signals(id) ON DELETE CASCADE,
    symbol           VARCHAR(20) NOT NULL,
    
    -- Prix au moment du signal
    price_at_signal  DECIMAL(20, 8) NOT NULL,
    
    -- Prix après périodes
    price_after_1h   DECIMAL(20, 8),
    price_after_4h   DECIMAL(20, 8),
    price_after_1d   DECIMAL(20, 8),
    price_after_7d   DECIMAL(20, 8),
    
    -- Analyse
    direction_signal VARCHAR(10),                            -- BUY, SELL, HOLD
    actual_direction VARCHAR(10),                            -- UP, DOWN, NEUTRAL
    was_correct      BOOLEAN,
    
    -- Rendement simulé
    pnl_1h_pct       DECIMAL(10, 4),
    pnl_4h_pct       DECIMAL(10, 4),
    pnl_1d_pct       DECIMAL(10, 4),
    pnl_best_pct     DECIMAL(10, 4),
    max_drawdown_pct DECIMAL(10, 4),
    
    -- SL/TP validations
    hit_stop_loss    BOOLEAN,
    hit_take_profit  BOOLEAN,
    
    evaluated_at     TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_outcomes_signal_id ON signal_outcomes(signal_id);
CREATE INDEX idx_outcomes_was_correct ON signal_outcomes(was_correct);
```

#### 2.1.5 Table `users`

```sql
CREATE TABLE users (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username          VARCHAR(100) UNIQUE NOT NULL,
    email             VARCHAR(255) UNIQUE NOT NULL,
    password_hash     VARCHAR(255) NOT NULL,
    
    persona_type      VARCHAR(20) CHECK (persona_type IN ('trader', 'journalist', 'investor')),
    api_key_hash      VARCHAR(255),                          -- Pour accès API programmatique
    
    watchlist         JSONB DEFAULT '[]',                    -- ["BTC", "ETH", ...]
    preferences       JSONB DEFAULT '{}',                    -- Theme, langue, notifications
    subscription_plan VARCHAR(20) DEFAULT 'free',            -- free, pro, enterprise
    
    created_at        TIMESTAMPTZ DEFAULT NOW(),
    updated_at        TIMESTAMPTZ DEFAULT NOW(),
    last_login_at     TIMESTAMPTZ
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);
```

#### 2.1.6 Table `news_articles`

```sql
CREATE TABLE news_articles (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title            VARCHAR(500) NOT NULL,
    content          TEXT,
    source           VARCHAR(100) NOT NULL,                  -- Decrypt, Cointelegraph, etc.
    url              VARCHAR(1000) UNIQUE NOT NULL,
    
    published_at     TIMESTAMPTZ,
    collected_at     TIMESTAMPTZ DEFAULT NOW(),
    
    -- Analyse texte
    sentiment_score  DECIMAL(5, 4),                          -- [-1, 1] négatif à positif
    keywords         JSONB DEFAULT '[]',                     -- ["DeFi", "regulatory", ...]
    entities         JSONB DEFAULT '[]',                     -- Symboles/personnes mentionnés
    reliability_score DECIMAL(5, 4),                         -- [0, 1] confiance source
    
    -- Archivage
    is_archived      BOOLEAN DEFAULT false
);

CREATE INDEX idx_articles_published ON news_articles(published_at DESC);
CREATE INDEX idx_articles_source ON news_articles(source);
CREATE INDEX idx_articles_sentiment ON news_articles(sentiment_score);
```

### 2.2 Structure MinIO (S3-compatibilité)

```
minio://
├── raw/                           # Données brutes (étiquette read-only)
│   ├── ohlcv/
│   │   ├── BINANCE/
│   │   │   └── {SYMBOL}/
│   │   │       └── {YYYY-MM-DD}/
│   │   │           ├── 1m.parquet
│   │   │           ├── 5m.parquet
│   │   │           └── 1h.parquet
│   │   └── COINGECKO/
│   │       └── metadata/{YYYY-MM-DD}.json
│   └── news/
│       └── {source}/{YYYY-MM-DD}.jsonl
│
├── datasets/                       # Préparés pour ML
│   ├── features/
│   │   └── features_{YYYY-MM-DD}_{model_v}.parquet
│   ├── labels/
│   │   └── labels_{YYYY-MM-DD}_{window}.parquet
│   └── validation/
│       └── test_set_{fold}.parquet
│
├── models/                         # Modèles entraînés
│   ├── xgboost_v1.0.pkl
│   ├── lstm_v1.1.joblib
│   └── ensemble_v2.0.pkl
│
├── mlflow-artifacts/               # Gérés par MLflow
│   ├── {experiment_id}/
│   │   └── {run_id}/
│   │       ├── artifacts/
│   │       ├── params.json
│   │       └── metrics.json
│
└── backups/                        # Sauvegardes
    ├── timescaledb/
    │   ├── cryptobot_2026-03-12_030000.sql.gz
    │   └── cryptobot_2026-03-11_030000.sql.gz
    └── minio/
        └── minio_backup_2026-03-11.tar.gz
```

**Lifecycle rules :**
- `raw/` : retention 180j (conformité historique)
- `datasets/` : retention 30j (remplacés régulièrement)
- `backups/` : retention 30j pour quotidiens, 90j pour hebdos
- `mlflow-artifacts/` : retention infinie (audit traçabilité expériences)

### 2.3 Flux Données Global

```
External APIs                 ETL Worker                  TimescaleDB         API/Frontend
┌──────────────────┐     ┌────────────────────┐     ┌──────────────┐     ┌──────────────┐
│ Binance REST/WS  │────→│ collect_ohlcv      │────→│ crypto_prices│────→│ GET /prices  │
│ :1200 req/min    │     │ (APScheduler)      │     │ (hypertable) │     │              │
└──────────────────┘     └────────────────────┘     └──────────────┘     └──────────────┘
┌──────────────────┐     ┌────────────────────┐     ┌──────────────┐
│ CoinGecko Demo   │────→│ collect_market     │────→│ crypto_prices│
│ :30 req/min      │     │ (APScheduler)      │     │ + metadata   │
└──────────────────┘     └────────────────────┘     └──────────────┘
┌──────────────────┐     ┌────────────────────┐     ┌──────────────┐
│ RSS News feeds   │────→│ collect_news       │────→│ news_articles│
│ (Decrypt, etc.)  │     │ (scraping 1-2s)    │     │              │
└──────────────────┘     └────────────────────┘     └──────────────┘

                         ┌────────────────────┐     ┌──────────────┐     ┌──────────────┐
                         │ compute_indicators │────→│ indicators   │────→│ GET /signals │
                         │ (post-collect)     │     │ (RSI, BB)    │     │              │
                         └────────────────────┘     └──────────────┘     └──────────────┘
                                                                              │
                                                    ┌──────────────────────→ ML Worker
                                                    │ training dataset
ML Worker                  TimescaleDB               export_datasets
┌────────────────────┐     ┌──────────────────┐     ┌──────────────┐
│ rule_engine        │────→│ trading_signals  │────→│ MinIO        │
│ (phase 1)          │     │                  │     │ datasets/    │
└────────────────────┘     └──────────────────┘     └──────────────┘
                                                    │
                                                    ↓ (feedback)
                         ┌──────────────────┐     ┌──────────────┐
                         │ signal_outcomes  │←────│ price after  │
                         │ (évaluation)     │     │ 1h/4h/1d     │
                         └──────────────────┘     └──────────────┘
```

### 2.4 Compression & Retention TimescaleDB

| Table | Compress après | Retention | Ratio compressibilité |
|-------|-----------------|-----------|---------------------|
| `crypto_prices` | 7j | 90j | ~80% (OHLCV répétitif) |
| `indicators` | 14j | 180j | ~60% (floats varés) |
| `trading_signals` | N/A | infini | N/A (archif audit) |
| `news_articles` | 30j | 1 an | ~40% (texte dedupliqué) |

**Stockage estimé :**
- 30 crypto × 7 timeframes × 90j OHLCV : ~600 MB non compressé → ~120 MB compressé
- 500 articles/jour × 365j : ~2 GB

---

## 3. EXIGENCES FONCTIONNELLES INFRASTRUCTURE

### 3.1 Exigences Docker (RF-INFRA-001 à RF-INFRA-010)

#### RF-INFRA-001 — Images Docker pinnées
- **Priorité MoSCoW:** MUST (critique, audit D1)
- **Description:** Toutes les images de base doivent avoir une version précise, jamais `:latest` ni tags flous (`:slim`, `:alpine`).
- **Acceptation:**
  - [ ] `timescaledb:2.14.2-pg16` (pas `latest-pg16`)
  - [ ] `minio:RELEASE.2024-03-30T` (pas `latest`)
  - [ ] `nginx:1.27-alpine` (pas `alpine` seul)
  - [ ] `grafana:10.4.2` (exact)
  - [ ] `prom/prometheus:v2.52.0` (exact)
  - [ ] Tous les Dockerfiles Python pinned au tag commit git
- **Fichiers touchés:** `docker-compose.yml`, `src/api/Dockerfile`, `src/etl/Dockerfile`, `src/ml/Dockerfile`, `src/frontend/Dockerfile`

#### RF-INFRA-002 — Dockerfile multi-stage pour images Python
- **Priorité:** MUST (sécurité, taille)
- **Description:** Chaque application Python doit utiliser un builder stage (dépendances compilation) et un runtime stage minimal (pas de gcc, pip, git, etc.).
- **Acceptation:**
  - [ ] `src/api/Dockerfile` : builder → runtime
  - [ ] `src/etl/Dockerfile` : builder → runtime
  - [ ] `src/ml/Dockerfile` : builder → runtime
  - [ ] `src/frontend/Dockerfile` : builder → runtime
  - [ ] **Exemple attendu :** 
    ```dockerfile
    FROM python:3.11-slim as builder
    WORKDIR /build
    COPY requirements.txt .
    RUN pip install --no-cache-dir -r requirements.txt
    
    FROM python:3.11-slim
    RUN useradd -m -u 1001 appuser
    COPY --from=builder /usr/local/lib /usr/local/lib
    COPY src/ /app/
    USER appuser
    CMD ["python", "-m", "uvicorn", "src.api.main:app", "--host", "0.0.0.0"]
    ```
  - [ ] User non-root (UID >= 1000)

#### RF-INFRA-003 — Health checks sur tous les services
- **Priorité:** MUST (disponibilité, orchestration)
- **Description:** Chaque service Docker doit avoir un healthcheck définissant comment vérifier s'il est opérationnel.
- **Acceptation:**
  - [ ] `timescaledb`: `pg_isready` (10s interval, 5s timeout, 5 retries)
  - [ ] `minio`: `curl -f http://localhost:9000/minio/health/live` (30s)
  - [ ] `api`: `curl -f http://localhost:8000/health` (30s)
  - [ ] `frontend`: `curl -f http://localhost:8501/_stcore/health` (30s)
  - [ ] `nginx`: `wget --spider http://127.0.0.1/health` (30s)
  - [ ] `mlflow`: `curl -f http://localhost:5000/` (30s)
  - [ ] `prometheus`: `wget --spider http://localhost:9090/-/healthy` (30s)
  - [ ] `grafana`: `wget --spider http://localhost:3000/api/health` (30s)

#### RF-INFRA-004 — Limites de ressources sur tous les services
- **Priorité:** MUST (stabilité production)
- **Description:** Chaque container a des limites CPU et mémoire pour éviter les runaway processes.
- **Acceptation:**
  - [ ] `timescaledb`: 1 GB memory
  - [ ] `minio`: 512 MB
  - [ ] `api`: 512 MB
  - [ ] `frontend`: 512 MB
  - [ ] `etl-worker`: 1 GB
  - [ ] `ml-worker`: 1 GB
  - [ ] `mlflow`: 512 MB
  - [ ] `prometheus`: 512 MB
  - [ ] `grafana`: 256 MB
  - [ ] Sintaxe `docker-compose.yml` : `deploy.resources.limits.memory: 512M`

#### RF-INFRA-005 — Volumes nommés uniquement, pas de bind mounts
- **Priorité:** MUST (persistence, portabilité)
- **Description:** Les données persistantes utilisent des volumes nommés Docker, jamais de `volumes: ./local:/container`.
- **Acceptation:**
  - [ ] `timescaledb-data`: `/var/lib/postgresql/data`
  - [ ] `minio-data`: `/data`
  - [ ] `prometheus-data`: `/prometheus`
  - [ ] `grafana-data`: `/var/lib/grafana`
  - [ ] Pas de bind mounts sauf configs read-only (Nginx, Prometheus)

#### RF-INFRA-006 — Réseau segmenté frontend/backend
- **Priorité:** MUST (sécurité)
- **Description:** `frontend-net` (nginx, api, frontend) isolé de `backend-net` (data services) pour éviter l'accès frontal aux bases.
- **Acceptation:**
  - [ ] `frontend-net` : nginx, api, frontend seulement
  - [ ] `backend-net` : timescaledb, minio, mlflow, etl-worker, ml-worker, prometheus, exporters
  - [ ] `api` sur **les deux** réseaux (bridge frontend et backend)
  - [ ] Vérification : `docker network inspect frontend-net` affiche 3 services, `backend-net` affiche 8

#### RF-INFRA-007 — Dependencies order avec health checks
- **Priorité:** MUST (orchestration)
- **Description:** Les services dépendants attendent que leurs dépendances soient healthy via `depends_on.condition: service_healthy`.
- **Acceptation:**
  - [ ] `api` attend `timescaledb` healthy + `minio` healthy
  - [ ] `frontend` attend `api` healthy
  - [ ] `mlflow` attend `timescaledb` healthy + `minio` healthy
  - [ ] `etl-worker` attend `timescaledb` healthy + `minio` healthy
  - [ ] `ml-worker` attend `timescaledb` healthy + `minio` healthy + `mlflow` healthy
  - [ ] `nginx` attend `api` healthy + `frontend` healthy

#### RF-INFRA-008 — Restart policy production
- **Priorité:** MUST (résilience)
- **Description:** `restart: unless-stopped` sur tous les services pour survie aux redémarrages Docker.
- **Acceptation:**
  - [ ] 10/10 services ont `restart: unless-stopped`

#### RF-INFRA-009 — .dockerignore pour chaque service
- **Priorité:** SHOULD (taille images)
- **Description:** Chaque Dockerfile s'appuie sur un `.dockerignore` pour exclure files inutiles (`.git`, `__pycache__`, tests, etc.).
- **Acceptation:**
  - [ ] `.dockerignore` à la racine exclut : `.git`, `.pytest_cache`, `mlruns`, `*.pyc`, `__pycache__`, `.env`, `*.md` (sauf README)
  - [ ] Taille images Python < 200 MB (après multi-stage)

#### RF-INFRA-010 — Ports isolés localhost (dev)
- **Priorité:** SHOULD (sécurité dev)
- **Description:** En développement, les ports exposés sont liés à `127.0.0.1:PORT` pour éviter l'accès réseau local.
- **Acceptation:**
  - [ ] `timescaledb`: `127.0.0.1:5433:5432`
  - [ ] `minio`: `127.0.0.1:9000:9000`, `127.0.0.1:9001:9001`
  - [ ] `api`: `127.0.0.1:8000:8000`
  - [ ] `frontend`: `127.0.0.1:8501:8501`
  - [ ] `mlflow`: `127.0.0.1:5000:5000`
  - [ ] `prometheus`: `127.0.0.1:9090:9090`
  - [ ] `grafana`: `127.0.0.1:3000:3000`
  - [ ] (Exception : nginx `0.0.0.0:80`, `0.0.0.0:443` en prod)

### 3.2 Exigences Nginx & TLS (RF-INFRA-011 à RF-INFRA-015)

#### RF-INFRA-011 — Reverse proxy API + Frontend
- **Priorité:** MUST (fonctionnalité core)
- **Description:** Nginx route `/api/*` vers FastAPI `:8000` et `/` vers Streamlit `:8501`.
- **Acceptation:**
  - [ ] `/api/` → `http://api:8000/` (proxy_pass, keep-alive)
  - [ ] `/api/auth/` → `http://api:8000/auth/` (idem)
  - [ ] `/health` → `http://api:8000/health` (no-log)
  - [ ] `/` → `http://frontend:8501` (WebSocket support, Upgrade headers)
  - [ ] Headers forwarding : `X-Real-IP`, `X-Forwarded-For`, `X-Forwarded-Proto`, `Host`
- **Fichier:** `infra/nginx/nginx.conf`

#### RF-INFRA-012 — Rate limiting Nginx
- **Priorité:** MUST (anti-abuse)
- **Description:** Limiter le débit API et endpoints d'auth pour éviter attaques brute-force et DoS.
- **Acceptation:**
  - [ ] `limit_req_zone api_limit: 30 req/s` (API général)
  - [ ] `limit_req_zone auth_limit: 5 req/min` (endpoints auth login/register)
  - [ ] Burst allowé : +20 requêtes pour API, +3 pour auth
  - [ ] Configuration Nginx :
    ```nginx
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=30r/s;
    limit_req_zone $binary_remote_addr zone=auth_limit:10m rate=5r/m;
    location /api/auth/ {
      limit_req zone=auth_limit burst=3 nodelay;
      ...
    }
    ```

#### RF-INFRA-013 — Headers de sécurité Nginx
- **Priorité:** MUST (OWASP)
- **Description:** Tous les headers de sécurité standard présents (X-Frame-Options, X-Content-Type-Options, etc.).
- **Acceptation:**
  - [ ] `X-Frame-Options: SAMEORIGIN` (clickjacking)
  - [ ] `X-Content-Type-Options: nosniff` (MIME sniffing)
  - [ ] `X-XSS-Protection: 1; mode=block` (XSS legacy)
  - [ ] `Referrer-Policy: strict-origin-when-cross-origin`
  - [ ] `server_tokens off` (masquer version Nginx)
  - [ ] Gzip enabled : `gzip on; gzip_min_length 1000; gzip_types ...`

#### RF-INFRA-014 — HTTPS/TLS avec Let's Encrypt
- **Priorité:** MUST (chiffrement, audit S6)
- **Description:** HTTPS obligatoire en production via Let's Encrypt (certbot).
- **Acceptation:**
  - [ ] HTTP (80) redirige vers HTTPS (443) : `return 301 https://$host$request_uri;`
  - [ ] Certificat Let's Encrypt dans `/etc/letsencrypt/live/{domain}/`
  - [ ] Nginx serve `fullchain.pem` + `privkey.pem`
  - [ ] TLS 1.2+ uniquement : `ssl_protocols TLSv1.2 TLSv1.3;`
  - [ ] Ciphers forts : `ssl_ciphers HIGH:!aNULL:!MD5;`
  - [ ] Renouvellement auto cron : `0 0 1 * * certbot renew --quiet && docker-compose restart nginx`
  - [ ] HSTS optional (recommandé) : `add_header Strict-Transport-Security "max-age=31536000" always;`

#### RF-INFRA-015 — Configuration CORS API
- **Priorité:** MUST (cross-origin security)
- **Description:** CORS restrictif, pas d'allow_methods=["*"].
- **Acceptation:**
  - [ ] `allow_origins`: liste whitelist (`http://localhost:3000`, `https://cryptobot.example.com`)
  - [ ] `allow_methods`: explicite (`GET`, `POST`, `PUT`, `DELETE`, `OPTIONS`)
  - [ ] `allow_headers`: explicite (`Content-Type`, `Authorization`)
  - [ ] `allow_credentials`: `True`
  - [ ] Configuration FastAPI `src/api/main.py`:
    ```python
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )
    ```

### 3.3 Exigences CI/CD (RF-INFRA-016 à RF-INFRA-020)

#### RF-INFRA-016 — Pipeline GitHub Actions complet
- **Priorité:** MUST (automatisation)
- **Description:** CI/CD pipeline : Lint → Type Check → Test → Build Docker → Deploy Ansible.
- **Acceptation:**
  - [ ] Sur `pull_request` et `push main` :
    - [ ] **Lint job** : `ruff check src/` + `ruff format --check src/`
    - [ ] **Type check** : `mypy src/ --ignore-missing-imports`
    - [ ] **Test job** : `pytest tests/ --cov=src --cov-fail-under=80`
    - [ ] **Build job** : `docker compose build --no-cache` (needs: test)
    - [ ] **Deploy job** (only on `push main`) : Ansible playbook
- **Fichier:** `.github/workflows/ci.yml`

#### RF-INFRA-017 — Secrets GitHub configurés
- **Priorité:** MUST (déploiement prod)
- **Description:** Tous les secrets nécessaires doivent exister en GitHub Secrets.
- **Acceptation:**
  - [ ] `VPS_IP` — IP/hostname du serveur production
  - [ ] `VPS_SSH_KEY` — Clé privée ED25519 pour user `deploy`
  - [ ] `VPS_USER` — Nom du user (ex: `deploy`)
  - [ ] Vérification : Settings → Secrets & variables → Actions affiche 3 secrets
  - [ ] Pas de secrets en plaintext dans `.yml`

#### RF-INFRA-018 — Test coverage gate
- **Priorité:** MUST (qualité)
- **Description:** CI échoue si couverture < 80%.
- **Acceptation:**
  - [ ] `pytest --cov=src --cov-fail-under=80` dans CI
  - [ ] Coverage report uploadé en artifact
  - [ ] Branch protection rule : passing checks obligatoires

#### RF-INFRA-019 — Artefacts et rapports CI
- **Priorité:** SHOULD (traçabilité)
- **Description:** CI publie coverage report, logs de build pour analyse post-mortem.
- **Acceptation:**
  - [ ] Coverage XML uploadé après test
  - [ ] Docker build logs conservés en cas d'erreur
  - [ ] Artifacts retenus 30 jours

#### RF-INFRA-020 — Branch protection main
- **Priorité:** MUST (intégrité)
- **Description:** Protéger la branche `main` contre les commits directs et push sans PR approuvée.
- **Acceptation:**
  - [ ] Require pull request before merging
  - [ ] Require status checks (lint, test, build)
  - [ ] Require code review (≥1)
  - [ ] Dismiss stale PR approvals
  - [ ] Include administrators

### 3.4 Exigences Ansible & Provisioning (RF-INFRA-021 à RF-INFRA-025)

#### RF-INFRA-021 — Playbook provision VPS
- **Priorité:** MUST (déploiement infra)
- **Description:** Script Ansible `provision.yml` configure un VPS vierge en une seule exécution : Docker, UFW, user, Nginx, certbot, fail2ban.
- **Acceptation:**
  - [ ] `infra/ansible/playbooks/provision.yml` existe
  - [ ] Tasks :
    - [ ] Mettre à jour OS + apt security updates
    - [ ] Installer Docker + Docker Compose v2
    - [ ] Créer user `deploy` (gid=1000+, avec sudo Docker)
    - [ ] Configurer UFW : allow 22 (SSH), 80 (HTTP), 443 (HTTPS)
    - [ ] Installer certbot + nginx
    - [ ] Configurer fail2ban (maxretry=5, bantime=3600s)
    - [ ] Configurer swap (2 GB si RAM < 4 GB)
  - [ ] Exécutable : `ansible-playbook -i inventories/production.ini playbooks/provision.yml`

#### RF-INFRA-022 — Playbook deploy application
- **Priorité:** MUST (déploiement app)
- **Description:** `deploy.yml` : git sync, docker build, healthcheck, service restart.
- **Acceptation:**
  - [ ] Tasks (sans `delete: true` destructif) :
    - [ ] Synchroniser via `rsync` (exclure `.git`, `.env`, pycache)
    - [ ] Vérifier `.env` présent (fail si absent)
    - [ ] `docker compose pull` (images pinnées)
    - [ ] `docker compose build` (applications)
    - [ ] `docker compose down` (graceful)
    - [ ] `docker compose up -d` (start)
    - [ ] Wait 15s pour stabilisation
    - [ ] Healthcheck API : `curl http://localhost:8000/api/health` (5 retries, 5s delay)
    - [ ] Healthcheck Frontend : `curl http://localhost:8501` (5 retries)
  - [ ] Exécutable depuis CI : GitHub Actions appelle `ansible-playbook deploybooks/deploy.yml`

#### RF-INFRA-023 — Stratégie rollback déploiement
- **Priorité:** HIGH (récupération urgence)
- **Description:** Capacité à revenir à la version précédente en < 5 minutes en cas de deploy cassé.
- **Acceptation:**
  - [ ] **Approche 1** : Garder images Docker des 3 dernières versions
    - [ ] Tag images : `api:v1.2.3`, `api:v1.2.2`, `api:v1.2.1`
    - [ ] Dans `docker-compose.yml.rollback`, remplacer tags
    - [ ] Script `rollback.sh` : restaure `.env`, change tags, `docker compose up -d`
  - [ ] **Approche 2** : Git tags + build historique
    - [ ] Chaque deploy étiqueté : `git tag deploy/v1.2.3 && git push origin deploy/v1.2.3`
    - [ ] Rollback = `git checkout deploy/v1.2.2 && docker-compose up -d --build`
  - [ ] Playbook `rollback.yml` : exécution facile du rollback
  - [ ] Temps revenu en arrière : < 5 minutes (pas de re-train ML, données inchangées)

#### RF-INFRA-024 — Logs et monitoring
- **Priorité:** MUST (observabilité)
- **Description:** Prometheus + Grafana pour métriques, Docker logs pour applicatif.
- **Acceptation:**
  - [ ] **Prometheus** (`:9090`):
    - [ ] Config `infra/prometheus/prometheus.yml` scrape 15s
    - [ ] Cibles : api (/metrics), postgres-exporter, nginx-exporter
    - [ ] Retention 15j (`--storage.tsdb.retention.time=15d`)
  - [ ] **Grafana** (`:3000`):
    - [ ] Datasource Prometheus configurée
    - [ ] 4 dashboards :
      - [ ] API Overview (latency, req/s, errors)
      - [ ] System (CPU, mémoire, disque)
      - [ ] Database (queries/s, cache hit ratio, table sizes)
      - [ ] Business (signaux/jour, utilisateurs, coût inférence ML)
  - [ ] **Docker logs** : `docker compose logs {service} -f --tail=100`
  - [ ] **Alertes Grafana** (optionnel Phase 1, requis Phase 2):
    - [ ] CPU > 80% (30s)
    - [ ] Mémoire > 85% (30s)
    - [ ] Healthcheck failed (2 retries)
    - [ ] API latency > 2s (p95)
    - [ ] DB connectionsclose à max

#### RF-INFRA-025 — Backups TimescaleDB + MinIO
- **Priorité:** MUST (DR)
- **Description:** Sauvegarde quotidienne de la BDD et des données MinIO.
- **Acceptation:**
  - [ ] **TimescaleDB pg_dump** :
    - [ ] Script `scripts/backup-db.sh` (ou Ansible task)
    - [ ] Commande : `docker exec timescaledb pg_dump -U $USER $DB | gzip > /backups/cryptobot_$(date +%Y%m%d_%H%M%S).sql.gz`
    - [ ] Stockage : disque local `/opt/backups/timescaledb/` OU MinIO `backups/timescaledb/`
    - [ ] Fréquence : quotidienne à 3h UTC (off-peak)
    - [ ] Retention : 30j pour quotidiens, 4 semaines pour hebdos (script `find ... -mtime +30 -delete`)
    - [ ] Vérification : test restore mensuel sur DB de test
  - [ ] **MinIO** :
    - [ ] Playbook `backup.yml` : `mc mirror minio/raw minio-backup/raw` (sync)
    - [ ] Fréquence : hebdomadaire (samedi 4h UTC)
    - [ ] Retention : 4 semaines
    - [ ] Vérification : archivage quotidien de `models/` (immuable)
  - [ ] **Configuration** :
    - [ ] Secrets de backup dans `.env` (DB creds, MinIO access keys)
    - [ ] Cron job sur VPS : `0 3 * * * ansible-playbook /opt/crypto-bot/infra/ansible/playbooks/backup.yml`

---

## 4. EXIGENCES FONCTIONNELLES DONNÉES

### 4.1 Hypertables TimescaleDB (RF-DATA-001 à RF-DATA-005)

#### RF-DATA-001 — Création hypertable `crypto_prices`
- **Priorité:** MUST
- **Description:** Table TimescaleDB partitionnée par `timestamp` pour séries temporelles OHLCV.
- **Acceptation:**
  - [ ] Migration Alembic crée table avec `SELECT create_hypertable('crypto_prices', 'timestamp')`
  - [ ] Colonnes : symbol, timeframe, timestamp, open, high, low, close, volume, market_cap, source
  - [ ] UNIQUE constraint : (symbol, timeframe, timestamp, source)
  - [ ] Index : (symbol, timeframe, timestamp DESC)
  - [ ] Auto-création hypertable si absent

#### RF-DATA-002 — Compression automatique
- **Priorité:** MUST
- **Description:** Données > 7j compressées automatiquement pour réduire taille disque.
- **Acceptation:**
  - [ ] `ALTER TABLE crypto_prices SET (timescaledb.compress, timescaledb.compress_segmentby = 'symbol, timeframe')`
  - [ ] `ADD COMPRESSION POLICY` : INTERVAL '7 days'
  - [ ] Compression par job Timescale (`SELECT add_compression_policy(...)`)
  - [ ] Test : vérifier compression activée : `SELECT * FROM timescaledb_information.jobs WHERE application_name = 'Compression Policy'`

#### RF-DATA-003 — Retention policy
- **Priorité:** SHOULD
- **Description:** Données > 90j supprimées automatiquement pour limiter stockage.
- **Acceptation:**
  - [ ] `ADD RETENTION POLICY` : INTERVAL '90 days'
  - [ ] Job Timescale lance suppression nuit (off-peak)
  - [ ] Option prod : passer à 180j ou 365j selon besoin de backstesting

#### RF-DATA-004 — Indexes appropriés
- **Priorité:** MUST
- **Description:** Indexes pour requêtes courantes (par symbol, timeframe, timestamp).
- **Acceptation:**
  - [ ] Index principal : (symbol, timeframe, timestamp DESC) — searchable par symbole + timeframe
  - [ ] Index secondaire : (timestamp DESC) — range queries
  - [ ] Pas d'index sur source (faible cardinalité)
  - [ ] Vérification : `\d+ crypto_prices` affiche 2 indexes

#### RF-DATA-005 — Migrations Alembic versionnées
- **Priorité:** MUST
- **Description:** Toutes les migrations BDD via Alembic en `src/etl/migrations/`.
- **Acceptation:**
  - [ ] Convention de nom : `{timestamp}_{description}.py` (ex: `20260312_create_hypertables.py`)
  - [ ] Uprade + downgrade reversibles
  - [ ] Exécution : `alembic upgrade head`
  - [ ] Validation : `alembic current` affiche la dernière appliquée
  - [ ] Migrations incluses en CI (automatic-apply dev, manual-review prod)

### 4.2 Indicateurs Techniques (RF-DATA-006 à RF-DATA-010)

#### RF-DATA-006 — Table `indicators` pour stockage
- **Priorité:** MUST
- **Description:** Stockage centralisé des indicateurs calculés (RSI, Bollinger, harmonic patterns, etc.).
- **Acceptation:**
  - [ ] Colonnes : id, symbol, timeframe, timestamp, rsi_14, bollinger_upper/middle/lower, bb_position, harmonic_pattern, trend_type, trend_slope, support, resistance, volume_ma_ratio
  - [ ] UNIQUE (symbol, timeframe, timestamp)
  - [ ] Index (symbol, timeframe, timestamp DESC)
  - [ ] Métadonnées JSONB pour extensibilité future

#### RF-DATA-007 — Calcul RSI multi-timeframe
- **Priorité:** MUST
- **Description:** RSI (Relative Strength Index, période 14) calculé pour 1h, 2h, 4h, 1D, 1W.
- **Acceptation:**
  - [ ] Librairie : `ta-lib` ou `pandas-ta` (pandas_ta recommandé, no C deps)
  - [ ] Implémentation: `etl/indicators/rsi_calculator.py`
  - [ ] Formule : RSI = 100 - (100 / (1 + RS)) où RS = gain_moy / perte_moy
  - [ ] Lissage : EMA (alpha 2/(14+1))
  - [ ] Insertion en BDD après chaque collect OHLCV
  - [ ] Latency < 100ms pour 30 cryptos

#### RF-DATA-008 — Bollinger Bands (squeeze detection)
- **Priorité:** MUST
- **Description:** Bandes de Bollinger (MA20, écart-type 2) pour détection serrages (signaux).
- **Acceptation:**
  - [ ] Colonnes : bollinger_upper, bollinger_middle (MA20), bollinger_lower
  - [ ] Position relative (0-1) : (prix - lower) / (upper - lower)
  - [ ] Squeeze detection : width < 2% de prix
  - [ ] Calcul : `etl/indicators/bollinger_calculator.py`

#### RF-DATA-009 — Harmonic patterns détection
- **Priorité:** SHOULD
- **Description:** Reconnaissance patterns harmoniques (Gartley, Butterfly, Crab, Bat) sur 4h et 1D.
- **Acceptation:**
  - [ ] Patterns : Gartley, Butterfly, Crab, Bat (ratios Fibonacci)
  - [ ] Implémentation : `etl/indicators/harmonic_patterns.py` (librairie `namedtuple` ou `dataclass`)
  - [ ] Confiance associée (0-1) basée sur précision ratios
  - [ ] Stockage : table `indicators.harmonic_pattern` + `harmonic_confidence`

#### RF-DATA-010 — Trend lines et support/resistance
- **Priorité:** SHOULD
- **Description:** Pente de trend line (régression linéaire), support/resistance levels.
- **Acceptation:**
  - [ ] Trend slope : regression linéaire sur 14 bougies (1D) / 28 bougies (hebdo)
  - [ ] Support/resistance : locaux extrema (low/high derniers 20j)
  - [ ] Trend classification : stable (slope < 0.1%), aggressive (slope > 0.5%)
  - [ ] Calcul : `etl/indicators/trend_calculator.py`

### 4.3 MinIO & Versioning Données (RF-DATA-011 à RF-DATA-013)

#### RF-DATA-011 — Structure MinIO organisée
- **Priorité:** MUST
- **Description:** Buckets S3-compatibles avec hiérarchie claire (raw, datasets, models, mlflow-artifacts, backups).
- **Acceptation:**
  - [ ] Bucket `raw/` (read-only après write initial)
  - [ ] Bucket `datasets/` pour training sets ML
  - [ ] Bucket `models/` pour PKL/joblib entraînés
  - [ ] Bucket `mlflow-artifacts/` (géré par MLflow)
  - [ ] Bucket `backups/` pour TimescaleDB + MinIO snapshots
  - [ ] Policy S3 : user ETL peut write/read raw + datasets ; user ML read datasets + write models
  - [ ] Expiration lifecycle : raw (180j), datasets (30j), backups (30j + 4w archive)

#### RF-DATA-012 — Lifecycle rules MinIO
- **Priorité:** SHOULD
- **Description:** Politiques d'expiration automatique pour gestion taille storage.
- **Acceptation:**
  - [ ] `raw/` : expire après 180j (conformité historique)
  - [ ] `datasets/` : expire après 30j (datasets remplacés régulièrement)
  - [ ] `backups/` : expire après 7j pour quotidiens, archive 30j après
  - [ ] Configuration : `mc ilm` ou API PutBucketLifecycle
  - [ ] Vérification : `mc ilm ls minio/raw` affiche policies

#### RF-DATA-013 — Versioning datasets ML
- **Priorité:** MUST
- **Description:** Datasets versionnés pour traçabilité expériences MLflow + reproductibilité.
- **Acceptation:**
  - [ ] Nom convention : `features_{YYYY-MM-DD}_{model_version}.parquet`
  - [ ] Checksum MD5 stocké en métadonnées MinIO
  - [ ] DVC (Data Version Control) optionnel mais recommandé
  - [ ] Métadonnées : date création, nombre rows, schema Parquet
  - [ ] Lien MLflow : run.data.params[`dataset_path`] pointe vers MinIO

### 4.4 Qualité & Validation Données (RF-DATA-014 à RF-DATA-016)

#### RF-DATA-014 — Validation Pydantic des données entrantes
- **Priorité:** MUST
- **Description:** Toutes les données externes validées via Pydantic avant insertion BDD.
- **Acceptation:**
  - [ ] Modèle `src/shared/models/OHLCVRecord` valide : symbol, timeframe, prices OHLCV, volume, timestamp
  - [ ] Modèle `IndicatorRecord` valide : symbol, timeframe, rsi, bollinger, patterns
  - [ ] Modèle `NewsArticle` valide : title, source, url, published_at
  - [ ] Constraints Pydantic : symbol length 2-20, prices > 0, volume >= 0
  - [ ] On erreur validation : log WARN + skip record (pas d'exception propagée)

#### RF-DATA-015 — Deduplication de données OHLCV
- **Priorité:** MUST
- **Description:** Pas de doublon (symbol, timeframe, timestamp, source) dans la BDD.
- **Acceptation:**
  - [ ] UNIQUE constraint BDD : (symbol, timeframe, timestamp, source)
  - [ ] ETL pre-check : avant INSERT, SELECT EXISTS ... (si existe, UPDATE volume)
  - [ ] Idempotence : job peut être rejoué sans corruption
  - [ ] Détection de gaps : si timestamp_now - timestamp_last > 2 * interval, log WARNING + trigger reconciliation

#### RF-DATA-016 — Reconciliation de données manquantes
- **Priorité:** SHOULD
- **Description:** Job horaire détectant et comblant les gaps dans les séries OHLCV.
- **Acceptation:**
  - [ ] Job `reconciliation` lance toutes les heures
  - [ ] Detecte gaps : requête pour chaque symbol × timeframe, compare avec NOW()
  - [ ] Si gap détecté : relance `collect_ohlcv` pour cette paire
  - [ ] Log : "Gap detected for BTC/1h: 2026-03-12 14:00 to 16:00 — relaunching collector"
  - [ ] Max 3 retries + backoff exponentiel

---

## 5. REMÉDIATION AUDIT

### 5.1 Issues Critiques Sécurité (Audit S1-S3)

| ID | Issue | Remédiation | Responsable | Délai |
|----|-------|-----------|-------------|-------|
| S1 | Secrets hardcodés dans `config.py` | Supprimer defaults Pydantic, fail fast si manquant | Backend | 30 min |
| S2 | Credentials MLflow visibles dans `docker ps` | Passer via env vars, utiliser `docker secrets` (Swarm) | DevOps | 20 min |
| S3 | Defaults `admin:admin` MinIO | Forcer password fort, utiliser `openssl rand -base64 32` | DevOps | 45 min |

**Livrable S1-S3 :** `.env.example` avec placeholders `CHANGE_ME_*`, validation startup failure.

### 5.2 Issues Infrastructure DevOps (Audit D1-D2, D5)

| ID | Issue | Remédiation | Evidence |
|----|-------|-----------|----------|
| D1 | Images unpinnées (`:latest`, `:alpine`) | Pinner tous les tags (voir RF-INFRA-001) | `docker images` affiche versions exactes |
| D2 | Ansible `delete: true` destructif | Remplacer par `delete: false` + `exclude: [.env, ...]` | `deploy.yml` lines 16-26 |
| D5 | MinIO pas de backup | Job `backup.yml` avec `mc mirror` hebdo | Cron job `0 4 * * 0 ...` |
| D6 | Pas d'alertes Grafana | Créer 5+ règles alertes (CPU, mem, healthcheck, latency) | Grafana UI → Alerting → 5 rules |

### 5.3 Couverture de Tests ML (Audit T1-T3)

| ID | Issue | Remédiation | Test à ajouter |
|----|-------|-----------|-----------------|
| T1 | Code ML exclu couverture | Retirer exclusions `pyproject.toml` section `[tool.pytest.ini_options]` | `--cov=src` affiche ML % |
| T2 | WalkForwardBacktester non testé | Corriger import dans `test_backtesting.py` | `tests/unit/ml/test_backtesting.py` +15 tests |
| T3 | Test E2E pipeline signals absent | Ajouter E2E : ETL → ML → API → Frontend | `tests/e2e/test_signal_pipeline.py` |

**Résultat :** Couverture réelle passe de 65% à 85%+.

---

## 6. MATRICE DE TRAÇABILITÉ

### 6.1 Audit → Exigences Mapping

| Audit ID | Sévérité | RF-INFRA | RF-DATA | Status |
|----------|----------|----------|---------|--------|
| S1 | CRITICAL | RF-INFRA-001 (.env) | — | Remédiation Phase 1 |
| S2 | CRITICAL | RF-INFRA-011 (Nginx) | — | Remédiation Phase 1 |
| S3 | CRITICAL | RF-INFRA-022 (Deploy) | — | Remédiation Phase 1 |
| D1 | CRITICAL | RF-INFRA-001 (Images) | — | Remédiation Phase 1 |
| D2 | CRITICAL | RF-INFRA-022 (Ansible) | — | Remédiation Phase 1 |
| D3 | HIGH | RF-INFRA-023 (Rollback) | — | Remédiation Phase 2 |
| D5 | HIGH | RF-INFRA-025 (Backups) | RF-DATA-011 | Remédiation Phase 2 |
| D6 | HIGH | RF-INFRA-024 (Monitoring) | — | Remédiation Phase 2 |
| C1 | HIGH | RF-INFRA-022, RF-INFRA-023 | — | Remédiation Phase 2 |
| C2 | HIGH | RF-INFRA-001 | RF-DATA-001 | Remédiation Phase 2 |

### 6.2 Composantes Infrastructure vs Données

```
COMPOSANTES INFRASTRUCTURE (RF-INFRA)
├── Docker Compose (RF-INFRA-001 to 010)
├── Nginx & TLS (RF-INFRA-011 to 015)
├── CI/CD GitHub Actions (RF-INFRA-016 to 020)
├── Ansible Provisioning (RF-INFRA-021 to 023)
└── Monitoring & Backups (RF-INFRA-024 to 025)

COMPOSANTES DONNÉES (RF-DATA)
├── TimescaleDB Hypertables (RF-DATA-001 to 005)
├── Indicateurs Techniques (RF-DATA-006 to 010)
├── MinIO & Versioning (RF-DATA-011 to 013)
└── Qualité & Validation (RF-DATA-014 to 016)
```

---

## 7. PLAN D'IMPLÉMENTATION

### Phase 1 — BLOQUANTS (Semaine 1)

Critique pour exécution : security fixes + pinning images.

| # | Task | Durée | Responsable | RF-INFRA | RF-DATA |
|---|------|-------|-------------|----------|---------|
| P1.1 | Supprimer secrets hardcodés config.py | 30 min | Backend | — | — |
| P1.2 | MLflow : credentials en env vars | 20 min | DevOps | RF-INFRA-022 | — |
| P1.3 | MinIO : password validation obligatoire | 45 min | DevOps | RF-INFRA-022 | RF-DATA-011 |
| P1.4 | Pinner images Docker (tous les services) | 30 min | DevOps | RF-INFRA-001 | — |
| P1.5 | Corriger Ansible `delete: true` → `delete: false` | 15 min | DevOps | RF-INFRA-022 | — |
| P1.6 | Inclure code ML dans couverture tests | 1h | ML | — | — |
| P1.7 | Corriger import WalkForwardBacktester | 15 min | ML | — | — |
| P1.8 | Test E2E pipeline signaux complet | 2h | Transversal | RF-INFRA-016 | RF-DATA-014 |

**Livrables P1** : `.env` sécurisé, images pinnées, Ansible sûr, couverture tests 80%+ réelle.

### Phase 2 — AVANT PRODUCTION (Semaine 2-3)

Préparation déploiement production.

| # | Task | Durée | RF-INFRA | RF-DATA |
|---|------|-------|----------|---------|
| P2.1 | Configurer HTTPS Let's Encrypt (Nginx) | 1h | RF-INFRA-014 | — |
| P2.2 | Healthcheck validation sur tous services | 30 min | RF-INFRA-003 | — |
| P2.3 | Rate limiting Nginx (API + auth) | 15 min | RF-INFRA-012 | — |
| P2.4 | Headers de sécurité Nginx | 10 min | RF-INFRA-013 | — |
| P2.5 | Secrets GitHub configurés (VPS_IP, SSH_KEY) | 10 min | RF-INFRA-017 | — |
| P2.6 | Playbook `rollback.yml` + script rollback | 2h | RF-INFRA-023 | — |
| P2.7 | Backup job TimescaleDB + MinIO | 1h | RF-INFRA-025 | RF-DATA-011 |
| P2.8 | Migration Alembic TimescaleDB finalisée | 2h | RF-INFRA-016 | RF-DATA-001 to 005 |
| P2.9 | Runbook production (procédures incidents) | 2h | RF-INFRA-022 | — |
| P2.10 | Harmony PostgreSQL version (pg16) | 30 min | — | RF-DATA-001 |

**Livrables P2** : Production-ready infrastructure, HTTPS activé, backups opérationnels, runbook.

### Phase 3 — OPTIONNALISÉ (Semaine 4+)

Amélioration continue post-lancement.

| # | Task | Durée | RF-INFRA | RF-DATA |
|---|------|-------|----------|---------|
| P3.1 | Alertes Grafana (5+ rules) | 1h | RF-INFRA-024 | — |
| P3.2 | Dashboards Grafana (4 dashboards) | 1.5h | RF-INFRA-024 | — |
| P3.3 | Harmonic patterns detection (Gartley, Butterfly) | 2h | — | RF-DATA-009 |
| P3.4 | Trend lines calculator | 1h | — | RF-DATA-010 |
| P3.5 | Reconciliation job gaps OHLCV | 1h | — | RF-DATA-016 |
| P3.6 | CI/CD cache optimization (Docker layer caching) | 1h | RF-INFRA-016 | — |
| P3.7 | Node-exporter + cAdvisor (Linux monitoring) | 1h | RF-INFRA-024 | — |
| P3.8 | DVC integration ML datasets | 1h | — | RF-DATA-013 |

**Livrables P3** : Monitoring complet, indicateurs avancés, optimisation CI.

---

## ANNEXES

### Annexe A : Variables d'Environnement .env.example

```bash
# ===== DATABASE =====
POSTGRES_DB=cryptobot
POSTGRES_USER=cryptobot
POSTGRES_PASSWORD=CHANGE_ME_strong_password_here
DATABASE_URL=postgresql://cryptobot:CHANGE_ME@timescaledb:5432/cryptobot

# ===== MINIO (S3-compatible) =====
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=CHANGE_ME_strong_password_here
MINIO_ENDPOINT=http://minio:9000
MINIO_REGION=us-east-1

# ===== API =====
API_SECRET_KEY=CHANGE_ME_random_jwt_secret_here
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4
CORS_ORIGINS=http://localhost:3000,https://cryptobot.example.com

# ===== FRONTEND =====
API_URL=http://api:8000
STREAMLIT_SERVER_HEADLESS=true
STREAMLIT_SERVER_PORT=8501

# ===== EXTERNAL APIs =====
COINGECKO_API_KEY=your_demo_api_key_here
BINANCE_API_KEY=your_binance_public_key_here

# ===== MLFLOW =====
MLFLOW_TRACKING_URI=http://mlflow:5000
MLFLOW_S3_ENDPOINT_URL=http://minio:9000
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=CHANGE_ME

# ===== MONITORING (Grafana) =====
GF_SECURITY_ADMIN_USER=admin
GF_SECURITY_ADMIN_PASSWORD=CHANGE_ME_strong_password_here
GF_USERS_ALLOW_SIGN_UP=false

# ===== LOGGING =====
LOG_LEVEL=INFO
ENVIRONMENT=development  # ou production
```

### Annexe B : Checklist Déploiement Production

- [ ] Phase 1 bloquants terminés (secrets, images, Ansible)
- [ ] Phase 2 complété (HTTPS, backups, runbook)
- [ ] Tests : couverture ≥ 80%, E2E signaux passant
- [ ] Secrets GitHub créés (VPS_IP, SSH_KEY)
- [ ] Certbot certificat Let's Encrypt actif
- [ ] Playbook provision testé sur VPS vierge
- [ ] Playbook deploy testé sur environnement staging
- [ ] Rollback script testé (downtime < 5 min)
- [ ] Monitoring Grafana fonctionnel (≥3 dashboards)
- [ ] Backup TimescaleDB quotidien configuré (cron)
- [ ] Runbook production rédigé et signé par équipe
- [ ] DNS pointé, HTTPS actif, healthcheck vert
- [ ] Load initial (canary deploy) 10% utilisateurs 24h
- [ ] Passage 100% utilisateurs après validation

### Annexe C : Références Files

| Fichier | Description | Modificateur |
|---------|-----------|-------------|
| `docker-compose.yml` | Services tous, networks, volumes | DevOps |
| `src/api/Dockerfile` | Build API FastAPI | Backend |
| `src/etl/Dockerfile` | Build ETL worker | Data Eng |
| `src/ml/Dockerfile` | Build ML worker | ML |
| `src/frontend/Dockerfile` | Build Streamlit | Frontend |
| `infra/nginx/nginx.conf` | Config reverse proxy | DevOps |
| `.github/workflows/ci.yml` | Pipeline CI/CD | DevOps |
| `infra/ansible/playbooks/provision.yml` | Setup VPS | DevOps |
| `infra/ansible/playbooks/deploy.yml` | Deploy app | DevOps |
| `infra/ansible/playbooks/backup.yml` | Backup strategy | DevOps |
| `src/etl/migrations/` | Alembic migrations | Data Eng |
| `src/shared/models/` | Pydantic models | All teams |
| `.env.example` | Template secrets | DevOps |

---

**Fin du document CDC Infrastructure & Données**

Statut : COMPLET (v2.1)  
Applicable immédiatement après Audit Remédiation Phase 1-2.

