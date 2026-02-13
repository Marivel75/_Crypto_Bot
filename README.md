# Crypto Bot - Collecteur de Données Marché

## Description

Crypto Bot est un système complet de collecte de données marché pour les cryptomonnaies, conçu pour récupérer, valider et stocker des données OHLCV (historique) et des données de ticker (temps réel) depuis plusieurs exchanges (Binance, Kraken, Coinbase). Le système utilise une architecture ETL (Extract, Transform, Load) robuste avec validation des données, sauvegarde automatique et monitoring complet.

Le système collecte par défaut les données pour 5 paires majeures (BTC/USDT, ETH/USDT, BNB/USDT, SOL/USDT, ADA/USDT) sur les 3 principaux exchanges pour une couverture complète du marché.

## Architecture

Le projet utilise une architecture modulaire avec séparation claire des responsabilités :

### Architecture Principale

- **Point d'entrée** : `main.py` - Interface CLI unifiée avec gestion des arguments
- **Planificateurs** : `src/schedulers/` - Gestion OHLCV (historique) et Ticker (temps réel)
- **Collecteurs** : `src/collectors/` - Collecte des données depuis les exchanges
- **Pipeline ETL** : `src/etl/` - Traitement Extract, Transform, Load
- **Services** : `src/services/` - Base de données, clients exchanges, utilitaires
- **Modèles** : `src/models/` - Schémas de données SQLAlchemy
- **Analytics** : `src/analytics/` - Indicateurs techniques et visualisation
- **Qualité** : `src/quality/` - Validation et intégrité des données

### Patterns de Conception

- **Factory Pattern** : `ExchangeFactory` pour la création des clients d'exchanges
- **Pipeline Pattern** : ETL orchestré pour le traitement des données
- **Scheduler Pattern** : Planification automatique de la collecte
- **Repository Pattern** : Abstraction des opérations de base de données
- **Context Managers** : Gestion des ressources et transactions

### Flux de Données

**Pipeline OHLCV :**

```
Exchange API → OHLCVCollector → OHLCVExtractor → OHLCVTransformer → OHLCVLoader → Base de données
```

**Pipeline Ticker :**

```
Exchange API → TickerCollector → Cache mémoire → Snapshots périodiques → Base de données
```

**Processus ETL :**

1. **Extract** : Récupération des données brutes depuis les APIs
2. **Transform** : Validation, normalisation et enrichissement des données
3. **Load** : Stockage avec gestion des transactions et déduplication

## Prérequis

```bash
# Installer les dépendances
pip install -r requirements.txt

# Configurer la base de données (si nécessaire)
python scripts/reset_db.py
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

| Argument              | Description                                      | Valeur par défaut                                            |
| --------------------- | ------------------------------------------------ | ------------------------------------------------------------ |
| `--ticker`            | Active la collecte de ticker en temps réel       | Désactivé                                                    |
| `--pairs`             | Liste des paires de trading                      | ["BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "ADA/USDT"] |
| `--ticker-pairs`      | Liste des paires pour le ticker                  | Même que les paires principales                              |
| `--snapshot-interval` | Intervalle de sauvegarde des snapshots (minutes) | 5                                                            |
| `--runtime`           | Durée d'exécution (minutes, 0=illimité)          | 60                                                           |
| `--exchanges`         | Liste des exchanges à utiliser                   | ["binance", "kraken", coinbase"]                             |

**Exemples :**

```bash
# OHLCV + Ticker avec paramètres personnalisés
python main.py --ticker --exchanges binance kraken coinbase --ticker-pairs BTC/USDT ETH/USDT BNB/USDT SOL/USDT ADA/USDT --snapshot-interval 10 --runtime 120

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
python main.py --schedule --ticker --exchanges binance kraken coinbase --schedule-time "08:30"

