# Rapport final de projet — Crypto Bot

**Auteurs** : Jules Willard — Mikaël Jayet  
**Formation** : DataScientest — Cursus Data Engineer / Data Scientist  
**Période** : Octobre 2025 – Mai 2026  
**Soutenance** : Juin 2026

---

# SYNTHÈSE

## Contexte et ambition

Dans le cadre de notre formation DataScientest, nous avons conduit de bout en bout un projet fil rouge autour des marchés crypto : de la définition du cahier des charges jusqu'au déploiement en production. L'objectif fixé par le sujet était de créer *"un bot de trading basé sur un modèle de Machine Learning qui investira sur les marchés crypto"* — en montrant notre capacité à définir un cahier des charges, à implémenter une solution technique complète et à assurer sa mise en production avec monitoring.

Nous avons structuré notre réponse autour d'une plateforme intégrée baptisée **Crypto Bot**, adressant trois personas identifiés en phase de discovery : Noah (trader indépendant), Sarah (journaliste financière) et Aleksandar (investisseur débutant).

## Ce que nous avons livré

En sept mois (janvier à mai 2026), nous avons intégralement construit, livré et déployé la plateforme. Elle couvre l'ensemble du pipeline, de la collecte brute jusqu'à l'interface utilisateur :

- **Pipeline ETL** multi-exchange (Binance, Kraken, Coinbase) avec bougies OHLCV, tickers, données CoinGecko et actualités RSS
- **API REST FastAPI** — 30+ endpoints couvrant toutes les fonctionnalités
- **Dashboard Streamlit** — 6 pages : chandelier, Market Overview, signaux BUY/SELL/HOLD, veille NLP, backtesting ML, paper trading
- **Moteur ML** — walk-forward backtesting, XGBoost/Random Forest/Régression Logistique, suivi MLflow
- **Paper trading temps réel** — WebSocket Binance, portefeuilles fictifs, P&L live
- **Infrastructure production** — Docker, Nginx, Ansible, Prometheus + Grafana 4 dashboards, domaine `monpetitbet.fr`

## Adéquation avec le sujet

La quasi-totalité des livrables attendus a été produite. Les principaux ajustements techniques portent sur des choix délibérés : MongoDB remplacé par PostgreSQL (suffisant), BeautifulSoup par des flux RSS (plus fiable). L'apprentissage par renforcement, envisagé dans le cadrage pour automatiser les ordres, n'a pas été implémenté — le paper trading constitue la première étape vers cet objectif.

## Points forts

La plateforme se distingue par la complétude de sa chaîne de valeur : 
- collecte automatisée jusqu'aux signaux actionnables, tout est connecté en temps réel
- adoption dès le premier jour d'une CI/CD, des branches protégées et des tests automatiques — une rigueur d'ingénierie qui a évité la dette technique
- paper trading avec WebSocket Binance et infrastructure Ansible/Grafana 

## Perspectives

Apprentissage par renforcement pour automatiser les décisions de trading, données on-chain, authentification JWT, activation SSL et mise en production complète sur `monpetitbet.fr`.

---
---

# RAPPORT COMPLET

---

## 1. Contexte du projet

### 1.1 Sujet DataScientest

Le sujet **Crypto / Finance** nous demande de *"travailler en équipe pour faire ressortir de la valeur ajoutée, montrer les compétences pour définir un cahier des charges, une implémentation technique, et assurer la mise en production avec monitoring"*.

Le projet est structuré en trois grandes étapes pédagogiques :

| Étape | Description | Livrables attendus |
|---|---|---|
| **1 — Cahier des charges**
| **2 — Conception** 
| **3 — Lancement**

### 1.2 Objectif central

> *"Créer un bot de trading basé sur un modèle de Machine Learning qui investira sur les marchés crypto."*

Nous avons interprété cet objectif de manière large : nous avons construit une **plateforme complète d'aide à la décision**, allant de la collecte de données jusqu'à la simulation de trading, avec toute la chaîne analytique et ML au milieu.

### 1.3 Planning initial

