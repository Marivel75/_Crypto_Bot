---
type: livrable-rncp
bloc: 2
source: rncp-agent-L2-ETL-Report
tags: [cryptobot, rncp, bloc2, etl]
created: 2026-04-14
---

# Bloc 2 — Rapport d'exécution ETL

Procédures d'extraction, traitement et stockage du pipeline CryptoBot. Ce document explicite comment les données brutes issues des APIs publiques crypto sont acquises, nettoyées, enrichies d'indicateurs et persistées dans TimescaleDB + MinIO.

Sources primaires : [[../../code/etl]], [[../../architecture/ac01-etl-pipeline]], [[../../architecture/c02-etl-components]].

## 1. Vue d'ensemble du pipeline ETL

Pipeline asynchrone piloté par APScheduler, 10 jobs indépendants, communication via interfaces partagées `src/shared/models/`. Aucun broker — orchestration in-process.

```
┌──────────────────────────────────────────────────────────────────────────┐
│  EXTRACT (collectors)                                                    │
│   Binance REST  ─┐                                                       │
│   CoinGecko     ─┤     httpx.AsyncClient                                 │
│   CCXT          ─┼──►  with_retry(5, exp-backoff)  ──►  Raw payloads     │
│   Alt.me F&G    ─┤     (rate-limit detect 429)                           │
│   RSS News      ─┤     (timeout 30s/connect 10s)                         │
│   ESMA/SEC*     ─┘                                                       │
├──────────────────────────────────────────────────────────────────────────┤
│  TRANSFORM (transformers)                                                │
│   Pydantic v2 validation  → OHLCVRecord / NewsArticle / IndicatorRecord  │
│   deduplicate_ohlcv       → clé (symbol, timeframe, timestamp)           │
│   filter_valid_records    → invariants high/low/volume                   │
│   detect_gaps             → expected_interval par TF                     │
│   compute_indicators      → RSI(14), BB(20,2), trend_slope               │
├──────────────────────────────────────────────────────────────────────────┤
│  LOAD (loaders)                                                          │
│   MinIO raw/                s3://raw/{source}/{symbol}/{yyyy-mm-dd}/     │
│   MinIO datasets/           Parquet + pyarrow, partition quotidienne     │
│   TimescaleDB crypto_prices UPSERT ON CONFLICT (symbol, timeframe, ts)   │
│   TimescaleDB indicators    UPSERT avec DO UPDATE                        │
│   TimescaleDB news          UPSERT ON CONFLICT (url)                     │
└──────────────────────────────────────────────────────────────────────────┘
        *ESMA/SEC = backlog Phase 2, non implémenté en MVP
```

Diagramme d'activité complet : [[../../architecture/ac01-etl-pipeline]]. Vue composants : [[../../architecture/c02-etl-components]].

## 2. Sources de données

Toutes les sources sont **gratuites ou tier gratuit**. Aucune clé payante. Les clés Demo (CoinGecko) sont optionnelles via `settings.coingecko_api_key`.

| Source          | Protocole     | Endpoint / URL                              | Rate-limit          | Fréquence collecte | Volume/jour estimé                                |
|-----------------|---------------|---------------------------------------------|---------------------|--------------------|---------------------------------------------------|
| Binance         | HTTPS REST    | `https://api.binance.com/api/v3/klines`     | 1200 req/min IP     | 1 min / 5 min      | `13 symbols × 3 TF × 1440 + 30 symbols × 4 TF × 288` ≈ 91 k klines |
| CoinGecko Demo  | HTTPS REST    | `https://api.coingecko.com/api/v3/coins/markets` | 30 req/min (Demo)   | 5 min              | 288 requêtes (1 batch × 13 coin_ids)              |
| CCXT            | HTTPS REST    | Multi-exchange fallback async               | dépend de l'exchange | ad-hoc (fallback) | [À MESURER] — déclenché seulement si Binance KO   |
| Alternative.me  | HTTPS REST    | `https://api.alternative.me/fng/?limit=1`   | non documenté       | 60 min             | 24 appels (1 valeur entière [0,100])              |
| News RSS        | HTTPS + XML   | decrypt.co/feed, cointelegraph.com/rss, cryptonews.com/news/feed/ | courtoisie HTTP     | 15 min             | `3 flux × 96` = 288 fetches, ~30 articles/h       |
| ESMA / SEC      | HTTPS REST    | _backlog Phase 2_                           | _n/a MVP_           | _n/a MVP_          | `[À IMPLÉMENTER]` — cf [[../../specs/data-sources-roadmap]] |

