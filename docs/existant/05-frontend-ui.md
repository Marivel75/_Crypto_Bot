# 04 — Equipe Frontend / UI

> **Lisez d'abord** `docs/00-overview.md` pour le contexte global du projet.

---

## Votre perimetre

Vous etes responsables de **tout ce que l'utilisateur voit** : dashboard, graphiques, chatbot UI, alertes.

| Vous gerez | Vous NE gerez PAS |
|-----------|-------------------|
| Application Streamlit | La collecte de donnees (equipe Data Eng) |
| Graphiques Plotly (chandeliers, heatmaps, indicateurs) | Les modeles ML (equipe ML) |
| Interface chatbot | Les endpoints API (equipe Backend) |
| Navigation, layout, theming | Docker/CI/CD (equipe DevOps) |
| Export de graphiques (PNG, SVG, CSV) | Le schema BDD (equipe Data Eng) |

**Votre code va dans** : `src/frontend/`
**Votre branche** : `frontend/xxx`

---

## Ce que les autres equipes attendent de vous

| Equipe | Ce qu'elle attend | Interface |
|--------|------------------|-----------|
| **Backend** | Que vous consommiez leurs endpoints API REST correctement | `GET/POST` sur `http://api:8000/api/v1/...` |
| **DevOps** | Un Dockerfile fonctionnel | `Dockerfile` dans `src/frontend/` |

## Ce que vous consommez

**IMPORTANT** : vous ne touchez JAMAIS a la BDD directement. Tout passe par l'API (equipe Backend).

| Source | Quoi | Comment |
|--------|------|---------|
| **Backend API** | Donnees de prix, indicateurs, signaux, news, portfolio | Appels HTTP vers FastAPI |

Voir `docs/03-backend-api.md` pour la liste complete des endpoints disponibles.

---

## Stack

| Technologie | Role |
|-------------|------|
| **Streamlit** | Framework principal — pages, widgets, layout |
| **Plotly** | Graphiques interactifs (chandeliers OHLCV, heatmaps, line charts, scatter) |
| **streamlit-plotly-events** | Clic sur les graphiques (optionnel) |
| **requests** | Appels HTTP vers l'API backend |

---

## Pages de l'application

### Page 1 : Dashboard principal (Noah — Trader)

```
+------------------------------------------------------------------+
|  CRYPTO BOT                               [Login] [Theme: Dark]  |
+------------------------------------------------------------------+
| [BTC ▼] [ETH] [SOL] [Watchlist +]                    [Alertes 3] |
+----------------------------+-------------------------------------+
|                            |  NEWS & SENTIMENT                   |
|   GRAPHIQUE CHANDELIERS    |  ┌──────────────────────────────┐   |
|   (Plotly candlestick)     |  │ ● Derniere news              │   |
|                            |  │ ● Derniere news              │   |
|   [1h][2h][3h][4h][1D][1W] |  │ ● Derniere news              │   |
|                            |  └──────────────────────────────┘   |
|   RSI: 62  BB: near upper  |  Fear & Greed: 72 (Greed)          |
|   Trend: stable weekly     |                                     |
+----------------------------+-------------------------------------+
|  SIGNAUX ACTIFS                  |  MULTI-TIMEFRAME              |
|  ┌────────────────────────────┐  |  ┌──────────────────────────┐ |
|  │ BUY BTC                    │  |  │ TF    RSI   BB    Trend  │ |
|  │ Confiance: 0.78            │  |  │ 1h    62   0.7   ↑       │ |
|  │ Regles: RSI multi-TF,     │  |  │ 2h    65   0.6   ↑       │ |
|  │         BB squeeze         │  |  │ 4h    68   0.5   ↑       │ |
|  │ Levier suggere: 5x        │  |  │ 1D    70   0.4   →       │ |
|  │ Marge securite: OK        │  |  │ 1W    —    —     ↑       │ |
|  └────────────────────────────┘  |  └──────────────────────────┘ |
+----------------------------------+------------------------------+
```

**Elements cles** :
- Graphique chandelier Plotly avec indicateurs superposes (RSI, Bollinger, trend lines)
- Selecteur de timeframe (1h, 2h, 3h, 4h, 1D, 1W, 1M)
- Selecteur de crypto (dropdown ou tabs)
- Panneau de signaux actifs avec detail des regles
- Tableau multi-timeframe montrant les indicateurs sur chaque TF
- Panneau news avec sentiment

### Page 2 : Veille & News (Sarah — Journaliste)

```
+------------------------------------------------------------------+
|  VEILLE CRYPTO                                                    |
+------------------------------------------------------------------+
| Filtres: [Source ▼] [Mot-cle: ___] [Date: du __ au __]          |
+------------------------------------------------------------------+
|  DERNIERES NEWS                     |  SENTIMENT AGREGE           |
|  ┌────────────────────────────────┐ |  ┌────────────────────────┐ |
|  │ Titre de l'article             │ |  │ BTC: Positif (0.72)   │ |
|  │ Source: Decrypt | 14:32        │ |  │ ETH: Neutre (0.48)    │ |
|  │ Sentiment: Positif (0.8)       │ |  │ SOL: Negatif (0.31)   │ |
|  │ Mots-cles: [SEC] [ETF]        │ |  └────────────────────────┘ |
|  └────────────────────────────────┘ |                              |
|  ┌────────────────────────────────┐ |  NUAGE DE MOTS              |
|  │ Titre de l'article 2          │ |  ┌────────────────────────┐ |
|  │ ...                            │ |  │  (word cloud Plotly)   │ |
|  └────────────────────────────────┘ |  └────────────────────────┘ |
+-------------------------------------+----------------------------+
| [Exporter CSV] [Exporter PNG]                                     |
+------------------------------------------------------------------+
```

