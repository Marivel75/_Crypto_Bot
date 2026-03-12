# Cahier des Charges Fonctionnelles — Crypto Bot

**Document Version:** 1.0
**Date:** 2026-03-12
**Auteur:** Product Manager — Core Platform (ETL + API)
**Périmètre:** Module ETL + Module API
**Langue:** Français

---

## Table des matières

1. [Module ETL — Exigences Fonctionnelles](#module-etl--exigences-fonctionnelles)
2. [Module API — Exigences Fonctionnelles](#module-api--exigences-fonctionnelles)
3. [Exigences Non-Fonctionnelles](#exigences-non-fonctionnelles)
4. [Matrice de Traçabilité](#matrice-de-traçabilité)

---

# MODULE ETL — EXIGENCES FONCTIONNELLES

## RF-ETL-001 : Collecte OHLCV via Binance REST (Historique)

**ID:** RF-ETL-001
**Priorité (MoSCoW):** MUST
**Statut:** Actif

### Description fonctionnelle

L'ETL doit collecter les données OHLCV (Open, High, Low, Close, Volume) historiques depuis l'API REST publique de Binance pour tous les symboles suivis (top 30 cryptos).

### Critères d'acceptation

- [ ] Collecte OHLCV via endpoint `/api/v3/klines` (sans authentification)
- [ ] Support des timeframes : 1m, 5m, 15m, 30m, 1h, 2h, 3h, 4h, 1D, 1W, 1M
- [ ] Pagination automatique (limit max 1000 candles par appel)
- [ ] Gestion des rate limits Binance (1200 requêtes/min) avec jitter aléatoire
- [ ] Retry avec exponential backoff (1s, 2s, 4s, 8s, 16s) en cas de 429/503
- [ ] Validation des données reçues avec un schéma Pydantic `OHLCVRecord`
- [ ] Reject automatique si high < low ou close hors [open; max(high, low)]
- [ ] Logging de chaque appel : timestamp, symbole, timeframe, nombre de candles reçues
- [ ] Gestion des gaps (détection si > 2 candles manquantes)

### Dépendances

- Binance API publique (pas de clé requise)
- Schéma Pydantic `OHLCVRecord` dans `src/shared/models/crypto.py`
- Table TimescaleDB `crypto_prices` (RF-ETL-008)

### Notes

- Pas d'authentification requise
- Préférer WebSocket pour le temps réel (voir RF-ETL-002)
- Cet endpoint est utilisé pour remplir les trous historiques et les backfills

---

## RF-ETL-002 : Collecte OHLCV via Binance WebSocket (Temps Réel)

**ID:** RF-ETL-002
**Priorité (MoSCoW):** MUST
**Statut:** Actif

### Description fonctionnelle

L'ETL doit maintenir une connexion WebSocket à Binance pour recevoir les candles OHLCV en temps réel à chaque clôture de bougie.

### Critères d'acceptation

- [ ] Connexion WebSocket à `wss://stream.binance.com:9443/ws`
- [ ] Subscription aux streams agrégés de candles : `{symbol.lower()}@kline_{interval}`
- [ ] Support des timeframes : 1m, 5m, 15m, 30m, 1h, 2h, 3h, 4h, 1D
- [ ] Reconnexion automatique avec exponential backoff si disconnection (max 5 tentatives)
- [ ] Heartbeat/ping-pong toutes les 30s
- [ ] Mise à jour des données immédiatement à la clôture de la bougie (champ `k.x` = true)
- [ ] Validation et déduplication : rejecter si (symbol, timeframe, timestamp) existe déjà en BDD
- [ ] Logging structuré JSON pour chaque candle reçue
- [ ] Alerte CRITICAL si WebSocket est déconnecté > 5 minutes

### Dépendances

- Binance WebSocket publique
- Table `crypto_prices` (RF-ETL-008)
- Runner asynchrone avec `asyncio`

### Notes

- Pas de perte de messages (buffer de max 1000 candles si latence réseau)
- Thread-safe avec lock pour les opérations d'écriture en BDD

---

## RF-ETL-003 : Collecte Multi-Exchange via CCXT

**ID:** RF-ETL-003
**Priorité (MoSCoW):** SHOULD
**Statut:** Optionnel — Phase 2

### Description fonctionnelle

Pour la résilience, l'ETL doit supporter la collecte OHLCV depuis d'autres exchanges publics via la librairie CCXT (fallback si Binance est indisponible).

### Critères d'acceptation

- [ ] Connecteur CCXT pour au minimum 2 autres exchanges (Kraken, Kucoin)
- [ ] Même validation Pydantic que Binance
- [ ] Deduplication cross-exchange : stocker le champ `source` pour chaque enregistrement
- [ ] Rate limiting respectant les limites de chaque exchange
- [ ] Fallback automatique si Binance indisponible > 10 min
- [ ] Logging de la source utilisée pour chaque bougie

### Dépendances

- CCXT Python library
- Table `crypto_prices` avec champ `source`

---

## RF-ETL-004 : Collecte Données de Marché via CoinGecko Demo API

**ID:** RF-ETL-004
**Priorité (MoSCoW):** MUST
**Statut:** Actif

### Description fonctionnelle

L'ETL doit collecter périodiquement les métadonnées de marché (market cap, ranking, volume 24h) depuis l'API gratuite CoinGecko Demo.

### Critères d'acceptation

- [ ] Utilisation de la clé API gratuite CoinGecko (fournie dans `.env`)
- [ ] Rate limiting respecté : 30 req/min, quota mensuel 10k requêtes
- [ ] Collecte des champs : symbol, market_cap, trading_volume_24h, market_cap_rank
- [ ] Mise en cache BDD (TTL 60s) pour éviter les appels redondants
- [ ] Batch requests : regrouper 250 cryptos par appel (endpoint `/api/v3/coins/markets`)
- [ ] Validation : rejecter si market_cap ou volume < 0
- [ ] Logging : timestamp, nombre de cryptos récupérées, statut HTTP

### Dépendances

- CoinGecko API gratuite
- Table `crypto_prices` (ajout des colonnes `market_cap`, `trading_volume_24h`)

### Notes

- API publique, pas d'authentification réseau requise (clé pour l'accès gratuit)
- Utiliser `httpx` pour les requêtes asynchrones

---

## RF-ETL-005 : Collecte News via Scraping et APIs

**ID:** RF-ETL-005
**Priorité (MoSCoW):** MUST
**Statut:** Actif

### Description fonctionnelle

L'ETL doit collecter les actualités crypto depuis plusieurs sources (scraping + APIs) pour l'affichage dans le frontend et l'analyse de sentiment.

### Critères d'acceptation

#### Sources RSS/Scraping :
- [ ] Scraping BeautifulSoup des sites : Decrypt (web3 news), Cointelegraph, PhoenixNews
- [ ] Respect des robots.txt et délai entre requêtes (1-2 secondes)
- [ ] User-Agent réaliste dans les headers HTTP
- [ ] Extraction des champs : title, content (paragraphes), url, published_at, source
- [ ] Parsing de la date publiée selon le format du site

#### Source API :
- [ ] Utilisation de l'API libre Phoenix News (news aggregator 1500+ sources)
- [ ] Récupération des derniers articles de la journée

#### Validation et stockage :
- [ ] Validation pydantic : titre non-vide, URL valide (RFC 3986)
- [ ] Deduplication par URL (UNIQUE constraint en BDD)
- [ ] Gestion des URLs shortcut (suivi des redirects HTTP 301/302)
- [ ] Rejecter les articles sans date de publication
- [ ] Logging : source, nombre d'articles extraits, erreurs de parsing

### Dépendances

- BeautifulSoup4, requests, aiohttp
- Schéma Pydantic `NewsArticle` (RF-ETL-010)
- Table `news_articles` (RF-ETL-009)

### Notes

- Respecter les conditions d'utilisation de chaque site (pas d'abuse)
- Limiter la fréquence de scraping : 1 call/15min par source
- Fallback gracieux si un site devient inaccessible (log warning, continuer)

---

## RF-ETL-006 : Collecte Fear & Greed Index

**ID:** RF-ETL-006
**Priorité (MoSCoW):** SHOULD
**Statut:** Optionnel — Phase 1

### Description fonctionnelle

L'ETL doit récupérer l'indice de peur/greed du marché crypto depuis l'API gratuite Alternative.me toutes les heures.

### Critères d'acceptation

- [ ] Appel API gratuite : `https://api.alternative.me/fng/?limit=1`
- [ ] Extraction des champs : value (0-100), value_classification (Fear/Extreme Fear/Neutral/Greed/Extreme Greed), timestamp
- [ ] Validation : value doit être dans [0, 100]
- [ ] Stockage dans une table dédiée `fear_greed_index` (ou JSONB dans crypto_prices)
- [ ] Deduplication par (date, timestamp) — rejeter les doublons
- [ ] Logging : valeur reçue, classification, timestamp

### Dépendances

- Alternative.me API gratuite (aucune clé requise)
- Table/colonne pour stocker l'indice

---

## RF-ETL-007 : Orchestration et Scheduling (APScheduler)

**ID:** RF-ETL-007
**Priorité (MoSCoW):** MUST
**Statut:** Actif

### Description fonctionnelle

L'ETL doit orchestrer l'exécution périodique de tous les jobs de collecte via APScheduler, sans message broker externe.

### Critères d'acceptation

#### Jobs planifiés :

| Job | Fréquence | Déclencheur |
|-----|-----------|------------|
| `collect_ohlcv_1m` | Toutes les 1 minute | Symboles top 13 |
| `collect_ohlcv_5m` | Toutes les 5 minutes | Symboles 14-30 |
| `collect_ohlcv_historical` | Une fois par jour (3h UTC) | Backfill mensuel |
| `collect_market_data` | Toutes les 5 minutes | CoinGecko market caps |
| `collect_news` | Toutes les 15 minutes | Web scraping + APIs |
| `collect_fear_greed` | Toutes les heures | Alternative.me |
| `compute_indicators` | Après chaque collect_ohlcv | Calcul RSI, Bollinger, etc. |
| `export_datasets` | Une fois par jour (6h UTC) | Parquet export vers MinIO |
| `reconciliation_gaps` | Toutes les heures | Détection et comblement des gaps |
| `evaluate_signal_outcomes` | Toutes les 4 heures | Évaluation post-hoc des signaux |

#### Implémentation :

- [ ] Configuration centralisée des jobs dans `src/etl/scheduler.py`
- [ ] Utilisation de APScheduler (apsched) avec backend en-memory ou SQLAlchemy
- [ ] Gestion des dépendances entre jobs : compute_indicators attend collect_ohlcv
- [ ] Timeout configurable par job (max 30 min pour les plus longs)
- [ ] Gestion des erreurs : log CRITICAL, skip l'itération, relancer au prochain cycle
- [ ] Monitoring : endpoint `/health` de l'ETL expose l'état du scheduler (running jobs, errors)
- [ ] Graceful shutdown : attendre la fin du job courant avant arrêt (timeout 2 min)

### Dépendances

- APScheduler library
- Configuration centralisée (pydantic-settings)
- Logging structuré

### Notes

- Pas de Redis, RabbitMQ, ou Kafka pour V1
- Les jobs sont idempotents (safe to re-run)
- Éviter les chevauchements : lock distribué par job_id en BDD

---

## RF-ETL-008 : Stockage TimescaleDB — Table OHLCV

**ID:** RF-ETL-008
**Priorité (MoSCoW):** MUST
**Statut:** Actif

### Description fonctionnelle

L'ETL doit créer et maintenir une hypertable TimescaleDB pour stocker les données OHLCV avec compression et retention automatiques.

### Critères d'acceptation

#### Schéma :

```sql
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
    timeframe     VARCHAR(10) NOT NULL
);
```

#### Configuration hypertable :

- [ ] Hypertable partitionnée par `timestamp` (intervalles de 1 jour)
- [ ] Chunks configurés pour 1 jour de données
- [ ] Index composite : `(symbol, timeframe, timestamp DESC)`
- [ ] Compression automatique après 7 jours (réduction de taille attendue : 90%)
- [ ] Retention policy : supprimer les données > 90 jours
- [ ] Unique constraint : `UNIQUE(symbol, timeframe, timestamp, source)`

#### Inserts :

- [ ] Batch inserts via `executemany()` (max 1000 lignes par batch)
- [ ] Déduplication avant insert : rejeter si clé unique existe
- [ ] Transaction ACID par batch (rollback si erreur)
- [ ] Logging : timestamp, symbole, timeframe, nombre de lignes insérées/rejetées

### Dépendances

- TimescaleDB extension PostgreSQL
- Alembic migrations

### Notes

- Pas de DELETE ni UPDATE (append-only)
- Requêtes optimisées par TimescaleDB pour les series temporelles
- Outil `timescaledb-tune` pour le tuning en production

---

## RF-ETL-009 : Stockage TimescaleDB — Tables Indicateurs, Signaux, News

**ID:** RF-ETL-009
**Priorité (MoSCoW):** MUST
**Statut:** Actif

### Description fonctionnelle

L'ETL doit créer et maintenir les tables complémentaires pour stocker les indicateurs techniques, signaux de trading, news, et outcomes.

### Critères d'acceptation

#### Table `indicators` :

```sql
CREATE TABLE indicators (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symbol            VARCHAR(20) NOT NULL,
    timeframe         VARCHAR(10) NOT NULL,
    timestamp         TIMESTAMPTZ NOT NULL,
    rsi               DECIMAL(10, 4),
    bollinger_upper   DECIMAL(20, 8),
    bollinger_middle  DECIMAL(20, 8),
    bollinger_lower   DECIMAL(20, 8),
    price_vs_bollinger DECIMAL(10, 6),
    harmonic_pattern  VARCHAR(50),
    trend_slope       DECIMAL(10, 6),
    trend_type        VARCHAR(20),
    metadata          JSONB DEFAULT '{}',
    UNIQUE (symbol, timeframe, timestamp)
);
```

- [ ] Hypertable partitionnée par `timestamp`
- [ ] Index : `(symbol, timeframe, timestamp DESC)`
- [ ] Compression après 7 jours
- [ ] Retention : 365 jours

#### Table `trading_signals` :

```sql
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
```

- [ ] Index : `(symbol, created_at DESC)`
- [ ] Compression : après 30 jours
- [ ] Retention : 1 an
- [ ] Contrainte : `confidence_score >= 0.6` (appliquée à l'application, pas en BDD)

#### Table `signal_outcomes` :

```sql
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
```

- [ ] Compression : après 30 jours
- [ ] Retention : 1 an

#### Table `news_articles` :

```sql
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
```

- [ ] Index : `(source, published_at DESC)`, `(collected_at DESC)`
- [ ] Compression : après 90 jours
- [ ] Retention : 2 ans

### Dépendances

- Alembic migrations
- TimescaleDB

---

## RF-ETL-010 : Validation des Données (Pydantic)

**ID:** RF-ETL-010
**Priorité (MoSCoW):** MUST
**Statut:** Actif

### Description fonctionnelle

L'ETL doit valider TOUTES les données reçues des sources externes avant insertion en BDD, en utilisant les schémas Pydantic centralisés dans `src/shared/models/`.

### Critères d'acceptation

- [ ] Schéma `OHLCVRecord` :
  - Symbol : pattern `^[A-Z0-9]+$` (max 20 chars)
  - Prix : Decimal positifs, high >= low
  - Volume : >= 0
  - Timestamp : datetime valide, max 5 min dans le futur
  - Source : parmi liste blanche (binance, coingecko, kraken, kucoin)
  - Timeframe : parmi liste autorisée (1m, 5m, 15m, 30m, 1h, 2h, 3h, 4h, 1D, 1W, 1M)

- [ ] Schéma `IndicatorRecord` :
  - RSI : [0, 100] ou None
  - Bollinger bands : upper >= middle >= lower
  - Price vs Bollinger : [-1, 1] ou None
  - Harmonic pattern : enum ou None

- [ ] Schéma `NewsArticle` :
  - Title : non-vide, max 500 chars
  - URL : valide (RFC 3986)
  - Source : parmi liste blanche
  - Published_at : pas dans le futur, pas > 2 ans dans le passé

- [ ] Rejection logging : chaque rejet doit logger symbole, raison, donnée invalide
- [ ] Métriques : compteur de rejets par source par heure (exposed dans `/health`)

### Dépendances

- Pydantic v2
- Modèles dans `src/shared/models/`

---

## RF-ETL-011 : Déduplication des Données

**ID:** RF-ETL-011
**Priorité (MoSCoW):** MUST
**Statut:** Actif

### Description fonctionnelle

L'ETL doit déduplicer les données reçues pour éviter les inserts redondants et maintenir l'intégrité des données.

### Critères d'acceptation

#### OHLCV :

- [ ] Clé de déduplication : `(symbol, timeframe, timestamp, source)`
- [ ] Si la clé existe en BDD : skip silencieusement (pas d'erreur, pas d'update)
- [ ] Vérification avant insert (requête SELECT LIMIT 1)
- [ ] Rejecter les doublons au sein d'un même batch (intra-batch deduplication)

#### News :

- [ ] Clé de déduplication : `url` (UNIQUE constraint en BDD)
- [ ] Si URL existe : skip silencieusement
- [ ] Suivi des redirects HTTP : canonicaliser les URLs avant vérification
  - Ex : `http://example.com/news/123` → `https://example.com/news/123`

#### Signaux :

- [ ] Pas de déduplication directe (insertés une seule fois par l'équipe ML)
- [ ] Integrity check : un signal ne peut pas avoir `confidence_score < 0.6` en BDD

### Dépendances

- Contraintes UNIQUE en BDD
- Requêtes paramétrées

---

## RF-ETL-012 : Détection et Comblement des Gaps

**ID:** RF-ETL-012
**Priorité (MoSCoW):** SHOULD
**Statut:** Phase 1

### Description fonctionnelle

L'ETL doit détecter les trous dans les données historiques (candles manquantes) et déclencher automatiquement une collecte de remplissage.

### Critères d'acceptation

- [ ] Job `reconciliation_gaps` exécuté toutes les heures
- [ ] Pour chaque (symbol, timeframe) : vérifier la continuité des timestamps
- [ ] Détection : si gap > 2 candles consécutives → log WARNING
- [ ] Auto-healing : déclencher un `collect_ohlcv_historical` pour remplir le gap
- [ ] Limite : max 3 tentatives par gap avant abandon (log CRITICAL)
- [ ] Reporting : endpoint `/api/v1/system/data-quality` expose les gaps non résolus

### Dépendances

- Table `crypto_prices`
- Job scheduler (RF-ETL-007)

---

## RF-ETL-013 : Stockage MinIO — Buckets et Partitionnement

**ID:** RF-ETL-013
**Priorité (MoSCoW):** SHOULD
**Statut:** Phase 1

### Description fonctionnelle

L'ETL doit exporter les données brutes et prétraitées vers MinIO (S3-compatible) pour archivage long terme et accès par le pipeline ML.

### Critères d'acceptation

#### Structure MinIO :

```
s3://raw/
  ├── binance/
  │   ├── OHLCV/
  │   │   └── {symbol}/{YYYYMMDD}/*.parquet
  │   └── metadata/
  │       └── {YYYYMMDD}.json
  ├── coingecko/
  │   └── market_data/{YYYYMMDD}.parquet
  └── news/
      └── articles/{YYYYMMDD}.parquet

s3://datasets/
  ├── features_{YYYYMMDD}.parquet
  ├── labels_{YYYYMMDD}.parquet
  └── metadata.json
```

#### Export OHLCV :

- [ ] Export quotidien (6h UTC) en format Parquet
- [ ] Partitionnement par symbol et date (colonnes : symbol, timeframe, timestamp)
- [ ] Compression : snappy (défaut Parquet)
- [ ] Rétention : archivage 1 an, puis suppression

#### Export Datasets :

- [ ] Préparation par l'équipe Data Eng des features/labels (après calcul d'indicateurs)
- [ ] Format Parquet, partitionné par date
- [ ] Métadonnées : schema, version features, timestamp

### Dépendances

- MinIO service (Docker)
- boto3 Python client
- pandas/pyarrow pour Parquet

---

## RF-ETL-014 : Logging Structuré et Monitoring

**ID:** RF-ETL-014
**Priorité (MoSCoW):** MUST
**Statut:** Actif

### Description fonctionnelle

Tous les jobs ETL doivent produire des logs structurés en JSON pour faciliter le debugging et le monitoring en production.

### Critères d'acceptation

- [ ] Format de log : JSON à la sortie (utilisable par Elasticsearch, Grafana)
- [ ] Champs obligatoires : timestamp (ISO 8601), level (DEBUG/INFO/WARNING/ERROR/CRITICAL), job_name, message, context (dict)
- [ ] Exemple :
  ```json
  {
    "timestamp": "2026-03-12T14:30:00Z",
    "level": "INFO",
    "job_name": "collect_ohlcv_1m",
    "message": "Batch insert completed",
    "context": {
      "symbol": "BTCUSDT",
      "timeframe": "1m",
      "rows_inserted": 1,
      "rows_rejected": 0,
      "duration_ms": 234
    }
  }
  ```
- [ ] Logs écrits sur stdout (Docker capture automatiquement)
- [ ] Log des erreurs non-capturées avec stack trace complet et contexte
- [ ] Rotation des logs (pas pertinent pour stdout, mais pour fichiers locaux : max 100 MB par fichier)

### Dépendances

- Python logging module
- JSON formatter custom

---

## RF-ETL-015 : Healthcheck ETL

**ID:** RF-ETL-015
**Priorité (MoSCoW):** SHOULD
**Statut:** Phase 1

### Description fonctionnelle

L'ETL worker doit exposer un endpoint HTTP de healthcheck pour la surveillance par Docker/orchestration.

### Critères d'acceptation

- [ ] Endpoint : `GET /health`
- [ ] Réponse 200 OK si tous les services sont sains (BDD, MinIO, scheduler)
- [ ] Réponse 503 Service Unavailable si un service critique est down
- [ ] Payload :
  ```json
  {
    "status": "healthy",
    "timestamp": "2026-03-12T14:30:00Z",
    "checks": {
      "database": {
        "status": "ok",
        "latency_ms": 12
      },
      "minio": {
        "status": "ok",
        "latency_ms": 45
      },
      "scheduler": {
        "status": "ok",
        "running_jobs": 2
      }
    },
    "metrics": {
      "ohlcv_rows_collected_1h": 1234,
      "rejections_1h": 5,
      "last_news_collection": "2026-03-12T14:28:00Z"
    }
  }
  ```

### Dépendances

- FastAPI ou autre serveur web léger
- Accès à la config des services

---

## RF-ETL-016 : Gestion d'Erreurs et Récupération

**ID:** RF-ETL-016
**Priorité (MoSCoW):** MUST
**Statut:** Actif

### Description fonctionnelle

L'ETL doit gérer les erreurs réseau, API, et BDD de manière robuste pour éviter les pertes de données ou les interruptions prolongées.

### Critères d'acceptation

#### Erreurs réseau (429, 503, timeout) :

- [ ] Exponential backoff : 1s, 2s, 4s, 8s, 16s (max 5 tentatives)
- [ ] Jitter aléatoire (±20%) pour éviter les thundering herd
- [ ] Réessai manuel des jobs échoués toutes les 5 min (max 3x)

#### Erreurs BDD (connection timeout, deadlock, constraint violation) :

- [ ] Rollback automatique de la transaction
- [ ] Log ERROR avec détail
- [ ] Retry le job complet au prochain cycle (si dernier essai < 5 min ago)
- [ ] Alerte CRITICAL si le même job échoue 3 fois consécutives

#### Erreurs de validation (rejection) :

- [ ] Skip l'enregistrement invalide
- [ ] Log WARNING avec raison + valeur rejetée
- [ ] Continuer le batch (pas de stop)

#### Graceful degradation :

- [ ] Si une source est indisponible : log WARNING, skip et continuer les autres
- [ ] Si 2 sources sur 3+ sont down : alerte CRITICAL, continuer quand même
- [ ] Pas de STOP complet du worker

### Dépendances

- Exception hierarchy dans `src/shared/exceptions.py`
- Configuration des timeouts

---

# MODULE API — EXIGENCES FONCTIONNELLES

## RF-API-001 : Enregistrement Utilisateur (Register)

**ID:** RF-API-001
**Priorité (MoSCoW):** MUST
**Statut:** Actif

### Description fonctionnelle

L'API doit permettre à un nouvel utilisateur de créer un compte en fournissant un email, username, mot de passe et type de persona (trader, journalist, investor).

### Critères d'acceptation

- [ ] Endpoint : `POST /api/v1/auth/register`
- [ ] Payload :
  ```json
  {
    "username": "alice123",
    "email": "alice@example.com",
    "password": "SecurePassword2026!",
    "persona_type": "trader"
  }
  ```
- [ ] Validation :
  - Username : 3-100 chars, alphanumeric + underscore, UNIQUE
  - Email : format RFC 5322, UNIQUE
  - Password : min 8 chars, recommandé: 1 uppercase, 1 digit, 1 special
  - Persona_type : enum ["trader", "journalist", "investor"]
- [ ] Réponse 201 Created :
  ```json
  {
    "data": {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "username": "alice123",
      "email": "alice@example.com",
      "persona_type": "trader",
      "preferences": {},
      "created_at": "2026-03-12T14:30:00Z"
    },
    "error": null,
    "meta": null
  }
  ```
- [ ] Réponse 400 Bad Request si validation échoue (email dupliquia, username existe, mot de passe faible)
- [ ] Hashing du mot de passe avec bcrypt (12 rounds) avant stockage
- [ ] Pas de retour du hash du mot de passe
- [ ] Logging : nouveau user registré (username, email)

### Dépendances

- passlib[bcrypt]
- Table `users` (RF-ETL-009)
- Schéma Pydantic `UserCreate`, `UserRead`

---

## RF-API-002 : Authentification et JWT (Login)

**ID:** RF-API-002
**Priorité (MoSCoW):** MUST
**Statut:** Actif

### Description fonctionnelle

L'API doit permettre à un utilisateur existant de se connecter avec email et mot de passe, et recevoir un token JWT pour les requêtes ultérieures.

### Critères d'acceptation

- [ ] Endpoint : `POST /api/v1/auth/login`
- [ ] Payload :
  ```json
  {
    "email": "alice@example.com",
    "password": "SecurePassword2026!"
  }
  ```
- [ ] Authentification :
  - Récupérer l'utilisateur par email
  - Vérifier le mot de passe avec bcrypt.verify()
  - Rejecter si email inexistant ou mot de passe incorrect (même message générique : "Invalid credentials")
- [ ] Token JWT :
  - Algorythme : HS256
  - Payload : `{"sub": user_id, "username": username, "exp": now + 24h}`
  - Clé secrète : depuis `.env` (HMAC_SECRET_KEY)
- [ ] Réponse 200 OK :
  ```json
  {
    "data": {
      "access_token": "eyJhbGc...",
      "token_type": "Bearer",
      "expires_in": 86400
    },
    "error": null,
    "meta": null
  }
  ```
- [ ] Réponse 401 Unauthorized si credentials invalides
- [ ] Logging : authentification utilisateur (success ou fail)

### Dépendances

- PyJWT
- Table `users`

---

## RF-API-003 : Current User Endpoint (Me)

**ID:** RF-API-003
**Priorité (MoSCoW):** MUST
**Statut:** Actif

### Description fonctionnelle

L'API doit retourner les infos de l'utilisateur actuellement authentifié, utilisé pour valider le JWT et le profil utilisateur.

### Critères d'acceptation

- [ ] Endpoint : `GET /api/v1/auth/me`
- [ ] Authentification requise : JWT dans header `Authorization: Bearer <token>`
- [ ] Validation du JWT :
  - Extraire le token du header
  - Décoder avec la clé secrète
  - Vérifier la signature et expiration
  - Rejecter si token invalide, expiré, ou malformé
- [ ] Récupérer l'utilisateur par `sub` du JWT
- [ ] Réponse 200 OK :
  ```json
  {
    "data": {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "username": "alice123",
      "email": "alice@example.com",
      "persona_type": "trader",
      "preferences": {"theme": "dark", "notifications": true},
      "created_at": "2026-03-12T14:30:00Z"
    },
    "error": null,
    "meta": null
  }
  ```
- [ ] Réponse 401 Unauthorized si token manquant, invalide, ou expiré
- [ ] Réponse 404 Not Found si utilisateur supprimé après création du token

### Dépendances

- PyJWT
- Middleware de validation JWT dans FastAPI

---

## RF-API-004 : Liste des Cryptos Suivies

**ID:** RF-API-004
**Priorité (MoSCoW):** MUST
**Statut:** Actif

### Description fonctionnelle

L'API doit exposer la liste des 30 symboles crypto suivis, avec métadonnées basiques (rank, market cap).

### Critères d'acceptation

- [ ] Endpoint : `GET /api/v1/crypto/list`
- [ ] Public (pas d'authentification requise)
- [ ] Réponse 200 OK :
  ```json
  {
    "data": [
      {
        "symbol": "BTCUSDT",
        "name": "Bitcoin",
        "rank": 1,
        "market_cap_usd": 1520000000000
      },
      {
        "symbol": "ETHUSDT",
        "name": "Ethereum",
        "rank": 2,
        "market_cap_usd": 210000000000
      }
    ],
    "error": null,
    "meta": null
  }
  ```
- [ ] Données statiques en mémoire ou cachées (TTL 24h)
- [ ] Ordre par rank croissant
- [ ] Champs : symbol, name, rank, market_cap_usd

### Dépendances

- Configuration centralisée des symboles dans `src/api/services/crypto_service.py`

---

## RF-API-005 : Données OHLCV Historiques

**ID:** RF-API-005
**Priorité (MoSCoW):** MUST
**Statut:** Actif

### Description fonctionnelle

L'API doit exposer les données de prix OHLCV historiques pour un symbole donné sur différents timeframes, avec pagination.

### Critères d'acceptation

- [ ] Endpoint : `GET /api/v1/crypto/{symbol}/prices`
- [ ] Public (pas d'authentification requise)
- [ ] Paramètres :
  - `symbol` : path param, pattern `^[A-Z0-9]+$` (ex : BTCUSDT)
  - `timeframe` : query param, default "1h", values ["1m", "5m", "15m", "30m", "1h", "2h", "3h", "4h", "1D", "1W", "1M"]
  - `start` : query param, ISO 8601 datetime (optionnel)
  - `end` : query param, ISO 8601 datetime (optionnel, défaut : now)
  - `limit` : query param, default 100, range [1, 1000]
  - `page` : query param, default 1, >= 1
- [ ] Validation :
  - Si symbol inexistant : 404 Not Found
  - Si timeframe invalide : 400 Bad Request
  - Si start > end : 400 Bad Request
- [ ] Requête BDD optimisée :
  - SELECT * FROM crypto_prices WHERE symbol = $1 AND timeframe = $2
  - Si start/end : AND timestamp BETWEEN $3 AND $4
  - ORDER BY timestamp DESC
  - LIMIT limit OFFSET (page-1)*limit
- [ ] Réponse 200 OK :
  ```json
  {
    "data": [
      {
        "symbol": "BTCUSDT",
        "price_open": "42500.50",
        "price_high": "43000.00",
        "price_low": "42400.00",
        "price_close": "42950.75",
        "volume_24h": "25000000",
        "market_cap": "850000000000",
        "timestamp": "2026-03-12T14:00:00Z",
        "source": "binance",
        "timeframe": "1h"
      }
    ],
    "error": null,
    "meta": {
      "total": 10000,
      "page": 1,
      "limit": 100
    }
  }
  ```
- [ ] Réponse vide si aucune donnée pour le filtre

### Dépendances

- Table `crypto_prices`
- Schéma Pydantic `OHLCVResponse`

---

## RF-API-006 : Indicateurs Techniques

**ID:** RF-API-006
**Priorité (MoSCoW):** MUST
**Statut:** Actif

### Description fonctionnelle

L'API doit exposer les indicateurs techniques calculés par l'ETL (RSI, Bollinger, harmonic patterns, etc.) pour un symbole et timeframe donné.

### Critères d'acceptation

- [ ] Endpoint : `GET /api/v1/crypto/{symbol}/indicators`
- [ ] Public
- [ ] Paramètres :
  - `symbol` : path param
  - `timeframe` : query param, default "1h"
  - `limit` : query param, default 100, range [1, 1000]
  - `page` : query param, default 1
- [ ] Requête BDD :
  - SELECT * FROM indicators WHERE symbol = $1 AND timeframe = $2
  - ORDER BY timestamp DESC
  - LIMIT/OFFSET pour pagination
- [ ] Réponse 200 OK :
  ```json
  {
    "data": [
      {
        "symbol": "BTCUSDT",
        "timeframe": "1h",
        "timestamp": "2026-03-12T14:00:00Z",
        "rsi": "68.5",
        "bollinger_upper": "44000.00",
        "bollinger_middle": "42500.00",
        "bollinger_lower": "41000.00",
        "price_vs_bollinger": "0.8",
        "harmonic_pattern": "Gartley",
        "trend_slope": "0.025",
        "trend_type": "aggressive",
        "metadata": {}
      }
    ],
    "error": null,
    "meta": {"total": 1000, "page": 1, "limit": 100}
  }
  ```
- [ ] Champs optionnels peuvent être null si non calculés

### Dépendances

- Table `indicators`
- Schéma Pydantic `IndicatorResponse`

---

## RF-API-007 : Dernier Prix et Indicateurs (Latest)

**ID:** RF-API-007
**Priorité (MoSCoW):** MUST
**Statut:** Actif

### Description fonctionnelle

L'API doit exposer le dernier prix OHLCV et les indicateurs techniques actuels pour un symbole (convenience endpoint pour le dashboard).

### Critères d'acceptation

- [ ] Endpoint : `GET /api/v1/crypto/{symbol}/latest`
- [ ] Public
- [ ] Paramètre : `symbol` path param
- [ ] Requête BDD :
  - Pour chaque timeframe pertinent (1h, 4h, 1D) : récupérer le dernier enregistrement
  - Ou retourner uniquement le 1h si pas de param timeframe
- [ ] Réponse 200 OK :
  ```json
  {
    "data": {
      "symbol": "BTCUSDT",
      "ohlcv": {
        "symbol": "BTCUSDT",
        "price_open": "42500.50",
        "price_high": "43000.00",
        "price_low": "42400.00",
        "price_close": "42950.75",
        "volume_24h": "25000000",
        "market_cap": "850000000000",
        "timestamp": "2026-03-12T14:00:00Z",
        "source": "binance",
        "timeframe": "1h"
      },
      "indicators": {
        "symbol": "BTCUSDT",
        "timeframe": "1h",
        "timestamp": "2026-03-12T14:00:00Z",
        "rsi": "68.5",
        "bollinger_upper": "44000.00",
        "bollinger_middle": "42500.00",
        "bollinger_lower": "41000.00",
        "price_vs_bollinger": "0.8",
        "harmonic_pattern": null,
        "trend_slope": "0.025",
        "trend_type": "aggressive"
      }
    },
    "error": null,
    "meta": null
  }
  ```

### Dépendances

- Tables `crypto_prices` et `indicators`
- Schéma Pydantic `LatestResponse`

---

## RF-API-008 : Market Overview

**ID:** RF-API-008
**Priorité (MoSCoW):** SHOULD
**Statut:** Phase 1

### Description fonctionnelle

L'API doit exposer un résumé du marché crypto (top movers, fear & greed index, market cap total).

### Critères d'acceptation

- [ ] Endpoint : `GET /api/v1/crypto/market-overview`
- [ ] Public
- [ ] Réponse 200 OK :
  ```json
  {
    "data": {
      "total_market_cap_usd": 3200000000000,
      "btc_dominance_pct": 52.5,
      "fear_greed_index": {
        "value": 62,
        "classification": "Greed"
      },
      "top_gainers_24h": [
        {"symbol": "DOGE", "change_pct": 15.5, "price_usd": "0.45"},
        {"symbol": "SHIB", "change_pct": 12.3, "price_usd": "0.000012"}
      ],
      "top_losers_24h": [
        {"symbol": "XRP", "change_pct": -8.2, "price_usd": "2.45"}
      ]
    },
    "error": null,
    "meta": null
  }
  ```
- [ ] Calcul des top movers : comparaison price_close 24h ago vs now
- [ ] Prise en cache (TTL 5 min) pour éviter les recalculs coûteux

### Dépendances

- Tables `crypto_prices`, `fear_greed_index` (si implémentée)

---

## RF-API-009 : Signaux Actifs (Active)

**ID:** RF-API-009
**Priorité (MoSCoW):** MUST
**Statut:** Actif

### Description fonctionnelle

L'API doit exposer les signaux de trading actifs (émis dans les dernières 24h) avec détails sur les règles et la confiance.

### Critères d'acceptation

- [ ] Endpoint : `GET /api/v1/signals/active`
- [ ] Public
- [ ] Requête BDD :
  - SELECT * FROM trading_signals WHERE created_at >= NOW() - INTERVAL '24 hours'
  - ORDER BY created_at DESC
  - Filtrer : confidence_score >= 0.6
- [ ] Réponse 200 OK :
  ```json
  {
    "data": [
      {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "symbol": "BTCUSDT",
        "signal_type": "BUY",
        "confidence_score": "0.75",
        "timeframe_primary": "4h",
        "timeframes_aligned": {
          "1h": {"rsi": 68, "bollinger_pos": 0.8},
          "2h": {"rsi": 70, "bollinger_pos": 0.85},
          "4h": {"rsi": 72, "bollinger_pos": 0.9}
        },
        "rules_triggered": ["rsi_multi_tf_convergence", "bollinger_band_walking"],
        "leverage_suggested": 5,
        "margin_safety": "2.5",
        "fees_estimated": "0.025",
        "model_version": "rules_v1",
        "created_at": "2026-03-12T12:30:00Z"
      }
    ],
    "error": null,
    "meta": null
  }
  ```

### Dépendances

- Table `trading_signals`
- Schéma Pydantic `SignalResponse`

---

## RF-API-010 : Signaux par Symbole

**ID:** RF-API-010
**Priorité (MoSCoW):** MUST
**Statut:** Actif

### Description fonctionnelle

L'API doit exposer l'historique des signaux pour un symbole crypto donné, avec pagination.

### Critères d'acceptation

- [ ] Endpoint : `GET /api/v1/signals/{symbol}`
- [ ] Public
- [ ] Paramètres :
  - `symbol` : path param
  - `timeframe` : query param (optionnel, filtrer par timeframe_primary)
  - `limit` : query param, default 50, range [1, 500]
  - `page` : query param, default 1
- [ ] Requête BDD :
  - SELECT * FROM trading_signals WHERE symbol = $1
  - Si timeframe : AND timeframe_primary = $2
  - ORDER BY created_at DESC
  - LIMIT/OFFSET
- [ ] Réponse 200 OK (même format que RF-API-009)
- [ ] Pagination meta

### Dépendances

- Table `trading_signals`

---

## RF-API-011 : Détail d'un Signal et Outcome

**ID:** RF-API-011
**Priorité (MoSCoW):** SHOULD
**Statut:** Phase 1

### Description fonctionnelle

L'API doit exposer le détail complet d'un signal avec son outcome (évaluation post-hoc si disponible).

### Critères d'acceptation

- [ ] Endpoint : `GET /api/v1/signals/{signal_id}/detail`
- [ ] Public
- [ ] Paramètre : `signal_id` path param (UUID)
- [ ] Requête BDD :
  - SELECT * FROM trading_signals WHERE id = $1
  - LEFT JOIN signal_outcomes ON signal_outcomes.signal_id = trading_signals.id
- [ ] Réponse 200 OK :
  ```json
  {
    "data": {
      "signal": { ... },
      "outcome": {
        "signal_id": "550e8400-e29b-41d4-a716-446655440000",
        "price_at_signal": "42950.75",
        "price_after_1h": "43100.00",
        "price_after_4h": "43500.00",
        "price_after_1d": "44000.00",
        "pnl_simulated": "0.0245",
        "was_correct": true,
        "evaluated_at": "2026-03-13T12:30:00Z"
      }
    },
    "error": null,
    "meta": null
  }
  ```
- [ ] Réponse 404 Not Found si signal_id inexistant

### Dépendances

- Tables `trading_signals`, `signal_outcomes`

---

## RF-API-012 : Performance des Signaux

**ID:** RF-API-012
**Priorité (MoSChoW):** SHOULD
**Statut:** Phase 1

### Description fonctionnelle

L'API doit exposer les statistiques agrégées de performance des signaux historiques (taux de réussite, PnL moyen).

### Critères d'acceptation

- [ ] Endpoint : `GET /api/v1/signals/performance`
- [ ] Public
- [ ] Requête BDD :
  - Compter les signaux avec outcome.was_correct = true/false
  - Moyenne de outcome.pnl_simulated
  - Répartition par signal_type (BUY/SELL/HOLD)
- [ ] Réponse 200 OK :
  ```json
  {
    "data": {
      "total_signals": 250,
      "win_rate_pct": 62.5,
      "avg_pnl": "0.0342",
      "by_signal_type": {
        "BUY": {"total": 150, "wins": 95, "win_rate": 63.3},
        "SELL": {"total": 80, "wins": 52, "win_rate": 65.0},
        "HOLD": {"total": 20, "wins": 8, "win_rate": 40.0}
      },
      "period": "last_30_days"
    },
    "error": null,
    "meta": null
  }
  ```

### Dépendances

- Tables `trading_signals`, `signal_outcomes`

---

## RF-API-013 : News Récentes

**ID:** RF-API-013
**Priorité (MoSChoW):** SHOULD
**Statut:** Phase 1

### Description fonctionnelle

L'API doit exposer les actualités crypto récentes avec possibilité de filtrer par source ou mot-clé.

### Critères d'acceptation

- [ ] Endpoint : `GET /api/v1/news/latest`
- [ ] Public
- [ ] Paramètres :
  - `source` : query param (optionnel, filter par source)
  - `keyword` : query param (optionnel, recherche dans title/content/keywords)
  - `limit` : query param, default 20, range [1, 100]
  - `page` : query param, default 1
- [ ] Requête BDD :
  - SELECT * FROM news_articles
  - Si source : AND source = $1
  - Si keyword : AND (title ILIKE '%keyword%' OR content ILIKE '%keyword%' OR keywords @> ARRAY[$1])
  - ORDER BY published_at DESC
  - LIMIT/OFFSET
- [ ] Réponse 200 OK :
  ```json
  {
    "data": [
      {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "title": "Bitcoin Breaks $43,000 as Institutions Pour In",
        "content": "...",
        "source": "Decrypt",
        "url": "https://decrypt.co/...",
        "published_at": "2026-03-12T10:30:00Z",
        "sentiment_score": "0.65",
        "keywords": ["Bitcoin", "institutional", "bullish"],
        "reliability_score": "0.95",
        "collected_at": "2026-03-12T11:00:00Z"
      }
    ],
    "error": null,
    "meta": {"total": 1200, "page": 1, "limit": 20}
  }
  ```

### Dépendances

- Table `news_articles`

---

## RF-API-014 : Détail d'un Article News

**ID:** RF-API-014
**Priorité (MoSChoW):** SHOULD
**Statut:** Phase 1

### Description fonctionnelle

L'API doit exposer le détail complet d'un article avec résultats de text mining (NLP).

### Critères d'acceptation

- [ ] Endpoint : `GET /api/v1/news/{news_id}`
- [ ] Public
- [ ] Requête BDD :
  - SELECT * FROM news_articles WHERE id = $1
  - LEFT JOIN text_mining_results ON text_mining_results.article_id = news_articles.id
- [ ] Réponse 200 OK :
  ```json
  {
    "data": {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "title": "Bitcoin Breaks $43,000...",
      "content": "...",
      "source": "Decrypt",
      "url": "https://...",
      "published_at": "2026-03-12T10:30:00Z",
      "sentiment_score": "0.65",
      "keywords": ["Bitcoin", "institutional"],
      "reliability_score": "0.95",
      "text_mining": {
        "summary": "Bitcoin surpasses $43,000 due to institutional interest.",
        "entities": [{"type": "ORG", "value": "Bitcoin"}],
        "topics": ["cryptocurrency", "trading", "investment"],
        "word_cloud": {"bitcoin": 10, "institutions": 8, "bullish": 5}
      }
    },
    "error": null,
    "meta": null
  }
  ```

### Dépendances

- Tables `news_articles`, `text_mining_results`

---

## RF-API-015 : Sentiment Global par Crypto

**ID:** RF-API-015
**Priorité (MoSChoW):** SHOULD
**Statut:** Phase 1

### Description fonctionnelle

L'API doit exposer un score de sentiment agrégé pour les articles mentionnant chaque crypto.

### Critères d'acceptation

- [ ] Endpoint : `GET /api/v1/news/sentiment`
- [ ] Public
- [ ] Requête BDD :
  - Matcher les keywords des articles avec les symboles crypto
  - GROUP BY symbol, calculer AVG(sentiment_score)
  - Compter les articles par symbol
- [ ] Réponse 200 OK :
  ```json
  {
    "data": {
      "last_24h": [
        {"symbol": "BTC", "avg_sentiment": "0.68", "article_count": 45},
        {"symbol": "ETH", "avg_sentiment": "0.62", "article_count": 28},
        {"symbol": "SOL", "avg_sentiment": "-0.15", "article_count": 5}
      ],
      "period": "24_hours"
    },
    "error": null,
    "meta": null
  }
  ```

### Dépendances

- Table `news_articles`

---

## RF-API-016 : Portfolio (CRUD)

**ID:** RF-API-016
**Priorité (MoSChoW):** SHOULD
**Statut:** Phase 1

### Description fonctionnelle

L'API doit permettre à un utilisateur authentifié de gérer son portefeuille (positions crypto).

### Critères d'acceptation

#### GET /api/v1/portfolio :

- [ ] Authentification requise (JWT)
- [ ] Récupérer toutes les positions de l'utilisateur courant
- [ ] Réponse 200 OK :
  ```json
  {
    "data": [
      {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "symbol": "BTC",
        "quantity": "0.5",
        "entry_price": "40000.00",
        "current_price": "43000.00",
        "unrealized_pnl": "1500.00",
        "unrealized_pnl_pct": "3.75"
      }
    ],
    "error": null,
    "meta": null
  }
  ```

#### POST /api/v1/portfolio :

- [ ] Authentification requise
- [ ] Payload :
  ```json
  {
    "symbol": "BTC",
    "quantity": "0.5",
    "entry_price": "40000.00"
  }
  ```
- [ ] Validation : symbol existe, quantity > 0, entry_price > 0
- [ ] Réponse 201 Created (returned object)

#### PUT /api/v1/portfolio/{id} :

- [ ] Authentification requise
- [ ] Modification d'une position (quantity, entry_price)
- [ ] Vérification que la position appartient à l'utilisateur courant
- [ ] Réponse 200 OK

#### DELETE /api/v1/portfolio/{id} :

- [ ] Authentification requise
- [ ] Suppression d'une position
- [ ] Vérification de propriété
- [ ] Réponse 204 No Content

### Dépendances

- Table `portfolio`
- JWT middleware

---

## RF-API-017 : Watchlist (CRUD)

**ID:** RF-API-017
**Priorité (MoSChoW):** SHOULD
**Statut:** Phase 1

### Description fonctionnelle

L'API doit permettre à un utilisateur authentifié de gérer sa liste de suivi (watchlist).

### Critères d'acceptation

#### GET /api/v1/watchlist :

- [ ] Authentification requise
- [ ] Récupérer les symboles de la watchlist de l'utilisateur
- [ ] Réponse 200 OK :
  ```json
  {
    "data": [
      {
        "symbol": "BTCUSDT",
        "name": "Bitcoin",
        "added_at": "2026-03-10T12:00:00Z"
      }
    ],
    "error": null,
    "meta": null
  }
  ```

#### POST /api/v1/watchlist :

- [ ] Authentification requise
- [ ] Payload : `{"symbol": "BTCUSDT"}`
- [ ] Validation : symbol existe dans la liste des suivis
- [ ] Deduplication : rejeter si symbole déjà dans la watchlist
- [ ] Réponse 201 Created

#### DELETE /api/v1/watchlist/{symbol} :

- [ ] Authentification requise
- [ ] Suppression du symbole
- [ ] Réponse 204 No Content

### Dépendances

- Table `watchlist` (à créer, avec user_id + symbol UNIQUE)

---

## RF-API-018 : Chatbot IA

**ID:** RF-API-018
**Priorité (MoSChoW):** SHOULD
**Statut:** Phase 1

### Description fonctionnelle

L'API doit permettre à un utilisateur authentifié de poser des questions au chatbot IA pour obtenir des insights sur les données crypto.

### Critères d'acceptation

- [ ] Endpoint : `POST /api/v1/chat`
- [ ] Authentification requise (JWT)
- [ ] Payload :
  ```json
  {
    "message": "What's the current state of Bitcoin?"
  }
  ```
- [ ] Service chatbot :
  - Récupérer le contexte utilisateur (portfolio, watchlist, signaux actifs, derniers prix)
  - Construire un system prompt : "You are a crypto market analyst. Answer questions about the following data: {context}. Always start with 'I am not a financial advisor.'"
  - Appeler l'API OpenAI (GPT-4o-mini) ou Anthropic (Claude)
  - Streaming (optionnel pour V1, peut être response simple avec token limit 500)
- [ ] Réponse 200 OK :
  ```json
  {
    "data": {
      "message": "I am not a financial advisor. Bitcoin is currently trading at $42,950, up 1.2% in the last 24 hours. Your portfolio holds 0.5 BTC with an unrealized gain of $1,500..."
    },
    "error": null,
    "meta": null
  }
  ```
- [ ] Réponse 429 Too Many Requests si l'utilisateur dépasse 10 messages/minute
- [ ] Logging : user_id, message length, API latency

### Dépendances

- OpenAI API key (dans `.env`)
- LangChain ou simple wrapper
- Rate limiting

---

## RF-API-019 : Healthcheck

**ID:** RF-API-019
**Priorité (MoSChoW):** MUST
**Statut:** Actif

### Description fonctionnelle

L'API doit exposer un endpoint de healthcheck pour la surveillance du service.

### Critères d'acceptation

- [ ] Endpoint : `GET /health`
- [ ] Public (pas d'authentification)
- [ ] Checks :
  - Connectivité BDD (requête simple : `SELECT 1`)
  - Connectivité MinIO (test de connexion)
  - Disponibilité de l'API elle-même (toujours 200 si l'endpoint répond)
- [ ] Réponse 200 OK si tous les checks passent :
  ```json
  {
    "status": "healthy",
    "timestamp": "2026-03-12T14:30:00Z",
    "checks": {
      "database": {"status": "ok", "latency_ms": 12},
      "minio": {"status": "ok", "latency_ms": 45}
    }
  }
  ```
- [ ] Réponse 503 Service Unavailable si un check critique échoue
- [ ] Timeout global : 5 secondes

### Dépendances

- Accès à la BDD et MinIO

---

## RF-API-020 : Statut des Sources de Données

**ID:** RF-API-020
**Priorité (MoSChoW):** SHOULD
**Statut:** Phase 1

### Description fonctionnelle

L'API doit exposer l'état de santé et la fraîcheur des données pour chaque source.

### Critères d'acceptation

- [ ] Endpoint : `GET /api/v1/system/sources-status`
- [ ] Public
- [ ] Réponse 200 OK :
  ```json
  {
    "data": {
      "sources": [
        {
          "name": "binance_ohlcv",
          "status": "healthy",
          "last_data_received": "2026-03-12T14:28:00Z",
          "data_staleness_minutes": 2,
          "error_rate_1h": 0.5,
          "uptime_24h_pct": 99.8
        },
        {
          "name": "coingecko_market_data",
          "status": "degraded",
          "last_data_received": "2026-03-12T14:15:00Z",
          "data_staleness_minutes": 15,
          "error_rate_1h": 5.2,
          "uptime_24h_pct": 98.2
        }
      ]
    },
    "error": null,
    "meta": null
  }
  ```
- [ ] Logique de statut :
  - healthy : fraîcheur < 5 min, error_rate < 1%
  - degraded : fraîcheur < 30 min, error_rate < 5%
  - unhealthy : fraîcheur > 30 min OU error_rate > 5%
  - offline : aucune donnée depuis > 2h

### Dépendances

- Logging de l'ETL exposé via une table ou cache

---

## RF-API-021 : Pagination

**ID:** RF-API-021
**Priorité (MoSChoW):** MUST
**Statut:** Actif

### Description fonctionnelle

Tous les endpoints retournant des listes doivent supporter la pagination avec limit/offset.

### Critères d'acceptation

- [ ] Paramètres standards :
  - `limit` : nombre d'éléments par page, default 20-100, max 1000
  - `page` : numéro de page (1-indexed), default 1
- [ ] Métadonnées de réponse :
  ```json
  "meta": {
    "total": 10000,
    "page": 1,
    "limit": 100,
    "has_next": true,
    "has_prev": false
  }
  ```
- [ ] Validation :
  - limit < 1 : erreur 400
  - page < 1 : erreur 400
  - limit > max : cliper à max

### Dépendances

- Middleware ou utility de pagination

---

## RF-API-022 : Rate Limiting

**ID:** RF-API-022
**Priorité (MoSChoW):** SHOULD
**Statut:** Phase 1

### Description fonctionnelle

L'API doit implémenter le rate limiting sur les endpoints sensibles pour éviter les abus.

### Critères d'acceptation

#### Endpoints protégés :

- [ ] `/auth/register` : 5 requêtes par minute par IP
- [ ] `/auth/login` : 10 requêtes par minute par IP
- [ ] `/chat` : 10 requêtes par minute par user_id (authentifié)
- [ ] Autres endpoints publics : 100 requêtes par minute par IP

#### Implémentation :

- [ ] Utiliser le middleware Nginx ou la librairie slowapi
- [ ] Header de réponse : `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`
- [ ] Réponse 429 Too Many Requests quand limite atteinte

### Dépendances

- slowapi ou Nginx

---

## RF-API-023 : Gestion des Erreurs

**ID:** RF-API-023
**Priorité (MoSChoW):** MUST
**Statut:** Actif

### Description fonctionnelle

L'API doit retourner des messages d'erreur cohérents et informatifs sans exposer d'informations sensibles.

### Critères d'acceptation

- [ ] Format standard pour toutes les erreurs :
  ```json
  {
    "data": null,
    "error": {
      "code": "RESOURCE_NOT_FOUND",
      "message": "The requested signal does not exist",
      "details": {} (optionnel, validation errors)
    },
    "meta": null
  }
  ```

- [ ] Codes d'erreur standards :
  - `INVALID_REQUEST` : validation échouée (400)
  - `UNAUTHORIZED` : JWT invalide/manquant (401)
  - `FORBIDDEN` : utilisateur n'a pas accès (403)
  - `RESOURCE_NOT_FOUND` : ressource inexistante (404)
  - `CONFLICT` : violation de contrainte unique (409)
  - `RATE_LIMIT_EXCEEDED` : trop de requêtes (429)
  - `INTERNAL_SERVER_ERROR` : erreur serveur (500)

- [ ] Ne jamais exposer :
  - Stack trace Python
  - Requête SQL originale
  - Tokens ou secrets
  - Numéros de version internes

- [ ] Logging côté serveur : log complet (stack, contexte) mais ne pas retourner

### Dépendances

- Exception hierarchy personnalisée

---

## RF-API-024 : CORS

**ID:** RF-API-024
**Priorité (MoSChoW):** MUST
**Statut:** Actif

### Description fonctionnelle

L'API doit configurer CORS pour accepter les requêtes du frontend Streamlit uniquement.

### Critères d'acceptation

- [ ] Configuration :
  - `allow_origins` : liste blanche de l'origin du frontend (ex : `http://localhost:8501`, `https://cryptobot.example.com`)
  - `allow_methods` : ["GET", "POST", "PUT", "DELETE"]
  - `allow_headers` : ["Content-Type", "Authorization"]
  - `allow_credentials` : true (pour les cookies de session si ajoutés plus tard)
  - `max_age` : 3600 (cache CORS preflight)

- [ ] Rejecter les origins non-autorisées
- [ ] Pas de wildcard `*` pour les origins

### Dépendances

- FastAPI CORSMiddleware

---

## RF-API-025 : Documentation Swagger/OpenAPI

**ID:** RF-API-025
**Priorité (MoSChoW):** SHOULD
**Statut:** Phase 1

### Description fonctionnelle

L'API doit générer automatiquement une documentation interactive Swagger (OpenAPI 3.0).

### Critères d'acceptation

- [ ] Endpoint `/docs` : interface interactive Swagger UI
- [ ] Endpoint `/redoc` : documentation ReDoc
- [ ] Tous les endpoints documentés avec :
  - Description textuelle
  - Paramètres (path, query, body) avec types et descriptions
  - Exemples de requête/réponse
  - Codes de statut possibles (200, 400, 401, 404, 500)
- [ ] Authentification dans Swagger : champ pour rentrer le JWT bearer token
- [ ] Schémas Pydantic auto-documentés (descriptions sur chaque champ)

### Dépendances

- FastAPI (auto-génération)

---

## RF-API-026 : Logging et Monitoring API

**ID:** RF-API-026
**Priorité (MoSChoW):** SHOULD
**Statut:** Phase 1

### Description fonctionnelle

L'API doit logger les requêtes et réponses pour le debugging et le monitoring.

### Critères d'acceptation

- [ ] Middleware de logging :
  - Chaque requête : method, path, status, latency, user_id (si auth)
  - Format JSON pour parsabilité
  - Logging en stdout pour Docker capture
- [ ] Niveau de détail :
  - DEBUG : requête/réponse complètes (bodies truncated > 1KB)
  - INFO : résumé (method, path, status, latency)
  - ERROR : erreurs 5xx avec stack trace

### Dépendances

- Middleware FastAPI custom

---

# EXIGENCES NON-FONCTIONNELLES

## RNF-001 : Performance — Temps de Réponse API

**Objectif :** P95 latency < 500ms, P99 < 2s

### Critères

- [ ] Requêtes simples (GET /crypto/list) : < 100ms
- [ ] Requêtes avec BDD (GET /crypto/{symbol}/prices) : < 300ms
- [ ] Requêtes complexes (GET /signals/performance) : < 1s
- [ ] Endpoint chatbot : < 5s (appel LLM compris)

---

## RNF-002 : Performance — ETL Throughput

**Objectif :** Collecter 30 cryptos × 10 timeframes × 1 candle/min = 300 candles/min

### Critères

- [ ] Batch insert TimescaleDB : < 5s pour 1000 rows
- [ ] Deduplication query : < 100ms par batch
- [ ] Calcul d'indicateurs : < 1s par crypto par timeframe

---

## RNF-003 : Disponibilité

**Objectif :** 99.5% uptime en production

### Critères

- [ ] Graceful degradation si un service est down (continue without that source)
- [ ] Alertes CRITICAL si un job échoue 3x consécutives
- [ ] Healthcheck tous les 30s

---

## RNF-004 : Sécurité — Authentification

**Exigences**

- [ ] JWT HS256 avec expiration 24h
- [ ] Mot de passe hashé bcrypt 12 rounds
- [ ] HTTPS obligatoire en production (Let's Encrypt)
- [ ] Pas de secrets en .env committé

---

## RNF-005 : Sécurité — Validation des Entrées

**Exigences**

- [ ] Validation Pydantic sur TOUS les inputs externes
- [ ] Requêtes SQL paramétrées (jamais de string interpolation)
- [ ] Rate limiting sur endpoints sensibles

---

## RNF-006 : Sécurité — Gestion des Erreurs

**Exigences**

- [ ] Ne pas exposer de stack traces au client
- [ ] Logging côté serveur avec contexte complet
- [ ] Messages d'erreur génériques (ex : "Invalid credentials" pour login fail)

---

## RNF-007 : Scalabilité — BDD

**Exigences**

- [ ] Connection pooling (SQLAlchemy max_overflow=0)
- [ ] Indexes sur colonnes fréquemment filtrées
- [ ] Hypertables TimescaleDB pour séries temporelles
- [ ] Pagination pour éviter les requêtes énormes

---

## RNF-008 : Scalabilité — API

**Exigences**

- [ ] Stateless (pas de session en mémoire)
- [ ] Caching HTTP (Cache-Control headers)
- [ ] Pagination standard

---

## RNF-009 : Résilience — Retry et Backoff

**Exigences**

- [ ] Exponential backoff : 1s, 2s, 4s, 8s, 16s
- [ ] Max 5 tentatives par requête
- [ ] Logging de chaque retry

---

## RNF-010 : Maintenabilité — Code

**Exigences**

- [ ] Type hints sur 100% des fonctions
- [ ] Tests unitaires + intégration >= 80% coverage
- [ ] Pydantic pour validation
- [ ] Repository pattern pour accès données

---

## RNF-011 : Maintenabilité — Documentation

**Exigences**

- [ ] Docstrings Google-style sur fonctions publiques
- [ ] README au niveau du projet
- [ ] Swagger OpenAPI auto
- [ ] Logging structuré JSON

---

## RNF-012 : Conformité Légale

**Exigences**

- [ ] Pas d'exécution automatique de trades (signaux informatifs uniquement)
- [ ] Disclaimer "Not financial advice" sur chatbot
- [ ] Respect robots.txt pour web scraping
- [ ] User-Agent correct sur requêtes HTTP

---

# MATRICE DE TRAÇABILITÉ

| Entité | RF-ETL | RF-API | RNF | Notes |
|--------|--------|--------|-----|-------|
| Binance REST | 001 | — | 002, 009 | Historique OHLCV |
| Binance WebSocket | 002 | — | 002, 009 | Temps réel OHLCV |
| CCXT | 003 | — | 009 | Fallback multi-exchange |
| CoinGecko | 004 | — | 009 | Market data |
| News scraping | 005 | 013-015 | 012 | Decrypt, Cointelegraph, etc. |
| Fear & Greed | 006 | 008 | — | Alternative.me |
| Scheduling | 007 | — | 003, 009 | APScheduler |
| TimescaleDB crypto_prices | 008 | 005-007 | 007 | Hypertable OHLCV |
| TimescaleDB indicators | 009 | 006 | 007 | Indicateurs techniques |
| TimescaleDB signals | 009 | 009-012 | 007 | Trading signals |
| TimescaleDB news | 009 | 013-015 | 007 | News articles |
| Validation Pydantic | 010 | 001-018 | 005, 010 | Toutes les entrées |
| Déduplication | 011 | — | 010 | Unicité garantie |
| Gap detection | 012 | 020 | 003 | Réconciliation horaire |
| MinIO | 013 | — | 007, 011 | Archivage datasets/modèles |
| Logging | 014 | 026 | 010, 011 | JSON structuré |
| Healthcheck | 015 | 019 | 003 | Monitoring |
| Error handling | 016 | 023 | 004-006, 010 | Graceful degradation |
| Auth register | — | 001 | 004, 005 | Pydantic + bcrypt |
| Auth login | — | 002 | 004, 005 | JWT HS256 |
| Auth me | — | 003 | 004 | Token validation |
| Pagination | — | 021 | 007 | Tous les endpoints liste |
| Rate limiting | — | 022 | 004, 005 | Endpoints sensibles |
| CORS | — | 024 | 004, 006 | Frontend Streamlit |
| Swagger | — | 025 | 011 | OpenAPI 3.0 |
| Chatbot | — | 018 | 004, 006 | LLM context + rate limit |

---

**Fin du document — Cahier des Charges Fonctionnelles v1.0**
