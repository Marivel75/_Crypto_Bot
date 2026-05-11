---
type: rncp-livrable
bloc: soutenance
titre: Outline slides soutenance CryptoBot
diplome: RNCP38919
projet: cryptobot
duree_presentation: 15 min
duree_qa: 15 min
nb_slides: 30
date_soutenance: 2026-06-11
statut: draft-v1
tags: [cryptobot, rncp, soutenance, slides, presentation]
created: 2026-04-14
owner: L5-Finance-Soutenance
---

# Outline slides soutenance — CryptoBot RNCP38919

**Format** : 30 slides, 15 min présentation + 15 min Q&A.
**Règle** : 1 slide = 30 secondes de parole en moyenne (30 slides × 30s = 15 min).
**Ton** : technique, factuel, orienté évidences. Pas de marketing.

---

## Slide 1 — Titre

- **Projet** : CryptoBot — Plateforme de veille crypto et signaux pondérés
- **Étudiants** : Jules Willard (PO + Data Eng), Mikael [Nom] (ML part-time)
- **Diplôme** : RNCP38919 — Expert en Architecture Digitale
- **Date soutenance** : 11 juin 2026
- **Jury** : [noms à compléter]
- Logo école + logo projet

**Narration (30s)** : « Bonjour, nous présentons CryptoBot, un projet de veille et de signaux crypto développé sur 6 sprints dans le cadre du RNCP38919. »

---

## Slide 2 — Problématique

- Question : **Comment générer des signaux de trading crypto interprétables sans automatiser l'exécution ?**
- 3 constats : opacité des outils SaaS, coût élevé (235 €/mois stack), manque de multi-persona
- Contexte 2026 : marché crypto volatil, MiCA en vigueur UE, explosion data on-chain

**Narration (30s)** : « Le marché crypto 2026 est saturé d'outils SaaS opaques et coûteux. Notre question : peut-on offrir des signaux interprétables, adaptés au profil utilisateur, sans automatiser l'exécution ? »

---

## Slide 3 — Proposition de valeur

- **3 piliers** :
  1. Dashboard de veille (OHLCV + news + régulation)
  2. Signaux pondérés multi-timeframe (confidence ≥ 0,6)
  3. Multi-persona (3 profils : Noah novice / Alex intermédiaire / Sam trader)
- **Différenciateur** : pas de trade auto, transparence totale (indicateurs visibles)

**Narration (30s)** : « Trois piliers : veille agrégée, signaux explicables, et multi-persona. Nous refusons l'exécution automatique par conviction éthique. »

---

## Slide 4 — Contraintes & éthique

- Strictement **informationnel** — aucune API exchange writeable connectée
- Conformité **RGPD** : consentement cookies, droit oubli, export data user
- Conformité **MiCA** (UE 2024) : disclaimers "not financial advice", pas de recommandation personnalisée
- Aucune gestion de clés privées utilisateurs

**Narration (30s)** : « Contraintes fortes : informationnel uniquement, RGPD + MiCA. Pas de clé privée user, pas d'ordre auto. »

---

## Slide 5 — Architecture macro (C01)

- [Insérer SVG `docs/diagrams/C01-macro.svg` de la page [[_other/common/projects/MPP/architecture/C01-macro]]]
- Flux : sources externes -> ETL -> TimescaleDB + MinIO -> ML -> API -> Frontend
- 12 services Docker Compose

**Narration (30s)** : « L'architecture C01 : 6 couches, 12 services Docker Compose, tout self-hosted sur VPS OVH. »

---

## Slide 6 — Stack technique

| Couche | Techno |
|--------|--------|
| Data | Python 3.11, Polars, Binance, CoinGecko, CCXT, RSS |
| Stockage | TimescaleDB 2.x (hypertables), MinIO S3, MLflow |
| ML | scikit-learn, XGBoost, LightGBM (Phase 1) + LSTM/DQN (Phase 2) |
| API | FastAPI 0.110, Pydantic v2, SQLAlchemy 2 async, JWT |
| Frontend | Streamlit + Plotly (SSR) |
| Infra | Docker Compose, Nginx, Let's Encrypt, Ansible, GitHub Actions |

**Narration (30s)** : « Stack Python end-to-end, pas de K8s, Streamlit pour rapidité, TimescaleDB pour time-series. »

---

## Slide 7 — Équipes & frontières

