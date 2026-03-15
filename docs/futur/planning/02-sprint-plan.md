# Plan de Sprints — CryptoBot S11-S16 (mars-juin 2026)

**Scrum Master**: BMAD Agent (Automated)
**Date**: 14 mars 2026
**Période**: S11-S16 (6 sprints × 2 semaines = 12 semaines)
**Soutenance**: juin 2026

---

## Résumé Exécutif

| Métrique | Valeur |
|----------|--------|
| **Portée totale** | 8 features, ~85 story points |
| **Durée estimée** | 6 sprints (12 semaines) |
| **Équipe** | 2 personnes (Jules = Data Eng, Mikael = Data Sci) |
| **Capacité par sprint** | ~15-20 points/sprint (10 j-h × 2 pers, facteur productivité 0.65) |
| **Vélocité cible** | 16 points/sprint (moyenne) |
| **Critères de succès** | Toutes features implémentées, tests ≥80%, démo fonctionnelle |

---

## Backlog Priorisé

### Légende Priorités
- **P0 (Critique)**: Bloquant pour soutenance, dépendances critiques
- **P1 (Haute)**: Valeur majeure, peu de dépendances
- **P2 (Moyenne)**: Valeur ajoutée, certaines dépendances
- **P3 (Basse)**: Nice-to-have, peut être réduit en Plan B

### Features Classées par Complexité et Dépendances

#### P0 — Quick Wins (Indépendants, à faire en premier)

| ID | Feature | Owner | Points | Jours Est. | Raison Priorité | Dépendances |
|----|---------| ------|--------|----------|-----------------|-------------|
| **F1** | Scraping réglementaire (BeautifulSoup) | Jules | **3** | 2-3j | Intégré système news existant, peu de risque | Aucune |
| **F2** | Sources ESMA/SEC RSS | Jules | **2** | 1-2j | Idem news.py, même pattern | Aucune |
| **F3** | Clustering K-Means non supervisé | Mikael | **3** | 2-3j | Analyse exploratory, indépendant | Aucune |

**Sous-total P0**: 8 points → ~1 sprint

#### P1 — Medium Effort (Dépendances légères)

| ID | Feature | Owner | Points | Jours Est. | Raison Priorité | Dépendances |
|----|---------| ------|--------|----------|-----------------|-------------|
| **F4** | Système d'alertes (SMTP + Telegram + in-app) | Jules | **5** | 3-4j | Requis signaux & news, demandes utilisateurs | Signal_generator OK |
| **F5** | Données on-chain (Blockchain.com API) | Jules | **5** | 3-4j | Enrichit marché data, indépendant | Aucune |
| **F6** | LSTM Deep Learning (PyTorch) | Mikael | **5** | 3-4j | Modèle supervisé Phase 2, indépendant | Data existantes |

**Sous-total P1**: 15 points → ~1.5 sprints

#### P2 — High Effort (Dépendances fortes)

| ID | Feature | Owner | Points | Jours Est. | Raison Priorité | Dépendances |
|----|---------| ------|--------|----------|-----------------|-------------|
| **F7** | Paper Trading Engine (modèle + API + UI) | Mikael + Jules | **13** | 5-6j | Nécessaire avant RL, value prod | Signals OK, API OK |
| **F8** | Reinforcement Learning (3 algos + env) | Mikael | **21** | 8-10j | Plus complexe, bloqué par F7 | Paper trading |

**Sous-total P2**: 34 points → ~2.5 sprints

---

## Détail des User Stories

### F1: Scraping Réglementaire (BeautifulSoup)

**Epic**: Data Enrichment
**Points**: 3 | **Owner**: Jules (Data Eng) | **Priorité**: P0

**User Story**:
En tant que Sarah (journaliste financière),
Je veux avoir accès aux documents réglementaires ESMA/SEC scrapés automatiquement,
Afin de suivre les évolutions légales du marché crypto.

**Acceptation Criteria**:
- [ ] Scraper BeautifulSoup pour ≥2 sources réglementaires (ESMA, SEC)
- [ ] Déduplication par URL + timestamp
- [ ] Insérer dans table `regulatory_documents`
- [ ] Validé avec Pydantic avant insert
- [ ] Tâche schedulée via APScheduler (2× quotidien)
- [ ] Logging des collectes avec timestamps
- [ ] Tests unitaires (mocks HTTP) ≥80%

**Tâches**:
1. **T1.1**: Concevoir modèle Pydantic `RegulatoryDocument` (1h)
2. **T1.2**: Implémenter `EsmaScraper` BeautifulSoup (6h)
3. **T1.3**: Implémenter `SecScraper` (6h)
4. **T1.4**: Ajouter migration Alembic pour table (2h)
5. **T1.5**: Intégrer dans `jobs.py` APScheduler (2h)
6. **T1.6**: Tests unitaires + mocks (4h)
7. **T1.7**: Documentation + logging (2h)

**Tech Notes**:
- Réutiliser pattern de `news_collector.py`
- Gérer rate-limits (1 req/sec min)
- Format URL validation avec `urllib.parse`
- Stockage texte brut + HTML backup dans MinIO

