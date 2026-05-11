---
type: rncp-competences-bloc
bloc: B4
source: rncp-agent-supervisor
tags: [cryptobot, rncp, competences, bloc4]
created: 2026-04-14
---

# Bloc B4 — Piloter un projet d'architecture technique de gestion de données

6 compétences. Chaque compétence liste les **livrables de preuve**, les **artefacts projet**, et une **phrase de justification**.

---

## C4.1 — Définir la structure organisationnelle du projet

**Preuves** :
- `[[00-overview]]` — vision 5 équipes et frontières
- `[[01-data-engineering]]` + `[[02-ml-data-science]]` + `[[03-backend-api]]` + `[[04-frontend-ui]]` + `[[05-devops-infra]]` — chartes par équipe
- `[[CLAUDE]]` (CLAUDE.md) — règles de scoping, interdits cross-code

**Justification** : 5 équipes formalisées avec scopes exclusifs (`src/etl`, `src/ml`, `src/api`, `src/frontend`, `infra/`), communication via `src/shared/` uniquement. Orchestrator transverse pour cross-team. Règle absolue : interdiction de modifier le code d'une autre équipe.

---

## C4.2 — Encadrer le développement du projet d'architecture de données

**Preuves** :
- `[[retrospectives]]` — retros Sprint S11 (12/16 pts, 75%) et S12 (18/16 pts, 112%), + squelettes S13-S16
- `[[sprint-plan]]` — 6 sprints, 62 story points, vélocité cible 16 pts/sprint
- `[[change-management]]` — CR template + matrice impact + 3 niveaux d'approbation
- `[[backlog]]`, `[[gantt]]`, `[[risks]]` (10 risques tracés avec sévérité)

**Justification** : encadrement Agile Scrum avec cadence sprint (2 semaines), daily via tmux multi-agent, rétros end-of-sprint, planning poker, Go/No-Go checklist. Traçabilité totale : chaque ticket Linear → commit → ADR si structurant.

---

## C4.3 — Gérer le budget du projet

**Preuves** :
- `[[cost-analysis]]` (livrable 5) — 386 lignes, budget total ~65 116 € TTC
- Méthode : capacité humaine (44 k€) + infra (370 €) + outils (150 €) + équipement (300 €) + buffer 20%

**Justification** : budget détaillé en 11 sections — méthode de chiffrage, capacité humaine (Jules + Mikael + renfort DevOps), infrastructure récurrente (OVH VPS, domaine, Cloudflare), outils & services (APIs LLM), coûts académiques, comparatif SaaS (ROI vs TradingView+CoinGlass+Santiment = 2 820 €/an), scénarios MVP/Phase2/V1 commerciale, hypothèses & risques, plan de financement. 14 hypothèses flaggées pour validation avec PO.

---

## C4.4 — Communiquer l'avancement et les résultats du projet

**Preuves** :
- `[[kpi-performance]]` — vélocité, predictability, cycle time, burn-down (Mermaid)
- `[[retrospectives]]` — synthèse par sprint + actions
- `[[sprint-summary]]` — 16 pts/sprint, capacité 20-25h/pers
- `[[soutenance/slides-outline]]` — 30 slides soutenance jury
- `[[soutenance/demo-script]]` — démo live 8 min

**Justification** : communication multi-canaux : revue hebdo avec Jules, snapshot mensuel dans `sprint-summary`, Slack `#cryptobot-weekly`, dashboards Grafana "Project Health", et soutenance orale avec slides + démo. Traçabilité : chaque KPI renvoie à sa source de mesure.

---

## C4.5 — Évaluer la performance du projet

**Preuves** :
- `[[kpi-performance]]` — 5 catégories KPI (Agilité, Produit, Qualité, DORA adapté, Infra)
- `[[audit-global]]` — audit B+ avec 38 findings (8 CRITICAL, 12 HIGH, 18 MEDIUM)
- `[[phase3]]` (audit/remediation/phase3) — 1200 tests verts, 0 failures, couverture ≈ 81.5%
- `[[decisions]]` — ADR-010 arbitrage Phase 2 périmètre

**Justification** : évaluation quantitative (KPI, tests, couverture, findings audit) + qualitative (rétros, change requests closed). Cycle d'amélioration continue : audit → remédiation phase 1/2/3 → re-audit. Exemple concret : 38 findings → 0 après 3 phases.

---

## C4.6 — Former les utilisateurs finaux de la solution

**Preuves** :
- `[[user-onboarding]]` — runbooks par persona Noah / Sarah / Aleksandar + format formation (vidéos 3-5 min + livret PDF + Q&A live)
- `[[faq-utilisateurs]]` — ~20 Q/R sur compte, signaux, news, performance, sécurité, facturation, roadmap
- `[[uc01-personas]]` — 3 personas et cas d'usage
- `[[sq01-auth-jwt-flow]]` — diagramme flux auth pour onboarding

**Justification** : plan d'accompagnement par persona (parcours différencié selon niveau : débutant Aleksandar avec mode "simple" + explications, expert Noah avec dashboard avancé, journaliste Sarah avec flux news). Mesure succès : taux d'activation 7j (cible 60%), NPS post-formation (cible ≥40), tickets support (cible ≤10/semaine phase ramp-up). Handoff support SLA 48h.

---

## Matrice compétences × livrables RNCP

| Compétence | L2 | L3 | L4 | L5 | Soutenance |
|------------|----|----|----|----|-----------:|
| C4.1 Structure | — | — | ✅ | — | ✅ |
| C4.2 Encadrer | — | — | ✅ | — | ✅ |
| C4.3 Budget | — | — | — | ✅ | ✅ |
| C4.4 Communiquer | — | — | ✅ | — | ✅ |
| C4.5 Évaluer | — | ✅ | ✅ | — | ✅ |
| C4.6 Former | — | — | ✅ | — | ✅ |
