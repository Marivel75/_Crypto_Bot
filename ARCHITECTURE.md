# Architecture du Crypto Bot

Ce document présente l'architecture technique et le schéma de fonctionnement du Crypto Bot, un système de collecte et d'analyse de données de marché cryptographique.

## Table des matières

- [Vue d'ensemble](#vue-densemble)
- [Architecture globale](#architecture-globale)
- [Composants principaux](#composants-principaux)
  - [Point d'entrée (main.py)](#point-dentrée-mainpy)
  - [Schedulers (Planificateurs)](#schedulers-planificateurs)
  - [Collectors (Collecteurs)](#collectors-collecteurs)
  - [Exchange Clients](#exchange-clients)
  - [Pipeline ETL](#pipeline-etl)
  - [Base de données](#base-de-données)
- [Flux de données](#flux-de-données)
- [Diagramme d'architecture](#diagramme-darchitecture)
- [Configuration](#configuration)
- [Exemple d'exécution](#exemple-déxécution)
- [Bonnes pratiques](#bonnes-pratiques)

## Vue d'ensemble

Le Crypto Bot est une application Python conçue pour collecter, transformer et stocker des données de marché cryptographique depuis plusieurs exchanges. Le système est architecturé selon un modèle modulaire avec une séparation claire des responsabilités, permettant une grande flexibilité et extensibilité.

## Architecture globale

```
[Configuration] → [main.py] → [Schedulers] → [Collectors] → [Exchange Clients] → [Pipeline ETL] → [Base de données]
```

## Composants principaux

### Point d'entrée (main.py)

- **Rôle** : Point d'entrée principal de l'application
- **Fonctionnalités** :
  - Analyse des arguments de ligne de commande
  - Chargement de la configuration
  - Initialisation des schedulers
  - Gestion des modes d'exécution (unique ou planifié)
  - Orchestration globale du processus

- **Modes disponibles** :
  - Mode unique (`run_collection_once`) : Exécution immédiate
  - Mode planifié (`run_scheduled_collection`) : Exécution quotidienne

### Schedulers (Planificateurs)

Deux types de schedulers spécialisés :

#### OHLCVScheduler
- **Responsabilité** : Planification de la collecte des données historiques OHLCV
- **Fonctionnalités clés** :
  - Planification quotidienne à heure configurable
  - Gestion des threads pour opérations asynchrones
  - Support multi-exchanges
  - Normalisation des timeframes selon l'exchange
  - Journalisation détaillée et gestion des erreurs

#### TickerScheduler
- **Responsabilité** : Collecte en temps réel des données de ticker
- **Fonctionnalités clés** :
  - Collecte continue avec snapshots périodiques
  - Cache mémoire pour les données temps réel
  - Sauvegarde hybride (mémoire + base de données)
  - Affichage des prix en temps réel
  - Gestion du cycle de vie des collecteurs

### Collectors (Collecteurs)

#### OHLCVCollector
- **Rôle** : Récupération des données historiques OHLCV
- **Fonctionnalités** :
  - Création des clients d'exchange via ExchangeFactory
  - Intégration avec le pipeline ETL
  - Validation des données
  - Gestion des contextes (base de données et exchange)
  - Génération de rapports de collecte

#### TickerCollector
- **Rôle** : Récupération des données de ticker en temps réel
- **Fonctionnalités** :
  - Cache mémoire avec limite de taille
  - Normalisation des données selon l'exchange
  - Sauvegarde périodique des snapshots
  - Nettoyage automatique du cache
  - Récupération des prix actuels et historiques

### Exchange Clients

- **ExchangeFactory** : Usine de création des clients d'exchange
- **Clients supportés** : Binance, Kraken, Coinbase
- **Fonctionnalités** :
  - Implémentation des méthodes `fetch_ohlcv()` et `fetch_ticker()`
  - Gestion des spécificités de chaque exchange
  - Normalisation des formats de données
  - Gestion des erreurs de connexion

### Pipeline ETL

Le pipeline ETL (Extract, Transform, Load) est le cœur du traitement des données.

#### Extraction (OHLCVExtractor)
- **Responsabilité** : Récupération des données brutes
- **Fonctionnalités** :
  - Extraction depuis les APIs des exchanges
  - Conversion en DataFrames pandas
  - Gestion des erreurs de connexion
  - Support des extractions par lots

#### Transformation (OHLCVTransformer)
- **Responsabilité** : Nettoyage et enrichissement des données
- **Fonctionnalités** :
  - Validation avec DataValidator0HCLV
  - Ajout de métadonnées (symbol, timeframe, exchange)
  - Conversion des timestamps
  - Calculs d'enrichissement (amplitude, variation, etc.)
  - Normalisation des formats

#### Chargement (OHLCVLoader)
- **Responsabilité** : Sauvegarde des données transformées
- **Fonctionnalités** :
  - Insertion dans la base de données
  - Gestion des transactions avec context managers
  - Insertion par batches pour performance
  - Gestion des conflits et doublons
  - Vérification de l'intégrité des données

### Base de données

- **Double support** :
  - SQLite : Pour l'environnement de développement
  - PostgreSQL/Supabase : Pour la production

- **Gestion des connexions** :
  - Context managers pour une gestion sécurisée
  - Pool de connexions pour PostgreSQL
  - Transactions automatiques avec commit/rollback

- **Modèles de données** :
  - `OHLCV` : Données historiques OHLCV
  - `TickerSnapshot` : Snapshots de prix en temps réel

## Flux de données

### Flux OHLCV (données historiques)

```
1. main.py lance OHLCVScheduler
2. OHLCVScheduler planifie l'exécution quotidienne
3. À l'heure planifiée, création de OHLCVCollector
4. OHLCVCollector initialise le client d'exchange
5. Exécution du pipeline ETL :
   a. Extraction des données brutes depuis l'exchange
   b. Transformation et validation des données
   c. Chargement dans la base de données
6. Génération du rapport de collecte
7. Vérification de l'intégrité de la base de données
```

### Flux Ticker (données temps réel)

```
1. main.py lance TickerScheduler
2. TickerScheduler démarre la collecte continue
3. Création de TickerCollector pour chaque exchange
4. Collecte périodique des tickers :
   a. Récupération depuis l'exchange
   b. Normalisation des données
   c. Ajout au cache mémoire
   d. Sauvegarde périodique des snapshots
5. Affichage des prix en temps réel
6. Nettoyage automatique du cache
```

## Diagramme d'architecture

```
┌───────────────────────────────────────────────────────────────┐
│                        Crypto Bot Application                 │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────┐    ┌─────────────┐    ┌───────────────────┐  │
│  │  main.py    │───▶│ Schedulers  │───▶│   Collectors     │  │
│  └─────────────┘    └─────────────┘    └───────────────────┘  │
│          ▲                  │                    │             │
│          │                  │                    │             │
│  ┌───────┴───────┐  ┌───────▼───────┐  ┌───────▼───────┐     │
│  │ Configuration │  │ Exchange      │  │ Pipeline ETL │     │
│  │ (YAML/CLI)    │  │ Clients       │  │              │     │
│  └───────────────┘  └───────┬───────┘  └───────┬───────┘     │
│                            │                  │             │
│                    ┌───────▼───────┐  ┌───────▼───────┐     │
│                    │  Exchange    │  │  Base de      │     │
│                    │  APIs         │  │  données      │     │
│                    │  (Binance,    │  │  (SQLite/     │     │
│                    │   Kraken,     │  │   Supabase)   │     │
│                    │   Coinbase)   │  └───────────────┘     │
│                    └───────────────┘                      │
│                                                           │
└───────────────────────────────────────────────────────────────┘
```

## Configuration

### Fichiers de configuration

- `config/config.yaml` : Configuration principale
- `config/settings.py` : Paramètres et constantes
- Variables d'environnement : Pour les secrets et paramètres sensibles

### Paramètres clés

- **Exchanges** : Liste des exchanges à utiliser (binance, kraken, coinbase)
- **Paires** : Liste des paires de trading (ex: BTC/USDT, ETH/USDT)
- **Timeframes** : Timeframes pour les données OHLCV (1h, 4h, 1d, etc.)
- **Planification** : Heure de collecte quotidienne
- **Ticker** : Intervalle de snapshot, taille du cache, durée d'exécution
- **Base de données** : URL de connexion, paramètres de pool

## Exemple d'exécution

### Mode planifié (production)

```bash
python main.py --schedule --exchanges binance kraken --env production
```

1. Chargement de la configuration de production
2. Initialisation des schedulers OHLCV et Ticker
3. Planification de la collecte OHLCV quotidienne à 09:00
4. Démarrage de la collecte Ticker en temps réel
5. Exécution immédiate de la première collecte OHLCV
6. Collecte continue des tickers avec snapshots toutes les 5 minutes
7. Vérification périodique de l'intégrité de la base de données

### Mode unique (développement)

```bash
python main.py --exchanges binance --ticker --runtime 30
```

1. Chargement de la configuration de développement
2. Exécution immédiate de la collecte OHLCV
3. Démarrage de la collecte Ticker pour 30 minutes
4. Sauvegarde des snapshots toutes les 5 minutes
5. Arrêt automatique après 30 minutes
6. Vérification finale de la base de données

## Bonnes pratiques

### Développement

- Utiliser le mode développement avec SQLite pour les tests
- Exécuter les tests unitaires avant les déploiements
- Utiliser les scripts de vérification de base de données
- Monitorer les logs pour détecter les problèmes

### Production

- Toujours utiliser l'environnement production avec PostgreSQL/Supabase
- Configurer une surveillance des processus
- Mettre en place des alertes pour les échecs de collecte
- Effectuer des sauvegardes régulières de la base de données
- Monitorer les performances et l'utilisation des ressources

### Extensibilité

- Pour ajouter un nouvel exchange :
  1. Créer un nouveau client dans `services/exchanges_api/`
  2. Mettre à jour `ExchangeFactory`
  3. Ajouter la normalisation dans les collectors
  4. Tester avec le mode développement

- Pour ajouter un nouveau type de données :
  1. Créer un nouveau collector
  2. Développer un pipeline ETL spécifique
  3. Étendre les modèles de base de données
  4. Intégrer avec les schedulers existants

## Conclusion

L'architecture du Crypto Bot est conçue pour être robuste, extensible et maintenable. La séparation claire des responsabilités entre les différents composants permet une évolution facile du système tout en assurant une collecte fiable des données de marché cryptographique.

La combinaison de la collecte historique (OHLCV) et temps réel (Ticker) offre une vue complète du marché, tandis que le support de plusieurs exchanges et bases de données assure une grande flexibilité d'utilisation.

Le système de configuration centralisé et les nombreux paramètres ajustables permettent une adaptation fine aux besoins spécifiques de chaque utilisation, que ce soit pour du développement, des tests ou une production à grande échelle.