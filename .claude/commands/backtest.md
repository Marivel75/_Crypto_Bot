# Backtest Strategy

Workflow de backtesting crypto complet.

## Etapes

### 1. Validation Strategie
Utiliser l'agent `crypto` pour valider la logique de la strategie :
- Les indicateurs choisis sont-ils coherents avec le timeframe ?
- Y a-t-il un edge theorique identifiable ?
- Les regles d'entree/sortie sont-elles non-ambigues ?

### 2. Infrastructure Check
Verifier l'infra de backtest existante dans le projet :
- Moteur de backtest disponible ?
- Donnees historiques presentes et a jour ?
- Pipeline de features fonctionnel ?

### 3. Implementation
Deleguer l'implementation a `codeagent` avec ces contraintes :
- Splits temporels stricts (pas de random split sur des series temporelles)
- Walk-forward avec fenetre glissante
- Purging : supprimer N barres entre train et test
- Embargo : buffer additionnel apres purging
- Transaction costs inclus (fees + slippage estime)

### 4. Metriques Obligatoires
Le rapport de backtest DOIT inclure :
- **Sharpe Ratio** (annualise)
- **Max Drawdown** (% et duree)
- **Win Rate** (%)
- **Profit Factor**
- **Nombre de trades**
- **Calmar Ratio**
- Equity curve avec drawdown overlay

### 5. Validation
- Comparer les resultats in-sample vs out-of-sample
- Verifier l'absence de look-ahead bias
- Tester la robustesse avec des parametres varies (+/- 20%)
- Si Sharpe < 0.5 out-of-sample, la strategie est rejetee

## Usage
```
/backtest <nom_strategie>
```
