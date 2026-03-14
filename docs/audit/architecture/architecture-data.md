# Architecture des Données — Crypto Bot

**Version:** 2.0
**Date:** 2026-03-12
**Auteur:** Équipe Data Engineering
**Périmètre:** TimescaleDB, MinIO, ETL Pipeline, Modèles de Données
**Audience:** Équipes Data Engineering, ML, Backend, DevOps

---

## 1. Architecture Générale des Données

### 1.1 Flux de Données Complet

```
┌──────────────────────────────────────────────────────────────────────────┐
│                      SOURCES EXTERNES (libres)                           │
├──────────────────────────────────────────────────────────────────────────┤
│ Binance Public API + WebSocket | CoinGecko Demo | CCXT | News RSS        │
│ Alternative.me (Fear & Greed)  | Decrypt, Cointelegraph (scraping)      │
└──────────────────┬───────────────────────────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                   EXTRACT (Collecte via APScheduler)                     │
├──────────────────────────────────────────────────────────────────────────┤
│ src/etl/collectors/binance.py       → OHLCV temps réel + historique     │
│ src/etl/collectors/coingecko.py     → Métadonnées, rankings              │
│ src/etl/collectors/ccxt_collector.py → Multi-exchanges fallback          │
│ src/etl/collectors/news.py          → Articles de news + scraping        │
│ src/etl/collectors/fear_greed.py    → Indices de peur/confiance          │
└──────────────────┬───────────────────────────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────────────────────────┐
│              VALIDATE (Validation Pydantic + Déduplication)              │
├──────────────────────────────────────────────────────────────────────────┤
│ OHLCVRecord validation : contraintes OHLCV (high ≥ open, close, low)   │
│ Volume ≥ 0, pas de NaN                                                  │
│ Déduplication par (symbol, timeframe, timestamp)                        │
│ Détection de gaps (données manquantes)                                  │
└──────────────────┬───────────────────────────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────────────────────────┐
│         TRANSFORM (Calcul Indicateurs, Nettoyage, Normalisation)        │
├──────────────────────────────────────────────────────────────────────────┤
│ RSI multi-timeframe (1h, 2h, 3h, 4h, 1D) via pandas-ta/ta-lib           │
│ Bollinger Bands (MA20, 2σ) + position relative du prix                  │
│ Harmonic patterns (Gartley, Butterfly, Crab, Bat)                      │
│ Trend lines + slope computation                                         │
│ Vérification cohérence temporelle                                       │
└──────────────────┬───────────────────────────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                 LOAD (Insertion TimescaleDB + MinIO)                    │
├──────────────────────────────────────────────────────────────────────────┤
│ crypto_prices (hypertable) ← OHLCV validé                               │
│ indicators ← indicateurs techniques calculés                            │
│ news_articles ← articles avec sentiment scores                          │
│ MinIO (raw/, datasets/) ← fichiers Parquet/CSV pour ML                  │
│ → Batch inserts, compression TimescaleDB après 7j, rétention 90j       │
└──────────────────┬───────────────────────────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────────────────────────┐
│     ML ENGINE + BACKEND API (Consomment les données TimescaleDB)        │
├──────────────────────────────────────────────────────────────────────────┤
│ trading_signals ← générés par l'équipe ML                               │
│ signal_outcomes ← évaluation post-hoc des signaux                       │
│ L'API expose les données aux utilisateurs via Streamlit                 │
└──────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Choix Architecturaux

#### TimescaleDB vs PostgreSQL vanilla

| Critère | TimescaleDB | PostgreSQL vanilla |
|---------|-------------|-------------------|
| **Hypertables temporelles** | Partitionnement automatique par time_interval | Nécessite manual partitioning |
| **Compression** | 10-100x compression après N jours (déterministe) | Impossible |
| **Continuous aggregates** | Agrégations pré-calculées, refresh incrémentiels | Nécessite views matérialisées |
| **Retention policies** | Auto-suppression des données expirées | Trigger manuel |
| **Query optimizer** | Optimisation pour séries temporelles (pruning) | Requêtes standard |
| **Scale** | Billions de points / millions d'INSERT/s | Limité à millions de points |

**Décision:** TimescaleDB pour la table `crypto_prices` (séries temporelles massives) + PostgreSQL standard pour les autres tables (utilisateurs, signaux, portfolio).

#### MinIO vs S3 AWS

| Critère | MinIO | S3 AWS |
|---------|-------|--------|
| **Coût** | Gratuit, self-hosted | $ par Go stocké + transfert |
| **Compatibilité** | 100% S3-compatible API | Standard |
| **Déploiement** | Docker container (1h) | Compte AWS + IAM config |
| **Contrôle** | Complet (données on-premise) | Délégué à AWS |

**Décision:** MinIO pour V1 (self-hosted, libre, ML friendly). Migration vers S3 possible en changeant juste l'endpoint.

#### No MongoDB — JSONB PostgreSQL instead

| Critère | JSONB PostgreSQL | MongoDB |
|---------|------------------|---------|
| **Typage** | Colonne JSONB = semi-structuré + typage SQL | Document collection = no schema |
| **Transactions** | ACID transactions across tables | Eventual consistency |
| **Queryability** | `WHERE metadata->>'key' = value` (indexed) | Query syntax different |
| **Backup** | `pg_dump` = simple | Snapshot-based |
| **Coût** | Inclus dans PostgreSQL | $ + complexity |

**Décision:** Utiliser `metadata JSONB` dans `indicators` et `trading_signals` pour les données non-structurées, pas de MongoDB séparé.

---

## 2. Schéma TimescaleDB Détaillé

### 2.1 DDL Complet et Commentaires

```sql
-- ============================================================
-- EXTENSION : TimescaleDB (pour hypertables)
-- ============================================================
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- ============================================================
-- TABLE : users (Authentification)
-- Gérée par l'équipe Backend via les services API
-- ============================================================
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL, -- bcrypt(password, rounds=12)
    persona_type VARCHAR(20) NOT NULL DEFAULT 'trader'
        CHECK (persona_type IN ('trader', 'journalist', 'investor')),
    preferences JSONB NOT NULL DEFAULT '{}', -- user-configurable preferences
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT ck_username_length CHECK (LENGTH(username) >= 3),
    CONSTRAINT ck_email_valid CHECK (email ~ '^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
);

