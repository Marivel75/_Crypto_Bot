---
type: rncp
bloc: 2
competence: C2.2.1
title: Normalisation 3NF et conception base de donnees
project: cryptobot
tags: [rncp38919, bloc2, database, 3nf, timescaledb, postgresql]
created: 2026-04-14
source_of_truth: src/shared/db_models.py
related: [[architecture/er01-database-schema]], [[architecture/cl02-orm-models]], [[equipes/05-devops-infra]]
---

# Normalisation 3NF — Base de donnees CryptoBot

## Contexte RNCP

Ce document couvre la competence **C2.2.1 (Concevoir et structurer une base de donnees)** du Bloc 2 du RNCP38919. Il decrit :

1. Le choix du SGBD et sa justification
2. L'analyse conceptuelle (MCD)
3. Le passage au modele logique (MLD)
4. La demonstration de conformite 3NF sur les 9 tables
5. Les denormalisations assumees et leur justification
6. La strategie d'indexation
7. La procedure d'evolution du schema

La verite du schema reside dans `src/shared/db_models.py` (SQLAlchemy 2.0 async) et est doublee par le diagramme PlantUML [[CryptoBot/avril/architecture/er01-database-schema]].

## 1. Choix du SGBD

### 1.1. Decision : TimescaleDB (PostgreSQL 16 + extension)

TimescaleDB est une extension native de PostgreSQL 16 qui ajoute la notion d'**hypertable** : une table logique partitionnee automatiquement en chunks physiques selon une colonne temporelle. Pour CryptoBot, le volume dominant est le flux OHLCV (Open-High-Low-Close-Volume) collecte en continu sur 30 symboles et 4 timeframes ; a 1 bougie / symbol / timeframe / minute, on tend vers ~170 000 inserts / jour, soit ~62 M lignes / an pour la seule table `crypto_prices`.

### 1.2. Justification first principles

| Exigence metier | Capacite TimescaleDB |
|-----------------|----------------------|
| Ingestion continue OHLCV | Hypertable, chunk_time_interval=1 jour, write path O(1) |
| Retention 90 jours | `add_retention_policy('crypto_prices', INTERVAL '90 days')` |
| Compression apres 7 jours | `add_compression_policy` + segmentby=symbol,timeframe, ratio 10-20x |
| Requetes analytiques | Continuous aggregates (phase 2) |
| Integrite transactionnelle | ACID complet (herite de PostgreSQL) |
| Integrite relationnelle | CHECK / FK / UNIQUE native |
| JSON semi-structure | JSONB indexable GIN |
| ORM async Python | SQLAlchemy 2.0 + asyncpg compatible |

### 1.3. Alternatives ecartees

- **PostgreSQL vanilla** : pas de partitionnement temporel automatique, compression absente, retention manuelle par cron. Plus de code applicatif, plus de bugs.
- **InfluxDB** : schema-less, pas de JOIN, ecosysteme de migration immature, pas de FK. Incompatible avec les 8 autres tables relationnelles.
- **ClickHouse** : excellent pour l'analytique mais faible pour les updates ponctuels (portfolio, watchlist) ; necessite un second SGBD pour l'OLTP.
- **MongoDB** : ecarte dans les ADR (cf `CLAUDE.md` : "No MongoDB, JSONB columns in PostgreSQL for unstructured data").

Le choix TimescaleDB unifie OLTP et time-series dans un seul moteur, ce qui reduit la surface operationnelle (un seul backup, une seule connexion, un seul SGBD a monitorer).

Reference ADR : [[CryptoBot/avril/history/decisions]] — decision "ADR-002 : TimescaleDB as unified store".

## 2. Modele Conceptuel de Donnees (MCD)

### 2.1. Entites principales

| Entite | Description | Volume estime 1 an |
|--------|-------------|--------------------|
| User | Compte utilisateur (trader / journaliste / investisseur) | ~1 000 |
| CryptoPrice | Bougie OHLCV par (symbol, timeframe, timestamp) | ~62 000 000 |
| Indicator | Indicateur technique calcule (RSI, BB, pattern, trend) | ~15 000 000 |
| TradingSignal | Signal informationnel (BUY/SELL/HOLD) emis par le moteur | ~100 000 |
| SignalOutcome | Evaluation post-mortem d'un signal (pnl, was_correct) | ~100 000 |
| Portfolio | Position virtuelle d'un utilisateur | ~10 000 |
| Watchlist | Symbole suivi par un utilisateur | ~20 000 |
| NewsArticle | Article de presse crypto (RSS / scraping) | ~500 000 |
| TextMiningResult | Resultat NLP d'un article (resume, entites, topics) | ~500 000 |

### 2.2. Cardinalites

