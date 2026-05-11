---
type: rncp-competences-matrix
source: rncp-agent-supervisor
tags: [cryptobot, rncp, competences, matrix]
created: 2026-04-14
---

# RNCP38919 — Matrice Compétences × Livrables

Cette matrice cartographie **chaque compétence officielle du référentiel RNCP38919** vers les livrables et artefacts qui la prouvent. Elle est l'entrée unique côté jury pour vérifier la couverture.

> Les compétences sont regroupées par bloc (B2, B3, B4). Détail dans les fichiers dédiés : `[[B2-concevoir]]`, `[[B3-deployer]]`, `[[B4-piloter]]`.

## Synthèse — 25 compétences, 24 livrables

| Bloc | Compétences | Statut global |
|------|-------------|---------------|
| B2 — Concevoir architecture | 6 | 🟢 couvertes |
| B3 — Déployer solution IA | 13 | 🟢 couvertes (LSTM/RL roadmap) |
| B4 — Piloter projet | 6 | 🟢 couvertes |

## Vue condensée

| Code | Compétence | Livrable(s) preuve |
|------|------------|--------------------|
| **B2** | **Concevoir un projet d'architecture technique de gestion de données** | |
| C2.1 | Identifier besoins architecture | `[[cdc]]`, `[[specs-fonctionnelles]]`, `[[uc01-personas]]` |
| C2.2 | Élaborer veille techno/réglementaire | `[[tech-radar]]`, `[[veille-reglementaire]]` |
| C2.3 | Exploiter la veille | `[[adrs-phase2]]`, `[[themes]]`, `[[decisions]]` |
| C2.4 | Définir périmètre projet | `[[ml-phase2-scope-revise]]`, `[[roadmap]]`, `[[PRD-phase2]]` |
| C2.5 | Émettre recommandations | `[[change-management]]`, `[[decisions]]` (ADR) |
| C2.6 | Élaborer architecture technique | 22 PlantUML `[[_canonical]]` + `[[db-normalization-3nf]]` |
| **B3** | **Déployer une solution d'analyse de données massives intégrant l'IA** | |
| C3.1 | Collecter données structurées/non structurées | `[[etl-execution-report]]`, `[[etl]]` |
| C3.2 | Élaborer solutions de stockage | `[[db-normalization-3nf]]`, `[[db-ddl-init]]`, `[[er01-database-schema]]` |
| C3.3 | Concevoir procédures extraction/traitement/stockage | `[[etl-execution-report]]`, `[[ac01-etl-pipeline]]` |
| C3.4 | Transformer données pour analyse | `[[etl-data-quality]]`, `[[etl]]` (transformers) |
| C3.5 | Analyser les données | `[[ml-justification-phase1]]`, `[[cl04-ml-rules-models]]` |
| C3.6 | Automatiser collecte/traitement/stockage | `[[etl-execution-report]]` §orchestration APScheduler |
| C3.7 | Développer algorithme IA | `[[ml-justification-phase1]]`, `[[ml-phase2-scope-revise]]` |
| C3.8 | Concevoir API entre composants | `[[api-contract-v1]]`, `[[api-openapi]]` |
| C3.9 | Conteneuriser composants | `[[container-images]]`, `[[dp01-docker-infrastructure]]` |
| C3.10 | Déployer le modèle en production | `[[cicd-evidence]]`, `[[prod-run-evidence]]`, `deploy.yml` |
| C3.11 | Orchestrer services | `docker-compose.yml`, `infra/ansible/README`, `[[dp01-docker-infrastructure]]` |
| C3.12 | Contrôler mise en production | `[[test-coverage-report]]`, `[[prod-run-evidence]]`, healthchecks |
| C3.13 | Automatiser déploiement + monitoring | `.github/workflows/deploy.yml`, `.gitlab-ci.yml`, Grafana+Prometheus+Loki |
| **B4** | **Piloter un projet d'architecture technique de gestion de données** | |
| C4.1 | Définir structure organisationnelle | `[[00-overview]]`, `[[01-data-engineering]]`…`[[05-devops-infra]]` |
| C4.2 | Encadrer développement | `[[retrospectives]]`, `[[sprint-plan]]`, `[[change-management]]` |
| C4.3 | Gérer budget projet | `[[cost-analysis]]` (L5) |
| C4.4 | Communiquer avancement et résultats | `[[kpi-performance]]`, `[[retrospectives]]`, `[[sprint-summary]]` |
| C4.5 | Évaluer performance projet | `[[kpi-performance]]`, `[[audit-global]]`, `[[phase3]]` |
| C4.6 | Former utilisateurs finaux | `[[user-onboarding]]`, `[[faq-utilisateurs]]` |

## Navigation par bloc

- **B2** — `[[B2-concevoir]]` — identification besoins + veille + périmètre + recommandations + architecture
- **B3** — `[[B3-deployer]]` — collecte + stockage + ETL + analyse + IA + API + conteneurs + déploiement + CI/CD
- **B4** — `[[B4-piloter]]` — structure + encadrement + budget + communication + évaluation + formation

## Mapping Livrables RNCP officiels → compétences

| Livrable officiel | Compétences prouvées | Dossier |
|-------------------|----------------------|---------|
| **Livrable 2** (B2+B3) : ETL, BDD, modélisation, algos IA | C2.6 + C3.1-7 | `livrables/L2-infrastructure/` |
| **Livrable 3** (B3) : API, conteneurs, CI/CD, tests, solution configurée | C3.8-13 | `livrables/L3-deploiement/` |
| **Livrable 4** (B4) : rapport mise en œuvre + plan accompagnement | C2.2-5 + C4.1,2,4,5,6 | `livrables/L4-pilotage/` |
| **Livrable 5** (B4) : analyse financière | C4.3 | `livrables/L5-finance/` |
| **Soutenance orale** | transverse | `livrables/soutenance/` |