**Definition of Done**:
- [ ] Code mergé sur `data-eng/regulatory-scraper`
- [ ] `ruff check`, `mypy`, `pytest` passent
- [ ] Coverage ≥80%
- [ ] PR reviewée
- [ ] Logs vérifiés sur test data
- [ ] Doc team Data Eng mise à jour

---

### F2: Sources ESMA/SEC RSS

**Epic**: Data Enrichment
**Points**: 2 | **Owner**: Jules (Data Eng) | **Priorité**: P0

**User Story**:
En tant que Sarah,
Je veux recevoir des alertes RSS des régulateurs,
Afin de détecter les changeants légaux en quasi-temps réel.

**Acceptation Criteria**:
- [ ] Parser RSS ESMA + SEC (2 flux min par source)
- [ ] Dédupliqué par `guid` (clé RSS standard)
- [ ] Insérer dans `news_articles` avec label `source_type='regulatory'`
- [ ] Validé Pydantic
- [ ] Tâche schedulée (4× par jour)
- [ ] Tests ≥80%

**Tâches**:
1. **T2.1**: Ajouter feedparser dépendance + config (1h)
2. **T2.2**: Implémenter `RssFeedCollector` abstrait (3h)
3. **T2.3**: Sous-classes pour ESMA/SEC (2h)
4. **T2.4**: Intégrer dans jobs (1h)
5. **T2.5**: Tests + mocks (2h)

**Tech Notes**:
- Réutiliser interface `BaseCollector`
- Mécanisme retry (exponential backoff)
- Cache de 4h pour même URL

**Definition of Done**:
- [ ] Mergé sur `data-eng/rss-collector`
- [ ] Validations QA: ≥3 articles parsés par flux
- [ ] Aucun dupliqué en 24h
- [ ] Log disponibles pour debugging

---

### F3: Clustering K-Means Non Supervisé

**Epic**: ML Analytics
**Points**: 3 | **Owner**: Mikael (ML) | **Priorité**: P0

**User Story**:
En tant que Noah (trader),
Je veux voir les cryptos groupées par similarité de patterns,
Afin d'identifier des cohorts de comportement.

**Acceptation Criteria**:
- [ ] K-Means sur features existantes (RSI, Bollinger, volume, trend)
- [ ] K=3-5 clusters (auto-tuning silhouette score)
- [ ] Feature scaling (StandardScaler)
- [ ] Visualisation Plotly heatmap clusters
- [ ] Sauvegardé dans MinIO + MLflow
- [ ] Tests reproductibilité ≥80%

**Tâches**:
1. **T3.1**: Feature engineering (RSI, vol, trend features) (3h)
2. **T3.2**: Implémenter pipeline KMeans (4h)
3. **T3.3**: Tuning silhouette + elbow method (2h)
4. **T3.4**: Export MinIO + MLflow (2h)
5. **T3.5**: Tests determinisme + seeds (3h)
6. **T3.6**: Intégration frontend (chart cluster) (2h)

**Tech Notes**:
- Seed numpy fixe pour reproductibilité
- Features normalisées [-1, 1]
- Sortie: dict{symbol → cluster_id}
- Pipeline réexécutable quotidiennement

**Definition of Done**:
- [ ] Mergé `ml/clustering`
- [ ] Silhouette score ≥0.5
- [ ] Résultats stables jour-à-jour (±0 changements)
- [ ] Snapshot MLflow avec timestamp
- [ ] Chart Plotly fonctionnel en frontend

---

### F4: Système d'Alertes (SMTP + Telegram + In-App)

**Epic**: User Engagement
**Points**: 5 | **Owner**: Jules (Data Eng) | **Priorité**: P1

**User Story**:
En tant que Noah,
Je veux recevoir des alertes instantanées par email/Telegram quand un signal fort émerge,
Afin de ne pas rater les opportunités critiques.

**Acceptation Criteria**:
- [ ] Envoyer email SMTP (Gmail/Mailgun) on signal.confidence ≥ 0.7
- [ ] Envoyer Telegram webhook on même condition
- [ ] Insérer `UserAlert` en BDD (historique in-app)
- [ ] Dédupliquer (pas 2 alertes identiques < 5min)
- [ ] Configurable par utilisateur (canaux + seuils)
- [ ] Tests + mocks SMTP/Telegram ≥80%
- [ ] Logs audit (qui reçoit quoi quand)

**Tâches**:
1. **T4.1**: Modèle Pydantic `UserAlert` + `AlertPreference` (2h)
2. **T4.2**: Migration BDD 2 tables (1h)
3. **T4.3**: Service `EmailAlertService` (SMTP) (3h)
4. **T4.4**: Service `TelegramAlertService` (webhook) (3h)
5. **T4.5**: Orchestration via signal_generator (2h)
6. **T4.6**: Endpoint API GET `/api/alerts` + POST preferences (2h)
7. **T4.7**: Tests + mock requests (4h)
8. **T4.8**: Doc + env vars (1h)

**Tech Notes**:
- Réutiliser pattern service de src/api/services/
- Config SMTP/Telegram via env vars
- Retry logic (max 3 tentatives, backoff)
- Rate limit utilisateur (1 alert/min)

