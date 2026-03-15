# Audit de Conformite — CryptoBot vs Cadrage PDF

**Date:** 2026-03-15
**Score global:** 67%
**Source:** Crypto_bot_cadrage_V2.pdf

## Score par axe

| Axe | Poids | Score |
|-----|-------|-------|
| Fonctionnalites | 30% | 65% |
| Stack technique | 15% | 72% |
| Contraintes techniques | 15% | 75% |
| Calendrier | 10% | 92% |
| Personas | 20% | 62% |
| Sources de veille | 10% | 40% |

## 8 Features Manquantes (33%)

| # | Feature | Cadrage PDF | Status |
|---|---------|-------------|--------|
| F1 | Paper Trading | "Passage d'ordre en paper trading" | A developper |
| F2 | Reinforcement Learning | "Monte Carlo, SARSA, Q-learning" | A developper |
| F3 | Deep Learning LSTM | "TensorFlow/PyTorch" | A developper |
| F4 | Clustering non supervise | "apprentissage non supervise" | A developper |
| F5 | Donnees on-chain | Persona Noah: "donnees on-chain" | A developper |
| F6 | Systeme d'alertes | 3 personas demandent alertes | A developper |
| F7 | Sources reglementaires | "ESMA, SEC, EU Blockchain Observatory" | A developper |
| F8 | Web scraping BeautifulSoup | "requests, BeautifulSoup" dans stack | A developper |

## Features implementees (67%)

- Veille actu et marche (RSS)
- Portefeuille de valeurs evolutif (watchlist + portfolio CRUD)
- Suivi des cours crypto (Binance, CoinGecko, CCXT)
- Dashboard (5 pages Streamlit + Plotly)
- Analytics (heatmap, correlations, Fear and Greed)
- ML supervise (XGBoost + rule engine)
- NLP sentiment (TF-IDF, word cloud)
- Backtesting walk-forward
- Monitoring (Prometheus, Grafana)
- Chatbot IA (Claude)
- CI/CD (GitHub Actions, Docker Compose, Ansible)