**Elements cles** :
- Liste des articles avec filtres (source, mot-cle, date)
- Score de sentiment par article et par crypto
- Nuage de mots
- Graphiques exportables (PNG, SVG, CSV)

### Page 3 : Portfolio & Signaux simples (Aleksandar — Investisseur)

```
+------------------------------------------------------------------+
|  MON PORTFOLIO                                                    |
+------------------------------------------------------------------+
|  ┌────────────────────────────────────────────────────────────┐   |
|  │ Crypto | Quantite | Prix achat | Prix actuel | P&L       │   |
|  │ BTC    | 0.05     | 62,000     | 67,200      | +8.4%     │   |
|  │ ETH    | 1.2      | 3,400      | 3,250       | -4.4%     │   |
|  │ SOL    | 10       | 140        | 165          | +17.9%    │   |
|  │ ───────────────────────────────────────────── | Total: +X%│   |
|  └────────────────────────────────────────────────────────────┘   |
+------------------------------------------------------------------+
|  CHATBOT IA                                                       |
|  ┌────────────────────────────────────────────────────────────┐   |
|  │ Vous: Pourquoi Bitcoin monte en ce moment ?                │   |
|  │                                                            │   |
|  │ Bot: Le Bitcoin est en hausse de 3.2% sur les dernieres   │   |
|  │ 24h. Plusieurs facteurs : le Fear & Greed est a 72        │   |
|  │ (zone de "Greed"), le RSI 4h est a 68 (haussier mais     │   |
|  │ attention au surachat), et les dernieres news sont         │   |
|  │ majoritairement positives (sentiment 0.72).                │   |
|  │                                                            │   |
|  │ ⚠ Je ne suis pas un conseiller financier.                 │   |
|  └────────────────────────────────────────────────────────────┘   |
|  [Votre message: _______________________________] [Envoyer]       |
+------------------------------------------------------------------+
```

### Page 4 : Analytics & Heatmap

- Heatmap des performances crypto (24h, 7d, 30d)
- Market cap, dominance, volumes
- Fear & Greed Index historique
- Comparaison entre cryptos

### Page 5 : Performance des signaux

- Historique des signaux emis
- Taux de reussite (global, par crypto, par timeframe)
- P&L simule
- Graphique de performance dans le temps

---

## Conventions

### Structure du code

```
src/frontend/
├── app.py                  # Point d'entree Streamlit (st.navigation)
├── config.py               # Settings (API_URL, etc.)
├── api_client.py           # Client HTTP pour appeler le backend
├── pages/
│   ├── 1_dashboard.py      # Dashboard trader (Noah)
│   ├── 2_veille.py         # Veille news (Sarah)
│   ├── 3_portfolio.py      # Portfolio + chatbot (Aleksandar)
│   ├── 4_analytics.py      # Heatmap, analytics
│   └── 5_performance.py    # Performance des signaux
├── components/
│   ├── candlestick.py      # Composant graphique chandelier
│   ├── indicators.py       # Composant affichage indicateurs
│   ├── signal_card.py      # Composant carte de signal
│   ├── news_feed.py        # Composant fil de news
│   └── chatbot.py          # Composant chatbot
├── Dockerfile
└── requirements.txt
```

### Client API

Toutes les pages appellent le backend via un client centralise :

```python
# src/frontend/api_client.py
import requests
import streamlit as st

API_URL = "http://api:8000"  # en Docker, sinon configurable

class APIClient:
    def __init__(self):
        self.token = st.session_state.get("token")

    def get(self, path: str, params: dict = None) -> dict:
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        r = requests.get(f"{API_URL}{path}", params=params, headers=headers)
        r.raise_for_status()
        return r.json()

    def post(self, path: str, data: dict = None) -> dict:
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        r = requests.post(f"{API_URL}{path}", json=data, headers=headers)
        r.raise_for_status()
        return r.json()
```

### Graphiques Plotly chandeliers

```python
import plotly.graph_objects as go

def create_candlestick(ohlcv_data):
    fig = go.Figure(data=[go.Candlestick(
        x=[d["timestamp"] for d in ohlcv_data],
        open=[d["price_open"] for d in ohlcv_data],
        high=[d["price_high"] for d in ohlcv_data],
        low=[d["price_low"] for d in ohlcv_data],
        close=[d["price_close"] for d in ohlcv_data],
    )])
    fig.update_layout(xaxis_rangeslider_visible=False)
    return fig
```

---

## UX

| Critere | Specification |
|---------|---------------|
| Temps de chargement | < 3 secondes pour le dashboard |
| Theme par defaut | Dark mode (preference traders) |
| Export | PNG, SVG, CSV pour graphiques et tableaux |
| Responsive | Desktop prioritaire |

---

## Taches

### Sprint 7 (Avril)
- [ ] Setup Streamlit multi-pages
- [ ] Client API centralise (`api_client.py`)
- [ ] Login / auth (session Streamlit)
- [ ] Page Dashboard : graphique chandelier Plotly
- [ ] Page Dashboard : selecteur de crypto et timeframe
- [ ] Page Dashboard : affichage des indicateurs multi-TF
- [ ] Page Dashboard : panneau signaux actifs
- [ ] Page Veille : liste des news avec filtres
- [ ] Page Portfolio : tableau CRUD

### Sprint 8 (Mai)
- [ ] Page Dashboard : panneau news + sentiment
- [ ] Page Veille : nuage de mots, sentiment agrege
- [ ] Page Veille : export PNG/SVG/CSV
- [ ] Page Portfolio : chatbot IA
- [ ] Page Analytics : heatmap performances
- [ ] Page Performance : historique des signaux
- [ ] Dark mode / Light mode toggle
- [ ] Tests fonctionnels (Selenium ou Playwright)