# Planification multi-exchanges sans ticker
python main.py --schedule --exchanges binance kraken coinbase --schedule-time "07:45"
```

## Configuration

### Système de Configuration Centralisé

Le système utilise une configuration centralisée dans `config/settings.py` avec support multiple :

- **Fichiers de configuration** : YAML ou JSON
- **Variables d'environnement** : Surcharge automatique
- **Arguments de ligne de commande** : Personnalisation à l'exécution
- **Valeurs par défaut** : Configuration prête à l'emploi

### Configuration par défaut

- **Paires** : ["BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "ADA/USDT"]
- **Timeframes** : ["1h", "4h"]
- **Exchanges** : ["binance", "kraken", "coinbase"]
- **Heure de planification** : "09:00"
- **Intervalle de snapshot ticker** : 5 minutes
- **Durée d'exécution ticker** : 60 minutes

### Génération de Configuration

```bash
# Générer un fichier de configuration par défaut
python scripts/generate_config.py --format yaml --output config/config.yaml
```

### Variables d'Environnement

Les variables suivantes sont supportées :

- `CRYPTO_BOT_PAIRS` : Liste des paires
- `CRYPTO_BOT_EXCHANGES` : Liste des exchanges
- `CRYPTO_BOT_TICKER_ENABLED` : Activer/désactiver le ticker
- `CRYPTO_BOT_DB_URL` : URL de la base de données
- `CRYPTO_BOT_LOG_LEVEL` : Niveau de logging

## Schéma de Base de Données

### Table OHLCV (`ohlcv`)

Stocke les données historiques de bougies :

```sql
CREATE TABLE ohlcv (
    id VARCHAR(36) PRIMARY KEY,
    timestamp DATETIME NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    exchange VARCHAR(20) NOT NULL,
    open FLOAT NOT NULL,
    high FLOAT NOT NULL,
    low FLOAT NOT NULL,
    close FLOAT NOT NULL,
    volume FLOAT NOT NULL,
    -- Champs enrichis
    price_range FLOAT,
    price_change FLOAT,
    price_change_pct FLOAT,
    date VARCHAR(10),
    -- Métadonnées
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**Index optimisés :**

- `idx_ohlcv_symbol_timeframe` : Requêtes par paire/timeframe
- `idx_ohlcv_timestamp` : Requêtes temporelles
- `idx_ohlcv_symbol_timestamp` : Requêtes combinées

### Table Ticker Snapshots (`ticker_snapshots`)

Stocke les snapshots périodiques des prix temps réel :

```sql
CREATE TABLE ticker_snapshots (
    id VARCHAR(36) PRIMARY KEY,
    snapshot_time DATETIME NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    exchange VARCHAR(20) NOT NULL,
    price FLOAT,
    volume_24h FLOAT,
    price_change_24h FLOAT,
    price_change_pct_24h FLOAT,
    high_24h FLOAT,
    low_24h FLOAT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**Index optimisés :**

- `idx_ticker_snapshot_time` : Requêtes temporelles
- `idx_ticker_symbol_time` : Requêtes par symbole et temps

### Support Multi-Bases de Données

- **Développement** : SQLite avec création automatique des tables
- **Production** : PostgreSQL (Supabase) avec connexions poolées
- **Migration** : Scripts de sauvegarde/restauration automatiques

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

## Gestion des Erreurs et Qualité

### Système de Validation des Données

Le système inclut une validation complète des données via `DataValidator0HCLV` :

**Validation des prix :**

- Détection des valeurs NaN et négatives
- Vérification de la cohérence (high ≥ low)
- Alertes pour les valeurs anormales

**Validation des volumes :**

- Détection des volumes négatifs
- Alertes pour les volumes excessifs

**Validation temporelle :**

- Détection des trous temporels
- Vérification de la continuité

**Validation structurelle :**

- Vérification des colonnes requises
- Validation des types de données

### Gestion des Erreurs Multi-Niveaux

**Couche Validation :** Validation des entrées et sanitisation
**Couche Métier :** Gestion des erreurs spécifiques au domaine
**Couche Infrastructure :** Gestion des erreurs base de données/API
**Couche Interface :** Messages d'erreur conviviaux

### Stratégies de Gestion

- **Try-catch** spécifiques avec types d'exceptions
- **Dégradation gracieuse** en cas d'échec partiel
- **Logging complet** avec contexte et stack traces
- **Mécanismes de retry** avec backoff exponentiel
- **Rollback automatique** des transactions en cas d'erreur

### Monitoring et Logging

**Système de logging complet :**

- Niveaux configurables (DEBUG, INFO, WARNING, ERROR)
- Sorties multiples (console, fichier)
- Rotation automatique des logs
- Contexte structuré pour le débuggage

**Métriques et monitoring :**

- Métriques de performance du pipeline ETL
- Compteurs de succès/échec par exchange
- Temps de traitement par symbole/timeframe
- Alertes sur les anomalies de données

## Développement et Tests

### Suite de Tests Complète

**89 tests unitaires et d'intégration couvrant :**

**Tests ETL (42 tests) :**

- `test_etl_extractor.py` (9 tests) : Extraction des données
- `test_etl_transformer.py` (12 tests) : Transformation et validation
- `test_etl_loader.py` (18 tests) : Chargement en base de données
- `test_etl_pipeline.py` (13 tests) : Orchestration complète

**Tests de Qualité (22 tests) :**

- `test_data_validator.py` : Validation des données OHLCV

**Tests de Services (15 tests) :**

- `test_ohlcv_collector.py` : Collecte des données historiques
- `test_ticker_service.py` : Services de ticker temps réel

**Tests d'intégration :**

- Tests multi-exchanges
- Validation de bout en bout
- Tests de performance

### Exécution des Tests

```bash
# Exécuter tous les tests
python -m pytest tests/ -v

# Tests avec couverture
python scripts/run_tests.py --coverage --report

# Tests par catégorie
python scripts/run_tests.py --type etl
python scripts/run_tests.py --type validation
python scripts/run_tests.py --type unit

# Tests d'intégration complets
python scripts/test_main.py

# Tests en environnement live
python scripts/test_live_sqlite.py
```

### Structure du Projet

```
├── src/                              # Code source principal
│   ├── schedulers/                   # Planificateurs de tâches
│   │   ├── scheduler_ohlcv.py        # Planification OHLCV
│   │   └── scheduler_ticker.py       # Planification ticker
│   ├── collectors/                   # Collecteurs de données
│   │   ├── ohlcv_collector.py       # Collecteur OHLCV
│   │   └── ticker_collector.py       # Collecteur ticker
│   ├── etl/                          # Pipeline ETL
│   │   ├── extractor.py              # Extraction
│   │   ├── transformer.py            # Transformation
│   │   ├── loader.py                 # Chargement
│   │   └── pipeline_ohlcv.py         # Orchestration
│   ├── services/                     # Services et utilitaires
│   │   ├── db.py                    # Base de données
│   │   ├── db_context.py             # Context managers
│   │   ├── exchange_context.py       # Context managers exchanges
│   │   └── exchange_factory.py       # Factory clients exchanges
│   ├── models/                       # Modèles SQLAlchemy
│   │   ├── ohlcv.py                  # Modèle OHLCV
│   │   └── ticker.py                 # Modèle Ticker
│   ├── quality/                      # Validation qualité
│   │   └── validator.py              # Validateur de données
│   ├── analytics/                    # Analytics et visualisation
│   │   ├── indicators.py             # Indicateurs techniques
│   │   ├── plot_manager.py           # Gestion graphiques
│   │   └── db_inspector.py          # Inspection base de données
│   └── services/exchanges_api/       # Clients API exchanges
│       ├── binance_client.py          # Client Binance
│       ├── kraken_client.py           # Client Kraken
│       └── coinbase_client.py         # Client Coinbase
├── scripts/                          # Scripts utilitaires
│   ├── backup_db.py                  # Sauvegarde base
│   ├── restore_db.py                 # Restauration base
│   ├── schedule_backups.py           # Planification sauvegardes
│   ├── check_db.py                   # Vérification base
│   ├── reset_db.py                   # Réinitialisation base
│   ├── generate_config.py            # Génération config
│   ├── run_tests.py                  # Exécution tests
│   └── test_main.py                  # Tests intégration
├── tests/                            # Suite de tests
│   ├── test_*.py                     # Tests unitaires
│   └── README.md                     # Documentation tests
├── config/                           # Fichiers configuration
│   ├── settings.py                   # Gestion configuration
│   └── config.yaml                   # Configuration par défaut
├── data/                             # Données locales
│   ├── processed/                    # Base de données SQLite
│   └── backups/                      # Sauvegardes automatiques
├── logs/                             # Logs d'exécution
├── main.py                           # Point d'entrée principal
├── logger_settings.py                # Configuration logging
└── requirements.txt                  # Dépendances Python
```

### Environnement de Développement

**Prérequis :**

- Python 3.8+
- pip (gestionnaire de paquets)
- Git

**Installation :**

```bash
# Cloner le dépôt
git clone <repository-url>
cd _Crypto_Bot

# Installer les dépendances
pip install -r requirements.txt

# Générer la configuration par défaut
python scripts/generate_config.py

# Initialiser la base de données
python scripts/reset_db.py
```

## Opérations et Maintenance

### Scripts de Maintenance

**Gestion de la base de données :**

```bash
# Vérification de la base
python scripts/check_db_modern.py

# Vérification complète via DBInspector
python -c "from src.analytics.db_inspector import DBInspector; DBInspector().run_complete_check()"

# Réinitialiser complètement la base
python scripts/reset_db.py

# Sauvegarder manuellement
python scripts/backup_db.py

# Restaurer depuis sauvegarde
python scripts/restore_db.py
```

**Planification des sauvegardes :**

```bash
# Démarrer le service de sauvegarde automatique
python scripts/schedule_backups.py

# Exécuter en arrière-plan
nohup python scripts/schedule_backups.py > /dev/null 2>&1 &
```

### Restauration de la Base de Données

Le script `restore_db.py` permet de restaurer la base de données à partir des sauvegardes.

**Types de sauvegardes disponibles :**

- **SQL** (`full_backup_*.sql`) : Dump complet de la base SQLite
- **CSV** (`csv_*/`) : Sauvegarde des tables en fichiers CSV (ohlcv.csv, ticker.csv)
- **JSON** (`essential_backup_*.json`) : Métadonnées et statistiques (pas de données brutes)

**Commandes disponibles :**

```bash
# Lister les sauvegardes disponibles
python scripts/restore_db.py --list

# Vérifier l'état actuel de la base de données
python scripts/restore_db.py --verify

# Mode interactif (choix de la sauvegarde à restaurer)
python scripts/restore_db.py
```

**Mode interactif :**

1. Affiche la liste des sauvegardes disponibles
2. Permet de choisir laquelle restaurer
3. Supprime les données existantes et insère les données de la sauvegarde
4. Vérifie l'intégrité après restauration

**Exemple de sortie :**

```
==================================================
MENU DE RESTAURATION
==================================================

📦 Sauvegardes SQL:
  0) full_backup_20260213_075111.sql