**Definition of Done**:
- [ ] Mergé `etl/alert-system`
- [ ] E2E test email + Telegram
- [ ] Vérification logs audit
- [ ] Coverage ≥80%
- [ ] Soutenance démo: envoyer alert en live

---

### F5: Données On-Chain (Blockchain.com API Gratuite)

**Epic**: Data Enrichment
**Points**: 5 | **Owner**: Jules (Data Eng) | **Priorité**: P1

**User Story**:
En tant que Noah,
Je veux accéder à des métriques on-chain (active addresses, tx volume, whale movements),
Afin d'enrichir mon analyse marché.

**Acceptation Criteria**:
- [ ] Collector pour Blockchain.com API gratuite
- [ ] Métriques: adresses actives, volume TX, whale wallets (top 100)
- [ ] Fréquence: quotidienne pour BTC/ETH
- [ ] Stockage MinIO (JSON snapshot) + TimescaleDB (agrégé)
- [ ] Validation données (cohérence jour-à-jour)
- [ ] Tests ≥80%

**Tâches**:
1. **T5.1**: Reconnaître API Blockchain.com (rate limits, endpoints) (2h)
2. **T5.2**: Implémenter `BlockchainComCollector` (4h)
3. **T5.3**: Modèles Pydantic on-chain metrics (2h)
4. **T5.4**: Migration BDD table `on_chain_metrics` (1h)
5. **T5.5**: Intégrer APScheduler (quotidien) (1h)
6. **T5.6**: Tests + mock HTTP (3h)
7. **T5.7**: Doc + env setup (1h)

**Tech Notes**:
- Free tier: ~50 req/h, batch requests
- Cache réponses 6h (données changeantes lentement)
- Gestion erreurs réseau (retry + skip)
- Feature pour ML: whale tx ratio

**Definition of Done**:
- [ ] Mergé `data-eng/blockchain-collector`
- [ ] Données quotidiennes collectées ≥7 jours
- [ ] Logs vérifiés
- [ ] Dashboard Plotly: whale activity chart

---

### F6: LSTM Deep Learning (PyTorch)

**Epic**: ML Models (Phase 2)
**Points**: 5 | **Owner**: Mikael (ML) | **Priorité**: P1

**User Story**:
En tant que Mikael (data scientist),
Je veux entraîner un modèle LSTM pour prédire les mouvements de prix à court terme,
Afin d'améliorer la precision des signaux par rapport aux règles.

**Acceptation Criteria**:
- [ ] Architecture: LSTM 1-2 couches → dense layer → classification (3 classes: BUY/SELL/HOLD)
- [ ] Input: séquence 48h d'indicateurs (1h bars)
- [ ] Train/val/test split temporal (70/15/15)
- [ ] Métrique: accuracy ≥65%, F1 ≥0.60 (par classe)
- [ ] Validation walk-forward (purging + embargo)
- [ ] Entraîné sur ≥100k samples (multi-crypto, multi-période)
- [ ] MLflow tracking (params, metrics, artifacts)
- [ ] Tests reproductibilité ≥80%

**Tâches**:
1. **T6.1**: Feature engineering 48h rolling window (4h)
2. **T6.2**: Préparation dataset (train/val/test temporal) (3h)
3. **T6.3**: Modèle LSTM architecture PyTorch (4h)
4. **T6.4**: Entraînement + validation (4h)
5. **T6.5**: MLflow tracking + hyperparameter tuning (2h)
6. **T6.6**: Tests reproductibilité + seed management (3h)
7. **T6.7**: Sauvegarde modèle + DVC (1h)
8. **T6.8**: Doc + notebook validation (2h)

**Tech Notes**:
- PyTorch: seed torch.manual_seed() + random.seed()
- DataLoader batch_size=32, shuffle=False (time series)
- Early stopping (patience=10 epochs)
- Sauvegarde best model à MinIO
- ONNX export pour inference rapide

**Definition of Done**:
- [ ] Mergé `ml/lstm-model`
- [ ] Notebook validation complet dans MLflow
- [ ] Metrics ≥seuil (65% acc, 0.60 F1)
- [ ] Tests pass
- [ ] Modèle prêt pour inference en prod

---

### F7: Paper Trading Engine (Modèle + API + Frontend)

**Epic**: Trading Simulation
**Points**: 13 | **Owner**: Mikael (lead) + Jules (support API) | **Priorité**: P2

**User Story**:
En tant que Noah,
Je veux simuler des trades basés sur les signaux générés sans risquer mon capital,
Afin de valider les stratégies avant trading réel.

**Acceptation Criteria**:
- [ ] Modèle `PaperTrade`: symbol, side, quantity, entry_price, stop_loss, take_profit, status, pnl
- [ ] Logique: place ordre → await signal exit → clôture auto (SL/TP/timeout)
- [ ] Portefeuille virtuel: balance initiale 10k USDT
- [ ] Calculs PnL: unrealized, realized, ROI %
- [ ] Journal de trades: historique complet exportable
- [ ] API endpoints: POST /paper-trades (new), GET /paper-trades (list), GET /portfolio (balance/positions)
- [ ] Plots Plotly: equity curve, drawdown, monthly returns
- [ ] Tests ≥80%

