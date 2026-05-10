# Crypto Bot

Plateforme de collecte, stockage et analyse de données crypto.  
Pipeline ETL multi-exchange → base de données → API REST → dashboard Streamlit + veille actualités + backtesting ML + **paper trading temps réel** + suivi d'expériences MLflow.

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
make run        # Tue l'éventuel processus existant, démarre l'API puis Streamlit
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

### Données

```bash
make collect                               # Collecte OHLCV incrémentale (binance)
make collect EXCHANGES="binance kraken"    # Plusieurs exchanges
make collect-schedule                      # Collecte planifiée quotidienne (09:00)
make ticker                                # Ticker temps réel (binance, 120s)
make ticker EXCHANGES="binance coinbase" RUNTIME=300
make collect-live                          # OHLCV incrémental + ticker en parallèle
make news                                  # Collecte des news RSS (une passe)
make history                               # Collecte l'historique OHLCV complet
```

### Tests

```bash
make tests        # Tous les tests (verbose)
make test-api     # Tests des endpoints API uniquement
make test-paper   # Tests du module paper trading uniquement
make test-cov     # Tous les tests + rapport de couverture
```

## Lancer l'API

```bash
uvicorn api.main:app --reload --port 8000
```

Au démarrage, l'API :
- crée les tables SQLAlchemy si absentes (OHLCV, ticker, market data, paper trading)
- démarre le collecteur WebSocket Binance en thread daemon (prix live pour le paper trading)

Documentation interactive : `http://localhost:8000/docs`

## Lancer le frontend

```bash
streamlit run frontend/app.py
```

Accessible sur `http://localhost:8501`. **L'API doit être démarrée en parallèle.**

Six pages :

| Page | Contenu |
|------|---------|
| Dashboard | Graphique chandelier + indicateurs techniques |
| Analytics | Fear & Greed, market cap, top movers, matrice de corrélation |
| Signaux | Tableau complet RSI / MACD / BB / SMA avec score composite BUY/SELL/HOLD |
| Veille | News RSS + sentiment VADER + NLP (entités, topics) |
| ML & Backtesting | Walk-forward walk-forward (Sharpe, drawdown, comparaison buy-and-hold) |
| **Paper Trading** | Simulation de trades sur capital fictif avec prix temps réel Binance |

## Paper Trading

Simulation de stratégies d'investissement sur capital fictif, sans risque financier réel.

### Fonctionnement

1. **Créer un portefeuille** — nom + capital de départ en USDT
2. **Passer un ordre BUY** — par quantité ou montant USDT ; le récapitulatif temps réel affiche le coût exact avant confirmation
3. **Suivre les positions** — P&L latent mis à jour avec les prix live Binance (WS)
4. **Fermer une position** — SELL au prix live ; P&L réalisé crédité sur le cash
5. **Analyser la performance** — courbe capital réalisé + projection live, win rate, meilleur/pire trade

### Prix temps réel

Au démarrage de l'API, un thread daemon se connecte au flux WebSocket `miniTicker` de Binance pour tous les symboles configurés. Les prix sont stockés dans un cache mémoire thread-safe (`LivePriceCache`) et utilisés en priorité par le moteur de paper trading, avec fallback sur la dernière bougie OHLCV.

La page Paper Trading se rafraîchit automatiquement toutes les **5 secondes** via `streamlit-autorefresh`.

### API paper trading

| Méthode | Route | Description |
|---------|-------|-------------|
| `POST` | `/paper-trading/portfolios` | Créer un portefeuille |
| `GET` | `/paper-trading/portfolios` | Lister les portefeuilles |
| `GET` | `/paper-trading/portfolios/{id}` | Résumé complet (métriques + positions) |
| `POST` | `/paper-trading/orders` | Ouvrir une position BUY |
| `POST` | `/paper-trading/orders/{id}/close` | Fermer une position |
| `GET` | `/paper-trading/orders` | Historique des trades (filtrable) |
| `GET` | `/paper-trading/live-prices` | Prix live depuis le cache WS |
| `GET` | `/paper-trading/live-prices/status` | État de la connexion WS |

## Collecter des données

### OHLCV + Market Data (exchanges & CoinGecko)

```bash
python main.py                              # collecte incrémentale (100 bougies)
python main.py --schedule                   # planifiée quotidiennement à 09:00
python main.py --exchanges binance kraken   # plusieurs exchanges
```

### Ticker temps réel

```bash
python main.py --ticker --exchanges binance --runtime 120
```

### Historique complet (requis pour le backtesting ML)

Le backtesting nécessite au minimum ~200 jours de données journalières.

```bash
python scripts/fetch_history.py
python scripts/fetch_history.py --exchange binance --timeframes 1d --limit 1000
python scripts/fetch_history.py --pairs BTC/USDT ETH/USDT --timeframes 1d 4h
```

### Actualités crypto (RSS)

