# Frontend — Pages et usage

```bash
streamlit run frontend/app.py   # http://localhost:8501
```

L'API doit être démarrée en parallèle (`make run` ou `make run-all`).

## Pages

| Page | Description |
|------|-------------|
| **Dashboard** | Graphique chandelier + indicateurs techniques (SMA, EMA, RSI, MACD, BB) |
| **Market Overview** | Fear & Greed Index, market cap global, top movers, matrice de corrélation |
| **Signaux** | Tableau RSI / MACD / BB / SMA + score composite BUY/SELL/HOLD par paire |
| **Veille** | News RSS filtrables (source, sentiment, topic, symbole) + NLP enrichi |
| **ML & Backtesting** | Walk-forward par symbole/timeframe, comparaison buy-and-hold, lien MLflow |
| **Paper Trading** | Simulation de trades sur capital fictif avec prix temps réel Binance |

## Refresh des données

- La plupart des pages utilisent `@st.cache_data` (TTL 120s) — cliquer sur **Actualiser** pour forcer le rechargement.
- La page Paper Trading se rafraîchit automatiquement toutes les **5 secondes** via `streamlit-autorefresh`.
- Si une erreur `AttributeError` apparaît après une mise à jour du code, **redémarrer Streamlit** (Ctrl+C + `make run`).

## Alertes email

La page Veille permet de s'abonner / se désabonner aux alertes de collecte.  
Un email de confirmation est envoyé à chaque action (avec les dernières actualités à l'inscription).  
Configurer les variables `ALERT_EMAIL_*` dans `.env`.