**Sous-Tâches**:

**Phase 1: Modèle & BDD (Mikael, 4j)**
1. **T7.1**: Modèle Pydantic + ORM `PaperTrade` (2h)
2. **T7.2**: Migration Alembic table + constraints (1h)
3. **T7.3**: Logique clôture: SL/TP/timeout (3h)
4. **T7.4**: Calcul PnL + portfolio (2h)
5. **T7.5**: Tests modèle ≥80% (3h)

**Phase 2: API (Jules, 2j)**
6. **T7.6**: Service `PaperTradeService` (3h)
7. **T7.7**: Routers: POST/GET /paper-trades, GET /portfolio (2h)
8. **T7.8**: Tests API (2h)

**Phase 3: Frontend (Mikael, 2j)**
9. **T7.9**: Page Streamlit `/portfolio` (trades actifs + historique) (3h)
10. **T7.10**: Charts equity, drawdown, monthly (3h)
11. **T7.11**: Tests Streamlit (1h)

**Tech Notes**:
- Clôture automatique: job APScheduler (check SL/TP toutes les 15min)
- Pas de slippage (prix signal = prix exécution)
- Multi-user: chacun sa balance
- Export CSV trades

**Definition of Done**:
- [ ] Mergé `ml/paper-trading` (modèle) + `api/paper-trading` (API) + branche frontend
- [ ] E2E: placer trade → vérifier clôture SL/TP
- [ ] Coverage ≥80%
- [ ] Démo soutenance: portefeuille vivant

---

### F8: Reinforcement Learning (3 Algos + Env)

**Epic**: Advanced ML
**Points**: 21 | **Owner**: Mikael (ML) | **Priorité**: P2

**User Story**:
En tant que Mikael,
Je veux entraîner des agents RL pour optimiser la stratégie de trading via apprentissage,
Afin de produire une stratégie adaptive et data-driven.

**Acceptation Criteria**:
- [ ] Environnement Gym custom: état (OHLCV + indicators), actions (BUY/SELL/HOLD), récompense (PnL % hourly)
- [ ] Agents: DQN + PPO + Random Baseline
- [ ] Entraînement: ≥100k steps par agent
- [ ] Validation: Sharpe ratio ≥1.0, win rate ≥55%, max drawdown ≤20%
- [ ] Convergence: loss décroissant, reward croissant (plot MLflow)
- [ ] Sauvegarde checkpoints + modèles
- [ ] Tests reproductibilité ≥80%

**Sous-Tâches**:

**Phase 1: Environnement (Mikael, 3j)**
1. **T8.1**: Design espace état/action/récompense (2h)
2. **T8.2**: Implémenter `TradingEnv` (Gym/Gymnasium) (4h)
3. **T8.3**: Normalisation état (2h)
4. **T8.4**: Tests env (action sampling, step logic) (2h)

**Phase 2: Agents (Mikael, 4j)**
5. **T8.5**: DQN (stable-baselines3) (5h)
   - Réseau Q-network, replay buffer, epsilon-greedy
   - Paramètres: learning_rate, gamma, epsilon decay
6. **T8.6**: PPO (stable-baselines3) (5h)
   - Actor-critic, GAE, clipped objective
   - Paramètres: learning_rate, n_steps, batch_size
7. **T8.7**: Baseline Random policy (1h)
8. **T8.8**: Hyperparameter search grid (2h)

**Phase 3: Training & Validation (Mikael, 2j)**
9. **T8.9**: Pipeline entraînement: data loading, train loop (3h)
10. **T8.10**: Logging MLflow (params, rewards, Sharpe, drawdown) (2h)
11. **T8.11**: Walk-forward backtesting (données hold-out) (3h)
12. **T8.12**: Comparaison vs stratégies baseline (1h)

**Phase 4: Integration & Testing (Mikael, 1j)**
13. **T8.13**: Sérialisation modèles (ONNX / .pt) (1h)
14. **T8.14**: Tests reproductibilité (seed, determinism) (2h)
15. **T8.15**: Doc + notebooks explications (2h)

**Tech Notes**:
- Gym: state shape (48, n_features), action shape (3,)
- Récompense: daily_pnl_pct - 0.01 * transaction_cost
- DQN: epsilon start=1.0, decay=0.995, final=0.01
- PPO: n_steps=2048, batch_size=64, n_epochs=10
- Entraînement: 100k-500k steps (peut être long, plan parallèle)
- Validation hold-out: ≥30k steps non entraînés

**Definition of Done**:
- [ ] Mergé `ml/rl-training`
- [ ] Tous agents converges (loss ↓, reward ↑)
- [ ] Validation metrics passent
- [ ] MLflow dashboard avec comparaison agents
- [ ] Checkpoints sauvegardés MinIO
- [ ] Tests ≥80%
- [ ] Démo soutenance: agent trading en live

---

## Plan de Sprints Détaillé

### Macro Timeline

