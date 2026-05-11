---
type: livrable-rncp
bloc: 2
source: rncp-agent-L2-ETL-Report
tags: [cryptobot, rncp, bloc2, etl, quality]
created: 2026-04-14
---

# Bloc 2 — Qualité des données ETL

Contrôles qualité appliqués au pipeline CryptoBot : quelles dimensions DAMA, quels seuils, quels mécanismes techniques, quels tests. Complément du rapport d'exécution [[CryptoBot/avril/rncp/livrables/L2-infrastructure/etl-execution-report]].

## 1. Indicateurs de qualité (DAMA)

Les 6 dimensions DAMA DMBOK appliquées au pipeline :

| Dimension      | Définition projet                                                        | Seuil cible MVP                     | Mesuré par                                                    |
|----------------|--------------------------------------------------------------------------|-------------------------------------|---------------------------------------------------------------|
| Completeness   | Aucun gap non comblé sur `PRIORITY_SYMBOLS` sur fenêtre 24h               | `≥ 99.5%` candles présentes         | `job_reconciliation` + `detect_gaps` SQL (`jobs.py:265-301`)  |
| Uniqueness     | Aucun doublon (symbol, timeframe, timestamp) en base                      | 100% (garanti par PK)               | PK composite TimescaleDB + `deduplicate_ohlcv`                |
| Timeliness     | Latence collecte → disponibilité API                                      | P95 `< 90s` pour OHLCV 1min         | Logs `duration` par run + Prometheus (`[À INSTRUMENTER]`)     |
| Validity       | Invariants OHLCV respectés (high ≥ low, volume ≥ 0)                       | `100%` records insérés valides      | `validate_ohlcv_relationships` (`cleaner.py:32-57`)            |
| Accuracy       | Écart cross-source Binance vs CoinGecko sur symboles priority             | Écart `< 0.5%` en valeur absolue    | `[À IMPLÉMENTER]` — job réconciliation cross-source Phase 2   |
| Consistency    | Cohérence OHLCV ↔ indicateurs (pas d'indicateur orphelin)                 | Foreign consistency = 100%          | UPSERT `(symbol, timeframe, timestamp)` partagée              |

Priorité MVP : Completeness, Uniqueness, Validity (bloquants). Timeliness et Accuracy suivent en Phase 2.

## 2. Dédoublonnage

Deux niveaux complémentaires.

### 2.1 In-memory avant insertion

`deduplicate_ohlcv(records)` dans `src/etl/transformers/cleaner.py:13-29` :

```python
def deduplicate_ohlcv(records: list[OHLCVRecord]) -> list[OHLCVRecord]:
    seen: set[tuple[str, str, str]] = set()
    unique: list[OHLCVRecord] = []
    for record in records:
        key = (record.symbol, record.timeframe, str(record.timestamp))
        if key not in seen:
            seen.add(key)
            unique.append(record)
    ...
```

Stratégie `first-seen wins`. Le compteur `removed = len(records) - len(unique)` est loggé au niveau INFO pour monitoring.

### 2.2 Garantie DB

Chaque hypertable a sa contrainte d'unicité, déclenchant un UPSERT côté SQL :

| Table           | Contrainte                          | Action sur conflit           |
|-----------------|-------------------------------------|------------------------------|
| `crypto_prices` | PK `(symbol, timeframe, timestamp)` | `DO NOTHING` (idempotent)    |
| `indicators`    | PK `(symbol, timeframe, timestamp)` | `DO UPDATE` (recalcul autorisé) |
| `news`          | UNIQUE `url`                        | `DO NOTHING`                 |

Référence : `src/etl/loaders/timescaledb.py:47-55` (crypto_prices) et `timescaledb.py:95-115` (indicators).

Cette double barrière permet de relancer un job sans risque de duplication, et de ré-exécuter les migrations ou backfills à volonté.

## 3. Validation Pydantic v2

Tous les records traversent Pydantic avant tout stockage. Modèles dans `src/shared/models/crypto.py` — outline [[../../architecture/cl01-pydantic-models]].

### 3.1 OHLCVRecord

Champs typés obligatoires :
- `symbol: str`
- `timeframe: str`
- `timestamp: datetime` (tz-aware UTC)
- `price_open/high/low/close: Decimal` — Decimal pour préserver la précision
- `volume_24h: Decimal`
- `market_cap: Decimal | None`
- `source: str`

Validation métier (post-Pydantic, car invariants inter-champs) dans `validate_ohlcv_relationships` (`cleaner.py:32-57`) — 6 règles déjà listées en [[CryptoBot/avril/rncp/livrables/L2-infrastructure/etl-execution-report#4-procédure-de-traitement]].

### 3.2 NewsArticle

Mandatory : `title: str`, `url: str (unique)`. Optionnels : `content`, `published_at`, `sentiment_score`, `keywords: list[str]`, `reliability_score`. Entrées RSS sans title ou link sont rejetées silencieusement (`news.py:151-153`).

### 3.3 IndicatorRecord

PK partagée avec OHLCV. Champs optionnels `rsi, bollinger_upper/middle/lower, price_vs_bollinger, harmonic_pattern, trend_slope, trend_type, metadata (jsonb)`. Les nulls sont acceptés — un record peut ne contenir que RSI sans Bollinger si l'historique est insuffisant pour BB(20).

## 4. Détection de gaps

Deux implémentations, une in-memory et une SQL.

### 4.1 In-memory (post-collecte)

`detect_gaps(records, expected_interval)` (`cleaner.py:95-128`). Parcourt la série triée, détecte toute paire `(t_i, t_{i+1})` où `actual_diff / expected_interval > 1`. Tolérance implicite : aucune — un écart strict de `> expected_interval` suffit.

### 4.2 SQL (reconciliation)

`detect_gaps(symbol, timeframe, interval_seconds, since)` côté TimescaleDB dans `src/etl/loaders/timescaledb.py`. Appelée par `job_reconciliation` toutes les heures pour chaque priority symbol sur la fenêtre `[-24h; now]` en timeframe 1h (`jobs.py:273-275`).

### 4.3 Tolérances par timeframe

`_TIMEFRAME_INTERVALS` (`cleaner.py:131-141`) — intervalle strict attendu :

| Timeframe | expected_interval | Tolérance cible projet             |
|-----------|-------------------|------------------------------------|
| 1m        | 60s               | 70s (10s grace)                    |
| 5m        | 300s              | 360s (60s grace)                   |
| 1h        | 3600s             | 3900s (1h + 5min grace)            |
| 4h        | 14400s            | 14700s (4h + 5min grace)           |
| 1D        | 86400s            | 87000s                             |

Note : les tolérances affichées sont le contrat cible issu de la spec RNCP. Le code actuel utilise une comparaison stricte `expected_count > 1` — les grace windows ne sont pas implémentées. `[À IMPLÉMENTER]` avant audit : ajouter un paramètre `tolerance_seconds` à `detect_gaps`.

### 4.4 Backfill automatique

Quand `detect_gaps` retourne des trous, `job_reconciliation` refait un `fetch_ohlcv(symbol, "1h", limit=100)` puis `insert_ohlcv_batch`. L'UPSERT ON CONFLICT garantit l'idempotence (`jobs.py:282-292`).

## 5. Réconciliation cross-source

Objectif : détecter les anomalies Binance (ex. spike isolé) en croisant avec CoinGecko sur les priority symbols.

État actuel : **non implémenté**. Seule la réconciliation temporelle intra-source (gap backfill) existe. La spec cible :

- Fréquence : horaire (partage avec `job_reconciliation`)
- Symboles : `PRIORITY_SYMBOLS` (13)
- Métrique : `abs(binance_close - coingecko_price) / binance_close`
- Seuil alerte : `> 0.5%` → log `ERROR` + émission métrique Prometheus `etl_reconciliation_divergence_total{symbol}`
- Action : aucune mutation auto — alerte pour inspection manuelle (un écart peut être légitime : liquidity différence, timing)

À ajouter dans `job_reconciliation` en Phase 2. Référence roadmap : [[../../specs/data-sources-roadmap]].

## 6. Métriques logguées et cible Prometheus

### 6.1 État actuel (logs texte)

Chaque étape critique émet une ligne INFO/WARNING structurée :

| Événement                 | Format log                                                         | Fichier:ligne            |
|---------------------------|--------------------------------------------------------------------|--------------------------|
| OHLCV fetch success       | `Binance OHLCV collected: symbol=%s timeframe=%s records=%d`       | `binance.py:115-120`     |
| OHLCV batch insert        | `OHLCV batch insert: %d/%d rows inserted`                          | `timescaledb.py:65`      |
| Dedup compte              | `Deduplicated OHLCV: removed %d duplicates from %d records`        | `cleaner.py:28`          |
| Invalid records           | `Invalid OHLCV record %s/%s at %s: %s`                             | `cleaner.py:74-80`       |
| Gaps détectés             | `Detected %d gaps (%d missing candles) in %s/%s`                   | `cleaner.py:121-127`     |
| Rate limit hit            | `Binance rate limit exceeded (Retry-After: %s)`                    | `binance.py:144`         |
| Job complete              | `job_collect_ohlcv_priority complete: %d fetched, %d valid, %d inserted` | `jobs.py:55-60`    |
| RSS feed parse            | `News feed collected: url=%s articles=%d`                          | `news.py:77-80`          |

### 6.2 Cible Prometheus

Métriques à exposer via un middleware asyncio + endpoint `/metrics` (actuellement `/health` seul, `main.py:170-175`) :

| Metric                                | Type      | Labels                        | Source logique                          |
|---------------------------------------|-----------|-------------------------------|-----------------------------------------|
| `etl_records_total`                   | Counter   | `source, status (valid/invalid/deduped)` | Compteurs déjà dans `cleaner.py` |
| `etl_duration_seconds`                | Histogram | `job_id`                      | `time.perf_counter()` autour de chaque job |
| `etl_retry_total`                     | Counter   | `collector, exception_type`   | Hook dans `with_retry` (`utils.py`)     |
| `etl_rate_limit_total`                | Counter   | `collector`                   | Bloc 429 de chaque collector            |
| `etl_gap_count`                       | Gauge     | `symbol, timeframe`           | Output `detect_gaps`                    |
| `etl_reconciliation_divergence_total` | Counter   | `symbol`                      | `[À IMPLÉMENTER]` en Phase 2            |

Référence outil : cf [[../../audit/technique/rate-limiting]] pour l'approche instrumentation retry.

## 7. Plan de test qualité

Tests unitaires colocalisés dans `tests/unit/etl/` (cf convention projet dans `CLAUDE.md`). Preuve de verdissement : [[../../audit/remediation/phase3]] — **1200 tests verts, couverture ≥ 80%** (quality gate `pytest --cov-fail-under=80`).

### 7.1 Couverture cible par module

| Module                                    | Tests nécessaires                                                                     |
|-------------------------------------------|---------------------------------------------------------------------------------------|
| `collectors/binance.py`                   | parse kline valide, 429 → `RateLimitError`, non-2xx → `ExternalAPIError`, parse malformé skippé |
| `collectors/coingecko.py`                 | résolution symbol→coin_id, symbole inconnu skippé avec warning                        |
| `collectors/fear_greed.py`                | parse payload nominal, payload sans `data` → `ValueError`, conversion pseudo-OHLCV    |
| `collectors/news.py`                      | feed valide, feed sans title/link skippé, feed.bozo loggé, date RFC2822 parsée        |
| `transformers/cleaner.py`                 | dedup first-seen, invariants OHLCV (5 cases négatifs), `detect_gaps` sur série trouée |
| `transformers/indicators.py`              | RSI(14), BB(20,2), skip si < 20 rows                                                   |
| `loaders/timescaledb.py`                  | insert idempotent (doublon ignoré), upsert indicators (DO UPDATE), batch vide → 0     |
| `loaders/minio_loader.py`                 | buckets créés idempotemment, parquet round-trip                                        |
| `jobs.py`                                 | `asyncio.gather` isole erreur per-symbole, `_compute_lexicon_sentiment` bornes [-1,1] |

### 7.2 Mocking

- HTTP externe : `respx` ou `httpx.MockTransport` pour stubs Binance/CoinGecko/Alt.me
- RSS : fixtures XML statiques + `feedparser.parse(...)` sur bytes in-memory
- MinIO : `minio.Minio` patché via `unittest.mock`
- TimescaleDB : session SQLAlchemy in-memory (SQLite) pour tests unitaires, conteneur TimescaleDB réel en integration

### 7.3 Intégration

Tests `tests/integration/etl/` nécessitent `docker-compose up timescaledb minio` — flow complet collect → validate → insert → retrieve.

### 7.4 Tests de non-régression qualité

Cas à garantir avant chaque merge :
1. Insertion de 1000 records dont 50 doublons → 950 rows en base, compteur dédup = 50
2. Kline Binance avec `high < low` (fuzz) → record en `invalid`, pas d'insertion
3. Gap simulé `[09:00, 09:03]` sur TF 1m → `detect_gaps` renvoie `(record09:00, record09:03, missing=2)`
4. Burst 429 → `with_retry` backoff 1s,2s,4s,8s puis raise → job_log `exception`, batch suivant OK

Liens : [[CryptoBot/avril/rncp/livrables/L2-infrastructure/etl-execution-report]], [[../../audit/remediation/phase3]], [[../../architecture/cl01-pydantic-models]], [[../../architecture/er01-database-schema]], [[../../code/etl]].