- **5 équipes** : Data Eng / ML / Backend / Frontend / DevOps
- Chaque équipe a son dossier `src/` et son doc `docs/0X-*.md`
- **Contrat cross-team** : `src/shared/` (models Pydantic, config, exceptions)
- Règle dure : jamais de code hors de son team boundary

**Narration (30s)** : « Cinq équipes isolées, communication uniquement via shared interfaces. Discipline stricte pour éviter les conflits de merge. »

---

## Slide 8 — Sprint roadmap (Gantt)

- [Insérer extrait Gantt S11-S16 de [[CryptoBot/avril/planning/gantt]]]
- S11 quick wins → S12 medium → S13-S14 paper trading → S15-S16 RL + polish
- Total : **62 story points** sur 6 sprints, vélocité cible 16 pts/sprint
- Soutenance : 11 juin 2026

**Narration (30s)** : « 6 sprints de 2 semaines, 62 points de story. Chemin critique sur RL en S15-S16, contingence Plan B-1 prête. »

---

## Slide 9 — Bloc 2 — Pipeline ETL (C02 + AC01)

- [Insérer diagramme C02 composants ETL + AC01 activité pipeline]
- Collecteurs : Binance (WS + REST), CoinGecko, CCXT, RSS
- Scheduler APScheduler (cron Docker pour V1)
- Transformation : Polars DataFrames, validation Patito
- Dédup par (symbol, timestamp, tf)

**Narration (30s)** : « Pipeline ETL orchestré par APScheduler, Polars pour la transfo, validation Patito. Robuste à 4 sources. »

---

## Slide 10 — Bloc 2 — Base de données (ER01)

- [Insérer diagramme ER01 schéma BDD]
- **TimescaleDB hypertable** `crypto_ohlcv` — compression 7j, rétention 2 ans
- Normalisation 3NF ([[rncp/bloc2-infrastructure/db-normalization-3nf]])
- Tables : `users`, `signals`, `crypto_ohlcv`, `news_articles`, `regulatory_documents`, `paper_trades`
- Index BRIN sur `timestamp`, B-tree sur `(symbol, tf)`

**Narration (30s)** : « Schéma 3NF, hypertable TimescaleDB pour OHLCV, compression après 7 jours pour tenir dans 160 GB. »

---

## Slide 11 — Bloc 2 — Moteur de règles

- Pondérations [[CryptoBot/avril/architecture/c06-phase2-ml-pipeline]] :
  - **RSI multi-TF** (1h/2h/3h/4h) — 25 %
  - **Bollinger Bands** (squeeze + band walking) — 20 %
  - **Harmonic patterns** (bat, gartley, butterfly, crab) — 15 %
  - **Trend lines** (weekly stable, monthly aggressive) — 20 %
  - **Volume + sentiment** (Fear & Greed) — 20 %
- Émission signal si `confidence ≥ 0,6`
- Vérification systématique marge 2x avant émission

**Narration (30s)** : « Moteur de règles pondérées, confidence minimale 0,6. Vérif marge 2x obligatoire. »

---

## Slide 12 — Bloc 2 — ML Phase 1

- [[rncp/bloc2-infrastructure/ml-justification-phase1]]
- **Blend XGBoost 60 % + LightGBM 40 %** sur features dérivées du rule engine
- Walk-forward backtesting avec **purging + embargo** (1 semaine)
- Labels : direction t+24h (BUY/SELL/HOLD), pas de prix absolu
- MLflow : tracking runs + feature importance + SHAP

**Narration (30s)** : « ML Phase 1 : blend XGBoost/LightGBM 60/40, walk-forward + purging. Jamais prédire le prix, toujours la direction. »

---

## Slide 13 — Bloc 3 — API FastAPI (C04)

- [Insérer C04 composants API]
- **8 routers** : auth, users, cryptos, signals, news, portfolio, paper-trades, alerts
- Pydantic v2 schemas request / response ([[CryptoBot/avril/architecture/cl03-api-schemas]])
- JWT Bearer auth, middleware rate-limiting (slowapi)
- OpenAPI 3.1 documenté, Swagger UI sur `/docs`

**Narration (30s)** : « FastAPI, 8 routers, auth JWT, rate limiting. OpenAPI 3.1 complet pour le jury. »

---

## Slide 14 — Bloc 3 — Conteneurs Docker (DP01)

