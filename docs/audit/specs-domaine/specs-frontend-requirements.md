# Cahier des Charges — Frontend UI / Streamlit

**Projet:** Crypto Bot
**Équipe:** Frontend & UI
**Auteur:** Product Manager Frontend & UX
**Date:** 2026-03-12
**Version:** 1.0

---

## Table des matières

1. [Executive Summary](#executive-summary)
2. [Exigences Fonctionnelles par Page](#exigences-fonctionnelles-par-page)
   - [Page 1 : Dashboard (Noah)](#page-1--dashboard-noah)
   - [Page 2 : Veille (Sarah)](#page-2--veille-sarah)
   - [Page 3 : Portfolio (Aleksandar)](#page-3--portfolio-aleksandar)
   - [Page 4 : Analytics](#page-4--analytics)
   - [Page 5 : Performance](#page-5--performance)
3. [Exigences Transversales UI](#exigences-transversales-ui)
4. [Exigences Techniques](#exigences-techniques)
5. [Exigences de Performance](#exigences-de-performance)
6. [Exigences de Sécurité](#exigences-de-sécurité)
7. [Exigences d'Accessibilité](#exigences-daccessibilité)

---

## Executive Summary

Cette section décrit les exigences détaillées du frontend Streamlit + Plotly de Crypto Bot. Le frontend expose une plateforme de veille crypto, d'analytics et d'aide au trading avec 5 pages principales :

1. **Dashboard** — Vue du trader : bougies OHLCV + signaux + news + indicateurs multi-TF
2. **Veille** — Vue de la journaliste : fil de news + sentiment + filtres + export
3. **Portfolio** — Vue de l'investisseur : positions P&L + watchlist + chatbot IA
4. **Analytics** — Heatmap corrélations, market overview, performance globale
5. **Performance** — Historique des signaux, taux de succès, backtesting

### Personas utilisateur

| Persona | Rôle | Besoins clés | Dispositif |
|---------|------|-------------|-----------|
| **Noah** | Trader indépendant | Signaux temps réel, multi-TF, alertes, journal | Desktop 1920+ |
| **Sarah** | Journaliste financière | Veille auto., filtres, export, NLP sentiment | Desktop/Tablet |
| **Aleksandar** | Investisseur débutant | Chatbot vulgarisé, P&L simple, watchlist | Desktop/Mobile |

### Architecture

```
┌────────────────────────────────────────┐
│   Streamlit App (src/frontend/)        │
│  ┌──────────────────────────────────┐  │
│  │  app.py (entry point)            │  │
│  │  ├─ Auth sidebar                 │  │
│  │  ├─ Theme CSS (dark/light)       │  │
│  │  ├─ i18n (FR/EN)                 │  │
│  │  └─ Navigation (st.navigation)   │  │
│  ├──────────────────────────────────┤  │
│  │  pages/                          │  │
│  │  ├─ 1_dashboard.py               │  │
│  │  ├─ 2_veille.py                  │  │
│  │  ├─ 3_portfolio.py               │  │
│  │  ├─ 4_analytics.py               │  │
│  │  └─ 5_performance.py             │  │
│  ├──────────────────────────────────┤  │
│  │  components/                     │  │
│  │  ├─ candlestick.py               │  │
│  │  ├─ indicators.py                │  │
│  │  ├─ signal_card.py               │  │
│  │  ├─ news_feed.py                 │  │
│  │  └─ chatbot.py                   │  │
│  ├──────────────────────────────────┤  │
│  │  api_client.py (HTTP client)     │  │
│  │  config.py (settings)            │  │
│  │  i18n/ (translations)            │  │
│  └──────────────────────────────────┘  │
└────────────────────────────────────────┘
          │
          └──→ FastAPI Backend (http://api:8000)
                  └──→ TimescaleDB + MinIO
```

---

## Exigences Fonctionnelles par Page

### Page 1 : Dashboard (Noah)

#### RF-UI-001 : Graphique candlestick OHLCV avec Plotly

**Priorité:** Must Have
**Statut:** Partiellement implémenté

**Description:**
Afficher un graphique candlestick (chandelier) interactif montrant :
- Bougies (open, high, low, close)
- Volume en sous-graphique
- Overlay Bollinger Bands (supérieur/inférieur/central)
- Légende interactive, zoom/pan
- Responsive (s'adapte à la largeur de la colonne)

**Critères d'acceptation:**
- Bougies vertes (haussières : #26c6a0) quand close >= open
- Bougies rouges (baissières : #ef5350) quand close < open
- Volume coloré selon la direction de la bougie
- Bollinger Bands : supérieur/inférieur en jaune (tirets), central en bleu (pointillés)
- Grille de fond discrète (rgba(255,255,255,0.06))
- Titre dynamique : "{SYMBOL} — {TIMEFRAME}"
- Tooltip au survol : horodatage, OHLCV, volume
- Pas de range slider en bas
- Hauteur : 580px
- Export PNG/SVG natif Plotly (bouton camera)

**Dépendances:**
- API `/api/v1/crypto/{symbol}/prices?timeframe={tf}&limit=200` (GET)
- API `/api/v1/crypto/{symbol}/indicators?timeframe={tf}` (GET, pour Bollinger)

**Notes d'implémentation:**
- Utiliser `plotly.subplots.make_subplots(rows=2, cols=1)` pour volume en sous-graphique
- Accepter un dict `indicators` avec clés `bollinger_upper`, `bollinger_middle`, `bollinger_lower`
- Logger un warning si les données OHLCV sont vides
- Afficher un empty-state stylisé avec message "Pas de données" si la liste est vide

---

#### RF-UI-002 : Sélecteur de crypto (symboles)

**Priorité:** Must Have
**Statut:** Implémenté

**Description:**
Dropdown permettant de choisir parmi les cryptos suivies (top 30 par market cap).

**Critères d'acceptation:**
- Symboles : BTC, ETH, BNB, XRP, SOL, ADA, AVAX, DOT, DOGE, TRX, ATOM (+ autres du top 30)
- Valeur par défaut : BTC
- Aucun symbole stablecoin (USDT, USDC) dans la liste
- Symboles configurables via `frontend_settings.tracked_symbols` (.env)
- Changement de symbole → rechargement des données (OHLCV, indicateurs, signaux)
- Cache invalidation : `st.cache_data.clear()` au changement
- Label multilingue : "Crypto" (FR) / "Cryptocurrency" (EN)

**Dépendances:**
- `frontend_settings.tracked_symbols` (config.py)
- API `/api/v1/crypto/list` (optionnel, pour récupérer la liste du backend)

**Notes d'implémentation:**
- Utiliser `st.selectbox()` avec `key="symbol_selector"`
- Appeler `st.rerun()` après changement

---

#### RF-UI-003 : Sélecteur de timeframe

**Priorité:** Must Have
**Statut:** Implémenté

**Description:**
Dropdown pour choisir la granularité temporelle des données OHLCV affichées.

**Critères d'acceptation:**
- Timeframes disponibles : 1h, 2h, 3h, 4h, 1D (1 jour), 1W (1 semaine), 1M (1 mois)
- Valeur par défaut : 4h (index 3)
- Labels multilingues
- Changement → rechargement graphique + indicateurs
- Ordre : court terme → long terme (gauche → droite)
- Configurables via `frontend_settings.timeframes`

**Dépendances:**
- `frontend_settings.timeframes` (config.py)
- API `/api/v1/crypto/{symbol}/prices?timeframe={tf}` (GET)

**Notes d'implémentation:**
- Utiliser `st.selectbox()` avec `key="timeframe_selector"`
- Invalider le cache après changement

---

#### RF-UI-004 : Bouton Rafraîchir

**Priorité:** Should Have
**Statut:** Implémenté

**Description:**
Bouton permettant l'utilisateur de forcer la revalidation du cache et de recharger les données.

**Critères d'acceptation:**
- Appelle `st.cache_data.clear()`
- Puis `st.rerun()`
- Label : "Rafraîchir" (FR) / "Refresh" (EN)
- Icône : Material Design "refresh"
- Type : primary (bouton bleu dégradé)
- Placé en haut à droite du dashboard

**Dépendances:**
- Aucune API (opération locale)

---

#### RF-UI-005 : Indicateur de connexion API

**Priorité:** Should Have
**Statut:** Implémenté

**Description:**
Afficher le statut de connexion au backend dans le header du dashboard.

**Critères d'acceptation:**
- Bouton/badge en haut à droite
- Vert + checkmark si `/api/health` répond (200 OK)
- Rouge + X si API injoignable
- Texte : "API connectée" (vert) / "API hors ligne" (rouge)
- Mis à jour au chargement de la page

**Dépendances:**
- API `GET /api/health` ou `GET /health`
- Timeout : 2s max

---

#### RF-UI-006 : Affichage des indicateurs (RSI, Bollinger)

**Priorité:** Must Have
**Statut:** Partiellement implémenté

**Description:**
Afficher un résumé textuel des indicateurs techniques du timeframe sélectionné sous le graphique candlestick.

**Critères d'acceptation:**
- RSI : valeur numérique à 2 décimales + zone (Survendu < 30, Normal 30-70, Suracheté > 70)
- Bollinger Bands : position du prix dans les bandes (% de 0 à 100)
  - 0% = à la limite inférieure
  - 50% = au milieu (SMA 20)
  - 100% = à la limite supérieure
- Trend lines : état de la tendance (stable, haussier ↑, baissier ↓)
- Format : pills/badges colorés horizontaux
- Mise à jour automatique quand les indicateurs changent

**Dépendances:**
- API `/api/v1/crypto/{symbol}/indicators?timeframe={tf}` (GET)
- Clés attendues : `rsi`, `bollinger_upper`, `bollinger_middle`, `bollinger_lower`, `trend_direction`

**Notes d'implémentation:**
- Fonction `render_indicator_summary(indicators_dict)` dans `components/indicators.py`
- Tolérer les valeurs None (afficher "—")
- Couleur RSI : rouge si < 30, vert si > 70, gris si normal

---

#### RF-UI-007 : Tableau multi-timeframe

**Priorité:** Should Have
**Statut:** Partiellement implémenté

**Description:**
Tableau affichant les indicateurs clés sur plusieurs timeframes (1h, 2h, 3h, 4h, 1D, 1W) simultanément.

**Critères d'acceptation:**
- Colonnes : Timeframe | RSI | Bollinger (%) | Trend | État de suracheté/vendu
- Lignes : une par TF (max 7)
- Données actualisées toutes les 60s
- Codes couleur : rouge (bearish), vert (bullish), gris (neutre)
- Responsive : scroll horizontal sur mobile
- Cliquable (optionnel) pour zoomer sur ce TF

**Dépendances:**
- API `/api/v1/crypto/{symbol}/indicators?timeframe={tf}` (GET, appelé pour chaque TF)
- Cache : 60s par TF

**Notes d'implémentation:**
- Fonction `render_multi_timeframe_table(data_list)` dans `components/indicators.py`
- Fetcher les données pour [1h, 2h, 3h, 4h, 1D, 1W] en parallèle si possible (asyncio côté API)
- Gérer les timeframes non disponibles (afficher "—")

---

#### RF-UI-008 : Panneau de signaux actifs

**Priorité:** Must Have
**Statut:** Partiellement implémenté

**Description:**
Afficher les signaux BUY/SELL/HOLD générés par le ML engine pour le symbole sélectionné.

**Critères d'acceptation:**
- Lister TOUS les signaux avec confiance >= 0.6 pour le symbole
- Chaque signal montre :
  - Direction (BUY/SELL/HOLD) avec icône + couleur (vert/rouge/gris)
  - Confiance (0.0 à 1.0) en pourcentage
  - Prix d'entrée suggéré
  - Stop loss
  - Take profit (liste, max 3 niveaux)
  - Levier suggéré (max 5x, avec avertissement margin 2x)
  - Indicateurs utilisés (liste des règles : "RSI multi-TF", "BB squeeze", etc.)
  - Timeframe du signal
  - Horodatage du signal
- Si aucun signal >= 0.6 : message "Aucun signal pour ce moment"
- Tri par confiance (décroissante)
- Cliquable pour voir le détail complet

**Dépendances:**
- API `GET /api/v1/signals/{symbol}` (GET, pour un symbole spécifique)
- API `GET /api/v1/signals/active` (GET, pour tous les signaux actifs)
- Modèle Signal : `{symbol, timeframe, direction, confidence, entry_price, stop_loss, take_profit[], leverage_suggested, indicators_used[], timestamp}`

**Notes d'implémentation:**
- Fonction `render_signals_panel(signals_list)` dans `components/signal_card.py`
- Filtrer en client si besoin : `[s for s in signals if s.get('confidence', 0) >= 0.6]`
- Composer la liste Take Profit sous forme `"SL: X, TP1: Y, TP2: Z"`
- Cache : 30s

---

#### RF-UI-009 : Panneau news (mini fil)

**Priorité:** Should Have
**Statut:** Implémenté (partiellement)

**Description:**
Afficher les 5 derniers articles de news dans le dashboard (colonne droite, petit écran).

**Critères d'acceptation:**
- Titres + source + sentiment score
- Lien cliquable vers l'article complet (optionnel)
- Max 5 articles
- Trié par date décroissante (plus récent en haut)
- Sentiment score : couleur rouge/gris/vert selon positif/neutre/négatif
- Cache : 120s

**Dépendances:**
- API `GET /api/v1/news/latest?limit=5` (GET)
- Clés attendues : `title`, `source`, `sentiment_score`, `url`, `published_at`

**Notes d'implémentation:**
- Fonction `render_news_card(article)` dans `components/news_feed.py`
- Si pas de données : afficher empty-state stylisé

---

### Page 2 : Veille (Sarah)

#### RF-UI-010 : Fil de news avec filtres

**Priorité:** Must Have
**Statut:** Implémenté (partiellement)

**Description:**
Afficher une liste complète des articles de news avec filtres côté client et serveur.

**Critères d'acceptation:**
- Filtre par source : Decrypt, Cointelegraph, PhoenixNews, CoinDesk (+ "Tous")
- Filtre par mot-clé (keyword search, côté serveur via API)
- Filtre par date : from/to avec `st.date_input()`
- Affichage : min 20 articles par défaut
- Tri : récent en premier (décroissant par `published_at`)
- Chaque article : titre, source, date/heure, sentiment, mots-clés, lien
- Pagination (optionnel) ou scroll infini avec "Charger plus"

**Dépendances:**
- API `GET /api/v1/news/latest?source={source}&keyword={keyword}&limit={limit}` (GET)
- Clés : `title`, `source`, `sentiment_score`, `keywords[]`, `published_at`, `url`, `id`

**Notes d'implémentation:**
- Filtres implémentés dans `_render_filter_bar()` (2_veille.py)
- Date filter : client-side via `_apply_date_filter()`
- Afficher le compte total d'articles trouvés
- Cache : 120s

---

#### RF-UI-011 : Graphique sentiment par source

**Priorité:** Should Have
**Statut:** Partiellement implémenté

**Description:**
Bar chart montrant le sentiment moyen par source de news.

**Critères d'acceptation:**
- Axe X : sources de news (Decrypt, Cointelegraph, etc.)
- Axe Y : sentiment score moyen (0 à 1)
- Couleur des barres : rouge (< 0.4), gris (0.4-0.6), vert (> 0.6)
- Tooltip au survol : source + score précis
- Titre : "Sentiment agrégé par source"
- Préférer API `/api/v1/news/sentiment` si disponible ; sinon, agréger côté client

**Dépendances:**
- API `GET /api/v1/news/sentiment` (GET) — renvoie [{symbol, sentiment_score}, ...]
- Ou agréger `news_list` côté client si API absente

**Notes d'implémentation:**
- Fonction `render_sentiment_chart(data_list)` dans `components/news_feed.py`
- Utiliser Plotly bar chart avec layout dark

---

#### RF-UI-012 : Nuage de mots (word cloud)

**Priorité:** Should Have
**Statut:** Partiellement implémenté

**Description:**
Visualiser les mots-clés les plus fréquents dans les articles de news sous forme de word cloud.

**Critères d'acceptation:**
- Taille des mots = fréquence (plus grand = plus fréquent)
- Max 30 mots
- Couleur dégradée en fonction de la fréquence
- Interactif : tooltip avec le compte exact
- Utiliser Plotly (pas matplotlib wordcloud)
- Titre : "Mots-clés tendance"

**Dépendances:**
- Agrégation client-side : `_aggregate_keywords(news_list)` → [{word, count}, ...]

**Notes d'implémentation:**
- Fonction `render_word_cloud(keywords_agg)` dans `components/news_feed.py`
- Plotly scatter avec `marker.size` proportionnel à count
- Couleur : `marker.color = count` avec colorscale "Viridis" ou "Plasma"

---

#### RF-UI-013 : Export CSV des articles

**Priorité:** Should Have
**Statut:** Implémenté

**Description:**
Bouton permettant de télécharger les articles visibles en CSV.

**Critères d'acceptation:**
- Colonnes : Titre, Source, Date, Sentiment Score, Mots-clés, URL
- Encodage : UTF-8
- Nom du fichier : `veille_crypto_{date}.csv`
- Bouton `st.download_button()` sous la liste
- Export : articles filtrés par les critères actuels

**Dépendances:**
- Aucune API (export côté client avec pandas DataFrame)

---

#### RF-UI-014 : Export PNG/SVG des graphiques

**Priorité:** Nice to Have
**Statut:** Natif Plotly

**Description:**
Permettre l'export des graphiques (sentiment, word cloud) en images.

**Critères d'acceptation:**
- Bouton "camera" natif Plotly (en haut à droite de chaque graphique)
- Formats : PNG, SVG
- Nom du fichier : `sentiment_chart_{timestamp}.png`, etc.

**Dépendances:**
- Natif Plotly (aucune implémentation supplémentaire)

---

### Page 3 : Portfolio (Aleksandar)

#### RF-UI-015 : Tableau des positions de portfolio

**Priorité:** Must Have
**Statut:** Implémenté (partiellement)

**Description:**
Afficher un tableau des positions du portefeuille de l'utilisateur (virtuel, non réel).

**Critères d'acceptation:**
- Colonnes : Crypto | Quantité | Prix d'achat | Prix actuel | P&L (%) | P&L (USD) | Notes
- Tri : par crypto (A-Z) par défaut ; cliquable pour trier
- Chaque P&L coloré : rouge si négatif, vert si positif
- Lignes totalisant les positions (somme quantité, moyenne prix, P&L total %)
- Responsive : scroll horizontal sur mobile
- Éditable inline (optionnel) ou via pop-up d'édition
- Authentification requise (JWT)

**Dépendances:**
- API `GET /api/v1/portfolio` (GET) — nécessite JWT
- Clés : `id, symbol, quantity, entry_price, current_price, notes`

**Notes d'implémentation:**
- Fonction `_render_portfolio_table(positions)` dans 3_portfolio.py
- Calcul P&L côté frontend : `(current - entry) / entry * 100`
- Afficher "—" si current_price manquant, utiliser entry_price en fallback
- Pandas DataFrame pour tableau

---

#### RF-UI-016 : Métriques P&L résumées

**Priorité:** Should Have
**Statut:** Implémenté

**Description:**
Afficher les KPIs portfolios en haut du tableau.

**Critères d'acceptation:**
- 3 colonnes (Streamlit metrics) :
  1. Valeur totale du portfolio (USD)
  2. Coût total d'achat (USD)
  3. P&L total (%)
- Format : `$X,XXX.XX` pour USD ; `+/-X.X%` pour pourcentage
- Delta : afficher aussi la valeur absolue en USD
- Couleur : vert si total P&L > 0, rouge sinon

**Dépendances:**
- Données du portfolio (cf. RF-UI-015)

---

#### RF-UI-017 : Formulaire d'ajout de position

**Priorité:** Must Have
**Statut:** Implémenté (partiellement)

**Description:**
Formulaire pour ajouter une nouvelle position au portfolio.

**Critères d'acceptation:**
- Champs :
  - Crypto (selectbox : BTC, ETH, ...) — obligatoire
  - Quantité (number_input, min=0, step=0.001) — obligatoire
  - Prix d'achat (number_input, min=0, step=0.01) — obligatoire
  - Notes (text_input) — optionnel
- Bouton "Ajouter position"
- Validation :
  - Crypto sélectionnée
  - Quantité > 0
  - Prix d'achat > 0
- Feedback : "Position ajoutée pour {symbol}" (success) ou erreur
- Réinitialiser le formulaire après succès

**Dépendances:**
- API `POST /api/v1/portfolio` (POST avec JWT)
- Body : `{symbol, quantity, entry_price, notes}`

**Notes d'implémentation:**
- Utiliser `st.form()` pour regrouper inputs + submit
- Appeler `st.rerun()` après création pour rafraîchir le tableau

---

#### RF-UI-018 : Formulaire d'édition de position

**Priorité:** Should Have
**Statut:** Implémenté

**Description:**
Éditer une position existante (quantité, prix d'achat, notes).

**Critères d'acceptation:**
- Selectbox pour choisir la position à éditer
- Champs pré-remplis avec les valeurs actuelles
- Éditer : quantité, prix, notes
- Ne pas pouvoir éditer le symbole (immutable)
- Bouton "Enregistrer" → API PUT
- Feedback succès/erreur
- Réinitialiser après succès

**Dépendances:**
- API `PUT /api/v1/portfolio/{position_id}` (PUT avec JWT)
- Body : `{quantity, entry_price, notes}`

---

#### RF-UI-019 : Suppression de position (avec confirmation)

**Priorité:** Should Have
**Statut:** Implémenté

**Description:**
Supprimer une position avec confirmation de sécurité.

**Critères d'acceptation:**
- Bouton "Supprimer"
- Confirmation : checkbox "Confirmer la suppression" + avertissement en rouge
- Message d'avertissement : "Cette action supprimera {symbol} — elle ne peut pas être annulée"
- Bouton désactivé tant que checkbox n'est pas cochée
- API DELETE
- Feedback succès

**Dépendances:**
- API `DELETE /api/v1/portfolio/{position_id}` (DELETE avec JWT)

---

#### RF-UI-020 : Watchlist (liste de suivi)

**Priorité:** Should Have
**Statut:** Implémenté

**Description:**
Gérer une liste de cryptos à suivre (watchlist) personnalisée par utilisateur.

**Critères d'acceptation:**
- Afficher la watchlist actuelle : liste de symboles
- Ajouter à la watchlist : selectbox + bouton
- Retirer de la watchlist : bouton "Remove" par ligne
- Vérifier qu'on n'ajoute pas un doublon
- Feedback : "BTC ajouté à votre watchlist" (success)
- Onglet séparé du portfolio dans l'UI

**Dépendances:**
- API `GET /api/v1/watchlist` (GET, JWT)
- API `POST /api/v1/watchlist` (POST, JWT) — body : `{symbol}`
- API `DELETE /api/v1/watchlist/{symbol}` (DELETE, JWT)

---

#### RF-UI-021 : Chatbot IA (assistant)

**Priorité:** Should Have
**Statut:** Partiellement implémenté

**Description:**
Interface de chat permettant des questions sur les cryptos, signaux, et portfolio.

**Critères d'acceptation:**
- Boîte de chat : historique des messages (utilisateur à gauche, bot à droite)
- Input : champ texte + bouton "Envoyer"
- Bot répond en exploitant :
  - Données de marché actuelles (prix, changement %)
  - Derniers signaux (si pertinent)
  - Sentiment de news récentes
  - Portfolio de l'utilisateur (s'il existe)
- Réponses vulgarisées pour Aleksandar (investisseur non-expert)
- Disclaimer obligatoire en bas : "⚠️ Je ne suis pas un conseiller financier"
- Historique de chat en session Streamlit (effacé au logout)
- Typing indicator ("Bot is typing...") optionnel

**Dépendances:**
- API `POST /api/v1/chat` (POST, JWT)
- Body : `{message: str}`
- Response : `{reply: str, disclaimer: str}`

**Notes d'implémentation:**
- Fonction `render_chatbot(client)` dans `components/chatbot.py`
- Utiliser `st.session_state["chat_history"]` pour historique
- Afficher horodatage des messages

---

### Page 4 : Analytics

#### RF-UI-022 : Heatmap des performances cryptos

**Priorité:** Should Have
**Statut:** À implémenter

**Description:**
Afficher une heatmap montrant les changements de prix (%) des cryptos sur différentes périodes.

**Critères d'acceptation:**
- Axes :
  - X : cryptos (BTC, ETH, BNB, ...)
  - Y : périodes (24h, 7d, 30d)
- Couleur : rouge (négatif) à vert (positif)
- Valeurs : % de changement à 2 décimales
- Responsive : adaptable en largeur/hauteur
- Interactif : tooltip au survol
- Titre : "Performance Crypto — 24h / 7j / 30j"
- Mise à jour : chaque 5 minutes

**Dépendances:**
- API `GET /api/v1/crypto/market-overview` (GET)
- Ou API spécifique `/api/v1/analytics/heatmap?period={24h|7d|30d}` (GET)

---

#### RF-UI-023 : Market overview (dominance, volumes)

**Priorité:** Nice to Have
**Statut:** À implémenter

**Description:**
Afficher des KPIs globaux du marché crypto.

**Critères d'acceptation:**
- Métrique 1 : Bitcoin dominance (%)
- Métrique 2 : Volume global 24h (USD)
- Métrique 3 : Nombre de cryptos actives
- Métrique 4 : Fear & Greed Index (si available)
- Streamlit metrics (colonnes)
- Mise à jour : 5 minutes

**Dépendances:**
- API `GET /api/v1/crypto/market-overview` (GET)
- Ou agrégation Backend

---

#### RF-UI-024 : Fear & Greed Index historique

**Priorité:** Nice to Have
**Statut:** À implémenter

**Description:**
Graphique de l'indice Fear & Greed sur les 30 derniers jours.

**Critères d'acceptation:**
- Axe X : dates (30 jours)
- Axe Y : indice (0-100)
- Zone : colorer les régions Fear (< 40) et Greed (> 60) différemment
- Ligne : courbe smooth de l'indice
- Source : Alternative.me API
- Cache : 1 jour (données ne changent que 1x/jour)

**Dépendances:**
- Backend scrape Alternative.me ou expose un endpoint `/api/v1/analytics/fear-greed`

---

#### RF-UI-025 : Comparateur crypto

**Priorité:** Nice to Have
**Statut:** À implémenter

**Description:**
Permettre de comparer plusieurs cryptos côte à côte (prix, changement, RSI, volume).

**Critères d'acceptation:**
- Multi-select : choisir 2-5 cryptos à comparer
- Tableau comparatif :
  - Colonne par crypto
  - Lignes : prix 24h, changement %, RSI, volume 24h, market cap
- Code couleur pour les changements
- Tri possible par colonne

**Dépendances:**
- API `GET /api/v1/crypto/{symbol}/latest` (GET, pour chaque symbole)

---

### Page 5 : Performance

#### RF-UI-026 : Historique des signaux émis

**Priorité:** Should Have
**Statut:** À implémenter

**Description:**
Afficher l'historique de tous les signaux générés par le système, avec contexte et résultats.

**Critères d'acceptation:**
- Tableau des signaux :
  - Date/heure d'émission
  - Crypto + Timeframe
  - Direction (BUY/SELL/HOLD)
  - Confiance
  - Prix d'entrée
  - Stop loss / Take profit
  - Résultat (si signal clôturé) : P&L %, temps ouvert
- Filtrer par :
  - Date (from/to)
  - Crypto
  - Direction (BUY/SELL/HOLD)
- Pagination : 50 signaux par page
- Afficher total + compteurs (# BUY, # SELL, # HOLD)

**Dépendances:**
- API `GET /api/v1/signals?symbol={symbol}&from={date}&to={date}&limit={limit}&offset={offset}` (GET)

---

#### RF-UI-027 : Taux de succès des signaux

**Priorité:** Should Have
**Statut:** À implémenter

**Description:**
Afficher les KPIs de performance du système de signaux.

**Critères d'acceptation:**
- Metrics (colonnes Streamlit) :
  1. Win rate global (%)
  2. Total signaux émis (count)
  3. Signaux gagnants (count)
  4. Signaux perdants (count)
  5. P&L moyen par signal (%)
  6. Ratio gain/perte (Profit Factor)
- Période : sélectionnable (7j, 30j, 90j, all)
- Codes couleur : vert si win rate > 50%, rouge sinon

**Dépendances:**
- API `GET /api/v1/signals/performance?period={7d|30d|90d|all}` (GET)

---

#### RF-UI-028 : Graphique de performance dans le temps

**Priorité:** Should Have
**Statut:** À implémenter

**Description:**
Courbe cumulée du P&L des signaux fermés au fil du temps.

**Critères d'acceptation:**
- Axe X : dates (historique)
- Axe Y : cumul P&L (USD ou %)
- Ligne : profit cumulé
- Ombre en arrière-plan : région positive (vert) / négative (rouge)
- Tooltip : date, P&L à cette date
- Filtrable par :
  - Crypto
  - Période (7d, 30d, 90d, all)
- Responsive

**Dépendances:**
- API `GET /api/v1/signals/cumulative-pnl?symbol={symbol}&period={period}` (GET)

---

#### RF-UI-029 : Breakdown par crypto / timeframe

**Priorité:** Nice to Have
**Statut:** À implémenter

**Description:**
Analyser la performance des signaux par crypto et par timeframe.

**Critères d'acceptation:**
- Heatmap : Crypto (lignes) × Timeframe (colonnes) = win rate (%)
- Ou tableaux séparés :
  - Tableau 1 : per-crypto stats (win rate, total signaux, P&L moyen)
  - Tableau 2 : per-timeframe stats (win rate, total signaux, P&L moyen)
- Code couleur : rouge (< 40%), gris (40-60%), vert (> 60%)

**Dépendances:**
- API `GET /api/v1/signals/performance-by-crypto` (GET)
- API `GET /api/v1/signals/performance-by-timeframe` (GET)

---

## Exigences Transversales UI

### RF-UI-030 : Navigation multi-pages Streamlit

**Priorité:** Must Have
**Statut:** Implémenté

**Description:**
Naviguer entre les 5 pages via `st.navigation()` (Streamlit ≥ 1.33).

**Critères d'acceptation:**
- Sidebar ou navigation en haut montrant 5 entrées :
  1. Dashboard (icône : trending_up)
  2. Veille (icône : newspaper)
  3. Portfolio (icône : account_balance_wallet)
  4. Analytics (icône : analytics)
  5. Performance (icône : emoji_events)
- Onglet actif surligné/coloré
- Chaque page a son propre URL (optionnel mais souhaitable)
- Navigation fluide sans rechargement complet
- Icônes Material Design

**Dépendances:**
- Streamlit >= 1.33

**Notes d'implémentation:**
- Utiliser `st.Page()` et `st.navigation()`
- app.py : définir les pages et lancer `nav.run()`

---

#### RF-UI-031 : Thème dark/light adaptatif

**Priorité:** Should Have
**Statut:** Implémenté

**Description:**
Appliquer un thème dark mode par défaut (préférence traders), avec support du light mode.

**Critères d'acceptation:**
- Couleur de fond dark : #0d1117 (GitHub dark)
- Texte : #e6edf3 (light gray)
- Accents : cyan (#22d3ee) et sky (#0ea5e9)
- Boutons : dégradé cyan → sky
- Cartes : border subtle gris foncé (#30363d)
- Adaptable via toggle dans sidebar (optionnel)
- Cohérent avec Streamlit's theme config

**Dépendances:**
- CSS customisé dans `app.py` via `st.markdown(..., unsafe_allow_html=True)`
- Pré-défini : `_THEME_CSS`

---

#### RF-UI-032 : Support i18n (Français/Anglais)

**Priorité:** Should Have
**Statut:** Implémenté

**Description:**
Supporter le français (par défaut) et l'anglais.

**Critères d'acceptation:**
- Sélecteur de langue dans le sidebar
- Changement → rerun complet
- Tous les labels, tooltips, messages en FR/EN
- Fichiers de traduction : `i18n/fr.py`, `i18n/en.py`
- Fonction `t(key, **kwargs)` pour traductions avec interpolation
- Format : `{"nav.dashboard": "Dashboard", ...}`

**Dépendances:**
- Modules `src/frontend/i18n/fr.py`, `src/frontend/i18n/en.py`
- Fonction `t()` globale

---

#### RF-UI-033 : Caching des réponses API

**Priorité:** Must Have
**Statut:** Implémenté

**Description:**
Mettre en cache les réponses API côté frontend pour réduire la latence et la charge serveur.

**Critères d'acceptation:**
- Prix OHLCV : 30-60s
- Signaux : 30-60s
- News : 120s
- Indicateurs : 60s
- Market overview : 300s (5 min)
- Sentiment : 120s
- Portfolio/Watchlist : pas de cache (toujours frais)
- Utiliser `@st.cache_data(ttl=X)` sur les fonctions fetch
- Bouton "Rafraîchir" invalide le cache manuel

**Dépendances:**
- Decorateur `@st.cache_data(ttl=...)`

---

#### RF-UI-034 : Gestion d'erreurs user-friendly

**Priorité:** Must Have
**Statut:** Implémenté

**Description:**
Afficher des messages d'erreur clairs et proposer des actions.

**Critères d'acceptation:**
- Erreur API 401 (Unauthorized) : "Votre session a expiré. Veuillez vous reconnecter."
- Erreur API 500 : "Erreur serveur. Réessayez dans quelques instants."
- Erreur timeout : "Connexion au serveur trop lente. Vérifiez votre connexion."
- Erreur validation (form) : message spécifique et inline (ex. "La quantité doit être > 0")
- Ne JAMAIS afficher stack trace ou détails techniques
- Icons visuels (⚠️, ❌, ✅) pour clarté

**Dépendances:**
- `st.error()`, `st.warning()`, `st.success()`, `st.info()`
- Logging côté client pour debugging

---

#### RF-UI-035 : Authentification (login/register)

**Priorité:** Must Have
**Statut:** Implémenté

**Description:**
Système de login/register via JWT.

**Critères d'acceptation:**
- **Login :**
  - Champs : email, password
  - Bouton "Se connecter"
  - Reçoit JWT du backend
  - Stocke JWT en `st.session_state["token"]`
  - Feedback : "Bienvenue {username}" (success)
- **Register :**
  - Champs : username, email, password, persona (trader/journalist/investor)
  - Bouton "S'inscrire"
  - Crée le compte via API
  - Auto-login après creation
  - Feedback : "Compte créé. Vous êtes connecté." (success)
- **Logout :**
  - Bouton dans le sidebar
  - Efface le token + session state
  - Redirect vers formulaire login
- **Auth-gated pages :**
  - Portfolio, Watchlist, Chat : vérifier JWT avant render
  - Afficher invite login si non-authentifié

**Dépendances:**
- API `POST /api/v1/auth/login` (POST)
- API `POST /api/v1/auth/register` (POST)
- API `GET /api/v1/auth/me` (GET, JWT)
- Stockage JWT : `st.session_state["token"]`

**Notes d'implémentation:**
- Sidebar auth : `_render_sidebar_auth()` dans app.py
- Login form : `_render_login_form()` dans app.py
- Register form : `_render_register_form()` dans app.py
- Vérifier token valide au chargement de page auth-gated

---

#### RF-UI-036 : Layout responsive (mobile/tablet/desktop)

**Priorité:** Should Have
**Statut:** Implémenté

**Description:**
Adapter le layout aux différentes résolutions d'écran.

**Critères d'acceptation:**
- **Desktop (1920+) :**
  - Sidebar visible (gauche)
  - Colonnes multiples (ex. chart + news côte à côte)
  - Layouts en `st.columns([3, 1])`, `st.columns(2)`
- **Tablet (768-1024) :**
  - Sidebar collapsible
  - Colonnes se resserrent ; graphiques scaled
  - Tableaux scrollables horizontalement
- **Mobile (< 768) :**
  - Sidebar minimisé ou caché (bouton hamburger, non natif Streamlit)
  - Colonnes empilées vertically
  - Full-width tableaux (horizontal scroll)
  - Buttons : min 44px height (touch-friendly)
  - Inputs : min 44px height
  - Font : ajustée pour lisibilité
- Aucune perte d'info, juste rearrangement visuel

**Dépendances:**
- CSS media queries dans `_THEME_CSS` (app.py)
- Streamlit's native responsive containers
- Plotly responsive layout

---

#### RF-UI-037 : Accessibilité (WCAG 2.1 AA)

**Priorité:** Should Have
**Statut:** Partiellement implémenté

**Description:**
Respecter les critères WCAG 2.1 niveau AA pour accessibilité.

**Critères d'acceptation:**
- Contraste des couleurs : ratio >= 4.5:1 pour texte/background
- Labels explicites sur tous les inputs
- Images : alt text si pertinent
- Focus visible sur les éléments interactifs
- Navigation au clavier (tabulation possible)
- Sémantique HTML (headings `st.header`, `st.subheader`)
- Icônes : accompagnées de texte (pas d'icône seule)
- Pas de dépendance au couleur seule (utiliser forme + texte)

**Dépendances:**
- Labels sur `st.text_input()`, `st.selectbox()`, etc.
- `help=""` tooltips

---

### RF-UI-038 : Indicateur de chargement et placeholder

**Priorité:** Should Have
**Statut:** Partiellement implémenté

**Description:**
Afficher un state de chargement pendant l'appel API.

**Critères d'acceptation:**
- `st.spinner()` autour des appels API longs
- Placeholder Plotly (graphique gris avec "Chargement...")
- Skeleton loaders pour tableaux (optionnel)
- Pas de blocage complet de la page

**Dépendances:**
- `st.spinner()` wrapper

---

## Exigences Techniques

### RF-UI-039 : Stack Streamlit

**Priorité:** Must Have
**Statut:** Implémenté

**Description:**
Utiliser le stack technologique prescrit.

**Critères d'acceptation:**
- Streamlit >= 1.33 (multi-page navigation)
- Plotly >= 5.0 (graphiques interactifs)
- httpx >= 0.24 (async HTTP client)
- pandas >= 1.5 (manipulation de données)
- pydantic-settings >= 2.0 (config)

**Dépendances:**
- `src/frontend/requirements.txt`

---

### RF-UI-040 : Client API centralisé

**Priorité:** Must Have
**Statut:** Implémenté

**Description:**
Un seul client HTTP centralisé (`APIClient`) pour tous les appels au backend.

**Critères d'acceptation:**
- Classe `APIClient` dans `src/frontend/api_client.py`
- Méthodes :
  - `.get(path, params={})`
  - `.post(path, json={})`
  - `.put(path, json={})`
  - `.delete(path)`
  - `.login(email, password)` → JWT
  - `.register(...)` → user dict
  - `.fetch_crypto_list()`, `.fetch_ohlcv()`, etc.
- Gestion centralisée des erreurs
- Auto-attach JWT aux headers
- Timeout : 10s par défaut
- Une seule instance en `st.session_state["api_client"]`

**Dépendances:**
- `src/frontend/api_client.py`

---

### RF-UI-041 : Configuration externalisée

**Priorité:** Must Have
**Statut:** Implémenté

**Description:**
Toute configuration (API URL, cache TTLs, symbols, timeframes) externalisée en `.env`.

**Critères d'acceptation:**
- Classe `FrontendSettings` dans `src/frontend/config.py`
- Lit `.env` via pydantic-settings
- Variables :
  - `API_URL` : URL du backend
  - `API_TIMEOUT` : timeout HTTP
  - `CACHE_TTL_PRICES`, `CACHE_TTL_SIGNALS`, etc.
  - `TRACKED_SYMBOLS` : liste de cryptos
  - `TIMEFRAMES` : liste de TFs
  - `LOG_LEVEL` : DEBUG, INFO, WARNING, ERROR
- Defaults sensibles (fallback si `.env` absent)
- `.env.example` documenté

**Dépendances:**
- `src/frontend/config.py`
- `.env.example`

---

### RF-UI-042 : Structure des composants

**Priorité:** Should Have
**Statut:** Implémenté

**Description:**
Organiser le code en composants réutilisables.

**Critères d'acceptation:**
- Dossier `src/frontend/components/` avec modules :
  - `candlestick.py` : fonction `render_candlestick(ohlcv, indicators, symbol, timeframe)`
  - `indicators.py` : `render_indicator_summary()`, `render_multi_timeframe_table()`
  - `signal_card.py` : `render_signals_panel(signals)`
  - `news_feed.py` : `render_news_card()`, `render_sentiment_chart()`, `render_word_cloud()`
  - `chatbot.py` : `render_chatbot(client)`
- Chaque composant :
  - Fonction pure ou classe avec `__call__()`
  - Accepte données + optionnellement le client API
  - Retourne None (render directement via `st.*`)
  - Documenté avec docstring

**Dépendances:**
- Module structure

---

### RF-UI-043 : Logging et debugging

**Priorité:** Should Have
**Statut:** Partiellement implémenté

**Description:**
Logging structuré pour debugging en production.

**Critères d'acceptation:**
- Logger `logging.getLogger(__name__)` dans chaque module
- Niveau : `INFO` par défaut ; `DEBUG` activable via `LOG_LEVEL` env
- Format : `%(asctime)s %(name)s %(levelname)s %(message)s`
- Loggé à STDOUT (Streamlit capture dans les conteneurs Docker)
- Pas de `print()` statements
- Logs utiles : API calls, erreurs utilisateur, cache hits

**Dépendances:**
- Module `logging` stdlib

---

## Exigences de Performance

### RF-UI-044 : Temps de chargement initial

**Priorité:** Must Have
**Statut:** À valider

**Description:**
Le dashboard doit charger en < 3 secondes (FCP).

**Critères d'acceptation:**
- TTFB (Time to First Byte) : < 1s
- Interaction (graphique visible) : < 2.5s
- Tous les éléments chargés : < 5s
- Mesuré sur connexion 4G simulée

**Dépendances:**
- Caching API (TTL appropriés)
- Optimisation Plotly (pas trop de points de données)
- Lazy-loading des pages (optionnel)

---

### RF-UI-045 : Optimisation des graphiques Plotly

**Priorité:** Should Have
**Statut:** Partiellement implémenté

**Description:**
Optimiser le rendu des graphiques Plotly pour ne pas ralentir l'UI.

**Critères d'acceptation:**
- Max 500 points de données par graphique
- Décimation côté API si besoin (sample 1/10 si > 5000 barres)
- Pas de graphiques qui rechargent constamment
- Plotly JS bundles minimisés

**Dépendances:**
- Config Plotly optimisée

---

### RF-UI-046 : Caching des ressources statiques

**Priorité:** Nice to Have
**Statut:** À implémenter

**Description:**
Mettre en cache les ressources statiques (CSS, fonts, icons).

**Critères d'acceptation:**
- CDN Lucide : cached (jeudi en ligne par défaut)
- Streamlit JS/CSS : cache navigateur
- Plotly JS : cache navigateur (chargé une fois)

**Dépendances:**
- Headers HTTP Cache-Control (côté Nginx)

---

## Exigences de Sécurité

### RF-UI-047 : Stockage sécurisé du JWT

**Priorité:** Must Have
**Statut:** Implémenté

**Description:**
Stocker le JWT de manière sécurisée, sans l'exposer en URL ou localStorage.

**Critères d'acceptation:**
- JWT stocké en `st.session_state` (mémoire, non persisten)
- Effacé au logout
- Effacé à la fermeture du navigateur (pas de cookie)
- Auto-invalidé après expiration (backend)
- Jamais envoyé à des URLs externes
- HTTPS only en production (géré par Nginx)

**Dépendances:**
- Session state Streamlit

---

### RF-UI-048 : Validation des inputs utilisateur

**Priorité:** Must Have
**Statut:** Implémenté (partiellement)

**Description:**
Valider les inputs avant envoi à l'API.

**Critères d'acceptation:**
- Champs obligatoires : non vides
- Email : format email valide
- Nombres : parsables en float/int
- Longueurs : pas d'inputs excessifs
- Afficher erreurs inline (pas d'appel API invalide)
- Backend valide aussi (defense in depth)

**Dépendances:**
- Pydantic ou règles manuelles via `st.*_input` constraints

---

### RF-UI-049 : Protection CSRF

**Priorité:** Should Have
**Statut:** À valider

**Description:**
Protéger contre les attaques CSRF (SOP + same-site cookies).

**Critères d'acceptation:**
- Streamlit : SOP by default (JS pas possible)
- API : SameSite cookies si utilisés (backend)
- Frontend : pas de vulnérabilité à CSRF

**Dépendances:**
- Backend Nginx + FastAPI config

---

### RF-UI-050 : Pas de données sensibles en logs/localStorage

**Priorité:** Must Have
**Statut:** À valider

**Description:**
Ne jamais logger ou exposer passwords, JWT, ou données personnelles.

**Critères d'acceptation:**
- Logs : pas de passwords, tokens, emails
- Exception handling : pas de stack traces exposés à l'UI
- localStorage/sessionStorage : pas utilisés
- Streamlit session state : pas d'accès external (mémoire seulement)

**Dépendances:**
- Code review

---

## Exigences d'Accessibilité

### RF-UI-051 : Contrast et lisibilité

**Priorité:** Should Have
**Statut:** Implémenté

**Description:**
Assurer un contraste suffisant pour les utilisateurs mal-voyants.

**Critères d'acceptation:**
- Texte/background : ratio >= 4.5:1 (AA)
- Headline/background : ratio >= 3:1 (AA large)
- Couleurs testées avec Stark (Figma plugin) ou WebAIM

**Dépendances:**
- Palette de couleurs validée

---

### RF-UI-052 : Navigation au clavier

**Priorité:** Should Have
**Statut:** Implémenté (natif Streamlit)

**Description:**
Tous les éléments interactifs accessibles via Tab/Enter/Espace.

**Critères d'acceptation:**
- Tab order logique
- Focus visible sur tous les boutons/inputs
- Pas de trap focus
- Streamlit native (pas besoin d'implémentation custom)

---

### RF-UI-053 : Labels explicites sur inputs

**Priorité:** Should Have
**Statut:** Implémenté

**Description:**
Chaque input a un label visible associé.

**Critères d'acceptation:**
- `st.selectbox("label", ...)` — label visible
- `st.text_input("label", ...)` — label visible
- Pas d'inputs orphelines
- Screen readers : labels associés via Streamlit

---

## Tableau Récapitulatif des Exigences

| ID | Description | Priorité | Statut | Page(s) |
|----|----|----------|--------|---------|
| RF-UI-001 | Graphique candlestick OHLCV | Must | Partial | Dashboard |
| RF-UI-002 | Sélecteur de crypto | Must | ✅ | Dashboard |
| RF-UI-003 | Sélecteur de timeframe | Must | ✅ | Dashboard |
| RF-UI-004 | Bouton Rafraîchir | Should | ✅ | Dashboard |
| RF-UI-005 | Indicateur connexion API | Should | ✅ | Dashboard |
| RF-UI-006 | Affichage indicateurs | Must | Partial | Dashboard |
| RF-UI-007 | Tableau multi-timeframe | Should | Partial | Dashboard |
| RF-UI-008 | Panneau signaux | Must | Partial | Dashboard |
| RF-UI-009 | Panneau news mini | Should | Partial | Dashboard |
| RF-UI-010 | Fil de news avec filtres | Must | Partial | Veille |
| RF-UI-011 | Graphique sentiment | Should | Partial | Veille |
| RF-UI-012 | Nuage de mots | Should | Partial | Veille |
| RF-UI-013 | Export CSV | Should | ✅ | Veille |
| RF-UI-014 | Export PNG/SVG | Nice | Native | Veille |
| RF-UI-015 | Tableau portfolio | Must | Partial | Portfolio |
| RF-UI-016 | Métriques P&L | Should | ✅ | Portfolio |
| RF-UI-017 | Formulaire ajout position | Must | Partial | Portfolio |
| RF-UI-018 | Formulaire édition | Should | ✅ | Portfolio |
| RF-UI-019 | Suppression avec confirmation | Should | ✅ | Portfolio |
| RF-UI-020 | Watchlist | Should | ✅ | Portfolio |
| RF-UI-021 | Chatbot IA | Should | Partial | Portfolio |
| RF-UI-022 | Heatmap performances | Should | TODO | Analytics |
| RF-UI-023 | Market overview | Nice | TODO | Analytics |
| RF-UI-024 | Fear & Greed historique | Nice | TODO | Analytics |
| RF-UI-025 | Comparateur crypto | Nice | TODO | Analytics |
| RF-UI-026 | Historique signaux | Should | TODO | Performance |
| RF-UI-027 | Taux de succès signaux | Should | TODO | Performance |
| RF-UI-028 | Graphique P&L cumulé | Should | TODO | Performance |
| RF-UI-029 | Performance par crypto/TF | Nice | TODO | Performance |
| RF-UI-030 | Navigation multi-pages | Must | ✅ | All |
| RF-UI-031 | Thème dark/light | Should | ✅ | All |
| RF-UI-032 | i18n FR/EN | Should | ✅ | All |
| RF-UI-033 | Caching API | Must | ✅ | All |
| RF-UI-034 | Gestion d'erreurs | Must | ✅ | All |
| RF-UI-035 | Authentification | Must | ✅ | All |
| RF-UI-036 | Layout responsive | Should | ✅ | All |
| RF-UI-037 | Accessibilité WCAG | Should | Partial | All |
| RF-UI-038 | Indicateur chargement | Should | Partial | All |
| RF-UI-039 | Stack Streamlit | Must | ✅ | Tech |
| RF-UI-040 | Client API centralisé | Must | ✅ | Tech |
| RF-UI-041 | Configuration externalisée | Must | ✅ | Tech |
| RF-UI-042 | Structure composants | Should | ✅ | Tech |
| RF-UI-043 | Logging | Should | Partial | Tech |
| RF-UI-044 | Temps chargement < 3s | Must | ? | Perf |
| RF-UI-045 | Optimisation Plotly | Should | Partial | Perf |
| RF-UI-046 | Caching ressources statiques | Nice | TODO | Perf |
| RF-UI-047 | Stockage JWT sécurisé | Must | ✅ | Sec |
| RF-UI-048 | Validation inputs | Must | Partial | Sec |
| RF-UI-049 | Protection CSRF | Should | ? | Sec |
| RF-UI-050 | Pas de données sensibles | Must | ? | Sec |
| RF-UI-051 | Contrast WCAG AA | Should | ? | A11y |
| RF-UI-052 | Navigation clavier | Should | ✅ | A11y |
| RF-UI-053 | Labels inputs | Should | ✅ | A11y |

---

## Notes de Livraison

### Dépendances inter-équipes

- **Backend API** : doit exposer tous les endpoints listés (RF-UI-010 à RF-UI-029)
- **DevOps** : Dockerfile frontend, Nginx routing, HTTPS/TLS en prod
- **ML** : génération des signaux (RF-UI-008, RF-UI-026-029)
- **ETL** : collecte de données OHLCV, news, sentiments

### Critères de fin de sprint

- [ ] Toutes les pages Must Have au minimum 70% complètes
- [ ] Pas de errors Streamlit console
- [ ] `ruff check src/frontend/` passe
- [ ] `mypy src/frontend/` passe (strict)
- [ ] Aucun secrets hardcodés (.env.example seulement)
- [ ] API client : 100% des endpoints implémentés
- [ ] Responsive test : Desktop (1920), Tablet (800), Mobile (375)
- [ ] Accessibility : tests WAVE WebAIM sans erreur (AA min)

### Timeline estimée

| Sprint | Deliverables | Effort |
|--------|---|--------|
| Sprint 7 (Avril) | Pages Dashboard + Veille basique + Auth | 40h |
| Sprint 8 (Mai) | Portfolio complet + Analytics basique | 30h |
| Sprint 9 (Juin) | Performance + Polish + Optimizations | 20h |
| **Total** | | **90h** |

---

## Appendix A : Glossaire

| Terme | Définition |
|-------|-----------|
| **OHLCV** | Open, High, Low, Close, Volume — données candlestick |
| **Timeframe (TF)** | Granularité temporelle (1h, 4h, 1D, etc.) |
| **Signal** | Recommandation BUY/SELL/HOLD du ML engine (confiance >= 0.6) |
| **RSI** | Relative Strength Index — indicateur momentum (0-100) |
| **Bollinger Bands** | Bandes de volatilité autour d'une SMA 20 |
| **Portfolio** | Positions de cryptos détenues par l'utilisateur (virtuel) |
| **Watchlist** | Liste de cryptos suivies par l'utilisateur |
| **JWT** | JSON Web Token — token d'authentification stateless |
| **Cache TTL** | Time To Live — durée de validité du cache en secondes |
| **SOP** | Same-Origin Policy — sécurité navigateur |
| **WCAG** | Web Content Accessibility Guidelines — normes d'accessibilité |

---

## Appendix B : Références API Backend

Tous les endpoints consommés par le frontend :

```
Authentication:
  POST   /api/v1/auth/login          (email, password) → {access_token}
  POST   /api/v1/auth/register       (username, email, password, persona_type) → {user}
  GET    /api/v1/auth/me             (JWT) → {username, email, persona_type}

Crypto Data:
  GET    /api/v1/crypto/list                      () → [{symbol, name}]
  GET    /api/v1/crypto/{symbol}/prices           (timeframe, limit) → [{timestamp, price_*}]
  GET    /api/v1/crypto/{symbol}/indicators       (timeframe) → [{rsi, bollinger_*}]
  GET    /api/v1/crypto/{symbol}/latest           () → {price_*, indicators}
  GET    /api/v1/crypto/market-overview           () → {total_market_cap, ...}

Signals:
  GET    /api/v1/signals/active                   () → [{symbol, direction, confidence}]
  GET    /api/v1/signals/{symbol}                 () → [{...}]
  GET    /api/v1/signals/{signal_id}/detail       () → {full_signal_data}
  GET    /api/v1/signals/performance              (period) → {win_rate, total, ...}

News:
  GET    /api/v1/news/latest                      (source, keyword, limit) → [{title, sentiment_score}]
  GET    /api/v1/news/{news_id}                   () → {full_article}
  GET    /api/v1/news/sentiment                   () → [{symbol, sentiment_score}]

Portfolio (JWT required):
  GET    /api/v1/portfolio                        () → [{id, symbol, quantity, entry_price}]
  POST   /api/v1/portfolio                        (symbol, quantity, entry_price, notes) → {position}
  PUT    /api/v1/portfolio/{position_id}          (quantity, entry_price, notes) → {updated}
  DELETE /api/v1/portfolio/{position_id}          () → {success}

Watchlist (JWT required):
  GET    /api/v1/watchlist                        () → [{symbol}]
  POST   /api/v1/watchlist                        (symbol) → {entry}
  DELETE /api/v1/watchlist/{symbol}               () → {success}

Chat (JWT required):
  POST   /api/v1/chat                             (message) → {reply, disclaimer}

Health:
  GET    /api/health                              () → {status}
```

---

**Document Version:** 1.0
**Date:** 2026-03-12
**Auteur:** Product Manager Frontend & UX
**Approuvé par:** [Equipe Frontend]
**État:** Draft → Ready for Development