```
Sprint 11 (14-28 mars)   → Quick wins (F1, F2, F3)
Sprint 12 (29 mars-12 av) → F4, F5 (medium)
Sprint 13 (13-27 avril)   → F6, début F7
Sprint 14 (28 avr-12 mai) → F7 (fin) + tests intégration
Sprint 15 (13-27 mai)     → F8 phase 1-2 (env + agents)
Sprint 16 (28 mai-11 juin)→ F8 phase 3-4 + polish + soutenance
```

---

### Sprint 11 (14-28 Mars 2026) — Quick Wins Foundation

**Objectif Sprint**: Établir base solide avec 3 quick wins indépendants, zéro dépendances critiques.

**Vélocité Planifiée**: 8 points | **Charge**: ~6j-h | **Risque**: Bas

#### User Stories Assignées

| ID | Title | Owner | Points | Status |
|----|-------|-------|--------|--------|
| F1 | Scraping Réglementaire | Jules | 3 | Committed |
| F2 | Sources RSS ESMA/SEC | Jules | 2 | Committed |
| F3 | Clustering K-Means | Mikael | 3 | Committed |

#### Tâches Détaillées (par ordre priorité)

**Jules — F1 & F2 (5 jours)**
- T1.1-1.7: Scraper ESMA/SEC (6 + 4 tests = 10h)
- T2.1-2.5: RSS parser (3 + 2 tests = 5h)
- Code review + merge: 1h
- **Total**: 16h (~2 jours)

**Mikael — F3 (3 jours)**
- T3.1-3.6: KMeans pipeline + frontend (20h)
- **Total**: 20h (~2.5 jours)

#### Risques Sprint 11

| Risque | Probabilité | Mitigation |
|--------|-------------|-----------|
| Taux de change API Blockchain.com gratuit rate-limit | M | Utiliser BeautifulSoup + local fallback |
| Parsing BeautifulSoup fragile aux changements HTML | M | Tests sur ≥2 snapshots HTML en fixtures |
| KMeans silhouette bas (<0.4) | L | Ajouter PCA ou normalisation |

#### Livrables Sprint 11

- [ ] MR mergé: `data-eng/regulatory-scraper`
- [ ] MR mergé: `data-eng/rss-collector`
- [ ] MR mergé: `ml/clustering`
- [ ] Coverage ≥80% (toutes 3 features)
- [ ] Logs validés: ≥1 document scrappé, ≥2 RSS parsés, clusters stables
- [ ] Doc teams mises à jour

#### Démo Sprint 11
- Afficher documents réglementaires scrapés dans Streamlit
- RSS ESMA/SEC dans feeds d'alertes
- Heatmap clusters cryptos

---

### Sprint 12 (29 Mars - 12 Avril 2026) — Medium Effort (Alertes + On-Chain)

**Objectif Sprint**: Ajouter alertes utilisateurs et enrichissement données on-chain.

**Vélocité Planifiée**: 10 points | **Charge**: ~7.5j-h | **Risque**: Moyen

#### User Stories Assignées

| ID | Title | Owner | Points | Status |
|----|-------|-------|--------|--------|
| F4 | Alertes SMTP/Telegram | Jules | 5 | Committed |
| F5 | On-Chain Blockchain.com | Jules | 5 | Committed |

#### Tâches Détaillées

**Jules (10 jours)**
- T4.1-4.8: Système alertes (15h)
- T5.1-5.7: Blockchain collector (15h)
- Intégration + tests: 5h
- **Total**: 35h (~4-5 jours)

#### Dépendances
- F4 dépend de: signal_generator (déjà en place ✓)
- F5 indépendant

#### Risques Sprint 12

| Risque | Mitigation |
|--------|-----------|
| Throttling SMTP (Gmail) | Utiliser Mailgun (free tier) ou queue async |
| Webhook Telegram en retard | Timeout 5s, queue asynchrone, retry 3x |
| Blockchain.com API gratuit insuffisant | Fallback local cache + polling 1× par jour |

#### Livrables Sprint 12

- [ ] MR mergé: `etl/alert-system`
- [ ] MR mergé: `data-eng/blockchain-collector`
- [ ] Tests E2E: envoyer alerte en live (Gmail + Telegram)
- [ ] Coverage ≥80%
- [ ] Dashboard alertes en Streamlit

---

### Sprint 13 (13-27 Avril 2026) — ML Phase 2 Start (LSTM + Paper Trading Phase 1)

**Objectif Sprint**: Lancer modèles supervisés (LSTM) et infrastructure paper trading.

**Vélocité Planifiée**: 18 points | **Charge**: ~11j-h | **Risque**: Moyen-Haut

#### User Stories Assignées

| ID | Title | Owner | Points | Status |
|----|-------|-------|--------|--------|
| F6 | LSTM Deep Learning | Mikael | 5 | Committed |
| F7.1 | Paper Trading (modèle + BDD) | Mikael | 6 | Committed |
| F7.2 | Paper Trading (API) | Jules | 4 | Committed |

#### Tâches Détaillées

**Mikael (7 jours)**
- T6.1-6.8: LSTM train + validation (23h)
- T7.1-7.5: Paper trading model (12h)
- **Total**: 35h (~4.5 jours)