📊 Sauvegardes CSV:
  1) csv_20260213_075111

📋 Sauvegardes essentielles (métadonnées):
  2) essential_backup_20260213_075111.json

  q) Quitter
==================================================
```

**Note :** La restauration CSV est recommandée car elle restaure à la fois les tables `ohlcv` et `ticker_snapshots`. La sauvegarde JSON ne contient que les métadonnées.

### Collecte de Données Market Data (CoinGecko)

Le système intègre la collecte de données globales du marché crypto via l'API CoinGecko.

**Données collectées :**

- Capitalisation totale du marché (par devise: USD, EUR, BTC, etc.)
- Volume total d'échange (par devise)
- Dominance des principales cryptomonnaies (BTC, ETH, etc.)
- Nombre de cryptomonnaies, de marchés, d'ICOs

**Configuration (dans `config/settings.py`) :**

```python
"market_data": {
    "enabled": True,           # Activé par défaut
    "schedule_time": "10:00",  # Heure de collecte quotidienne
}
```

**Tables de données :**

- `global_market_snapshot` : Snapshot principal avec métadonnées globales
- `global_market_cap` : Capitalisation par devise (63 devises)
- `global_market_volume` : Volume par devise (63 devises)
- `global_market_dominance` : Dominance par cryptomonnaie (10+ actifs)

**Utilisation :**

```bash
# La collecte Market Data s'exécute automatiquement avec main.py
python main.py

