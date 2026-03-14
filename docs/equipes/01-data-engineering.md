# 01 — Equipe Data Engineering

> **Lisez d'abord** `docs/00-overview.md` pour le contexte global du projet.

---

## Votre perimetre

Vous etes responsables de **tout ce qui touche a la donnee** : collecte, stockage, qualite, pipelines.

| Vous gerez | Vous NE gerez PAS |
|-----------|-------------------|
| Pipeline ETL (collecte, validation, transformation, chargement) | Les modeles ML (equipe ML) |
| Schema TimescaleDB (tables, hypertables, migrations) | Les endpoints API REST (equipe Backend) |
| Configuration MinIO (buckets, policies) | L'interface Streamlit (equipe Frontend) |
| Sources de donnees externes (Binance, CoinGecko, scraping) | Docker/CI/CD (equipe DevOps) |
| Calcul et stockage des indicateurs techniques | L'authentification (equipe Backend) |
| Qualite des donnees (validation, deduplication) | |

**Votre code va dans** : `src/etl/`
**Votre branche** : `data-eng/xxx`

---

## Ce que les autres equipes attendent de vous

| Equipe | Ce qu'elle attend | Interface |
|--------|------------------|-----------|
| **ML** | Donnees OHLCV propres dans TimescaleDB, indicateurs calcules par TF, datasets dans MinIO | Tables `crypto_prices`, `indicators`, bucket `minio://datasets/` |
| **Backend** | Schema BDD stable, tables de signaux et users exploitables | Schema Alembic versionne, models pydantic dans `src/shared/` |
| **Frontend** | Donnees fraiches et coherentes dans la BDD | Les donnees sont servies par l'API (equipe Backend), pas directement par vous |
| **DevOps** | Scripts de migration, seed data, healthchecks | `src/etl/migrations/`, endpoint `/health` sur le worker ETL |

---

## Sources de donnees

### Sources de prix (prioritaires)

