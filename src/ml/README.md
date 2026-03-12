# ML — Equipe Data Science

Voir `docs/02-ml-data-science.md` pour le detail des taches et specifications.

## Structure attendue

```
src/ml/
├── __init__.py
├── config/
│   └── indicators.yaml     # Config des indicateurs (params, seuils, TF)
├── rules/
│   ├── engine.py            # Moteur de regles multi-TF
│   ├── rsi_rules.py         # Regles RSI
│   ├── bollinger_rules.py   # Regles Bollinger
│   ├── harmonic_rules.py    # Detection harmonic patterns
│   └── trend_rules.py       # Regles trend lines
├── models/
│   ├── trainer.py           # Entrainement des modeles supervises
│   ├── predictor.py         # Inference / generation de signaux
│   └── backtester.py        # Backtesting walk-forward
├── nlp/
│   ├── sentiment.py         # Analyse de sentiment
│   └── text_mining.py       # TF-IDF, word clouds, etc.
├── signal_generator.py      # Genere les signaux et les insert dans la BDD
├── dvc.yaml                 # Pipeline DVC
├── Dockerfile               # (si le ML tourne dans un container separe)
└── requirements.txt
```
