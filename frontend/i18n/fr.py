"""French translations."""

from __future__ import annotations

TRANSLATIONS: dict[str, str] = {
    # app
    "app.subtitle": "Surveillance & Signaux",
    "app.disclaimer": "Projet scolaire - pas de conseil financier.",
    # api
    "api.unavailable": "API non disponible. Vérifiez que le backend est démarré.",
    "api.invalid_response": "Réponse invalide du backend.",
    "api.http_error": "Erreur API ({status}).",
    # nav
    "nav.dashboard": "Dashboard",
    "nav.analytics": "Analytics",
    "nav.signals": "Signaux",
    # dashboard
    "dashboard.header": "Dashboard",
    "dashboard.api_connected": "API connectée",
    "dashboard.api_offline": "API hors ligne",
    "dashboard.crypto": "Crypto",
    "dashboard.timeframe": "Timeframe",
    "dashboard.refresh": "Actualiser",
    "dashboard.candlestick_header": "Graphique chandelier",
    "dashboard.chart_unavailable": "Graphique indisponible - vérifiez la connexion au backend.",
    "dashboard.no_data_title": "Aucune donnée disponible",
    "dashboard.no_ohlcv_data": "Aucune bougie pour {symbol} ({timeframe}). Le collecteur ETL n'a peut-être pas encore ingéré ce symbole.",
    "dashboard.indicators_header": "Indicateurs",
    "dashboard.signals_header": "Signaux récents",
    "dashboard.no_signals": "Aucun signal disponible.",
    # analytics
    "analytics.header": "Analytics",
    "analytics.market_cap": "Market Cap Total",
    "analytics.btc_dominance": "BTC Dominance",
    "analytics.eth_dominance": "ETH Dominance",
    "analytics.data_unavailable": "Donnée non disponible",
    "analytics.top_movers": "Top Movers",
    "analytics.gainers": "Gainers (24h)",
    "analytics.losers": "Losers (24h)",
    "analytics.col_crypto": "Crypto",
    "analytics.col_price": "Prix",
    "analytics.col_change_24h": "Variation 24h",
    "analytics.col_volume_24h": "Volume 24h",
    "analytics.no_gainers": "Aucun gainer disponible",
    "analytics.no_losers": "Aucun loser disponible",
    "analytics.correlation_title": "Matrice de Corrélation (closes journaliers)",
    "analytics.correlation_chart_title": "Corrélation des rendements journaliers",
    "analytics.correlation_insufficient": "Données insuffisantes pour calculer la matrice de corrélation.",
    "analytics.correlation_min_hint": "Au moins 2 symboles avec historique sont requis.",
    "analytics.backend_unavailable": "Backend non disponible - impossible de charger les analytics.",
    "analytics.backend_hint": "Vérifiez que le service FastAPI est démarré et accessible.",
    "analytics.heatmap_title": "Performance 24h",
    "analytics.heatmap_chart_title": "Performance 24h par crypto",
    "analytics.no_heatmap": "Aucune donnée de performance disponible.",
    "analytics.volume_header": "Volumes 24h",
    # signals page
    "signals.header": "Signaux Techniques",
    "signals.symbol": "Symbole",
    "signals.timeframe": "Timeframe",
    "signals.limit": "Nombre de bougies",
    "signals.no_data": "Aucune donnée pour {symbol} ({timeframe}).",
    "signals.col_timestamp": "Timestamp",
    "signals.col_close": "Clôture",
    "signals.col_rsi": "RSI(14)",
    "signals.col_sma20": "SMA(20)",
    "signals.col_ema20": "EMA(20)",
    "signals.col_macd": "MACD",
    "signals.col_bb_upper": "BB Upper",
    "signals.col_bb_lower": "BB Lower",
    # candlestick component
    "candlestick.no_data_title": "Aucune donnée OHLCV disponible",
    "candlestick.no_data_annotation": "Aucune donnée à afficher",
    "candlestick.price_axis": "Prix (USDT)",
    # indicators component
    "indicators.not_available": "Indicateurs non disponibles.",
    "indicators.rsi_overbought": "Suracheté",
    "indicators.rsi_oversold": "Survendu",
    "indicators.rsi_neutral": "Neutre",
    "indicators.bb_above_upper": "Au-dessus bande sup.",
    "indicators.bb_near_upper": "Proche bande sup.",
    "indicators.bb_below_lower": "Sous bande inf.",
    "indicators.bb_near_lower": "Proche bande inf.",
    "indicators.bb_middle": "Milieu",
    "indicators.macd_bullish": "Haussier",
    "indicators.macd_bearish": "Baissier",
    "indicators.macd_neutral": "Neutre",
    # nav
    "nav.veille": "Veille",
    # news / veille page
    "news.header": "Veille Crypto",
    "news.filters": "Filtres",
    "news.all_sources": "Toutes les sources",
    "news.all_sentiments": "Tous",
    "news.source_label": "Source",
    "news.sentiment_label": "Sentiment",
    "news.limit": "Nombre d'articles",
    "news.loading": "Chargement des actualités…",
    "news.no_articles": "Aucun article disponible pour ces filtres.",
    "news.no_sentiment": "Aucune donnée de sentiment disponible.",
    "news.article_count": "{n} article(s) affiché(s)",
    "news.tab_articles": "Articles",
    "news.tab_sentiment": "Sentiment",
    "news.sentiment_by_source": "Sentiment par source",
    "news.positive": "Positif",
    "news.negative": "Négatif",
    "news.neutral": "Neutre",
    "news.avg_score": "Score moyen",
    # ml / backtesting
    "ml.header": "Backtesting ML",
    "ml.nav": "ML & Backtesting",
    "ml.what_is_title": "C'est quoi le backtesting ?",
    "ml.what_is_body": """
Le **backtesting** consiste à tester une stratégie de trading sur des données *historiques* pour évaluer
ce qu'elle aurait rapporté dans le passé. C'est la seule façon objective de valider un modèle ML
avant de le confronter aux marchés réels.

**Pourquoi le walk-forward ?**
On ne mélange jamais passé et futur. À chaque fold, le modèle s'entraîne sur une fenêtre de dates
puis est testé sur la fenêtre *suivante* — exactement comme en production.

```
|— train 180j —|purge|— test 30j —|embargo|— train 180j —|purge|— test 30j —| ...
```

- **Purge** : quelques jours retirés entre train et test pour éviter que les labels se chevauchent.
- **Embargo** : quelques jours sautés après le test pour éviter les corrélations résiduelles.

**Limite importante** : de bons résultats sur le passé ne garantissent pas les performances futures.
Le backtesting est un outil de validation, pas une promesse.
""",
    "ml.params_title": "Paramètres",
    "ml.symbol": "Symbole",
    "ml.timeframe": "Timeframe",
    "ml.model_type": "Modèle",
    "ml.train_window": "Fenêtre d'entraînement (jours)",
    "ml.test_window": "Fenêtre de test (jours)",
    "ml.run_button": "Lancer le backtest",
    "ml.running": "Calcul en cours…",
    "ml.no_data": "Aucune donnée — vérifiez le symbole et la timeframe.",
    "ml.not_enough_data": "Pas assez de données historiques pour ces paramètres. Réduisez les fenêtres ou collectez plus de données.",
    "ml.results_title": "Résultats",
    "ml.metrics_title": "Métriques agrégées",
    "ml.folds_title": "Détail par fold",
    "ml.baseline_title": "Stratégie vs Buy-and-Hold",
    "ml.metric_sharpe": "Sharpe ratio",
    "ml.metric_winrate": "Win rate",
    "ml.metric_pnl": "PnL total",
    "ml.metric_drawdown": "Max Drawdown",
    "ml.metric_accuracy": "Accuracy",
    "ml.metric_pf": "Profit Factor",
    "ml.baseline_strategy": "Stratégie ML",
    "ml.baseline_bah": "Buy & Hold",
    "ml.baseline_excess": "Excès de rendement",
    "ml.metrics_explain_title": "Comment lire ces métriques ?",
    "ml.metrics_explain_body": """
| Métrique | Ce qu'elle mesure | Bon signe |
|---|---|---|
| **Sharpe ratio** | Rendement ajusté du risque (annualisé) | > 1.0 |
| **Win rate** | % de trades gagnants | > 50 % |
| **PnL total** | Somme des log-returns sur les positions BUY | > 0 |
| **Max Drawdown** | Perte max pic → creux | Proche de 0 |
| **Profit Factor** | Gains bruts / Pertes brutes | > 1.0 |
| **Accuracy** | % de prédictions correctes | > 55 % (marchés bruités) |

Le **buy-and-hold** est la stratégie de référence : acheter et ne rien faire.
Si la stratégie ML ne bat pas le buy-and-hold, elle n'apporte pas de valeur.
""",
    # fear & greed
    "fng.title": "Fear & Greed Index",
    "fng.subtitle": "Sentiment du marché crypto (alternative.me)",
    "fng.unavailable": "Indice non disponible",
    "fng.extreme_fear": "Peur Extrême",
    "fng.fear": "Peur",
    "fng.neutral": "Neutre",
    "fng.greed": "Avidité",
    "fng.extreme_greed": "Avidité Extrême",
    # news vader
    "news.vader_title": "Comment est calculé le sentiment ?",
    "news.vader_explanation": """
**Score VADER** (Valence Aware Dictionary and sEntiment Reasoner)

Chaque article reçoit un **score compound** entre **-1** et **+1**, calculé à partir du titre et du début du contenu :

| Score | Label | Interprétation |
|---|---|---|
| ≥ +0.05 | ▲ Positif | Tonalité optimiste (hausse, record, adoption…) |
| ≤ -0.05 | ▼ Négatif | Tonalité pessimiste (crash, hack, régulation…) |
| Entre les deux | ● Neutre | Factuel ou ambigu |

VADER analyse chaque mot via un dictionnaire pondéré et tient compte de la ponctuation (majuscules, points d'exclamation).
L'**agrégat par source** (onglet Sentiment) permet de comparer la tonalité globale de chaque média.
""",
}