# Mode planifié (collecte quotidienne)
python main.py --schedule

# Exécution manuelle
python -c "from src.schedulers.scheduler_market_data import MarketDataScheduler; MarketDataScheduler().run_once()"
```

### Monitoring

**Inspection de la base de données :**

```python
from src.analytics.db_inspector import DBInspector

# Créer un inspecteur
inspector = DBInspector()

# Vérification complète (recommandée)
inspector.run_complete_check()

# Inspection individuelle
inspector.inspect_db()

# Statistiques détaillées
stats = inspector.get_db_stats()
inspector.print_db_summary(stats)

# Vérification de santé
health = inspector.check_db_health()
inspector.print_health_summary(health)

# Récupérer les données OHLCV
ohlcv_data = inspector.get_ohlcv_data(
    symbol="BTC/USDT",
    limit=100,
    start_date="2024-01-01"
)

# Formater la taille
size_formatted = inspector.format_bytes(1048576)  # Returns "1.00 MB"
```

**Analytics et indicateurs :**

```python
from src.analytics.indicators import calculate_sma
from src.analytics.plot_manager import PlotManager

# Calculer une SMA
sma = calculate_sma(data, window=20)

# Visualiser les données
plotter = PlotManager()
plotter.plot_with_sma(data, sma, window=20)
```

### Gestion des Logs

**Consultation des logs :**

```bash
# Logs de l'application
tail -f crypto_bot.log

