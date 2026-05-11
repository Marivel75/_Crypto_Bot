---
type: rncp
bloc: 4
competence: C4.3.1
title: Tech Radar CryptoBot — veille technologique
project: cryptobot
tags: [cryptobot, rncp, bloc4, veille, tech-radar]
created: 2026-04-14
source_of_truth: history/themes.md
related: [[meta/stack]], [[history/themes]], [[specs/adrs-phase2]], [[rncp/bloc4-pilotage/veille-reglementaire]]
---

# Tech Radar CryptoBot

Inspire du **Thoughtworks Tech Radar** : 4 anneaux concentriques (Adopt / Trial / Assess / Hold) et 4 quadrants (Langages & Frameworks / Outils / Plateformes / Techniques). Le radar materialise la veille technologique de l'equipe et fonde les decisions d'evolution stack.

## 1. Principes

- **Adopt** — technos matures, deployees en production, recommandees par defaut. Aucun debat.
- **Trial** — en production partielle, verdict pragmatique positif, a generaliser apres validation.
- **Assess** — evaluation active, POC ou veille ciblee. Pas encore en production.
- **Hold** — technologies a eviter pour les nouveaux developpements. Remplacement en cours ou deprecation imminente.

## 2. Adopt (16)

### Langages et frameworks
- **Python 3.11** — base du projet, syntaxe moderne (`X | Y`, `match`, `asyncio.timeout`).
- **FastAPI** — framework API async, source de verite OpenAPI, integration Pydantic native.
- **Pydantic v2** — toutes les structures de donnees (30+ schemas, 7 packages).
- **pytest** — runner de tests standard, coverage ≥ 80 %.

### Outils
- **Ruff** — lint + format, remplace black/isort/flake8.
- **uv** — installation et environnement reproductible, plus rapide que pip/poetry.
- **Polars** — dataframes vectorises, privilegie a pandas.
- **PlantUML** — 22 diagrammes architecture, source de verite visuelle.

### Plateformes
- **TimescaleDB** (PostgreSQL 16 + extension) — hypertable `crypto_prices`, compression 7j, retention 90j.
- **Docker Compose** — 12 services, 2 networks, 4 volumes (~5.8 GB).
- **Nginx** — reverse proxy, TLS termination.
- **Let's Encrypt (certbot)** — SSL/TLS automatique, sidecar container.
- **Cloudflare** — DNS + proxy + protection DDoS.

### Techniques
- **GitHub Actions** — CI/CD principal (projet SAP + CryptoBot).
- **Loki + Grafana + Prometheus** — stack observabilite (metriques + logs + alerting).
- **Conventional Commits** — `type(scope): description`, scopes projet `etl|ml|api|frontend|infra|shared`.

## 3. Trial (12)

### Langages et frameworks
- **Streamlit 1.3x** — frontend SSR, 5 pages, client REST api_client.py. Choisi vs Dash pour rapidite dev + support Plotly natif.
- **asyncpg** — driver async PostgreSQL, pool 10/20.
- **pydantic-settings** — configuration centralisee via `src/shared/config.py`.

### Outils
- **MLflow 2.x** — experiment tracking ML Phase 2.
- **DVC** — versioning datasets ML.
- **XGBoost / LightGBM** — models ML supervised Phase 2.
- **respx** — mocking HTTP pour tests integration.
- **mermaid** — diagrammes secondaires (complement a PlantUML).

### Plateformes
- **MinIO** — S3-compatible object storage, artefacts MLflow + datasets.
- **Ansible** — provisioning VPS OVH, deploiement prod.

### Techniques
- **hex-line / hex-graph MCP** — optimisation token (vs lecture brute de fichiers).

## 4. Assess (11)

### Langages et frameworks
- **LSTM PyTorch** — models sequentiels pour Phase 2 (prediction direction/returns).
- **Gymnasium RL** — evaluation reinforcement learning pour generation signaux (post-Phase 2).

### Outils
- **K-means / HDBSCAN** — clustering regimes de marche.
- **locust / k6** — load testing API avant mise en prod.
- **OpenTelemetry** — traces distribuees (complementaire a Prometheus).
- **Vector.dev** — remplacement prevu de Promtail (EOL mars 2026) pour ingestion logs Loki.
- **Dagster** — alternative APScheduler, DAG avec observabilite native.
- **Great Expectations** — data quality sur les datasets ML + OHLCV.

### Plateformes
- **Kubernetes** — post-ecole, pour scaling multi-instances (non V1).
- **Helm** — packaging applicatif K8s (conditionne a adoption K8s).
- **Ollama self-hosted LLM** — alternative au LLM externe pour chatbot assistant (souverainete donnees).

## 5. Hold (7)

- **pandas** — remplace par Polars pour toute manipulation dataframe (perfs + memoire).
- **Flask** — incompatible async, remplace par FastAPI.
- **Promtail** — EOL mars 2026, migration vers Vector.dev planifiee.
- **Elasticsearch** — trop lourd pour le volume logs du projet, Loki suffit.
- **Kubernetes pour V1** — complexite operationnelle injustifiee a l'echelle ecole.
- **Oracle DB** — licence fermee, non alignee avec la stack open-source du projet.
- **Alertmanager** — Grafana Alerting natif couvre tous les besoins, reduction de stack.

## 6. Gouvernance du radar

- **Revue trimestrielle** animee par le lead DevOps + lead tech (Jules).
- **Entrees/sorties** tracees dans [[CryptoBot/avril/history/themes]] avec obs-id, justification et impact prevu.
- **Mouvement autorise** : Assess → Trial → Adopt (ou Hold) ; Adopt → Hold uniquement apres ADR formel.
- **Participants** : tous les leads d'equipe (Data Eng, ML, Backend, Frontend, DevOps) soumettent des propositions via PR sur ce fichier.
- **Critere d'entree Adopt** : ≥ 3 mois en Trial sans regression bloquante + couverture ≥ 80 %.

## 7. Sources de veille

Flux RSS et canaux suivis (frequence de revue en parentheses) :

- **Thoughtworks Tech Radar** — radar de reference, nouvelle edition tous les 6 mois.
- **awesome-python** (GitHub) — decouverte libs Python (mensuel).
- **HackerNews** front page — tendances tech globales (quotidien, filtre 48 h).
- **InfoQ** — architecture, DevOps, ML (hebdo).
- **SpeakerDeck** — talks conferences (mensuel, filtres Python / data).
- **Reddit** r/Python, r/datascience, r/fastapi, r/MachineLearning (hebdo).
- **Twitter/X** — listes curatees : core dev Python, leads data, pentesters.
- **Conferences** — PyCon (mai), PyData (automne), FOSDEM (fevrier), EuroPython (juillet). Restitution systematique dans [[CryptoBot/avril/history/themes]] apres chaque evenement.
- **Newsletter** : Python Weekly, Real Python, Data Elixir, DevOps'ish.

## Documents lies

[[CryptoBot/avril/meta/stack]] | [[CryptoBot/avril/specs/adrs-phase2]] | [[CryptoBot/avril/history/themes]] | [[rncp/bloc4-pilotage/veille-reglementaire]]