-- Indices
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);

-- ============================================================
-- HYPERTABLE : crypto_prices (Séries temporelles OHLCV)
-- Partitionnée par timestamp, compressée après 7j, rétention 90j
-- ============================================================
CREATE TABLE crypto_prices (
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,  -- 1m, 5m, 1h, 2h, 3h, 4h, 1D, 1W, 1M
    timestamp TIMESTAMPTZ NOT NULL,
    price_open NUMERIC(20, 8) NOT NULL,   -- Open price
    price_high NUMERIC(20, 8) NOT NULL,   -- Highest price in period
    price_low NUMERIC(20, 8) NOT NULL,    -- Lowest price in period
    price_close NUMERIC(20, 8) NOT NULL,  -- Close price
    volume_24h NUMERIC(20, 8) NOT NULL,   -- Trading volume
    market_cap NUMERIC(20, 2),            -- Market capitalization (optional)
    source VARCHAR(50) NOT NULL,          -- binance, coingecko, ccxt, etc.

    PRIMARY KEY (symbol, timeframe, timestamp),

    CONSTRAINT ck_prices_high_low CHECK (price_high >= price_low),
    CONSTRAINT ck_prices_volume_positive CHECK (volume_24h >= 0),
    CONSTRAINT ck_price_within_range CHECK (price_open BETWEEN price_low AND price_high),
    CONSTRAINT ck_price_close_within_range CHECK (price_close BETWEEN price_low AND price_high)
);

-- Créer l'hypertable TimescaleDB (automatiquement partitionnée par timestamp)
SELECT create_hypertable('crypto_prices', 'timestamp',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => true);

-- Compression : après 7 jours, compresser les chunks anciens
-- Résultat : ~10-50x reduction de taille disque pour données historiques
ALTER TABLE crypto_prices SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'symbol, timeframe',
    timescaledb.compress_orderby = 'timestamp DESC'
);

SELECT add_compression_policy('crypto_prices',
    INTERVAL '7 days',
    if_not_exists => true);

-- Retention : supprimer les données > 90 jours
-- (Garder ~3 mois historiques pour backtest et rétrospectives)
SELECT add_retention_policy('crypto_prices',
    INTERVAL '90 days',
    if_not_exists => true);

-- Indices pour requêtes courantes
CREATE INDEX idx_prices_symbol_timeframe_ts
    ON crypto_prices (symbol, timeframe, timestamp DESC);
CREATE INDEX idx_prices_timestamp
    ON crypto_prices (timestamp DESC);
CREATE INDEX idx_prices_symbol
    ON crypto_prices (symbol);

-- ============================================================
-- TABLE : indicators (Indicateurs techniques pré-calculés)
-- Calculée par l'équipe Data Engineering
-- ============================================================
CREATE TABLE indicators (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,

    -- RSI (Relative Strength Index) — plage [0, 100]
    rsi NUMERIC(10, 4),

    -- Bandes de Bollinger (MA 20, 2 écarts-types)
    bollinger_upper NUMERIC(20, 8),
    bollinger_middle NUMERIC(20, 8),
    bollinger_lower NUMERIC(20, 8),

    -- Position relative du prix dans les bandes [-1, 1]
    -- -1 = au lower band, 0 = au middle (MA), 1 = au upper band
    price_vs_bollinger NUMERIC(10, 6),

    -- Pattern harmonique détecté (Gartley, Butterfly, Crab, Bat)
    harmonic_pattern VARCHAR(50),

    -- Pente de la trend line (coefficient slope)
    trend_slope NUMERIC(10, 6),

    -- Classification de trend : stable, aggressive, neutral
    trend_type VARCHAR(20),

    -- Données non-structurées supplémentaires (JSON)
    -- Ex: {"volume_ratio": 1.3, "wave_count": 5, "confluence_score": 0.85}
    metadata JSONB NOT NULL DEFAULT '{}',

    UNIQUE (symbol, timeframe, timestamp),

    CONSTRAINT ck_rsi_range CHECK (rsi IS NULL OR (rsi >= 0 AND rsi <= 100)),
    CONSTRAINT ck_price_vs_bollinger_range CHECK (price_vs_bollinger IS NULL OR (price_vs_bollinger >= -1 AND price_vs_bollinger <= 1))
);

-- Indices
CREATE INDEX idx_indicators_symbol_tf_ts
    ON indicators (symbol, timeframe, timestamp DESC);
CREATE INDEX idx_indicators_harmonic
    ON indicators (harmonic_pattern)
    WHERE harmonic_pattern IS NOT NULL;

-- ============================================================
-- TABLE : trading_signals (Signaux générés par l'équipe ML)
-- Signaux informatifs uniquement — PAS d'exécution automatique
-- ============================================================
CREATE TABLE trading_signals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol VARCHAR(20) NOT NULL,
    signal_type VARCHAR(10) NOT NULL
        CHECK (signal_type IN ('BUY', 'SELL', 'HOLD')),
    confidence_score NUMERIC(5, 4) NOT NULL -- [0.0, 1.0]
        CHECK (confidence_score >= 0 AND confidence_score <= 1),
    timeframe_primary VARCHAR(10) NOT NULL,

    -- État des indicateurs par timeframe
    -- Ex: {"1h": {"rsi": 68, "bb_position": 0.8}, "4h": {"rsi": 70}}
    timeframes_aligned JSONB NOT NULL DEFAULT '{}',

    -- Règles qui ont déclenché le signal
    -- Ex: ["rsi_overbought_multi_tf", "bollinger_squeeze"]
    rules_triggered JSONB NOT NULL DEFAULT '[]',

    -- Levier suggéré (vérifier règle 2x margin)
    leverage_suggested INTEGER CHECK (leverage_suggested IS NULL OR (leverage_suggested >= 1 AND leverage_suggested <= 20)),

    -- Sécurité margin minimum (toujours >= 2x notional)
    margin_safety NUMERIC(10, 4),

    -- Frais estimés (maker + taker + funding rate)
    fees_estimated NUMERIC(10, 6),

    -- Version du modèle : rules_v1, xgboost_v2, lstm_v1, etc.
    model_version VARCHAR(50) NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Contrainte métier : émettre seulement si confidence >= 0.6
    CONSTRAINT ck_confidence_threshold CHECK (confidence_score >= 0.6)
);