- [Insérer DP01 deployment diagram — [[CryptoBot/avril/architecture/dp01-docker-infrastructure]]]
- **12 services** : timescaledb, minio, mlflow, api, frontend, etl-worker, nginx, certbot, prometheus, grafana, loki, redis
- Healthchecks sur tous, `restart: unless-stopped`
- Volumes nommés persistants, network bridge isolé
- Multi-stage builds Dockerfile, base `python:3.11-slim`, non-root user

**Narration (30s)** : « 12 services Docker Compose, healthchecks partout, non-root. Multi-stage pour image ~180 MB. »

---

## Slide 15 — Bloc 3 — CI/CD

- **GitHub Actions** (repo principal) : lint + type + test + build + scan Trivy
- **GitLab CI** (mirror école imposé) : même pipeline, Docker-in-Docker
- **Ansible** déploiement VPS : playbook `site.yml` -> pull image -> `docker compose up -d`
- [[rncp/bloc3-deploiement/cicd-evidence]] — captures pipelines verts

**Narration (30s)** : « Double CI GitHub + GitLab (école), déploiement Ansible idempotent. Pipelines 100 % verts avant merge. »

---

## Slide 16 — Bloc 3 — Sécurité

- **TLS 1.3** uniquement (Nginx), Let's Encrypt auto-renew
- Secrets : `.env` jamais commité, Ansible Vault en prod, rotation trimestrielle
- **RGPD** : cookies consent, droit oubli (`DELETE /users/me`), export data JSON
- bcrypt passwords (cost 12), JWT rotation 15 min + refresh 7 j
- Scan Trivy sur images, Bandit sur code
- Audit [[CryptoBot/avril/audit/technique/ci-cd-secrets]] + [[CryptoBot/avril/audit/technique/rate-limiting]]

**Narration (30s)** : « TLS 1.3, bcrypt, JWT court, secrets en Vault. RGPD conforme. Audit technique dédié. »

---

## Slide 17 — Bloc 3 — Tests

- **Pyramide** : 1200 tests unit + intégration + E2E
- Coverage **78 %** (gate CI : 80 % — légèrement en dessous, flagger comme dette)
- `pytest-asyncio` + `respx` pour mocks HTTP
- E2E : scenario signal generation → API → dashboard UI
- [[rncp/bloc3-deploiement/test-coverage-report]] — rapport détaillé

**Narration (30s)** : « 1200 tests, couverture 78 % (cible 80 %, écart documenté). Pyramide classique avec E2E critique. »

---

## Slide 18 — Bloc 4 — Pilotage

- **Sprints de 2 semaines** avec daily 15 min, sprint review + rétro le vendredi
- **Registre risques** [[CryptoBot/avril/planning/risks]] — 7 risques suivis, revus chaque vendredi
- **KPI projet** : vélocité, defects escape, coverage, uptime staging
- **ADRs** documentés dans [[CryptoBot/avril/history/decisions]]

**Narration (30s)** : « Pilotage agile strict : daily, rétro, risk review hebdo. 7 risques tracés, ADRs datés. »

---

## Slide 19 — Bloc 4 — Accompagnement (personas)

- **3 personas** [[_other/common/projects/MPP/architecture/UC01-personas]] :
  - **Noah** (25 ans, novice) — UI simplifiée, explications textuelles, disclaimers
  - **Alex** (35 ans, intermédiaire) — graphiques techniques, paper trading, alertes
  - **Sam** (45 ans, trader) — API raw, multi-timeframe, export CSV, webhook
- Chaque persona a un parcours validé en E2E

**Narration (30s)** : « Trois personas distincts, UI adaptée, parcours E2E. Noah voit moins, Sam voit tout. »

---

## Slide 20 — Bloc 4 — Veille

- **Tech radar** [[bloc4-pilotage/tech-radar]] : 4 quadrants (tools / platforms / languages / techniques)
- **Veille réglementaire** [[bloc4-pilotage/veille-reglementaire]] : MiCA UE, SEC US, ESMA
- Scraping automatisé ESMA + SEC (F1/F2) → table `regulatory_documents`
- Revue mensuelle tech + revue trimestrielle régul

**Narration (30s)** : « Veille structurée : tech radar 4 quadrants, scraping régul UE/US automatique, revues planifiées. »

---

## Slide 21 — Bloc 4 — Finances

