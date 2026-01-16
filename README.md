# Crypto Bot - Collecteur de Données Marché

## Description

Crypto Bot est un système de collecte de données marché pour les cryptomonnaies. Il permet de récupérer des données OHLCV (historique) et des données de ticker (temps réel) depuis plusieurs exchanges (Binance, Kraken, Coinbase).

## Architecture

Le projet utilise une architecture modulaire avec une séparation claire entre :

- **Données OHLCV** (historique) : gérées par `scheduler_ohlcv.py`
- **Données de ticker** (temps réel) : gérées par `scheduler_ticker.py`
- **Point d'entrée unifié** : `main.py`

## Prérequis

```bash
# Installer les dépendances
pip install -r requirements.txt

# Configurer la base de données (si nécessaire)
python scripts/reset_database.py
```

## Utilisation

### 1. Exécution unique (mode par défaut)

Collecte immédiate des données OHLCV sans planification.

```bash
python main.py
```

### 2. Tests complets

Avant d'exécuter en production, vous pouvez tester toutes les fonctionnalités :

```bash
# Test complet (OHLCV + Ticker + Multi-exchanges)
python scripts/test_main.py
```

**Le script `test_main.py` teste :**
- Collecte OHLCV depuis plusieurs exchanges
- Collecte de ticker en temps réel
- Fonctionnement multi-exchanges
- Qualité des données et intégrité de la base

**Options disponibles :**

| Argument              | Description                                      | Valeur par défaut               |
| --------------------- | ------------------------------------------------ | ------------------------------- |
| `--ticker`            | Active la collecte de ticker en temps réel       | Désactivé                       |
| `--ticker-pairs`      | Liste des paires pour le ticker                  | Même que les paires principales |
| `--snapshot-interval` | Intervalle de sauvegarde des snapshots (minutes) | 5                               |
| `--runtime`           | Durée d'exécution (minutes, 0=illimité)          | 60                              |
| `--exchanges`         | Liste des exchanges à utiliser                   | ["binance"]                     |

**Exemples :**

```bash
# OHLCV + Ticker avec paramètres personnalisés
python main.py --ticker --exchanges binance kraken --ticker-pairs BTC/USDT ETH/USDT --snapshot-interval 10 --runtime 120

# Plusieurs exchanges sans ticker
python main.py --exchanges binance kraken coinbase
```

### 2. Mode planifié (collecte quotidienne)

```bash
python main.py --schedule
```

**Options supplémentaires pour le mode planifié :**

| Argument          | Description                              | Valeur par défaut |
| ----------------- | ---------------------------------------- | ----------------- |
| `--schedule-time` | Heure de la collecte quotidienne (HH:MM) | "09:00"           |

**Exemples :**

```bash
# Planification avec OHLCV + Ticker
python main.py --schedule --ticker --exchanges binance kraken --schedule-time "08:30"

# Planification multi-exchanges sans ticker
python main.py --schedule --exchanges binance kraken coinbase --schedule-time "07:45"
```

## Configuration par défaut

- **Paires** : ["BTC/USDT", "ETH/USDT"]
- **Timeframes** : ["1h", "4h"]
- **Exchanges** : ["binance"]
- **Heure de planification** : "09:00"
- **Intervalle de snapshot ticker** : 5 minutes
- **Durée d'exécution ticker** : 60 minutes

## Structure des données

### Données OHLCV (historique)

Stockées dans la table `ohlcv_data` :

- `symbol` : Paire de trading (ex: BTC/USDT)
- `exchange` : Exchange source
- `timeframe` : Timeframe (1h, 4h, etc.)
- `open`, `high`, `low`, `close` : Prix OHLC
- `volume` : Volume de trading
- `timestamp` : Horodatage

### Données de ticker (temps réel)

Stockées dans la table `ticker_snapshots` :

- `symbol` : Paire de trading
- `exchange` : Exchange source
- `price` : Prix actuel
- `volume_24h` : Volume sur 24h
- `price_change_24h` : Variation de prix sur 24h
- `price_change_pct_24h` : Variation en pourcentage
- `high_24h`, `low_24h` : Plus haut/bas sur 24h
- `snapshot_time` : Heure du snapshot

## Exemples complets

### 1. Collecte unique avec ticker pour surveillance en temps réel

```bash
python main.py \
  --ticker \
  --exchanges binance kraken \
  --ticker-pairs BTC/USDT ETH/USDT SOL/USDT \
  --snapshot-interval 10 \
  --runtime 180
```

Ce commande va :

1. Collecter les données OHLCV pour BTC/USDT et ETH/USDT sur Binance et Kraken
2. Démarrer la collecte de ticker en temps réel pour BTC/USDT, ETH/USDT et SOL/USDT
3. Sauvegarder des snapshots toutes les 10 minutes
4. S'exécuter pendant 180 minutes (3 heures)

### 2. Planification quotidienne avec surveillance continue

```bash
python main.py \
  --schedule \
  --ticker \
  --exchanges binance kraken coinbase \
  --schedule-time "08:15" \
  --runtime 0  # Illimité
```

Ce commande va :

1. Exécuter immédiatement une collecte OHLCV initiale
2. Démarrer la collecte de ticker en temps réel (illimitée)
3. Planifier une collecte OHLCV quotidienne à 08:15
4. Surveiller Binance, Kraken et Coinbase

## Gestion des erreurs

Le système inclut une gestion robuste des erreurs :

- Journalisation détaillée avec `logger_settings.py`
- Gestion des exceptions pour chaque composant
- Arrêt propre des threads et collecteurs
- Messages d'erreur clairs et informatifs

## Développement

### Tests

```bash
# Exécuter les tests
python scripts/run_tests.py

# Tester la connexion à la base de données
python scripts/test_live_sqlite.py
```

### Structure du projet

```
src/
├── scheduler_ohlcv.py      # Planification des données OHLCV
├── scheduler_ticker.py     # Planification des données de ticker
├── collectors/             # Collecteurs de données
├── services/               # Services et clients API
├── etl/                    # Pipeline ETL
└── models/                 # Modèles de données

scripts/                   # Scripts utilitaires
main.py                    # Point d'entrée principal
README.md                  # Documentation
```

## Contribution

Pour contribuer au projet :

1. Forker le dépôt
2. Créer une branche pour votre fonctionnalité (`git checkout -b feature/nouvelle-fonctionnalite`)
3. Committer vos changements (`git commit -m 'Ajout de nouvelle fonctionnalité'`)
4. Pusher vers la branche (`git push origin feature/nouvelle-fonctionnalite`)
5. Ouvrir une Pull Request

## License

Ce projet est sous license MIT. Voir le fichier LICENSE pour plus de détails.