```bash
python scripts/collect_news.py --once      # collecte unique
python scripts/collect_news.py             # boucle toutes les 60 min
```

Chaque article est enrichi automatiquement : sentiment VADER, mots-clés TF-IDF, entités (symboles, exchanges), topics.

## NLP & Text Mining

Le module `src/ml/nlp/` enrichit chaque article collecté en trois dimensions :

| Analyse | Méthode | Exemple |
|---|---|---|
| Mots-clés | TF-IDF (unigrammes + bigrammes) | `["etf approved", "sec", "rally"]` |
| Entités | Regex + dictionnaire | `{"crypto_symbols": ["BTC","ETH"], "exchanges": ["binance"]}` |
| Topics | Classification par mots-clés | `["regulation", "adoption"]` |

Topics reconnus : `regulation`, `hack_security`, `adoption`, `defi`, `nft`, `macro`, `price_action`, `general`.

## Backtesting ML

Disponible via l'API (`GET /ml/backtest`) et la page **ML & Backtesting** du frontend.  
Évalue les modèles (Random Forest, Régression Logistique, Dummy) sur des fenêtres walk-forward avec purge et embargo.  
Métriques : Sharpe, win rate, PnL, drawdown max, profit factor, comparaison buy-and-hold.

**Prérequis** : lancer `fetch_history.py` au moins une fois.

## MLflow

Chaque backtest est tracé automatiquement : paramètres, métriques, comparaison vs buy-and-hold.

```bash
mlflow ui --port 5001          # en local
# ou : make docker             # MLflow inclus dans la stack Docker → http://localhost:5001
```

Les expériences sont stockées dans `./data/mlflow/` (SQLite backend) — données persistantes entre redémarrages.

## Tests

```bash
make tests                # tous les tests (pytest verbose)
make test-api             # endpoints API uniquement
make test-paper           # module paper trading uniquement
make test-cov             # tous les tests + rapport de couverture
```

## Structure du projet

```
├── api/
│   ├── routers/          # Endpoints FastAPI (ohlcv, market, signals, news, ml, alerts, paper_trading)
│   ├── schemas/          # Schémas Pydantic (validation requêtes/réponses)
│   ├── dependencies.py   # Session SQLAlchemy (get_db)
│   └── main.py           # App FastAPI + lifespan (WS collector)
├── frontend/
│   ├── pages/            # 6 pages Streamlit
│   ├── components/       # Composants réutilisables (chandelier, indicateurs, news)
│   ├── api_client.py     # Client HTTP vers l'API
│   └── app.py            # Point d'entrée Streamlit
├── src/
│   ├── collectors/       # OHLCV, ticker, news RSS, Fear & Greed, WebSocket prix live
│   ├── etl/              # Pipeline Extract → Transform → Load
│   ├── models/           # Modèles SQLAlchemy (OHLCV, ticker, market data, paper trading)
│   ├── paper_trading/    # Moteur paper trading (PaperTrader)
│   ├── services/         # DB session, LivePriceCache (singleton WS)
│   ├── analytics/        # Indicateurs techniques (SMA, EMA, RSI, MACD, BB)
│   ├── ml/
│   │   ├── backtesting/          # Walk-forward backtester
│   │   ├── feature_engineering/  # FeatureBuilder, DatasetBuilder
│   │   ├── models/               # BaselineModel, ModelEvaluator
│   │   ├── nlp/                  # Text mining : TF-IDF, entités, topics
│   │   └── mlflow_utils.py
│   └── quality/          # Validation des données
├── config/               # settings.py, config.yaml
├── docs/                 # Cahiers des charges (cadrage V2, paper trading)
├── scripts/              # fetch_history.py, collect_news.py, test_nlp.py…
├── tests/                # Suite de tests pytest
├── Makefile
├── docker-compose.yml
├── main.py               # Point d'entrée collecte OHLCV
└── requirements.txt
```

## Stack technique

| Couche | Technologie |
|---|---|
| Collecte | ccxt, CoinGecko API, feedparser |
| Prix temps réel | WebSocket Binance (`miniTicker`), `websockets` |
| Sentiment | vaderSentiment (news), Fear & Greed Index (alternative.me) |
| NLP / Text Mining | scikit-learn TF-IDF, regex, classification par mots-clés |
| Stockage | SQLAlchemy, SQLite (dev) / PostgreSQL (prod) |
| API | FastAPI, uvicorn |
| Frontend | Streamlit, Plotly, streamlit-autorefresh |
| ML | scikit-learn, XGBoost, pandas |
| Backtesting | Walk-forward maison (purge + embargo, Sharpe, drawdown) |
| Suivi ML | MLflow (SQLite backend, artifacts locaux) |
| Indicateurs | pandas-ta-classic |
| Infra | Docker, Docker Compose |
| Tests | pytest, pytest-cov, httpx |
