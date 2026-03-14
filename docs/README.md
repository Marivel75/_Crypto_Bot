# Documentation CryptoBot

## Equipes
Documentation par equipe — a lire en premier.

| Fichier | Contenu |
|---------|---------|
| [00-overview.md](equipes/00-overview.md) | Vue d'ensemble projet (TOUTES equipes) |
| [01-data-engineering.md](equipes/01-data-engineering.md) | ETL, collecteurs, TimescaleDB, MinIO |
| [02-ml-data-science.md](equipes/02-ml-data-science.md) | Rule engine, ML, backtesting, NLP |
| [03-backend-api.md](equipes/03-backend-api.md) | FastAPI, endpoints, auth, services |
| [04-frontend-ui.md](equipes/04-frontend-ui.md) | Streamlit, pages, composants, Plotly |
| [05-devops-infra.md](equipes/05-devops-infra.md) | Docker, Nginx, Ansible, CI/CD |

## Specifications Phase 2 (33% restants)
Tout ce qu'il faut pour developper les 8 features manquantes.

### Cahier des charges
| Fichier | Contenu | Statut |
|---------|---------|--------|
| [PRD-phase2.md](specs/PRD-phase2.md) | **PRD complet 8 features** (100/100) — 17 user stories, criteres d'acceptation | VALIDE |

### Architecture
| Fichier | Contenu | Statut |
|---------|---------|--------|
| [architecture-systeme.md](specs/architecture-systeme.md) | Architecture systeme (DB, API, services Docker) | BROUILLON |
| [architecture-ml-pipelines.md](specs/architecture-ml-pipelines.md) | Architecture ML (RL, LSTM, clustering) | BROUILLON |
| [architecture-scraping.md](specs/architecture-scraping.md) | Architecture scraping BeautifulSoup | BROUILLON |
| [ADRs-phase2.md](specs/ADRs-phase2.md) | Decisions architecturales Phase 2 | BROUILLON |

### Specs par feature
| Fichier | Contenu | Features |
|---------|---------|----------|
| [paper-trading-alertes.md](specs/paper-trading-alertes.md) | Paper trading + alertes (schemas, endpoints, frontend) | F1, F6 |
| [analysis-ml-gaps.md](specs/analysis-ml-gaps.md) | Analyse ML (RL, LSTM, clustering) | F2, F3, F4 |
| [ux-design-nouvelles-features.md](specs/ux-design-nouvelles-features.md) | Wireframes et UX par persona | F1-F8 |
| [data-sources-roadmap.md](specs/data-sources-roadmap.md) | Roadmap sources de donnees | F5, F7, F8 |
| [data-sources-summary.md](specs/data-sources-summary.md) | Resume sources de donnees | F5, F7, F8 |
| [data-sources-quickstart.md](specs/data-sources-quickstart.md) | Guide rapide integration sources | F5, F7, F8 |
| [implementation-checklist.md](specs/implementation-checklist.md) | Checklist d'implementation | F1-F8 |

## Planning
Roadmap, sprints et suivi.

| Fichier | Contenu |
|---------|---------|
| [06-roadmap.md](planning/06-roadmap.md) | Planning global et sprints |
| [06-sprint-plan.md](planning/06-sprint-plan.md) | Plan de sprints detaille |
| [06a-sprint-gantt-tracking.md](planning/06a-sprint-gantt-tracking.md) | Gantt et suivi |
| [06b-risk-mitigation.md](planning/06b-risk-mitigation.md) | Risques et mitigations |
| [06c-sprint-summary.md](planning/06c-sprint-summary.md) | Resume sprints |

## Audit
Documentation d'audit qualite (Vague 1-3).

| Dossier | Contenu |
|---------|---------|
| [audit.md](audit/audit.md) | Rapport d'audit principal |
| [CDC.md](audit/CDC.md) | Cahier des charges initial |
| [SPECIFICATIONS_FONCTIONNELLES.md](audit/SPECIFICATIONS_FONCTIONNELLES.md) | Specs fonctionnelles |
| [vague.md](audit/vague.md) | Suivi des vagues QA |
| [specs-domaine/](audit/specs-domaine/) | Specs par domaine (ML, frontend, infra) |
| [architecture/](audit/architecture/) | Architecture applicative et data |
| [sujets-techniques/](audit/sujets-techniques/) | DB migrations, env vars, rate limiting, CI/CD |
| [remediation/](audit/remediation/) | Plans de remediation (phases 1-3) |

## Reference
| Fichier | Contenu |
|---------|---------|
| [glossaire.md](glossaire.md) | Glossaire des termes |
| [../SCHEMAS.HTML](../SCHEMAS.HTML) | Diagrammes Mermaid interactifs (10 schemas) |
| [../Crypto_bot_cadrage_V2.pdf](../Crypto_bot_cadrage_V2.pdf) | Cadrage PDF original |
