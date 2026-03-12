# Frontend — Equipe UI

Voir `docs/04-frontend-ui.md` pour le detail des taches, wireframes et specifications.

## Structure attendue

```
src/frontend/
├── __init__.py
├── app.py                  # Point d'entree Streamlit
├── config.py               # Settings (API_URL, etc.)
├── api_client.py           # Client HTTP pour appeler le backend
├── pages/
│   ├── 1_dashboard.py      # Dashboard trader (Noah)
│   ├── 2_veille.py         # Veille news (Sarah)
│   ├── 3_portfolio.py      # Portfolio + chatbot (Aleksandar)
│   ├── 4_analytics.py      # Heatmap, analytics
│   └── 5_performance.py    # Performance des signaux
├── components/
│   ├── candlestick.py      # Composant graphique chandelier Plotly
│   ├── indicators.py       # Composant affichage indicateurs
│   ├── signal_card.py      # Composant carte de signal
│   ├── news_feed.py        # Composant fil de news
│   └── chatbot.py          # Composant chatbot
├── Dockerfile
└── requirements.txt
```

## Important

**Ne jamais acceder a la BDD directement.** Tout passe par l'API backend via `api_client.py`.