| Date | Étape |
|---|---|
| 03/09/2025 | Kick-off |
| Septembre 2025 | Discovery et préparation projet |
| Octobre 2025 | Cahier des charges |
| Novembre 2025 | MVP |
| Décembre 2025 | Schéma BDD et pipeline |
| Février 2026 | Intégration des algorithmes ML/DL |
| Avril 2026 | Création de l'API |
| Mai 2026 | Déploiement automatisé |
| Juin 2026 | Rapport et Soutenance |

---

## 2. Phase Discovery

### 2.1 Analyse du secteur

Notre phase de discovery nous a conduit à cartographier le secteur des crypto-monnaies selon plusieurs dimensions.

**Le marché en chiffres :**

| Exchange | Volume journalier médian | Cryptos listées |
|---|---|---|
| Binance | 16,3 Mds $ | 517 |
| Bybit | 4,2 Mds $ | 733 |
| Crypto.com | 3,6 Mds $ | 419 |
| OKX | 2,6 Mds $ | 343 |
| Coinbase | 2,5 Mds $ | 298 |

Binance représente à lui seul plus de 40 % des volumes mondiaux sur les exchanges centralisés. Nous avons retenu Binance, Kraken et Coinbase comme sources primaires — les trois exchanges disposant à la fois d'une API ccxt robuste et d'une liquidité suffisante pour des données OHLCV fiables.

**Popularité des actifs :** Bitcoin est identifié par 90 % des répondants, Ethereum par 50 %, ce qui justifie notre focus sur les paires BTC/USDT et ETH/USDT comme paires de référence.

### 2.2 Personas utilisateurs

Nous avons identifié trois profils cibles à partir de notre travail de discovery :

**Noah, 32 ans — Trader indépendant**  
Utilise des perpétuels sur DEX (Hyperliquid). Suit le marché quotidiennement, cherche une vue unifiée graphiques/actualités/signaux avec transparence sur les critères d'alerte. Son parcours idéal : signal → plan de trade → lien DEX. Il a besoin que la plateforme lui apprenne *pourquoi* un signal a été déclenché.

**Sarah, 30 ans — Journaliste financière**  
Double formation généraliste et économie-finance, sans compétence technique. Cherche une veille fiable, filtrage du bruit, détection des fake news, alertes réglementaires, résumés automatiques. L'outil doit lui permettre de produire des articles précis et de développer rapidement une expertise.

**Aleksandar — Investisseur débutant**  
Veut apprendre à investir en crypto sans risque réel, suivre un portefeuille fictif et comprendre les mécanismes des marchés. La pédagogie et la simplicité priment.

### 2.3 Benchmark concurrentiel

Nous avons identifié et analysé une dizaine de solutions existantes :

| Solution | Positionnement | Fonctionnalités clés | API |
|---|---|---|---|
| **Altfins** | Trading analytics | Signaux techniques, screener | Oui |
| **CryptoQuant** | Analytics on-chain | Métriques on-chain, flux exchange | Oui |
| **3commas.io** | Trading bots | Paper trading, bots automatisés | Oui |
| **Santiment** | Data & sentiment | Sentiment de marché, données sociales | Oui |
| **Glassnode** | Analytics on-chain | Wallets, transactions, DeFi | Oui |
| **Tickeron** | Trading généraliste | Signaux, paper trading, crypto + finance tradi | Oui |
| **Altrady** | Trading multibourses | Data viz, paper trading, multi-exchange | Oui |
| **Quantify Crypto** | Data viz | Heatmaps, analytics | Oui |
| **Dune Analytics** | Data on-chain | SQL-like sur données blockchain | Oui |

**Enseignements du benchmark** : Les solutions existantes sont soit trop coûteuses pour un usage individuel, soit trop spécialisées (uniquement on-chain, uniquement signaux techniques, ou uniquement trading automatisé). Aucune ne combine dans une même plateforme open-source la collecte ETL, l'analyse NLP de news, les signaux techniques, le backtesting ML et le paper trading. C'est notre angle de différenciation.

### 2.4 Cadre réglementaire identifié

