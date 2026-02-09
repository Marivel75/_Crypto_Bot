# Gestion des Environnements de Base de Données

Ce document explique comment utiliser le système d'environnements pour séparer les données de test et de production.

## 🏗️ Architecture

Le système utilise deux bases de données distinctes :

```
data/
├── production/
│   └── crypto_data.db          # Base de production (collecte quotidienne)
└── testing/
    └── crypto_data_test.db     # Base de test (isolée)
```

## 🚀 Utilisation

### 1. Initialisation

```bash
# Créer les deux environnements
python scripts/manage_environments.py create-test
python scripts/manage_environments.py create-prod

# Vérifier l'état
python scripts/manage_environments.py info
```

### 2. Exécution des Tests Isolés

```bash
# Exécuter les tests sans affecter la production
python scripts/run_isolated_tests.py test

# Tests avec couverture
python scripts/run_isolated_tests.py coverage

# Tests unitaires uniquement
python scripts/run_isolated_tests.py unit
```

### 3. Collecte de Données

```bash
# Mode production (par défaut)
python main.py --ticker --exchanges binance kraken coinbase

# Forcer explicitement le mode production
export CRYPTO_BOT_ENV=production
python main.py --schedule

# Mode test (affecte seulement la base de test)
export CRYPTO_BOT_ENV=testing
python main.py --ticker
```

### 4. Gestion des Bases

```bash
# Réinitialiser uniquement la base de test
python scripts/reset_db.py --env testing

# Réinitialiser uniquement la base de production
python scripts/reset_db.py --env production

# Réinitialiser toutes les bases
python scripts/reset_db.py --env all
# ou
python scripts/reset_db.py --all
```

## 🔧 Configuration

### Variables d'Environnement

| Variable | Valeur | Effet |
|----------|--------|--------|
| `CRYPTO_BOT_ENV` | `production` | Force la base de production |
| `CRYPTO_BOT_ENV` | `testing` | Force la base de test |
| `CRYPTO_BOT_TEST` | `true` | Alternative pour forcer le mode test |

### Détection Automatique

1. **Variable d'environnement** `CRYPTO_BOT_ENV`
2. **Variable alternative** `CRYPTO_BOT_TEST`
3. **Par défaut** : `production`

## 📊 Vérification

### État des Environnements

```python
from src.services.db_environment import db_env

# Informations complètes
info = db_env.get_database_info()
print(f"Environnement actuel: {info['current_environment']}")
print(f"URL actuelle: {info['current_url']}")

# Lister les bases existantes
databases = db_env.list_databases()
for env, db_info in databases.items():
    exists = "✅" if db_info['exists'] else "❌"
    print(f"{env}: {exists} {db_info['size_formatted']}")
```

### Scripts de Monitoring

```bash
# Informations sur les environnements
python scripts/manage_environments.py info

# Vérification de la base de test
python scripts/check_db.py  # Utilise l'environnement actuel

# Forcer la vérification de la base de test
CRYPTO_BOT_ENV=testing python scripts/check_db.py
```

## 🎯 Bonnes Pratiques

### Pour le Développement

1. **Toujours utiliser les tests isolés** :
   ```bash
   python scripts/run_isolated_tests.py test
   ```

2. **Vérifier l'environnement avant la collecte** :
   ```bash
   python scripts/manage_environments.py info
   ```

3. **Nettoyer régulièrement la base de test** :
   ```bash
   python scripts/manage_environments.py clean-test
   ```

### Pour la Production

1. **S'assurer d'être en mode production** :
   ```bash
   export CRYPTO_BOT_ENV=production
   python main.py --schedule
   ```

2. **Sauvegarder régulièrement la base de production** :
   ```bash
   python scripts/backup_db.py
   ```

3. **Ne jamais exécuter de tests sur la base de production**

## 🔄 Migration

### Depuis une base unique

Si vous avez actuellement une seule base de données :

1. **Créer les environnements** :
   ```bash
   python scripts/manage_environments.py create-test
   python scripts/manage_environments.py create-prod
   ```

2. **Déplacer la base existante** vers production :
   ```bash
   mv data/processed/crypto_data.db data/production/crypto_data.db
   ```

3. **Vérifier** :
   ```bash
   python scripts/manage_environments.py info
   ```

### Migration Automatique

```bash
# Script de migration (à créer)
python scripts/migrate_to_environments.py
```

## 🚨 Sécurité

- **Isolation** : Les tests ne peuvent jamais affecter la production
- **Traçabilité** : Logs clairs indiquant quelle base est utilisée
- **Contrôle** : Variables d'environnement pour un contrôle explicite
- **Vérification** : Scripts pour vérifier l'état des environnements

## 📈 Avantages

✅ **Sécurité** : Protection complète des données de production  
✅ **Flexibilité** : Tests rapides sans nettoyage manuel  
✅ **Clarté** : Séparation nette des environnements  
✅ **Automatisation** : Scripts pour toutes les opérations  
✅ **Traçabilité** : Logs détaillés des opérations