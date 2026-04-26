# Crypto Bot

Plateforme de collecte, stockage et analyse de données crypto.  
Pipeline ETL multi-exchange → base de données → API REST → dashboard Streamlit + veille actualités + backtesting ML.

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

Cinq pages : Dashboard (chandelier + indicateurs), Analytics (Fear & Greed, market cap, movers, corrélation), Signaux (tableau complet), Veille (news RSS + sentiment VADER), ML & Backtesting (walk-forward).

## Collecter des données

### OHLCV + Market Data (exchanges & CoinGecko)

```bash
python main.py                                             # collecte incrémentale (100 bougies)
python main.py --schedule                                  # planifiée quotidiennement à 09:00
python main.py --ticker --exchanges binance --runtime 120  # ticker temps réel
```

### Historique complet (requis pour le backtesting ML)

Le backtesting nécessite au minimum ~200 jours de données journalières.  
Binance permet jusqu'à 1000 bougies par requête (~2.7 ans sur 1d).

```bash
# Collecte complète toutes paires/exchanges/timeframes du config
python scripts/fetch_history.py

# Options ciblées
python scripts/fetch_history.py --exchange binance --timeframes 1d --limit 1000
python scripts/fetch_history.py --pairs BTC/USDT ETH/USDT --timeframes 1d 4h
```

### Actualités crypto (RSS — Decrypt, CoinTelegraph, CryptoNews)

```bash
python scripts/collect_news.py --once      # collecte unique
python scripts/collect_news.py             # boucle toutes les 60 min
python scripts/collect_news.py --interval 30
```

## Backtesting ML

Disponible via l'API (`GET /ml/backtest`) et la page **ML & Backtesting** du frontend.  
Évalue les modèles (Random Forest, Régression Logistique, Dummy) sur des fenêtres walk-forward
avec purge et embargo. Métriques : Sharpe, win rate, PnL, drawdown max, profit factor, comparaison buy-and-hold.

**Prérequis** : lancer `fetch_history.py` au moins une fois pour disposer d'un historique suffisant.

## Tests

```bash
./scripts/run_tests.py --verbose             # tous les tests
./scripts/run_tests.py --verbose --coverage  # avec couverture

# Par groupe
./scripts/run_tests.py --type api
./scripts/run_tests.py --type etl
./scripts/run_tests.py --type ml        # inclut le backtester
./scripts/run_tests.py --type frontend
./scripts/run_tests.py --type news
./scripts/run_tests.py --type fear
./scripts/run_tests.py --type unit
./scripts/run_tests.py --type validation
```

→ Détails : [`tests/README.md`](tests/README.md)

## Structure du projet

```
├── api/              # Backend FastAPI (OHLCV, market, signals, news, ml)
├── frontend/         # Dashboard Streamlit (5 pages, composants Plotly)
├── src/
│   ├── collectors/   # Collecteurs OHLCV, ticker, news RSS, Fear & Greed
│   ├── etl/          # Pipeline Extract → Transform → Load
│   ├── models/       # Modèles SQLAlchemy
│   ├── analytics/    # Indicateurs techniques (SMA, EMA, RSI, MACD, BB)
│   ├── ml/
│   │   ├── backtesting/   # Walk-forward backtester (Sharpe, drawdown, buy-and-hold)
│   │   ├── feature_engineering/  # FeatureBuilder, DatasetBuilder
│   │   └── models/        # BaselineModel (Random Forest, LogReg, Dummy), ModelEvaluator
│   └── quality/      # Validation des données
├── config/           # Configuration (settings.py, config.yaml)
├── scripts/
│   ├── fetch_history.py   # Collecte historique OHLCV (jusqu'à 1000 bougies)
│   ├── collect_news.py    # Collecte news RSS en boucle
│   ├── run_tests.py       # Lancement des tests par groupe
│   └── ...                # backup, reset_db, generate_config…
├── tests/            # Suite de tests (413 tests)
├── main.py           # Point d'entrée collecte OHLCV incrémentale
└── requirements.txt
```

## Stack technique

| Couche | Technologie |
|---|---|
| Collecte | ccxt, CoinGecko API, feedparser |
| Sentiment | vaderSentiment (news), Fear & Greed Index (alternative.me) |
| Stockage | SQLAlchemy, SQLite (dev) / PostgreSQL (prod) |
| API | FastAPI, uvicorn |
| Frontend | Streamlit, Plotly |
| ML | scikit-learn, pandas |
| Backtesting | Walk-forward maison (purge + embargo, Sharpe, drawdown) |
| Indicateurs | pandas-ta-classic |
| Tests | pytest, httpx |
