# 🗃️ Documentation du Système de Sauvegarde Crypto Bot

## 📋 Introduction

Ce document explique comment utiliser le système de sauvegarde automatique du projet Crypto Bot. Le système permet de protéger les données OHLCV contre les pertes accidentelles et offre plusieurs méthodes de sauvegarde pour une redondance maximale.

## 🎯 Objectifs

- **Protection des données** : Prévenir la perte de données critiques
- **Restauration rapide** : Permettre une récupération facile en cas de problème
- **Automatisation** : Minimiser l'intervention manuelle
- **Redondance** : Plusieurs méthodes de sauvegarde pour la sécurité

## 📁 Structure des Sauvegardes

```
data/
└── backups/
    ├── full_backup_YYYYMMDD_HHMMSS.sql      # Sauvegarde SQL complète
    ├── csv_YYYYMMDD_HHMMSS/                # Sauvegarde CSV
    │   └── ohlcv.csv                      # Données complètes en CSV
    └── essential_backup_YYYYMMDD_HHMMSS.json # Données essentielles
```

## 🔧 Configuration

### Répertoires

- **Sauvegardes** : `data/backups/` (configurable dans `scripts/backup_db.py`)
- **Logs** : `logs/` (backup.log, restore.log, schedule_backups.log)

### Paramètres

- **Nombre de sauvegardes conservées** : 7 (derniers jours, configurable dans `scripts/backup_db.py`)
- **Fréquence** : Quotidienne + toutes les 6 heures
- **Méthodes** : 3 (SQL, CSV, JSON essentiel)

## 🚀 Utilisation

### 1. Sauvegarde Manuelle

Exécute une sauvegarde complète immédiatement :

```bash
python scripts/backup_db.py
```

**Sortie attendue** :

```
📁 Répertoire de sauvegarde: /chemin/vers/data/backups
🚀 Début de la sauvegarde complète
🔄 Sauvegarde SQL en cours: data/backups/full_backup_YYYYMMDD_HHMMSS.sql
✅ Sauvegarde SQL réussie
🔄 Sauvegarde CSV en cours: data/backups/csv_YYYYMMDD_HHMMSS
✅ Sauvegarde CSV réussie
🔄 Sauvegarde des données essentielles en cours
✅ Sauvegarde des données essentielles réussie
✅ Sauvegarde terminée: 3/3 méthodes réussies
```

### 2. Restauration

Restaure les données à partir de la dernière sauvegarde disponible :

```bash
python scripts/restore_db.py
```

**Processus** :

1. Liste les sauvegardes disponibles
2. Utilise la sauvegarde SQL la plus récente en priorité
3. Vérifie l'intégrité des données après restauration
4. Affiche un résumé complet

**Sortie attendue** :

```
🔧 Initialisation du système de restauration
📋 Sauvegardes disponibles:
  sql_dumps: 1 sauvegardes
    - full_backup_YYYYMMDD_HHMMSS.sql
  csv_backups: 1 sauvegardes
    - csv_YYYYMMDD_HHMMSS
🔄 Restauration SQL en cours depuis: full_backup_YYYYMMDD_HHMMSS.sql
✅ Restauration SQL réussie
🔍 Vérification de la restauration:
  Nombre d'enregistrements: 26324
  Symboles: ['ETH/USD', 'BTC/USDT', 'ETH/USDT', 'BTC/USD']
  Timeframes: ['1h', '4h', '1d', '6h']
✅ Restauration complète réussie
```

### 3. Planification Automatique

Lance un service en arrière-plan pour des sauvegardes régulières :

```bash
python scripts/schedule_backups.py
```

**Planification** :

- Sauvegarde quotidienne à minuit (00:00)
- Sauvegarde toutes les 6 heures
- Exécution immédiate au démarrage

**Pour exécuter en arrière-plan** :

```bash
nohup python scripts/schedule_backups.py > /dev/null 2>&1 &
```

