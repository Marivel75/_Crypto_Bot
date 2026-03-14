# 02 — Equipe ML / Data Science

> **Lisez d'abord** `docs/00-overview.md` pour le contexte global du projet.

---

## Votre perimetre

Vous etes responsables de **tout ce qui touche a l'intelligence du systeme** : regles de trading, modeles ML, backtesting, MLOps.

| Vous gerez | Vous NE gerez PAS |
|-----------|-------------------|
| Systeme de regles multi-timeframes (Phase 1) | La collecte de donnees (equipe Data Eng) |
| Modeles ML supervises et non supervises (Phase 2) | Le calcul des indicateurs (equipe Data Eng les calcule, vous definissez lesquels) |
| Backtesting et evaluation des strategies | Les endpoints API (equipe Backend) |
| MLflow (tracking, registry) | L'interface Streamlit (equipe Frontend) |
| DVC (versioning datasets) | Docker/CI/CD (equipe DevOps) |
| NLP / text mining / sentiment | Le schema BDD (equipe Data Eng, mais vous inserez dans `trading_signals`) |

**Votre code va dans** : `src/ml/`
**Votre branche** : `ml/xxx`

---

## Ce que les autres equipes attendent de vous

| Equipe | Ce qu'elle attend | Interface |
|--------|------------------|-----------|
| **Data Eng** | La liste des indicateurs a calculer et leurs parametres | Fichier de config `src/ml/config/indicators.yaml` |
| **Backend** | Des signaux dans la table `trading_signals` avec un format stable | Insert SQL via SQLAlchemy, schema dans `src/shared/models/` |
| **Frontend** | Des signaux exploitables (type, confiance, regles, explications) | L'API sert les signaux (equipe Backend), vous les produisez |

## Ce que vous consommez

| Source | Quoi | Ou |
|--------|------|-----|
| **Data Eng** | Donnees OHLCV propres | Table `crypto_prices` |
| **Data Eng** | Indicateurs calcules par timeframe | Table `indicators` |
| **Data Eng** | Datasets d'entrainement | MinIO `minio://datasets/` |
| **Data Eng** | Articles de news + sentiment | Tables `news_articles`, `text_mining_results` |

---

## Approche en deux phases

### Phase 1 : Systeme de regles explicites multi-timeframes

**L'objectif** : definir des regles basees sur les indicateurs techniques qui detectent des configurations bull/bear. Le systeme doit comprendre les **timeframes locaux** — quand un indicateur atteint un seuil sur un TF, les TF adjacents ont des valeurs proches mais pas identiques, et c'est cette convergence qu'il faut detecter.

**Exemple concret** :
```
RSI sur 3h = 70 (surachat)
RSI sur 2h = 68 (proche surachat)
RSI sur 4h = 68 (proche surachat)
→ Convergence multi-TF detectee → Signal de surachat fort
```

**Indicateurs et regles a definir** :

| Indicateur | Regle | Multi-TF |
|------------|-------|----------|
| **RSI** | Surachat (>70) / survente (<30) — comparer les valeurs entre TF adjacents (1h, 2h, 3h, 4h) | Oui |
| **Bollinger Bands** | Prix vs bandes — squeeze (bandes resserrees) = volatilite a venir, breakout = signal | Oui |
| **RSI vs Bollinger (maison)** | Comparer le RSI et la position du prix dans les Bollinger — indicateur proprietaire de convergence | Oui |
| **Harmonic Patterns** | Detection de Gartley, Butterfly, etc. — utilise des trend lines locales | Oui |
| **Trend lines** | Trend weekly (stable) vs trend monthly (aggressive) — les dips en monthly sont plus importants mais la trend weekly tient | Weekly, Monthly |

**Principe des trend lines multi-TF** :
- La **trend weekly** est globalement stable et respectee
- La **trend monthly** peut etre plus aggressive (pentes plus fortes)
- Sur la trend weekly stable, on cherche les **patterns locaux** sur des TF plus petits (4h, 1D)
- Les **dips en monthly** sont plus importants en amplitude, mais la trend weekly sert de support

**Sortie** : chaque combinaison de regles produit un label :
- `BULL` : configuration haussiere
- `BEAR` : configuration baissiere
- `NEUTRAL` : pas de signal clair

### Phase 2 : Apprentissage supervise sur les patterns

Les labels generes par la Phase 1 deviennent les donnees d'entrainement pour un modele ML :

| Modele | Usage | Librairie |
|--------|-------|-----------|
| **XGBoost / LightGBM** | Classification BULL/BEAR/NEUTRAL | XGBoost, LightGBM |
| **Random Forest** | Baseline et interpretabilite | scikit-learn |
| **LSTM** | Series temporelles si les modeles tabulaires ne suffisent pas | TensorFlow / PyTorch |

**Features d'entree** (par crypto, par timeframe) :
- RSI par TF (1h, 2h, 3h, 4h, 1D)
- Ecart RSI entre TF adjacents (convergence)
- Position prix dans Bollinger par TF
- Bollinger squeeze (largeur des bandes)
- Trend slope par TF (1D, 1W, 1M)
- Harmonic pattern detecte (one-hot)
- Volume relatif
- Fear & Greed Index
- Sentiment NLP (si dispo)

