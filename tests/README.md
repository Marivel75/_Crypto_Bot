# Tests Crypto Bot

Ce répertoire contient tous les tests pour le projet Crypto Bot.
Les tests sont aussi lancés par un workflow `tests.yml` sur GitHub Actions.

## Structure

```
tests/
├── test_ohlcv_collector.py        # OHLCVCollector
├── test_ticker_service.py         # TickerCollector et TickerCache
├── test_data_validator.py         # DataValidator
├── test_etl_extractor.py          # OHLCVExtractor
├── test_etl_transformer.py        # OHLCVTransformer
├── test_etl_loader.py             # OHLCVLoader
├── test_etl_pipeline.py           # ETLPipelineOHLCV
├── test_feature_builder.py        # FeatureBuilder (ML)
├── test_dataset_builder.py        # DatasetBuilder (ML)
├── test_baseline.py               # BaselineModel (ML)
├── test_evaluator.py              # Evaluator (ML)
├── test_api.py                    # API FastAPI (health, ohlcv, market, signals)
├── test_frontend_utils.py         # Frontend — utils (fmt_ts, extract_*)
├── test_frontend_api_client.py    # Frontend — APIClient (httpx mocké)
├── test_frontend_components.py    # Frontend — candlestick, indicators
└── README.md
```

## Lancer tous les tests

La commande à retenir — exécute l'intégralité de la suite en mode verbeux :

```bash
./scripts/run_tests.py --verbose
```

Avec rapport de couverture (src/ + api/) :

```bash
./scripts/run_tests.py --verbose --coverage
```

Avec rapport HTML en plus :

```bash
./scripts/run_tests.py --verbose --coverage --report
open htmlcov/index.html
```

> Le script est exécutable directement (`chmod +x` déjà appliqué). Si nécessaire : `python scripts/run_tests.py --verbose`.

## Lancer un groupe de tests

```bash
# Tests collecteurs (OHLCV + ticker)
./scripts/run_tests.py --type unit --verbose

# Tests validation des données
./scripts/run_tests.py --type validation --verbose

# Tests ETL (extractor, transformer, loader, pipeline)
./scripts/run_tests.py --type etl --verbose

# Tests Machine Learning (features, dataset, baseline, evaluator)
./scripts/run_tests.py --type ml --verbose

# Tests API FastAPI
./scripts/run_tests.py --type api --verbose

# Tests Frontend Streamlit
./scripts/run_tests.py --type frontend --verbose
```

## Lancer un test précis avec pytest

```bash
# Un fichier
python -m pytest tests/test_api.py -v

# Une classe
python -m pytest tests/test_api.py::TestSignals -v

# Un test unitaire
python -m pytest tests/test_api.py::TestSignals::test_returns_data_with_indicators -v
```

## Détail des tests

### test_ohlcv_collector.py — 15 tests
Initialisation, validation des paramètres, `fetch_and_store`, gestion des erreurs et doublons.

### test_ticker_service.py — 15 tests
Cache ticker, boucle de collecte, snapshots en base.

### test_data_validator.py — 22 tests
Structure DataFrame, prix (NaN, négatifs, très bas), volume, cohérence high/low, métadonnées.

### test_etl_extractor.py — 9 tests
Extraction unitaire et batch, gestion des erreurs d'extraction.

### test_etl_transformer.py — 12 tests
Transformation, enrichissement, normalisation des symboles, batch.

### test_etl_loader.py — 18 tests
Chargement, transactions, rollback, gestion des doublons, batch.

### test_etl_pipeline.py — 13 tests
Orchestration complète Extract→Transform→Load, métriques, erreurs partielles.

### test_feature_builder.py
Features de retour, volatilité, indicateurs techniques, structure des bougies, volume, temporel.

### test_dataset_builder.py
Création des datasets supervisés (X, y), encodage de la cible, TimeSeriesSplit.

### test_baseline.py
Entraînement et prédiction : Dummy, LogisticRegression, RandomForest. Cross-validation.

### test_evaluator.py
Métriques : accuracy, precision, recall, F1. Cas limites (prédictions vides, classes absentes).

### test_api.py — 34 tests
Base SQLite en mémoire + `StaticPool`, override de la dépendance `get_db`.

- **TestHealth** (2) : status ok, connexion DB
- **TestOHLCV** (8) : filtres symbol/timeframe/exchange, limit, schéma, tri DESC
- **TestOHLCVSymbols** (4) : liste, schéma, count, filtre exchange
- **TestOHLCVLatest** (2) : données retournées, timeframe par défaut
- **TestMarketTop** (5) : snapshot, limit, schéma, tri par rank, 404 devise inconnue
- **TestMarketGlobal** (3) : données, schéma, liste dominance
- **TestMarketTicker** (3) : liste, filtre symbol, schéma
- **TestSignals** (7) : symbol obligatoire, indicateurs présents et numériques, 404, limites min/max

## Couverture

```bash
# Terminal
./scripts/run_tests.py --coverage

# HTML
./scripts/run_tests.py --coverage --report
open htmlcov/index.html

# Avec pytest directement (src + api)
python -m pytest --cov=src --cov=api tests/ --cov-report=term
```

*Mise à jour : 26/04/2026 — 251 tests au total*