## 📊 Méthodes de Sauvegarde

### 1. Sauvegarde SQL (pg_dump)

**Avantages** :

- Méthode la plus complète et fiable
- Préserve tous les schémas, index et contraintes
- Format compressé pour économiser de l'espace

**Fichier** : `full_backup_YYYYMMDD_HHMMSS.sql`

**Utilisation** : Prioritaire pour la restauration

### 2. Sauvegarde CSV

**Avantages** :

- Format universel et lisible
- Facile à importer dans d'autres outils
- Permet une analyse rapide des données

**Fichier** : `csv_YYYYMMDD_HHMMSS/ohlcv.csv`

**Utilisation** : Alternative si la sauvegarde SQL est corrompue

### 3. Sauvegarde Essentielle (JSON)

**Avantages** :

- Fichier compact avec les statistiques clés
- Rapide à générer et restaurer
- Utile pour une analyse rapide

**Fichier** : `essential_backup_YYYYMMDD_HHMMSS.json`

**Contenu** :

```json
[
  {
    "symbol": "BTC/USD",
    "timeframe": "1h",
    "count": 7700,
    "first_date": 1767866400000,
    "last_date": 1768294800000,
    "avg_price": 90740.34,
    "total_volume": 1113686.95
  },
  ...
]
```

## 🔍 Vérification et Maintenance

### Lister les sauvegardes

```bash
ls -la data/backups/
```

### Vérifier l'espace disque

```bash
du -sh data/backups/
```

### Nettoyage manuel

Le système conserve automatiquement les 7 dernières sauvegardes. Pour un nettoyage manuel :

```bash
# Supprimer les sauvegardes de plus de 30 jours
find data/backups/ -name "full_backup_*" -mtime +30 -delete
find data/backups/ -name "csv_*" -mtime +30 -exec rm -rf {} \;
find data/backups/ -name "essential_backup_*" -mtime +30 -delete
```

## ⚠️ Dépannage

### Problème : Échec de la sauvegarde SQL

**Cause possible** : `pg_dump` non installé ou permissions insuffisantes

**Solution** :

```bash
# Installer les outils PostgreSQL
sudo apt-get install postgresql-client  # Ubuntu/Debian
brew install libpq  # macOS

# Vérifier les permissions
chmod -R 755 data/backups/
```

### Problème : Fichiers de sauvegarde corrompus

**Solution** :

1. Vérifier l'espace disque : `df -h`
2. Tester la restauration depuis une autre sauvegarde
3. Relancer une sauvegarde manuelle

### Problème : Restauration incomplète

**Solution** :

1. Vérifier les logs : `cat logs/restore.log`
2. Essayer une autre méthode de sauvegarde
3. Contacter l'administrateur de la base de données

## 📈 Statistiques et Monitoring

### Vérifier les logs

```bash
# Logs des sauvegardes
tail -f logs/backup.log

# Logs des restaurations
tail -f logs/restore.log

# Logs de la planification
tail -f logs/schedule_backups.log
```

### Statistiques des sauvegardes

```bash
# Nombre de sauvegardes
ls data/backups/ | wc -l

# Taille totale
du -sh data/backups/

# Dernière sauvegarde
ls -t data/backups/ | head -5
```

## 🎓 Exemples d'Utilisation Avancée

### Sauvegarde et restauration spécifique

```bash
# Sauvegarder vers un emplacement personnalisé
python scripts/backup_db.py && cp -r data/backups /chemin/personnalisé/

# Restaurer depuis une sauvegarde spécifique
python -c "
from scripts.restore_db import DatabaseRestore
restore = DatabaseRestore()
restore.restore_from_sql('full_backup_20240115_120000.sql')
"
```

### Intégration avec des outils externes

```bash
# Sauvegarde vers Google Drive
gdrive upload --recursive data/backups/
```

---

\_Documentation mise à jour le 13/01/2026