# Logs de sauvegarde
tail -f logs/backup.log

# Logs de restauration
tail -f logs/restore.log

# Logs de planification
tail -f logs/schedule_backups.log
```

### Performance et Scalabilité

**Optimisations intégrées :**

- Connexions poolées à la base de données
- Insertion par batches pour gros volumes
- Cache mémoire pour données temps réel
- Index optimisés pour requêtes fréquentes
- Gestion des rate limits des APIs

**Métriques disponibles :**

- Temps de traitement par symbole
- Taux de succès par exchange
- Volume de données traitées
- Erreurs et alertes

## Contribution

### Processus de Développement

1. **Forker** le dépôt
2. **Créer une branche** : `git checkout -b feature/nouvelle-fonctionnalite`
3. **Développer** avec tests unitaires
4. **Valider** le code avec les linters
5. **Tester** : `python scripts/run_tests.py --coverage`
6. **Committer** : `git commit -m 'Ajout: description de la fonctionnalité'`
7. **Pusher** : `git push origin feature/nouvelle-fonctionnalite`
8. **Ouvrir une Pull Request**

### Standards de Code

- **Style** : PEP 8 avec Black/isort
- **Tests** : Couverture > 80%
- **Documentation** : Docstrings pour toutes les fonctions publiques
- **Logging** : Messages structurés avec contexte
- **Configuration** : Pas de hardcoding, utiliser settings

### Types de Contributions

- **Bug fixes** : Corrections d'anomalies
- **Nouveaux exchanges** : Intégration d'autres plateformes
- **Indicateurs techniques** : Ajout d'analyses avancées
- **Performance** : Optimisations et scalabilité
- **Documentation** : Amélioration de la documentation
- **Tests** : Amélioration de la couverture

## License

Ce projet est sous license MIT. Voir le fichier LICENSE pour plus de détails.

## Configuration Multi-Exchange Étendue

Le système est maintenant configuré par défaut pour une couverture maximale du marché :

### Exchanges Supportés (par défaut)

- **Binance** : Liquidité maximale, paires majeures
- **Kraken** : Fiabilité européenne, données historiques riches
- **Coinbase** : Conformité réglementaire, APIs stables

### Paires Majeures (par défaut)

- **BTC/USDT** : Bitcoin - Référence du marché
- **ETH/USDT** : Ethereum - Plateforme smart contracts
- **BNB/USDT** : Binance Coin - Écosystème Binance
- **SOL/USDT** : Solana - Hauts débits et faibles coûts
- **ADA/USDT** : Cardano - Approche académique durable

### Avantages de cette Configuration

**Diversification des sources** :

- Réduction du risque de dépendance à un seul exchange
- Comparaison des prix et volumes entre plateformes
- Détection d'anomalies ou d'arbitrages potentiels

**Couverture du marché** :

- 5 paires représentant ~80% de la capitalisation crypto
- Différentes catégories (store of value, smart contracts, DeFi)
- Données pertinentes pour l'analyse technique

**Redondance et fiabilité** :

- Si un exchange est indisponible, les autres continuent
- Validation croisée des données entre exchanges
- Historique plus robuste et complet

---

**Dernière mise à jour** : Février 2026  
**Version** : 2.1  
**État** : Production Ready - Multi-Exchange par défaut
