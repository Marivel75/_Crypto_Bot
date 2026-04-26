# Crypto Bot — API

API REST exposant les données collectées par le Crypto Bot : données OHLCV, market data CoinGecko et indicateurs techniques calculés à la volée.

## Lancement

```bash
# Depuis la racine du projet
uvicorn api.main:app --reload
```

L'API démarre sur `http://localhost:8000`.  
La documentation interactive (Swagger UI) est disponible sur `http://localhost:8000/docs`.

---

## Endpoints

### `GET /health`

Vérifie l'état de l'API et de la connexion à la base de données.

```bash
curl http://localhost:8000/health
```

```json
{
  "status": "ok",
  "db": "connected",
  "timestamp": "2026-04-25T10:36:42.376533"
}
```

---

### `GET /ohlcv`

Retourne les données OHLCV stockées en base, avec filtres optionnels.

| Paramètre    | Type     | Défaut | Description                          |
|-------------|----------|--------|--------------------------------------|
| `symbol`    | string   | —      | Paire de trading (ex: `BTC/USDT`)    |
| `timeframe` | string   | —      | Timeframe (ex: `1h`, `4h`, `1d`)     |
| `exchange`  | string   | —      | Exchange (ex: `binance`, `kraken`)   |
| `start_date`| datetime | —      | Date de début (ISO 8601)             |
| `end_date`  | datetime | —      | Date de fin (ISO 8601)               |
| `limit`     | int      | 100    | Nombre de résultats (max 1000)       |

```bash
curl "http://localhost:8000/ohlcv?symbol=BTC/USDT&timeframe=1d&limit=10"
```

---

### `GET /ohlcv/symbols`

Liste tous les symboles disponibles en base, avec le nombre de bougies et la date de la dernière.

| Paramètre  | Type   | Défaut | Description                        |
|-----------|--------|--------|------------------------------------|
| `exchange` | string | —      | Filtrer par exchange               |

```bash
curl "http://localhost:8000/ohlcv/symbols"
```

```json
[
  {
    "symbol": "BTC/USDT",
    "exchange": "binance",
    "timeframe": "1d",
    "count": 300,
    "latest_timestamp": "2026-04-06T00:00:00"
  }
]
```

---

### `GET /ohlcv/latest`

Retourne les dernières bougies disponibles pour un ou tous les symboles.

| Paramètre   | Type   | Défaut | Description                        |
|------------|--------|--------|------------------------------------|
| `symbol`   | string | —      | Paire de trading                   |
| `timeframe`| string | `1d`   | Timeframe                          |
| `exchange` | string | —      | Filtrer par exchange               |

```bash
curl "http://localhost:8000/ohlcv/latest?symbol=ETH/USDT&timeframe=4h"
```

---

### `GET /market/top`

Retourne le dernier snapshot des top N cryptos (source : CoinGecko).

| Paramètre  | Type   | Défaut | Description                          |
|-----------|--------|--------|--------------------------------------|
| `limit`   | int    | 20     | Nombre de cryptos (max 100)          |
| `currency` | string | `usd`  | Devise de référence (`usd`, `eur`…) |

```bash
curl "http://localhost:8000/market/top?limit=10"
```

```json
{
  "snapshot_time": "2026-04-06T15:22:51",
  "vs_currency": "usd",
  "cryptos": [
    {
      "rank": 1,
      "symbol": "BTC",
      "name": "Bitcoin",
      "price": 69648.0,
      "market_cap": 1395116276730.0,
      "volume_24h": 42275507980.0,
      "price_change_pct_24h": 4.03
    }
  ]
}
```

---

### `GET /market/global`

Retourne le dernier snapshot du marché global crypto : market cap total, volume, dominance BTC/ETH.

```bash
curl "http://localhost:8000/market/global"
```

```json
{
  "snapshot_time": "2026-04-06T15:22:51",
  "active_cryptocurrencies": 17123,
  "market_cap_usd": 2340000000000.0,
  "volume_usd": 98000000000.0,
  "market_cap_change_24h": 2.1,
  "dominance": [
    { "asset": "btc", "percentage": 54.2 },
    { "asset": "eth", "percentage": 12.1 }
  ]
}
```

---

### `GET /market/ticker`

Retourne les derniers snapshots ticker (prix temps réel mis en cache).

| Paramètre  | Type   | Défaut | Description               |
|-----------|--------|--------|---------------------------|
| `symbol`  | string | —      | Paire de trading          |
| `exchange` | string | —     | Filtrer par exchange      |
| `limit`   | int    | 50     | Nombre de résultats (max 200) |

```bash
curl "http://localhost:8000/market/ticker?symbol=BTC/USDT"
```

---

### `GET /signals`

Retourne les données OHLCV enrichies des indicateurs techniques calculés à la volée.

Indicateurs inclus : SMA 20/50, EMA 20, RSI 14, MACD (ligne / signal / histogramme), Bollinger Bands (upper / middle / lower).

| Paramètre   | Type   | Défaut | Description                        |
|------------|--------|--------|------------------------------------|
| `symbol`   | string | **obligatoire** | Paire de trading (ex: `BTC/USDT`) |
| `timeframe`| string | `1d`   | Timeframe                          |
| `exchange` | string | —      | Filtrer par exchange               |
| `limit`    | int    | 100    | Nombre de bougies retournées (min 10, max 500) |

```bash
curl "http://localhost:8000/signals?symbol=BTC/USDT&timeframe=1d&limit=30"
```

```json
[
  {
    "timestamp": "2026-04-06T00:00:00",
    "symbol": "BTC/USDT",
    "timeframe": "1d",
    "exchange": "binance",
    "open": 66980.21,
    "high": 67368.77,
    "low": 66265.94,
    "close": 66961.55,
    "volume": 7373.5,
    "sma_20": 67098.38,
    "sma_50": 68532.13,
    "ema_20": 67415.49,
    "rsi_14": 38.97,
    "macd_line": -352.14,
    "macd_signal": 25.34,
    "macd_histogram": -377.49,
    "bb_upper": 68656.34,
    "bb_middle": 67098.38,
    "bb_lower": 65540.41
  }
]
```

> **Note** : les 50 premières bougies récupérées servent de warm-up pour les indicateurs (fenêtre SMA 50) et ne sont pas retournées.

---

## Structure

```
api/
├── main.py              # App FastAPI, routers, CORS
├── dependencies.py      # Dépendance DB (session SQLAlchemy)
├── routers/
│   ├── health.py        # GET /health
│   ├── ohlcv.py         # GET /ohlcv, /ohlcv/symbols, /ohlcv/latest
│   ├── market.py        # GET /market/top, /market/global, /market/ticker
│   └── signals.py       # GET /signals
└── schemas/
    ├── ohlcv.py         # Pydantic : OHLCVResponse, SymbolInfo
    ├── market.py        # Pydantic : TopCrypto, GlobalMarket, Ticker
    └── signals.py       # Pydantic : SignalResponse
```

## Migration PostgreSQL

L'API est agnostique du moteur de base de données. Pour basculer de SQLite à PostgreSQL, il suffit de modifier `DATABASE_URL` dans `config/config.yaml` ou `.env` — aucun changement de code nécessaire.

```yaml
# config/config.yaml
database:
  url: "postgresql://user:password@localhost:5432/crypto_bot"
```
