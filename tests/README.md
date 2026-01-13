# 🧪 Tests Crypto Bot

Ce répertoire contient tous les tests pour le projet Crypto Bot.

## 📁 Structure

```
tests/
├── test_market_collector.py  # Tests unitaires pour MarketCollector
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

### 2. Utilisation du script de test

```bash
# Aide
python scripts/run_tests.py --help

# Exécuter les tests unitaires
python scripts/run_tests.py --type unit --verbose

# Exécuter tous les tests avec couverture
python scripts/run_tests.py --coverage

# Générer un rapport HTML
python scripts/run_tests.py --coverage --report
```

## 📊 Tests Actuels

### test_market_collector.py

**14 tests** couvrant :

- **Initialisation** (8 tests) :
  - Validation des paramètres d'entrée
  - Gestion des exchanges (Binance, Kraken, Coinbase)
  - Gestion des erreurs de configuration

- **Validation** (3 tests) :
  - Validation des paires et timeframes
  - Gestion des valeurs vides et invalides

- **Fonctionnement** (3 tests) :
  - Test de `fetch_and_store` avec succès
  - Gestion des exceptions
  - Gestion des doublons

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

*Mise à jour : 13/01/2026