---
type: rncp-livrable
source: docs/rncp/bloc2-infrastructure/ml-justification-phase1.md
tags: [cryptobot, rncp, bloc2, ml, phase1, rules, justification]
created: 2026-04-14
ingested_by: agent-L2-IA-Justif
rncp_ref: RNCP38919
bloc: "Bloc 2 — Conception et developpement d'une solution technologique"
competence: "Justifier les algorithmes d'IA implementes au regard du besoin metier et des donnees disponibles"
---

# ML Phase 1 — Justification des algorithmes (rule engine)

> Livrable RNCP38919 Bloc 2. Justifie le choix rules-first, detaille chaque regle, agregation, corrections, et limites. Ground-truth : [[../../code/ml]], [[../../architecture/cl04-ml-rules-models]], `src/ml/rules/engine.py`, `src/ml/signal_generator.py`.

## 1. Objectif metier

Emettre des signaux `BUY / SELL / HOLD` **strictement informationnels** sur les cryptos du top 30 (priorite 13 : BTC, ETH, USDT, USDC, BNB, XRP, SOL, ADA, AVAX, DOT, DOGE, TRX, ATOM). Le systeme n'execute **aucun ordre** sur exchange reel ; il conseille trois personas (Noah agressif, Sarah conservatrice, Aleksandar educatif) avec des seuils de confiance differencies (cf. [[../../specs/PRD-phase2]]).

Contraintes :

- **Reglementaire** : pas de trade automatise = pas d'agrement PSAN / AMF. Les signaux sont des "informations d'aide a la decision".
- **Pedagogique** : projet d'ecole, chaque decision doit etre expliquee a un jury non-quant.
- **Financier** : APIs gratuites seulement (Binance public, CoinGecko Demo, CCXT, news RSS, Fear & Greed).

## 2. Choix d'une approche rules-first

Trois approches etaient possibles au demarrage du projet (septembre 2025) :

| Approche | Interpretabilite | Auditabilite decision | Requiert historique label | Demarrage froid |
|----------|------------------|-----------------------|---------------------------|-----------------|
| **Rule engine** (retenue Phase 1) | Totale (YAML lisible) | Chaque signal trace les regles declenchees | Non | Immediat |
| Supervised ML seul | Faible (boite noire) | Impossible sans SHAP/LIME lourd | Oui (>=2 ans labellises) | Bloque |
| Deep learning (LSTM) seul | Tres faible | Non auditable sans outils externes | Oui (grands volumes) | Bloque |

**Decision** : rule-first Phase 1, ML en complement Phase 2 (cf. [[CryptoBot/avril/rncp/livrables/L2-infrastructure/ml-phase2-scope-revise]]).

Justification first-principles :

1. Un signal non-executif doit **pouvoir etre explique** au persona qui le recoit ("pourquoi BUY ?" -> "RSI 1h/4h converge + band-walking haute + pattern Gartley termine").
2. Sans historique labellise propre (`trades.signal_id` inexistant au Sprint 1), un modele supervise n'a rien a apprendre.
3. Les regles encodent l'expertise trader fournie par le client (doc de cadrage V1) sans probleme de fuite temporelle.

## 3. Regle RSI multi-TF

**Formule** : RSI(14) = 100 - 100 / (1 + RS) ou RS = moyenne des gains 14 periodes / moyenne des pertes 14 periodes.

**Parametrage** (`src/ml/config/indicators.yaml`, timeframes 1h/2h/3h/4h) :

- `overbought` : 70 -> biais SELL
- `oversold` : 30 -> biais BUY
- Convergence : BUY si >=3 des 4 TFs signalent oversold simultanement (supermajority sur `multi_tf_rules.py`).

**Ponderation dans l'agregation** : 0.25 (cf. `_RULE_WEIGHTS` dans `src/ml/rules/engine.py:20-25`).

**Sortie** : `RuleResult(rule_name="rsi_oversold_multi_tf_supermajority", direction="BUY", confidence=0.0-1.0, timeframe="4h", details=...)`.