Références code :
- `src/etl/collectors/binance.py:17` — `_BASE_URL`, timeout `httpx.Timeout(30.0, connect=10.0)`
- `src/etl/collectors/coingecko.py:15` — `_BASE_URL`, base_delay 2.0s (rate limit stricter)
- `src/etl/collectors/news.py:16-20` — `_DEFAULT_SOURCES` (Decrypt, Cointelegraph, CryptoNews)
- `src/etl/collectors/fear_greed.py:18` — URL unique `?limit=1`
- `src/etl/collectors/ccxt_collector.py` — exchange par défaut `"binance"`

Note : la doc projet liste PhoenixNews ; le code actuel a substitué par `cryptonews.com`. À aligner — cf section 8.

## 3. Procédure d'extraction

Chaque collector est une classe async context-manager partageant un `httpx.AsyncClient` avec pool de connexions. Les 5 collectors suivent un pattern commun.

### 3.1 Pattern commun

```python
async with BinanceCollector() as collector:
    records = await with_retry(
        lambda: collector._get_klines(symbol, interval, limit),
        max_attempts=5,
        base_delay=1.0,
        exceptions=(RateLimitError, ExternalAPIError, httpx.TransportError),
    )
```

### 3.2 Paramètres par collector

| Collector       | Auth                                | Pagination              | Retry (max_attempts / base_delay) | Timeout total / connect | Circuit breaker               |
|-----------------|-------------------------------------|-------------------------|-----------------------------------|-------------------------|-------------------------------|
| Binance         | Public (aucune)                     | `limit` param (≤1000)   | 5 / 1.0s                          | 30s / 10s               | 429 → `RateLimitError` + retry-after |
| CoinGecko       | Header `x-cg-demo-key` si présent   | `per_page` + `page`     | 5 / 2.0s                          | 30s / 10s               | 429 → `RateLimitError`        |
| CCXT            | Public Binance fallback             | `limit` param           | `[À MESURER]`                     | défaut httpx ccxt       | exception bubble-up           |
| Fear & Greed    | Public                              | `limit=1` (dernière)    | 3 / 2.0s                          | 30s / 10s               | Non-2xx → `ExternalAPIError`  |
| News RSS        | `User-Agent: crypto-bot/1.0`        | feed entries (all)      | Aucun retry (per-feed isolé)      | 30s / 10s               | Feeds individuels isolés try/except |

Références : `src/etl/collectors/binance.py:101-106`, `coingecko.py:96-101`, `fear_greed.py:72-77`, `news.py:72-87`, `src/shared/utils.py:46-76` (with_retry implementation avec backoff exponentiel 1s → 2s → 4s → 8s → 16s).

### 3.3 Concurrence

Job-level concurrency gate : `_CONCURRENCY = asyncio.Semaphore(5)` dans `src/etl/jobs.py:15`. Limite simultanée à 5 fetches même sur 30 symboles × 4 timeframes.

`asyncio.gather(..., return_exceptions=True)` isole les échecs par symbole (`src/etl/jobs.py:42,77,223,254,294`) — un symbole KO n'annule pas le batch.

### 3.4 Gestion des erreurs

Hiérarchie d'exceptions partagée (cf [[../../architecture/cl05-exceptions]]) :
- `RateLimitError` → déclenche backoff + `Retry-After` header quand dispo (`binance.py:142-147`, `coingecko.py:142-147`)
- `ExternalAPIError` → propagée après 5 tentatives, journalisée via `logger.exception`
- `httpx.TransportError` → réseau, incluse dans le retry set

## 4. Procédure de traitement

