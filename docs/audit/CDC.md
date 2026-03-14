# Cahier des Charges — Crypto Bot

**Version :** 1.0
**Date :** 2026-03-12
**Classification :** Projet DTSC — École
**Auteurs :** Équipe BMAD (1 Master, 3 Analystes, 3 Product Managers, 3 Architectes)
**Validé par :** Audit technique du 2026-03-12 (note globale B+)

---

## Table des matières

1. [Contexte et Objectifs](#1-contexte-et-objectifs)
2. [Périmètre Fonctionnel](#2-périmètre-fonctionnel)
3. [Exigences Fonctionnelles — ETL](#3-exigences-fonctionnelles--etl)
4. [Exigences Fonctionnelles — API Backend](#4-exigences-fonctionnelles--api-backend)
5. [Exigences Fonctionnelles — ML & Signaux](#5-exigences-fonctionnelles--ml--signaux)
6. [Exigences Fonctionnelles — Frontend](#6-exigences-fonctionnelles--frontend)
7. [Exigences Non-Fonctionnelles](#7-exigences-non-fonctionnelles)
8. [Architecture Technique](#8-architecture-technique)
9. [Architecture des Données](#9-architecture-des-données)
10. [Architecture Infrastructure](#10-architecture-infrastructure)
11. [Sécurité](#11-sécurité)
12. [Plan de Remédiation Audit](#12-plan-de-remédiation-audit)
13. [Macro-Planning](#13-macro-planning)
14. [KPIs et Critères d'Acceptation](#14-kpis-et-critères-dacceptation)
15. [Glossaire](#15-glossaire)
16. [Livrables et Gouvernance](#16-livrables-et-gouvernance)
17. [Annexes — Documents de Référence](#17-annexes--documents-de-référence)

---

## 1. Contexte et Objectifs

### 1.1 Présentation du projet

Crypto Bot est une plateforme de surveillance, d'analytics et de génération de signaux de trading pour le marché crypto. C'est un **projet scolaire DTSC** strictement informationnel — **aucune exécution automatique de trades**.

### 1.2 Objectifs stratégiques

| # | Objectif | Indicateur de succès |
|---|----------|---------------------|
| O1 | Collecter et stocker les données OHLCV des top 30 cryptos en temps réel | Données à jour avec < 5 min de latence |
| O2 | Générer des signaux de trading fiables via règles techniques + ML | Win rate > 55%, confiance calibrée |
| O3 | Exposer les données et signaux via une API REST sécurisée | P95 latence < 500ms, 99.5% uptime |
| O4 | Fournir un dashboard interactif d'aide à la décision | 5 pages fonctionnelles, UX < 3s chargement |
| O5 | Démontrer les compétences en Data Science, ML et DevOps | Couverture tests ≥ 80%, CI/CD opérationnel |

### 1.3 Contraintes fondamentales

- **Aucune API payante** — Binance public, CoinGecko Demo, CCXT uniquement
- **Aucun Kubernetes** — Docker Compose pour V1
- **Aucune exécution de trade** — signaux informationnels uniquement
- **Aucun MongoDB** — JSONB dans TimescaleDB
- **Budget** : 0€ (hors VPS OVH)

### 1.4 Équipe

| Équipe | Répertoire | Documentation |
|--------|-----------|---------------|
| Data Engineering | `src/etl/`, `src/shared/` | `docs/01-data-engineering.md` |
| ML / Data Science | `src/ml/` | `docs/02-ml-data-science.md` |
| Backend / API | `src/api/` | `docs/03-backend-api.md` |
| Frontend / UI | `src/frontend/` | `docs/04-frontend-ui.md` |
| DevOps / Infra | `infra/`, `docker-compose.yml`, `nginx/` | `docs/05-devops-infra.md` |

### 1.5 Stack technique

| Couche | Technologies |
|--------|-------------|
| Langage | Python 3.11+ |
| API | FastAPI + Uvicorn |
| Frontend | Streamlit + Plotly |
| Base de données | TimescaleDB (PostgreSQL 16) |
| Object Storage | MinIO (S3-compatible) |
| ML Tracking | MLflow |
| Dataset Versioning | DVC |
| Orchestration ETL | APScheduler |
| Conteneurisation | Docker Compose |
| Reverse Proxy | Nginx |
| CI/CD | GitHub Actions |
| Provisioning | Ansible |

---

## 2. Périmètre Fonctionnel

### 2.1 Vue d'ensemble

```
[Sources Externes] → [ETL Pipeline] → [TimescaleDB + MinIO]
                                              │
                                    [ML Engine] ──── [FastAPI REST API]
                                    [Rules+ML]           │
                                    [MLflow]        [Streamlit + Plotly]
```

### 2.2 Synthèse des exigences

| Module | Nb Exigences | Priorité MUST | SHOULD | COULD | Détail |
|--------|-------------|---------------|--------|-------|--------|
| ETL | 16 RF | 12 | 3 | 1 | §3 |
| API Backend | 26 RF | 18 | 6 | 2 | §4 |
| ML & Signaux | 23 RF + 3 RF Analytics | 16 | 7 | 3 | §5 |
| Frontend | 53 RF | 32 | 14 | 7 | §6 |
| **Non-fonctionnelles** | **12 RNF** | **8** | **3** | **1** | §7 |
| **Total** | **133 RF + 12 RNF** | **86** | **33** | **14** | |

### 2.3 Symboles suivis

Top 30 par capitalisation. Priorité 13 : **BTC, ETH, USDT, USDC, BNB, XRP, SOL, ADA, AVAX, DOT, DOGE, TRX, ATOM**

### 2.4 Sources de données (gratuites)

| Source | Type | Fréquence | Données |
|--------|------|-----------|---------|
| Binance Public REST | OHLCV historique | Toutes les 5 min | Klines, order book |
| Binance WebSocket | OHLCV temps réel | Continu | Klines stream |
| CoinGecko Demo | Métadonnées marché | Toutes les 15 min | Rankings, market cap |
| CCXT | Multi-exchange fallback | À la demande | OHLCV multi-exchange |
| News RSS | Articles crypto | Toutes les 30 min | Decrypt, Cointelegraph |
| Alternative.me | Sentiment | Toutes les 6h | Fear & Greed Index |

---

## 3. Exigences Fonctionnelles — ETL

> Détail complet : [`SPECIFICATIONS_FONCTIONNELLES.md`](./SPECIFICATIONS_FONCTIONNELLES.md) §Module ETL

### 3.1 Collecte de données

| ID | Titre | Priorité | Description |
|----|-------|----------|-------------|
| RF-ETL-001 | Collecte OHLCV Binance REST | MUST | Historique via `/api/v3/klines`, 11 timeframes, pagination auto, rate limit 1200 req/min |
| RF-ETL-002 | Collecte OHLCV Binance WebSocket | MUST | Temps réel via stream `kline_<tf>`, reconnexion automatique, heartbeat |
| RF-ETL-003 | Collecte multi-exchange CCXT | SHOULD | Fallback si Binance indisponible, même format OHLCVRecord |
| RF-ETL-004 | Collecte CoinGecko | MUST | Market data, rankings, metadata, respect 30 req/min (Demo) |
| RF-ETL-005 | Collecte News | MUST | Scraping RSS (Decrypt, Cointelegraph), extraction titre/contenu/date |
| RF-ETL-006 | Collecte Fear & Greed | SHOULD | Alternative.me, index 0-100, historique 30 jours |

### 3.2 Orchestration et traitement

| ID | Titre | Priorité | Description |
|----|-------|----------|-------------|
| RF-ETL-007 | Orchestration APScheduler | MUST | 9 jobs planifiés (OHLCV 5min, CoinGecko 15min, News 30min, etc.) |
| RF-ETL-008 | Stockage TimescaleDB OHLCV | MUST | Hypertable `crypto_prices`, compression 7j, rétention 90j |
| RF-ETL-009 | Stockage indicateurs et signaux | MUST | Tables `indicators`, `trading_signals`, `news_articles` |
| RF-ETL-010 | Validation Pydantic | MUST | `OHLCVRecord` : high ≥ open, close, low ; volume ≥ 0 |
| RF-ETL-011 | Déduplication | MUST | Clé unique (symbol, timeframe, timestamp), upsert |
| RF-ETL-012 | Détection de gaps | MUST | Alerte si > 2 candles manquantes consécutives |
| RF-ETL-013 | Stockage MinIO | SHOULD | Buckets `raw/`, `datasets/`, format Parquet/CSV |
| RF-ETL-014 | Logging structuré | MUST | JSON, chaque job : timestamp, records fetched/inserted, erreurs |
| RF-ETL-015 | Healthcheck | MUST | Endpoint interne, vérification connectivité DB + sources |
| RF-ETL-016 | Gestion d'erreurs | MUST | Exponential backoff (1s→16s), retry 3x, circuit breaker |

### 3.3 Critères d'acceptation ETL

- [ ] Collecte OHLCV opérationnelle pour les 13 cryptos prioritaires
- [ ] Latence données < 5 minutes vs exchange
- [ ] Débit ≥ 300 candles/minute
- [ ] Pas de gaps > 2 candles sur 24h
- [ ] Logs exploitables pour chaque run ETL
- [ ] Toutes les données validées par Pydantic avant insertion

---

## 4. Exigences Fonctionnelles — API Backend

> Détail complet : [`SPECIFICATIONS_FONCTIONNELLES.md`](./SPECIFICATIONS_FONCTIONNELLES.md) §Module API

### 4.1 Authentification

| ID | Titre | Priorité | Endpoint |
|----|-------|----------|----------|
| RF-API-001 | Inscription | MUST | `POST /api/auth/register` — bcrypt 12 rounds |
| RF-API-002 | Connexion JWT | MUST | `POST /api/auth/login` — access + refresh tokens |
| RF-API-003 | Profil utilisateur | MUST | `GET /api/auth/me` — JWT required |

### 4.2 Données crypto

| ID | Titre | Priorité | Endpoint |
|----|-------|----------|----------|
| RF-API-004 | Liste symboles | MUST | `GET /api/crypto/list` |
| RF-API-005 | Prix OHLCV | MUST | `GET /api/crypto/{symbol}/prices?tf=4h&limit=100` |
| RF-API-006 | Indicateurs | MUST | `GET /api/crypto/{symbol}/indicators` |
| RF-API-007 | Dernier prix | MUST | `GET /api/crypto/{symbol}/latest` |
| RF-API-008 | Market overview | SHOULD | `GET /api/crypto/market-overview` |

### 4.3 Signaux de trading

| ID | Titre | Priorité | Endpoint |
|----|-------|----------|----------|
| RF-API-009 | Signaux actifs | MUST | `GET /api/signals/active` — dernières 24h |
| RF-API-010 | Signaux par crypto | MUST | `GET /api/signals/{symbol}` |
| RF-API-011 | Détail signal | SHOULD | `GET /api/signals/{id}/detail` — outcome inclus |
| RF-API-012 | Performance signaux | SHOULD | `GET /api/signals/performance` — win rate, P&L |

### 4.4 News et sentiment

| ID | Titre | Priorité | Endpoint |
|----|-------|----------|----------|
| RF-API-013 | Dernières news | MUST | `GET /api/news/latest?limit=20` |
| RF-API-014 | Détail article | SHOULD | `GET /api/news/{id}` — NLP metadata |
| RF-API-015 | Sentiment par crypto | MUST | `GET /api/news/sentiment?symbol=BTC` |

### 4.5 Utilisateur

| ID | Titre | Priorité | Endpoint |
|----|-------|----------|----------|
| RF-API-016 | Portfolio CRUD | MUST | `GET/POST/PUT/DELETE /api/portfolio` — JWT required |
| RF-API-017 | Watchlist CRUD | MUST | `GET/POST/DELETE /api/watchlist` — JWT required |
| RF-API-018 | Chatbot IA | COULD | `POST /api/chat` — JWT required |

### 4.6 Système et infrastructure API

| ID | Titre | Priorité | Description |
|----|-------|----------|-------------|
| RF-API-019 | Healthcheck | MUST | `GET /api/health` — status DB, MinIO, services |
| RF-API-020 | Sources status | SHOULD | `GET /api/system/sources-status` |
| RF-API-021 | Pagination | MUST | `limit`/`page` sur tous les endpoints liste |
| RF-API-022 | Rate limiting | MUST | Auth : 5 req/min, API : 30 req/s |
| RF-API-023 | Gestion erreurs | MUST | Enveloppe `{success, data, error, meta}` |
| RF-API-024 | CORS | MUST | Whitelist origin Streamlit uniquement |
| RF-API-025 | Documentation OpenAPI | MUST | Swagger auto-généré par FastAPI |
| RF-API-026 | Logging et monitoring | MUST | Prometheus metrics, structured logging |

### 4.7 Format de réponse API

```json
{
    "success": true,
    "data": { "..." },
    "error": null,
    "meta": { "total": 100, "page": 1, "limit": 20 }
}
```

---

## 5. Exigences Fonctionnelles — ML & Signaux

> Détail complet : [`.claude/specs/cdc-ml-analytics.md`](./.claude/specs/cdc-ml-analytics.md)

### 5.1 Phase 1 — Moteur de Règles

| ID | Titre | Priorité | Description |
|----|-------|----------|-------------|
| RF-ML-001 | Config YAML indicateurs | MUST | `src/ml/config/indicators.yaml` — source unique des seuils |
| RF-ML-002 | RSI multi-timeframe | MUST | Convergence RSI sur 1h/2h/3h/4h, seuils overbought 70 / oversold 30 |
| RF-ML-003 | Bollinger Bands | MUST | Squeeze detection, breakout, band walking (MA20, 2σ) |
| RF-ML-004 | Harmonic Patterns | MUST | Gartley, Butterfly, Bat, Crab — ratios Fibonacci ±2% tolérance |
| RF-ML-005 | Trend Lines | MUST | Weekly (stable, 200 périodes) vs Monthly (agressif, 400 périodes) |
| RF-ML-006 | Convergence RSI+Bollinger | SHOULD | RSI oversold + prix bas de bande = signal fort (weight 0.95) |
| RF-ML-007 | Convergence Trend+RSI | SHOULD | Dip en uptrend = BULL, rally en downtrend = BEAR |
| RF-ML-008 | Alignement multi-TF | MUST | Majorité ≥60% TFs concordants → signal avec poids 0.6-0.9 |
| RF-ML-009 | Agrégation pondérée | MUST | Scores par direction, pénalité opposition, seuil confiance ≥ 0.6 |

**Poids des règles :**

| Indicateur | Poids | Justification |
|------------|-------|--------------|
| RSI | 0.25 | Momentum, réactif |
| Bollinger Bands | 0.25 | Volatilité, mean-reversion |
| Harmonic Patterns | 0.30 | Pattern recognition, haute précision |
| Trend Lines | 0.20 | Contexte directionnel |

### 5.2 Génération de signaux

| ID | Titre | Priorité | Description |
|----|-------|----------|-------------|
| RF-ML-010 | Signal Generator | MUST | Fusion rules + ML (60/40) + ajustement sentiment ±5pp |
| RF-ML-011 | Seuil confiance | MUST | Émission uniquement si `confidence ≥ 0.6` |
| RF-ML-012 | Levier et marge | MUST | Suggestion 5x/10x/20x selon confiance, vérification marge 2x |
| RF-ML-013 | Estimation frais | MUST | 0.17% round-trip (maker + taker + slippage), annulation si frais > 50% du gain |
| RF-ML-014 | Batch generation | MUST | `generate_signals_for_symbols()` — tous les symboles, idempotent |
| RF-ML-015 | Logging signaux | MUST | Chaque signal loggé avec contexte complet des indicateurs |

**Format signal :**

```python
{
    "symbol": "BTCUSDT",
    "signal_type": "BUY | SELL | HOLD",
    "confidence_score": 0.0 - 1.0,      # émis si ≥ 0.6
    "timeframe_primary": "4h",
    "rules_triggered": ["rsi_overbought_multi_tf", "bollinger_breakout"],
    "leverage_suggested": 5 | 10 | 20,
    "margin_safety": 0.4 | 0.2 | 0.1,   # toujours ≥ 2x rule
    "fees_estimated": 0.0017,
    "model_version": "rules_v1",
    "created_at": "2026-03-12T14:00:00Z"
}
```

### 5.3 Phase 2 — ML Supervisé

| ID | Titre | Priorité | Description |
|----|-------|----------|-------------|
| RF-ML-016 | Feature Engineering | MUST | 28+ features (RSI/TF, Bollinger pos, trend slope, volume ratio, sentiment) |
| RF-ML-017 | Walk-Forward Backtesting | MUST | `WalkForwardBacktester` — purge/embargo, Sharpe annualisé, max drawdown |
| RF-ML-018 | Training Models | MUST | XGBoost, LightGBM, Random Forest, LSTM — split temporel 80/20 |
| RF-ML-019 | MLflow Tracking | MUST | Params, métriques, artifacts dans PostgreSQL + MinIO |
| RF-ML-020 | DVC Versioning | SHOULD | Datasets versionnés dans MinIO via Git |
| RF-ML-021 | Concept Drift Detection | SHOULD | Métriques rolling, retrain trigger hebdomadaire |
| RF-ML-022 | NLP Sentiment | SHOULD | TF-IDF + Logistic Regression, score -1.0 à +1.0 |
| RF-ML-023 | Model Registry | MUST | Staging → Production, archivage automatique |

### 5.4 Module Analytics

| ID | Titre | Priorité | Description |
|----|-------|----------|-------------|
| RF-ANA-001 | Heatmap corrélations | MUST | Plotly interactive, multi-timeframe, Pearson sur rendements |
| RF-ANA-002 | Historique signaux | MUST | Tableau filtrable, outcome (was_correct, P&L simulé) |
| RF-ANA-003 | Métriques backtest | SHOULD | Dashboard Sharpe, Sortino, max drawdown, win rate, profit factor |

---

## 6. Exigences Fonctionnelles — Frontend

> Détail complet : [`.claude/specs/frontend-ui-cdc/01-requirements.md`](./.claude/specs/frontend-ui-cdc/01-requirements.md)

### 6.1 Personas

| Persona | Rôle | Besoins clés |
|---------|------|-------------|
| Noah | Trader technique | Bougies OHLCV, indicateurs, signaux temps réel |
| Sarah | Journaliste crypto | Fil de news, sentiment, word cloud, export |
| Aleksandar | Investisseur | Portfolio P&L, watchlist, chatbot IA |

### 6.2 Page 1 — Dashboard (Noah)

| ID | Titre | Priorité |
|----|-------|----------|
| RF-UI-001 | Graphique chandelier OHLCV (Plotly) | MUST |
| RF-UI-002 | Sélecteur crypto (top 30) | MUST |
| RF-UI-003 | Sélecteur timeframe (1m à 1M) | MUST |
| RF-UI-004 | Overlay RSI multi-TF | MUST |
| RF-UI-005 | Overlay Bollinger Bands | MUST |
| RF-UI-006 | Overlay volume | MUST |
| RF-UI-007 | Panneau signaux actifs | MUST |
| RF-UI-008 | Mini fil de news | SHOULD |
| RF-UI-009 | Marqueurs signaux sur graphique | SHOULD |
| RF-UI-010 | Fear & Greed gauge | SHOULD |

### 6.3 Page 2 — Veille (Sarah)

| ID | Titre | Priorité |
|----|-------|----------|
| RF-UI-011 | Fil de news temps réel | MUST |
| RF-UI-012 | Filtrage par crypto | MUST |
| RF-UI-013 | Score sentiment par article | MUST |
| RF-UI-014 | Jauge sentiment agrégé | MUST |
| RF-UI-015 | Word cloud mots-clés | SHOULD |
| RF-UI-016 | Timeline sentiment historique | SHOULD |
| RF-UI-017 | Filtrage par source | SHOULD |
| RF-UI-018 | Export CSV/PDF | COULD |

### 6.4 Page 3 — Portfolio (Aleksandar)

| ID | Titre | Priorité |
|----|-------|----------|
| RF-UI-019 | Ajout de position | MUST |
| RF-UI-020 | Vue P&L temps réel | MUST |
| RF-UI-021 | Historique transactions | MUST |
| RF-UI-022 | Répartition en camembert | MUST |
| RF-UI-023 | Watchlist CRUD | MUST |
| RF-UI-024 | Alertes prix | SHOULD |
| RF-UI-025 | Chatbot IA | COULD |
| RF-UI-026 | Export portfolio | SHOULD |

### 6.5 Page 4 — Analytics

| ID | Titre | Priorité |
|----|-------|----------|
| RF-UI-027 | Heatmap corrélations | MUST |
| RF-UI-028 | Market overview (top/flop) | MUST |
| RF-UI-029 | Fear & Greed historique | SHOULD |
| RF-UI-030 | Comparaison cryptos | SHOULD |
| RF-UI-031 | Volume analysis | COULD |

### 6.6 Page 5 — Performance

| ID | Titre | Priorité |
|----|-------|----------|
| RF-UI-032 | Historique signaux | MUST |
| RF-UI-033 | Win rate / hit ratio | MUST |
| RF-UI-034 | P&L cumulé graphique | MUST |
| RF-UI-035 | Filtrage par modèle | SHOULD |
| RF-UI-036 | Métriques avancées (Sharpe, drawdown) | SHOULD |

### 6.7 Exigences transversales UI

| ID | Titre | Priorité |
|----|-------|----------|
| RF-UI-037 | Navigation sidebar multi-page | MUST |
| RF-UI-038 | Thème sombre | MUST |
| RF-UI-039 | Internationalisation FR/EN | MUST |
| RF-UI-040 | Cache API avec TTL | MUST |
| RF-UI-041 | Gestion erreurs user-friendly | MUST |
| RF-UI-042 | Authentification (login/register) | MUST |
| RF-UI-043 | Responsive (desktop + tablette) | SHOULD |
| RF-UI-044 | Accessibilité WCAG 2.1 AA | SHOULD |
| RF-UI-045-053 | Composants réutilisables, logging, settings | SHOULD/COULD |

### 6.8 Stack Frontend

- **Streamlit** — framework principal (pas de React/Vue)
- **Plotly** — graphiques interactifs (candlestick, heatmap, line)
- **`api_client.py`** — isolation totale de l'accès API
- **`st.cache_data`** — caching avec TTL approprié
- **JAMAIS** d'accès direct à TimescaleDB, MinIO ou MLflow

---

## 7. Exigences Non-Fonctionnelles

> Détail complet : [`SPECIFICATIONS_FONCTIONNELLES.md`](./SPECIFICATIONS_FONCTIONNELLES.md) §Exigences Non-Fonctionnelles

| ID | Catégorie | Exigence | Cible |
|----|-----------|----------|-------|
| RNF-001 | Performance API | Temps de réponse | P95 < 500ms, P99 < 2s |
| RNF-002 | Performance ETL | Débit de collecte | ≥ 300 candles/min |
| RNF-003 | Disponibilité | Uptime | 99.5% (hors maintenance planifiée) |
| RNF-004 | Sécurité Auth | Hachage mot de passe | bcrypt 12 rounds |
| RNF-005 | Sécurité API | Validation entrées | Pydantic sur TOUS les endpoints |
| RNF-006 | Sécurité Erreurs | Exposition interne | Jamais de stack traces en réponse |
| RNF-007 | Scalabilité DB | Connection pooling | SQLAlchemy async, pool 5-20 connexions |
| RNF-008 | Scalabilité API | Caching | `st.cache_data` TTL, pagination obligatoire |
| RNF-009 | Résilience | Retry externe | Exponential backoff 1s→16s, max 3 retries |
| RNF-010 | Maintenabilité | Couverture tests | ≥ 80% par module |
| RNF-011 | Maintenabilité | Qualité code | ruff + mypy strict, max 400 lignes/fichier |
| RNF-012 | Conformité | Données utilisateur | RGPD si applicable (consentement, droit d'oubli) |

### Performance ML spécifique

| Métrique | Cible |
|----------|-------|
| Inférence signal (rule engine) | < 200ms par symbole |
| Inférence signal (ML model) | < 500ms par symbole |
| Training XGBoost (1 symbole) | < 5 min |
| Backtesting walk-forward (1 symbole) | < 2 min |
| MLflow logging | < 1s par run |

---

## 8. Architecture Technique

> Détail complet : [`docs/06-architecture-applicative.md`](./docs/06-architecture-applicative.md)

### 8.1 Vue d'ensemble

```
┌──────────────────────────────────────────────────────────────────┐
│                 SOURCES DE DONNÉES EXTERNES                      │
│  [Binance] [CoinGecko] [CCXT] [News RSS] [Alternative.me]      │
└────────────────────────────┬─────────────────────────────────────┘
                             │
               ┌─────────────▼──────────────┐
               │   ETL PIPELINE             │
               │  (src/etl/)               │
               │  APScheduler + Collectors  │
               └─────────────┬──────────────┘
                             │
         ┌───────────────────┴──────────────────┐
         │                                      │
 ┌───────▼────────┐                 ┌──────────▼───────┐
 │  TimescaleDB   │                 │    MinIO (S3)    │
 │  (PostgreSQL16)│                 │  (Artifacts ML)  │
 └───────┬────────┘                 └──────────────────┘
         │
 ┌───────┴───────────────────┐
 │                           │
 ┌▼──────────────┐   ┌──────▼─────────────┐
 │  ML ENGINE    │   │  FastAPI Backend   │
 │  Rules + ML   │   │  8 routers         │
 │  MLflow       │   │  Response envelope │
 └───────────────┘   └──────┬─────────────┘
                            │
                     ┌──────▼─────────────┐
                     │  Streamlit         │
                     │  5 pages + Plotly  │
                     └────────────────────┘
```

### 8.2 Architecture API (FastAPI)

**Structure en couches :** Routes → Services → Repositories → Database

**8 routeurs :**
- `auth` — inscription, connexion, profil
- `crypto` — données OHLCV, indicateurs, market overview
- `signals` — signaux actifs, détails, performance
- `news` — articles, sentiment
- `portfolio` — CRUD positions (JWT)
- `watchlist` — CRUD suivi (JWT)
- `chat` — chatbot IA (JWT)
- `system` — health, sources status

**Enveloppe de réponse :** `ApiResponse[T]` avec `success`, `data`, `error`, `meta`

**Middleware :** CORS, Prometheus metrics, logging structuré, exception handlers

**Dépendances :** `get_db()` (session async), `get_current_user()` (JWT decode)

### 8.3 Architecture ML

**Phase 1 — Rule Engine :**
```
IndicatorRecord[TF] → RuleEngine.evaluate() → RuleResult[] → aggregate() → TradingSignal | None
```

**Phase 2 — Supervised ML :**
```
Features → ModelTrainer.train() → MLflow log → WalkForwardBacktester.run() → Model Registry
```

**Signal Generation Pipeline :**
```
TimescaleDB → SignalGenerator.generate() → Rules (60%) + ML (40%) + Sentiment (±5pp) → emit if ≥ 0.6
```

### 8.4 Architecture Frontend (Streamlit)

- Multi-page app (`src/frontend/app.py` + `pages/`)
- Composants réutilisables (`components/`)
- **APIClient isolé** (`api_client.py`) — SEUL point d'accès aux données
- Caching `@st.cache_data(ttl=300)` pour limiter les appels API
- i18n FR/EN via fichiers de traduction

### 8.5 Architecture ETL

**9 jobs APScheduler :**

| Job | Intervalle | Source | Destination |
|-----|-----------|--------|-------------|
| OHLCV Binance REST | 5 min | Binance | `crypto_prices` |
| OHLCV WebSocket | Continu | Binance | `crypto_prices` |
| CoinGecko metadata | 15 min | CoinGecko | `crypto_prices` |
| News scraping | 30 min | RSS feeds | `news_articles` |
| Fear & Greed | 6h | Alternative.me | `indicators` |
| Indicator calculation | 15 min | `crypto_prices` | `indicators` |
| Signal generation | 4h | `indicators` | `trading_signals` |
| Data quality check | 1h | `crypto_prices` | Logs |
| Gap reconciliation | Quotidien | `crypto_prices` | `crypto_prices` |

### 8.6 Patterns architecturaux

| Pattern | Usage | Exemple |
|---------|-------|---------|
| Repository | Abstraction accès données | `UserRepository`, `SignalRepository` |
| Service | Logique métier séparée des routes | `CryptoService`, `SignalService` |
| Dependency Injection | FastAPI `Depends()` | `get_db()`, `get_current_user()` |
| Async/Await | Toutes les I/O | SQLAlchemy async, httpx |
| Config centralisée | pydantic-settings | `src/shared/config.py` |
| Exception hierarchy | Gestion d'erreurs structurée | `CryptoBotError` → `NotFoundError`, `AuthError` |

---

## 9. Architecture des Données

> Détail complet : [`docs/data-architecture.md`](./docs/data-architecture.md)

### 9.1 TimescaleDB — Schéma principal

| Table | Type | Clé primaire | Description |
|-------|------|-------------|-------------|
| `users` | Relationnelle | `id` (UUID) | Comptes utilisateurs (bcrypt) |
| `crypto_prices` | **Hypertable** | `(symbol, timeframe, timestamp)` | OHLCV + volume |
| `indicators` | Relationnelle | `id` | RSI, Bollinger, harmonics, trend |
| `trading_signals` | Relationnelle | `id` | Signaux générés (BUY/SELL/HOLD) |
| `signal_outcomes` | Relationnelle | `id` | Évaluation post-hoc des signaux |
| `portfolio` | Relationnelle | `id` | Positions utilisateur |
| `watchlist` | Relationnelle | `id` | Cryptos suivies par utilisateur |
| `news_articles` | Relationnelle | `id` | Articles + sentiment score |

### 9.2 Politiques TimescaleDB

| Politique | Configuration | Impact |
|-----------|--------------|--------|
| Compression | Après 7 jours | Réduction 80% espace disque |
| Rétention | Données brutes : 90 jours | Nettoyage automatique |
| Hypertable | `crypto_prices` partitionné par temps | Requêtes temporelles optimisées |
| Index | `(symbol, timeframe, timestamp)` | Lookups O(log n) |

### 9.3 MinIO — Structure des buckets

| Bucket | Contenu | Lifecycle |
|--------|---------|-----------|
| `raw/` | Données brutes Parquet/CSV | 30 jours |
| `datasets/` | Features ML préparées | Permanent (DVC) |
| `models/` | Artifacts de modèles entraînés | Permanent |
| `mlflow-artifacts/` | Artifacts MLflow (params, métriques) | Permanent |
| `exports/` | Exports utilisateur (CSV, PDF) | 7 jours |

### 9.4 Contrats inter-équipes

| Producteur | Consommateur | Table/Bucket | Format |
|-----------|-------------|-------------|--------|
| ETL | ML, API | `crypto_prices` | OHLCVRecord Pydantic |
| ETL | ML, API | `indicators` | IndicatorRecord Pydantic |
| ETL | API | `news_articles` | NewsArticle Pydantic |
| ML | API | `trading_signals` | TradingSignal Pydantic |
| API | Frontend | HTTP REST JSON | ApiResponse[T] |

---

## 10. Architecture Infrastructure

> Sources : Architect 3 (Infra) + audit.md §3 (DevOps)

### 10.1 Topologie Docker Compose

```
              ┌──────────────┐
              │    Nginx     │ ← ports 80, 443
              │ (Reverse     │
              │  Proxy)      │
              └──┬───────┬───┘
                 │       │
          ┌──────▼──┐  ┌─▼────────┐
          │Frontend │  │  API     │
          │Streamlit│  │ FastAPI  │
          │ :8501   │  │  :8000   │
          └─────────┘  └──┬───────┘
                          │ backend-net
     ┌────────┬───────────┼──────────┬──────────┐
     │        │           │          │          │
┌────▼──┐ ┌──▼───┐ ┌─────▼──┐ ┌────▼───┐ ┌───▼────┐
│Timesc.│ │MinIO │ │ MLflow │ │  ETL   │ │  ML    │
│  DB   │ │(S3)  │ │Tracking│ │ Worker │ │ Worker │
│ :5432 │ │:9000 │ │ :5000  │ │        │ │        │
└───────┘ └──────┘ └────────┘ └────────┘ └────────┘
```

**Réseaux :**
- `frontend-net` : nginx, api, frontend (exposé)
- `backend-net` : api, timescaledb, minio, mlflow, etl-worker, ml-worker (interne)

**Isolation critique :** TimescaleDB et MinIO ne sont PAS accessibles depuis le frontend.

### 10.2 Images Docker (pinnées)

| Service | Image | Version |
|---------|-------|---------|
| TimescaleDB | `timescale/timescaledb` | `2.14.2-pg16` |
| MinIO | `minio/minio` | `RELEASE.2024-03-13` |
| Nginx | `nginx` | `1.27-alpine` |
| Python (API, ETL, ML) | `python` | `3.11.9-slim` |
| Prometheus | `prom/prometheus` | `v2.52.0` |
| Grafana | `grafana/grafana` | `10.4.2` |

### 10.3 CI/CD (GitHub Actions)

```
PR / push main → [Lint ruff] → [Type mypy] → [Tests pytest ≥80%] → [Docker build] → [Deploy Ansible]
```

| Stage | Outils | Gate |
|-------|--------|------|
| Lint | `ruff check`, `ruff format --check` | 0 erreurs |
| Type check | `mypy --strict` | 0 erreurs |
| Tests | `pytest --cov-fail-under=80` | Couverture ≥ 80% |
| Build | `docker compose build` | Build success |
| Deploy | `ansible-playbook deploy.yml` | Healthcheck pass |

### 10.4 Ansible

| Playbook | Usage | Fréquence |
|----------|-------|-----------|
| `provision.yml` | Setup VPS (Docker, UFW, fail2ban, swap) | Une fois |
| `deploy.yml` | Sync + build + up + healthcheck | À chaque release |
| `ssl.yml` | Let's Encrypt + auto-renew | Une fois |
| `backup.yml` | pg_dump + mc mirror | Cron quotidien |

### 10.5 Monitoring

| Composant | Métriques | Alertes |
|-----------|----------|---------|
| Prometheus | Scrape toutes les 15s | — |
| Grafana | 4 dashboards (API, DB, System, Business) | CPU > 80%, mémoire > 85% |
| postgres-exporter | Connexions, query time, cache hit | Connexions > 80 |
| nginx-exporter | Requêtes/s, erreurs 4xx/5xx | Erreurs > 1% |

### 10.6 Backup et recovery

| Donnée | Méthode | Fréquence | Rétention | RTO/RPO |
|--------|---------|-----------|-----------|---------|
| TimescaleDB | `pg_dump` compressé → MinIO | Quotidien 3h UTC | 30 jours | 30 min / 24h |
| MinIO | `mc mirror` vers bucket backup | Hebdomadaire | 4 semaines | 2h / 7j |
| Configuration | Git repository | À chaque commit | Illimitée | Instant |

---

## 11. Sécurité

> Source : Audit sécurité du 2026-03-12 (note C)

### 11.1 Points positifs existants

- bcrypt 12 rounds pour les mots de passe
- JWT HS256 avec expiration + validation
- SQL 100% paramétré (SQLAlchemy ORM)
- Multi-stage Docker, user non-root (UID 1001)
- Rate limiting Nginx sur endpoints auth
- `.env` correctement gitignored

### 11.2 Exigences de sécurité

| ID | Exigence | Priorité |
|----|----------|----------|
| SEC-001 | Aucun secret hardcodé dans le code source | CRITICAL |
| SEC-002 | Mots de passe forts obligatoires (pas de defaults) | CRITICAL |
| SEC-003 | HTTPS avec Let's Encrypt en production | HIGH |
| SEC-004 | CORS restrictif (whitelist Streamlit origin) | HIGH |
| SEC-005 | Headers sécurité Nginx (X-Frame-Options, CSP, HSTS) | HIGH |
| SEC-006 | Images Docker pinnées (pas de `:latest`) | HIGH |
| SEC-007 | Validation Pydantic sur TOUS les endpoints | HIGH |
| SEC-008 | Credentials MLflow via env vars (pas CLI args) | CRITICAL |
| SEC-009 | Firewall UFW (22, 80, 443 uniquement) | HIGH |
| SEC-010 | Fail2ban SSH (ban après 5 tentatives) | HIGH |
| SEC-011 | Logging sans secrets (masquer tokens, passwords) | MEDIUM |
| SEC-012 | Audit dépendances régulier | MEDIUM |

---

## 12. Plan de Remédiation Audit

> Source : [`audit.md`](./audit.md) — Note globale B+, 8 CRITICAL, 12 HIGH

### 12.1 Phase 1 — Bloquants (Semaine 1)

| Priorité | Issue | Effort | Équipe |
|----------|-------|--------|--------|
| P0 | **S1** — Supprimer secrets hardcodés de `config.py` | 30 min | Backend |
| P0 | **S2** — MLflow : passer DB creds en env vars | 20 min | DevOps |
| P0 | **S3** — Forcer mots de passe forts (pas de defaults) | 45 min | DevOps |
| P0 | **D1** — Pinner toutes les images Docker | 30 min | DevOps |
| P0 | **D2** — Corriger Ansible `delete: true` | 15 min | DevOps |
| P0 | **T1** — Inclure code ML dans la couverture | 1h | ML |
| P0 | **T2** — Corriger import `WalkForwardBacktester` | 15 min | ML |
| P0 | **T3** — Écrire test E2E pipeline signaux | 2h | Transversal |

**Effort Phase 1 : ~5h**

### 12.2 Phase 2 — Avant Production (Semaines 2-3)

| Priorité | Issue | Effort |
|----------|-------|--------|
| P1 | **S4** — Validation input signals/watchlist | 15 min |
| P1 | **S5** — Restreindre CORS | 10 min |
| P1 | **S6** — Activer HTTPS + Let's Encrypt | 1h |
| P1 | **S7** — Headers sécurité Nginx | 10 min |
| P1 | **S8** — Pinner images Python | 10 min |
| P1 | **D3** — Script de rollback | 2h |
| P1 | **D5** — Backup MinIO | 1h |
| P1 | **C1** — Écrire runbook de production | 2h |
| P1 | **C2** — Harmoniser version PostgreSQL (pg16) | 30 min |

**Effort Phase 2 : ~7h**

### 12.3 Phase 3 — Améliorations (Semaine 4+)

| Priorité | Issues | Effort |
|----------|--------|--------|
| P2 | A1-A5 — Architecture et qualité | 4h |
| P2 | T4-T7 — Testing et ML | 3h |
| P2 | S9-S12 — Sécurité medium/low | 1h |
| P2 | D6-D10 — DevOps medium | 3h |
| P2 | C3-C5 — Documentation | 2h |

**Effort Phase 3 : ~13h**

**Effort total remédiation : ~25h**

---

## 13. Macro-Planning

### 13.1 Phases du projet

| Phase | Période | Focus | Livrables |
|-------|---------|-------|-----------|
| **Phase 0** | Semaine 1 | Remédiation P0 (bloquants) | 8 issues CRITICAL résolues |
| **Phase 1** | Semaines 2-3 | Remédiation P1 + ETL complet | ETL opérationnel, HTTPS, backups |
| **Phase 2** | Semaines 4-6 | ML Phase 1 + API complète | Rule engine, signaux, API 26 endpoints |
| **Phase 3** | Semaines 7-9 | Frontend 5 pages + ML Phase 2 | Dashboard, veille, portfolio, analytics, performance |
| **Phase 4** | Semaines 10-12 | Monitoring + Tests + Polish | Grafana, couverture ≥80%, runbook, docs |

### 13.2 Sprint planning détaillé

| Sprint | Semaine | Équipe | Objectif |
|--------|---------|--------|----------|
| S0 | 1 | Tous | Remédiation 8 CRITICAL (secrets, images, tests) |
| S1 | 2-3 | ETL + DevOps | ETL 16 RF + HTTPS + Backup + CI/CD |
| S2 | 4-5 | API + ML | API 26 endpoints + Rule Engine 15 RF |
| S3 | 6-7 | ML + Frontend | Backtesting + Signal Generator + Dashboard |
| S4 | 8-9 | Frontend | 5 pages Streamlit (53 RF) |
| S5 | 10-11 | ML + DevOps | ML Phase 2 (training, MLflow) + Monitoring |
| S6 | 12 | Tous | Tests E2E, polish, documentation finale |

---

## 14. KPIs et Critères d'Acceptation

### 14.1 KPIs techniques

| Métrique | Actuel | Cible | Gate |
|----------|--------|-------|------|
| Couverture tests réelle | ~65-70% | ≥ 80% | CI bloquant |
| Vulnérabilités CRITICAL | 8 | 0 | Déploiement bloqué |
| Vulnérabilités HIGH | 12 | 0 | Déploiement bloqué |
| Images Docker pinnées | 3/8 | 8/8 | — |
| Latence API P95 | Non mesuré | < 500ms | Monitoring |
| Uptime | Non mesuré | ≥ 99.5% | Monitoring |
| HTTPS activé | Non | Oui | Obligatoire prod |

### 14.2 KPIs métier

| Métrique | Cible | Mesure |
|----------|-------|--------|
| Signaux générés/jour | ≥ 5 | Table `trading_signals` |
| Win rate signaux | > 55% | Table `signal_outcomes` |
| Confiance moyenne émise | 0.65-0.80 | Moyenne `confidence_score` |
| Cryptos couvertes | 13 prioritaires | Symboles uniques |
| Latence données vs exchange | < 5 min | Timestamp diff |
| Articles news/jour | ≥ 20 | Table `news_articles` |

### 14.3 Critères d'acceptation globaux

- [ ] Tous les 133 RF MUST passent leurs critères d'acceptation
- [ ] 0 vulnérabilité CRITICAL ou HIGH
- [ ] Couverture tests ≥ 80% sur chaque module
- [ ] CI/CD pipeline vert (lint + types + tests + build)
- [ ] HTTPS activé en production
- [ ] Backups quotidiens opérationnels
- [ ] Monitoring avec alertes configurées
- [ ] Documentation à jour (runbook, API docs, architecture)
- [ ] 5 pages frontend fonctionnelles
- [ ] Pipeline ML complet (collecte → signaux → affichage)

---

## 15. Glossaire

| Terme | Définition |
|-------|-----------|
| **OHLCV** | Open, High, Low, Close, Volume — données d'une bougie |
| **Hypertable** | Table TimescaleDB partitionnée automatiquement par temps |
| **Walk-forward** | Méthode de backtesting avec fenêtres glissantes (train → test → avance) |
| **Purging** | Suppression des données de training proches de la fenêtre de test pour éviter le leakage |
| **Embargo** | Période tampon entre train et test pour éviter le leakage temporel |
| **MoSCoW** | Priorisation : Must, Should, Could, Won't |
| **Rule Engine** | Moteur de règles explicites (Phase 1 ML) |
| **Confidence** | Score 0.0-1.0 mesurant la conviction d'un signal |
| **Signal** | Recommandation BUY/SELL/HOLD avec confiance, SL, TP |
| **Fear & Greed** | Index 0-100 mesurant le sentiment de marché |
| **RSI** | Relative Strength Index — oscillateur momentum |
| **Bollinger Bands** | Bandes de volatilité autour d'une moyenne mobile |
| **Harmonic Patterns** | Patterns géométriques basés sur les ratios de Fibonacci |
| **MLflow** | Plateforme de tracking d'expériences ML |
| **DVC** | Data Version Control — versionnement de datasets |
| **CCXT** | Librairie Python multi-exchange crypto |
| **APScheduler** | Scheduler Python pour jobs récurrents |
| **JWT** | JSON Web Token — mécanisme d'authentification stateless |
| **bcrypt** | Algorithme de hachage de mots de passe |
| **MinIO** | Object storage S3-compatible auto-hébergé |
| **Alembic** | Outil de migration de schéma SQLAlchemy |
| **CDC** | Cahier des Charges — ce document |

---

## 16. Livrables et Gouvernance

### 16.1 Livrables du projet

| # | Livrable | Format | Responsable |
|---|----------|--------|-------------|
| L1 | Pipeline ETL opérationnel | Code Python + Docker | Data Engineering |
| L2 | Moteur de règles (Phase 1) | Code Python | ML |
| L3 | Pipeline ML supervisé (Phase 2) | Code Python + MLflow | ML |
| L4 | API REST complète (26 endpoints) | FastAPI + Swagger | Backend |
| L5 | Frontend 5 pages | Streamlit + Plotly | Frontend |
| L6 | Infrastructure Docker + CI/CD | Compose + Actions + Ansible | DevOps |
| L7 | Documentation technique | Markdown (docs/) | Tous |
| L8 | Tests (unit + integration + E2E) | pytest, ≥80% coverage | Tous |
| L9 | Runbook de production | Markdown | DevOps |
| L10 | Audit de sécurité résolu | Rapport + fixes | Tous |

### 16.2 Règles de gouvernance

**Communication inter-équipes :**
- JAMAIS d'import cross-team direct (ETL ← API interdit)
- Toute communication via `src/shared/` (modèles Pydantic)
- API REST comme seul mécanisme d'échange frontend ↔ backend

**Qualité gates :**
- Tout merge vers `main` passe le CI complet
- Review par au moins 1 membre de l'équipe
- Aucun secret hardcodé (ruff S105/S106)
- Aucun `print()` (ruff T20)

**Conventions de code :**
- Type hints sur TOUTES les signatures
- `logging` module uniquement (pas de `print`)
- `pathlib.Path` uniquement (pas de `os.path`)
- Pydantic v2 pour tous les modèles de données
- Docstrings Google style sur les fonctions publiques

**Commits :**
- Format : `type(scope): description`
- Types : `feat`, `fix`, `refactor`, `test`, `docs`, `chore`
- Scopes : `etl`, `ml`, `api`, `frontend`, `infra`, `shared`

---

## 17. Annexes — Documents de Référence

| Document | Chemin | Contenu |
|----------|--------|---------|
| Audit technique | [`audit.md`](./audit.md) | Résultats de l'audit (B+, 39 issues) |
| Spécifications ETL + API | [`SPECIFICATIONS_FONCTIONNELLES.md`](./SPECIFICATIONS_FONCTIONNELLES.md) | 42 RF + 12 RNF détaillées |
| Spécifications ML & Analytics | [`.claude/specs/cdc-ml-analytics.md`](./.claude/specs/cdc-ml-analytics.md) | 26 RF ML avec pseudocode |
| Spécifications Frontend | [`.claude/specs/frontend-ui-cdc/01-requirements.md`](./.claude/specs/frontend-ui-cdc/01-requirements.md) | 53 RF UI avec wireframes |
| Architecture applicative | [`docs/06-architecture-applicative.md`](./docs/06-architecture-applicative.md) | Architecture logicielle complète |
| Architecture données | [`docs/data-architecture.md`](./docs/data-architecture.md) | TimescaleDB, MinIO, schémas DDL |
| Audit sécurité | [`SECURITY_AUDIT.md`](./SECURITY_AUDIT.md) | Vulnérabilités OWASP détaillées |
| Vue d'ensemble | [`docs/00-overview.md`](./docs/00-overview.md) | Vision produit |
| Roadmap | [`docs/06-roadmap.md`](./docs/06-roadmap.md) | Sprints et KPIs |

---

*Document généré par une équipe BMAD de 10 agents spécialisés (1 Master, 3 Analystes, 3 Product Managers, 3 Architectes)*
*Basé sur l'audit technique validé du 2026-03-12*
*Crypto Bot — Projet DTSC — 2026*