| Relation | Cardinalite | Semantique |
|----------|-------------|------------|
| User -> Portfolio | 1 -- 0..N | Un utilisateur possede N entrees de portefeuille |
| User -> Watchlist | 1 -- 0..N | Un utilisateur suit N symboles |
| TradingSignal -> SignalOutcome | 1 -- 0..1 | Un signal est evalue au plus une fois |
| NewsArticle -> TextMiningResult | 1 -- 0..1 | Un article est analyse NLP au plus une fois |
| CryptoPrice -- Indicator | (symbol, timeframe, timestamp) logique | Pas de FK formelle (contrainte TimescaleDB, cf 4.2) |

### 2.3. Diagramme

Cf [[CryptoBot/avril/architecture/er01-database-schema]] (PlantUML rendu en `docs/diagrams/png/ER01-database-schema.png`).

## 3. Passage au Modele Logique de Donnees (MLD)

### 3.1. Cles primaires

| Table | Cle primaire | Type |
|-------|--------------|------|
| users | id | UUID v4 |
| crypto_prices | (symbol, timeframe, timestamp) | Composite -- requise par TimescaleDB hypertable |
| indicators | id | UUID v4 + UNIQUE (symbol, timeframe, timestamp) |
| trading_signals | id | UUID v4 |
| signal_outcomes | id | UUID v4 |
| portfolio | id | UUID v4 |
| watchlist | id | UUID v4 + UNIQUE (user_id, symbol) |
| news_articles | id | UUID v4 + UNIQUE (url) |
| text_mining_results | id | UUID v4 |

Choix UUID v4 : evite les conflits lors de fusions multi-source (Binance / CoinGecko / CCXT), permet la generation cote client ou cote ORM sans round-trip DB.

### 3.2. Cles etrangeres et cascades

Toutes les FK sont `ON DELETE CASCADE` car la semantique metier impose que la suppression d'un parent detruise ses enfants :

| Enfant | Parent | Justification cascade |
|--------|--------|-----------------------|
| portfolio.user_id | users.id | Suppression RGPD utilisateur -> suppression positions |
| watchlist.user_id | users.id | Suppression RGPD utilisateur -> suppression watchlist |
| signal_outcomes.signal_id | trading_signals.id | Un outcome orphelin est non interpretable |
| text_mining_results.article_id | news_articles.id | Le NLP n'a de sens qu'attache a l'article |

### 3.3. Contraintes CHECK (domaine)

Codees au niveau SQL pour defendre l'invariant cote DB, pas uniquement cote Pydantic :

| Table | Contrainte | Valeur |
|-------|-----------|--------|
| users | ck_users_persona_type | persona_type IN ('trader', 'journalist', 'investor') |
| trading_signals | ck_trading_signals_signal_type | signal_type IN ('BUY', 'SELL', 'HOLD') |
| trading_signals | ck_confidence_range | confidence_score BETWEEN 0 AND 1 |
| trading_signals | ck_leverage_range | leverage_suggested BETWEEN 1 AND 20 |
| indicators | ck_rsi_range | rsi BETWEEN 0 AND 100 |
| indicators | ck_bollinger_ratio | price_vs_bollinger BETWEEN -1 AND 1 |
| news_articles | ck_sentiment_range | sentiment_score BETWEEN -1 AND 1 |
| news_articles | ck_reliability_range | reliability_score BETWEEN 0 AND 1 |

Note : `db_models.py` implemente formellement `ck_users_persona_type` et `ck_trading_signals_signal_type`. Les plages numeriques (RSI, confidence, leverage) sont aujourd'hui defendues au niveau Pydantic et PlantUML ; l'ajout des CHECK SQL correspondants est **prevu dans la migration Alembic `add_domain_constraints`** (cf 6).

## 4. Normalisation

### 4.1. Demonstration par table

Pour chaque table on verifie :
- **1NF** : atomicite des colonnes, pas de groupes repetes
- **2NF** : 1NF + chaque attribut non-cle depend de la cle entiere (pas de dependance partielle sur cle composee)
- **3NF** : 2NF + aucun attribut non-cle ne depend transitivement d'un autre attribut non-cle