Notre veille réglementaire a identifié les textes et organismes clés encadrant notre activité :

- **MiCA** (Markets in Crypto-Assets) : règlement européen entré en application en 2024, encadrant les émetteurs de crypto-actifs et les prestataires de services
- **AMF** (Autorité des Marchés Financiers) : régulateur français, compétent sur les PSAN (Prestataires de Services sur Actifs Numériques)
- **ESMA** (European Securities and Markets Authority) : coordination réglementaire européenne
- **SEC** (Securities and Exchange Commission) : autorité américaine, influence les cours mondiaux par ses décisions (ETF, enforcement)
- **MiFID 2** : directive européenne sur les marchés financiers, applicable à certains instruments crypto
- **RGPD** : applicable à notre gestion des données utilisateurs (emails d'abonnés, adresses IP)

### 2.5 KPIs sectoriels identifiés

| KPI | Acronyme | Définition |
|---|---|---|
| Market Capitalization | Market Cap | Prix courant × quantité en circulation |
| Total Value Locked | TVL | Valeur totale détenue sur un réseau DeFi — indicateur de vitalité |
| Volume journalier | Vol. | Volume de transactions sur 24h — indicateur de liquidité |
| Fear & Greed Index | F&G | Indice de sentiment de marché (0-100) |
| RSI, MACD, BB ... | — | Indicateurs techniques classiques |
| Sharpe ratio | — | Rendement ajusté du risque (évaluation stratégies) |

---

## 3. Équipe et organisation

### 3.1 Répartition des rôles

Notre cadrage estimait **70 jours de travail total** (40 DE + 30 DS) pour un budget théorique de **32 000 €** à 400 €/j TJM, auxquels s'ajoutent 4 000 € de coûts annexes (cloud, APIs, maintenance).

### 3.2 Méthode de travail

Nous avons adopté un workflow Git structuré dès le premier jour :

- **Branches protégées** : `main` (production) et `dev` (intégration)
- **Feature branches** : une branche par fonctionnalité, mergée via Pull Request
- **70+ Pull Requests** ouvertes et mergées sur la durée du projet
- **CI/CD** via GitHub Actions : tests automatiques sur chaque PR avant merge
- **Convention de commits** : messages descriptifs en français, avec préfixes (`feat`, `fix`, `chore`)
- **Documentation** : README, docs/ et diagrammes UML maintenus en parallèle du code

---

## 4. Roadmap prévue et réalisée

Le sujet DataScientest définissait une roadmap technique en 10 sprints. Voici notre réalisation effective :

| Sprint | Thème prévu | Statut | Réalisation effective |
|---|---|---|---|
| 1 | DevOps & CI/CD | ✅ | GitHub Actions, branches protégées, Docker (livré dès jan 2026) |
| 2 | Collecte APIs (CoinGecko, news…) | ✅ | ccxt multi-exchange + CoinGecko + RSS feedparser |
| 3 | Structuration BDD | ✅ | SQLAlchemy + SQLite/PostgreSQL, 8 domaines de tables |
| 4 | ETL & qualité données | ✅ | Pipeline Extract→Validate→Transform→Load, DataValidator |
| 5 | Analytics & KPIs | ✅ | Indicateurs techniques (RSI, MACD, BB, SMA), Fear & Greed, signaux |
| 6 | ML & Reinforcement Learning | ⚠️ | ML supervisé livré (XGBoost, RF, LR) ; RL non implémenté |
| 7 | Dashboard v1 | ✅ | 6 pages Streamlit avec Plotly |
| 8 | Tests & CI/CD finalisation | ✅ | pytest, couverture src + api |
| 9 | Déploiement & monitoring | ✅ | Ansible, Nginx, Prometheus, Grafana (4 dashboards) |
| 10 | Alertes & chatbot (optionnel) | ⚠️ | Alertes email livrées ; chatbot LLM non implémenté |

**Note sur le reinforcement learning** : le sujet envisageait Monte Carlo, SARSA et Q-learning pour automatiser les décisions BUY/SELL/HOLD. Le RL reste un axe d'évolution identifié.

---

## 5. Architecture technique

### 5.1 Vue d'ensemble

```
┌─────────────────────────────────────────────────────────┐
│                    Sources de données                    │
│  Binance · Kraken · Coinbase · CoinGecko · RSS · WebSocket│
└──────────────────────┬──────────────────────────────────┘
                       │ ccxt / feedparser / websockets
┌──────────────────────▼──────────────────────────────────┐
│               Pipeline ETL (src/collectors + etl/)       │
│  Extract → Validate → Transform → Load                   │
└──────────────────────┬──────────────────────────────────┘
                       │ SQLAlchemy ORM
┌──────────────────────▼──────────────────────────────────┐
│           Base de données (SQLite / PostgreSQL)          │
│  ohlcv · ticker · market_data · news · paper_trading    │
│  alert_subscribers                                       │
└──────────┬───────────────────────────────────┬──────────┘
           │                                   │
┌──────────▼──────────┐             ┌──────────▼──────────┐
│    API FastAPI       │             │   ML Pipeline        │
│    (api/)            │             │   (src/ml/)          │
│  30+ endpoints       │             │  Features · Models   │
│  Pydantic schemas    │             │  Walk-forward · MLflow│
└──────────┬──────────┘             └─────────────────────┘
           │ HTTP / WebSocket
┌──────────▼──────────────────────────────────────────────┐
│              Frontend Streamlit (frontend/)              │
│  Dashboard · Market Overview · Signaux · Veille          │
│  ML Backtesting · Paper Trading                          │
└─────────────────────────────────────────────────────────┘
```

### 5.2 Stack technique : prévue vs retenue

| Couche | Stack envisagée (cadrage) | Stack retenue | Justification |
|---|---|---|---|
| Collecte | requests, BeautifulSoup, python-binance | **ccxt, feedparser** | ccxt : multi-exchange unifié ; RSS : plus fiable que le scraping HTML |
| Sentiment/NLP | scikit-learn TF-IDF | **scikit-learn TF-IDF + vaderSentiment** | Conforme + ajout VADER pour scoring continu |
| Stockage | PostgreSQL + MongoDB | **SQLAlchemy + SQLite/PostgreSQL** | MongoDB non nécessaire ; PostgreSQL couvre tous les besoins |
| API | FastAPI + Pydantic | **FastAPI + Pydantic v2 + uvicorn** | Conforme |
| Frontend | Streamlit ou Shiny | **Streamlit + Plotly** | Streamlit retenu (maturité, communauté, intégration Python) |
| ML | scikit-learn, TensorFlow/PyTorch | **scikit-learn + XGBoost** | TF/PyTorch non justifiés sur notre volume de données |
| RL | Monte Carlo, SARSA, Q-learning | **Non implémenté** | Complexité vs données disponibles ; paper trading privilégié |
| Experiment tracking | MLflow | **MLflow** | Conforme |
| Infra | Docker, GitHub Actions | **Docker + GitHub Actions + Ansible + Nginx + Prometheus + Grafana** | Au-delà du cadrage initial |

### 5.3 APIs retenues

Parmi les APIs étudiées en phase de discovery, voici celles effectivement intégrées :

| API | Usage | Gratuit |
|---|---|---|
| **Binance** (via ccxt) | OHLCV, ticker, WebSocket miniTicker | Oui |
| **Kraken** (via ccxt) | OHLCV | Oui |
| **Coinbase** (via ccxt) | OHLCV | Oui |
| **CoinGecko** | Fear & Greed, market cap, top movers | Oui (limité) |
| **RSS multi-sources** | Actualités crypto (feedparser) | Oui |

Les APIs PhoenixNews, Cryptorank et CoinGecko Premium (identifiées comme pertinentes en discovery) n'ont pas été intégrées car payantes. L'axe de diversification des sources news reste un axe d'évolution.

### 5.4 Base de données

Notre schéma comporte **8 domaines de tables** :

| Domaine | Tables | Description |
|---|---|---|
| OHLCV | `ohlcv` | Bougies multi-exchange, multi-timeframe |
| Ticker | `ticker_snapshots` | Snapshots périodiques prix/volume |
| Market Data | `global_market_snapshot`, `top_crypto_snapshot`, `crypto_detail_snapshot` | Données CoinGecko |
| News & NLP | `news_articles` | Articles enrichis (VADER, TF-IDF, entités, topics) |
| Alerting | `alert_subscribers` | Emails abonnés |
| Paper Trading | `paper_portfolios`, `paper_trades` | Portefeuilles et ordres fictifs |

Le dual-support SQLite (dev) / PostgreSQL (prod) est géré via `CRYPTO_BOT_DB_URL` dans le Makefile.

---

## 6. Fonctionnalités réalisées

### 6.1 Pipeline de collecte de données

**Architecture ETL modulaire** (`src/collectors/`, `src/etl/`) :

- `Extractor` : appel API via ccxt avec gestion des rate limits
- `Transformer` : normalisation des timestamps (UTC), déduplication, validation des types, calcul d'indicateurs de base
- `Loader` : insertion incrémentale (upsert par clé composite exchange/symbol/timeframe/timestamp)
- `DataValidator` : contrôles de cohérence OHLCV (high ≥ low, volumes positifs, timestamps valides)

**Sources et modes de collecte** :

| Source | Données | Mode |
|---|---|---|
| Binance, Kraken, Coinbase | OHLCV | Incrémental, planifié 09h00, historique 1000 bougies |
| Binance WebSocket | Prix live | Continu (daemon thread) |
| CoinGecko | Fear & Greed, market cap global, top movers | À la demande via API |
| RSS (multi-sources) | Actualités crypto | Une passe ou boucle 60 min |

### 6.2 API REST

Notre API FastAPI expose **30+ endpoints** en 7 routeurs :

| Routeur | Endpoints principaux |
|---|---|
| `ohlcv` | Bougies, liste des symboles disponibles |
| `market` | Fear & Greed, market cap global, top movers, historique |
| `signals` | Score composite RSI/MACD/BB/SMA par symbole |
| `news` | Articles filtrables (source, sentiment, topic, symbole) |
| `ml` | Backtest walk-forward, features ML |
| `alerts` | Subscribe/unsubscribe email, liste abonnés |
| `paper_trading` | Portefeuilles, ordres BUY/SELL, P&L, prix live |

### 6.3 Frontend Streamlit — 6 pages

| Page | Persona principal | Contenu |
|---|---|---|
| **Dashboard** | Noah | Chandelier Plotly + SMA/EMA/BB superposables |
| **Market Overview** | Sarah, Aleksandar | Fear & Greed, market cap, top movers, corrélations |
| **Signaux** | Noah | Score BUY/SELL/HOLD par actif (RSI/MACD/BB/SMA) |
| **Veille** | Sarah | News RSS enrichies NLP, filtres multi-critères, abonnement alertes |
| **ML & Backtesting** | Noah, DS | Walk-forward, Sharpe, PnL, drawdown, vs buy-and-hold |
| **Paper Trading** | Aleksandar, Noah | Portefeuilles fictifs, ordres live WebSocket, courbe capital |

### 6.4 Machine Learning et Backtesting

**Feature engineering** : le `FeatureBuilder` génère automatiquement à partir des bougies OHLCV :
SMA 7/14/21/50, EMA 7/14/21, RSI 14, MACD signal/histogramme, Bollinger Bands, volume relatif, log-returns sur 1/3/5 jours, label J+1.

**Walk-forward backtesting** : méthode rigoureuse anti-data-leakage avec purge et embargo entre fenêtres d'entraînement (défaut 60 jours) et de test (défaut 15 jours). Chaque fold est évalué indépendamment.

**Modèles évalués** :

| Modèle | Type | Rôle |
|---|---|---|
| Dummy Classifier | Baseline probabiliste | Référence plancher |
| Régression Logistique | Baseline linéaire | Référence interprétable |
| Random Forest | Ensemble bagging | Robustesse |
| **XGBoost** | Gradient boosting | Modèle principal |

**Métriques** : Sharpe ratio annualisé, win rate, PnL total (log-returns), max drawdown, accuracy directionnelle, profit factor, comparaison vs buy-and-hold.

Chaque backtest est automatiquement loggé dans MLflow avec paramètres, métriques et artifacts.

### 6.5 NLP & Text Mining

| Analyse | Méthode | Exemple |
|---|---|---|
| Sentiment | VADER (compound -1 → +1) | `score: 0.72` → positif |
| Mots-clés | TF-IDF unigrammes + bigrammes | `["etf approved", "sec", "rally"]` |
| Entités | Regex + dictionnaire | `{"crypto_symbols": ["BTC","ETH"], "exchanges": ["binance"]}` |
| Topics | Classification par mots-clés | `["regulation", "adoption"]` |

8 topics : `regulation`, `hack_security`, `adoption`, `defi`, `nft`, `macro`, `price_action`, `general`.

### 6.6 Système d'alertes email

Notifications SMTP (Gmail) pour les événements clés :
- Démarrage et fin de collecte (avec résumé ETL + état de la base)
- Confirmation d'inscription (avec les 5 dernières actualités)
- Confirmation de désabonnement
- Alerte erreur critique pipeline

### 6.7 Paper Trading

Composants :
- `PaperTrader` : moteur métier (portefeuilles, P&L, gestion positions)
- `LivePriceCache` : singleton thread-safe alimenté par WebSocket Binance
- 8 endpoints REST dédiés
- Rafraîchissement automatique toutes les 5s (streamlit-autorefresh)

---

## 7. Infrastructure et déploiement

### 7.1 Environnement local

```bash
make setup      # Installation multi-OS (setup.sh : macOS / Debian / RedHat / Arch / Alpine)
make run        # API + Streamlit (SQLite)
make run-all    # API + MLflow + Streamlit
make docker     # Stack complète Docker
```

### 7.2 Docker Compose

Stack Docker : API (FastAPI 8000), Frontend (Streamlit 8501), MLflow (5001 avec `--allowed-hosts "*"`).

### 7.3 Infrastructure production

Nous avons conçu et versionné une infrastructure de déploiement production complète (`_v1/infra/`) :

- **Ansible** : provision VPS vierge (packages, swap 2G, UFW, Fail2Ban), déploiement via rsync, sauvegardes quotidiennes, SSL Let's Encrypt
- **Nginx** : reverse proxy avec rate limiting (30 req/s API), support WebSocket Streamlit, headers de sécurité
- **Prometheus + Grafana** : 4 dashboards de monitoring — API overview, business metrics, PostgreSQL, ressources système — scraping toutes les 15s
- **Services prod** : TimescaleDB, MinIO (artifacts MLflow), API, Frontend, ETL worker, ML worker, Prometheus, Grafana
- **Domaine** : `monpetitbet.fr`

### 7.4 CI/CD

GitHub Actions déclenche les tests sur chaque Pull Request. Nous avons protégé les branches `main` et `dev` contre les pushs directs dès février 2026.

---

## 8. Qualité et tests

Notre suite de tests couvre :
- **Tests API** (`test_api.py`) : endpoints FastAPI via `httpx.AsyncClient`, codes HTTP, schémas Pydantic
- **Tests paper trading** (`test_paper_trading.py`) : moteur `PaperTrader`, ordres BUY/SELL, calcul P&L, cas limites

Robustesse du pipeline : rate limiting exchanges (backoff), collecte incrémentale, fallback WebSocket → OHLCV, alertes non bloquantes.

```bash
make test-cov   # pytest --cov=src --cov=api --cov-report=term-missing
```

---

## 9. Adéquation avec le sujet DataScientest

### 9.1 Livrables produits

| Livrable attendu | Statut | Forme |
|---|---|---|
| Guide d'entretien / Discovery | ✅ | Glossaire secteur, benchmark, personas (XLSX + cadrage) |
| Experience Map | ✅ | 3 personas détaillés (Noah, Sarah, Aleksandar) |
| Analyse SWOT | ✅ | SWOT sectoriel crypto |
| Veille technologique | ✅ | Benchmark 10 concurrents, APIs étudiées, réglementation |
| Schéma BDD | ✅ | `docs/database_schema.md` |
| Pipeline ETL | ✅ | `src/etl/` — Extract → Validate → Transform → Load |
| MVP fonctionnel | ✅ | 6 pages Streamlit + API REST + ML |
| Roadmap technique | ✅ | 10 sprints documentés |
| Tests | ✅ | pytest, CI GitHub Actions |
| Déploiement & monitoring | ✅ | Ansible, Docker, Nginx, Prometheus, Grafana |
| Rapport final | ✅ | Ce document |

### 9.2 Fonctionnalités du sujet

| Feature cadrage | Statut | Notes |
|---|---|---|
| Veille actu & marché | ✅ Livré | RSS + VADER + NLP, au-delà du scope |
| Suivi des cours temps réel | ✅ Livré | WebSocket Binance, non prévu initialement |
| Dashboard | ✅ Livré | Chandelier interactif + indicateurs |
| Analytics | ✅ Livré | Market Overview (Fear & Greed, corrélations…) |
| ML supervisé | ✅ Livré | Random Forest, XGBoost, walk-forward |
| ML non supervisé | ⚠️ Partiel | Pas de clustering explicite en production |
| ML par renforcement | ❌ Non livré | Paper trading privilégié comme étape intermédiaire |
| Paper trading | ✅ Livré et élargi | WebSocket live, métriques financières complètes |
| Monitoring infra | ✅ Livré | Prometheus + Grafana |
| PostgreSQL | ✅ Livré | + migration SQLite→PostgreSQL |
| MongoDB | ❌ Abandonné | PostgreSQL suffisant |
| TensorFlow/PyTorch | ❌ Non utilisés | scikit-learn + XGBoost suffisants |
| MLflow | ✅ Livré | Conforme |
| Docker | ✅ Livré | API + Frontend + MLflow |
| GitHub Actions CI/CD | ✅ Livré | Dès le départ |
| Chatbot LLM (optionnel) | ❌ Non livré | 

---

## 10. Analyse rétrospective

### 10.1 Points forts

**Complétude de la chaîne de valeur** : nous livrons une plateforme end-to-end fonctionnelle, de la collecte brute jusqu'au trading simulé. Aucun maillon n'est laissé en suspens.

**Rigueur dès le départ** : CI/CD, branches protégées, tests unitaires et architecture modulaire ont été mis en place dès le premier commit. Cette rigueur a évité la dette technique qui fragilise souvent les projets académiques.

**Adaptation pragmatique** : plusieurs pivots (MongoDB → PostgreSQL, BeautifulSoup → RSS, PyTorch → XGBoost) ont été réalisés sans dérapage de calendrier, grâce à une architecture découplée et une culture du test.

**Au-delà du scope du cadrage** : WebSocket Binance pour les prix temps réel, paper trading complet avec P&L live, infrastructure Ansible/Prometheus/Grafana et `setup.sh` multi-OS dépassent les ambitions initiales.

**~70 Pull Requests en 5 mois** : collaboration structurée avec répartition claire des responsabilités.

### 10.2 Difficultés rencontrées

**MLflow en Docker** : le middleware de sécurité de MLflow 2.x rejette par défaut les requêtes ne venant pas de `localhost`. L'ajout de `--allowed-hosts "*"` a résolu le problème.

**Installation multi-OS (`setup.sh`)** : la plateforme devait fonctionner sur les machines des deux membres de l'équipe (macOS), les environnements CI Linux et le VPS Debian de production. Un simple `pip install -r requirements.txt` ne suffisait pas : `psycopg2` requiert `libpq-dev` sur Debian, `postgresql-devel` sur RedHat, ou `libpq` via Homebrew sur macOS ; plusieurs packages ML nécessitent en outre des headers de compilation (`python3-dev`, `build-essential`). Nous avons écrit `setup.sh`, un script bash qui détecte l'OS via `uname -s` puis affine la distribution Linux via les marqueurs `/etc/debian_version`, `/etc/redhat-release`, `/etc/arch-release` et `/etc/alpine-release`, avant d'appeler le bon gestionnaire de paquets (`apt`, `yum`, `pacman`, `apk`, `brew`). Le script vérifie également la version Python (3.10+ requis), crée et active le venv (sauf si conda est déjà actif), copie `.env.example` en `.env` et initialise les dossiers nécessaires. Windows est explicitement détecté et orienté vers WSL2 ou `make docker`. Ce script a uniformisé l'onboarding et supprimé les divergences d'environnement entre les membres de l'équipe et le CI.

**Compatibilité Linux** : `make run` présentait un bug sur Linux (absence de timeout sur la boucle d'attente de l'API, erreurs uvicorn masquées). Résolu par un compteur de timeout et `--log-level info`.

**Cache Streamlit** : `@st.cache_resource` a causé une `AttributeError` lors des mises à jour de code sans redémarrage complet — comportement inhérent à Streamlit.

**Volume de données pour le ML** : le walk-forward nécessite ~260 bougies minimum. Le rate limiting de CoinGecko et des exchanges a rendu la collecte initiale laborieuse.

### 10.3 Axes d'amélioration

**Apprentissage par renforcement** : objectif initial non atteint. Le paper trading peut servir d'environnement de simulation pour un agent RL (Monte Carlo, Q-learning comme prévu dans la roadmap).

**Authentification** : la plateforme ne gère pas encore les utilisateurs. Un flow JWT a été étudié.

**Données on-chain** : les personas (Noah notamment) expriment un besoin de données on-chain (flux DEX, activité whale) que nous n'avons pas couvert. Glassnode, Dune Analytics et Nansen sont identifiés comme sources.

**Sources news premium** : PhoenixNews (~1500 sources temps réel) et Cryptorank ont été identifiés en discovery mais non intégrés (coût).

**Mise en production complète** : `monpetitbet.fr` est prêt, le SSL reste à activer (configuration Nginx HTTPS commentée).

---

## Annexes

### A. Chronologie des commits

| Période | Activité principale |
|---|---|
| Jan 2026 | Fondations ETL, SQLite, tests, CI/CD |
| Fév 2026 | Market data CoinGecko, tables supplémentaires |
| Mar 2026 | ML feature engineering, modèles baseline |
| Avr 2026 | Sprint : API, Frontend, MLflow, Backtesting |
| Mai 2026 | Docker, NLP, signaux, XGBoost, alerting |
| Mai 2026 | Paper trading, PostgreSQL, WebSocket |
| Mai 2026 | Fixes, setup, docs, infra prod |
| **Total** | | **~100 commits, 65 PRs** |

### B. Livrables

| Livrable | Localisation |
|---|---|
| Code source | `Marivel75/_Crypto_Bot` (GitHub) |
| API documentée | `http://localhost:8000/docs` |
| Front | `http://localhost:8501` |
| Documentation technique | `docs/` |
| Schéma BDD | `docs/database_schema.md` |
| Diagrammes UML | `_v1/_all-diagrams.md` |
| Infrastructure prod | `_v1/infra/` |
| Script d'installation | `setup.sh` |
| Tests | `tests/` |
| Cadrage | `Crypto_bot_cadrage_V2.pdf` |
| Ressources discovery | `ressources_projet/` |

### C. Dépendances principales

```
ccxt>=4.0.0              # Multi-exchange crypto
FastAPI>=0.104.0         # API REST
SQLAlchemy>=2.0.0        # ORM
streamlit>=1.40.0        # Frontend
plotly>=5.18.0           # Visualisation
scikit-learn>=1.3.0      # ML
xgboost>=2.0.0           # Gradient boosting
mlflow>=2.10.0           # Experiment tracking
vaderSentiment>=3.3.2    # Analyse de sentiment
feedparser>=6.0.0        # Collecte RSS
websockets>=11.0         # WebSocket Binance
psycopg2-binary>=2.9.9   # PostgreSQL
```
