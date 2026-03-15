# Documentation CryptoBot

Source de verite : `Crypto_bot_cadrage_V2.pdf`
Conformite actuelle : 67% — voir `futur/analyse/01-conformite-cadrage.md`
Schemas interactifs : `SCHEMAS.HTML` (20 diagrammes Mermaid)

---

## Existant (67% implemente)

Documentation de ce qui est deja construit et fonctionne.

| # | Fichier | Contenu |
|---|---------|---------|
| 01 | [01-overview.md](existant/01-overview.md) | Vue d'ensemble projet |
| 02 | [02-data-engineering.md](existant/02-data-engineering.md) | ETL, collecteurs, TimescaleDB |
| 03 | [03-ml-data-science.md](existant/03-ml-data-science.md) | Rule engine, XGBoost, NLP |
| 04 | [04-backend-api.md](existant/04-backend-api.md) | FastAPI, endpoints, auth JWT |
| 05 | [05-frontend-ui.md](existant/05-frontend-ui.md) | Streamlit, Plotly, 5 pages |
| 06 | [06-devops-infra.md](existant/06-devops-infra.md) | Docker, Nginx, CI/CD |
| 07 | [07-glossaire.md](existant/07-glossaire.md) | Glossaire des termes |

---

## Futur (33% a developper)

### Analyse

| # | Fichier | Contenu |
|---|---------|---------|
| 01 | [01-conformite-cadrage.md](futur/analyse/01-conformite-cadrage.md) | Audit 67% vs cadrage PDF |
| 02 | [02-analysis-ml-gaps.md](futur/analyse/02-analysis-ml-gaps.md) | Gaps ML (RL, LSTM, clustering) |
| 03 | [03-data-sources-roadmap.md](futur/analyse/03-data-sources-roadmap.md) | Roadmap sources de donnees |
| 04 | [04-data-sources-summary.md](futur/analyse/04-data-sources-summary.md) | Resume sources |
| 05 | [05-observability-architecture.md](futur/analyse/05-observability-architecture.md) | Monitoring (Prometheus, Loki, traces) |

### Produit

| # | Fichier | Contenu |
|---|---------|---------|
| 01 | [01-PRD-phase2.md](futur/produit/01-PRD-phase2.md) | PRD 8 features (100/100 BMAD) |
| 02 | [02-paper-trading-alertes.md](futur/produit/02-paper-trading-alertes.md) | Specs paper trading + alertes |
| 03 | [03-data-sources-quickstart.md](futur/produit/03-data-sources-quickstart.md) | Guide rapide sources |

### Architecture

| # | Fichier | Contenu |
|---|---------|---------|
| 01 | [01-architecture-systeme.md](futur/architecture/01-architecture-systeme.md) | Architecture systeme (brouillon) |
| 02 | [02-architecture-ml-pipelines.md](futur/architecture/02-architecture-ml-pipelines.md) | Pipelines ML RL/LSTM/clustering |
| 03 | [03-architecture-scraping.md](futur/architecture/03-architecture-scraping.md) | Architecture scraping BS4 |
| 04 | [04-ADRs-phase2.md](futur/architecture/04-ADRs-phase2.md) | Decisions architecturales |
| 05 | [05-architecture-bmad-validated.md](futur/architecture/05-architecture-bmad-validated.md) | Architecture BMAD Gate 2 |

### UX

| # | Fichier | Contenu |
|---|---------|---------|
| 01 | [01-ux-design.md](futur/ux/01-ux-design.md) | Wireframes par persona |

### Planning

| # | Fichier | Contenu |
|---|---------|---------|
| 01 | [01-roadmap.md](futur/planning/01-roadmap.md) | Planning global |
| 02 | [02-sprint-plan.md](futur/planning/02-sprint-plan.md) | Plan de sprints |
| 03 | [03-sprint-gantt.md](futur/planning/03-sprint-gantt.md) | Gantt et suivi |
| 04 | [04-risk-mitigation.md](futur/planning/04-risk-mitigation.md) | Risques et mitigations |
| 05 | [05-sprint-summary.md](futur/planning/05-sprint-summary.md) | Resume sprints |
| 06 | [06-backlog.csv](futur/planning/06-backlog.csv) | Backlog CSV |
| 07 | [07-README-sprint.md](futur/planning/07-README-sprint.md) | Guide sprint |
| 08 | [08-implementation-checklist.md](futur/planning/08-implementation-checklist.md) | Checklist implementation |

---

## Audit QA

| Dossier | Contenu |
|---------|---------|
| [audit/audit.md](audit/audit.md) | Rapport principal |
| [audit/CDC.md](audit/CDC.md) | Cahier des charges initial |
| [audit/SPECIFICATIONS_FONCTIONNELLES.md](audit/SPECIFICATIONS_FONCTIONNELLES.md) | Specs fonctionnelles |
| [audit/specs-domaine/](audit/specs-domaine/) | Specs ML, frontend, infra |
| [audit/architecture/](audit/architecture/) | Architecture applicative et data |
| [audit/sujets-techniques/](audit/sujets-techniques/) | DB, env vars, rate limiting, CI/CD |
| [audit/remediation/](audit/remediation/) | Remediation phases 1-3 |

---

## Fichiers speciaux

| Fichier | Description |
|---------|-------------|
| [SCHEMAS.HTML](SCHEMAS.HTML) | 20 diagrammes Mermaid interactifs (existant + futur) |
| [bmm-workflow-status.yaml](bmm-workflow-status.yaml) | Statut workflow BMAD |
| [../Crypto_bot_cadrage_V2.pdf](../Crypto_bot_cadrage_V2.pdf) | Cadrage PDF (source de verite) |