- Total projet : **~45 000 € HT** (54 000 € HT avec buffer 20 %)
- Détail [[bloc4-finance/cost-analysis]] :
  - Humain 44 500 € (95 HJ × 2 devs + renfort)
  - Infra 224 € (VPS + domaine + GitHub)
  - Outils 195 € (LLM + Mailgun)
- **ROI vs SaaS** : break-even à 8 utilisateurs 2 ans
- Hypothèses flaggées pour validation Jules

**Narration (30s)** : « Budget 45 k€ HT dominé par l'humain. Infra sous 500 €. Break-even vs SaaS à 8 users 2 ans. »

---

## Slide 22 — DÉMO LIVE

- Transition : « Je laisse le slide de côté et lance la démo. »
- Cf. [[rncp/soutenance/demo-script]]
- Fallback : screenshots `infra/screenshots/` si panne live

**Narration** : passer directement à la démo, ne pas lire le slide.

---

## Slide 23 — Résultats obtenus

- ✅ **1200 tests** verts
- ✅ **Coverage 78 %** (cible 80 %, gap documenté)
- ✅ **22 diagrammes PlantUML** (source de vérité archi)
- ✅ **Audit interne B+** (cf. [[CryptoBot/avril/audit/audit-global]])
- ✅ **Staging déployé** sur VPS OVH, dashboard accessible
- ✅ **7 livrables RNCP** complets (Blocs 2/3/4 + soutenance)

**Narration (30s)** : « Résultats : 1200 tests, 22 diagrammes, audit B+, 7 livrables. Soutenance prête. »

---

## Slide 24 — Limites & gaps

- ❌ **LSTM Phase 2 non livré** — reporté Plan B-1 (DQN only envisagé, puis coupé)
- ❌ **RL non livré** — R1 matérialisé, Plan B-3 activé fin S15
- ⚠️ **Coverage 78 % < 80 %** — flaggé dette technique
- ⚠️ **Prod VPS SSH inaccessible** depuis lab école (NAT) — démo sur staging local
- ✅ **Contradictions résolues** — cf. [[_other/common/projects/SAP/meta/contradictions]] (14 items traités sur 14)

**Narration (30s)** : « Transparence : LSTM et RL non livrés, Plan B-3 activé. Coverage 78 % documenté. Contradictions toutes résolues. »

---

## Slide 25 — Retours d'expérience

- **Learning 1** : **PlantUML comme ground truth** — 22 diagrammes sources évitent les divergences code / docs.
- **Learning 2** : **Équipes isolées + `src/shared/`** — zéro conflit de merge en 6 sprints, grâce à la discipline team boundary.
- **Learning 3** : **MCP hex-line + Claude Code** — outillage agent qui a permis de produire 7 livrables RNCP en 2 semaines, via délégation à subagents spécialisés.

**Narration (30s)** : « Trois enseignements : PlantUML = vérité, équipes isolées = zéro conflit, MCP agents = productivité démultipliée. »

---

## Slide 26 — Évolutions Phase 2

- **Q3 2026** : Paper trading full stack (F7 reporté)
- **Q4 2026** : LSTM + XGBoost ensemble (F6 reporté)
- **Q1 2027** : RL agents DQN + PPO si convergence confirmée en lab (F8)
- **Q2 2027** : Alertes Telegram + SMTP en prod (F4 reporté)
- **Long terme** : v1 commerciale freemium (cf. [[bloc4-finance/cost-analysis]] §10.3)

**Narration (30s)** : « Roadmap post-école : paper trading Q3, LSTM Q4, RL si convergence. Commercial long terme si MRR atteint. »

---

## Slide 27 — Compétences démontrées (matrice RNCP)

| Compétence RNCP38919 | Livrable | Slide |
|----------------------|----------|------:|
| C1 Concevoir architecture | [[_other/common/projects/MPP/architecture/_canonical]] | 5-6 |
| C2 Modéliser données | [[CryptoBot/avril/architecture/er01-database-schema]] | 10 |
| C3 Développer API | [[rncp/bloc3-deploiement/api-contract-v1]] | 13 |
| C4 Déployer infra | [[rncp/bloc3-deploiement/container-images]] | 14-15 |
| C5 Sécuriser | [[rncp/bloc3-deploiement/rgpd-compliance]] | 16 |
| C6 Tester | [[rncp/bloc3-deploiement/test-coverage-report]] | 17 |
| C7 Piloter projet | [[CryptoBot/avril/planning/sprint-plan]] | 18 |
| C8 Accompagner utilisateurs | [[bloc4-pilotage/user-onboarding]] | 19 |
| C9 Faire de la veille | [[bloc4-pilotage/tech-radar]] | 20 |
| C10 Chiffrer projet | [[bloc4-finance/cost-analysis]] | 21 |

