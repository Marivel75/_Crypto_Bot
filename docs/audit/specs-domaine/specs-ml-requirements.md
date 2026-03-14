# Cahier des Charges — Module ML/Data Science

**Version :** 2.0  
**Date :** 2026-03-12  
**Périmètre :** `src/ml/` — Équipe ML/Data Science  
**Responsable :** PM ML + Analyst ML  
**Audience :** Équipes (Dev, Testing, DevOps, Frontend), Stakeholders, Auditeurs

---

## Executive Summary

Le module ML/Data Science Crypto Bot est une plateforme intelligente deux-phases qui génère des **signaux de trading informatifs** (JAMAIS d'exécution automatisée) basés sur l'analyse technique multi-timeframes et l'apprentissage supervisé.

### Architecture ML

```
Phase 1 : Rule Engine (v1)
├── RSI convergence multi-TF (1h, 2h, 3h, 4h)
├── Bollinger Bands (squeeze + band walking)
├── Harmonic Patterns (Gartley, Butterfly, Bat, Crab)
├── Trend Lines (weekly stable, monthly aggressive)
└── Output: TradingSignal (confidence ≥ 0.6) → TimescaleDB

Phase 2 : Supervised ML (v2+)
├── Features: indicators + convergence + volatility + sentiment
├── Models: XGBoost, LightGBM, LSTM (walk-forward validation)
├── MLflow: experiment tracking, model registry
├── DVC: dataset versioning (MinIO remote)
└── Output: optimized thresholds + ensemble predictions
```

### Principes Fondamentaux

1. **Aucun data leakage** — Split temporel strict, jamais aléatoire
2. **Seuil de confiance** — Signaux émis si confidence ≥ 0.6 uniquement
3. **Vérification marge** — Ratio 2x de marge libre obligatoire (doc §4.3)
4. **Transparence** — Chaque signal trace les règles déclenchées
5. **Reproducibilité** — Seeds déterministes, config YAML externalisée

---

## 1. Exigences Fonctionnelles — Phase 1 (Rule Engine)

### RF-ML-001 — Chargement Configuration Indicateurs

**Priorité :** MUST  
**Description :** Le système charge une configuration YAML centralisée (`src/ml/config/indicators.yaml`) contenant les seuils, les timeframes et les poids de chaque indicateur.

**Acceptation :**
- [ ] Fichier `indicators.yaml` existe et est parsé sans erreur
- [ ] Contient sections : `rsi`, `bollinger`, `harmonic`, `trend`, `multi_tf`
- [ ] Chaque section définit : `enabled`, `timeframes`, `thresholds` (overbought, oversold, etc.)
- [ ] Changement de config ne demande pas redéploiement (chargé à runtime)
- [ ] Logs indiquent le chemin et la date du chargement

**Dépendances :** Aucune  
**Fichiers associés :** `src/ml/rules/engine.py`, `src/ml/config/indicators.yaml`

---

### RF-ML-002 — Rule Engine : RSI Multi-Timeframe

**Priorité :** MUST  
**Description :** Le rule engine détecte la convergence RSI sur timeframes adjacentes (1h, 2h, 3h, 4h) et émet des signaux overbought/oversold.

**Spécification RSI :**
- Timeframes : 1h, 2h, 3h, 4h (configurable)
- Overbought (par défaut) : RSI > 70
- Oversold (par défaut) : RSI < 30
- Convergence : au moins 2 TF adjacentes en surachat/survente
- Output : `RuleResult` avec `direction` (BUY/SELL), `confidence`, `reason`

**Acceptation :**
- [ ] `evaluate_rsi(symbol, indicators, config)` retourne `RuleResult | None`
- [ ] Teste convergence sur toutes les paires de TF adjacentes
- [ ] Confidence augmente si > 2 TF en convergence (max 1.0)
- [ ] Logs tracent chaque évaluation RSI (symbol, TF, valeur, convergence)
- [ ] Tests unitaires couvrent : overbought, oversold, pas de convergence, TF manquante

**Dépendances :** RF-ML-001  
**Fichiers associés :** `src/ml/rules/rsi_rules.py`, `tests/unit/test_rsi_rules.py`

---

### RF-ML-003 — Rule Engine : Bollinger Bands

**Priorité :** MUST  
**Description :** Détecte squeeze (resserrement bandes) et band walking (prix walk les bandes).

**Spécification Bollinger :**
- Période (par défaut) : 20 candles, 2σ
- Squeeze : écart bandes < 1% du prix moyen
- Band walking : prix > bande haute 3+ fois consécutives (BUY), ou < bande basse (SELL)
- Output : `RuleResult` avec raison (squeeze_detected, band_walking_up, etc.)

**Acceptation :**
- [ ] `evaluate_bollinger(symbol, indicators, config)` retourne `RuleResult | None`
- [ ] Détecte squeeze avec seuil configurable
- [ ] Identifie band walking sur min. 3 candles
- [ ] Confidence 0.7 pour squeeze, 0.8 pour band walking
- [ ] Tests : squeeze vide, pas de bandes, band walking incomplet

**Dépendances :** RF-ML-001  
**Fichiers associés :** `src/ml/rules/bollinger_rules.py`, `tests/unit/test_bollinger_rules.py`

---

### RF-ML-004 — Rule Engine : Harmonic Patterns

**Priorité :** SHOULD  
**Description :** Détecte patterns harmoniques (Gartley, Butterfly, Bat, Crab) sur les trend lines.

**Spécification :**
- Patterns : Gartley (0.618, 0.786), Butterfly (1.27), Bat (0.5, 0.886), Crab (1.618)
- Points : X, A, B, C, D définis par trend lines locales
- Confiance : basée sur la précision du ratio (±2%)
- Output : `RuleResult` avec nom du pattern, ratio de précision

**Acceptation :**
- [ ] `evaluate_harmonic(symbol, indicators, config)` retourne `RuleResult | None`
- [ ] Identifie ≥ 3 patterns harmoniques (Gartley, Butterfly, Bat)
- [ ] Calcule les ratios Fibonacci pour chaque pattern
- [ ] Confiance : 0.7 si ratio ±2%, 0.85 si ±1%
- [ ] Tests : pattern complet, pattern incomplet, ratio hors tolérance
- [ ] Lien vers harmonic_rules.py

**Dépendances :** RF-ML-001, RF-ML-006  
**Fichiers associés :** `src/ml/rules/harmonic_rules.py`, `tests/unit/test_harmonic_rules.py`

---

### RF-ML-005 — Rule Engine : Trend Lines (Weekly/Monthly)

**Priorité :** SHOULD  
**Description :** Analyse les trend lines à timeframes grandes (1W, 1M) pour identifier la tendance stable vs agressive.

**Spécification :**
- Weekly trend : régression linéaire sur 13 semaines (stable)
- Monthly trend : régression linéaire sur 6 mois (agressive)
- Dips significatifs : retrace < 50% de la pente hebdomadaire → achat
- Output : `RuleResult` avec pente, confiance basée sur R²

**Acceptation :**
- [ ] `evaluate_trend(symbol, indicators, config)` retourne `RuleResult | None`
- [ ] Calcule pente weekly et monthly via régression
- [ ] Détecte dips > 2% avec confiance ajustée R²
- [ ] Tests : trend haussière, baissière, sideway, données manquantes

**Dépendances :** RF-ML-001  
**Fichiers associés :** `src/ml/rules/trend_rules.py`, `tests/unit/test_trend_rules.py`

---

### RF-ML-006 — Rule Engine : Multi-Timeframe Alignment

**Priorité :** MUST  
**Description :** Vérifie l'alignement des signaux à travers plusieurs TF (multi-TF alignment) pour augmenter la confiance.

**Spécification :**
- Alignment : min. 3 TF adjacentes émettent la même direction (BUY ou SELL)
- Supermajority : > 50% des TF en convergence
- Weight : chaque TF contribution pondérée (4h > 1h)
- Output : `list[RuleResult]` si alignment détecté

**Acceptation :**
- [ ] `evaluate_multi_tf_alignment(indicators_snapshot, config)` retourne `list[RuleResult]`
- [ ] Vérifie ≥ 3 TF en convergence pour émettre
- [ ] Confidence = min(1.0, nombre_TF_alignées / 4)
- [ ] Logs tracent la composition TF
- [ ] Tests : 0 TF, 2 TF (non-émission), 4 TF, direction mixte

**Dépendances :** RF-ML-001, RF-ML-002, RF-ML-003  
**Fichiers associés :** `src/ml/rules/multi_tf_rules.py`, `tests/unit/test_multi_tf_rules.py`

---

### RF-ML-007 — Rule Engine Aggregation

**Priorité :** MUST  
**Description :** Agrège tous les RuleResult en un unique TradingSignal via voting pondéré.

**Spécification :**
- Poids : RSI 0.25, Bollinger 0.25, Harmonic 0.30, Trend 0.20
- Direction dominante : max(score_BUY, score_SELL)
- Pénalité opposition : si 2 directions reçoivent votes, réduire confiance de 50% × opposition_ratio
- Emission : confiance finale ≥ 0.6 uniquement
- Output : `TradingSignal` ou `None`

**Acceptation :**
- [ ] `aggregate(results, symbol)` retourne `TradingSignal | None`
- [ ] Calcule score pondéré par direction
- [ ] Applique pénalité opposition
- [ ] Retourne `None` si confiance < 0.6
- [ ] Logs indiquent : direction, confiance, règles déclenchées, raison du rejet
- [ ] Tests : 0 résultat, 1 résultat, direction mixte, confiance limite

**Dépendances :** RF-ML-001 à RF-ML-006  
**Fichiers associés :** `src/ml/rules/engine.py`, `tests/unit/test_rule_engine_aggregation.py`

---

## 2. Exigences Fonctionnelles — Feature Engineering & Training

### RF-ML-008 — Feature Engineering

**Priorité :** MUST  
**Description :** Construit une matrice de features pour l'entraînement ML à partir des indicateurs TimescaleDB.

**Features extraites :**
- RSI par TF : `rsi_1h`, `rsi_2h`, `rsi_3h`, `rsi_4h`
- Écarts RSI : `rsi_gap_1h_2h`, `rsi_gap_2h_3h`, etc. (convergence)
- Position Bollinger : `boll_pos_1h`, `boll_pos_4h` ([-1, 1] normalized)
- Squeeze : `boll_squeeze_1h`, `boll_squeeze_4h` (booléen one-hot)
- Pente trend : `trend_slope_1h`, `trend_slope_4h`
- Pattern harmonic : `harmonic_gartley`, `harmonic_butterfly` (one-hot)
- Volume relatif : `volume_ratio_1h`, `volume_ratio_4h` (courant / MA-20)
- Fear & Greed Index : `fng_index` (0–100 normalized)
- Sentiment NLP : `sentiment_score` ([-1, 1])

**Acceptation :**
- [ ] `build_feature_matrix()` retourne `pd.DataFrame` avec colonnes ci-dessus
- [ ] Toutes les features sont `float64` (pas d'objet)
- [ ] Lignes avec NaN supprimées après construction
- [ ] Log indique nombre de features et nombre de lignes finales
- [ ] Tests : données vides, données partielles, tout manquant

**Dépendances :** Indicateurs TimescaleDB disponibles  
**Fichiers associés :** `src/ml/models/feature_engineering.py`, `tests/unit/test_feature_engineering.py`

---

### RF-ML-009 — Temporal Split (No Random Split)

**Priorité :** MUST  
**Description :** Split train/test **strictement temporel** — jamais aléatoire sur data temporelle.

**Spécification :**
- Ratio : 80/20 par défaut (configurable)
- Ordre : train_df = données anciennes, test_df = données récentes
- Vérification : `assert train.index.max() < test.index.min()`
- Output : `(train_df, test_df)` avec DatetimeIndex

**Acceptation :**
- [ ] `temporal_split(df, train_ratio=0.8)` retourne tuple de DataFrames
- [ ] Train et test non-chevauchants
- [ ] Train précède test chronologiquement
- [ ] Logs affichent : nb lignes train, nb lignes test, ratio effectif
- [ ] Lève ValueError si df vide ou ratio hors (0, 1)
- [ ] Tests : ratio 0.5/0.9, df petit (2 lignes), df grand (10k lignes)

**Dépendances :** RF-ML-008  
**Fichiers associés :** `src/ml/models/trainer.py`, `tests/unit/test_temporal_split.py`

---

### RF-ML-010 — Model Training (XGBoost)

**Priorité :** MUST  
**Description :** Entraîne un classifieur XGBoost multi-classe (BUY/SELL/HOLD) avec tracking MLflow.

**Spécification :**
- Hyperparams : `n_estimators=300`, `max_depth=5`, `lr=0.05`, `subsample=0.8`, `colsample_bytree=0.8`
- Objectif : `logloss` (3 classes)
- Validation : eval_set pendant training (early stopping possible)
- Random state : 42 (reproducibilité)
- Output : modèle xgb.XGBClassifier + métriques

**Métriques à logger :**
- Accuracy, F1, ROC-AUC (test set)
- Nb samples train/test
- Feature importance (top 5)
- Runtime (en secondes)

**Acceptation :**
- [ ] `train(features, labels)` retourne `run_id` MLflow
- [ ] Features et labels mêmes longueurs
- [ ] Lève ValueError si < 10 samples
- [ ] MLflow logs : params, metrics, model, signature
- [ ] Modèle sauvegardé avec `infer_signature()`
- [ ] Tests : cas heureux, erreur size mismatch, données insuffisantes

**Dépendances :** RF-ML-008, RF-ML-009, MLflow configuré  
**Fichiers associés :** `src/ml/models/trainer.py`, `tests/unit/test_trainer.py`

---

### RF-ML-011 — Model Training (LightGBM & Random Forest)

**Priorité :** SHOULD  
**Description :** Entraîne des modèles additionnels (LightGBM, Random Forest) comme ensembles/baselines.

**Spécification :**
- LightGBM : `num_leaves=31`, `learning_rate=0.05`, `num_boost_round=300`
- Random Forest : `n_estimators=300`, `max_depth=10`, `n_jobs=-1`
- Output : modèles sérialisés en MinIO
- Ensemble : moyenne des 3 predictions

**Acceptation :**
- [ ] LightGBM entraîné et loggé en MLflow
- [ ] RF entraîné et loggé en MLflow
- [ ] Ensemble method: `(xgb + lgb + rf) / 3`
- [ ] Métriques comparatives dans MLflow UI
- [ ] Tests : entraînement simple, prédictions cohérentes

**Dépendances :** RF-ML-008, RF-ML-009, MLflow  
**Fichiers associés :** `src/ml/models/trainer.py`

---

### RF-ML-012 — LSTM Model (Optional Phase 2+)

**Priorité :** COULD  
**Description :** Modèle LSTM pour capturer dépendances temporelles dans les séries de signaux (phase 2+).

**Spécification :**
- Lookback : 20 candles (80 heures @ 4h)
- Architecture : 2 couches LSTM (64 units) + Dense(3, softmax)
- Loss : categorical crossentropy
- Optimizer : Adam
- Callbacks : EarlyStopping, ModelCheckpoint

**Acceptation :**
- [ ] Modèle compil et entraîné sans erreur
- [ ] Predictions shape = (batch, 3) pour BUY/SELL/HOLD
- [ ] Sérialisé en SavedModel + MLflow
- [ ] Tests : forward pass, shape output, gradient flow

**Dépendances :** TensorFlow/PyTorch, RF-ML-008  
**Fichiers associés :** `src/ml/models/lstm_trainer.py`

---

## 3. Exigences Fonctionnelles — Backtesting

### RF-ML-013 — Walk-Forward Backtester

**Priorité :** MUST  
**Description :** Backteste une stratégie via walk-forward avec purging et embargo windows.

**Spécification Walk-Forward :**
```
Données: 2 ans (730 jours)
Train window: 6 mois (180 jours) — glissant
Test window : 1 mois (30 jours)
Stride: 1 mois (30 jours) — chevauchement acceptable
Purging: 5 jours avant test window (exclude du train)
Embargo: 5 jours après test window (exclude du train suivant)

Fold 0: train [0:180], test [180:210]
Fold 1: train [240:420], test [420:450]  (purging [175:240])
Fold 2: train [480:660], test [660:690]
...
```

**Résultats par fold :**
- n_trades : nb de trades simulés
- win_rate : fraction de trades gagnants
- profit_factor : profit_gross / loss_gross
- sharpe_ratio : (ret_mean / ret_std) * sqrt(252)
- max_drawdown : peak-to-trough
- total_return : cumul retours

**Acceptation :**
- [ ] `WalkForwardBacktester(data, signal_fn)` crée instance
- [ ] `run()` retourne `BacktestSummary` avec liste de folds
- [ ] Purging/embargo respect chronologique
- [ ] Log chaque fold : dates, nb trades, sharpe
- [ ] Gère cas limite : < 1 trade, trop peu de données
- [ ] Tests : petit dataset (100 rows), signal synthétique, métrique cohérente

**Dépendances :** RF-ML-007 (signal engine)  
**Fichiers associés :** `src/ml/backtesting/backtest_engine.py`, `tests/unit/test_backtest_engine.py`

---

### RF-ML-014 — Backtesting Metrics

**Priorité :** MUST  
**Description :** Calcule les métriques de backtesting : Sharpe, Win Rate, Profit Factor, Max Drawdown.

**Formules :**
- Sharpe : `(mean_return / std_return) * sqrt(252)`
- Win rate : `nb_winning_trades / total_trades`
- Profit factor : `sum(winning_trades) / abs(sum(losing_trades))`
- Max drawdown : `(peak - trough) / peak` max sur la série cumul
- Total return : `final_equity / initial_equity - 1`

**Acceptation :**
- [ ] Sharpe annualisé pour 4h candles (6/jour, 252 jours)
- [ ] Win rate dans [0, 1]
- [ ] Profit factor > 1 = profitable
- [ ] Max drawdown dans [0, 1]
- [ ] Handles cas edge : 0 trades, 1 trade, tous gagnants, tous perdants
- [ ] Tests : série de retours simple, cas extrêmes

**Dépendances :** RF-ML-013  
**Fichiers associés :** `src/ml/backtesting/backtest_engine.py`, `tests/unit/test_backtest_metrics.py`

---

### RF-ML-015 — Backtesting Baseline (Buy & Hold)

**Priorité :** MUST  
**Description :** Compare la stratégie ML contre un baseline "Buy & Hold" sur la même période.

**Spécification :**
- Position : long depuis le jour 1 du test window
- Exit : jour final du test window
- Return benchmark : `(price_end - price_start) / price_start`
- Comparaison : Sharpe stratégie vs Sharpe B&H

**Acceptation :**
- [ ] B&H return calculé correctement
- [ ] Même période test que stratégie
- [ ] Log affiche : B&H sharpe, stratégie sharpe, delta
- [ ] Tests : prix montant, prix baissant, prix stable

**Dépendances :** RF-ML-013, RF-ML-014  
**Fichiers associés :** `src/ml/backtesting/backtest_engine.py`, `tests/integration/test_backtest_baseline.py`

---

## 4. Exigences Fonctionnelles — Signal Generation

### RF-ML-016 — Signal Generator Interface

**Priorité :** MUST  
**Description :** Orchestre le rule engine et l'optional ML predictor pour générer un unique TradingSignal.

**Modes :**
- Rules-only (Phase 1) : confiance du rule engine uniquement
- Rules+ML (Phase 2) : blending 60% ML + 40% rules
- Conflicting signals : pénaliser à 40% de la confiance minimale

**Pipeline :**
1. Évalue rule engine → direction, confidence, rules_triggered
2. Si predictor dispo : évalue ML → direction, confidence
3. Si même direction : blending (0.6*ML + 0.4*rules)
4. Si directions opposées : penalize (0.4 * min(ML, rules))
5. Sentiment adjustment : ±5pp selon news sentiment
6. Vérification seuil : confiance ≥ 0.6 sinon suppression
7. Calcul leverage : 5x (conf 0.65-0.74), 10x (0.75-0.84), 20x (≥0.85)
8. Verification marge : 2x du notional
9. Vérification frais : si frais ≥ 50% gain attendu → suppression

**Acceptation :**
- [ ] `generate(symbol, indicators, news_sentiment)` retourne `TradingSignal | None`
- [ ] Mode rules-only : une confiance
- [ ] Mode rules+ML : blending visible en logs
- [ ] Sentiment adjustment : ±5pp correctement appliqué
- [ ] Confiance finale ∈ [0, 1]
- [ ] Logs tracent chaque étape
- [ ] Tests : mode rules, mode ML, conflit direction, sentiment positif/négatif

**Dépendances :** RF-ML-007, RF-ML-010  
**Fichiers associés :** `src/ml/signal_generator.py`, `tests/unit/test_signal_generator.py`

---

### RF-ML-017 — Leverage Suggestion

**Priorité :** MUST  
**Description :** Suggère un levier (5, 10, ou 20x) basé sur la confiance du signal.

**Table de décision :**
| Confiance | Levier | Raison |
|-----------|--------|--------|
| < 0.65 | None | Trop faible |
| 0.65-0.74 | 5x | Modéré |
| 0.75-0.84 | 10x | Intermédiaire |
| ≥ 0.85 | 20x | Fort |

**Acceptation :**
- [ ] `_suggest_leverage(confidence)` retourne int|None
- [ ] Boundaries testées exactement (0.65, 0.75, 0.85)
- [ ] Confiance 0.64 → None, 0.65 → 5x, etc.
- [ ] Logs affichent levier suggéré et raison
- [ ] Tests : limites exactes, valeurs intermédiaires

**Dépendances :** RF-ML-016  
**Fichiers associés :** `src/ml/signal_generator.py`, `tests/unit/test_leverage_suggestion.py`

---

### RF-ML-018 — Margin Safety Verification (2x Rule)

**Priorité :** MUST  
**Description :** Vérifie et documente le ratio de marge libre — toujours 2x la position.

**Formule :**
```
Box = 1 / leverage
Margin required = 2 × box = 2 / leverage

Examples:
- 5x  → box 20%  → margin 40% (4x)
- 10x → box 10%  → margin 20% (2x)
- 20x → box 5%   → margin 10% (1x)

⚠️ Si leverage suggéré mais capital insuffisant → signal dégradé à leverage inférieur
```

**Acceptation :**
- [ ] `_compute_margin_safety(leverage)` retourne Decimal|None
- [ ] Calcul exact : 2 / leverage
- [ ] Logs indiquent marge requise vs capital dispo (si dispo fourni)
- [ ] Tests : tous les leviers 5, 10, 20, None

**Dépendances :** RF-ML-017  
**Fichiers associés :** `src/ml/signal_generator.py`, `tests/unit/test_margin_safety.py`

---

### RF-ML-019 — Fees Verification

**Priorité :** MUST  
**Description :** Estime les frais cumulés et supprime le signal si frais > 50% du gain attendu.

**Frais estimés :**
- Maker : 0.02%
- Taker : 0.05%
- Funding rate : 0% (stockage, exemple moyen)
- Slippage : 0.10% (estimation conservative)
- **Total round-trip : ~0.17%**

**Vérification :**
```
Expected gain proxy = confidence × 1% (move de base prudent)
Fees threshold = 50% × expected_gain
If fees ≥ threshold → suppress signal
```

**Acceptation :**
- [ ] `_estimate_fees(leverage)` retourne Decimal (0.0017)
- [ ] `_verify_fees(confidence, fees)` retourne bool
- [ ] Confidence 0.6 → expected gain 0.6% → threshold 0.3% → 0.17% OK
- [ ] Logs affichent : frais estimés, gain attendu, décision
- [ ] Tests : confiance basse (suppression), confiance haute (émission)

**Dépendances :** RF-ML-016  
**Fichiers associés :** `src/ml/signal_generator.py`, `tests/unit/test_fees_verification.py`

---

### RF-ML-020 — Signal Persistence

**Priorité :** MUST  
**Description :** Persiste les TradingSignal qualifiés dans la table TimescaleDB `trading_signals`.

**Champs sauvegardés :**
- `id` (UUID)
- `symbol`, `signal_type`, `confidence_score`
- `timeframe_primary`, `timeframes_aligned` (JSONB)
- `rules_triggered` (array de strings)
- `leverage_suggested`, `margin_safety`, `fees_estimated`
- `model_version` (rules_v1, xgboost_v2, etc.)
- `created_at` (NOW)

**Acceptation :**
- [ ] `save_signal(session, signal)` insère dans BDD
- [ ] ID généré (UUID)
- [ ] Timestamps UTC
- [ ] JSONB et arrays sérialisés correctement
- [ ] Logs tracent l'insertion (id, symbol, type, conf)
- [ ] Tests : insertion simple, double insertion (idempotence), rollback

**Dépendances :** RF-ML-016, TimescaleDB prêt  
**Fichiers associés :** `src/ml/signal_generator.py`, `tests/integration/test_signal_persistence.py`

---

## 5. Exigences Fonctionnelles — Batch Signal Generation

### RF-ML-021 — Async Signal Pipeline

**Priorité :** MUST  
**Description :** Pipeline async pour générer des signaux pour tous les symboles trackés (13 principaux + top 30).

**Pipeline :**
```
Pour chaque symbol ∈ TRACKED_SYMBOLS:
  1. Fetch indicators multi-TF (1h, 2h, 3h, 4h, 1D, 1W, 1M) depuis TimescaleDB
  2. Generator.generate(symbol, indicators) → signal | None
  3. Si signal : save_signal()
  4. Log : symbol, signal count

Résultat : dict[symbol] → count (0 ou 1 par symbol)
```

**Idempotence :**
- Appeler 2× dans la même période 4h peut produire doublons
- APScheduler caller doit garantir fréquence ≤ 4h
- Pas de suppression de signaux en doublon (audit trail)

**Acceptation :**
- [ ] `generate_signals_for_symbols(symbols, session)` async
- [ ] Retourne dict[symbol] = nb_signals
- [ ] Fetch indicators pour toutes les TF
- [ ] Gère symboles avec données partielles (log warning)
- [ ] Gère erreurs par-symbol (log, continue)
- [ ] Temps total < 5 min pour 13 symboles
- [ ] Logs : start, symboles traités, total émis, elapsed

**Dépendances :** RF-ML-016, RF-ML-020, TimescaleDB, AsyncSession  
**Fichiers associés :** `src/ml/signal_generator.py`, `tests/integration/test_signal_pipeline.py`

---

### RF-ML-022 — Scheduler Integration

**Priorité :** MUST  
**Description :** Intègre la pipeline de signaux avec APScheduler pour exécution périodique.

**Job :**
- Nom : `generate_trading_signals`
- Trigger : cron chaque 4 heures (0h, 4h, 8h, 12h, 16h, 20h UTC)
- Timeout : 5 minutes
- Retry : 2 tentatives en cas d'erreur
- Logging : MLflow + application logs

**Acceptation :**
- [ ] Job registered dans ETL scheduler
- [ ] Exécution autonome sans intervention
- [ ] Erreurs loggées (pas de silent fail)
- [ ] Métriques loggées (symbols processed, signals emitted)
- [ ] Tests : job exécution mock, vérification signal count

**Dépendances :** RF-ML-021  
**Fichiers associés :** `src/etl/main.py` (job registration), `tests/integration/test_scheduler.py`

---

## 6. Exigences Fonctionnelles — MLflow & DVC

### RF-ML-023 — MLflow Experiment Tracking

**Priorité :** MUST  
**Description :** Tracke tous les entraînements ML dans MLflow avec params, metrics, et artifacts.

**Convention :**
- Experiment name : `{symbol}_{timeframe}_{model_type}` (ex: `BTC_4h_xgboost`)
- Run tags : `phase`, `symbol`, `model_type`, `version`
- Params : hyperparams + features utilisées
- Metrics : accuracy, F1, ROC-AUC, train/test sizes
- Artifacts : modèle (pkl/h5), figures (feature importance, confusion matrix), dataset metadata

**Acceptation :**
- [ ] `settings.mlflow_tracking_uri` pointe vers PostgreSQL (pas fichier)
- [ ] Chaque `train()` crée un run et logs params/metrics
- [ ] `mlflow.xgboost.log_model()` sauvegarde modèle
- [ ] `infer_signature()` appliquée pour API schema
- [ ] UI MLflow accessible (localhost:5000)
- [ ] Tests : création experiment, log params, model registry

**Dépendances :** MLflow service, PostgreSQL  
**Fichiers associés :** `src/ml/models/trainer.py`, `src/ml/mlflow_utils.py`

---

### RF-ML-024 — Model Registry & Staging

**Priorité :** SHOULD  
**Description :** Enregistre les modèles en production avec stages (None → Staging → Production).

**Workflow :**
```
1. Train nouveau modèle → run_id XYZ
2. Register dans model registry : name="BTC_4h_xgboost_vN", run_id=XYZ
3. Stage "None" par défaut
4. Manual approval : transition → "Staging"
5. Evaluation / A/B test
6. Approved : transition → "Production"
7. Deprecated old version → "Archived"
```

**Acceptation :**
- [ ] Model register via MLflow API (pas manual)
- [ ] Versioning automatique (v1, v2, v3)
- [ ] Stages (None, Staging, Production) implémentés
- [ ] Prédiction charge modèle "Production" stage
- [ ] Logs tracent transition stage
- [ ] Tests : register, fetch production, stage transition

**Dépendances :** RF-ML-023  
**Fichiers associés :** `src/ml/mlflow_utils.py`, `src/ml/models/predictor.py`

---

### RF-ML-025 — DVC Dataset Versioning

**Priorité :** SHOULD  
**Description :** Version les datasets d'entraînement avec DVC, remote MinIO.

**Structure :**
```
data/
  raw/
    binance_ohlcv_2024-2026.parquet  → .dvc file
    indicators_2024-2026.parquet     → .dvc file
  processed/
    features_train_fold0.parquet     → .dvc file
    features_test_fold0.parquet      → .dvc file

dvc.yaml:
  - fetch data from MinIO (minio://datasets/...)
  - compute features
  - split train/test
```

**Acceptation :**
- [ ] `dvc.yaml` décrit pipeline complet
- [ ] `.dvc` files committés, données dans MinIO
- [ ] `dvc pull` restaure datasets
- [ ] Remote MinIO configuré (`dvc remote add -d ...`)
- [ ] Reproducibility : `dvc repro` rejoue tout
- [ ] Tests : DVC pipeline exécution (mock MinIO)

**Dépendances :** MinIO, DVC CLI  
**Fichiers associés :** `dvc.yaml`, `data/.gitignore`, `src/ml/dvc_utils.py`

---

## 7. Exigences Fonctionnelles — NLP & Sentiment

### RF-ML-026 — Sentiment Analysis Pipeline

**Priorité :** SHOULD  
**Description :** Analyse le sentiment des articles de news pour ajuster la confiance des signaux.

**Modèle :**
- Algorithme : TF-IDF vectorizer + Logistic Regression (scikit-learn)
- Output : score ∈ [-1.0, 1.0]
  - +1.0 = very bullish (positive news)
  - 0.0 = neutral
  - -1.0 = very bearish (negative news)
- Entrée : titre + snippet de l'article

**Acceptation :**
- [ ] `SentimentAnalyzer().train(texts, labels)` entraîne modèle
- [ ] `predict(text)` retourne float ∈ [-1, 1]
- [ ] Modèle sérialisable en pickle
- [ ] Tests : texte bullish (+0.9), neutre (≈0), bearish (-0.9)
- [ ] Données : min. 30 articles par sentiment pour train

**Dépendances :** scikit-learn  
**Fichiers associés :** `src/ml/nlp/sentiment.py`, `tests/unit/test_sentiment.py`

---

### RF-ML-027 — Sentiment Integration in Signals

**Priorité :** SHOULD  
**Description :** Intègre le score de sentiment dans la confiance du signal (±5 pp).

**Adjustment :**
```
sentiment_adj = sentiment_score × 0.05
Si direction BUY : confidence += sentiment_adj
Si direction SELL : confidence -= sentiment_adj
confidence = clamp(confidence, 0.0, 0.95)
```

**Acceptation :**
- [ ] `generate()` accepte `news_sentiment` optionnel
- [ ] Adjustment ±5pp appliqué correctement
- [ ] Capping à 0.95 max (prudent)
- [ ] Logs indiquent sentiment contribution
- [ ] Tests : sentiment positif (boost), négatif (réduction), None (no-op)

**Dépendances :** RF-ML-016, RF-ML-026  
**Fichiers associés :** `src/ml/signal_generator.py`, `tests/unit/test_sentiment_integration.py`

---

### RF-ML-028 — News Aggregate Sentiment

**Priorité :** SHOULD  
**Description :** Calcule un sentiment agrégé à partir des derniers N articles (24h) par symbol.

**Spécification :**
- Fenêtre : 24 heures avant le signal
- Articles : tous ceux mentionnant le symbol + marché global
- Agrégation : moyenne (ou médiane)
- Pondération : recency (poids plus élevé pour articles récents)

**Acceptation :**
- [ ] Query news_articles pour symbol dans les 24h
- [ ] Fetch sentiment_score (pré-calculé par ETL)
- [ ] Moyenne pondérée : poids = exp(-minutes_ago / 1440)
- [ ] Retourne scalar ou None (si < 3 articles)
- [ ] Tests : plusieurs articles, 1 article, 0 articles

**Dépendances :** RF-ML-026, news_articles table  
**Fichiers associés :** `src/ml/repositories/timescale.py`, `tests/integration/test_news_sentiment.py`

---

## 8. Exigences Fonctionnelles — Concept Drift Detection

### RF-ML-029 — Concept Drift Monitoring

**Priorité :** SHOULD  
**Description :** Détecte les changements dans la distribution des données (drift) qui rendraient le modèle obsolète.

**Métriques de drift :**
- Distribution shift (KL divergence) : indicateurs histograms train vs récent
- Performance drift : Sharpe ratio sur fenêtres glissantes
- Calibration drift : distribution prédictions vs réalité

**Triggers de retrain :**
- KL divergence > 0.5 (shift significatif)
- Sharpe ratio baisse de > 30% sur 2 semaines
- Win rate baisse de > 20% sur 1 mois

**Acceptation :**
- [ ] `DriftDetector` classe calcule KL divergence
- [ ] Logs alertent si drift détecté
- [ ] Dashboard affiche drift metrics (optionnel)
- [ ] Retrain automatique si drift > seuil (future: alerter DevOps)
- [ ] Tests : drift synthétique (shift features), pas de drift

**Dépendances :** RF-ML-010, RF-ML-013  
**Fichiers associés :** `src/ml/monitoring/drift_detection.py`, `tests/unit/test_drift_detection.py`

---

### RF-ML-030 — Model Retraining Schedule

**Priorité :** SHOULD  
**Description :** Retrain automatique hebdomadaire ou sur trigger drift.

**Schedule :**
- Baseline : chaque lundi 02:00 UTC (après week-end)
- Trigger : si drift détecté (RF-ML-029)
- Window : données 3 mois glissants
- Validation : comparer nouveau modèle vs version Production
- Promotion : si Sharpe nouveau ≥ ancien, transition → Staging
- Manual approval avant Production

**Acceptation :**
- [ ] APScheduler job `retrain_models` chaque lundi
- [ ] Drift detection déclenche retrain ad-hoc
- [ ] Logs tracent chaque retrain (start, end, metrics)
- [ ] MLflow nouveau run + model registry entry
- [ ] Tests : mock scheduler, mock data, verify metrics

**Dépendances :** RF-ML-023, RF-ML-029  
**Fichiers associés :** `src/etl/main.py` (job), `src/ml/retraining.py`

---

## 9. Exigences Non-Fonctionnelles

### RNF-ML-001 — Performance Inference

**Requirement :** Latence d'inférence < 500 ms par symbol (règles + optional ML).

**Mesure :**
- Temps rule engine evaluation
- Temps ML predictor (si chargé)
- Temps persistence DB
- Total < 500ms pour tous les 13 symboles → <40ms/symbol

**Acceptation :**
- [ ] Profiling montre < 40ms/symbol en mode rules
- [ ] ML predictor (XGBoost) < 50ms par symbol
- [ ] Persistence async (non-bloquant)
- [ ] Logs affichent timing per-symbol et total
- [ ] Tests de performance : benchmark suite

**Fichiers associés :** `src/ml/signal_generator.py`, `tests/performance/test_inference_speed.py`

---

### RNF-ML-002 — Model Accuracy Targets

**Requirement :** Modèles ML doivent dépasser le baseline "Buy & Hold" en termes de Sharpe ratio.

**Targets :**
- Baseline B&H Sharpe : ~0.5-1.0 (historique 2024-2026)
- Modèle cible : Sharpe ≥ 1.2 (XGBoost, LightGBM)
- Win rate : ≥ 55% (meilleur que aléatoire 50%)
- Profit factor : ≥ 1.2

**Acceptation :**
- [ ] Walk-forward test montre Sharpe > baseline
- [ ] Win rate > 50%
- [ ] Profit factor > 1.0
- [ ] MLflow metrics documentent comparaison
- [ ] Pas de overfitting : test Sharpe ≥ 80% du train Sharpe

**Fichiers associés :** `src/ml/backtesting/`, `tests/integration/test_model_accuracy.py`

---

### RNF-ML-003 — Reproducibility

**Requirement :** Tous les résultats ML sont reproductibles via seeds et checkpoints.

**Mesures :**
- Random seed = 42 global (NumPy, XGBoost, TensorFlow)
- Timestamps fixés dans tests (@freeze_time)
- DVC versioning datasets
- MLflow artifacts (models, data snapshots)
- Config externalisée (YAML, pas hardcoding)

**Acceptation :**
- [ ] `np.random.seed(42)` appliqué avant train
- [ ] Tests utilisent @freeze_time pour time
- [ ] DVC pull → DVC repro reproduit exactement
- [ ] Re-run entraînement → même métriques
- [ ] Tests : compare run 1 vs run 2 metrics (assertEqual)

**Fichiers associés :** `src/ml/models/trainer.py`, `dvc.yaml`, `tests/`

---

### RNF-ML-004 — Monitoring & Logging

**Requirement :** Tous les composants ML loggent structuré, pas de print().

**Standards :**
- Logger : `logging.getLogger(__name__)`
- Niveau : INFO (start/end), DEBUG (trace), WARNING (anormal), ERROR (failure)
- Format structuré : timestamp, level, module, message + context
- ExtraFields : symbol, model_version, confidence, rule_names

**Acceptation :**
- [ ] Zéro print() en code ML (sauf tests debug)
- [ ] Logger importé dans chaque module
- [ ] Logs incluent contexte (symbol, metric, etc.)
- [ ] Error logs avec `exc_info=True`
- [ ] Tests vérifient logs (mock logger)

**Fichiers associés :** Tous les fichiers `src/ml/`

---

### RNF-ML-005 — Type Hints & Type Safety

**Requirement :** Toutes les fonctions ML ont type hints complets (params + return).

**Standards :**
- `from __future__ import annotations`
- Type hints sur tous les paramètres et return
- Complex types : `Optional[T]`, `list[T]`, `dict[K, V]`
- `mypy --strict` passes
- Pydantic models pour data structs

**Acceptation :**
- [ ] `mypy src/ml/ --strict` passes
- [ ] Pas de `type: ignore` (sauf justifiés)
- [ ] Return types explicites
- [ ] Données entrées/sorties typées Pydantic
- [ ] Tests : type checking intégré

**Fichiers associés :** Tous les fichiers `src/ml/`

---

### RNF-ML-006 — Test Coverage

**Requirement :** Couverture minimale 80% du code ML (inclusif).

**Details :**
- Ligne 1 (current) : ~50-60% (excl. du scope)
- Cible après remédiation : ≥80% (incl. code ML)
- Coverage gates en CI (`--cov-fail-under=80`)
- Exclusions justifiées : debug code, version fallbacks

**Acceptation :**
- [ ] `pytest --cov=src/ml tests/ --cov-fail-under=80` passe
- [ ] Code ML inclu (pas de `omit src/ml/`)
- [ ] 80% lines, branches, statements couverts
- [ ] Report généré & archivé
- [ ] Pull request rejetée si coverage < 80%

**Fichiers associés :** `tests/unit/`, `tests/integration/`, `pyproject.toml` ([tool.coverage])

---

## 10. Matrice de Traçabilité

| Req ID | Titre | Impl | Tests | Docs | Audit |
|--------|-------|------|-------|------|-------|
| RF-ML-001 | Config YAML | `engine.py:43-59` | `test_rule_engine.py` | §2.1 | A4 |
| RF-ML-002 | RSI Multi-TF | `rsi_rules.py` | `test_rsi_rules.py` | §2.2 | — |
| RF-ML-003 | Bollinger Bands | `bollinger_rules.py` | `test_bollinger_rules.py` | §2.3 | — |
| RF-ML-004 | Harmonic Patterns | `harmonic_rules.py` | `test_harmonic_rules.py` | §2.4 | — |
| RF-ML-005 | Trend Lines | `trend_rules.py` | `test_trend_rules.py` | §2.5 | — |
| RF-ML-006 | Multi-TF Alignment | `multi_tf_rules.py` | `test_multi_tf_rules.py` | §2.6 | — |
| RF-ML-007 | Aggregation | `engine.py:202-302` | `test_engine_aggregation.py` | §2.7 | — |
| RF-ML-008 | Feature Engineering | `feature_engineering.py` | `test_feature_engineering.py` | §3.1 | — |
| RF-ML-009 | Temporal Split | `trainer.py:126-160` | `test_temporal_split.py` | §3.2 | T5 |
| RF-ML-010 | XGBoost Training | `trainer.py:166-240` | `test_trainer.py` | §3.3 | T1 |
| RF-ML-011 | LightGBM & RF | `trainer.py` | `test_trainer.py` | §3.4 | — |
| RF-ML-012 | LSTM Model | `lstm_trainer.py` | `test_lstm.py` | §3.5 | — |
| RF-ML-013 | Walk-Forward | `backtest_engine.py` | `test_backtest.py` | §4.1 | T2 |
| RF-ML-014 | Metrics | `backtest_engine.py` | `test_backtest_metrics.py` | §4.2 | — |
| RF-ML-015 | Baseline B&H | `backtest_engine.py` | `test_baseline.py` | §4.3 | — |
| RF-ML-016 | Signal Generator | `signal_generator.py:50-187` | `test_signal_generator.py` | §5.1 | — |
| RF-ML-017 | Leverage | `signal_generator.py:296-312` | `test_leverage.py` | §5.2 | — |
| RF-ML-018 | Margin Safety | `signal_generator.py:334-352` | `test_margin.py` | §5.3 | — |
| RF-ML-019 | Fees Verify | `signal_generator.py:355-371` | `test_fees.py` | §5.4 | — |
| RF-ML-020 | Persistence | `signal_generator.py:189-221` | `test_persistence.py` | §5.5 | — |
| RF-ML-021 | Async Pipeline | `signal_generator.py:379-470` | `test_signal_pipeline.py` | §6.1 | T3 |
| RF-ML-022 | Scheduler | `etl/main.py` | `test_scheduler.py` | §6.2 | — |
| RF-ML-023 | MLflow | `trainer.py`, `mlflow_utils.py` | `test_mlflow.py` | §7.1 | — |
| RF-ML-024 | Model Registry | `mlflow_utils.py` | `test_registry.py` | §7.2 | — |
| RF-ML-025 | DVC Versioning | `dvc.yaml` | `test_dvc.py` | §7.3 | — |
| RF-ML-026 | Sentiment | `nlp/sentiment.py` | `test_sentiment.py` | §8.1 | — |
| RF-ML-027 | Sentiment Integration | `signal_generator.py:133-139` | `test_sentiment_int.py` | §8.2 | — |
| RF-ML-028 | News Aggregate | `repositories/timescale.py` | `test_news_sentiment.py` | §8.3 | — |
| RF-ML-029 | Drift Detection | `monitoring/drift_detection.py` | `test_drift.py` | §9.1 | — |
| RF-ML-030 | Retrain Schedule | `retraining.py` | `test_retrain.py` | §9.2 | — |
| RNF-ML-001 | Inference Speed | `signal_generator.py` | `test_perf_inference.py` | §10.1 | — |
| RNF-ML-002 | Model Accuracy | `backtest_engine.py` | `test_accuracy.py` | §10.2 | — |
| RNF-ML-003 | Reproducibility | Tous | `test_repro.py` | §10.3 | — |
| RNF-ML-004 | Monitoring | Tous | `test_logging.py` | §10.4 | — |
| RNF-ML-005 | Type Hints | Tous | `mypy --strict` | §10.5 | A1 |
| RNF-ML-006 | Test Coverage | `pytest --cov` | CI gates | §10.6 | T1 |

---

## 11. Remédiation Audit

### Audit T1 — Code ML Exclu de Couverture

**Problème :** `src/ml/` exclu de coverage, couverture réelle ~50-60%, cible affichée 80%.

**Remédiation :**
1. **Modifier `pyproject.toml`** — enlever exclusion `omit = ["src/ml/*"]`
2. **Ajouter tests manquants :**
   - `tests/unit/test_rsi_rules.py` — tous les cas RSI
   - `tests/unit/test_bollinger_rules.py` — squeeze, band walking
   - `tests/unit/test_harmonic_rules.py` — patterns
   - `tests/unit/test_trend_rules.py` — trend slopes
   - `tests/unit/test_feature_engineering.py` — feature matrix build
   - `tests/unit/test_trainer.py` — training loop
   - `tests/unit/test_backtest_engine.py` — metrics calculation
   - `tests/unit/test_signal_generator.py` — signal generation
3. **Ajouter test E2E :** `tests/integration/test_signal_e2e.py`
   - Collecte indicateurs → Rule Engine → Signal → Persistence
4. **Vérifier :** `pytest --cov=src/ml tests/ --cov-report=html`

**Effort :** 8-10h  
**Acceptance :** Coverage `src/ml/` ≥ 80%, CI gates enforced  
**Issue Audit :** T1

---

### Audit T2 — WalkForwardBacktester Non Testé

**Problème :** Tests importent `Backtester` (mauvaise classe), WalkForwardBacktester zéro coverage.

**Remédiation :**
1. **Corriger imports tests :** `from src.ml.backtesting.backtest_engine import WalkForwardBacktester`
2. **Implémenter `tests/unit/test_backtest_engine.py`:**
   - Création instance, run() sur petit dataset
   - Vérifier folds, dates non-chevauchantes
   - Calculs metrics : sharpe, win_rate, profit_factor
   - Cas edge : 1 trade, 0 trades, tous gagnants/perdants
3. **Tests purging/embargo :** vérifier exclusions temporelles
4. **Baseline B&H :** comparer vs benchmark

**Effort :** 6-8h  
**Acceptance :** `test_backtest_engine.py` 100% coverage, tests passing  
**Issue Audit :** T2

---

### Audit T3 — Pas de Test E2E Signal Pipeline

**Problème :** Pipeline complet (ETL → ML → API → Frontend) non validé.

**Remédiation :**
1. **Créer `tests/integration/test_signal_e2e.py`:**
   - Mock MinIO + TimescaleDB
   - Fetch OHLCV + indicators (fixtures)
   - RuleEngine.evaluate() → TradingSignal
   - SignalGenerator.generate() → TradingSignal
   - Persist signal
   - Fetch via API endpoint
   - Afficher dans Streamlit (mock ou screenshot)
2. **Données test :** fixture avec 100 lignes 4h data (10 jours)
3. **Vérifications :** signal confidence >= 0.6, rules_triggered non-vide, persistence OK

**Effort :** 4-6h  
**Acceptance :** Test exécuté avec succès, couverture > 70%  
**Issue Audit :** T3

---

### Audit T4 — Double API Rule Engine

**Problème :** `evaluate()` et `generate_signals()` redondants dans RuleEngine.

**Remédiation :**
1. **Audit code :** vérifier API réelle utilisée
2. **Si `evaluate()` est legacy :** dépubliciser ou déprécier
3. **Standardiser :** un seul point entry (likely `evaluate()` + `aggregate()`)
4. **Tests :** vérifier pas de breakage, logger deprecation

**Effort :** 2-3h  
**Acceptance :** Single API, backward compat si nécessaire  
**Issue Audit :** T4

---

### Audit T5 — Feature Engineering Data Leakage

**Problème :** Risque que indicators soient calculés avant split temporel.

**Remédiation :**
1. **Audit flux :** tracer où indicators sont calculés
2. **Si ETL calcule globally :** OK (they do, per doc)
3. **Si ML refait calcul :** VÉRIFIER split temporel avant tout calcul ML
4. **Tests :** créer test explicite
   - Split données en train/test
   - Calcul features sur train uniquement
   - Appliquer scaler train → test (pas fit test)
5. **Documentation :** clarifier dans docstring feature_engineering.py

**Effort :** 3-4h  
**Acceptance :** Test de non-leakage passing  
**Issue Audit :** T5

---

### Audit T6 — Pas de Freeze Time dans Tests ML

**Problème :** Tests utilisent `datetime.now()` au lieu de `@freeze_time`.

**Remédiation :**
1. **Rechercher tous les tests ML :** `grep -r "datetime.now()" tests/`
2. **Remplacer par :**
   ```python
   @freeze_time("2026-03-12 12:00:00")
   def test_xxx():
       ...
   ```
3. **Fixtures :** créer `@pytest.fixture` pour timestamp fixe
4. **Random seeds :** vérifier `np.random.seed(42)` en début chaque test

**Effort :** 2-3h  
**Acceptance :** Tous les tests ML déterministes  
**Issue Audit :** T6

---

### Audit T7 — Pas de Test Seuils Signaux (Confidence >= 0.6)

**Problème :** Pas de test de régression pour seuil confiance et autres limits.

**Remédiation :**
1. **Créer `tests/unit/test_signal_thresholds.py`:**
   - Confidence 0.59 → No signal emission
   - Confidence 0.60 → Signal emitted
   - Confidence 0.61 → Signal emitted
   - Leverage : 0.64→None, 0.65→5x, 0.75→10x, 0.85→20x
   - Margin : tests tous les leviers
   - Fees : confiance basse → suppression
2. **Mutation testing :** vérifier que changer seuils casse tests

**Effort :** 3-4h  
**Acceptance :** Tous les seuils critiques testés, mutation kills  
**Issue Audit :** T7

---

## 12. Plan de Déploiement (Recommandations)

### Pré-Prod (Semaine 1-2)

- [ ] T1 : Inclure code ML dans coverage (1h)
- [ ] T2 : Tester WalkForwardBacktester (8h)
- [ ] A1-A2 : Type hints + ORM aliasing (3h)
- [ ] RNF-ML-006 : Coverage gate CI (1h)

### MVP (Semaine 3-4)

- [ ] RF-ML-001 à RF-ML-007 : Rule engine complet + tests (12h)
- [ ] RF-ML-008 à RF-ML-010 : Feature engineering + XGBoost (10h)
- [ ] RF-ML-013 à RF-ML-015 : Backtesting complet (8h)
- [ ] RF-ML-016 à RF-ML-020 : Signal generation + persistence (10h)

### Production Ready (Semaine 5+)

- [ ] RF-ML-021 à RF-ML-022 : Async pipeline + scheduler (6h)
- [ ] RF-ML-023 à RF-ML-025 : MLflow + DVC (8h)
- [ ] RF-ML-026 à RF-ML-028 : Sentiment NLP (6h)
- [ ] T3 : Test E2E pipeline (6h)
- [ ] RNF-ML-001 à RNF-ML-004 : Perf, monitoring, reproducibility (8h)

---

## 13. Acceptance Criteria Globales

1. **Code Quality**
   - [ ] `ruff check src/ml/` passe (0 violations)
   - [ ] `mypy src/ml/ --strict` passe (0 errors)
   - [ ] No `print()`, all `logging`
   - [ ] No hardcoded secrets

2. **Testing**
   - [ ] `pytest tests/ --cov=src/ml --cov-fail-under=80` passe
   - [ ] 100% de RF-ML-001 à RF-ML-030 testées
   - [ ] Test E2E signal pipeline réussi

3. **Documentation**
   - [ ] Chaque fonction a docstring (Numpy style)
   - [ ] README `src/ml/` explique architecture
   - [ ] Tous les RFC répertoriés dans CDC

4. **Performance**
   - [ ] Inference < 500ms total (< 40ms/symbol)
   - [ ] Model Sharpe > baseline B&H
   - [ ] Retraining < 30 min

5. **MLOps**
   - [ ] MLflow UI accessible, experiments loggées
   - [ ] DVC pipeline exécutable (`dvc repro`)
   - [ ] Model registry avec staging/production

---

## Conclusion

Ce CDC couvre les 30 exigences fonctionnelles (RF-ML-001 à RF-ML-030) et 6 non-fonctionnelles (RNF-ML-001 à RNF-ML-006) du module ML/Data Science. Il address tous les findings de l'audit (T1-T7, A1-A5) et fournit :

- **Specifications détaillées** pour chaque composant (rules, features, training, backtesting, signalling)
- **Matrice de traçabilité** vers code source et tests
- **Plan de remédiation** audit avec efforts estimés
- **Acceptance criteria** clairs et vérifiables
- **Tests requis** pour 100% coverage cible

**Livrable :** Ce document, accompagné des commits de correction et de la suite de tests, valide la production-readiness du module ML.

---

**Auteurs :** PM ML, Analyst ML  
**Révision :** 2.0  
**Date :** 2026-03-12  
**Statut :** Approved for implementation