-- Indices
CREATE INDEX idx_signals_symbol_created
    ON trading_signals (symbol, created_at DESC);
CREATE INDEX idx_signals_confidence
    ON trading_signals (confidence_score DESC);
CREATE INDEX idx_signals_timestamp
    ON trading_signals (created_at DESC);

-- ============================================================
-- TABLE : signal_outcomes (Évaluation post-hoc des signaux)
-- Remplie par un job ETL qui évalue les signaux après 1h, 4h, 1j
-- ============================================================
CREATE TABLE signal_outcomes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    signal_id UUID NOT NULL REFERENCES trading_signals(id) ON DELETE CASCADE,

    -- Prix au moment du signal
    price_at_signal NUMERIC(20, 8) NOT NULL,

    -- Prix observé après X temps
    price_after_1h NUMERIC(20, 8),
    price_after_4h NUMERIC(20, 8),
    price_after_1d NUMERIC(20, 8),

    -- P&L simulé (si le signal avait été suivi)
    -- PnL = (price_after - price_at_signal) / price_at_signal * leverage
    pnl_simulated NUMERIC(10, 4),

    -- True si la direction prédite a été correcte
    was_correct BOOLEAN,

    evaluated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indices
CREATE INDEX idx_outcomes_signal_id
    ON signal_outcomes (signal_id);
CREATE INDEX idx_outcomes_evaluated
    ON signal_outcomes (evaluated_at DESC);

