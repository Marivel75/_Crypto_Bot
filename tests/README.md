# 🧪 Tests Crypto Bot

Ce répertoire contient tous les tests pour le projet Crypto Bot.
Les tests sont aussi lancés par un workflow tests.yml sur github.

## 📁 Structure

```
tests/
├── test_market_collector.py  # Tests unitaires pour MarketCollector
├── test_data_validator.py    # Tests unitaires pour DataValidator
├── test_etl_extractor.py    # Tests unitaires pour OHLCVExtractor
├── test_etl_transformer.py   # Tests unitaires pour OHLCVTransformer
├── test_etl_loader.py       # Tests unitaires pour OHLCVLoader
├── test_etl_pipeline.py     # Tests unitaires pour ETLPipeline
├── README.md                # Documentation des tests
└── integration/             # (À venir) Tests d'intégration
```

## 🚀 Exécution des Tests

### 1. Exécution de base

```bash
# Exécuter tous les tests
python -m pytest tests/ -v

# Exécuter un fichier de test spécifique
python -m pytest tests/test_market_collector.py -v

# Exécuter un test spécifique
python -m pytest tests/test_market_collector.py::TestMarketCollectorInitialization::test_initialization_with_valid_parameters -v
```

### 2. Exécution des tests ETL

```bash
# Exécuter tous les tests ETL
python -m pytest tests/test_etl_*.py -v

# Exécuter les tests de l'extracteur
python -m pytest tests/test_etl_extractor.py -v

# Exécuter les tests du transformateur
python -m pytest tests/test_etl_transformer.py -v

# Exécuter les tests du chargeur
python -m pytest tests/test_etl_loader.py -v

# Exécuter les tests du pipeline
python -m pytest tests/test_etl_pipeline.py -v

# Exécuter un test spécifique du pipeline
python -m pytest tests/test_etl_pipeline.py::TestETLPipeline::test_run_batch_success -v
```

### 3. Utilisation du script de test

```bash
# Aide
python scripts/run_tests.py --help

# Exécuter les tests unitaires (MarketCollector)
python scripts/run_tests.py --type unit --verbose

# Exécuter les tests de validation (DataValidator)
python scripts/run_tests.py --type validation --verbose

# Exécuter les tests ETL
python scripts/run_tests.py --type etl --verbose

# Exécuter tous les tests avec couverture
python scripts/run_tests.py --coverage

# Générer un rapport HTML
python scripts/run_tests.py --coverage --report

# Exécuter un test spécifique avec pytest directement
python -m pytest tests/test_data_validator.py::TestCompleteOHLCVValidation::test_validate_complete_valid_data -v
```

## 📊 Tests Actuels

### test_market_collector.py

**15 tests** couvrant :

- **Initialisation** (8 tests) :

  - Validation des paramètres d'entrée
  - Gestion des exchanges (Binance, Kraken, Coinbase)
  - Gestion des erreurs de configuration

- **Validation** (3 tests) :

  - Validation des paires et timeframes
  - Gestion des valeurs vides et invalides

- **Fonctionnement** (4 tests) :
  - Test de `fetch_and_store` avec succès
  - Gestion des exceptions
  - Gestion des doublons
  - Intégration avec le pipeline ETL

### test_data_validator.py

**22 tests** couvrant le module de validation des données :

- **Initialisation** (1 test) :
  - Test des valeurs par défaut du valideur

- **Validation de structure** (3 tests) :
  - DataFrame vide
  - Colonnes manquantes
  - Structure valide

- **Validation des prix** (5 tests) :
  - Prix NaN, non numériques, négatifs
  - Prix très bas (warnings)
  - Prix valides

- **Validation du volume** (4 tests) :
  - Volume NaN, négatif
  - Volume très élevé (warnings)
  - Volume valide

- **Validation de cohérence** (2 tests) :
  - Cohérence high/low
  - Prix d'ouverture/fermeture négatifs

- **Validation des métadonnées** (3 tests) :
  - Symbol et timeframe invalides
  - Métadonnées valides

- **Validation complète** (3 tests) :
  - Données complètement valides
  - Données avec erreurs
  - Données avec warnings

### test_etl_extractor.py

**9 tests** couvrant le composant d'extraction :