## 4. Regle Bollinger Bands

**Formule** : SMA20 +/- 2 * ecart-type sur 20 periodes.

**Patterns detectes** (`src/ml/rules/bollinger_rules.py`) :

- **Squeeze** : largeur des bandes < 10e percentile sur 100 periodes -> breakout imminent, direction a confirmer par volume.
- **Band walking** : >=3 bougies consecutives en contact avec la bande superieure (BUY continuation) ou inferieure (SELL continuation).
- **Breakout** : premiere bougie hors bande apres squeeze.

**Ponderation** : 0.25.

Helpers : `_band_width_pct`, `_detect_squeeze`, `_detect_breakout`, `_detect_band_walking`.

## 5. Regle Harmonic Patterns

**Patterns Fibonacci** (`src/ml/rules/harmonic_rules.py`) :

| Pattern | Ratio XA-AB | Ratio AB-BC | Ratio BC-CD | Type |
|---------|-------------|-------------|-------------|------|
| Bat | 0.382-0.500 | 0.382-0.886 | 1.618-2.618 | Reversal |
| Gartley | 0.618 | 0.382-0.886 | 1.272-1.618 | Reversal |
| Butterfly | 0.786 | 0.382-0.886 | 1.618-2.618 | Extension |
| Crab | 0.382-0.618 | 0.382-0.886 | 2.240-3.618 | Extension |

**Tolerance** : +/- 5 % sur chaque ratio (`_validate_ratio`).

**Ponderation** : 0.30 (poids le plus fort car patterns harmoniques sont les moins faciles a declencher -> quand ils passent, leur valeur informationnelle est elevee).

## 6. Regle Trend Lines

**Detection** (`src/ml/rules/trend_rules.py`) :

- **Lignes hebdo stables** : slope `abs(m) < 0.02 / candle`, R^2 >= 0.7 sur 12 semaines -> support/resistance macro.
- **Lignes mensuelles agressives** : slope `abs(m) >= 0.05 / candle`, R^2 >= 0.6 sur 6 mois -> tendance dominante.

**Confluence** : intersection ligne stable + ligne agressive au cours actuel +/- 0.5 % -> signal renforce.

**Ponderation** : 0.20.

Helpers : `_is_stable_trend`, `_is_aggressive_trend`, `_trend_direction`, `_compute_trend_confidence`.

## 7. Agregation

Implementee dans `RuleEngine.aggregate()` (`src/ml/rules/engine.py:202-302`).

**Formule** :

```
direction_scores[dir] = Somme(weight_i * confidence_i) pour chaque regle i votant dir
dominant = argmax(direction_scores)
raw_confidence = direction_scores[dominant] / weights[dominant]

# Penalite si votes opposes
if weights[opposing] > 0:
    opposition_ratio = scores[opposing] / (scores[dominant] + scores[opposing])
    raw_confidence *= (1 - opposition_ratio * 0.5)

final_confidence = min(raw_confidence, 1.0)
```

**Seuil d'emission** : `SIGNAL_CONFIDENCE_THRESHOLD = 0.6` (cf. `src/shared/constants.py`). Un score < 0.6 -> pas de signal emis (log "below threshold").

**Blend Rules + ML** (dans `SignalGenerator.generate()`, `signal_generator.py:115-130`) :

