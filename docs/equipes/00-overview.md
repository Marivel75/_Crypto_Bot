# 00 — Vue d'ensemble du projet

> **Ce document doit etre lu par TOUTES les equipes.** Il donne le contexte global du projet.

---

## Resume

**Crypto Bot** est un projet d'ecole qui cree une plateforme de veille, analytics et aide au trading crypto. Le projet :
- Collecte des donnees de prix sur le **top 30 cryptos** via des APIs gratuites (Binance, CoinGecko)
- Calcule des **indicateurs techniques multi-timeframes** (RSI, Bollinger, harmonics, trend lines)
- Apprend les **patterns bull/bear** via un systeme de regles puis du ML supervise
- Genere des **signaux informatifs** (BUY/SELL/HOLD) — **PAS d'execution automatique de trades**
- Affiche tout dans un **dashboard Streamlit** avec chatbot IA

## Stack V1

```
Python 3.11+ | FastAPI | Streamlit | Plotly
PostgreSQL + TimescaleDB | MinIO (S3) | MLflow + DVC
Docker Compose | Nginx | GitHub Actions
```

## Architecture globale

```
+-------------------------------------------+
|         SOURCES DE DONNEES                 |
| [Binance public] [CoinGecko Demo] [CCXT]  |
| [Decrypt] [Cointelegraph] [PhoenixNews]   |
| [ESMA] [SEC] [Alternative.me]             |
+------------------+------------------------+
                   |
          +--------v---------+
          |   ETL PIPELINE   |    ← Equipe Data Engineering
          |  Python services  |
          |  APScheduler      |
          +--------+---------+
                   |
          +--------v---------+
          |   TimescaleDB    |    ← Equipe Data Engineering (schema)
          |   + MinIO (S3)   |
          +--------+---------+
                   |
     +-------------+-------------+
     |                           |
+----v--------+           +-----v-------+
| ML ENGINE   |           | FastAPI     |    ← Equipe Backend
| Regles + ML |           | API REST    |
| MLflow      |           +-----+-------+
+----+--------+                 |
     |  ← Equipe ML       +----v-------+
     |                     | Streamlit  |    ← Equipe Frontend
     +-------------------->| + Plotly   |
                           +------------+

[Docker Compose + Nginx + CI/CD]    ← Equipe DevOps
```

## Personas

### Noah, 32 ans — Trader independant
- Suit le marche crypto quotidiennement
- Trade des perpetuels sur Hyperliquid (DEX)
- Veut une vue unifiee : bougies + news + indicateurs + signaux
- Besoins : signaux multi-timeframes, indicateurs techniques, alertes, journal de trades

### Sarah, 30 ans — Journaliste financiere
- Specialisation crypto pour un quotidien
- Pas de competences techniques
- Besoins : veille automatisee, alertes reglementaires, graphiques exportables, resumes NLP

### Aleksandar, 35 ans — Investisseur debutant
- Petit portefeuille crypto (Revolut)
- Veut comprendre le marche simplement
- Besoins : chatbot IA, signaux vulgarises, suivi de portefeuille basique

## Cryptos suivies

Top 30 par market cap. Les 13 prioritaires : BTC, ETH, USDT, USDC, BNB, XRP, SOL, ADA, AVAX, DOT, DOGE, TRX, ATOM.

## Ce que le projet NE FAIT PAS

- Pas d'execution automatique de trades
- Pas de gestion de fonds clients
- Pas de sources de donnees payantes (Glassnode, Dune, etc.)
- Pas de Kubernetes (Docker Compose suffit)
- Pas de broker evenementiel (Redis/RabbitMQ)
- C'est un projet d'ecole, pas une startup

## Decisions architecturales

| ADR | Decision | Justification |
|-----|----------|---------------|
| ADR-001 | TimescaleDB au lieu de PostgreSQL vanilla | Donnees OHLCV = series temporelles, compression, requetes rapides |
| ADR-002 | Suppression de MongoDB | JSONB PostgreSQL suffit pour les donnees non structurees |
| ADR-003 | MinIO (S3 self-hosted) | Datasets, modeles, artefacts MLflow sans lakehouse |
| ADR-004 | Pas de broker | APScheduler/cron Docker suffisent en V1 |
| ADR-005 | Streamlit au lieu de Dash | Plus rapide a dev, support Plotly natif, suffisant pour projet ecole |
| ADR-006 | Pas d'execution automatique | Signaux informatifs uniquement |
