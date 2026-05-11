# ML, Backtesting & NLP

## Backtesting ML

Disponible via `GET /ml/backtest` et la page **ML & Backtesting** du frontend.

**Prérequis** : lancer `make history` au moins une fois (minimum ~200 jours de données journalières).

### Modèles évalués

- Random Forest
- Régression Logistique
- Dummy (baseline)

### Méthode

Walk-forward avec purge et embargo pour éviter le data leakage.

### Métriques

Sharpe ratio, win rate, PnL cumulé, drawdown max, profit factor, comparaison vs buy-and-hold.

## MLflow

Chaque backtest est tracé automatiquement (paramètres, métriques, artifacts).

```bash
make mlflow     # Lance MLflow seul → http://localhost:5001
make run-all    # Lance API + MLflow + Streamlit ensemble
make docker     # MLflow inclus dans la stack Docker
```

Stockage local : `mlflow-local.db` (backend SQLite) + `mlflow-artifacts/`.

## NLP & Text Mining

Module `src/ml/nlp/` — enrichissement automatique de chaque article RSS collecté.

| Analyse | Méthode | Exemple de résultat |
|---|---|---|
| Mots-clés | TF-IDF (unigrammes + bigrammes) | `["etf approved", "sec", "rally"]` |
| Entités | Regex + dictionnaire | `{"crypto_symbols": ["BTC","ETH"], "exchanges": ["binance"]}` |
| Topics | Classification par mots-clés | `["regulation", "adoption"]` |

Topics reconnus : `regulation`, `hack_security`, `adoption`, `defi`, `nft`, `macro`, `price_action`, `general`.

## Feature Engineering

Le `FeatureBuilder` génère automatiquement les features techniques à partir des bougies OHLCV :
SMA, EMA, RSI, MACD, Bollinger Bands, volume relatif, retours logarithmiques.

```bash
# Aperçu des features via l'API
GET /ml/features?symbol=BTC/USDT&timeframe=1d
```