- Memes directions : `confidence = 0.6 * ml + 0.4 * rules` (ML dominant quand d'accord).
- Directions conflictuelles : `confidence = 0.4 * min(ml, rules)` (penalite forte).

Le 60/40 privilegie ML quand les deux convergent mais garde les regles comme garde-fou en cas de conflit.

## 8. Correction sentiment

Post-traitement NLP (`signal_generator.py:133-139`) :

```
sentiment_adj = news_sentiment * 0.05       # news_sentiment dans [-1.0, 1.0]
if direction == "BUY":
    confidence += sentiment_adj              # +5pp max
else:
    confidence -= sentiment_adj
confidence = clamp(confidence, 0.0, 0.95)    # cap 0.95
```

**Cap 0.95** : on ne force **jamais** une confiance absolue. Les marches restent imprevisibles, un modele qui s'affiche a 1.00 est un modele qui ment.

Source du sentiment : `src/ml/nlp/sentiment.py` (Logistic Regression sur TF-IDF, news RSS Decrypt + Cointelegraph + PhoenixNews).

## 9. Kill-switch fees

Verification finale (`signal_generator.py:354-371`) : si les frais cumules estimes depassent 50 % du gain attendu, le signal est supprime (HOLD implicite).

```
base_move = 0.01                              # 1% expected move for qualifying signal
expected_gain = confidence * base_move
fees = maker(0.02%) + taker(0.05%) + slippage(0.10%) = 0.17% round-trip
emit = (fees < 0.5 * expected_gain)
```

A conf = 0.6 : `expected_gain = 0.6%`, `fees < 0.3%` -> OK a 0.17 %.
A conf = 0.35 : `expected_gain = 0.35%`, `fees < 0.175%` -> rejete.

Ce kill-switch protege le persona des signaux marginaux ou les frais mangeraient le gain.

## 10. Leverage suggere

Barem par tier de confiance (`signal_generator.py:295-312`) :

| Confidence | Leverage suggere | Marge safety (2x) |
|------------|------------------|-------------------|
| >= 0.85 | 20x | 5 %  (box 2.5 % x 2) |
| >= 0.75 | 10x | 10 % (box 5 % x 2) |
| >= 0.65 | 5x  | 20 % (box 10 % x 2) |
| < 0.65  | aucun | N/A |

**Regle 2x constante** : la marge libre demandee est toujours 2x la taille du box de liquidation. Cette regle vient directement du doc de cadrage client et protege des liquidations sur volatilite intraday.

## 11. Limites connues

1. **Pas d'apprentissage** : les poids `{rsi: 0.25, bollinger: 0.25, harmonic: 0.30, trend: 0.20}` sont figes en YAML. Un changement de regime marche n'entraine pas de recalibrage auto.
2. **Overfitting humain** : les ponderations ont ete ajustees a l'oeil par le client sur sa propre experience, pas optimisees sur un training set. Biais de confirmation possible.
3. **Pas de regime-awareness** : BULL / BEAR / SIDEWAYS ne modifient pas les regles (la Phase 2 roadmap S16 ajoutera K-means clustering cf. [[CryptoBot/avril/rncp/livrables/L2-infrastructure/ml-phase2-scope-revise]]).
4. **Pas de cross-asset** : chaque symbole est evalue en silo ; correlations BTC-altcoins non exploitees.
5. **Latence donnees** : les indicateurs proviennent d'ETL APScheduler, rafraichissement 4h pour les timeframes longs -> un crash flash peut arriver entre deux ticks.

Ces limites sont la raison d'etre du blend Phase 2 (XGBoost + LightGBM apprennent des patterns que les regles ratent) et de la roadmap S14-S16.

## 12. Preuves

- **Tests unitaires** : couverture 100 % du module `src/ml/rules/` (cf. [[../../audit/remediation/phase3]]).
- **Coverage global** : `pyproject.toml` fixe `fail_under = 78` (contradiction #16 CLAUDE.md dit 80, a harmoniser).
- **Ground-truth code** : [[../../code/ml]] (outline complet, 20 fichiers, 24 classes, 78 fonctions publiques).
- **Diagrammes canoniques** : [[../../architecture/cl04-ml-rules-models]], [[../../architecture/c03-ml-components]].
- **ADR-010** : peripmetre Phase 2 acte dans [[../../history/decisions]].

## Liens

- [[CryptoBot/avril/rncp/livrables/L2-infrastructure/ml-phase2-scope-revise]] — scope livre vs roadmap
- [[../../code/ml]] — outline code source
- [[../../architecture/cl04-ml-rules-models]] — diagramme de classes
- [[../../architecture/c03-ml-components]] — composants ML
- [[../../meta/contradictions]] — lignes 19-22 resolues
- [[../../history/decisions]] — ADR-010
