# Crypto Bot

Plateforme de collecte, stockage et analyse de données crypto.  
Pipeline ETL multi-exchange → base de données → API REST → dashboard Streamlit.

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

L'API est accessible sur `http://localhost:8000`.  
Documentation interactive : `http://localhost:8000/docs`

→ Détails des endpoints : [`api/README.md`](api/README.md)

## Lancer le frontend

```bash
streamlit run frontend/app.py
```

L'interface est accessible sur `http://localhost:8501`.  
**L'API doit être démarrée en parallèle.**

Trois pages : Dashboard (graphique chandelier + indicateurs), Analytics (market cap, movers, corrélation), Signaux (tableau complet).

## Collecter des données

Collecte OHLCV + Market Data depuis les exchanges et CoinGecko :

```bash
# Collecte unique
python main.py

# Collecte planifiée (quotidienne à 09:00)
python main.py --schedule

# Avec ticker temps réel
python main.py --ticker --exchanges binance kraken --runtime 120
```

## Tests

```bash
# Tous les tests (mode verbeux)
./scripts/run_tests.py --verbose

# Avec rapport de couverture
./scripts/run_tests.py --verbose --coverage

# Par groupe
./scripts/run_tests.py --type api       # Tests API FastAPI
./scripts/run_tests.py --type etl       # Tests pipeline ETL
./scripts/run_tests.py --type ml        # Tests Machine Learning
./scripts/run_tests.py --type unit      # Tests collecteurs
./scripts/run_tests.py --type validation
```

→ Détails : [`tests/README.md`](tests/README.md)

## Structure du projet

```
├── api/              # Backend FastAPI (endpoints OHLCV, market, signals)
├── frontend/         # Dashboard Streamlit (3 pages, composants Plotly)
├── src/
│   ├── collectors/   # Collecteurs OHLCV et ticker
│   ├── etl/          # Pipeline Extract → Transform → Load
│   ├── models/       # Modèles SQLAlchemy
│   ├── analytics/    # Indicateurs techniques (SMA, EMA, RSI, MACD, BB)
│   ├── ml/           # Machine Learning (feature engineering, modèles)
│   └── quality/      # Validation des données
├── config/           # Configuration (settings.py, config.yaml)
├── scripts/          # Utilitaires (run_tests.py, backup, reset_db…)
├── tests/            # Suite de tests (251 tests)
├── main.py           # Point d'entrée collecte de données
└── requirements.txt
```

## Stack technique

| Couche | Technologie |
|---|---|
| Collecte | ccxt, CoinGecko API |
| Stockage | SQLAlchemy, SQLite (dev) / PostgreSQL (prod) |
| API | FastAPI, uvicorn |
| Frontend | Streamlit, Plotly |
| ML | scikit-learn, pandas |
| Indicateurs | pandas-ta-classic |
| Tests | pytest, httpx |