| Source | Methode | Donnees | Rate limit |
|--------|---------|---------|------------|
| **Binance** | API REST publique (pas d'auth) + WebSocket | OHLCV, order book, trades | 1200 req/min |
| **CoinGecko** | API Demo (cle gratuite) | Market cap, ranking, metadata | 30 req/min, 10k/mois |
| **CCXT** | Librairie Python | Connecteur unifie multi-exchanges | Depends de l'exchange |

### Sources de veille

| Source | Methode | Donnees |
|--------|---------|---------|
| Decrypt | Scraping (BeautifulSoup) | Actualites Web3/crypto |
| Cointelegraph | Scraping | Actualites blockchain |
| Phoenix News | API | Agregateur 1500+ sources |
| ESMA / SEC / EU Blockchain | Scraping | Reglementation |
| Alternative.me | API gratuite | Fear & Greed Index |
| Cryptorank | API | Data crypto agrege |

### Gestion des rate limits

- **Binance** : preferer WebSocket pour le temps reel, REST pour l'historique uniquement
- **CoinGecko** : cache en BDD (TTL 60s), batch requests, pas d'appels redondants
- **Scraping** : respecter robots.txt, delai entre requetes (1-2s), user-agent correct

---

## Pipeline ETL

```
[Sources externes]
    |
    v
[EXTRACT]           requests, CCXT, BeautifulSoup, aiohttp
    |                Planification : APScheduler (dans le worker ETL)
    v
[VALIDATE]          pydantic schemas (dans src/shared/models/)
    |                Deduplication par (symbol, timestamp, timeframe)
    |                Detection de gaps (donnees manquantes)
    v
[TRANSFORM]         pandas, numpy
    |                Calcul des indicateurs techniques
    |                Nettoyage, normalisation
    v
[LOAD]              TimescaleDB (hypertables) via SQLAlchemy
    |                MinIO (fichiers bruts CSV/Parquet)
```

### Gestion des erreurs

- Retry avec backoff exponentiel : 1s, 2s, 4s, 8s, 16s (max 5 tentatives)
- Logging structure JSON pour chaque job (timestamp, source, status, error)
- Si un job echoue 3 fois : log CRITICAL + skip et continuer les autres sources
- Job de reconciliation horaire : detecte les gaps et relance la collecte

### Jobs planifies

| Job | Frequence | Description |
|-----|-----------|-------------|
| `collect_ohlcv` | Toutes les minutes (top cryptos), 5 min (reste) | Collecte OHLCV via Binance/CCXT |
| `collect_market_data` | Toutes les 5 minutes | Market cap, volumes via CoinGecko |
| `collect_news` | Toutes les 15 minutes | Scraping news + API |
| `collect_fear_greed` | Toutes les heures | Fear & Greed Index |
| `compute_indicators` | Apres chaque collect_ohlcv | Calcul RSI, Bollinger, etc. |
| `export_datasets` | Quotidien (3h UTC) | Export Parquet vers MinIO pour le ML |
| `reconciliation` | Toutes les heures | Detection et comblement des gaps |

---

## Schema TimescaleDB

### Tables a creer

```sql
-- ============================================================
-- HYPERTABLE : donnees OHLCV (series temporelles)
-- ============================================================
CREATE TABLE crypto_prices (
    symbol        VARCHAR(20) NOT NULL,
    price_open    DECIMAL(20, 8) NOT NULL,
    price_high    DECIMAL(20, 8) NOT NULL,
    price_low     DECIMAL(20, 8) NOT NULL,
    price_close   DECIMAL(20, 8) NOT NULL,
    volume_24h    DECIMAL(20, 8) NOT NULL,
    market_cap    DECIMAL(20, 2),
    timestamp     TIMESTAMPTZ NOT NULL,
    source        VARCHAR(50) NOT NULL,
    timeframe     VARCHAR(10) NOT NULL  -- 1m, 5m, 1h, 2h, 3h, 4h, 1D, 1W, 1M
);

SELECT create_hypertable('crypto_prices', 'timestamp');
CREATE INDEX idx_prices_symbol_tf ON crypto_prices (symbol, timeframe, timestamp DESC);

-- Politique de retention
SELECT add_retention_policy('crypto_prices', INTERVAL '90 days',
    if_not_exists => true);

-- Compression apres 7 jours
ALTER TABLE crypto_prices SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'symbol, timeframe',
    timescaledb.compress_orderby = 'timestamp DESC'
);
SELECT add_compression_policy('crypto_prices', INTERVAL '7 days');

-- ============================================================
-- TABLE : indicateurs techniques par timeframe
-- ============================================================
CREATE TABLE indicators (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol            VARCHAR(20) NOT NULL,
    timeframe         VARCHAR(10) NOT NULL,
    timestamp         TIMESTAMPTZ NOT NULL,
    rsi               DECIMAL(10, 4),
    bollinger_upper   DECIMAL(20, 8),
    bollinger_middle  DECIMAL(20, 8),
    bollinger_lower   DECIMAL(20, 8),
    price_vs_bollinger DECIMAL(10, 6),  -- position relative du prix
    harmonic_pattern  VARCHAR(50),       -- Gartley, Butterfly, etc.
    trend_slope       DECIMAL(10, 6),    -- pente de la trend line
    trend_type        VARCHAR(20),       -- stable, aggressive, etc.
    metadata          JSONB DEFAULT '{}',
    UNIQUE (symbol, timeframe, timestamp)
);

-- ============================================================
-- TABLE : signaux de trading (informatifs)
-- Inseree par l'equipe ML, schema defini ici
-- ============================================================
CREATE TABLE trading_signals (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol              VARCHAR(20) NOT NULL,
    signal_type         VARCHAR(10) NOT NULL CHECK (signal_type IN ('BUY', 'SELL', 'HOLD')),
    confidence_score    DECIMAL(5, 4) NOT NULL,
    timeframe_primary   VARCHAR(10) NOT NULL,
    timeframes_aligned  JSONB DEFAULT '{}',
    rules_triggered     JSONB DEFAULT '{}',
    leverage_suggested  INTEGER,
    margin_safety       DECIMAL(10, 4),
    fees_estimated      DECIMAL(10, 6),
    model_version       VARCHAR(50),
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- TABLE : resultats des signaux a posteriori
-- Inseree par un job ETL d'evaluation
-- ============================================================
CREATE TABLE signal_outcomes (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    signal_id        UUID REFERENCES trading_signals(id),
    price_at_signal  DECIMAL(20, 8),
    price_after_1h   DECIMAL(20, 8),
    price_after_4h   DECIMAL(20, 8),
    price_after_1d   DECIMAL(20, 8),
    pnl_simulated    DECIMAL(10, 4),
    was_correct      BOOLEAN,
    evaluated_at     TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- TABLE : portefeuille
-- ============================================================
CREATE TABLE portfolio (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       UUID REFERENCES users(id),
    symbol        VARCHAR(20) NOT NULL,
    quantity      DECIMAL(20, 8) NOT NULL,
    entry_price   DECIMAL(20, 8) NOT NULL,
    current_price DECIMAL(20, 8),
    updated_at    TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- TABLE : utilisateurs
-- Geree par l'equipe Backend pour l'auth, schema defini ici
-- ============================================================
CREATE TABLE users (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username      VARCHAR(100) UNIQUE NOT NULL,
    email         VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    persona_type  VARCHAR(20) CHECK (persona_type IN ('trader', 'journalist', 'investor')),
    preferences   JSONB DEFAULT '{}',
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- TABLE : articles de news (JSONB pour donnees non structurees)
-- ============================================================
CREATE TABLE news_articles (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title            VARCHAR(500) NOT NULL,
    content          TEXT,
    source           VARCHAR(100) NOT NULL,
    url              VARCHAR(1000) UNIQUE NOT NULL,
    published_at     TIMESTAMPTZ,
    sentiment_score  DECIMAL(5, 4),
    keywords         JSONB DEFAULT '[]',
    reliability_score DECIMAL(5, 4),
    collected_at     TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- TABLE : resultats de text mining
-- ============================================================
CREATE TABLE text_mining_results (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    article_id   UUID REFERENCES news_articles(id),
    word_cloud   JSONB DEFAULT '{}',
    summary      TEXT,
    entities     JSONB DEFAULT '[]',
    topics       JSONB DEFAULT '[]',
    processed_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Migrations

- Outil : **Alembic** (compatible SQLAlchemy + TimescaleDB)
- Dossier : `src/etl/migrations/`
- Convention : `YYYYMMDD_description.py`
- Toutes les migrations doivent etre reversibles

---

## Structure MinIO

```
minio/
├── raw/                    # Donnees brutes (ne jamais modifier)
│   ├── binance/            # OHLCV bruts en Parquet partitionne par jour
│   ├── coingecko/          # JSON metadata coins
│   └── news/               # Articles bruts
├── datasets/               # Datasets prepares pour le ML (equipe ML les consomme)
│   ├── features_YYYYMMDD.parquet
│   └── labels_YYYYMMDD.parquet
├── models/                 # Modeles entraines (equipe ML les ecrit)
├── mlflow-artifacts/       # Artefacts MLflow (gere par MLflow)
└── exports/                # Rapports, figures, CSV exports
```

**Convention** : l'equipe Data Engineering ecrit dans `raw/` et `datasets/`. L'equipe ML ecrit dans `models/` et lit depuis `datasets/`.

---

## Models pydantic partages

Vous devez definir les models pydantic dans `src/shared/models/` pour que toutes les equipes utilisent les memes schemas :

```python
# src/shared/models/crypto.py
from pydantic import BaseModel
from datetime import datetime
from decimal import Decimal

class OHLCVRecord(BaseModel):
    symbol: str
    price_open: Decimal
    price_high: Decimal
    price_low: Decimal
    price_close: Decimal
    volume_24h: Decimal
    market_cap: Decimal | None = None
    timestamp: datetime
    source: str
    timeframe: str

class IndicatorRecord(BaseModel):
    symbol: str
    timeframe: str
    timestamp: datetime
    rsi: Decimal | None = None
    bollinger_upper: Decimal | None = None
    bollinger_middle: Decimal | None = None
    bollinger_lower: Decimal | None = None
    price_vs_bollinger: Decimal | None = None
    harmonic_pattern: str | None = None
    trend_slope: Decimal | None = None
    trend_type: str | None = None

class NewsArticle(BaseModel):
    title: str
    content: str | None = None
    source: str
    url: str
    published_at: datetime | None = None
    sentiment_score: Decimal | None = None
    keywords: list[str] = []
    reliability_score: Decimal | None = None
```

---

## Indicateurs techniques a calculer

L'equipe ML definit les indicateurs et leurs parametres, mais **c'est vous qui les calculez et les stockez**. Voici la liste initiale (voir `docs/02-ml-data-science.md` pour les details) :

| Indicateur | Parametres | Timeframes |
|------------|-----------|------------|
| RSI | Periode 14 (par defaut) | 1h, 2h, 3h, 4h, 1D |
| Bollinger Bands | MA20, 2 ecarts-types | 1h, 2h, 3h, 4h, 1D |
| Prix vs Bollinger | Position relative du prix dans les bandes | Tous |
| Trend line slope | Regression lineaire sur N bougies | 1D, 1W, 1M |
| Trend type | Classification (stable, aggressive) | 1W, 1M |
| Harmonic patterns | Detection Gartley, Butterfly, etc. | 4h, 1D |
| Volume relatif | Volume / MA20(volume) | Tous |

**Librairie recommandee** : `ta-lib` ou `pandas-ta` pour les calculs d'indicateurs.

---

## Taches

### Sprint 1-2 (Novembre-Decembre)
- [ ] Connecteur Binance OHLCV (REST + WebSocket)
- [ ] Connecteur CoinGecko Demo
- [ ] Connecteur CCXT (wrapper unifie)
- [ ] Schema TimescaleDB (Alembic migrations)
- [ ] Setup MinIO (buckets, policies)
- [ ] Worker ETL avec APScheduler
- [ ] Validation pydantic des donnees entrantes
- [ ] Deduplication
- [ ] Logging structure

### Sprint 3-4 (Decembre-Janvier)
- [ ] Scraping news (Decrypt, Cointelegraph)
- [ ] Collecte Fear & Greed Index
- [ ] Calcul des indicateurs techniques (RSI, Bollinger)
- [ ] Job de reconciliation (detection de gaps)
- [ ] Export datasets Parquet vers MinIO
- [ ] Tests unitaires + integration (> 80% couverture)

### Sprint 5+ (Janvier+)
- [ ] Indicateurs avances (harmonics, trend lines)
- [ ] Job d'evaluation des signaux (signal_outcomes)
- [ ] Optimisation des performances (batch inserts, compression)
