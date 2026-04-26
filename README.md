# Crypto Bot

Plateforme de collecte, stockage et analyse de données crypto.  
Pipeline ETL multi-exchange → base de données → API REST → dashboard Streamlit + veille actualités.

## Installation

```bash
pip install -r requirements.txt
```

Base de données SQLite créée automatiquement au premier lancement.  
Pour PostgreSQL, définir `DATABASE_URL` dans `config/config.yaml`.

## Lancer l'API

```bash
uvicorn api.main:app --reload --port 8000
```

Accessible sur `http://localhost:8000` — documentation interactive : `http://localhost:8000/docs`

→ Détails des endpoints : [`api/README.md`](api/README.md)

## Lancer le frontend

```bash
streamlit run frontend/app.py
```

Accessible sur `http://localhost:8501`. **L'API doit être démarrée en parallèle.**

Quatre pages : Dashboard (chandelier + indicateurs), Analytics (market cap, movers, corrélation), Signaux (tableau complet), Veille (news RSS + sentiment).

## Collecter des données

**OHLCV + Market Data** (exchanges & CoinGecko) :

```bash
python main.py                                          # collecte unique
python main.py --schedule                               # planifiée (quotidienne 09:00)
python main.py --ticker --exchanges binance --runtime 120  # ticker temps réel
```

**Actualités crypto** (RSS — Decrypt, CoinTelegraph, CryptoNews) :

```bash
python scripts/collect_news.py --once      # collecte unique
python scripts/collect_news.py             # boucle toutes les 60 min
python scripts/collect_news.py --interval 30  # boucle toutes les 30 min
```

## Tests

```bash
./scripts/run_tests.py --verbose           # tous les tests
./scripts/run_tests.py --verbose --coverage  # avec couverture

# Par groupe
./scripts/run_tests.py --type api
./scripts/run_tests.py --type etl
./scripts/run_tests.py --type ml
./scripts/run_tests.py --type frontend
./scripts/run_tests.py --type news
./scripts/run_tests.py --type unit
./scripts/run_tests.py --type validation
```

→ Détails : [`tests/README.md`](tests/README.md)

## Structure du projet

```
├── api/              # Backend FastAPI (OHLCV, market, signals, news)
├── frontend/         # Dashboard Streamlit (4 pages, composants Plotly)
├── src/
│   ├── collectors/   # Collecteurs OHLCV, ticker, news RSS
│   ├── etl/          # Pipeline Extract → Transform → Load
│   ├── models/       # Modèles SQLAlchemy
│   ├── analytics/    # Indicateurs techniques (SMA, EMA, RSI, MACD, BB)
│   ├── ml/           # Machine Learning (feature engineering, modèles)
│   └── quality/      # Validation des données
├── config/           # Configuration (settings.py, config.yaml)
├── scripts/          # Utilitaires (collect_news, run_tests, backup…)
├── tests/            # Suite de tests (354 tests)
├── main.py           # Point d'entrée collecte OHLCV
└── requirements.txt
```

## Stack technique

| Couche | Technologie |
|---|---|
| Collecte | ccxt, CoinGecko API, feedparser |
| Sentiment | vaderSentiment |
| Stockage | SQLAlchemy, SQLite (dev) / PostgreSQL (prod) |
| API | FastAPI, uvicorn |
| Frontend | Streamlit, Plotly |
| ML | scikit-learn, pandas |
| Indicateurs | pandas-ta-classic |
| Tests | pytest, httpx |
