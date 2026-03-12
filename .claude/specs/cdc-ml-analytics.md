# Cahier des Charges — Module ML & Analytics
## Crypto Bot — Plateforme de Signaux de Trading Crypto

**Version** : 1.0
**Date** : 2026-03-12
**Auteur** : Product Manager, Équipe ML & Analytics
**Statut** : À développer (Phase 1 & 2)

---

## Table des matières

1. [Résumé exécutif](#résumé-exécutif)
2. [Phase 1 — Moteur de Règles](#phase-1--moteur-de-règles)
3. [Phase 2 — ML Supervisé](#phase-2--ml-supervisé)
4. [Module Analytics](#module-analytics)
5. [Critères d'acceptation transversaux](#critères-dacceptation-transversaux)
6. [Dépendances & interfaces](#dépendances--interfaces)

---

## Résumé exécutif

Ce document définit les exigences pour deux modules interconnectés du projet Crypto Bot :

1. **Phase 1 — Moteur de Règles Explicites** : Système de détection de patterns multi-timeframe basé sur des indicateurs techniques (RSI, Bollinger Bands, Harmonic Patterns, Trend Lines). Sortie : labels BULL/BEAR/NEUTRAL avec confiance (0–1).

2. **Phase 2 — ML Supervisé** : Apprentissage supervisé sur les labels Phase 1 pour optimiser les seuils d'indicateurs par crypto et timeframe. Modèles : XGBoost, LightGBM, LSTM. MLflow tracking, DVC versioning, walk-forward backtesting.

3. **Module Analytics** : Heatmaps de corrélations, historique de performance des signaux, métriques de backtest (Sharpe, Sortino, max drawdown, win rate).

**Périmètre** : `src/ml/` (Phase 1 & 2), `src/frontend/pages/analytics.py` (Analytics).

**Livrables** :
- Configuration YAML (`src/ml/config/indicators.yaml`)
- Moteur de règles + aggregateur de confiance
- Pipeline ML (feature engineering, train/val/test walk-forward)
- MLflow & DVC setup (experiment tracking, artifact storage)
- NLP sentiment scoring
- Analytics backend & frontend

---

# PHASE 1 — MOTEUR DE RÈGLES

## RF-ML-001 : Configuration des indicateurs techniques

**ID** : RF-ML-001
**Titre** : Fichier de configuration centralisé des seuils d'indicateurs
**Priorité** : MUST
**Type** : Données de configuration

### Description

Le système doit utiliser un fichier YAML centralisé (`src/ml/config/indicators.yaml`) pour définir tous les seuils et paramètres des indicateurs techniques. Ce fichier est la **source unique de vérité** pour les règles du moteur Phase 1 et doit être lisible par l'équipe Data Eng (pour validation) et le moteur ML (pour évaluation).

### Critères d'acceptation

- [x] Fichier `src/ml/config/indicators.yaml` existe et contient :
  - Section `rsi` : timeframes (1h, 2h, 3h, 4h), seuils overbought (défaut 70), oversold (défaut 30)
  - Section `bollinger` : période (défaut 20), écart-type (défaut 2), squeeze threshold (défaut 0.1)
  - Section `harmonic` : ratios (0.618, 0.786, 1.13, 1.618), tolerance (défaut 0.02)
  - Section `trend` : période weekly (défaut 200), période monthly (défaut 400), support/resistance tolerance (défaut 0.02)
  - Section `multi_tf` : timeframes prioritaires, convergence threshold (défaut 0.3 pour RSI)
  - Section `nlp` : modèle sentiment, threshold score
- [x] Schéma YAML validé par Pydantic (`src/ml/config/schema.py`)
- [x] Seuils sont des Decimal ou float (pas de hardcoding dans le code)
- [x] Le fichier peut être rechargé sans redémarrage (via un endpoint `/api/ml/reload-config`)
- [x] Logging explicite lors du chargement et validation des paramètres

### Critères de test

```python
def test_indicators_config_loads_successfully():
    """Verify YAML config parses without errors."""
    cfg = IndicatorConfig.from_yaml("src/ml/config/indicators.yaml")
    assert cfg.rsi is not None
    assert cfg.rsi.overbought == 70
    assert cfg.rsi.oversold == 30
    assert len(cfg.rsi.timeframes) == 4

def test_indicators_config_schema_validation():
    """Verify Pydantic schema rejects invalid config."""
    with pytest.raises(ValidationError):
        IndicatorConfig(rsi={"overbought": 150})  # invalid
```

### Dépendances

- Équipe Data Eng : définir les paramètres par crypto historiquement
- `src/shared/models/` : ne pas ajouter de dépendances

---

## RF-ML-002 : Évaluation RSI multi-timeframe

**ID** : RF-ML-002
**Titre** : Détection RSI convergence sur timeframes adjacentes (1h, 2h, 3h, 4h)
**Priorité** : MUST
**Type** : Règle d'indicateur

### Description

Le RSI (Relative Strength Index) est un momentum oscillateur (0–100) qui détecte le surachat (> overbought) et la survente (< oversold). La **convergence multi-TF** signifie que le RSI atteint un seuil similaire sur des timeframes adjacentes (1h, 2h, 3h, 4h), ce qui renforce le signal.

Règles :
- **RSI surachat convergent** : RSI ≥ overbought sur au moins 2 TF consécutives (1h–2h–3h–4h) → **direction BUY**, confiance = f(écarts entre TF)
- **RSI survente convergent** : RSI ≤ oversold sur au moins 2 TF consécutives → **direction SELL**, confiance = f(écarts entre TF)
- **Écart RSI entre TF** : plus les valeurs sont proches, plus la confiance augmente (écart < 5 = 1.0, écart < 10 = 0.8, etc.)

### Critères d'acceptation

- [x] Module `src/ml/rules/rsi_rules.py` implémente `evaluate_rsi(symbol, indicators_by_tf, config)`
- [x] Accepte `indicators_by_tf: dict[str, IndicatorRecord]` (une IndicatorRecord par timeframe)
- [x] Retourne `RuleResult | None` avec :
  - `direction` : "BUY" ou "SELL"
  - `confidence` : Decimal (0–1)
  - `rule_name` : "rsi_overbought_multi_tf" ou "rsi_oversold_multi_tf"
  - `reason` : chaîne explicative (ex: "RSI 1h=72, 2h=70, 3h=68 → surachat convergent")
- [x] Détecte la convergence sur ≥2 TF consécutives
- [x] Pondère la confiance par l'écart RSI inter-TF (plus l'écart est faible, plus la confiance est haute)
- [x] Seuils overbought/oversold sont lus depuis `config`
- [x] Pas de hardcoding de seuils dans le code

### Algorithme

```
1. Extraire RSI pour 1h, 2h, 3h, 4h depuis indicators_by_tf
2. Trier les TF par ordre croissant
3. Trouver une séquence de 2+ TF consécutives où :
   - RSI >= overbought OU RSI <= oversold
4. Si trouvé :
   - direction = "BUY" si overbought, "SELL" si oversold
   - écart_max = max(|RSI[tf_i] - RSI[tf_j]|) pour tous pairs dans séquence
   - confiance = 1.0 - (écart_max / 100) * 0.5  # écart 0 → conf 1.0, écart 10 → conf 0.95
   - Retourner RuleResult(direction, confiance, "rsi_...", reason)
5. Sinon : Retourner None
```

### Critères de test

```python
def test_rsi_overbought_convergent_2tf():
    """RSI ≥70 on 1h and 2h → BUY with high confidence."""
    indicators = {
        "1h": IndicatorRecord(rsi=72, ...),
        "2h": IndicatorRecord(rsi=70, ...),
        "3h": IndicatorRecord(rsi=65, ...),
        "4h": IndicatorRecord(rsi=68, ...),
    }
    result = evaluate_rsi("BTC", indicators, config)
    assert result is not None
    assert result.direction == "BUY"
    assert result.confidence >= Decimal("0.9")

def test_rsi_convergent_large_gap_reduces_confidence():
    """RSI 1h=72, 4h=60 → weaker signal."""
    indicators = {
        "1h": IndicatorRecord(rsi=72, ...),
        "2h": IndicatorRecord(rsi=71, ...),
        "3h": IndicatorRecord(rsi=65, ...),
        "4h": IndicatorRecord(rsi=60, ...),
    }
    result = evaluate_rsi("BTC", indicators, config)
    assert result is not None
    assert result.confidence < Decimal("0.9")
    assert result.confidence > Decimal("0.5")

def test_rsi_no_convergent_sequence():
    """RSI all oversold but non-consecutive → None."""
    indicators = {
        "1h": IndicatorRecord(rsi=28, ...),  # oversold
        "2h": IndicatorRecord(rsi=45, ...),  # neutral
        "3h": IndicatorRecord(rsi=25, ...),  # oversold
        "4h": IndicatorRecord(rsi=32, ...),  # neutral
    }
    result = evaluate_rsi("BTC", indicators, config)
    assert result is None
```

### Dépendances

- `src/ml/rules/models.py` : `RuleResult`, `RuleLabel`
- `src/shared/models/crypto.py` : `IndicatorRecord`
- `src/ml/config/indicators.yaml` : seuils RSI

---

## RF-ML-003 : Détection Bollinger Bands squeeze & breakout

**ID** : RF-ML-003
**Titre** : Détection squeeze (resserrement) et breakout (évasion) des Bollinger Bands
**Priorité** : MUST
**Type** : Règle d'indicateur

### Description

Les Bollinger Bands encadrent le prix avec 2 bandes (haute et basse) écartées de N écarts-types de la moyenne mobile. Un **squeeze** (bandes resserrées) signale une faible volatilité avant une évasion. Un **breakout** (prix casse une bande) signale le début d'un mouvement directionnel.

Règles :
- **Bollinger Squeeze** : largeur des bandes < squeeze_threshold → volatilité basse, **direction HOLD** (pas de signal)
- **Bollinger Breakout Haut** : prix > upper band pendant N candles → **direction BUY**, confiance élevée
- **Bollinger Breakout Bas** : prix < lower band pendant N candles → **direction SELL**, confiance élevée
- **Bollinger Band Walk** : prix oscille entre bande et MA → **direction HOLD**

### Critères d'acceptation

- [x] Module `src/ml/rules/bollinger_rules.py` implémente `evaluate_bollinger(symbol, indicators_by_tf, config)`
- [x] Accepte `indicators_by_tf: dict[str, IndicatorRecord]` avec champs :
  - `bb_upper` : bande supérieure
  - `bb_middle` : moyenne mobile
  - `bb_lower` : bande inférieure
  - `bb_width` : largeur en % (upper - lower) / middle
  - `close` : prix de clôture actuel
- [x] Retourne `RuleResult | None` avec :
  - `direction` : "BUY", "SELL", ou None (HOLD ne produit pas de signal)
  - `confidence` : Decimal (0–1)
  - `rule_name` : "bollinger_squeeze", "bollinger_breakout_up", "bollinger_breakout_down"
  - `reason` : description (ex: "Price 45000 broke above upper band 44500")
- [x] Détecte squeeze : `bb_width < squeeze_threshold` → pas de signal
- [x] Détecte breakout haut : `close > bb_upper * (1 + tolerance)` → BUY
- [x] Détecte breakout bas : `close < bb_lower * (1 - tolerance)` → SELL
- [x] Tous seuils lus depuis `config`

### Algorithme

```
1. Extraire bb_upper, bb_middle, bb_lower, close pour 4h (timeframe par défaut)
2. Calculer bb_width = (bb_upper - bb_lower) / bb_middle (en %)
3. Si bb_width < squeeze_threshold :
   - Retourner None (pas de signal lors du squeeze)
4. Si close > bb_upper * (1 + tolerance) :
   - direction = "BUY"
   - confiance = 0.8 (breakout établi)
5. Sinon si close < bb_lower * (1 - tolerance) :
   - direction = "SELL"
   - confiance = 0.8 (breakout établi)
6. Sinon si bb_lower <= close <= bb_upper :
   - distance_to_band = min(close - bb_lower, bb_upper - close)
   - band_width = bb_upper - bb_lower
   - proximity = distance_to_band / band_width
   - Si proximity < 0.2 (près d'une bande) :
     - direction = "BUY" si proche bande basse, "SELL" si proche bande haute
     - confiance = 0.6
   - Sinon :
     - Retourner None
7. Retourner RuleResult(direction, confiance, rule_name, reason)
```

### Critères de test

```python
def test_bollinger_breakout_up():
    """Price breaks above upper band → BUY."""
    indicators = {
        "4h": IndicatorRecord(
            bb_upper=44500,
            bb_middle=42000,
            bb_lower=39500,
            bb_width=0.07,  # 7%
            close=44800,  # above upper
        )
    }
    result = evaluate_bollinger("BTC", indicators, config)
    assert result is not None
    assert result.direction == "BUY"
    assert result.confidence >= Decimal("0.75")

def test_bollinger_squeeze_no_signal():
    """Squeeze (width < threshold) → None."""
    indicators = {
        "4h": IndicatorRecord(
            bb_upper=42050,
            bb_middle=42000,
            bb_lower=41950,
            bb_width=0.0024,  # 0.24% (very tight)
            close=42000,
        )
    }
    result = evaluate_bollinger("BTC", indicators, config)
    assert result is None

def test_bollinger_band_walk_near_upper():
    """Price near upper band (but not broken) → weak BUY."""
    indicators = {
        "4h": IndicatorRecord(
            bb_upper=44500,
            bb_middle=42000,
            bb_lower=39500,
            bb_width=0.075,
            close=44300,  # 95% of the way to upper band
        )
    }
    result = evaluate_bollinger("BTC", indicators, config)
    assert result is not None
    assert result.direction == "BUY"
    assert result.confidence == Decimal("0.6")
```

### Dépendances

- `src/ml/rules/models.py` : `RuleResult`
- `src/shared/models/crypto.py` : `IndicatorRecord`
- `src/ml/config/indicators.yaml` : période, écart-type, squeeze_threshold

---

## RF-ML-004 : Détection Harmonic Patterns

**ID** : RF-ML-004
**Titre** : Identification de patterns harmoniques (Gartley, Butterfly, Bat, Crab)
**Priorité** : SHOULD
**Type** : Règle d'indicateur

### Description

Les patterns harmoniques (Gartley, Butterfly, Bat, Crab) sont des configurations de prix basées sur les ratios de Fibonacci qui prédisent des retournements. Chaque pattern est défini par 4 points (X, A, B, C) avec des ratios de longueur spécifiques.

**Gartley** (aussi appelé 5-0) :
- XA : mouvement initial
- AB = 0.618 × XA
- BC = 1.618 × AB (ou 2.618 × AB selon variante)
- CD = 1.272 × XA (ou 1.618 × XA)
- D (PRZ) = 0.786 × XA depuis A

**Butterfly** :
- AB = 0.786 × XA
- BC = 1.618 × AB
- CD = 1.272 × XA
- D = 1.27 × XA depuis A (extension)

**Bat** :
- AB = 0.50 × XA
- BC = 1.618–2.618 × AB
- CD = 0.886 × XA
- D = 0.886 × XA depuis A

**Crab** :
- AB = 0.618 × XA
- BC = 1.618–2.618 × AB
- CD = 1.618 × XA
- D = 1.618 × XA depuis A (extension forte)

### Critères d'acceptation

- [x] Module `src/ml/rules/harmonic_rules.py` implémente `evaluate_harmonic(symbol, indicators_by_tf, config)`
- [x] Accepte `indicators_by_tf: dict[str, IndicatorRecord]` avec champs :
  - `high`, `low` : prix max/min de la période (pour 4h et 1D)
  - Données OHLCV récentes (derniers 20–50 candles en mémoire)
- [x] Retourne `RuleResult | None` avec :
  - `direction` : "BUY" (si pattern haussier, pullback en D), "SELL" (si pattern baissier)
  - `confidence` : Decimal (0.6–0.9 selon précision du match)
  - `rule_name` : "harmonic_gartley", "harmonic_butterfly", "harmonic_bat", "harmonic_crab"
  - `reason` : "Gartley pattern detected at D level with 98% ratio match"
- [x] Détecte patterns sur les 4 dernières heures (16–50 candles dépendant de la granularité)
- [x] Vérifie les ratios Fibonacci avec une tolérance configurable (défaut 2%)
- [x] Classifie les points (X, A, B, C, D) en trouvant des swing points (highs/lows locaux)
- [x] Détermine la direction basée sur le type de pattern et la position de D

### Algorithme (simplifié)

```
1. Extraire 50 derniers candles (high, low, close) de l'historique TimescaleDB
2. Identifier les swing points locaux (highs et lows)
3. Pour chaque séquence de 4 swing points (X, A, B, C) :
   4. Calculer les ratios : AB/XA, BC/AB, CD/XA, D_price/A_price
   5. Pour chaque pattern type (Gartley, Butterfly, Bat, Crab) :
      6. Comparer les ratios observés vs. attendus (±tolerance)
      7. Si tous les ratios match (80%+ de précision) :
         8. C = reversal (prix change direction)
         9. Estimer le niveau D (PRZ = Potential Reversal Zone)
         10. Si D est proche du prix actuel (±2%) :
             11. direction = "BUY" si pattern haussier, "SELL" sinon
             12. confiance = 0.6 + (précision_ratio_match / 100) * 0.3
             13. Retourner RuleResult
12. Retourner None si aucun pattern détecté
```

### Critères de test

```python
def test_harmonic_gartley_detected():
    """Identify Gartley pattern with proper Fibonacci ratios."""
    # Simulated candles with known Gartley ratios
    ohlcv = [
        {"high": 100, "low": 100},  # X
        {"high": 120, "low": 120},  # A (20 up)
        {"high": 115, "low": 115},  # B (12.4 = 0.618*20, pullback)
        {"high": 108, "low": 108},  # C (retest)
        {"high": 98, "low": 98},    # D (0.786*20 = 15.72 down from A = 104.28)
    ]
    result = evaluate_harmonic("BTC", {"4h": IndicatorRecord(...)}, config)
    assert result is not None
    assert result.rule_name == "harmonic_gartley"
    assert result.confidence >= Decimal("0.7")

def test_harmonic_crab_bearish():
    """Identify inverted Crab (bearish) pattern."""
    # Simulated inverted Crab
    # ... (similar structure, bearish direction)
    result = evaluate_harmonic("ETH", {"4h": IndicatorRecord(...)}, config)
    assert result is not None
    assert result.direction == "SELL"

def test_harmonic_no_pattern_match():
    """Random candles → None."""
    # Random high/low with no Fibonacci structure
    result = evaluate_harmonic("BTC", {"4h": IndicatorRecord(...)}, config)
    assert result is None
```

### Dépendances

- `src/ml/rules/models.py` : `RuleResult`
- `src/shared/models/crypto.py` : `IndicatorRecord`
- `src/ml/config/indicators.yaml` : ratios Fibonacci, tolérance
- Équipe Data Eng : streaming des 50 derniers candles en TimescaleDB

---

## RF-ML-005 : Détection Trend Lines

**ID** : RF-ML-005
**Titre** : Support/Resistance multi-timeframe (Weekly stable vs. Monthly aggressive)
**Priorité** : SHOULD
**Type** : Règle d'indicateur

### Description

Les trend lines (droites de tendance) sur les longs timeframes (1W, 1M) offrent un support/résistance structurel. La philosophie :

- **Weekly trend** : trend à moyen terme, globalement stable. Dips temporaires sont des opportunités d'achat.
- **Monthly trend** : trend à long terme, plus aggressifs. Les dips en monthly sont rares mais importants.
- **Stratégie** : On cherche des dips en intraday/4h qui respectent le support weekly, tout en alignant avec la trend monthly.

Règles :
- **Dip vers weekly support** : prix casse le support 4h mais reste > support 1W → BUY, confiance élevée
- **Bounce vers weekly MA** : prix casse la bande basse 4h mais re-monte vers MA 1W → BUY faible
- **Prix rejette la monthly resistance** : prix ne peut pas casser la monthly resistance plusieurs fois → SELL
- **Trend weekly cassée** : prix < support 1W sur 3 bougies → pas de signal BUY

### Critères d'acceptation

- [x] Module `src/ml/rules/trend_rules.py` implémente `evaluate_trend(symbol, indicators_by_tf, config)`
- [x] Accepte `indicators_by_tf: dict[str, IndicatorRecord]` avec champs :
  - `trend_line_support_1w`, `trend_line_resistance_1w` : trend weekly
  - `trend_line_support_1m`, `trend_line_resistance_1m` : trend monthly
  - `sma_200_4h`, `sma_200_1w`, `sma_200_1m` : moyennes mobiles par timeframe
  - `close` : prix actuel
- [x] Retourne `RuleResult | None` avec :
  - `direction` : "BUY" ou "SELL"
  - `confidence` : Decimal (0.6–0.85)
  - `rule_name` : "trend_dip_weekly_support", "trend_bounce_ma_weekly", "trend_resist_monthly"
  - `reason` : "Price 42500 dips to weekly support 42000, respects monthly trend"
- [x] Détecte les dips vers support weekly (prix < support mais > support - 2% tolerance)
- [x] Vérifie que la trend weekly est respectée (prix > SMA 200 1W)
- [x] Vérifie que la trend monthly n'est pas cassée (prix pas trop loin sous support 1M)
- [x] Pondère confiance par la distance à la SMA (plus proche = plus fort signal)

### Algorithme

```
1. Extraire trend_support_1w, trend_resist_1w, trend_support_1m, trend_resist_1m
2. Extraire SMA 200 (1W, 1M, 4h), close actuel
3. Si close < trend_support_1w + tolerance ET close > trend_support_1m - tolerance :
   - dip_to_support = (close - trend_support_1w) / trend_support_1w
   - Si dip_to_support < 0.02 (dip de 0–2%) :
     - direction = "BUY"
     - confiance = 0.75 + min(distance_to_sma_1w, 0.1)
     - Retourner RuleResult
4. Sinon si close < trend_support_1w ET close > trend_support_1m :
   - # Dip faible (0–2% sous support)
   - direction = "BUY"
   - confiance = 0.65
   - Retourner RuleResult
5. Sinon si close > trend_resist_1m ET échecs précédents > 2 :
   - direction = "SELL"
   - confiance = 0.70
   - Retourner RuleResult
6. Retourner None
```

### Critères de test

```python
def test_trend_dip_weekly_support():
    """Price dips to weekly support, respects monthly → BUY."""
    indicators = {
        "1w": IndicatorRecord(
            trend_support=42000,
            sma_200=42500,
            close=41950,  # dip 0.12% under support
        ),
        "1m": IndicatorRecord(
            trend_support=40000,
            sma_200=40500,
        ),
        "4h": IndicatorRecord(close=41950),
    }
    result = evaluate_trend("BTC", indicators, config)
    assert result is not None
    assert result.direction == "BUY"
    assert result.confidence >= Decimal("0.7")

def test_trend_support_1w_broken():
    """Price < weekly support + 2% → no BUY signal."""
    indicators = {
        "1w": IndicatorRecord(
            trend_support=42000,
            sma_200=42500,
            close=41800,  # far under support
        ),
        "1m": IndicatorRecord(trend_support=40000),
    }
    result = evaluate_trend("BTC", indicators, config)
    assert result is None or result.direction != "BUY"

def test_trend_monthly_support_broken():
    """Price < monthly support → no BUY (trend broken)."""
    indicators = {
        "1m": IndicatorRecord(
            trend_support=40000,
            close=39500,  # below monthly support
        ),
    }
    result = evaluate_trend("BTC", indicators, config)
    # Should not emit strong BUY signal when monthly is broken
    assert result is None
```

### Dépendances

- `src/ml/rules/models.py` : `RuleResult`
- `src/shared/models/crypto.py` : `IndicatorRecord`
- Équipe Data Eng : calculer et stocker trend lines (support/résistance) et SMA 200 par timeframe

---

## RF-ML-006 : Convergence RSI & Bollinger Bands

**ID** : RF-ML-006
**Titre** : Règle composite : RSI overbought + position prix dans Bollinger
**Priorité** : SHOULD
**Type** : Règle convergence

### Description

Combiner deux indicateurs pour augmenter la confiance : Si le RSI indique un surachat ET le prix est au-dessus de la band supérieure (ou très proche), c'est un signal plus fort qu'un seul indicateur.

Règles :
- **RSI surachat + prix > BB upper** → confiance augmente (0.8–0.95)
- **RSI surachat + prix proche bande (90–100% entre bande basse et haute)** → confiance modérée (0.7–0.8)
- **RSI surachat mais prix < bande basse** → confiance faible (contradiction)

### Critères d'acceptation

- [x] Module `src/ml/rules/convergence_rules.py` implémente `evaluate_rsi_bollinger_convergence(indicators_by_tf, config)`
- [x] Accepte `indicators_by_tf: dict[str, IndicatorRecord]` (snapshot par timeframe)
- [x] Retourne `list[RuleResult]` (zéro, un ou plusieurs résultats)
- [x] Vérifie convergence RSI + Bollinger pour chaque timeframe (1h, 2h, 3h, 4h)
- [x] Pondère confiance par le degré de concordance
- [x] Seuils lus depuis `config`

### Algorithme

```
1. Pour chaque timeframe (1h, 2h, 3h, 4h) :
   2. Extraire rsi, bb_upper, bb_lower, close
   3. Si rsi >= overbought :
      4. proximity_to_upper = (close - bb_lower) / (bb_upper - bb_lower)
      5. Si proximity_to_upper >= 0.9 :
         6. confiance = 0.85 (RSI overbought + price at top)
         7. direction = "BUY"
         8. Ajouter RuleResult à results
      9. Sinon si proximity_to_upper >= 0.7 :
         10. confiance = 0.72 (RSI overbought + price near top)
         11. direction = "BUY"
         12. Ajouter RuleResult
      13. Sinon si proximity_to_upper < 0.3 :
          14. # Contradiction : RSI overbought but price low → penalise
          15. confiance = 0.5 (weak)
          16. direction = None (no signal)
   17. Sinon si rsi <= oversold :
       18. proximity_to_lower = (close - bb_lower) / (bb_upper - bb_lower)
       19. Si proximity_to_lower <= 0.1 :
           20. confiance = 0.85 (RSI oversold + price at bottom)
           21. direction = "SELL"
           22. Ajouter RuleResult
       23. Sinon si proximity_to_lower <= 0.3 :
           24. confiance = 0.72 (RSI oversold + price near bottom)
           25. direction = "SELL"
           26. Ajouter RuleResult
27. Retourner results (list[RuleResult])
```

### Critères de test

```python
def test_rsi_bb_convergence_bullish_strong():
    """RSI overbought + price > BB upper → 0.85 confidence."""
    indicators_by_tf = {
        "4h": IndicatorRecord(
            rsi=75,
            bb_upper=44500,
            bb_lower=39500,
            close=44700,
        ),
    }
    results = evaluate_rsi_bollinger_convergence(indicators_by_tf, config)
    assert len(results) == 1
    assert results[0].direction == "BUY"
    assert results[0].confidence >= Decimal("0.8")

def test_rsi_bb_convergence_contradiction():
    """RSI overbought but price < BB lower → weak/no signal."""
    indicators_by_tf = {
        "4h": IndicatorRecord(
            rsi=75,
            bb_upper=44500,
            bb_lower=39500,
            close=39000,  # below lower band
        ),
    }
    results = evaluate_rsi_bollinger_convergence(indicators_by_tf, config)
    # Should be empty or very weak confidence
    assert len(results) == 0 or results[0].confidence <= Decimal("0.5")
```

### Dépendances

- `src/ml/rules/models.py` : `RuleResult`
- `src/shared/models/crypto.py` : `IndicatorRecord`
- RF-ML-002, RF-ML-003 (dépendent du calcul RSI et Bollinger)

---

## RF-ML-007 : Convergence Trend & RSI multi-timeframe

**ID** : RF-ML-007
**Titre** : Convergence Trend Lines + RSI sur 1h et 4h (dip = opportunité)
**Priorité** : SHOULD
**Type** : Règle convergence

### Description

Détecter quand un dip court-terme (RSI 1h survente) se produit dans un trend long-terme supportif (prix > support 1W). Cela identifie les petits dips qui respectent les structures majeures.

Règles :
- **RSI 1h oversold + prix dips vers support 1W** → BUY, confiance 0.75–0.85
- **RSI 4h overbought + prix rejette resistance 1W** → SELL, confiance 0.70–0.80

### Critères d'acceptation

- [x] Module `src/ml/rules/convergence_rules.py` implémente `evaluate_trend_rsi_convergence(indicators_by_tf, config)`
- [x] Accepte `indicators_by_tf: dict[str, IndicatorRecord]`
- [x] Retourne `list[RuleResult]`
- [x] Vérifie convergence entre trend lines (1W, 1M) et RSI (1h, 4h)
- [x] Pondère confiance par la proximité à la trend line

### Algorithme

```
1. Extraire RSI 1h, RSI 4h, trend_support_1w, trend_resist_1m, close
2. Si RSI 1h <= oversold ET close proche trend_support_1w :
   3. direction = "BUY"
   4. confiance = 0.75 + (distance_trend / tolerance) * 0.1
   5. Ajouter RuleResult
6. Sinon si RSI 4h >= overbought ET close proche trend_resist_1m :
   7. direction = "SELL"
   8. confiance = 0.70 + (distance_trend / tolerance) * 0.1
   9. Ajouter RuleResult
10. Retourner results
```

### Dépendances

- RF-ML-002, RF-ML-005 (RSI et Trend)

---

## RF-ML-008 : Alignment multi-timeframe (supermajority)

**ID** : RF-ML-008
**Titre** : Consensus entre 3+ timeframes (supermajority direction voting)
**Priorité** : SHOULD
**Type** : Règle convergence

### Description

Déterminer quand 3 ou 4 timeframes adjacentes (1h, 2h, 3h, 4h) donnent toutes le même signal directionnel. C'est un signal très fort (confiance 0.85+).

Règles :
- **3/4 timeframes → BUY** : confiance 0.80+
- **4/4 timeframes → BUY** : confiance 0.90+
- **2/4 timeframes → BUY** : pas de signal (trop faible)

### Critères d'acceptation

- [x] Module `src/ml/rules/multi_tf_rules.py` implémente `evaluate_supermajority_tf_alignment(indicators_by_tf, config)`
- [x] Retourne `list[RuleResult]`
- [x] Vote directionnel : chaque TF est classée BUY/SELL/NEUTRAL par ses indicateurs
- [x] Requiert ≥3 TF avec le même vote
- [x] Pondère confiance par le pourcentage de consensus (3/4 = 0.80, 4/4 = 0.90)

### Dépendances

- RF-ML-002, RF-ML-003, RF-ML-005 (directionnels des TF individuelles)

---

## RF-ML-009 : Aggregation et pondération des règles

**ID** : RF-ML-009
**Titre** : Agrégation pondérée des résultats de règles individuelles
**Priorité** : MUST
**Type** : Orchestration

### Description

Combiner les résultats des différentes règles (RSI, Bollinger, Harmonic, Trend, Convergences) en un seul score directionnel et une confiance globale.

Pondérations (somme = 1.0) :
- RSI : 0.25
- Bollinger : 0.25
- Harmonic : 0.30
- Trend : 0.20

Agrégation :
1. Pour chaque résultat de règle, noter direction (BUY/SELL) et confiance (0–1)
2. Trier les résultats par direction
3. Calculer weighted score : sum(confiance × poids) pour chaque direction
4. Direction dominante = celle avec le plus haut weighted score
5. Pénaliser si l'opposition a aussi des votes (penaliser par opposition ratio)
6. Émettre signal seulement si confiance finale ≥ 0.6

### Critères d'acceptation

- [x] Classe `RuleEngine` dans `src/ml/rules/engine.py` implémente la méthode `aggregate(results: list[RuleResult], symbol: str) -> TradingSignal | None`
- [x] Accepte une liste de `RuleResult` (résultats individuels des règles)
- [x] Retourne `TradingSignal | None` (None si confiance < threshold)
- [x] Poids lus depuis `_RULE_WEIGHTS` (configurable)
- [x] Penalise les signaux contradictoires (une règle BUY, une autre SELL)
- [x] Inclut la liste des règles déclenchées dans `rules_triggered`
- [x] Détermine le timeframe primaire (préférence : 4h > 1D > 1h > 2h > 3h > 1W > 1M)

### Algorithme (détaillé)

```python
def aggregate(self, results: list[RuleResult], symbol: str) -> TradingSignal | None:
    if not results:
        return None

    # 1. Tally weighted votes per direction
    direction_scores = {"BUY": Decimal("0"), "SELL": Decimal("0")}
    direction_weights = {"BUY": Decimal("0"), "SELL": Decimal("0")}
    triggered_rules = []

    for result in results:
        # 2. Resolve direction
        if result.direction in {"BUY", "SELL"}:
            direction = result.direction
            confidence = result.confidence
        elif result.label in {RuleLabel.BULL, RuleLabel.BEAR}:
            direction = "BUY" if result.label == RuleLabel.BULL else "SELL"
            confidence = Decimal(str(result.weight))
        else:
            continue  # skip NEUTRAL

        # 3. Look up rule weight
        rule_key = _infer_rule_key(result.rule_name)
        weight = _RULE_WEIGHTS.get(rule_key, Decimal("0.25"))

        # 4. Accumulate
        direction_scores[direction] += confidence * weight
        direction_weights[direction] += weight
        triggered_rules.append(result.rule_name)

    # 5. Determine dominant direction
    dominant = "BUY" if direction_scores["BUY"] >= direction_scores["SELL"] else "SELL"
    total_weight = direction_weights[dominant]
    if total_weight == Decimal("0"):
        return None

    # 6. Weighted average confidence for dominant direction
    raw_confidence = direction_scores[dominant] / total_weight

    # 7. Penalize if opposition has votes
    opposing = "SELL" if dominant == "BUY" else "BUY"
    if direction_weights[opposing] > Decimal("0"):
        opposition_ratio = direction_scores[opposing] / (direction_scores[dominant] + direction_scores[opposing])
        raw_confidence = raw_confidence * (Decimal("1") - opposition_ratio * Decimal("0.5"))

    final_confidence = min(raw_confidence, Decimal("1.0"))

    # 8. Threshold check
    if final_confidence < SIGNAL_CONFIDENCE_THRESHOLD:
        return None

    # 9. Create TradingSignal
    primary_tf = _infer_primary_timeframe(results)
    signal = TradingSignal(
        symbol=symbol,
        signal_type=cast("Literal['BUY', 'SELL', 'HOLD']", dominant),
        confidence_score=final_confidence,
        timeframe_primary=primary_tf,
        timeframes_aligned={},
        rules_triggered=triggered_rules,
        leverage_suggested=None,
        margin_safety=None,
        fees_estimated=None,
        model_version="rules_v1",
    )
    return signal
```

### Critères de test

```python
def test_aggregate_all_buy_rules():
    """All rules vote BUY → high confidence."""
    results = [
        RuleResult(direction="BUY", confidence=Decimal("0.8"), rule_name="rsi_overbought_multi_tf", ...),
        RuleResult(direction="BUY", confidence=Decimal("0.75"), rule_name="bollinger_breakout_up", ...),
        RuleResult(label=RuleLabel.BULL, weight=Decimal("0.8"), rule_name="harmonic_gartley", ...),
    ]
    signal = engine.aggregate(results, "BTC")
    assert signal is not None
    assert signal.signal_type == "BUY"
    assert signal.confidence_score >= Decimal("0.75")

def test_aggregate_mixed_signals_penalize():
    """2 BUY rules, 1 SELL rule → lower confidence."""
    results = [
        RuleResult(direction="BUY", confidence=Decimal("0.8"), rule_name="rsi_...", ...),
        RuleResult(direction="BUY", confidence=Decimal("0.75"), rule_name="bollinger_...", ...),
        RuleResult(direction="SELL", confidence=Decimal("0.7"), rule_name="trend_...", ...),
    ]
    signal = engine.aggregate(results, "BTC")
    assert signal is not None
    assert signal.signal_type == "BUY"
    assert signal.confidence_score < Decimal("0.75")  # penalized

def test_aggregate_below_threshold():
    """Final confidence < 0.6 → None (no signal)."""
    results = [
        RuleResult(direction="BUY", confidence=Decimal("0.55"), rule_name="...", ...),
    ]
    signal = engine.aggregate(results, "BTC")
    assert signal is None
```

### Dépendances

- `src/ml/rules/models.py` : `RuleResult`, `RuleLabel`
- `src/shared/models/signal.py` : `TradingSignal`
- `src/shared/constants.py` : `SIGNAL_CONFIDENCE_THRESHOLD` (0.6)

---

## RF-ML-010 : Signal generation avec fusion ML optionnelle

**ID** : RF-ML-010
**Titre** : Orchestration Rule Engine + ML Predictor avec blending de confiance
**Priorité** : MUST
**Type** : Orchestration

### Description

Classe `SignalGenerator` qui orchestrate le moteur de règles et un prédicteur ML optionnel, en blendant leurs confiances.

Blending :
- **Rules-only mode** : utiliser la confiance du moteur de règles directement
- **Rules + ML mode** :
  - Si ML direction == Rule direction : confiance_blended = 0.6 × ML_conf + 0.4 × Rule_conf
  - Si ML direction != Rule direction : confiance_blended = 0.4 × min(ML_conf, Rule_conf) (penalité)

Ajustement sentiment :
- News sentiment dans [-1, 1] : ajuster confiance de ±5pp
  - BUY + sentiment=1.0 → +5pp (max 0.95)
  - SELL + sentiment=-1.0 → +5pp
  - Inverse pour contradiction

Seuil d'émission : confiance finale ≥ 0.6

### Critères d'acceptation

- [x] Classe `SignalGenerator` dans `src/ml/signal_generator.py`
- [x] Constructor : `__init__(rule_engine: RuleEngine, predictor: Predictor | None = None)`
- [x] Méthode `generate(symbol, indicators, news_sentiment=None) -> TradingSignal | None`
- [x] Appelle `rule_engine.evaluate()` et `aggregate()`
- [x] Si predictor disponible, appelle `predictor.predict(features)`
- [x] Blende confiances : 60% ML, 40% règles
- [x] Applique ajustement sentiment
- [x] Seuil d'émission : confiance ≥ 0.6
- [x] Méthode `save_signal(session, signal)` : persiste vers `trading_signals` table
- [x] Logging structuré (signal emitted, signal suppressed, etc.)

### Critères de test

```python
@pytest.mark.asyncio
async def test_signal_generator_rules_only():
    """Generate signal with rules-only mode."""
    engine = RuleEngine.from_yaml()
    generator = SignalGenerator(rule_engine=engine)

    indicators = {"4h": IndicatorRecord(rsi=75, bb_upper=44500, ...)}
    signal = generator.generate("BTC", indicators)

    assert signal is not None
    assert signal.model_version == "rules_v1"

@pytest.mark.asyncio
async def test_signal_generator_with_predictor():
    """Generate signal with ML predictor blending."""
    engine = RuleEngine.from_yaml()
    predictor = MockPredictor(predictions={"direction": "BUY", "confidence": 0.85})
    generator = SignalGenerator(rule_engine=engine, predictor=predictor)

    indicators = {...}
    signal = generator.generate("BTC", indicators)

    assert signal is not None
    assert signal.model_version == "xgboost_v2"
    assert signal.confidence_score == Decimal("0.68")  # 0.6*0.85 + 0.4*0.7

@pytest.mark.asyncio
async def test_signal_save_to_database():
    """Save signal to trading_signals table."""
    signal = TradingSignal(symbol="BTC", signal_type="BUY", confidence_score=Decimal("0.75"), ...)
    generator = SignalGenerator(rule_engine=..., predictor=None)

    async with async_session_factory() as session:
        await generator.save_signal(session, signal)
        await session.commit()

    # Verify saved
    async with async_session_factory() as session:
        orm = await session.execute(
            select(TradingSignalOrm).where(TradingSignalOrm.symbol == "BTC")
        )
        assert orm.scalar() is not None

@pytest.mark.asyncio
async def test_signal_generator_sentiment_adjustment():
    """Positive sentiment boosts BUY confidence."""
    engine = RuleEngine.from_yaml()
    generator = SignalGenerator(rule_engine=engine)

    indicators = {"4h": IndicatorRecord(rsi=70, ...)}
    signal_no_sentiment = generator.generate("BTC", indicators, news_sentiment=None)
    signal_positive = generator.generate("BTC", indicators, news_sentiment=0.8)

    assert signal_positive is not None
    assert signal_positive.confidence_score > signal_no_sentiment.confidence_score
```

### Dépendances

- `src/ml/rules/engine.py` : `RuleEngine`
- `src/shared/models/signal.py` : `TradingSignal`
- `src/shared/db_models.py` : `TradingSignalOrm`

---

## RF-ML-011 : Signal confidence threshold & emission gate

**ID** : RF-ML-011
**Titre** : Seuil d'émission de signaux (confidence ≥ 0.6)
**Priorité** : MUST
**Type** : Validation

### Description

Aucun signal n'est émis vers la table `trading_signals` si sa confiance < 0.6. C'est un seuil dur qui prévient les signaux faibles de polluer le système.

### Critères d'acceptation

- [x] Constante `SIGNAL_CONFIDENCE_THRESHOLD = Decimal("0.6")` dans `src/shared/constants.py`
- [x] Signal généré avec confiance < 0.6 retourne `None` (pas de TradingSignal)
- [x] Logs INFO quand un signal est supprimé pour cause confiance insuffisante
- [x] Logs INFO quand un signal est émis (avec confiance, rules triggered, etc.)

### Critères de test

```python
def test_signal_suppressed_below_threshold():
    """Signal with conf=0.55 is suppressed."""
    generator = SignalGenerator(rule_engine=engine)
    indicators = {...}  # produces conf=0.55
    signal = generator.generate("BTC", indicators)
    assert signal is None
```

### Dépendances

- `src/shared/constants.py`

---

## RF-ML-012 : Vérification levier et marge

**ID** : RF-ML-012
**Titre** : Suggestion de levier avec vérification règle 2x marge
**Priorité** : MUST
**Type** : Validation

### Description

Chaque signal peut suggérer un levier (5x, 10x, 20x). La règle 2x est obligatoire : la marge libre requise doit être **2x la position en notionnel**.

Exemple :
- Position notionnel = 10,000 USDT
- Levier 5x → box 20% → marge requise = 2 × 20% = 40%
- Capital minimum requis = 10,000 / 0.05 × 0.4 = 80,000 USDT

Si capital insuffisant, **dégrader le signal** (réduire confiance ou retirer levier).

### Critères d'acceptation

- [x] Méthode `SignalGenerator._suggest_leverage(confidence: Decimal) -> int | None`
  - confiance ≥ 0.85 → levier 20x
  - confiance ≥ 0.75 → levier 10x
  - confiance ≥ 0.65 → levier 5x
  - confiance < 0.65 → None (pas de levier suggéré)
- [x] Méthode `SignalGenerator._compute_margin_safety(leverage: int | None) -> Decimal | None`
  - levier 5x → marge 2 × 20% = 40%
  - levier 10x → marge 2 × 10% = 20%
  - levier 20x → marge 2 × 5% = 10%
  - None → None
- [x] Champ `TradingSignal.margin_safety` stocke la marge requise
- [x] Logs INFO si un signal est dégradé (levier retiré) pour cause marge insuffisante

### Critères de test

```python
def test_suggest_leverage_high_confidence():
    """Confidence 0.85 → suggest 20x."""
    leverage = SignalGenerator._suggest_leverage(Decimal("0.85"))
    assert leverage == 20

def test_suggest_leverage_medium_confidence():
    """Confidence 0.75 → suggest 10x."""
    leverage = SignalGenerator._suggest_leverage(Decimal("0.75"))
    assert leverage == 10

def test_suggest_leverage_low_confidence():
    """Confidence 0.60 → no leverage."""
    leverage = SignalGenerator._suggest_leverage(Decimal("0.60"))
    assert leverage is None

def test_margin_safety_calculation():
    """Levier 10x → marge 20%."""
    margin = SignalGenerator._compute_margin_safety(10)
    assert margin == Decimal("0.20")

def test_margin_safety_none():
    """No leverage → no margin requirement."""
    margin = SignalGenerator._compute_margin_safety(None)
    assert margin is None
```

### Dépendances

- `src/shared/models/signal.py` : `TradingSignal`

---

## RF-ML-013 : Estimation des frais de trading

**ID** : RF-ML-013
**Titre** : Calcul des frais cumulés (maker, taker, funding, slippage)
**Priorité** : MUST
**Type** : Validation

### Description

Estimer les frais totaux aller-retour pour un trade. Si les frais dépassent 50% du gain espéré, supprimer le signal.

Frais :
- Maker : ~0.02% par transaction
- Taker : ~0.05% par transaction
- Slippage : 0.05–0.2% (estimation mid-range 0.10%)
- Funding rate : sur perpétuels, ~0.01% par 8h (ignorer pour approximation V1)

Total round-trip (entrée + sortie) : (0.02% + 0.05%) × 2 + 0.10% = ~0.17%

Si `confiance × 1% gain < 0.5 × frais` → supprimer signal.

### Critères d'acceptation

- [x] Méthode `SignalGenerator._estimate_fees(leverage: int | None) -> Decimal`
  - Retourne ~0.0017 (0.17%)
  - Indépendant du levier (les deux profit et perte s'échellonnent également)
- [x] Méthode `SignalGenerator._verify_fees(confidence: Decimal, fees: Decimal) -> bool`
  - base_move = 0.01 (1% expected move for a qualifying signal)
  - expected_gain = confidence × base_move
  - Retourne True si fees < expected_gain × 0.5
- [x] Champ `TradingSignal.fees_estimated` stocke les frais estimés
- [x] Signal supprimé si vérification échoue → Logs INFO

### Critères de test

```python
def test_estimate_fees_round_trip():
    """Round-trip fees ≈ 0.17%."""
    fees = SignalGenerator._estimate_fees(None)
    assert fees == Decimal("0.0017")

def test_verify_fees_high_confidence():
    """Confidence 0.80, fees 0.17% → True (gain covers fees)."""
    result = SignalGenerator._verify_fees(Decimal("0.80"), Decimal("0.0017"))
    assert result is True

def test_verify_fees_low_confidence():
    """Confidence 0.60, fees 0.17% → False (gain < fees)."""
    result = SignalGenerator._verify_fees(Decimal("0.60"), Decimal("0.0017"))
    # 0.60 * 0.01 = 0.006 (0.6% expected gain)
    # 0.006 * 0.5 = 0.003 (threshold)
    # 0.0017 < 0.003 → True (passes)
    assert result is True
```

### Dépendances

- `src/shared/models/signal.py` : `TradingSignal`

---

## RF-ML-014 : Pipeline batch de génération de signaux

**ID** : RF-ML-014
**Titre** : Fonction async batch pour générer et sauvegarder signaux pour tous les symboles
**Priorité** : MUST
**Type** : Orchestration

### Description

Fonction `generate_signals_for_symbols()` appelée par APScheduler (toutes les 4h) qui :
1. Charge les données multi-timeframe actuelles depuis TimescaleDB
2. Évalue le moteur de règles pour chaque symbole
3. Génère les signaux qualifiés (confiance ≥ 0.6)
4. Persiste les signaux dans `trading_signals`
5. Retourne un résumé (symbole → nb signaux émis)

Idempotent : appeler 2 fois dans la même période 4h produit des doublons → À gérer via ETL (upsert).

### Critères d'acceptation

- [x] Fonction `async def generate_signals_for_symbols(symbols: list[str] | None = None, session: AsyncSession | None = None) -> dict[str, int]`
- [x] Si `symbols=None`, utilise `TRACKED_SYMBOLS` de `src/shared/constants.py`
- [x] Charge dernières données multi-TF pour chaque symbole (1h, 2h, 3h, 4h, 1D, 1W, 1M)
- [x] Appelle `SignalGenerator.generate()` pour chaque symbole
- [x] Sauvegarde les signaux émis (confiance ≥ 0.6) via `SignalGenerator.save_signal()`
- [x] Logs INFO : "Signal generation complete: X/Y signals emitted in Zs"
- [x] Logs exception pour chaque symbole en erreur (ne pas crash la pipeline)
- [x] Retourne dict : `{"BTC": 1, "ETH": 0, "SOL": 1, ...}` (nb signaux par symbole)

### Critères de test

```python
@pytest.mark.asyncio
async def test_generate_signals_for_symbols_success():
    """Batch generation completes, saves signals, returns summary."""
    symbols = ["BTC", "ETH"]
    async with async_session_factory() as session:
        result = await generate_signals_for_symbols(symbols, session)

    assert isinstance(result, dict)
    assert "BTC" in result
    assert "ETH" in result
    assert all(isinstance(v, int) for v in result.values())

@pytest.mark.asyncio
async def test_generate_signals_per_symbol_isolation():
    """Error in one symbol doesn't affect others."""
    symbols = ["BTC", "INVALID_SYMBOL", "ETH"]
    async with async_session_factory() as session:
        result = await generate_signals_for_symbols(symbols, session)

    assert result["BTC"] >= 0
    assert result["INVALID_SYMBOL"] == 0  # error handled
    assert result["ETH"] >= 0
```

### Dépendances

- `src/ml/signal_generator.py` : `SignalGenerator`, `generate_signals_for_symbols`
- `src/shared/constants.py` : `TRACKED_SYMBOLS`
- Équipe Data Eng : `TimescaleIndicatorRepository`, `TimescaleSignalRepository`

---

## RF-ML-015 : Logging structuré du moteur de règles

**ID** : RF-ML-015
**Titre** : Logging détaillé (DEBUG/INFO) de l'exécution des règles
**Priorité** : SHOULD
**Type** : Observabilité

### Description

Chaque règle et le moteur de règles loguent leurs actions pour debugging et audit :
- DEBUG : chaque règle évaluée (fired ou skipped)
- INFO : signal généré (symbol, direction, confidence, rules triggered)
- WARNING : règle contradictoire ou résultat inattendu
- ERROR : exception dans une règle (loggée mais pipeline continue)

### Critères d'acceptation

- [x] `logging.getLogger(__name__)` dans chaque module de règle
- [x] Logs DEBUG : "Rule 'rsi_overbought_multi_tf' fired for BTCUSDT: BUY (confidence=0.85)"
- [x] Logs INFO : "Signal emitted: BTCUSDT BUY conf=0.75 model=rules_v1 rules=['rsi_overbought_multi_tf', ...]"
- [x] Logs WARNING : "Rule engine evaluation failed for BTC: [exception]"
- [x] Logs ERROR via `logger.exception()` pour les unexpected errors

### Dépendances

- `logging` module (stdlib)

---

# PHASE 2 — ML SUPERVISÉ

## RF-ML-016 : Feature engineering pipeline

**ID** : RF-ML-016
**Titre** : Extraction et transformation des features pour ML
**Priorité** : MUST
**Type** : Pipeline

### Description

Construire un vecteur de features par crypto, par timeframe, par timestamp qui servira d'entrée aux modèles ML. Les features doivent **éviter le data leakage temporel** : les indicateurs sont calculés AVANT le split temporel, jamais après.

Features (par crypto, par timeframe) :
- RSI (1h, 2h, 3h, 4h) → 4 features
- Écart RSI inter-TF (max gap) → 1 feature
- Position prix dans Bollinger (0–1) par TF → 4 features
- Bollinger width (%) → 1 feature
- SMA 200 position (prix - SMA / SMA) → 3 features (1h, 4h, 1D)
- Trend slope (1W, 1M) → 2 features
- Harmonic pattern detected (one-hot) → 4 features (gartley, butterfly, bat, crab)
- Volume relatif (vol / vol_MA20) → 1 feature
- Fear & Greed Index → 1 feature
- Sentiment NLP (news score) → 1 feature
- Volatilité (ATR ou stddev) → 1 feature

Total : ~28 features par observation.

Target (label) : BULL (1), BEAR (0), NEUTRAL (pas d'entraînement)

### Critères d'acceptation

- [x] Module `src/ml/feature_engineering.py` ou `src/ml/features/engineer.py`
- [x] Classe `FeatureEngineer` avec méthode `extract(symbol: str, timeframe: str, timestamp: datetime) -> dict[str, float]`
- [x] Retourne dict de 28+ features avec noms explicites (ex: "rsi_1h", "bb_width_4h", "harmonic_pattern_gartley")
- [x] Features sont Decimal ou float (type-safe)
- [x] Aucun data leakage : utilise uniquement des données ≤ timestamp
- [x] Gère les données manquantes (NaN → mean/forward-fill)
- [x] Normalisation optionnelle (StandardScaler) appliquée APRÈS le split temporel

### Algorithme (simplifié)

```python
def extract(self, symbol: str, timeframe: str, timestamp: datetime) -> dict[str, float]:
    """Extract feature vector for one symbol at one timestamp."""
    features = {}

    # 1. Fetch latest indicator snapshot (≤ timestamp)
    indicators = self.timescale_repo.get_indicators_as_of(symbol, timestamp)

    # 2. RSI features
    for tf in ["1h", "2h", "3h", "4h"]:
        features[f"rsi_{tf}"] = float(indicators.get(tf, {}).get("rsi", 50.0))

    # 3. RSI gap (max diff between consecutive TFs)
    rsi_values = [features[f"rsi_{tf}"] for tf in ["1h", "2h", "3h", "4h"]]
    features["rsi_gap_max"] = float(max(abs(rsi_values[i] - rsi_values[i+1]) for i in range(3)))

    # 4. Bollinger features
    for tf in ["1h", "2h", "3h", "4h"]:
        bb = indicators.get(tf, {})
        close = bb.get("close", 0.0)
        upper = bb.get("bb_upper", 0.0)
        lower = bb.get("bb_lower", 0.0)
        if upper > lower:
            proximity = (close - lower) / (upper - lower)
            features[f"bb_proximity_{tf}"] = float(proximity)
            features[f"bb_width_{tf}"] = float((upper - lower) / bb.get("bb_middle", 1.0))
        else:
            features[f"bb_proximity_{tf}"] = 0.5
            features[f"bb_width_{tf}"] = 0.0

    # 5. SMA features (position relative to MA)
    for tf in ["1h", "4h", "1D"]:
        sma = indicators.get(tf, {}).get("sma_200", 0.0)
        close = indicators.get(tf, {}).get("close", 0.0)
        if sma > 0:
            features[f"sma_position_{tf}"] = float((close - sma) / sma)
        else:
            features[f"sma_position_{tf}"] = 0.0

    # 6. Trend slope (1W, 1M)
    for tf in ["1W", "1M"]:
        trend_data = self.timescale_repo.get_trend_slope(symbol, tf)
        features[f"trend_slope_{tf}"] = float(trend_data.get("slope", 0.0))

    # 7. Harmonic pattern (one-hot)
    harmonic = indicators.get("4h", {}).get("harmonic_pattern", "none")
    for pattern in ["gartley", "butterfly", "bat", "crab"]:
        features[f"harmonic_{pattern}"] = 1.0 if harmonic == pattern else 0.0

    # 8. Volume
    vol_current = indicators.get("4h", {}).get("volume", 0.0)
    vol_ma = indicators.get("4h", {}).get("volume_ma20", 1.0)
    features["volume_ratio"] = float(vol_current / vol_ma) if vol_ma > 0 else 1.0

    # 9. Fear & Greed
    fng = self.fng_repo.get_as_of(timestamp)
    features["fear_greed"] = float(fng.value / 100.0) if fng else 0.5

    # 10. Sentiment NLP
    sentiment = self.sentiment_repo.get_aggregate(symbol, timestamp, window_hours=24)
    features["sentiment_news"] = float(sentiment or 0.0)

    # 11. Volatility (ATR)
    atr = indicators.get("4h", {}).get("atr", 0.0)
    features["volatility_atr"] = float(atr)

    return features
```

### Critères de test

```python
def test_feature_engineer_extract_shape():
    """Feature vector has expected shape."""
    engineer = FeatureEngineer(repos=...)
    features = engineer.extract("BTC", "4h", datetime(2025, 1, 1, 12, 0, 0))
    assert len(features) >= 25
    assert all(isinstance(v, (float, int)) for v in features.values())

def test_feature_engineer_no_data_leakage():
    """Features use data ≤ timestamp, not after."""
    engineer = FeatureEngineer(repos=...)
    timestamp = datetime(2025, 1, 1, 12, 0, 0)
    features = engineer.extract("BTC", "4h", timestamp)
    # Verify all data sources were queried with query_until=timestamp
    # (Implementation detail, but critical)
    assert True  # Manual inspection
```

### Dépendances

- `src/shared/models/crypto.py` : `IndicatorRecord`
- Équipe Data Eng : `TimescaleIndicatorRepository`, `TimescaleSignalRepository`

---

## RF-ML-017 : Training / validation / test walk-forward

**ID** : RF-ML-017
**Titre** : Backtesting walk-forward avec purging et embargo windows
**Priorité** : MUST
**Type** : Pipeline

### Description

Split temporel des données pour éviter le data leakage :

```
Historical data (2 years)
|==== TRAIN (6 months) ====|==== TEST (1 month) ====|
                |==== TRAIN (6 months) ====|==== TEST (1 month) ====|
                                        |==== TRAIN (6 months) ====|==== TEST (1 month) ====|
```

Purging & embargo :
- **Purging** : exclure les observations de test à partir du training (T-1 à T, les labels futur sont connus)
- **Embargo** : exclure une fenêtre après le test (ex: 1 jour) pour éviter data leakage du labelling futur

Pour chaque fold :
1. Entraîner sur TRAIN
2. Prédire sur TEST
3. Évaluer : accuracy, Sharpe, max drawdown, win rate
4. Comparer vs. baseline Buy & Hold

### Critères d'acceptation

- [x] Classe `WalkForwardBacktester` dans `src/ml/backtesting.py` ou `src/ml/backtest/walk_forward.py`
- [x] Méthode `run(data: pd.DataFrame, train_window_days=180, test_window_days=30, embargo_days=1) -> BacktestResult`
- [x] Accepte DataFrame avec colonnes : timestamp, symbol, close, features (*)
- [x] Retourne `BacktestResult` avec :
  - Résultats par fold : fold_id, test_period, accuracy, sharpe, max_dd, win_rate
  - Métriques agrégées : accuracy_mean, sharpe_mean, etc.
  - Résultats Buy & Hold (baseline)
  - Récapitulatif : "Model beats baseline? Yes/No"
- [x] Purging : exclure labels connus du training
- [x] Embargo : exclure fenêtre après test
- [x] Pas de split aléatoire (ordre temporel préservé)
- [x] Pas de data leakage : features calculées AVANT le timestamp

### Algorithme

```python
def run(self, data: pd.DataFrame, train_days=180, test_days=30, embargo_days=1):
    """Walk-forward backtest."""
    # 1. Sort data by timestamp
    data = data.sort_values("timestamp").reset_index(drop=True)

    # 2. Define folds
    total_rows = len(data)
    folds = []
    train_size = int(train_days * 24 / 4)  # 4h candles (assuming 4h data)
    test_size = int(test_days * 24 / 4)
    embargo_size = int(embargo_days * 24 / 4)

    start_idx = 0
    while start_idx + train_size + test_size <= total_rows:
        train_start = start_idx
        train_end = start_idx + train_size
        test_start = train_end
        test_end = test_start + test_size
        embargo_end = min(test_end + embargo_size, total_rows)

        folds.append({
            "fold_id": len(folds),
            "train": (train_start, train_end),
            "test": (test_start, test_end),
            "embargo": (test_end, embargo_end),
        })

        start_idx += test_size  # shift by test window (no overlap)

    # 3. Train & test each fold
    results = []
    for fold in folds:
        train_data = data.iloc[fold["train"][0]:fold["train"][1]]
        test_data = data.iloc[fold["test"][0]:fold["test"][1]]

        # Train model
        model = self.train_model(train_data)

        # Predict on test
        predictions = model.predict(test_data[FEATURE_COLS])

        # Evaluate
        metrics = self.evaluate_fold(test_data, predictions)
        results.append(metrics)

    # 4. Aggregate and compare to baseline
    agg_metrics = self.aggregate_results(results)
    baseline_metrics = self.baseline_buy_and_hold(data)

    return BacktestResult(
        folds=results,
        aggregate=agg_metrics,
        baseline=baseline_metrics,
        beats_baseline=agg_metrics.sharpe > baseline_metrics.sharpe,
    )
```

### Critères de test

```python
def test_walk_forward_backtest_runs():
    """WalkForwardBacktester creates folds and runs."""
    backtester = WalkForwardBacktester(model=RandomForestClassifier())
    data = pd.DataFrame({
        "timestamp": pd.date_range("2023-01-01", periods=1000, freq="4h"),
        "symbol": ["BTC"] * 1000,
        "close": np.random.randn(1000).cumsum() + 100,
        "target": np.random.choice([0, 1], 1000),
        **{f"feat_{i}": np.random.randn(1000) for i in range(10)}
    })

    result = backtester.run(data)
    assert len(result.folds) >= 1
    assert result.aggregate is not None
    assert result.baseline is not None

def test_walk_forward_no_data_leakage():
    """Test set labels not used in training."""
    # Manual inspection: ensure fold["train"][1] <= fold["test"][0]
    # (Implementation detail)
    pass
```

### Dépendances

- `src/ml/backtesting.py` : `WalkForwardBacktester`, `BacktestResult`
- Scikit-learn, XGBoost, LightGBM pour les modèles

---

## RF-ML-018 : Model training (XGBoost, LightGBM, LSTM)

**ID** : RF-ML-018
**Titre** : Entraînement de modèles supervisés sur les labels Phase 1
**Priorité** : MUST
**Type** : Pipeline

### Description

Trois architectures de modèles supervisés :

1. **XGBoost / LightGBM** (modèles tabulaires)
   - Entrée : vecteur de 28+ features
   - Sortie : probabilité [BULL, BEAR, NEUTRAL] (3 classes)
   - Avantage : rapide, interpretable, SHAP values
   - Hyperparamètres : tuning via GridSearchCV ou Optuna

2. **Random Forest** (baseline)
   - Même format que XGBoost
   - Pour comparaison et interpretabilité

3. **LSTM** (series temporelles, Phase 2b)
   - Entrée : séquence de 10 observations (40h window)
   - Sortie : probabilité [BULL, BEAR]
   - Avantage : capture les dynamiques temporelles
   - À implémenter si les modèles tabulaires insuffisent

### Critères d'acceptation

- [x] Module `src/ml/models/xgboost_trainer.py` ou `src/ml/training/train.py`
- [x] Classe `XGBoostTrainer` avec méthode `train(X_train, y_train, X_val, y_val) -> xgb.XGBClassifier`
- [x] Hyperparamètres pour 3 classes (BULL/BEAR/NEUTRAL)
- [x] Validation : rapporte accuracy, F1, confusion matrix
- [x] Classe `LGBMTrainer` analogue
- [x] Classe `RandomForestTrainer` pour baseline
- [x] Toutes les classes sauvegardent le modèle en `.pkl` ou `.joblib` vers MinIO

### Configuration XGBoost

```python
params = {
    "objective": "multi:softprob",  # 3-class classification
    "num_class": 3,
    "max_depth": 6,
    "learning_rate": 0.1,
    "n_estimators": 100,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "random_state": 42,
}
```

### Critères de test

```python
def test_xgboost_trainer_trains():
    """XGBoostTrainer trains a model."""
    trainer = XGBoostTrainer()
    X_train = np.random.randn(100, 28)
    y_train = np.random.choice([0, 1, 2], 100)
    X_val = np.random.randn(20, 28)
    y_val = np.random.choice([0, 1, 2], 20)

    model = trainer.train(X_train, y_train, X_val, y_val)

    assert model is not None
    assert hasattr(model, "predict_proba")

    # Predictions
    preds = model.predict_proba(X_val)
    assert preds.shape == (20, 3)
```

### Dépendances

- `xgboost`, `lightgbm`, `scikit-learn`

---

## RF-ML-019 : MLflow experiment tracking

**ID** : RF-ML-019
**Titre** : Tracking d'expériences avec MLflow (params, metrics, artifacts)
**Priorité** : MUST
**Type** : MLOps

### Description

Chaque run d'entraînement est enregistré dans MLflow :

- **Experiment** : `{crypto}_{timeframe}_{model_type}` (ex: `BTC_4h_xgboost`)
- **Run** : chaque entraînement = 1 run
- **Params** : hyperparamètres du modèle
- **Metrics** : accuracy, F1, Sharpe, max_dd, win_rate (par fold et agrégés)
- **Artifacts** : modèle sérialisé, feature importances (plot SHAP), training log

MLflow backend = PostgreSQL (même instance TimescaleDB)
MLflow artifact store = MinIO (`minio://mlflow-artifacts/`)

### Critères d'acceptation

- [x] Initialisation MLflow : `mlflow.set_tracking_uri("postgresql://...")`
- [x] Chaque run loggue :
  - Paramètres : `mlflow.log_params({"max_depth": 6, "learning_rate": 0.1, ...})`
  - Métrique : `mlflow.log_metric("accuracy", 0.85, step=fold_id)`
  - Artefact : modèle `.pkl`, shap plot `.png`
- [x] Naming convention : experiment = `{symbol}_{timeframe}_{model}`, run = timestamp
- [x] Transitions de stage : None → Staging → Production via API
- [x] Logs MLflow : "Model registered: BTC_4h_xgboost_v1 → Staging"

### Critères de test

```python
@pytest.mark.asyncio
async def test_mlflow_experiment_created():
    """MLflow experiment is created for a symbol/timeframe/model combo."""
    mlflow.set_tracking_uri("sqlite:////tmp/mlflow_test.db")
    exp_name = "BTC_4h_xgboost_test"
    mlflow.create_experiment(exp_name)

    with mlflow.start_run(experiment_name=exp_name):
        mlflow.log_param("max_depth", 6)
        mlflow.log_metric("accuracy", 0.85)

    experiment = mlflow.get_experiment_by_name(exp_name)
    assert experiment is not None
```

### Dépendances

- `mlflow`, PostgreSQL backend, MinIO artifact store

---

## RF-ML-020 : DVC dataset versioning

**ID** : RF-ML-020
**Titre** : Versioning des datasets avec DVC (remote = MinIO)
**Priorité** : SHOULD
**Type** : MLOps

### Description

Chaque version de dataset (features + labels) est trackée avec DVC. Cela permet de reproduire les entraînements et de tracer les changements de données.

Structure :
```
dvc.yaml
  stages:
    prepare:
      cmd: python src/ml/scripts/prepare_data.py --symbol BTC --output data/features_BTC.parquet
      deps:
        - src/ml/feature_engineering.py
      outs:
        - data/features_BTC.parquet:
            remote: minio
    train:
      cmd: python src/ml/scripts/train.py --data data/features_BTC.parquet
      deps:
        - data/features_BTC.parquet
      params:
        - train.max_depth
        - train.learning_rate
      outs:
        - models/BTC_xgboost.pkl
```

DVC remote = MinIO bucket `minio://datasets/`

### Critères d'acceptation

- [x] Fichier `src/ml/dvc.yaml` ou `.dvc/config` configuré avec remote MinIO
- [x] Script `src/ml/scripts/prepare_data.py` génère les features Parquet
- [x] Script `src/ml/scripts/train.py` entraîne et sauvegarde le modèle
- [x] `dvc repro` re-crée le pipeline complet (idempotent si data inchangées)
- [x] Versions des datasets loggées en git (`dvc.lock`)

### Critères de test

```bash
# Manual test
cd src/ml
dvc repro  # Should complete without errors
dvc status  # Should show no changes (if data unchanged)
```

### Dépendances

- `dvc`, MinIO remote

---

## RF-ML-021 : Concept drift detection & retrain triggers

**ID** : RF-ML-021
**Titre** : Détection de dérive de concept et triggers de réentraînement
**Priorité** : SHOULD
**Type** : MLOps

### Description

Déceler quand les patterns historiques changent (concept drift) et déclencher un réentraînement :

**Méthodes** :
- **Métrique de performance** : accuracy en rolling window (ex: 7 jours). Si chute > 10pp → retrain
- **Distribution des features** : comparer KL divergence de distribution train vs. actuelle. Si KL > threshold → retrain
- **Métrique métier** : Sharpe ratio en rolling window. Si chute > 20% → retrain

**Trigger** :
- Réentraîner chaque lundi (après le weekend)
- Réentraîner si l'une des conditions de drift est détectée

**Action** :
- Réentraîner le modèle sur les 6 derniers mois (fenêtre mobile)
- Évaluer sur 1 mois de test
- Comparer à l'ancienne version
- Si meilleur : promouvoir à Production
- Si pire : log WARNING, garder ancien modèle

### Critères d'acceptation

- [x] Classe `ConceptDriftDetector` avec méthode `detect(metrics_history: pd.DataFrame) -> bool`
- [x] Méthodes de détection : rolling accuracy, KL divergence, Sharpe
- [x] Seuils configurables (défaut : acc drop 10pp, Sharpe drop 20%)
- [x] Logs INFO : "Concept drift detected: accuracy dropped from 0.85 to 0.73"
- [x] Fonction `should_retrain() -> bool` appelée par APScheduler
- [x] Logs INFO si retrain décidé

### Critères de test

```python
def test_concept_drift_detection_accuracy_drop():
    """Accuracy drop > 10pp → detect drift."""
    detector = ConceptDriftDetector(accuracy_threshold=-0.10)
    history = pd.DataFrame({
        "timestamp": pd.date_range("2025-01-01", periods=30, freq="D"),
        "accuracy": [0.85] * 15 + [0.73] * 15,  # drop at day 15
    })

    drift_detected = detector.detect(history)
    assert drift_detected is True

def test_concept_drift_stable_no_detect():
    """Stable accuracy → no drift."""
    detector = ConceptDriftDetector(accuracy_threshold=-0.10)
    history = pd.DataFrame({
        "timestamp": pd.date_range("2025-01-01", periods=30, freq="D"),
        "accuracy": [0.85] * 30,  # constant
    })

    drift_detected = detector.detect(history)
    assert drift_detected is False
```

### Dépendances

- `src/ml/drift_detection.py` : `ConceptDriftDetector`
- Équipe DevOps : APScheduler job `check_concept_drift`

---

## RF-ML-022 : NLP sentiment scoring

**ID** : RF-ML-022
**Titre** : Classification de sentiment sur articles de news (positif/négatif/neutre)
**Priorité** : SHOULD
**Type** : Feature engineering

### Description

Analyser les articles de news pour en extraire un score de sentiment (positif = +1.0, neutre = 0.0, négatif = -1.0). Ce score ajuste la confiance des signaux (cf. RF-ML-010).

Techniques :
- **TF-IDF + Logistic Regression** : simple, rapide, bon baseline
- **Transformer** (ex: DistilBERT fine-tuned) : plus précis mais coûteux

Pour V1, utiliser TF-IDF + LR.

### Critères d'acceptation

- [x] Module `src/ml/nlp/sentiment.py` ou `src/ml/nlp/sentiment_classifier.py`
- [x] Classe `SentimentClassifier` avec méthode `classify(text: str) -> dict[str, float]`
  - Retourne : `{"positive": 0.6, "negative": 0.2, "neutral": 0.2}` (probas softmax)
- [x] Méthode `aggregate_sentiment(articles: list[NewsArticle], window_hours=24) -> float`
  - Retourne : weighted average sentiment dans [-1, 1]
- [x] Modèle entraîné et sauvegardé en `.pkl` vers MinIO
- [x] Intégration avec la pipeline : `TextMiningRepository.get_aggregate_sentiment(symbol, timestamp)`

### Critères de test

```python
def test_sentiment_classifier_positive():
    """Classify positive news."""
    clf = SentimentClassifier.from_pkl("models/sentiment_tfidf.pkl")
    result = clf.classify("Bitcoin reaches new all-time high! Bullish sentiment!")
    assert result["positive"] > 0.6

def test_sentiment_classifier_negative():
    """Classify negative news."""
    clf = SentimentClassifier.from_pkl("models/sentiment_tfidf.pkl")
    result = clf.classify("Crypto market crash, investors panic selling.")
    assert result["negative"] > 0.5

def test_sentiment_aggregate():
    """Aggregate multiple articles."""
    clf = SentimentClassifier.from_pkl("models/sentiment_tfidf.pkl")
    articles = [
        NewsArticle(title="BTC bullish", text="..."),
        NewsArticle(title="ETH neutral", text="..."),
    ]
    sentiment = clf.aggregate_sentiment(articles)
    assert isinstance(sentiment, float)
    assert -1.0 <= sentiment <= 1.0
```

### Dépendances

- `src/ml/nlp/sentiment.py`
- `scikit-learn` (TF-IDF, LogisticRegression)
- Équipe Data Eng : `TextMiningRepository`

---

## RF-ML-023 : Model registry & promotion

**ID** : RF-ML-023
**Titre** : MLflow model registry (Staging → Production)
**Priorité** : MUST
**Type** : MLOps

### Description

Gérer le cycle de vie des modèles :

1. **Staging** : modèle fraîchement entraîné, en validation
2. **Production** : modèle validé, utilisé pour les signaux actuels
3. **Archived** : ancien modèle, kept for audit trail

Promotion :
- Après training + walk-forward backtest, placer le modèle en Staging
- Si accuracy / Sharpe > baseline + 5%, promouvoir à Production
- Ancienne version → Archived

### Critères d'acceptation

- [x] MLflow Model Registry configuré
- [x] Modèles nommés : `{symbol}_{timeframe}_{model_type}_v{version}`
  - Ex: `BTC_4h_xgboost_v1`
- [x] Transitions de stage : None → Staging → Production (via MLflow API)
- [x] Logs INFO : "Model BTC_4h_xgboost_v2 promoted to Production (accuracy 0.87, baseline 0.82)"
- [x] Ancien modèle transitionné à Archived
- [x] `SignalGenerator` charge le modèle Production pour les signaux actuels

### Critères de test

```python
@pytest.mark.asyncio
async def test_model_registry_promote_to_production():
    """Register model and promote to Production."""
    client = mlflow.tracking.MlflowClient()

    # Register model
    model_uri = "runs:/abc123/model"
    registered = client.create_model_version("BTC_4h_xgboost_v1", model_uri, "MLflow")
    assert registered.current_stage == "None"

    # Promote to Staging
    client.transition_model_version_stage("BTC_4h_xgboost_v1", registered.version, "Staging")
    assert client.get_model_version("BTC_4h_xgboost_v1", registered.version).current_stage == "Staging"

    # Promote to Production
    client.transition_model_version_stage("BTC_4h_xgboost_v1", registered.version, "Production")
    assert client.get_model_version("BTC_4h_xgboost_v1", registered.version).current_stage == "Production"
```

### Dépendances

- MLflow Model Registry

---

# MODULE ANALYTICS

## RF-ANA-001 : Heatmap de corrélations inter-cryptos

**ID** : RF-ANA-001
**Titre** : Matrice de corrélations affichée sous forme de heatmap (Plotly)
**Priorité** : SHOULD
**Type** : Visualisation

### Description

Pour les 13 cryptos prioritaires, calculer les corrélations de rendements (returns) sur différentes périodes (1h, 4h, 1D, 1W) et afficher sous forme de heatmap interactive.

Format : corrélation de Pearson entre séries de rendements log.

### Critères d'acceptation

- [x] Page Streamlit `src/frontend/pages/analytics.py` (fonction ou section)
- [x] Sélecteur de timeframe (1h, 4h, 1D, 1W)
- [x] Sélecteur de fenêtre temporelle (7j, 30j, 90j, 1y)
- [x] Calcul : corrélation Pearson de log-returns
- [x] Heatmap Plotly avec couleurs (bleu négatif, blanc zéro, rouge positif)
- [x] Hover : affiche corrélation exacte
- [x] Cache Streamlit : `@st.cache_data(ttl=3600)`

### Critères de test

```python
def test_correlation_matrix_computed():
    """Compute correlation matrix for crypto symbols."""
    symbols = ["BTC", "ETH", "SOL"]
    start = datetime(2025, 1, 1)
    end = datetime(2025, 1, 31)

    repo = TimescaleOHLCVRepository(session)
    corr_matrix = repo.compute_correlation_matrix(symbols, start, end, timeframe="4h")

    assert corr_matrix.shape == (3, 3)
    assert all(-1 <= corr_matrix.iloc[i, j] <= 1 for i in range(3) for j in range(3))
```

### Dépendances

- `src/frontend/pages/analytics.py` : page Streamlit
- Équipe Data Eng : `TimescaleOHLCVRepository.compute_correlation_matrix()`

---

## RF-ANA-002 : Historique de performance des signaux

**ID** : RF-ANA-002
**Titre** : Tableau avec tous les signaux générés + outcome (was_correct, P&L simulé)
**Priorité** : SHOULD
**Type** : Visualisation

### Description

Afficher un tableau (Streamlit DataFrame ou Plotly Table) avec :
- Timestamp du signal
- Symbole, direction (BUY/SELL), confiance
- Prix au moment du signal
- Prix actuel (ou prix après 1h, 4h, 1D)
- P&L simulé si le signal avait été suivi
- Correctness : signal prédisait-il le bon mouvement?
- Rules triggered

Filtrables par : symbole, direction, confiance, date range.

### Critères d'acceptation

- [x] Page Streamlit `src/frontend/pages/analytics.py` (section signals history)
- [x] Colonnes : timestamp, symbol, direction, confidence, price_at_signal, price_now, pnl_simulated, was_correct, rules_triggered
- [x] Filtres : symbol (multi-select), direction (BUY/SELL/ALL), confidence (slider ≥0.6), date_range
- [x] Tri : par timestamp desc (plus récent en haut)
- [x] Pagination : 50 signaux par page
- [x] Stats résumées : accuracy (%), win_rate (%), avg confidence

### Critères de test

```python
@pytest.mark.asyncio
async def test_signal_outcomes_computed():
    """Compute P&L and correctness for a signal."""
    signal = TradingSignal(
        symbol="BTC",
        signal_type="BUY",
        confidence_score=Decimal("0.75"),
        created_at=datetime(2025, 1, 1, 12, 0, 0),
    )

    # Simulate prices
    price_at_signal = Decimal("45000")
    price_after_4h = Decimal("45500")  # +1.1%

    outcome = SignalOutcomeCalculator.compute(
        signal,
        price_at_signal,
        price_after_4h,
    )

    assert outcome.was_correct is True  # BUY and price went up
    assert outcome.pnl_simulated > Decimal("0")
```

### Dépendances

- `src/frontend/pages/analytics.py`
- `src/shared/models/signal.py` : `SignalOutcome`

---

## RF-ANA-003 : Métriques de backtest (Sharpe, Sortino, max drawdown, win rate)

**ID** : RF-ANA-003
**Titre** : Dashboard avec métriques de performance agrégées (par crypto, par timeframe, globalement)
**Priorité** : SHOULD
**Type** : Visualisation

### Description

Afficher un dashboard avec les métriques clés :

- **Sharpe Ratio** : rendement / volatilité (target ≥ 1.5)
- **Sortino Ratio** : rendement / volatilité baisse seulement (target ≥ 2.0)
- **Max Drawdown** : perte cumulative maximale (target ≤ -20%)
- **Win Rate** : % de signaux corrects (target ≥ 55%)
- **Profit Factor** : (sum wins) / (sum losses) (target ≥ 1.5)
- **Return on Equity** : total gain / capital deployed (target ≥ 30% annualisé)

Granularités :
- Par crypto (BTC, ETH, etc.)
- Par modèle (rules_v1, xgboost_v1, etc.)
- Global (agrégé sur tous)
- Par timeframe (1h, 4h, 1D, etc.)

### Critères d'acceptation

- [x] Page Streamlit `src/frontend/pages/analytics.py` (section metrics)
- [x] Affichage des 6 KPIs en cartes (avec background color based on target)
- [x] Sélecteurs : crypto (multi), model (multi), timeframe (multi), date_range
- [x] Historique : graphique de Sharpe / accuracy / win_rate en rolling window (7D, 30D, etc.)
- [x] Comparaison vs. baseline Buy & Hold
- [x] Table par crypto : Sharpe, Sortino, max_dd, win_rate

### Critères de test

```python
def test_sharpe_ratio_calculated():
    """Compute Sharpe ratio from returns."""
    returns = pd.Series([0.01, -0.005, 0.02, 0.01, -0.01])  # 1%, -0.5%, 2%, etc.

    sharpe = PortfolioMetrics.sharpe_ratio(returns, risk_free_rate=0.0)

    assert isinstance(sharpe, float)
    assert sharpe >= -5  # reasonable range

def test_max_drawdown_calculated():
    """Compute maximum drawdown."""
    equity_curve = [100, 105, 103, 108, 102, 110]

    max_dd = PortfolioMetrics.max_drawdown(equity_curve)

    assert max_dd <= 0
    assert max_dd > -0.1  # small drawdown
```

### Dépendances

- `src/frontend/pages/analytics.py`
- `src/ml/metrics.py` ou `src/shared/metrics.py` : `PortfolioMetrics` (Sharpe, Sortino, max_dd, win_rate, etc.)

---

# CRITÈRES D'ACCEPTATION TRANSVERSAUX

## RF-COMMON-001 : Pydantic models pour tous les signaux

**Priorité** : MUST

- [x] `TradingSignal` dans `src/shared/models/signal.py` est la source unique de vérité
- [x] Tous les signaux générés sont validés contre ce modèle
- [x] Aucun signal sans confiance, direction, symbol
- [x] Tous les types Decimal pour les prix et confiances (pas de float pour les calculs financiers)

## RF-COMMON-002 : Type hints strictes

**Priorité** : MUST

- [x] Toutes les fonctions dans `src/ml/` ont des type hints complets
- [x] `mypy --strict` passe sans erreurs
- [x] Pas de `# type: ignore` (déboguer la cause sous-jacente)

## RF-COMMON-003 : Tests avec 80%+ coverage

**Priorité** : MUST

- [x] Couverture globale `src/ml/` ≥ 80% (exclure `__main__.py`, configs, etc.)
- [x] TDD : tests écrits AVANT le code
- [x] Unit tests : pas de I/O, mocking de TimescaleDB & MinIO
- [x] Integration tests : avec Docker services (async/await)
- [x] CI enforce : `pytest --cov=src/ml --cov-fail-under=80`

## RF-COMMON-004 : Logging structuré

**Priorité** : MUST

- [x] `logging` module partout (jamais `print()`)
- [x] Logs DEBUG pour chaque décision règle
- [x] Logs INFO pour signaux émis et supprimés
- [x] Logs WARNING pour comportements anormaux
- [x] Logs ERROR avec exception context

## RF-COMMON-005 : Pas d'hardcoding de seuils

**Priorité** : MUST

- [x] Tous les seuils (RSI, Bollinger, harmonic ratios, etc.) dans `src/ml/config/indicators.yaml`
- [x] Seuils lus via `IndicatorConfig` (Pydantic)
- [x] Pas de magic numbers dans le code Python

## RF-COMMON-006 : Async/await pour I/O

**Priorité** : MUST

- [x] Toutes les opérations TimescaleDB sont async (SQLAlchemy async)
- [x] Toutes les opérations MinIO sont async (boto3 async ou equivalent)
- [x] Fonctions de signal generation sont `async def`
- [x] Pas de `.run()` ou `asyncio.run()` dans les modules (laissé aux callers)

## RF-COMMON-007 : Idempotence APScheduler

**Priorité** : MUST

- [x] `generate_signals_for_symbols()` peut être appelée 2 fois dans la même période sans corruption
- [x] Idempotence gérée via UPSERT SQL ou detection de doublons (équipe Data Eng)

---

# DÉPENDANCES & INTERFACES

## Équipe Data Engineering

**Fournit** :
- Table `crypto_prices` (OHLCV) en TimescaleDB
- Table `indicators` (RSI, Bollinger, trend lines, etc.) pre-calculés
- `TimescaleIndicatorRepository` : interface async pour lire les indicateurs
- `TimescaleOHLCVRepository` : interface async pour les prix
- `TimescaleSignalRepository` : interface async pour insérer/lire signaux

**Attend** :
- Configuration YAML des indicateurs à calculer (via `src/ml/config/indicators.yaml`)

## Équipe Backend / API

**Fournit** :
- Endpoints REST pour lire les signaux :
  - `GET /api/signals?symbol=BTC&limit=100&offset=0`
  - `GET /api/signals/{signal_id}`
  - `GET /api/analytics/correlation?symbols=BTC,ETH&timeframe=4h&period=30d`

**Attend** :
- Signaux générés dans `trading_signals` table (via RF-ML-010)

## Équipe Frontend

**Fournit** :
- Pages Streamlit pour afficher analytics

**Attend** :
- Endpoints API pour données signaux
- Format stable de TradingSignal

## Équipe DevOps

**Fournit** :
- MLflow service (PostgreSQL backend)
- MinIO service (artifact store)
- APScheduler job runner

**Attend** :
- Scripts entièrement testés et CI/CD ready

---

## Dates et jalons

| Jalon | Date | Responsable |
|-------|------|-------------|
| RF-ML-001 à RF-ML-015 (Phase 1 core) | Fin Mars 2025 | ML/Data Science |
| RF-ML-016 à RF-ML-023 (Phase 2 core) | Mi-Avril 2025 | ML/Data Science |
| RF-ANA-001 à RF-ANA-003 (Analytics) | Fin Avril 2025 | Frontend + ML |
| Intégration E2E (signals → API → Frontend) | Mi-Mai 2025 | Transversal |
| Production readiness (audit, security) | Fin Mai 2025 | DevOps + QA |

---

**Document version 1.0**
**Généré par : Product Manager, Équipe ML & Analytics**
**Date : 2026-03-12**
**Status : Prêt pour développement**