**Narration (30s)** : « Matrice compétences RNCP x livrables : chaque compétence est tracée vers un livrable du vault. »

---

## Slide 28 — Remerciements

- **Équipe enseignante** : [nom référent RNCP], [nom tuteur technique]
- **Équipe projet** : Jules (PO), Mikael (ML)
- **Outillage** : Anthropic Claude, OVH, TimescaleDB, MinIO, communauté Python
- **Famille / proches** — support moral des 6 sprints

**Narration (30s)** : « Merci au jury, à l'équipe enseignante, à Mikael, et à l'écosystème open source. »

---

## Slide 29 — Q&A — questions anticipées

- Q1 : « Pourquoi pas Kubernetes ? »  → Docker Compose suffit pour V1, K8s = overhead non justifié.
- Q2 : « Pourquoi Streamlit vs React ? »  → SSR natif, Plotly intégré, équipe 2 devs.
- Q3 : « Comment garantir la qualité des signaux ? » → Backtesting walk-forward + purging, confidence ≥ 0,6.
- Q4 : « Vous avez 78 % coverage au lieu de 80 %, pourquoi ? » → Gap sur edge cases UI, documenté en dette.
- Q5 : « Pourquoi pas de trade auto ? »  → Contrainte MiCA + éthique + pas de licence PSAN.
- Q6 : « Coût réel vs 45 k€ affichés ? » → Projet pédagogique, coût d'opportunité temps étudiant, infra personnelle.
- Q7 : « Phase 2 : comment financer ? » → [[bloc4-finance/cost-analysis]] §10 — grants + incubateur + love money.

---

## Slide 30 — Annexes & liens

- **Repo** : github.com/[org]/cryptobot
- **Vault Obsidian** : `_vault/common/projects/cryptobot/` — 94 pages
- **Diagrammes** : `docs/diagrams/` — 22 PlantUML
- **Livrables RNCP** : [[CryptoBot/avril/rncp/_index]]
- **Contact** : jules@[email] — mikael@[email]

**Narration (30s)** : « Tout est dans le vault Obsidian, 94 pages, 22 diagrammes, repo ouvert au jury. Merci. »

---

## Guide de narration

| Timing | Slide(s) | Durée cumul |
|--------|----------|------------|
| Ouverture | 1-4 | 2 min |
| Archi + stack | 5-8 | 2 min |
| Bloc 2 (data + ML) | 9-12 | 2 min |
| Bloc 3 (déploiement) | 13-17 | 2 min 30 |
| Bloc 4 (pilotage) | 18-21 | 2 min |
| Démo | 22 | 8 min (compte séparé) |
| Résultats + limites + REX | 23-26 | 2 min |
| Compétences + merci | 27-28 | 1 min |
| Q&A | 29 | 15 min |
| Annexes | 30 | 30 s |
| **TOTAL** | | **15 min + 8 min démo + 15 min Q&A = 38 min** |

> **Attention** : le brief indiquait 15 min présentation incluant démo, ou 15+15. Clarifier avec jury. Si démo dans les 15 min, couper slides 9-17 (Bloc 2 + 3 en 2 min au lieu de 4 min 30).

---

## Fichiers visuels requis

- `/docs/diagrams/C01-macro.svg` (slide 5)
- `/docs/diagrams/C02-etl-components.svg` (slide 9)
- `/docs/diagrams/AC01-etl-pipeline.svg` (slide 9)
- `/docs/diagrams/ER01-database-schema.svg` (slide 10)
- `/docs/diagrams/C04-api-components.svg` (slide 13)
- `/docs/diagrams/DP01-docker-infrastructure.svg` (slide 14)
- Extrait Gantt S11-S16 (slide 8) — générer depuis [[CryptoBot/avril/planning/gantt]]
- Captures dashboards Streamlit pour backup démo (slide 22)

---

*Fin de l'outline slides.*
