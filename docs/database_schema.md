# Schéma de la base de données — Crypto Bot

Le projet utilise un schéma unique pour les deux backends :

| Environnement | Backend | Activation |
|---|---|---|
| Développement local | SQLite (`data/processed/crypto_data.db`) | défaut (`make run`) |
| Production | PostgreSQL (Neon.tech ou local) | `make run DB=postgres` |

Les tables sont créées automatiquement au démarrage de l'API (`Base.metadata.create_all`).  
La migration SQLite → PostgreSQL est réalisée via `make db-migrate`.

---

## Vue d'ensemble des relations

```
┌─────────────────────────────────────────────────────────────────┐
│  OHLCV                      TICKER                              │
│  ──────                     ──────                              │
│  ohlcv                      ticker_snapshots                    │
│  (série temporelle          (snapshots périodiques              │
│   bougies multi-exchange)    prix/volume par exchange)          │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  MARKET DATA (CoinGecko)                                        │
│  ──────────────────────                                         │
│  global_market_snapshot  ──┬── global_market_cap               │
│                            ├── global_market_volume            │
│                            └── global_market_dominance         │
│                                                                 │
│  top_crypto_snapshot     ──── top_crypto                       │
│                                                                 │
│  crypto_detail_snapshot  ──── crypto_detail                    │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  NEWS & NLP                 ALERTING                            │
│  ──────────                 ─────────                           │
│  news_articles              alert_subscribers                   │
│  (RSS + enrichissement      (emails abonnés                     │
│   VADER / TF-IDF / NER)      aux alertes de collecte)          │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  PAPER TRADING                                                  │
│  ─────────────                                                  │
│  paper_portfolios  ──────── paper_trades                        │
│  (portefeuilles fictifs)    (ordres BUY/SELL simulés)           │
└─────────────────────────────────────────────────────────────────┘
```

---

## 1. OHLCV

### `ohlcv`

Table principale de la collecte. Une ligne = une bougie (Open/High/Low/Close/Volume) pour un symbole, un timeframe et un exchange donné.