**Jules (3 jours)**
- T7.6-7.8: Paper trading API (7h)
- Support intégration: 2h
- **Total**: 9h (~1 jour)

#### Dépendances
- F7.1 indépendant
- F7.2 bloqué par T7.1-7.4 (modèle + BDD)
- F6 indépendant

#### Risques Sprint 13

| Risque | Mitigation |
|--------|-----------|
| Entraînement LSTM long (>4h par itération) | Runner GPU if available, sinon CPU parallèle |
| LSTM accuracy <65% | Réduire scope: baseline simple 2-couches, hyperparameter tuning |
| Paper trading clôture complexe | Simplifier: clôture sur SL/TP seulement (pas timeout) |

#### Livrables Sprint 13

- [ ] MR mergé: `ml/lstm-model` (notebook + MLflow)
- [ ] MR mergé: `ml/paper-trading-model` + `api/paper-trading-api`
- [ ] Accuracy LSTM ≥65%, F1 ≥0.60
- [ ] Coverage ≥80%
- [ ] Portefeuille paper trading fonctionnel (balance + calcul PnL)

---

### Sprint 14 (28 Avril - 12 Mai 2026) — Paper Trading Frontend + Integration

**Objectif Sprint**: Compléter paper trading et valider intégrations, préparation RL.

**Vélocité Planifiée**: 16 points | **Charge**: ~10j-h | **Risque**: Moyen

#### User Stories Assignées

| ID | Title | Owner | Points | Status |
|----|-------|-------|--------|--------|
| F7.3 | Paper Trading (Frontend) | Mikael | 4 | Committed |
| (Buffer) | Intégration + tests E2E + buffer | Jules + Mikael | 6 | Committed |
| (Refactor) | Optimisations, documentation | Jules + Mikael | 6 | Committed |

#### Tâches Détaillées

**Mikael (4 jours)**
- T7.9-7.11: Frontend Streamlit (7h)
- Tests Streamlit + fixes (3h)
- **Total**: 10h (~1.5 jours)

**Jules + Mikael (6 jours)**
- Intégration signals → paper trades (3h)
- Tests E2E complets (5h)
- Documentation + logging (3h)
- Optimisations perf (2h)
- **Total**: 13h (~2 jours)

#### Risques Sprint 14

| Risque | Mitigation |
|--------|-----------|
| Calcul PnL incorrect (edge cases) | Tests unitaires exhaustifs (long/short, SL/TP) |
| Page Streamlit lente (100+ trades) | Pagination, cache, queries optimisées |
| Bugs intégration signal → trade | Logs détaillés, tests E2E avec données réelles |

#### Livrables Sprint 14

- [ ] MR mergé: `frontend/paper-trading`
- [ ] Intégration validée: signal → auto-trade
- [ ] E2E test: placer order → vérifier clôture
- [ ] Dashboard paper trading complet (equity curve, trades, stats)
- [ ] Coverage global ≥80%

---

### Sprint 15 (13-27 Mai 2026) — RL Phase 1-2 (Environment + Agents)

**Objectif Sprint**: Implémenter environnement RL et deux agents (DQN + PPO).

**Vélocité Planifiée**: 18 points | **Charge**: ~11j-h | **Risque**: Haut

#### User Stories Assignées

| ID | Title | Owner | Points | Status |
|----|-------|-------|--------|--------|
| F8.1-2 | RL Env + DQN | Mikael | 10 | Committed |
| F8.3-4 | RL PPO + baseline | Mikael | 8 | Committed |

#### Tâches Détaillées (Parallel Path)

**Mikael (10-11 jours)**
- T8.1-8.4: Env design + tests (10h)
- T8.5: DQN training + tuning (5h)
- T8.6: PPO training + tuning (5h)
- T8.7: Baseline random (1h)
- T8.8: Hyperparameter grid search (2h)
- **Total**: 23h (~3 jours en parallèle)

**Goulot**: Entraînement long (peut tourner 24h). Stratégie: lancer agents en parallèle (GPU/CPU threads).

#### Risques Sprint 15 (CRITIQUES)

| Risque | Probabilité | Mitigation |
|--------|-------------|-----------|
| Agents ne convergent pas (loss reste haut) | H | Réduire scope: 1 agent seulement (DQN), simplifier env |
| Entraînement >72h non fini | M | Commencer S15-1 (debut semaine), laisser tourner 48h |
| Out of memory GPU (si disponible) | L | Réduire batch_size, utiliser CPU |
| Validation metrics <seuil (Sharpe <1.0) | M | Ajuster reward function, ajouter penalty, tuning hyperparams |

#### Livrables Sprint 15 (Minimum)

- [ ] MR mergé: `ml/rl-env` (environnement stable)
- [ ] MR mergé: `ml/rl-agents` (DQN + PPO)
- [ ] Agents convergent (loss ↓ sur 100k+ steps)
- [ ] MLflow tracking complet
- [ ] Coverage tests ≥70% (may relax to 70% due to complexity)

---

### Sprint 16 (28 Mai - 11 Juin 2026) — RL Validation + Final Polish + Soutenance

