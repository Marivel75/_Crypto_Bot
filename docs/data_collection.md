# Collecte de données

## OHLCV incrémental

```bash
make collect                               # Binance (défaut)
make collect EXCHANGES="binance kraken"    # Plusieurs exchanges
make collect-schedule                      # Planifié quotidiennement à 09:00
make collect-live                          # OHLCV incrémental + ticker en parallèle
```

Ou directement :

```bash
python main.py
python main.py --schedule
python main.py --exchanges binance kraken
```

## Ticker temps réel

```bash
make ticker                                        # Binance, 120s
make ticker EXCHANGES="binance coinbase" RUNTIME=300
```

## Historique complet (requis pour le backtesting)

Le backtesting ML nécessite au minimum ~200 jours de données journalières.

```bash
make history

# Options avancées
python scripts/fetch_history.py --exchange binance --timeframes 1d --limit 1000
python scripts/fetch_history.py --pairs BTC/USDT ETH/USDT --timeframes 1d 4h
```

## Actualités crypto (RSS)

```bash
make news                              # Une passe unique
python scripts/collect_news.py         # Boucle toutes les 60 min
```

Chaque article collecté est enrichi automatiquement :
- **Sentiment** : score VADER (positif / négatif / neutre)
- **Mots-clés** : TF-IDF (unigrammes + bigrammes)
- **Entités** : symboles crypto, exchanges (regex + dictionnaire)
- **Topics** : `regulation`, `hack_security`, `adoption`, `defi`, `nft`, `macro`, `price_action`, `general`

## Alertes email

Les abonnés reçoivent un email au démarrage et à la fin de chaque collecte.  
Configurer via les variables `ALERT_EMAIL_*` dans `.env` (voir README).

## Base de données

```bash
make db-check               # Vérifie la connexion active
make db-inspect             # Inspecte le contenu (SQLite par défaut)
make db-inspect DB=postgres
make db-migrate             # Migre SQLite → PostgreSQL
```

Voir `docs/database_schema.md` pour le schéma complet des tables.