- **Initialisation** (2 tests) :
  - Initialisation avec exchange valide
  - Gestion des erreurs d'initialisation

- **Extraction** (4 tests) :
  - Extraction réussie
  - Gestion des erreurs d'extraction
  - Extraction avec données vides
  - Extraction avec données partielles

- **Batch** (3 tests) :
  - Extraction batch réussie
  - Gestion des erreurs batch
  - Extraction batch avec symboles multiples

### test_etl_transformer.py

**12 tests** couvrant le composant de transformation :

- **Initialisation** (1 test) :
  - Initialisation avec valideur

- **Transformation** (6 tests) :
  - Transformation réussie
  - Gestion des erreurs de transformation
  - Transformation avec données manquantes
  - Transformation avec données invalides
  - Enrichissement des données
  - Normalisation des données

- **Batch** (5 tests) :
  - Transformation batch réussie
  - Gestion des erreurs batch
  - Transformation batch avec symboles multiples
  - Transformation batch avec données mixtes
  - Transformation batch avec erreurs partielles

### test_etl_loader.py

**18 tests** couvrant le composant de chargement :

- **Initialisation** (2 tests) :
  - Initialisation avec base de données valide
  - Gestion des erreurs d'initialisation

- **Chargement** (6 tests) :
  - Chargement réussi
  - Gestion des erreurs de chargement
  - Chargement avec données vides
  - Chargement avec doublons
  - Chargement avec données invalides
  - Chargement avec erreurs de base de données

- **Batch** (10 tests) :
  - Chargement batch réussi
  - Gestion des erreurs batch
  - Chargement batch avec symboles multiples
  - Chargement batch avec données mixtes
  - Chargement batch avec erreurs partielles
  - Chargement batch avec transactions
  - Chargement batch avec rollback
  - Chargement batch avec commit
  - Chargement batch avec validation
  - Chargement batch avec métriques

### test_etl_pipeline.py

**13 tests** couvrant le pipeline ETL complet :

- **Initialisation** (2 tests) :
  - Initialisation avec composants valides
  - Gestion des erreurs d'initialisation

- **Exécution** (6 tests) :
  - Exécution réussie
  - Gestion des erreurs d'exécution
  - Exécution avec données vides
  - Exécution avec données partielles
  - Exécution avec erreurs de validation
  - Exécution avec erreurs de transformation

- **Batch** (5 tests) :
  - Exécution batch réussie
  - Gestion des erreurs batch
  - Exécution batch avec symboles multiples
  - Exécution batch avec données mixtes
  - Exécution batch avec métriques complètes

## 📈 Rapport de Couverture

Pour générer un rapport de couverture :

```bash
# Installer pytest-cov
pip install pytest-cov

# Exécuter avec couverture
python -m pytest --cov=src tests/ --cov-report=term

# Générer un rapport HTML
python -m pytest --cov=src tests/ --cov-report=html

# Ouvrir le rapport
open htmlcov/index.html
```

## 🏗️ Architecture ETL

Le projet utilise maintenant une architecture ETL modulaire pour le traitement des données OHLCV :

```
MarketCollector
  └── ETLPipeline (orchestration)
      ├── OHLCVExtractor (extraction)
      ├── OHLCVTransformer (transformation + validation)
      └── OHLCVLoader (chargement)
```

### Composants ETL

- **OHLCVExtractor** : Récupère les données depuis les exchanges avec gestion des erreurs et retry
- **OHLCVTransformer** : Valide, enrichit et normalise les données avec DataValidator0HCLV
- **OHLCVLoader** : Charge les données dans la base de données avec gestion des transactions
- **ETLPipeline** : Orchestre le pipeline complet avec suivi des performances et gestion des erreurs

### PipelineResult

Le pipeline utilise un objet `PipelineResult` pour suivre les métriques d'exécution :
- Temps d'exécution par étape
- Nombre de lignes traitées
- Statut de succès/échec
- Messages d'erreur détaillés
- Métadonnées de traitement

\*Mise à jour : 13/01/2026
*Ajout des tests pour DataValidator : 13/01/2026
*Ajout du pipeline ETL complet : 13/01/2026
*Total tests : 89 (15 + 22 + 9 + 12 + 18 + 13)