**Objectif Sprint**: Finaliser RL, valider tout, préparer démo soutenance.

**Vélocité Planifiée**: 15 points | **Charge**: ~9j-h | **Risque**: Moyen

#### User Stories Assignées

| ID | Title | Owner | Points | Status |
|----|-------|-------|--------|--------|
| F8.3-4 | RL Validation + comparaison | Mikael | 5 | Committed |
| (Polish) | Bug fixes, doc finale, déploiement | Jules + Mikael | 10 | Committed |

#### Tâches Détaillées

**Mikael (3 jours)**
- T8.9-8.15: Walk-forward validation, integration (10h)
- Comparaison agents vs baseline (2h)
- MLflow dashboard (1h)
- **Total**: 13h (~2 jours)

**Jules + Mikael (4 jours)**
- Bug fixes finaux (4h)
- Documentation complète (3h)
- Test final sur data 2026 Q1 (2h)
- Preparation démo soutenance (2h)
- Déploiement staging (1h)
- **Total**: 12h (~1.5 jours)

#### Risques Sprint 16 (Final)

| Risque | Mitigation |
|--------|-----------|
| RL agents encore en training | Utiliser checkpoints intermédiaires, résultats partiels OK pour démo |
| Bugs critiques détectés | Freeze features, fix bugs uniquement |
| Performance déploiement | Test local avant staging, optimiser queries |

#### Livrables Sprint 16 (GO/NOGO)

**CRITICAL for Soutenance**:
- [ ] Tous MRs mergés + tests passent
- [ ] Coverage global ≥80%
- [ ] CI/CD pipeline vert
- [ ] Déploiement staging OK
- [ ] Démo live: signals + alerts + paper trading + RL agents
- [ ] Documentation complète
- [ ] README soutenance

---

## Chemin Critique et Dépendances

### DAG (Directed Acyclic Graph)

```
F1, F2, F3 (P0 indépendants)
    ↓
F4, F5 (P1, dépendent de signaux ok)
    ↓
    ├─→ F6 (LSTM, indépendant)
    └─→ F7.1 (Paper Trading modèle, indépendant)
        ↓
        F7.2 (Paper Trading API)
        ↓
        F7.3 (Paper Trading UI)
        ↓
        F8 (RL, BLOQUÉ par F7)
```

### Chemin Critique

```
S11: F1, F2, F3 ✓
S12: F4, F5 ✓
S13: F6 ✓, F7.1-2 ✓
S14: F7.3, intégration ✓
S15-S16: F8 (CRITIQUE PATH) — Dépend de tout précédent
```

**Slack time**:
- F1, F2, F3, F4, F5: peuvent être retardés de 1 sprint max sans impact
- F6: peut être retardé de 1 sprint (LSTM est optionnel pour MVP)
- F7: critique (RL dépend de paper trading)
- F8: doit commencer S15 au plus tard

---

## Stratégie Plan B (Risk Mitigation)

Si RL est trop complexe ou prend trop de temps:

### Plan B-1: RL réduit (Scope Reduction)
- Keep DQN only (drop PPO)
- Simplify action space: BUY / HOLD only (no SELL)
- Reduce training steps: 50k instead of 100k
- **Impact**: -8 points, -2 days, -2 sprints → faisable S15 seul

### Plan B-2: RL removed (Scope Cut)
- Skip F8 entirely
- Focus on paper trading + LSTM as final ML
- **Impact**: -21 points, 1 full sprint freed
- **Presentation**: "Phase 1 ML + simulation ready, RL future work"
- **Go-live**: S15 au lieu de S16, buffer 1 semaine

### Plan B-3: Simplifications rapides
- Remove on-chain (F5) if time constraint → F5 = 5 points saved
- Remove clustering (F3) → keep in S11 mais deprioritize
- Remove regulatory scraping → simple RSS only (F2 enough)

**Recommendation**: Plan B-1 est le bon compromis. RL simplifié (DQN only) produit valeur.

---

## Velocity Tracking & Metrics

### Mesures Chaque Sprint

| Métrique | Cible | Calcul |
|----------|-------|--------|
| **Velocity actuelle** | 16-18 pts | Points stories fermées |
| **Sprint goal completion** | ≥90% | (Committed - Not Done) / Committed |
| **Coverage** | ≥80% | pytest --cov=src |
| **Build success** | 100% | CI/CD pass rate |
| **Code review turnaround** | <24h | (Merge time - PR creation) |

### Burndown Chart (Template par Sprint)

```
Points restants
      |
   20 +
      | ▲  Ideal trend
      |  \
   15 +   \  Actual (example)
      |    \
   10 +     \
      |      \
    5 +       \___
      |           \___
    0 +________________

      Mon Tue Wed Thu Fri

Target: Points → 0 by Friday EOD
```

### Rétrospective Format

**Toutes les 2 semaines (vendredi 16:00)**:
- Velocity: points prévus vs réalisés
- Blockers: _____
- Apprentissages: _____
- Ajustements S+1: _____

### Indicateurs d'Alerte

