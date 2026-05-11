---
type: rncp-competences-bloc
bloc: B2
source: rncp-agent-supervisor
tags: [cryptobot, rncp, competences, bloc2]
created: 2026-04-14
---

# Bloc B2 — Concevoir un projet d'architecture technique de gestion de données

6 compétences. Chaque compétence liste les **livrables de preuve** (wikilinks), les **artefacts code/doc**, et une **phrase de justification** pour le jury.

---

## C2.1 — Identifier les besoins en architecture de gestion de données

**Preuves** :
- `[[cdc]]` — cahier des charges initial (vault `audit/cdc.md`)
- `[[specs-fonctionnelles]]` — RF-ETL-001 → RF-ML-007 avec critères d'acceptation
- `[[uc01-personas]]` — 3 personas (Noah trader, Sarah journaliste, Aleksandar novice), 13 cas d'usage
- `[[PRD-phase2]]` — 8 features P0-P2 Phase 2

**Justification** : les besoins métier sont formalisés en amont via CDC, specs fonctionnelles et personas. Les besoins techniques (volume : 13 symboles × 9 TF × 1min → ~117 k records/jour ; latence ingestion < 5 min ; rétention 90 j) dérivent des personas et sont cristallisés dans l'architecture macro `[[c01-macro]]`.

---

## C2.2 — Élaborer et exercer un système de veille technologique et réglementaire

**Preuves** :
- `[[tech-radar]]` — 46 technos mappées sur 4 anneaux (Adopt 16 / Trial 12 / Assess 11 / Hold 7)
- `[[veille-reglementaire]]` — RGPD, MiCA, DORA, MiFID II, AMF, CNIL, LCEN
- `[[data-sources-roadmap]]` — veille sources (ESMA, AMF, SEC RSS)

**Justification** : un radar Thoughtworks-style est tenu + une veille réglementaire dédiée crypto (MiCA 2023/1114, RGPD). Sources RSS ingérées via pipeline ETL, revue trimestrielle formalisée.

---

## C2.3 — Exploiter la veille au sein de son organisation

**Preuves** :
- `[[adrs-phase2]]` — ADRs déclenchés par veille (choix TimescaleDB, MinIO, MLflow, Polars sur pandas)
- `[[themes]]` — synthèse trimestrielle des thèmes issus de la veille
- `[[decisions]]` — 10 ADR datés avec contexte/décision/conséquences

**Justification** : la veille n'est pas un rapport mort — elle alimente directement les ADR (ex. Promtail EOL mars 2026 → bascule Vector.dev actée en S13). Circuit : alerte veille → analyse impact 48h → CR si action → ADR si décision structurante.

---

## C2.4 — Définir le périmètre du projet de gestion données

**Preuves** :
- `[[ml-phase2-scope-revise]]` — arbitrage Phase 2 livrée (Rules+XGBoost+LightGBM) vs roadmap (LSTM+RL+K-means)
- `[[roadmap]]` — 6 sprints S11-S16, 8 epics, 62 story points
- `[[PRD-phase2]]` — features P0 (bloquantes soutenance) vs P1/P2 (roadmap)
- `[[sprint-plan]]` — découpage capacité / vélocité

**Justification** : le périmètre est explicitement borné par ADR (ADR-010 périmètre Phase 2 soutenance), avec contradictions résolues dans `[[contradictions]]`. Éviter l'effet tunnel : scope livré = testé, scope roadmap = documenté.

---

## C2.5 — Émettre des recommandations auprès de sa hiérarchie et de membres d'une équipe pluridisciplinaire

**Preuves** :
- `[[change-management]]` — 3 niveaux d'approbation (CR interne / cross-team / archi), template CR, matrice impact 5×5
- `[[decisions]]` — 10 ADR en français tracés avec références observations (obs-id)
- `[[00-overview]]` — 5 équipes + matrices de responsabilités + règle "jamais cross-code"
- `[[sprint-plan]]` — recommandations per sprint (dépendances, risques)

**Justification** : les recommandations suivent un circuit formel (issue Linear `change-request` → revue → décision commentée → ADR). Pluridisciplinarité : 5 équipes (Data Eng, ML, Backend, Frontend, DevOps) + PO (Jules) — communication via `src/shared/` uniquement.

---

## C2.6 — Élaborer une architecture technique de gestion de données

**Preuves** :
- **22 PlantUML** `[[_canonical]]` — ground truth absolue (C01 macro, C02-C07 composants, CL01-CL05 classes, ER01 schéma, AC01-AC02 activité, SQ01-SQ04 séquence, ST01 états, DP01 déploiement, UC01 cas d'usage)
- `[[db-normalization-3nf]]` — analyse 3NF des 9 tables + justif dénormalisation hypertable
- `[[db-ddl-init]]` — script DDL PostgreSQL + TimescaleDB exécutable
- `[[dp01-docker-infrastructure]]` — 12 services, 2 réseaux, 4 volumes, ~5.8 GB RAM

**Justification** : architecture en couches (collecte → transformation → stockage → analyse → API → UI), justifiée par 22 PlantUML canoniques servant de contrat. Choix structurants : TimescaleDB (hypertable, compression 7j, rétention 90j), MinIO (S3-compatible artifacts), MLflow (tracking + registry), Docker Compose (pas K8s pour V1).

---

## Matrice compétences × livrables RNCP

| Compétence | L2 | L3 | L4 | L5 | Soutenance |
|------------|----|----|----|----|-----------:|
| C2.1 Besoins | ✅ | — | ✅ | — | ✅ |
| C2.2 Veille | — | — | ✅ | — | ✅ |
| C2.3 Exploiter veille | — | — | ✅ | — | ✅ |
| C2.4 Périmètre | ✅ | — | ✅ | — | ✅ |
| C2.5 Recommandations | — | — | ✅ | — | ✅ |
| C2.6 Architecture | ✅ | ✅ | — | — | ✅ |
