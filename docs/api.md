# API REST — Référence

L'API FastAPI démarre sur le port **8000**. Documentation interactive : `http://localhost:8000/docs`

Au démarrage, elle crée les tables SQLAlchemy absentes et lance le collecteur WebSocket Binance en thread daemon.

## Endpoints principaux

### OHLCV

| Méthode | Route | Description |
|---------|-------|-------------|
| `GET` | `/ohlcv` | Bougies OHLCV (exchange, symbol, timeframe, limit) |
| `GET` | `/ohlcv/symbols` | Liste des paires disponibles |

### Market Data

| Méthode | Route | Description |
|---------|-------|-------------|
| `GET` | `/market/fear-greed` | Fear & Greed Index (CoinGecko) |
| `GET` | `/market/global` | Market cap global, dominance BTC |
| `GET` | `/market/top-movers` | Top gainers / losers |
| `GET` | `/market/history` | Historique market cap |

### Signaux techniques

| Méthode | Route | Description |
|---------|-------|-------------|
| `GET` | `/signals` | RSI, MACD, BB, SMA + score BUY/SELL/HOLD |

### News & Veille

| Méthode | Route | Description |
|---------|-------|-------------|
| `GET` | `/news` | Articles RSS (filtres : source, sentiment, symbole, limit) |
| `GET` | `/news/sources` | Sources disponibles |
| `GET` | `/news/topics` | Topics disponibles |

### Alertes email

| Méthode | Route | Description |
|---------|-------|-------------|
| `POST` | `/alerts/subscribe` | S'abonner aux alertes de collecte |
| `DELETE` | `/alerts/unsubscribe/{email}` | Se désabonner |
| `GET` | `/alerts/subscribers` | Liste des abonnés actifs |

### ML & Backtesting

| Méthode | Route | Description |
|---------|-------|-------------|
| `GET` | `/ml/backtest` | Lancer un backtest walk-forward |
| `GET` | `/ml/features` | Aperçu des features générées |

### Paper Trading

| Méthode | Route | Description |
|---------|-------|-------------|
| `POST` | `/paper-trading/portfolios` | Créer un portefeuille |
| `GET` | `/paper-trading/portfolios` | Lister les portefeuilles |
| `GET` | `/paper-trading/portfolios/{id}` | Résumé complet (métriques + positions) |
| `POST` | `/paper-trading/orders` | Ouvrir une position BUY |
| `POST` | `/paper-trading/orders/{id}/close` | Fermer une position |
| `GET` | `/paper-trading/orders` | Historique des trades (filtrable) |
| `GET` | `/paper-trading/live-prices` | Prix live depuis le cache WebSocket |
| `GET` | `/paper-trading/live-prices/status` | État de la connexion WebSocket |

### Utilitaires

| Méthode | Route | Description |
|---------|-------|-------------|
| `GET` | `/health` | Santé de l'API |

## Lancer l'API manuellement

```bash
uvicorn api.main:app --reload --port 8000
```
