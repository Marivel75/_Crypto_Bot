# ETL — Equipe Data Engineering

Voir `docs/01-data-engineering.md` pour le detail des taches et specifications.

## Structure attendue

```
src/etl/
├── __init__.py
├── main.py                 # Point d'entree du worker ETL (APScheduler)
├── collectors/
│   ├── binance.py          # Collecteur OHLCV Binance
│   ├── coingecko.py        # Collecteur CoinGecko
│   ├── news.py             # Scraping news (Decrypt, Cointelegraph)
│   └── fear_greed.py       # Fear & Greed Index
├── transformers/
│   ├── indicators.py       # Calcul des indicateurs techniques (RSI, BB, etc.)
│   └── cleaner.py          # Nettoyage, deduplication
├── loaders/
│   ├── timescaledb.py      # Insertion dans TimescaleDB
│   └── minio_loader.py     # Upload vers MinIO
├── migrations/             # Alembic migrations
│   └── ...
├── Dockerfile
└── requirements.txt
```
