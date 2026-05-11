---
type: rncp-livrable
source: docs/rncp/bloc2-infrastructure/ml-phase2-scope-revise.md
tags: [cryptobot, rncp, bloc2, ml, phase2, scope-acte]
created: 2026-04-14
ingested_by: agent-L2-IA-Justif
rncp_ref: RNCP38919
bloc: "Bloc 2 — Conception et developpement d'une solution technologique"
competence: "Tracer le perimetre IA livre vs roadmap et justifier la validation des modeles"
adr: ADR-010
---

# ML Phase 2 — Perimetre revise pour soutenance RNCP38919

> Livrable RNCP38919 Bloc 2. Acte la separation entre **ce qui est livre en code** pour la soutenance de juin 2026 et **ce qui reste en roadmap post-soutenance**. Resout les contradictions 19-22 de [[../../meta/contradictions]].

## 1. Resume decision

Les specs Phase 2 ([[../../specs/PRD-phase2]], [[../../specs/architecture-ml-pipelines]], [[../../specs/analysis-ml-gaps]]) decrivent un ensemble a 5 modeles (Rules 30 % + XGBoost 20 % + LSTM 20 % + RL 15 % + Regime 15 %). Le code livre au 2026-04-14 contient **Rules + XGBoost + LightGBM + blend 60/40** (cf. [[../../code/ml]], `src/ml/models/trainer.py`, `src/ml/signal_generator.py`).

**Decision (ADR-010)** : pour la soutenance RNCP38919 de juin 2026, le perimetre defendu est limite au code livre. LSTM, RL (DQN / SARSA / Q-Learning), K-means regime detection passent en **roadmap S14-S16 post-soutenance**. Cela evite de mentir sur du code qui n'existe pas et concentre la soutenance sur ce qui est testable.

Principe first-principles : un jury audite ce qu'il peut executer, pas ce qu'il lit dans un PlantUML. Mieux vaut 3 modeles livres + 3 roadmapes que 5 modeles specs non-livres.

## 2. Tableau perimetre