-- ============================================================
-- TABLE : portfolio (Positions de l'utilisateur)
-- Suivi des cryptos détenues par chaque utilisateur
-- ============================================================
CREATE TABLE portfolio (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    symbol VARCHAR(20) NOT NULL,
    quantity NUMERIC(20, 8) NOT NULL,  -- Nombre de pièces/tokens
    entry_price NUMERIC(20, 8) NOT NULL, -- Prix d'entrée
    current_price NUMERIC(20, 8),      -- Prix actuel (MAJ par ETL)
    notes TEXT,                        -- Notes utilisateur
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT ck_quantity_positive CHECK (quantity > 0),
    CONSTRAINT ck_entry_price_positive CHECK (entry_price > 0),
    UNIQUE (user_id, symbol) -- Un seul position par symbol par utilisateur
);

-- Indices
CREATE INDEX idx_portfolio_user_id ON portfolio(user_id);
CREATE INDEX idx_portfolio_symbol ON portfolio(symbol);

-- ============================================================
-- TABLE : watchlist (Cryptos suivies par l'utilisateur)
-- Relations many-to-many : utilisateurs ↔ symboles à surveiller
-- ============================================================
CREATE TABLE watchlist (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    symbol VARCHAR(20) NOT NULL,
    added_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (user_id, symbol) -- Pas de doublons
);

-- Indices
CREATE INDEX idx_watchlist_user_id ON watchlist(user_id);
CREATE INDEX idx_watchlist_symbol ON watchlist(symbol);

-- ============================================================
-- TABLE : news_articles (Articles de news / veille)
-- Collectée par scraping (Decrypt, Cointelegraph) ou API
-- ============================================================
CREATE TABLE news_articles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(500) NOT NULL,
    content TEXT,
    source VARCHAR(100) NOT NULL, -- decrypt, cointelegraph, etc.
    url VARCHAR(1000) UNIQUE NOT NULL,
    published_at TIMESTAMPTZ,

    -- Sentiment score [-1 (négatif) à 1 (positif)]
    sentiment_score NUMERIC(5, 4) CHECK (sentiment_score IS NULL OR (sentiment_score >= -1 AND sentiment_score <= 1)),

    -- Mots-clés extraits (array JSONB)
    keywords JSONB NOT NULL DEFAULT '[]',

    -- Score de fiabilité [0, 1] basé sur la source
    reliability_score NUMERIC(5, 4),

    collected_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indices
CREATE INDEX idx_news_source ON news_articles(source);
CREATE INDEX idx_news_published ON news_articles(published_at DESC);
CREATE INDEX idx_news_sentiment ON news_articles(sentiment_score);
CREATE INDEX idx_news_keywords ON news_articles USING GIN (keywords);

-- ============================================================
-- TABLE : text_mining_results (Analyse de texte post-collecte)
-- Word clouds, résumés, NER (Named Entity Recognition), topics
-- ============================================================
CREATE TABLE text_mining_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    article_id UUID NOT NULL REFERENCES news_articles(id) ON DELETE CASCADE,

    -- Word cloud : fréquences des mots importants
    -- Ex: {"bitcoin": 10, "ethereum": 8, "crypto": 15}
    word_cloud JSONB NOT NULL DEFAULT '{}',

    -- Résumé automatique de l'article
    summary TEXT,

    -- Entités nommées extraites (symboles, personnalités, etc.)
    -- Ex: [{"text": "Bitcoin", "type": "CRYPTO"}, {"text": "SEC", "type": "ORG"}]
    entities JSONB NOT NULL DEFAULT '[]',

    -- Topics détectés (LDA, clustering, etc.)
    -- Ex: ["regulation", "market_analysis", "security"]
    topics JSONB NOT NULL DEFAULT '[]',

    processed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indices
CREATE INDEX idx_text_mining_article ON text_mining_results(article_id);
CREATE INDEX idx_text_mining_topics ON text_mining_results USING GIN (topics);

-- ============================================================
-- VUES UTILES (pour requêtes courantes)
-- ============================================================

-- Vue : Dernières données OHLCV par timeframe et symbole
CREATE OR REPLACE VIEW v_latest_prices AS
SELECT DISTINCT ON (symbol, timeframe)
    symbol, timeframe, timestamp,
    price_open, price_high, price_low, price_close, volume_24h
FROM crypto_prices
ORDER BY symbol, timeframe, timestamp DESC;

-- Vue : Indicateurs + signaux combinés (pour le dashboard)
CREATE OR REPLACE VIEW v_signal_readiness AS
SELECT
    s.symbol,
    s.timeframe_primary,
    COUNT(ind.id) as indicator_count,
    MAX(s.created_at) as latest_signal_at,
    s.signal_type,
    s.confidence_score
FROM trading_signals s
LEFT JOIN indicators ind ON s.symbol = ind.symbol AND ind.timestamp >= (NOW() - INTERVAL '24 hours')
GROUP BY s.symbol, s.timeframe_primary, s.signal_type, s.confidence_score;
```

### 2.2 Propriétés TimescaleDB

#### Hypertable `crypto_prices`

- **Partitionnement:** Automatique par `timestamp`, chunks de 1 jour
- **Compression:** Activée après 7 jours → ~50x reduction
- **Retention:** 90 jours max (suppression auto après)
- **Unique constraint:** (symbol, timeframe, timestamp)
- **Deduplication:** ETL garantit pas d'insertion double via upsert

#### Autres tables

- **Regular tables:** users, indicators, trading_signals, portfolio, watchlist, news_articles, text_mining_results
- **Foreign keys:** avec ON DELETE CASCADE (cohérence référentielle)
- **Constraints:** CHECK pour domaines (price_high >= price_low, confidence in [0,1])

---

## 3. MinIO — Architecture de Stockage d'Objets

### 3.1 Structure des Buckets

```
minio-instance/
├── raw/                          # Données brutes (write-once, never modify)
│   ├── binance/
│   │   └── ohlcv_YYYY-MM-DD/
│   │       ├── BTC_1m.parquet
│   │       ├── BTC_5m.parquet
│   │       └── ...
│   ├── coingecko/
│   │   └── metadata/
│   │       └── coins_YYYY-MM-DD.json
│   └── news/
│       └── articles_YYYY-MM-DD.parquet
│
├── datasets/                     # Datasets préparés pour ML (read by ML team)
│   ├── features_YYYYMMDD.parquet      # Features pour le training
│   ├── labels_YYYYMMDD.parquet        # Labels (direction, PnL)
│   ├── test_split_YYYYMMDD.parquet    # Test set (temporal, purged)
│   └── train_split_YYYYMMDD.parquet   # Train set (avec embargo)
│
├── models/                       # Modèles entraînés (write by ML team)
│   ├── xgboost_v1_model.pkl
│   ├── xgboost_v1_scaler.pkl
│   ├── lstm_v2_weights.h5
│   └── ...
│
├── mlflow-artifacts/             # Gérés par MLflow (experiments, metrics)
│   └── ...
│
└── exports/                      # Rapports, figures, backups
    ├── backtest_results_YYYYMMDD.html
    ├── signal_performance_YYYYMMDD.csv
    └── dashboard_snapshot.png
```

### 3.2 Conventions de Nommage des Objets

**Format standard:** `{bucket}/{category}/{symbol_or_type}/{date}/{filename}`

**Exemples:**
- `raw/binance/ohlcv_2026-03-12/BTC_1h.parquet` — OHLCV Binance BTC 1h, date 2026-03-12
- `raw/news/articles_2026-03-12.parquet` — Tous les articles du jour
- `datasets/features_2026-03-12.parquet` — Features générées pour le ML
- `models/xgboost_v1/model.pkl` — Modèle XGBoost version 1
- `exports/backtest_2026-03-01_2026-03-12.html` — Rapport backtest période donnée

### 3.3 Politiques de Cycle de Vie (Lifecycle)

```json
{
  "Rules": [
    {
      "ID": "delete-raw-after-30d",
      "Status": "Enabled",
      "Filter": { "Prefix": "raw/" },
      "Expiration": { "Days": 30 },
      "NoncurrentVersionExpiration": { "NoncurrentDays": 7 }
    },
    {
      "ID": "archive-exports-after-90d",
      "Status": "Enabled",
      "Filter": { "Prefix": "exports/" },
      "Expiration": { "Days": 90 }
    }
  ]
}
```

**Rationale:**
- `raw/` : supprimer après 30j (données historiques disponibles dans TimescaleDB)
- `datasets/` : garder 6 mois (trail for audits + réentraînement possible)
- `models/` : garder indefiniment (backups critical)
- `mlflow-artifacts/` : garder avec policy de rétention MLflow (par défaut 30j)

### 3.4 Accès et Sécurité

```python
# src/shared/config.py — Configuration d'accès MinIO

minio_endpoint = "minio:9000"  # Docker internal
minio_root_user = "minioadmin"  # À changer en prod
minio_root_password = "minioadmin"  # À changer en prod

# Initialisation client MinIO
from minio import Minio

client = Minio(
    minio_endpoint,
    access_key=minio_root_user,
    secret_key=minio_root_password,
    secure=False  # True en prod avec HTTPS
)

# Créer buckets
buckets = ["raw", "datasets", "models", "mlflow-artifacts", "exports"]
for bucket in buckets:
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)
```

---

## 4. Modèles de Données Détaillés

### 4.1 OHLCVRecord (Pydantic v2)

```python
# src/shared/models/crypto.py

from pydantic import BaseModel, ConfigDict, Field, model_validator
from decimal import Decimal
from datetime import datetime

class OHLCVRecord(BaseModel):
    """Données OHLCV pour une crypto sur un timeframe donné.

    Utilisé par ALL teams pour validation et sérialisation.
    """
    model_config = ConfigDict(frozen=True)

    symbol: str = Field(
        ...,
        description="Paire de trading, ex. BTCUSDT, ETHUSDT",
        min_length=3,
        max_length=20
    )
    price_open: Decimal = Field(..., description="Prix d'ouverture", gt=0)
    price_high: Decimal = Field(..., description="Prix le plus haut", gt=0)
    price_low: Decimal = Field(..., description="Prix le plus bas", gt=0)
    price_close: Decimal = Field(..., description="Prix de fermeture", gt=0)
    volume_24h: Decimal = Field(..., description="Volume sur 24h", ge=0)
    market_cap: Decimal | None = Field(None, description="Capitalisation marché (optionnel)")
    timestamp: datetime = Field(..., description="UTC timestamp du prix")
    source: str = Field(..., description="Source: binance, coingecko, ccxt, etc.")
    timeframe: str = Field(
        ...,
        description="Interval de la bougie",
        pattern="^(1m|5m|15m|1h|2h|3h|4h|1D|1W|1M)$"
    )

    @model_validator(mode="after")
    def validate_ohlcv_constraints(self) -> "OHLCVRecord":
        """Vérifier les contraintes logiques des OHLCV."""
        # High doit être >= Open, Close, Low
        if self.price_high < max(self.price_open, self.price_close, self.price_low):
            raise ValueError(
                f"price_high ({self.price_high}) must be >= "
                f"max(open={self.price_open}, close={self.price_close}, low={self.price_low})"
            )
        # Low doit être <= Open, Close, High
        if self.price_low > min(self.price_open, self.price_close, self.price_high):
            raise ValueError(
                f"price_low ({self.price_low}) must be <= "
                f"min(open={self.price_open}, close={self.price_close}, high={self.price_high})"
            )
        # Volume doit être >= 0
        if self.volume_24h < 0:
            raise ValueError(f"volume_24h cannot be negative: {self.volume_24h}")
        return self
```

### 4.2 IndicatorRecord (Pydantic v2)

```python
# src/shared/models/crypto.py

class IndicatorRecord(BaseModel):
    """Indicateurs techniques pré-calculés pour une crypto sur un timeframe."""
    model_config = ConfigDict(frozen=True)

    symbol: str
    timeframe: str
    timestamp: datetime

    # RSI (Relative Strength Index) — plage [0, 100]
    rsi: Decimal | None = Field(
        None,
        description="RSI value [0, 100]",
        ge=0,
        le=100
    )

    # Bandes de Bollinger
    bollinger_upper: Decimal | None = Field(None, description="Upper Bollinger Band")
    bollinger_middle: Decimal | None = Field(None, description="Middle (SMA 20)")
    bollinger_lower: Decimal | None = Field(None, description="Lower Bollinger Band")

    # Position relative [-1, 1]
    price_vs_bollinger: Decimal | None = Field(
        None,
        description="Position du prix dans les bandes (-1=lower, 0=middle, 1=upper)",
        ge=-1,
        le=1
    )

    # Harmonic pattern
    harmonic_pattern: str | None = Field(
        None,
        description="Pattern détecté: Gartley, Butterfly, Crab, Bat"
    )

    # Trend
    trend_slope: Decimal | None = Field(None, description="Pente de la trend line")
    trend_type: str | None = Field(None, description="stable, aggressive, neutral")

    # Données non-structurées
    metadata: dict = Field(
        default_factory=dict,
        description="Données additionnelles JSON"
    )
```

### 4.3 TradingSignal (Pydantic v2)

```python
# src/shared/models/signal.py

from typing import Literal

class TradingSignal(BaseModel):
    """Signal de trading informatif (PAS d'exécution automatique)."""
    model_config = ConfigDict(frozen=True)

    symbol: str
    signal_type: Literal["BUY", "SELL", "HOLD"]
    confidence_score: Decimal = Field(
        ...,
        description="Confiance [0, 1], seuil d'émission >= 0.6",
        ge=0,
        le=1
    )
    timeframe_primary: str = Field(..., description="Timeframe principal")

    # État des indicateurs par timeframe
    timeframes_aligned: dict = Field(
        default_factory=dict,
        description='{"1h": {"rsi": 68}, "4h": {"rsi": 70}}'
    )

    # Règles déclenchées
    rules_triggered: list[str] = Field(
        default_factory=list,
        description="Noms des règles qui ont déclenché ce signal"
    )

    leverage_suggested: int | None = Field(
        None,
        description="Levier suggéré (1-20)",
        ge=1,
        le=20
    )

    margin_safety: Decimal | None = Field(
        None,
        description="Facteur de sécurité margin (minimum 2x)"
    )

    fees_estimated: Decimal | None = Field(None, description="Frais estimés")

    model_version: str = Field(..., description="rules_v1, xgboost_v2, etc.")

    created_at: datetime | None = None
```

### 4.4 NewsArticle (Pydantic v2)

```python
# src/shared/models/crypto.py

class NewsArticle(BaseModel):
    """Article de news collecté via scraping ou API."""
    model_config = ConfigDict(frozen=True)

    title: str = Field(..., min_length=5, max_length=500)
    content: str | None = None
    source: str = Field(..., description="decrypt, cointelegraph, etc.")
    url: str = Field(..., description="URL unique de l'article")
    published_at: datetime | None = None

    # Sentiment [-1, 1]
    sentiment_score: Decimal | None = Field(
        None,
        description="Sentiment [-1 négatif, 1 positif]",
        ge=-1,
        le=1
    )

    keywords: list[str] = Field(default_factory=list, description="Mots-clés extraits")

    reliability_score: Decimal | None = Field(
        None,
        description="Score de fiabilité de la source [0, 1]",
        ge=0,
        le=1
    )
```

---

## 5. Flux de Données Détaillés — ETL Pipeline

### 5.1 Architecture ETL

```
Worker ETL (Docker Container)
│
├─ APScheduler (ordonnanceur de jobs)
│   ├─ collect_ohlcv (toutes les minutes pour top cryptos, 5 min pour autres)
│   ├─ collect_market_data (toutes les 5 min)
│   ├─ collect_news (toutes les 15 min)
│   ├─ collect_fear_greed (chaque heure)
│   ├─ compute_indicators (après collect_ohlcv)
│   ├─ export_datasets (quotidien 3h UTC)
│   └─ reconciliation (chaque heure — détecte et comble les gaps)
│
└─ Collecteurs (src/etl/collectors/)
    ├─ binance.py → API REST + WebSocket
    ├─ coingecko.py → API Demo (gratuite, rate-limité)
    ├─ ccxt_collector.py → Multi-exchange fallback
    ├─ news.py → Scraping + APIs
    └─ fear_greed.py → Alternative.me API
```

### 5.2 Pipeline Complet pour OHLCV

```python
# src/etl/jobs.py (Orchestration simplifiée)

async def collect_ohlcv_job() -> None:
    """Tâche planifiée: collecte OHLCV Binance + validation + insertion."""

    # EXTRACT
    collector = BinanceCollector()
    raw_ohlcv = await collector.fetch_ohlcv(
        symbols=settings.tracked_symbols,
        timeframes=['1h', '4h', '1D']
    )
    # raw_ohlcv = [{"symbol": "BTC", "timestamp": ..., "o": 45000, "h": 45500, ...}, ...]

    # VALIDATE (Pydantic)
    records = []
    validation_errors = []
    for raw in raw_ohlcv:
        try:
            record = OHLCVRecord(
                symbol=raw['symbol'],
                price_open=Decimal(str(raw['o'])),
                price_high=Decimal(str(raw['h'])),
                price_low=Decimal(str(raw['l'])),
                price_close=Decimal(str(raw['c'])),
                volume_24h=Decimal(str(raw['v'])),
                timestamp=datetime.fromisoformat(raw['timestamp']),
                source='binance',
                timeframe='1h'
            )
            records.append(record)
        except ValidationError as e:
            validation_errors.append({"raw": raw, "error": str(e)})
            logger.warning(f"Validation failed for {raw}: {e}")

    # Logging
    logger.info(f"Collected {len(records)} valid records, {len(validation_errors)} failed")

    # TRANSFORM (Deduplication)
    async with AsyncSession(engine) as session:
        # Vérifier ce qui existe déjà en DB
        existing_keys = set()
        for record in records:
            stmt = select(crypto_prices).where(
                (crypto_prices.symbol == record.symbol) &
                (crypto_prices.timeframe == record.timeframe) &
                (crypto_prices.timestamp == record.timestamp)
            )
            result = await session.execute(stmt)
            if result.scalar():
                existing_keys.add((record.symbol, record.timeframe, record.timestamp))

        # Filtrer les doublons
        new_records = [r for r in records if (r.symbol, r.timeframe, r.timestamp) not in existing_keys]
        logger.info(f"Deduplicated: {len(new_records)} new, {len(existing_keys)} already exist")

        # LOAD (Batch insert)
        if new_records:
            stmt = insert(crypto_prices).values([r.model_dump() for r in new_records])
            await session.execute(stmt)
            await session.commit()
            logger.info(f"Inserted {len(new_records)} OHLCV records")

# Enregistrer dans APScheduler
scheduler.add_job(
    collect_ohlcv_job,
    'interval',
    minutes=1,  # Top 13 cryptos every min
    id='collect_ohlcv',
    max_instances=1,  # Pas de parallélisme
    misfire_grace_time=30
)
```

### 5.3 Indicateurs Techniques — Computation

```python
# src/etl/transformers/indicators.py

async def compute_indicators_job() -> None:
    """Tâche planifiée: calcul des indicateurs techniques après chaque collect_ohlcv."""

    async with AsyncSession(engine) as session:
        # Récupérer les dernières OHLCV (dernières 200 bougies par symbol/tf)
        symbols_and_tfs = [
            ("BTC", "1h"), ("BTC", "4h"), ("BTC", "1D"),
            ("ETH", "1h"), ("ETH", "4h"), ("ETH", "1D"),
            # ... 13 cryptos × 5 timeframes
        ]

        for symbol, timeframe in symbols_and_tfs:
            # Fetch OHLCV
            stmt = (
                select(crypto_prices)
                .where(crypto_prices.symbol == symbol)
                .where(crypto_prices.timeframe == timeframe)
                .order_by(crypto_prices.timestamp.desc())
                .limit(200)
            )
            result = await session.execute(stmt)
            ohlcv_data = result.scalars().all()

            if len(ohlcv_data) < 20:  # Pas assez de données
                logger.warning(f"Not enough data for {symbol} {timeframe}")
                continue

            # Convertir en DataFrame
            df = pd.DataFrame([
                {
                    'open': o.price_open,
                    'high': o.price_high,
                    'low': o.price_low,
                    'close': o.price_close,
                    'volume': o.volume_24h,
                    'timestamp': o.timestamp
                }
                for o in ohlcv_data
            ]).sort_values('timestamp')

            # Calcul des indicateurs (ta-lib ou pandas-ta)
            try:
                # RSI (Relative Strength Index, period=14)
                df['rsi'] = ta.momentum.rsi(df['close'], window=14)

                # Bollinger Bands (MA=20, std=2)
                bb = ta.volatility.bollinger_bands(df['close'], window=20, window_dev=2)
                df['bb_upper'] = bb.iloc[:, 2]  # Upper band
                df['bb_middle'] = bb.iloc[:, 0]  # SMA
                df['bb_lower'] = bb.iloc[:, 1]  # Lower band

                # Position relative dans les bandes
                df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
                df['bb_position'] = df['bb_position'].clip(-1, 1)  # Normalize to [-1, 1]

                # Harmonic patterns (custom detection via geometric patterns)
                # ... logique de détection des patterns harmoniques

                # Trend line (linear regression slope)
                trend_x = np.arange(len(df))
                trend_slope, _ = np.polyfit(trend_x, df['close'].values, 1)

                # Stocker le dernier calculé
                latest = df.iloc[-1]

                # INSERT ou UPDATE dans indicators
                indicator = IndicatorRecord(
                    symbol=symbol,
                    timeframe=timeframe,
                    timestamp=latest['timestamp'],
                    rsi=Decimal(str(latest['rsi'])) if pd.notna(latest['rsi']) else None,
                    bollinger_upper=Decimal(str(latest['bb_upper'])),
                    bollinger_middle=Decimal(str(latest['bb_middle'])),
                    bollinger_lower=Decimal(str(latest['bb_lower'])),
                    price_vs_bollinger=Decimal(str(latest['bb_position'])),
                    harmonic_pattern=None,  # TODO: implement detection
                    trend_slope=Decimal(str(trend_slope)),
                    trend_type='stable' if abs(trend_slope) < 0.01 else 'aggressive'
                )

                stmt = insert(indicators).values(indicator.model_dump())
                stmt = stmt.on_conflict_do_update(
                    index_elements=['symbol', 'timeframe', 'timestamp'],
                    set_=stmt.excluded
                )
                await session.execute(stmt)

            except Exception as e:
                logger.error(f"Failed to compute indicators for {symbol} {timeframe}: {e}")

        await session.commit()
```

### 5.4 Qualité des Données — Validation et Réconciliation

```python
# src/etl/jobs.py

async def reconciliation_job() -> None:
    """Tâche horaire: détection des gaps, alertes staleness."""

    async with AsyncSession(engine) as session:
        # 1. Détection de gaps dans les OHLCV
        gaps_detected = []
        for symbol in settings.tracked_symbols:
            for tf in settings.timeframes:
                stmt = (
                    select(crypto_prices)
                    .where(crypto_prices.symbol == symbol)
                    .where(crypto_prices.timeframe == tf)
                    .order_by(crypto_prices.timestamp.desc())
                    .limit(100)
                )
                result = await session.execute(stmt)
                records = result.scalars().all()

                # Vérifier les gaps
                for i in range(len(records) - 1):
                    current_ts = records[i].timestamp
                    next_ts = records[i + 1].timestamp
                    expected_interval = parse_timeframe_to_timedelta(tf)
                    actual_gap = current_ts - next_ts

                    if actual_gap > expected_interval * 1.5:  # 50% de tolérance
                        gaps_detected.append({
                            'symbol': symbol,
                            'timeframe': tf,
                            'gap': actual_gap,
                            'expected': expected_interval
                        })

        if gaps_detected:
            logger.warning(f"Gaps detected: {gaps_detected}")
            # Ajouter à queue de retry pour collector

        # 2. Vérification de freshness (staleness)
        now = datetime.now(timezone.utc)
        for symbol in settings.tracked_symbols:
            # Dernière donnée 1h
            stmt = (
                select(func.max(crypto_prices.timestamp))
                .where(crypto_prices.symbol == symbol)
                .where(crypto_prices.timeframe == '1h')
            )
            result = await session.execute(stmt)
            last_timestamp = result.scalar()

            if last_timestamp:
                staleness = now - last_timestamp
                if staleness > timedelta(minutes=5):  # Plus de 5 min = stale
                    logger.critical(f"Data is stale for {symbol}: {staleness} old")
```

---

## 6. Stratégie de Sauvegarde et Continuité

### 6.1 Backup TimescaleDB

**Stratégie:** Dump quotidien vers MinIO + WAL archiving

```bash
#!/bin/bash
# infra/scripts/backup-db.sh

DATE=$(date +%Y-%m-%d)
BACKUP_FILE="/tmp/cryptobot_${DATE}.sql.gz"

# pg_dump + compression
pg_dump -U cryptobot -h timescaledb cryptobot | gzip > "$BACKUP_FILE"

# Upload vers MinIO
mc cp "$BACKUP_FILE" minio/exports/db_backups/

# Retention: garder 30 derniers jours
mc find minio/exports/db_backups/ --older-than 30d -delete

# Notification
echo "Database backed up to MinIO: exports/db_backups/${DATE}.sql.gz"
```

**Cron:** `0 3 * * * /bin/bash /app/infra/scripts/backup-db.sh`
(Chaque jour à 3h UTC)

### 6.2 Backup MinIO

**Stratégie:** `mc mirror` quotidien vers un bucket de backup external

```bash
#!/bin/bash
# infra/scripts/backup-minio.sh

DATE=$(date +%Y-%m-%d)

# Mirror raw et datasets vers backup
mc mirror --remove minio/raw minio-backup/raw_${DATE}/
mc mirror --remove minio/datasets minio-backup/datasets_${DATE}/

# Retention: 7 derniers jours de backups
find /minio-backup -type d -name "raw_*" -mtime +7 -exec rm -rf {} \;
find /minio-backup -type d -name "datasets_*" -mtime +7 -exec rm -rf {} \;
```

### 6.3 Recovery Procedures

#### TimescaleDB Recovery

```bash
# 1. Stop services
docker-compose stop api etl-worker ml-worker

# 2. Restore from backup
BACKUP_DATE="2026-03-10"
mc cp minio/exports/db_backups/cryptobot_${BACKUP_DATE}.sql.gz - | \
  gunzip | psql -U cryptobot -h timescaledb -d cryptobot

# 3. Restart services
docker-compose up -d
```

#### MinIO Recovery

```bash
# Restore raw/ and datasets/
mc mirror minio-backup/raw_2026-03-10 minio/raw/
mc mirror minio-backup/datasets_2026-03-10 minio/datasets/
```

---

## 7. Justifications Techniques

### 7.1 TimescaleDB vs PostgreSQL vanilla

| Aspect | Impact | Justification |
|--------|--------|---------------|
| **Compression** | -80% disk usage après 7j | Données OHLCV peuvent atteindre 100M points/mois pour 30 symboles × 9 timeframes |
| **Retention policy** | Auto-cleanup sans trigger | Implémenter via trigger vanilla = complexe et non-performant |
| **Continuous aggregates** | Requêtes OHLCV agrégées pré-calculées | Cacherait 4h OHLCV depuis 1h OHLCV (évite recalcul) |
| **Multi-node support** | Scalabilité horizontale future | TimescaleDB Cloud permet réplication activement |

### 7.2 MinIO vs S3

| Aspect | Impact | Justification |
|--------|--------|---------------|
| **Coût** | $0 vs $50-200/mois | Données = TB de parquets — prohibitif en AWS |
| **Compliance** | On-premise, PII non en cloud AWS | École française, peut vouloir données locales |
| **Latence** | <5ms (local Docker) vs 50-100ms (AWS) | ML workers besoin de fetch rapides de datasets |
| **Portabilité** | Migrer vers S3 = changer endpoint uniquement | API 100% compatible |

### 7.3 No MongoDB — JSONB à la place

| Aspect | Impact | Justification |
|--------|--------|---------------|
| **Cohérence** | ACID guarantee across {indicators, signals} | MongoDB = eventual consistency, risque inconsistency |
| **Query power** | `metadata->'pattern'='Gartley'` indexed | Requêtes complexes = plus de flexibilité SQL |
| **Operational simplicity** | 1 DB au lieu de 2 | Moins de prod ops, moins de failure modes |
| **Joins** | `signals JOIN indicators ON ...` | Nécessaire pour correlation analysis; MongoDB ne supporte pas joins |

---

## 8. Matrice de Responsabilités

### 8.1 Qui écrit quoi?

| Table / Bucket | Écrit par | Lit depuis | Fréquence |
|---|---|---|---|
| crypto_prices | Data Eng (ETL) | ML, Backend, Frontend | Temps réel |
| indicators | Data Eng (compute job) | ML (backtesting) | Après OHLCV |
| trading_signals | ML Engine | Backend API, Frontend | Selon règles/ML |
| signal_outcomes | Data Eng (eval job) | Reporting | Post-hoc |
| users | Backend API | Backend, Frontend | On user action |
| portfolio | Backend API | Frontend | On user update |
| watchlist | Backend API | Frontend | On user update |
| news_articles | Data Eng (scrape job) | Frontend (feed) | Toutes les 15 min |
| text_mining_results | Data Eng (NLP job) | Reporting | Post-hoc |
| raw/* (MinIO) | Data Eng | Data Eng, ML | Batch |
| datasets/* (MinIO) | Data Eng (export job) | ML (training) | Quotidien |
| models/* (MinIO) | ML Engine | ML (serving), Backend (scoring) | Post-training |

### 8.2 Contrats d'Interface

**Data Eng → ML:**
- Tables: `crypto_prices`, `indicators`, `trading_signals` (read)
- MinIO: `raw/` (read), `datasets/` (write)
- Interface: Données propres, timestampées, sans gaps > 2x expected

**Data Eng → Backend:**
- Tables: Toutes en lecture
- Contrat: Schema stable (versioning via Alembic), migrations backward-compatible

**Data Eng → Frontend:**
- Via Backend API uniquement (pas d'accès direct DB)

---

## 9. Performance et Optimisation

### 9.1 Requêtes Critiques — Indices

```sql
-- Request 1: Derniers OHLCV pour un symbol/tf (dashboard)
SELECT * FROM crypto_prices
WHERE symbol = 'BTC' AND timeframe = '1h'
ORDER BY timestamp DESC LIMIT 100;
-- Index: (symbol, timeframe, timestamp DESC) ✓

-- Request 2: Indicateurs > N jours pour backtest
SELECT * FROM indicators
WHERE symbol = 'BTC' AND timeframe = '4h'
AND timestamp >= NOW() - INTERVAL '90 days'
ORDER BY timestamp;
-- Index: (symbol, timeframe, timestamp DESC) ✓

-- Request 3: Signaux récents avec confiance élevée
SELECT * FROM trading_signals
WHERE confidence_score >= 0.6
AND created_at >= NOW() - INTERVAL '24 hours'
ORDER BY created_at DESC;
-- Index: (confidence_score, created_at DESC) + partial index

-- Request 4: Recherche news par keywords
SELECT * FROM news_articles
WHERE keywords @> '["Bitcoin"]'::jsonb;
-- Index: (keywords) USING GIN ✓
```

### 9.2 Batch Inserts vs Single Inserts

**Préférer batch inserts:**

```python
# Lent : 100 requêtes SQL
for record in records:
    await session.execute(insert(crypto_prices).values(record.model_dump()))

# Rapide : 1 requête SQL
await session.execute(
    insert(crypto_prices).values([r.model_dump() for r in records])
)
# Speedup: ~50-100x pour 1000 records
```

### 9.3 Compression TimescaleDB — Impact

```sql
-- Avant compression (7 jours de données, 13 cryptos × 5 TF)
SELECT pg_size_pretty(pg_total_relation_size('crypto_prices'));
→ 500 MB

-- Après compression (job lancé)
SELECT pg_size_pretty(pg_total_relation_size('crypto_prices'));
→ 15 MB (33x reduction)
```

---

## 10. Checklist d'Implémentation

- [ ] **DDL TimescaleDB** : Toutes les 8 tables créées, hypertable + policies active
- [ ] **Alembic migrations** : Versioning schema, reversibilité garantie
- [ ] **MinIO buckets** : raw/, datasets/, models/, mlflow-artifacts/, exports/ créés
- [ ] **Pydantic models** : OHLCVRecord, IndicatorRecord, TradingSignal, NewsArticle définies
- [ ] **ETL pipeline** : APScheduler, jobs planifiés, retry logic avec exponential backoff
- [ ] **Data quality** : Validation Pydantic, déduplication, gap detection, staleness checks
- [ ] **Backup strategy** : pg_dump quotidien + MinIO lifecycle policies
- [ ] **Monitoring** : Health check sur ETL worker, logs structurés JSON, alertes staleness
- [ ] **Tests** : Unit tests collecteurs (mocked), integration tests avec TimescaleDB (Docker)
- [ ] **Documentation** : DDL commenté, conventions de naming, contrats d'interface

---

## 11. Feuille de Route — Phases

### Phase 1 (Nov-Déc 2024) — Foundation
- Schema TimescaleDB + migrations Alembic
- Connecteur Binance (REST OHLCV)
- Validation Pydantic, déduplication
- Worker ETL avec APScheduler
- MinIO buckets + lifecycle policies

### Phase 2 (Jan 2025) — Enrichissement
- Connecteurs CoinGecko, CCXT, Fear & Greed
- Scraping news (Decrypt, Cointelegraph)
- Calcul indicateurs techniques (RSI, Bollinger)
- Export Parquet vers MinIO
- Reconciliation job (gap detection)

### Phase 3 (Fév+ 2025) — Optimisations
- Indicateurs avancés (harmonic patterns, trend lines)
- Signal outcomes evaluation
- Continuous aggregates TimescaleDB
- Compression + retention policies validation
- Backup automation + recovery testing

---

**Document Version:** 2.0
**Date:** 2026-03-12
**Prochain Review:** 2026-04-12 (monthly)
