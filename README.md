# CryptoBot TA Indicators

Collecte et planifie des donnees crypto (OHLCV + ticker) sur plusieurs exchanges.

## Prerequis

- Python 3.12+
- `uv` (gestionnaire de dependances, utilise par le Makefile)
- `jq` (lecture de `data/scheduler_config.json` via `scheduler.sh`)

## Installation rapide

```bash
cp .env.example .env
make sync
```

## Configuration

Le fichier principal est `data/scheduler_config.json`.

Exemple de structure attendue:

```json
{
  "default_exchange": "binance",
  "schedule_time": "09:00",
  "pairs": ["BTC/USDT", "ETH/USDT"],
  "timeframes": ["1h", "4h"],
  "exchanges": [
    {
      "name": "binance",
      "pairs": ["BTC/USDT", "ETH/USDT"],
      "timeframes": ["1h", "4h"]
    }
  ]
}
```

Variables d'environnement utiles:

- `CONFIG` (chemin du JSON de config)
- `PAIRS`, `TIMEFRAMES`, `EXCHANGE`, `SCHEDULE_TIME` (override temporaire)
- `DATABASE_URL` ou variables PostgreSQL dans `.env`

Pour afficher ce qui est resolu par le script:

```bash
make show-config
```

## Usage

Valider la config:

```bash
make validate-config
```

Execution immediate (OHLCV):

```bash
make run
EXCHANGE=kraken PAIRS=BTC/USD TIMEFRAMES=1h make run
```

Planification quotidienne:

```bash
make schedule
EXCHANGE=coinbase SCHEDULE_TIME=09:00 make schedule
```

Raccourcis:

```bash
make run-binance
make run-kraken
make run-coinbase
make schedule-binance
make schedule-kraken
make schedule-coinbase
```

CLI directe (sans Makefile):

```bash
uv run python -m src.cli run --pair BTC/USDT --timeframe 1h --exchange binance
uv run python -m src.cli schedule --pair BTC/USDT --timeframe 1h --exchange binance --schedule-time 09:00
```

Si le package est installe:

```bash
crypto-bot run --pair BTC/USDT --timeframe 1h --exchange binance
```

## Tests

```bash
make test
```

## Fichiers utiles

- `scheduler.sh` : lit le JSON et construit les arguments de la CLI.
- `data/scheduler_config.json` : source de verite des paires/timeframes/exchanges.
- `data/processed/crypto_data.db` : base SQLite par defaut (si pas de `DATABASE_URL`).