| Table | Dependances fonctionnelles | Forme atteinte | Remarque |
|-------|----------------------------|----------------|----------|
| users | id -> username, email, password_hash, persona_type, preferences, created_at | **3NF** | Atomiques, pas de groupe repete |
| crypto_prices | (symbol, timeframe, timestamp) -> open, high, low, close, volume, market_cap, source | **3NF** | Cle composite, toutes les colonnes dependent de la cle complete |
| indicators | id -> symbol, timeframe, timestamp, rsi, bollinger_*, price_vs_bollinger, harmonic_pattern, trend_slope, trend_type, metadata | **3NF** | UNIQUE (symbol, timeframe, timestamp) evite la duplication logique |
| trading_signals | id -> symbol, signal_type, confidence, timeframe_primary, timeframes_aligned, rules_triggered, leverage, margin_safety, fees, model_version, created_at | **3NF** | timeframes_aligned en JSONB = attribut atomique du point de vue relationnel |
| signal_outcomes | id -> signal_id, price_at_signal, price_after_1h, price_after_4h, price_after_1d, pnl_simulated, was_correct, evaluated_at | **3NF** | price_after_Nh = observations independantes, pas de dependance transitive |
| portfolio | id -> user_id, symbol, quantity, entry_price, current_price, notes, timestamps | **3NF** | current_price est une observation, pas une fonction d'autres colonnes |
| watchlist | id -> user_id, symbol, added_at | **3NF** | UNIQUE (user_id, symbol) garantit 1 symbole / utilisateur |
| news_articles | id -> title, content, source, url, published_at, sentiment_score, keywords, reliability_score, collected_at | **3NF** | url UNIQUE = cle candidate alternative |
| text_mining_results | id -> article_id, word_cloud, summary, entities, topics, processed_at | **3NF** | Chaque sortie NLP est un attribut propre |

### 4.2. Denormalisations assumees

Toutes les tables atteignent 3NF dans leur forme ORM. Cependant **deux denormalisations intentionnelles** sont documentees :

#### D1. Duplication (symbol, timeframe, timestamp) entre `crypto_prices` et `indicators`

**Probleme** : `indicators.(symbol, timeframe, timestamp)` reference logiquement `crypto_prices.(symbol, timeframe, timestamp)` -- une FK composite serait plus pure.

**Decision** : pas de FK. Justifications :
1. `crypto_prices` est une **hypertable TimescaleDB** : les FK pointant vers une hypertable ne sont pas supportees (limitation documentee par Timescale).
2. La FK bloquerait la **retention policy** : a J+91 les lignes de `crypto_prices` disparaissent ; les FK empecheraient la suppression ou casseraient `indicators` par cascade.
3. Le couplage est maintenu par le pipeline ETL (`src/etl/`) qui emet toujours prices -> indicators en sequence.

#### D2. `current_price` dans `portfolio`

**Probleme** : `current_price` peut etre recalcule a tout moment par une lecture de `crypto_prices`.

**Decision** : cache materialise a chaque tick de l'ETL. Justification : eviter un JOIN O(N) par rendu UI ; la coherence eventuelle est acceptable pour un affichage de portefeuille (delta < 1 min).

### 4.3. Tables JSONB : argumentation 1NF

Les colonnes JSONB suivantes pourraient theoriquement violer 1NF :

- `users.preferences`
- `indicators.metadata`
- `trading_signals.timeframes_aligned`, `rules_triggered`
- `news_articles.keywords`
- `text_mining_results.word_cloud`, `entities`, `topics`

**Defense 1NF** : dans PostgreSQL, JSONB est un **type scalaire natif**. Les valeurs sont atomiques du point de vue relationnel (on ne peut pas JOIN sur une cle interne JSONB sans fonction explicite). L'alternative serait une table `user_preferences (user_id, key, value)` -- 3NF mais qui multiplie les lignes et penalise les lectures de profil. L'ADR "JSONB over child tables for semi-structured metadata" justifie ce choix.

## 5. Index strategiques

### 5.1. Index existants (db_models.py)

| Table | Index | Colonne(s) | Usage |
|-------|-------|------------|-------|
| crypto_prices | idx_prices_symbol_tf | (symbol, timeframe, timestamp) | Requete OHLCV par couple |
| crypto_prices | (auto TimescaleDB) | timestamp DESC | Scans temporels par chunk |
| indicators | uq_indicators_symbol_tf_ts | (symbol, timeframe, timestamp) UNIQUE | Upsert + JOIN logique |
| trading_signals | idx_signals_symbol_created | (symbol, created_at) | Historique signaux par symbole |
| trading_signals | idx_signals_created | (created_at) | Dashboard "derniers signaux" |
| signal_outcomes | idx_outcomes_signal | (signal_id) | Rattachement outcome -> signal |
| signal_outcomes | idx_outcomes_correct | (was_correct) | KPI win-rate |
| portfolio | idx_portfolio_user | (user_id) | Lecture portfolio par utilisateur |
| news_articles | idx_news_published | (published_at) | Timeline news |
| news_articles | idx_news_source | (source) | Filtre par source |

### 5.2. Index additionnels proposes (roadmap)

| Table | Index | Colonne(s) | Usage |
|-------|-------|------------|-------|
| trading_signals | idx_signals_user_active | (user_id) WHERE archived=false | Index partiel -- dashboard user |
| trading_signals | idx_signals_symbol_tf_created | (symbol, timeframe_primary, created_at DESC) | Backtesting par (symbole, TF) |
| crypto_prices | idx_prices_symbol_desc | (symbol, timestamp DESC) | Dernier prix par symbole |
| news_articles | idx_news_sentiment | (sentiment_score) WHERE sentiment_score IS NOT NULL | Tri par sentiment |
| indicators | idx_indicators_rsi_extreme | (symbol, timestamp) WHERE rsi > 70 OR rsi < 30 | Alertes RSI extremes |