| Composant | Livre (code) | Specs (roadmap) | Justification |
|-----------|--------------|-----------------|---------------|
| **RuleEngine** (4 base + 4 convergence evaluators) | OUI | — | Phase 1 stable, coverage 100 %, cf. [[CryptoBot/avril/rncp/livrables/L2-infrastructure/ml-justification-phase1]]. |
| **XGBoost classifier** | OUI | — | Classif binaire direction (BUY vs SELL/HOLD), walk-forward temporel, MLflow tracking. `trainer.py` livre. |
| **LightGBM classifier** | OUI | — | Ensemble avec XGBoost : variance reduction, temps d'entrainement plus court, gestion native des categorielles (symbole). |
| **Blend Rules + ML 60/40** | OUI | — | Rules = autorite explicable, ML = affinement. Directions identiques -> 0.6 ML + 0.4 rules. Conflit -> penalite 0.4 * min(ml, rules) (cf. `signal_generator.py:115-130`). |
| **MLflow + MinIO** (tracking + artifacts) | OUI | — | Experiment `cryptobot-signals`, registry Staging -> Production. |
| **WalkForwardBacktester** (purge + embargo) | OUI | — | `src/ml/backtesting/backtest_engine.py`, metriques Sharpe / drawdown / profit factor. |
| **LSTM multi-TF** (3 modeles 4h / 1d / 1w) | NON | S14 | Requiert historique labellise >= 2 ans sur chaque TF + infra GPU absente (VPS OVH CPU-only). Cout entrainement + validation temporelle = 4 semaines. |
| **RL DQN / SARSA / Q-Learning** | NON | S15 | Necessite `CryptoTradingEnv` Gymnasium a construire, convergence incertaine (risque R8 de [[../../planning/risks]]). Paper Trading Feature 1 est prerequis (tracking `trades.signal_id` non disponible aujourd'hui). |
| **K-means regimes** (BULL / BEAR / SIDEWAYS) | NON | S16 | Depend du `EnhancedFeatureBuilder` avec ~30 variables cross-asset non encore assemblees (sentiment cross-asset, Fear&Greed integre, on-chain fallback non branche). |
| **SignalGeneratorV2** (ensemble 5-model) | NON | S16 | Consequence mecanique : pas d'ensemble tant que LSTM/RL/Regime absents. |

## 3. Features engineering actuel

Defini dans `src/ml/models/trainer.py` (`FEATURE_COLS`, lignes 27-32) :

| Categorie | Features | Source |
|-----------|----------|--------|
| **RSI multi-TF** | `rsi_1h`, `rsi_2h`, `rsi_3h`, `rsi_4h` | `indicators.rsi` par timeframe |
| **Bollinger position** | `boll_pos_1h`, `boll_pos_4h` | `indicators.price_vs_bollinger` |
| **Trend slope** | `trend_slope_1h`, `trend_slope_4h` | `indicators.trend_slope` |
| **Volume ratio** | `volume_ratio_1h`, `volume_ratio_4h` | OHLCV volume / rolling mean 20 periodes |

Total : **10 features numeriques**. Toutes provenant de TimescaleDB, aucune API externe payante.

Enrichissements existants mais pas encore branches au trainer : MACD (`src/etl/indicators/macd.py`), harmonic one-hot (pattern type), sentiment NLP (`src/ml/nlp/sentiment.py`), Fear & Greed (Alternative.me). Leur integration est le chantier de l'`EnhancedFeatureBuilder` S16.

## 4. Entrainement

Implementation dans `ModelTrainer.train()` (`src/ml/models/trainer.py:166-240`).

**Strategie** :

- **Temporal split strict** : `temporal_split(df, train_ratio=0.8)` coupe chronologiquement 80 % train / 20 % test. **Jamais** de random split (fuite temporelle garantie sur time-series).
- **Walk-forward backtester** (`src/ml/backtesting/backtest_engine.py`) : 6 mois train / 1 mois test, glissant.
- **Purge + embargo** : `BacktestConfig` defini avec fenetres de purge autour de chaque split pour empecher le label leak quand le label utilise des rendements futurs (horizon H candles).
- **Ratios finaux** : 70 % train / 15 % validation / 15 % test hors-echantillon.

**Hyperparametres XGBoost** (lignes 193-202) :

```python
params = {
    "n_estimators": 300,
    "max_depth": 5,
    "learning_rate": 0.05,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "eval_metric": "logloss",
    "random_state": 42,
}
```

Conservateurs a dessein (max_depth 5, subsample 0.8) pour limiter l'overfit sur un dataset encore petit.

## 5. Tracking MLflow

| Element | Valeur |
|---------|--------|
| Experiment | `cryptobot-signals` |
| Tracking URI | `settings.mlflow_tracking_uri` (prod : http://mlflow:5000) |
| Metrics logguees | `accuracy`, `f1`, `roc_auc` (lignes 223-228 de trainer.py) |
| Metrics metier visees | `sharpe_ratio`, `max_drawdown`, `hit_rate`, `roi_net_fees` (backtester) |
| Params logs | tous les hyperparametres + `train_samples`, `test_samples`, `feature_cols` |
| Artifacts | modele XGBoost (`mlflow.xgboost.log_model`), signature inferee, registered_model_name = experiment_name |
| Registry | Staging -> Production apres validation humaine |

Backend storage : MinIO (compatible S3) pour artifacts, PostgreSQL pour metadata MLflow.

## 6. Versioning donnees

**DVC** sur `data/processed/{yyyy-mm-dd}/` avec remote MinIO.

Datasets versionnes :

- `ohlcv.parquet` : OHLCV multi-TF, partitionne par symbole
- `indicators.parquet` : RSI / BB / MACD / trend par TF
- `sentiment.parquet` : sentiment score par article + timestamp
- `labels.parquet` : labels binaires BUY/nonBUY derives des regles Phase 1

Chaque run MLflow logue le `dvc hash` du dataset utilise -> reproductibilite totale.

## 7. Pas de prediction de prix absolu

**ADR implicite** : XGBoost et LightGBM predisent la **direction** (classification binaire BUY vs SELL/HOLD) ou le **rendement futur** (regression sur `log(close_t+H / close_t)`), **jamais** un prix absolu.

Justification first-principles :

- Les prix crypto sont non-stationnaires : un modele entraine a "predire BTC = 45000" sera obsolete des qu'il monte a 60000.
- Les rendements sont stationnaires par construction (centres autour de 0, variance bornee).
- Un modele qui annonce un prix absolu cree une illusion de precision aupres du persona -> danger ethique.

## 8. Resolution contradictions

Mapping direct vers [[../../meta/contradictions]] :

| Ligne contradictions.md | Statut avant | Statut apres ADR-010 | Phrase de cloture |
|-------------------------|--------------|-----------------------|---------------------|
| **19** (specs : 5 modeles vs PlantUML C06 : 3) | OPEN | **RESOLVED** | Scope revise : Phase 2 livree = Rules + XGBoost + LightGBM. LSTM / RL / Regime deviennent roadmap post-soutenance. PlantUML C06 a aligner sur livre. |
| **20** (RL absent C06 mais exige par specs) | OPEN | **RESOLVED (roadmap S15)** | Scope revise : RL reporte en roadmap S15, conforme a ADR-004 de [[../../specs/adrs-phase2]]. |
| **21** (LSTM 3 split TF vs C06 composant unique) | OPEN | **RESOLVED (roadmap S14)** | Scope revise : LSTM entierement deporte en roadmap S14. Split 3-TF (4h / 1d / 1w) a implementer a ce moment. |
| **22** (aucun `lstm*.py` dans code) | OPEN | **RESOLVED** | Scope revise : Phase 2 livree ne contient pas de LSTM, ce qui est coherent avec le code et PlantUML C06 a mettre a jour. |

## 9. Liens

- [[CryptoBot/avril/rncp/livrables/L2-infrastructure/ml-justification-phase1]] — justification rule engine
- [[../../history/decisions]] — ADR-010 (entree dediee)
- [[../../meta/contradictions]] — section "Resolutions 2026-04-14"
- [[../../specs/PRD-phase2]]
- [[../../specs/architecture-ml-pipelines]]
- [[../../specs/analysis-ml-gaps]]
- [[../../architecture/c06-phase2-ml-pipeline]]
- [[../../code/ml]]
- [[../../planning/roadmap]]
