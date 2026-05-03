# Crypto Bot

Plateforme de collecte, stockage et analyse de données crypto.  
Pipeline ETL multi-exchange → base de données → API REST → dashboard Streamlit + veille actualités + backtesting ML + suivi d'expériences MLflow.

## Démarrage rapide

```bash
pip install -r requirements.txt

make run        # Lance API (8000) + Streamlit (8501) en local
make docker     # Lance la stack complète via Docker (API + Front + MLflow)
make help       # Affiche toutes les commandes disponibles
```

## Commandes make

### Local (sans Docker)

```bash
make run        # Lance l'API FastAPI en arrière-plan + Streamlit au premier plan
make stop       # Arrête l'API FastAPI (Ctrl+C arrête Streamlit)
```

### Docker (stack complète)

```bash
make docker       # Build et démarre tous les services
make docker-stop  # Arrête tous les conteneurs
make docker-logs  # Affiche les logs en temps réel
```

| Service  | URL                          |
|----------|------------------------------|
| API REST | http://localhost:8000/docs   |
| Frontend | http://localhost:8501        |
| MLflow   | http://localhost:5001        |

### Données et tests

```bash
make news     # Collecte des news RSS (une passe)
make history  # Collecte l'historique OHLCV complet
make tests    # Lance tous les tests pytest
```

## Installation manuelle

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

Cinq pages : Dashboard (chandelier + indicateurs), Analytics (Fear & Greed, market cap, movers, corrélation), Signaux (tableau complet), Veille (news RSS + sentiment VADER + NLP), ML & Backtesting (walk-forward).

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
python scripts/fetch_history.py                                          # toutes paires/exchanges/timeframes
python scripts/fetch_history.py --exchange binance --timeframes 1d --limit 1000
python scripts/fetch_history.py --pairs BTC/USDT ETH/USDT --timeframes 1d 4h
```

### Actualités crypto (RSS — Decrypt, CoinTelegraph, CryptoNews)

```bash
python scripts/collect_news.py --once      # collecte unique
python scripts/collect_news.py             # boucle toutes les 60 min
python scripts/collect_news.py --interval 30
```

Chaque article est enrichi automatiquement par le pipeline NLP : sentiment VADER, mots-clés TF-IDF, entités (symboles crypto, exchanges), topics.

## NLP & Text Mining

Le module `src/ml/nlp/` enrichit chaque article collecté en trois dimensions :

| Analyse | Méthode | Exemple |
|---|---|---|
| Mots-clés | TF-IDF (unigrammes + bigrammes) | `["etf approved", "sec", "rally"]` |
| Entités | Regex + dictionnaire | `{"crypto_symbols": ["BTC","ETH"], "exchanges": ["binance"]}` |
| Topics | Classification par mots-clés | `["regulation", "adoption"]` |

Topics reconnus : `regulation`, `hack_security`, `adoption`, `defi`, `nft`, `macro`, `price_action`, `general`.

```bash
# Tester le pipeline NLP sans réseau
python scripts/test_nlp.py --offline

# Collecte live + enrichissement en base
python scripts/test_nlp.py

# Afficher les derniers articles enrichis
python scripts/test_nlp.py --db
```

→ Détails : [`src/ml/nlp/README.md`](src/ml/nlp/README.md)

## Backtesting ML

Disponible via l'API (`GET /ml/backtest`) et la page **ML & Backtesting** du frontend.  
Évalue les modèles (Random Forest, Régression Logistique, Dummy) sur des fenêtres walk-forward
avec purge et embargo. Métriques : Sharpe, win rate, PnL, drawdown max, profit factor, comparaison buy-and-hold.

**Prérequis** : lancer `fetch_history.py` au moins une fois pour disposer d'un historique suffisant.

## MLflow

Chaque backtest est tracé automatiquement dans MLflow : paramètres (symbole, modèle, fenêtres), métriques (Sharpe, win rate, PnL, drawdown), comparaison vs buy-and-hold.

```bash
# En local (MLflow doit tourner séparément)
mlflow ui --port 5001

# Via Docker (inclus dans make docker)
# → http://localhost:5001
```

Les expériences sont stockées dans `./data/mlflow/` (SQLite backend) — les données persistent entre les redémarrages.

## Tests

```bash
make tests                                   # tous les tests (pytest)

./scripts/run_tests.py --verbose             # avec sortie détaillée
./scripts/run_tests.py --verbose --coverage  # avec couverture

# Par groupe
./scripts/run_tests.py --type api
./scripts/run_tests.py --type etl
./scripts/run_tests.py --type ml
./scripts/run_tests.py --type frontend
./scripts/run_tests.py --type news
```

→ Détails : [`tests/README.md`](tests/README.md)

## Structure du projet

```
├── api/              # Backend FastAPI (OHLCV, market, signals, news, ml)
├── frontend/         # Dashboard Streamlit (5 pages, composants Plotly)
├── mlflow/           # Dockerfile MLflow (backend SQLite)
├── src/
│   ├── collectors/   # Collecteurs OHLCV, ticker, news RSS, Fear & Greed
│   ├── etl/          # Pipeline Extract → Transform → Load
│   ├── models/       # Modèles SQLAlchemy
│   ├── analytics/    # Indicateurs techniques (SMA, EMA, RSI, MACD, BB)
│   ├── ml/
│   │   ├── backtesting/          # Walk-forward backtester (Sharpe, drawdown, buy-and-hold)
│   │   ├── feature_engineering/  # FeatureBuilder, DatasetBuilder
│   │   ├── models/               # BaselineModel (Random Forest, LogReg, Dummy), ModelEvaluator
│   │   ├── nlp/                  # Text mining : TF-IDF, entités, topics
│   │   └── mlflow_utils.py       # Helpers MLflow (log_experiment, log_backtest_metrics)
│   └── quality/      # Validation des données
├── config/           # Configuration (settings.py, config.yaml)
├── scripts/
│   ├── fetch_history.py   # Collecte historique OHLCV
│   ├── collect_news.py    # Collecte news RSS en boucle
│   ├── test_nlp.py        # Test du pipeline NLP
│   ├── run_tests.py       # Lancement des tests par groupe
│   └── ...
├── tests/            # Suite de tests (413 tests)
├── Makefile          # Commandes make (run, docker, news, history, tests…)
├── docker-compose.yml
├── main.py           # Point d'entrée collecte OHLCV incrémentale
└── requirements.txt
```

## Stack technique

| Couche | Technologie |
|---|---|
| Collecte | ccxt, CoinGecko API, feedparser |
| Sentiment | vaderSentiment (news), Fear & Greed Index (alternative.me) |
| NLP / Text Mining | scikit-learn TF-IDF, regex, classification par mots-clés |
| Stockage | SQLAlchemy, SQLite (dev) / PostgreSQL (prod) |
| API | FastAPI, uvicorn |
| Frontend | Streamlit, Plotly |
| ML | scikit-learn, pandas |
| Backtesting | Walk-forward maison (purge + embargo, Sharpe, drawdown) |
| Suivi ML | MLflow (SQLite backend, artifacts locaux) |
| Indicateurs | pandas-ta-classic |
| Infra | Docker, Docker Compose |
| Tests | pytest, httpx |