### 5.3. Principe directeur

**Index = contrat de lecture**. Ajouter un index uniquement si :
1. Une requete reelle le justifie (tracee par `pg_stat_statements`)
2. Le benefice SELECT > cout INSERT/UPDATE
3. L'index partiel `WHERE` est utilise quand une fraction de la table concentre 90% des lectures (ex : signaux actifs)

## 6. Evolution du schema -- Migrations Alembic

### 6.1. Chaine d'outils

```
src/shared/db_models.py (SSOT ORM)
        v alembic revision --autogenerate
alembic/versions/YYYY_MM_DD_slug.py
        v alembic upgrade head
PostgreSQL 16 + TimescaleDB
```

Note : au moment de la redaction, le dossier `alembic/` n'est pas encore initialise dans le repo (branche `roulio-dev`). La premiere migration sera :

```bash
uv run alembic init alembic
uv run alembic revision --autogenerate -m "initial_schema"
uv run alembic upgrade head
```

### 6.2. Promotion hypertable (hors Alembic)

Alembic ne supporte pas nativement `SELECT create_hypertable()`. Le protocole :

1. Migration Alembic cree `crypto_prices` en table classique
2. Migration SQL **post-Alembic** execute :
   ```sql
   SELECT create_hypertable('crypto_prices', 'timestamp', chunk_time_interval => INTERVAL '1 day', if_not_exists => TRUE);
   ALTER TABLE crypto_prices SET (timescaledb.compress, timescaledb.compress_segmentby = 'symbol,timeframe', timescaledb.compress_orderby = 'timestamp DESC');
   SELECT add_compression_policy('crypto_prices', INTERVAL '7 days');
   SELECT add_retention_policy('crypto_prices', INTERVAL '90 days', if_not_exists => TRUE);
   ```
3. Ce script est versionne dans `alembic/timescale/001_hypertable.sql` et execute par le hook `alembic upgrade head` via `op.execute(...)`.

### 6.3. Procedure zero-downtime (ADD NOT NULL)

Ajouter une colonne NOT NULL sans downtime :

```sql
-- Etape 1 : migration N, ajout en nullable avec default
ALTER TABLE trading_signals ADD COLUMN strategy_id UUID DEFAULT '00000000-0000-0000-0000-000000000000';

-- Etape 2 : backfill par batch (application ou job)
UPDATE trading_signals SET strategy_id = '...' WHERE strategy_id = '00000000-...' AND created_at > NOW() - INTERVAL '1 day';
-- repeter jusqu'a purge complete

-- Etape 3 : migration N+1, promotion NOT NULL + drop default
ALTER TABLE trading_signals ALTER COLUMN strategy_id SET NOT NULL;
ALTER TABLE trading_signals ALTER COLUMN strategy_id DROP DEFAULT;
ALTER TABLE trading_signals ADD CONSTRAINT fk_signals_strategy FOREIGN KEY (strategy_id) REFERENCES strategies(id);
```

### 6.4. Downgrade / rollback

Toute migration doit implementer `downgrade()`. Procedure de rollback :

```bash
uv run alembic downgrade -1   # revient d'une migration
uv run alembic history         # inspection
uv run alembic current         # version en base
```

**Regle** : jamais de downgrade destructif en production sans sauvegarde prealable (cf [[bloc2-infrastructure/db-backup-recovery]]).

## 7. Alias ORM

Pour coherence avec la couche service, `src/shared/models/orm.py` re-exporte les classes canoniques avec des alias :

| Alias | Canonique |
|-------|-----------|
| OHLCVOrm | CryptoPriceOrm |
| PortfolioEntryOrm | PortfolioOrm |
| WatchlistEntryOrm | WatchlistOrm |

Contradiction documentee dans `meta/contradictions.md` L23, a resoudre en phase 3 par un renommage global (Pydantic + ORM + doc).

## 8. References

- [[CryptoBot/avril/architecture/er01-database-schema]] -- diagramme ER PlantUML
- [[CryptoBot/avril/architecture/cl02-orm-models]] -- diagramme classes SQLAlchemy
- [[CryptoBot/avril/equipes/05-devops-infra]] -- exploitation TimescaleDB
- [[bloc2-infrastructure/db-ddl-init]] -- script DDL reconstruit
- [[bloc2-infrastructure/db-backup-recovery]] -- strategie de sauvegarde
- [[CryptoBot/avril/history/decisions]] -- ADR TimescaleDB / JSONB / No MongoDB
- `src/shared/db_models.py` -- source de verite ORM
- `docs/diagrams/ER01-database-schema.puml` -- diagramme source