**Objectif** : le modele ML doit **optimiser les parametres des indicateurs** par crypto et par timeframe. Par exemple, le seuil RSI optimal pour BTC sur 4h n'est peut-etre pas 70 mais 68 ou 72.

---

## Backtesting

| Parametre | Valeur |
|-----------|--------|
| Split | **Temporel uniquement** (jamais aleatoire) |
| Train window | 6 mois glissants |
| Test window | 1 mois |
| Baseline | Buy & hold sur la meme periode |
| Metriques | Accuracy, Sharpe simule, win rate, profit factor |

```
Donnees historiques (ex: 2 ans)
|===TRAIN (6 mois)===|==TEST (1 mois)==|
        |===TRAIN (6 mois)===|==TEST (1 mois)==|
                |===TRAIN (6 mois)===|==TEST (1 mois)==|
```

> **IMPORTANT** : ne jamais faire de split aleatoire. Les donnees financieres sont temporelles, un split aleatoire = data leakage = resultats irrealistes.

---

## NLP / Text Mining

| Technique | Usage | Librairie |
|-----------|-------|-----------|
| TF-IDF | Ponderation des termes importants dans les articles | scikit-learn |
| Analyse de sentiment | Score positif/negatif/neutre | scikit-learn, NLTK |
| CountVectorizer | Vectorisation de textes | scikit-learn |
| Bag of Words | Representation textuelle | scikit-learn |

Les scores de sentiment sont stockes dans `news_articles.sentiment_score` par l'equipe Data Eng apres que vous ayez fourni le modele de scoring.

---

## MLOps

| Composant | Outil | Configuration |
|-----------|-------|---------------|
| Experiment tracking | MLflow | Backend store = PostgreSQL (meme instance) |
| Model registry | MLflow | Staging → Production |
| Artifact store | MinIO (`minio://mlflow-artifacts/`) | Modeles, figures, metriques |
| Dataset versioning | DVC | Remote = MinIO (`minio://datasets/`) |
| Notebooks | Jupyter | Exploration et prototypage |

### Convention MLflow

- **Experiment** : `{crypto}_{timeframe}_{model_type}` — ex: `BTC_4h_xgboost`
- **Run** : chaque entrainement = un run avec params, metriques, artefacts
- **Model name** : `{crypto}_{timeframe}_{model_type}_v{version}`
- **Stages** : `None` → `Staging` → `Production`

### Convention DVC

- Les datasets sont dans MinIO (`minio://datasets/`)
- Chaque version de dataset est trackee par DVC dans le repo Git
- Fichier `dvc.yaml` a la racine de `src/ml/` pour les pipelines reproductibles

---

## Signaux generes

Quand le systeme emet un signal, il insert dans `trading_signals` :

```python
# src/shared/models/signal.py
from pydantic import BaseModel
from datetime import datetime
from decimal import Decimal

class TradingSignal(BaseModel):
    symbol: str                          # ex: "BTC"
    signal_type: str                     # "BUY", "SELL", "HOLD"
    confidence_score: Decimal            # 0.0 a 1.0
    timeframe_primary: str               # TF principal du signal
    timeframes_aligned: dict             # {"1h": {"rsi": 68}, "4h": {"rsi": 70}, ...}
    rules_triggered: list[str]           # ["rsi_overbought_multi_tf", "bollinger_squeeze"]
    leverage_suggested: int | None       # levier suggere (optionnel)
    margin_safety: Decimal | None        # marge de securite calculee
    fees_estimated: Decimal | None       # frais estimes
    model_version: str                   # "rules_v1" ou "xgboost_v2"
```

### Verification levier et marge

Si un signal suggere un levier, calculer la marge de securite :
- Levier 5x → box 10% → marge requise = 2x la position (20%)
- Levier 10x → box 5% → marge requise = 2x la position (10%)
- Levier 20x → box 2.5% → marge requise = 2x la position (5%)

**Regle** : toujours 2x la position en marge libre pour eviter la liquidation. Si le capital ne le permet pas, degrader le signal.

### Verification des frais

Prendre en compte dans chaque signal :
- Frais maker : ~0.02%
- Frais taker : ~0.05%
- Funding rates : variables (toutes les 8h sur perpetuels)
- Slippage estime : 0.05-0.2% selon liquidite

Si frais cumules > gain espere → ne pas emettre le signal.

---

## Taches

### Sprint 5 (Janvier)
- [ ] Definir la config des indicateurs (`src/ml/config/indicators.yaml`)
- [ ] Implementer le systeme de regles multi-TF (Phase 1)
- [ ] Definir les seuils par indicateur et par TF
- [ ] Labelliser les donnees historiques (BULL/BEAR/NEUTRAL)

### Sprint 6 (Fevrier-Mars)
- [ ] Setup MLflow (backend=Postgres, artifacts=MinIO)
- [ ] Setup DVC (remote=MinIO)
- [ ] Entrainer modeles supervises (XGBoost, RF)
- [ ] Backtesting walk-forward
- [ ] Optimisation des parametres d'indicateurs
- [ ] NLP : modele de sentiment sur les news
- [ ] Evaluation : le modele bat-il buy & hold ?

### Sprint 7+ (Avril+)
- [ ] Generer des signaux en temps reel (inserer dans `trading_signals`)
- [ ] Modele de verification levier/marge
- [ ] Ajuster les modeles en continu
- [ ] Tests unitaires sur les regles et les modeles