| Colonne | Type | Contrainte | Description |
|---|---|---|---|
| `id` | VARCHAR(36) | PK | UUID v4 généré à la collecte |
| `timestamp` | DATETIME | NOT NULL | Ouverture de la bougie (UTC) |
| `symbol` | VARCHAR(20) | NOT NULL | Paire de trading (ex : `BTC/USDT`) |
| `timeframe` | VARCHAR(10) | NOT NULL | Granularité (`1h`, `4h`, `1d`) |
| `open` | FLOAT | NOT NULL | Prix d'ouverture |
| `high` | FLOAT | NOT NULL | Plus haut |
| `low` | FLOAT | NOT NULL | Plus bas |
| `close` | FLOAT | NOT NULL | Prix de clôture |
| `volume` | FLOAT | NOT NULL | Volume échangé |
| `price_range` | FLOAT | | `high - low` (calculé à l'ETL) |
| `price_change` | FLOAT | | `close - open` |
| `price_change_pct` | FLOAT | | Variation en % |
| `date` | VARCHAR(10) | | Date au format `YYYY-MM-DD` |
| `exchange` | VARCHAR(20) | NOT NULL | Source (`binance`, `kraken`, `coinbase`) |
| `created_at` | DATETIME | | Horodatage d'insertion |
| `updated_at` | DATETIME | | Horodatage de mise à jour |

**Index** : `(symbol, timeframe)`, `(timestamp)`, `(symbol, timestamp)`

**Volume actuel** : ~84 000 lignes — 3 symboles × 3 timeframes × plusieurs exchanges

---

## 2. Ticker

### `ticker_snapshots`

Snapshots périodiques du carnet d'ordres (prix, volume 24h, variation). Collectés en continu par le ticker collector, à intervalle configurable.

| Colonne | Type | Contrainte | Description |
|---|---|---|---|
| `id` | VARCHAR(36) | PK | UUID v4 |
| `snapshot_time` | DATETIME | NOT NULL | Heure du snapshot |
| `symbol` | VARCHAR(20) | NOT NULL | Paire (ex : `BTC/USDT`) |
| `exchange` | VARCHAR(20) | NOT NULL | Exchange source |
| `price` | FLOAT | | Prix actuel |
| `volume_24h` | FLOAT | | Volume sur 24h |
| `price_change_24h` | FLOAT | | Variation absolue 24h |
| `price_change_pct_24h` | FLOAT | | Variation en % sur 24h |
| `high_24h` | FLOAT | | Plus haut 24h |
| `low_24h` | FLOAT | | Plus bas 24h |
| `created_at` | DATETIME | | Horodatage d'insertion |

**Index** : `(snapshot_time)`, `(symbol, snapshot_time)`

> À distinguer du cache live WebSocket (`LivePriceCache`) qui est en mémoire uniquement et n'est pas persisté en base.

---

## 3. Market Data

Données globales du marché collectées via l'API CoinGecko. Organisées autour de **snapshots** : chaque collecte crée un snapshot parent, les données détaillées sont attachées à ce snapshot.

### 3a. Marché global

#### `global_market_snapshot`

Un snapshot = une collecte de l'état global du marché crypto.

| Colonne | Type | Description |
|---|---|---|
| `id` | INTEGER PK | Auto-increment |
| `timestamp` | DATETIME | Horodatage de la collecte (unique) |
| `active_cryptocurrencies` | INTEGER | Nombre de cryptos actives |
| `upcoming_icos` | INTEGER | ICOs à venir |
| `ongoing_icos` | INTEGER | ICOs en cours |
| `ended_icos` | INTEGER | ICOs terminées |
| `markets` | INTEGER | Nombre de marchés actifs |
| `market_cap_change_24h` | FLOAT | Variation de la capitalisation 24h (%) |
| `volume_change_24h` | FLOAT | Variation du volume 24h (%) |
| `created_at` | DATETIME | Horodatage d'insertion |

#### `global_market_cap`

Capitalisation totale par devise pour chaque snapshot.

| Colonne | Type | Description |
|---|---|---|
| `id` | INTEGER PK | |
| `snapshot_id` | INTEGER FK→`global_market_snapshot.id` | |
| `currency` | VARCHAR(10) | Devise (`usd`, `eur`, `btc`…) |
| `value` | FLOAT | Capitalisation dans cette devise |

#### `global_market_volume`

Volume total par devise — même structure que `global_market_cap`.

#### `global_market_dominance`

Dominance de chaque crypto majeure (% de la capitalisation totale).

| Colonne | Type | Description |
|---|---|---|
| `id` | INTEGER PK | |
| `snapshot_id` | INTEGER FK→`global_market_snapshot.id` | |
| `asset` | VARCHAR(10) | Symbole (`btc`, `eth`…) |
| `percentage` | FLOAT | Part de marché en % |

---

### 3b. Top cryptos

#### `top_crypto_snapshot`

Un snapshot = une collecte du classement Top N.

| Colonne | Type | Description |
|---|---|---|
| `id` | INTEGER PK | Auto-increment |
| `snapshot_time` | DATETIME | Horodatage |
| `vs_currency` | VARCHAR(10) | Devise de référence (ex : `usd`) |

#### `top_crypto`

Chaque crypto du classement pour un snapshot donné.

| Colonne | Type | Description |
|---|---|---|
| `id` | INTEGER PK | |
| `snapshot_id` | INTEGER FK→`top_crypto_snapshot.id` | |
| `rank` | INTEGER | Position dans le classement |
| `crypto_id` | VARCHAR(50) | ID CoinGecko (ex : `bitcoin`) |
| `symbol` | VARCHAR(20) | Symbole (ex : `BTC`) |
| `name` | VARCHAR(50) | Nom complet |
| `market_cap` | FLOAT | Capitalisation boursière (USD) |
| `price` | FLOAT | Prix actuel |
| `volume_24h` | FLOAT | Volume 24h |
| `price_change_pct_24h` | FLOAT | Variation 24h (%) |

---

### 3c. Détails crypto

#### `crypto_detail_snapshot`

Snapshot des collectes détaillées (métadonnées, liens, community data).

| Colonne | Type | Description |
|---|---|---|
| `id` | INTEGER PK | |
| `snapshot_time` | DATETIME | Horodatage |
| `cryptos_count` | INTEGER | Nombre de cryptos collectées |

#### `crypto_detail`

Métadonnées complètes d'une crypto pour un snapshot.

| Colonne | Type | Description |
|---|---|---|
| `id` | INTEGER PK | |
| `snapshot_id` | INTEGER FK→`crypto_detail_snapshot.id` | |
| `crypto_id` | VARCHAR(50) | ID CoinGecko |
| `symbol` | VARCHAR(20) | Symbole |
| `name` | VARCHAR(100) | Nom complet |
| `rank` | INTEGER | Classement market cap |
| `categories` | VARCHAR(500) | Catégories (JSON sérialisé) |
| `genesis_date` | VARCHAR(30) | Date de création |
| `hashing_algorithm` | VARCHAR(100) | Algorithme de hash |
| `block_time_minutes` | INTEGER | Temps de bloc (min) |
| `image_large` / `image_small` | VARCHAR | URLs images |
| `links_homepage` / `links_blockchain_site` / … | VARCHAR | Liens (JSON sérialisé) |
| `community_twitter` / `community_reddit` / … | INTEGER | Métriques communauté |
| `developer_stars` / `developer_forks` / … | INTEGER | Métriques GitHub |
| `market_cap` / `total_volume` / `high_24h` / … | FLOAT | Données marché |
| `ath_price` | FLOAT | All-Time High |
| `ath_date` | VARCHAR(30) | Date ATH (ISO 8601, ex : `2021-11-10T14:24:11.849Z`) |
| `atl_price` | FLOAT | All-Time Low |
| `atl_date` | VARCHAR(30) | Date ATL |
| `circulating_supply` / `total_supply` / `max_supply` | FLOAT | Offre |
| `last_updated` | DATETIME | Dernière mise à jour CoinGecko |

---

## 4. News & NLP

### `news_articles`

Articles collectés via les flux RSS des principales sources crypto. Chaque article est enrichi automatiquement à la collecte.

| Colonne | Type | Description |
|---|---|---|
| `id` | VARCHAR(36) PK | UUID v4 |
| `title` | VARCHAR(500) | Titre de l'article |
| `url` | VARCHAR(1000) | URL canonique (unique) |
| `source` | VARCHAR(150) | Nom de la source RSS |
| `published_at` | DATETIME | Date de publication |
| `content` | TEXT | Contenu ou résumé |
| `sentiment_score` | FLOAT | Score VADER entre −1 (négatif) et +1 (positif) |
| `sentiment_label` | VARCHAR(20) | `positive` / `negative` / `neutral` |
| `keywords` | JSON | Liste de mots-clés TF-IDF (ex : `["etf approved", "sec"]`) |
| `entities` | JSON | Entités détectées (ex : `{"crypto_symbols": ["BTC"], "exchanges": ["binance"]}`) |
| `topics` | JSON | Topics classifiés (ex : `["regulation", "adoption"]`) |
| `collected_at` | DATETIME | Horodatage d'insertion |

**Topics reconnus** : `regulation`, `hack_security`, `adoption`, `defi`, `nft`, `macro`, `price_action`, `general`

> `keywords`, `entities` et `topics` sont stockés en JSON natif (PostgreSQL) ou TEXT sérialisé (SQLite). SQLAlchemy gère la transparence.

---

## 5. Alerting

### `alert_subscribers`

Liste des emails abonnés aux alertes automatiques envoyées lors des collectes (démarrage, erreur, succès).

| Colonne | Type | Description |
|---|---|---|
| `id` | INTEGER PK | Auto-increment |
| `email` | VARCHAR | Email unique, indexé |
| `active` | BOOLEAN | `true` = abonné actif |
| `created_at` | DATETIME | Date d'inscription |

---

## 6. Paper Trading

### `paper_portfolios`

Portefeuilles fictifs créés par l'utilisateur pour simuler des stratégies sans risque réel.

| Colonne | Type | Description |
|---|---|---|
| `id` | VARCHAR(36) PK | UUID v4 |
| `name` | VARCHAR(100) | Nom du portefeuille |
| `initial_capital` | FLOAT | Capital de départ (USDT) |
| `cash` | FLOAT | Cash disponible actuel (USDT) |
| `created_at` | DATETIME | Date de création |

### `paper_trades`

Ordres passés (BUY) et clôturés (SELL) dans un portefeuille fictif.

| Colonne | Type | Contrainte | Description |
|---|---|---|---|
| `id` | VARCHAR(36) | PK | UUID v4 |
| `portfolio_id` | VARCHAR(36) | FK→`paper_portfolios.id` | Portefeuille parent |
| `symbol` | VARCHAR(20) | NOT NULL | Paire tradée (ex : `BTC/USDT`) |
| `side` | VARCHAR(4) | NOT NULL | `BUY` (seule valeur à l'ouverture) |
| `quantity` | FLOAT | NOT NULL | Quantité d'actif achetée |
| `entry_price` | FLOAT | NOT NULL | Prix d'entrée (prix live ou close bougie) |
| `entry_time` | DATETIME | NOT NULL | Horodatage d'ouverture |
| `exit_price` | FLOAT | | Prix de clôture (NULL si position ouverte) |
| `exit_time` | DATETIME | | Horodatage de clôture |
| `status` | VARCHAR(6) | NOT NULL | `OPEN` ou `CLOSED` |
| `pnl` | FLOAT | | P&L réalisé en USDT (NULL si OPEN) |
| `pnl_pct` | FLOAT | | P&L en % (NULL si OPEN) |
| `signal_source` | VARCHAR(50) | NOT NULL | Origine du signal : `manual`, `technical`, `xgboost`, `random_forest`… |
| `signal_score` | FLOAT | | Score du signal déclencheur (0–1) |
| `created_at` | DATETIME | | Horodatage d'insertion |

**Index** : `(portfolio_id)`, `(status)`, `(symbol)`

---

## Bases SQLAlchemy

Le projet utilise **6 bases SQLAlchemy distinctes** pour découpler les domaines. Chaque base est créée indépendamment au démarrage de l'API.

| Base | Tables | Fichier |
|---|---|---|
| `OHLCVBase` | `ohlcv` | `src/models/ohlcv.py` |
| `TickerBase` | `ticker_snapshots` | `src/models/ticker.py` |
| `MarketDataBase` | `global_market_*`, `top_crypto*`, `crypto_detail*` | `src/models/market_data_base.py` |
| `NewsBase` | `news_articles` | `src/models/news.py` |
| `AlertBase` | `alert_subscribers` | `src/models/alert_subscriber.py` |
| `PaperTradeBase` | `paper_portfolios`, `paper_trades` | `src/models/paper_trade.py` |

---

## Notes de compatibilité SQLite / PostgreSQL

| Point | SQLite | PostgreSQL |
|---|---|---|
| Colonnes JSON | Stockées en TEXT, sérialisées par SQLAlchemy | Type JSON natif |
| Booléens | Stockés en INTEGER (0/1) | Type BOOLEAN natif |
| Clés primaires auto-increment | `INTEGER PRIMARY KEY` | `SERIAL` / `BIGSERIAL` |
| Contraintes FK | Non enforced par défaut | Enforced strictement |
| `check_same_thread` | Requis (`True` par défaut) | Non applicable |
| Migration de schéma | `ALTER TABLE ... ADD COLUMN` | Idem + support complet DDL |

> **Ordre de migration** : lors du `make db-migrate`, les tables sont insérées dans l'ordre topologique des foreign keys (`sorted_tables` de SQLAlchemy) pour respecter les contraintes PostgreSQL.