Pipeline de transformers in-memory, exécutés séquentiellement dans chaque job. Pas de persistance intermédiaire côté raw-OHLCV (l'idempotence vient du UPSERT TimescaleDB).

### 4.1 Ordre des transformations (cas OHLCV)

1. **Parse** — Binance retourne des arrays positionnels ; `BinanceCollector._parse_kline` mappe les indices `_IDX_OPEN_TIME=0 … _IDX_VOLUME=5` en `OHLCVRecord` Pydantic (`src/etl/collectors/binance.py:164-186`). Prix en `Decimal` pour éviter la perte de précision float.
2. **Dédoublonnage** — `deduplicate_ohlcv(records)` (`src/etl/transformers/cleaner.py:13-29`) : clé naturelle `(symbol, timeframe, timestamp)`, first-seen wins, compteur logué.
3. **Validation invariants** — `filter_valid_records(records)` (`cleaner.py:60-92`) partitionne en `valid/invalid` selon 5 invariants (`cleaner.py:32-57`) :
   - `high >= open`
   - `high >= close`
   - `low <= open`
   - `low <= close`
   - `volume >= 0`
   Les records invalides sont loggés (niveau `warning`) et écartés.
4. **Détection de gaps** — `detect_gaps(records, expected_interval)` (`cleaner.py:95-128`) : parcourt la série triée, calcule `actual_diff = records[i].ts - records[i-1].ts`, signale si `actual_diff / expected_interval > 1`. `_TIMEFRAME_INTERVALS` (`cleaner.py:131-141`) mappe `1m→1min`, `5m→5min`, `1h→1h`, `4h→4h`, `1D→1d`, `1W→7d`, `1M→30d`.
5. **Insertion** — cf section 5.

### 4.2 Calcul d'indicateurs

Job dédié `job_compute_indicators` (5 min). Pour chaque `(symbol, timeframe)` dans `RSI_BB_TIMEFRAMES ∪ TREND_TIMEFRAMES` :

1. `fetch_ohlcv_for_indicators(symbol, tf, limit=500)` (`timescaledb.py`)
2. Skip si `len(rows) < 20` (`jobs.py:215-216`) — on n'a pas assez d'historique pour RSI(14) + BB(20)
3. `compute_indicators_for_symbol` : construit DataFrame pandas, calcule
   - `compute_rsi(close, period=14)`
   - `compute_bollinger_bands(close, period=20, stddev=2)`
   - `compute_price_vs_bollinger`, `compute_trend_slope`, `compute_volume_relatif`
4. UPSERT vers `indicators` (DO UPDATE car recalcul possible).

Référence code : `src/etl/transformers/indicators.py` + outline [[../../code/etl]].

### 4.3 Enrichissement NLP (news)

Job `job_enrich_news_nlp` (20 min, `jobs.py:304-333`) :

1. `fetch_unprocessed_news(limit=100)` — articles sans sentiment
2. Par article : `extract_keywords(text, top_n=10)` + `_compute_lexicon_sentiment(text)`
3. Sentiment lexicon (`jobs.py:336-397`) : 24 positifs (`bullish, surge, rally, ...`) / 25 négatifs (`bearish, crash, hack, ...`). Score = `(pos - neg) / total` ∈ `[-1, 1]`.
4. `update_news_nlp(article_id, sentiment, keywords)` — UPDATE SQL.

## 5. Procédure de stockage

Stockage dual : MinIO pour raw/datasets (immutable, partitionné), TimescaleDB pour clean/requêtable.

### 5.1 MinIO (S3-compatible)

Buckets créés idempotemment au démarrage via `ensure_buckets_exist` (`minio_loader.py:45-54`) :

| Bucket            | Contenu                                     | Partitionnement                                   |
|-------------------|---------------------------------------------|---------------------------------------------------|
| `raw`             | Payloads JSON bruts (CoinGecko) + OHLCV Parquet | `binance/{symbol}/{yyyy-mm-dd}/ohlcv.parquet` (`minio_loader.py:79`) puis `coingecko/markets/{yyyy-mm-dd}/market_data.json` (`jobs.py:121`) |
| `datasets`        | Features/training sets pour ML              | `{filename}` par upload, nommage libre appelant   |
| `models`          | Artefacts ML (.pkl, .onnx)                  | Externe ETL — écrit par équipe ML                 |
| `mlflow-artifacts`| Runs MLflow                                 | Géré par MLflow lui-même                          |

Serialisation Parquet via `pandas.to_parquet(engine="pyarrow", index=False)` (`minio_loader.py:76, 164`). Appels bloquants MinIO encapsulés dans `asyncio.to_thread` pour ne pas bloquer la boucle événementielle.

Note : la spec RNCP parlait de partition `s3://raw/{source}/{yyyy-mm-dd}/{hh}/` ; l'implémentation actuelle expose `raw/binance/{symbol}/{date}/ohlcv.parquet` — pas de partition horaire car les fichiers sont daily. À revoir si on passe à un ingest temps-quasi-réel (cf risques).

### 5.2 TimescaleDB

3 hypertables principales. Clé primaire composite sur OHLCV + indicators. Référence schéma complet : [[../../architecture/er01-database-schema]].

| Table             | PK composite                                | Stratégie d'insertion                             | Fichier/lignes           |
|-------------------|---------------------------------------------|---------------------------------------------------|--------------------------|
| `crypto_prices`   | `(symbol, timeframe, timestamp)`            | `INSERT … ON CONFLICT DO NOTHING`                 | `timescaledb.py:47-55`   |
| `indicators`      | `(symbol, timeframe, timestamp)`            | `INSERT … ON CONFLICT DO UPDATE` (recalcul possible) | `timescaledb.py:95-115`  |
| `news`            | `url` UNIQUE                                | `ON CONFLICT (url) DO NOTHING`                    | `timescaledb.py:129-150` |
| `signal_outcomes` | clé `signal_id`                             | `insert_signal_outcome` upsert-équivalent         | `timescaledb.py` (section outcomes) |

Rétention/compression — politique cible documentée : rétention 90j, compression à 7j. `[À CONFIRMER]` dans la migration `src/etl/migrations/versions/20241101_initial_schema.py` (non relu ici).

## 6. Orchestration APScheduler

10 jobs enregistrés dans `build_scheduler()` (`src/etl/main.py:50-136`), tous avec `max_instances=1, coalesce=True` — pas de run en parallèle du même job, les missed runs coalescent.

| # | Job ID                     | Trigger             | Collectors             | Transformers                          | Loaders                    | SLA cible                    |
|---|----------------------------|---------------------|------------------------|---------------------------------------|----------------------------|------------------------------|
| 1 | `collect_ohlcv_priority`   | interval 1 min      | Binance                | dedup, validate                       | `insert_ohlcv_batch`       | < 60s par run                |
| 2 | `collect_ohlcv_all`        | interval 5 min      | Binance (30 symbols)   | dedup, validate                       | `insert_ohlcv_batch`       | < 300s par run               |
| 3 | `collect_market_data`      | interval 5 min      | CoinGecko              | aggrégation mkt-cap + BTC dominance   | `upload_raw_json` + `insert_ohlcv_batch` (pseudo) | < 30s |
| 4 | `collect_news`             | interval 15 min     | News RSS               | parse feedparser                      | `insert_news_batch`        | < 60s                        |
| 5 | `enrich_news_nlp`          | interval 20 min     | —                      | `extract_keywords`, sentiment lexicon | `update_news_nlp`          | < 120s pour 100 articles     |
| 6 | `collect_fear_greed`       | interval 60 min     | Alternative.me         | F&G → pseudo-OHLCV                    | `insert_ohlcv_batch`       | < 10s                        |
| 7 | `compute_indicators`       | interval 5 min      | — (lit DB)             | RSI, Bollinger, trend                 | `insert_indicators_batch`  | < 180s                       |
| 8 | `export_datasets`          | cron 03:00 UTC      | — (lit DB)             | Parquet serialisation                 | `upload_ohlcv_parquet`     | < 600s                       |
| 9 | `reconciliation`           | interval 60 min     | Binance (backfill)     | `detect_gaps` (SQL side)              | `insert_ohlcv_batch`       | < 300s                       |
|10 | `evaluate_signal_outcomes` | interval 60 min     | — (lit DB)             | `pct_change`, correctness             | `insert_signal_outcome`    | < 60s                        |

Health-check aiohttp exposé sur port 8080 (`src/etl/main.py:42-47, 170-175`) pour sondes Docker/LB.

Lifecycle : SIGINT/SIGTERM → `scheduler.shutdown(wait=False)` + `runner.cleanup()` (`main.py:180-192`).

## 7. Rapport d'exécution (simulation)

Rapport JSON structuré généré par `uv run python -m src.etl.main --once --report-json` (le flag `--once --report-json` est une extension à implémenter — actuellement le scheduler tourne en boucle infinie, cf risques).

Schema attendu :

```json
{
  "run_started_at": "2026-04-14T09:00:00Z",
  "run_finished_at": "2026-04-14T09:02:17Z",
  "duration_sec": "[À MESURER]",
  "jobs": [
    {
      "id": "collect_ohlcv_priority",
      "status": "success",
      "records_processed": "[À MESURER]",
      "records_valid": "[À MESURER]",
      "records_inserted": "[À MESURER]",
      "retry_count": "[À MESURER]",
      "errors": []
    }
  ]
}
```

Les logs textuels actuels émettent déjà ces valeurs :
- `"OHLCV batch insert: %d/%d rows inserted"` (`timescaledb.py:65`)
- `"job_collect_ohlcv_priority complete: %d fetched, %d valid, %d inserted"` (`jobs.py:55-60`)
- `"Deduplicated OHLCV: removed %d duplicates from %d records"` (`cleaner.py:28`)
- `"Detected %d gaps (%d missing candles) in %s/%s"` (`cleaner.py:121-127`)

Un collecteur de métriques structurées (Prometheus) peut agréger ces lignes — cf [[CryptoBot/avril/rncp/livrables/L2-infrastructure/etl-data-quality]] section 6.

## 8. Limites et évolutions

Décisions d'architecture explicites (`docs/00-overview.md` + [[../../architecture/_canonical]]) :

- **Pas de Kafka** ni autre message broker — APScheduler + SQL UPSERT en V1. Scale vertical uniquement. Limite : un crash du worker ETL = perte des fetches en vol (pas de reprise transactionnelle cross-source).
- **Pas de CDC** (Debezium/Kafka Connect) — pas de propagation streaming vers downstream ; les consommateurs lisent TimescaleDB directement.
- **Pas de trade execution** — strictement informationnel (signaux uniquement).
- **ESMA/SEC absents du MVP** — backlog Phase 2, cf [[../../specs/data-sources-roadmap]].
- **PhoenixNews** mentionné dans les specs non présent dans `_DEFAULT_SOURCES` (remplacé par cryptonews.com). Divergence à réconcilier.
- **Partitionnement horaire MinIO** (`s3://raw/{source}/{yyyy-mm-dd}/{hh}/`) promis dans la spec, mais l'implémentation actuelle est daily. OK pour MVP, à revoir pour haute-fréquence.
- **CCXT collector** est un fallback non utilisé en chemin nominal. Aucun switch automatique Binance → CCXT implémenté.
- **Rate-limit global non agrégé** — chaque collector gère son 429 localement. Pas de circuit-breaker global entre jobs (un burst de 429 Binance ne freine pas `collect_ohlcv_all`).

Évolutions Phase 2 planifiées (cf [[../../specs/PRD-phase2]], [[../../specs/data-sources-roadmap]]) :
- Flux ESMA régulation, SEC EDGAR
- Scraping social (Twitter/Reddit) via specs [[../../specs/architecture-scraping]]
- CDC TimescaleDB → streaming Kafka pour notifications temps réel
- MLflow-driven feature pipelines ([[../../architecture/c06-phase2-ml-pipeline]])

Liens connexes : [[../../architecture/ac01-etl-pipeline]], [[../../architecture/c02-etl-components]], [[../../architecture/er01-database-schema]], [[../../code/etl]], [[CryptoBot/avril/rncp/livrables/L2-infrastructure/etl-data-quality]].