- Velocity < 12 pts (3 sprints de suite) → ajuster team capacity
- MRs outstanding > 5 → review bottleneck
- Coverage chute < 75% → enforce TDD
- CI failures > 2/jour → prioritize fixes

---

## Tests et Qualité Globale

### Stratégie QA par Type

| Type | Exemple | Owner | Fréquence |
|------|---------|-------|-----------|
| **Unit** | test_rsi_calculation | Dev (Mikael/Jules) | À chaque commit |
| **Integration** | test_signal_insertion_to_db | Dev (Mikael/Jules) | Avant MR |
| **E2E** | test_alert_sent_on_signal_trigger | QA / Dev | End sprint |
| **Load** | test_api_1k_req/s | DevOps | Sprint 14+ |

### Coverage Gates

```bash
# Before commit
ruff check src/ --fix && ruff format src/ && mypy src/ --strict
pytest tests/ --cov=src --cov-fail-under=80 --cov-report=html

# CI/CD enforces
- Exit 1 if coverage < 78%
- Exit 1 if ruff fails
- Exit 1 if mypy fails
```

### Test Pyramid (Approx Distribution)

- **Unit tests**: 60% (logique métier pure)
- **Integration tests**: 30% (BDD, services, APIs)
- **E2E tests**: 10% (user flows critiques)

---

## Documentation et Onboarding

### Docs à produire (par équipe)

| Doc | Owner | Sprint | Format |
|-----|-------|--------|--------|
| F1-F5 README | Jules | S11-S12 | .md dans src/etl/ |
| F6 Notebook validation LSTM | Mikael | S13 | .ipynb |
| F7 Paper trading guide | Mikael + Jules | S14 | .md + API schema |
| F8 RL env + agents guide | Mikael | S15-S16 | .md + notebook |
| Soutenance runbook | Jules + Mikael | S16 | .md + screenshots |

### Checklist Soutenance (S16 EOD)

- [ ] Tous tests passent (CI vert)
- [ ] Coverage ≥80%
- [ ] Déploiement staging OK
- [ ] Démo préparée (scripts, data snapshots)
- [ ] README et docs complets
- [ ] Video walkthrough enregistrée (fallback)
- [ ] Profs avertis: "Ready to present"

---

## Assumptions et Contraintes

### Assumptions

1. **Équipe**: 2 personnes (Jules + Mikael), temps partiel (~25h/semaine chacun)
2. **Infrastructure**: Docker Compose + TimescaleDB + MinIO déjà running
3. **Code baseline**: Signal generator + rule engine + API + frontend déjà en place
4. **Données**: OHLCV + indicators + news collectées quotidiennement
5. **GPU**: Optionnel (CPU suffisant pour LSTM, RL moins rapide mais ok)

### Contraintes

- Pas de changements architecture majeurs (pas Kubernetes, pas new BDD)
- Pas de nouvelles données payantes (free sources only)
- Pas de 24/7 sur-appel (projet école)
- Soutenance fixée juin 2026 (immovable deadline)

### Dépendances Externes

- API Blockchain.com: uptime ≥99%, sinon fallback local cache
- Gmail/Mailgun SMTP: uptime ≥95%
- Telegram webhook: uptime ≥95%

---

## Recommendations Finales

### Pour les Développeurs

1. **Sprint 11-12**: Focus sur quick wins, build momentum
2. **Sprint 13-14**: Paper trading est clé (RL en dépend)
3. **Sprint 15**: Lancer RL tôt, laisser tourner 48h en parallèle
4. **Sprint 16**: Polish + démo, pas de nouvelles features

### Pour le Product Owner

- Prioriser **paper trading** (F7) — plus important que on-chain (F5)
- Si push vient: couper on-chain ou clustering plutôt que RL
- Valider business value: alertes (F4) très apprécié, clustering (F3) nice-to-have

### Pour Stakeholders

- **MVP (S14)**: Signaux + alertes + paper trading = produit utilisable
- **Full (S16)**: + LSTM + RL agents = advanced analytics
- **Timeline**: Réaliste 6 sprints, 12 semaines, fin juin ✓
- **Risk**: RL peut être réduit (Plan B) si temps serré

---

## Annexe: Fibonacci Estimation Rationalisée

| Points | Effort | Exemple |
|--------|--------|---------|
| **1** | <1h | Config, docs |
| **2** | 1-2h | Simple collector, model training |
| **3** | 2-3h | Scrapers, basic ML (clustering) |
| **5** | 3-5h | Medium feature (alerts, on-chain) |
| **8** | 5-8h | Complex feature (LSTM), API layer |
| **13** | 8-13h | Very complex (paper trading) |
| **21** | 13-21h | Epic level (RL agents + env) |

**Total Backlog**: 8+2+3+5+5+5+13+21 = **62 points** (non-F7 split)

Ajustement pour dépendances et intégration: **85 points** (comptant F7 split = 6+4+4=14 au lieu de 13).

---

**Document Version**: 1.0
**Auteur**: BMAD Scrum Master (Automated)
**Basé sur**: CLAUDE.md v1.0, Codebase analysis 2026-03-14
**Prochain review**: S11 Fin (28 mars)
