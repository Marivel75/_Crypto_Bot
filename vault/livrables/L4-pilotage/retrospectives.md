---
type: rncp-bloc4
bloc: 4
competence: pilotage
source: agent-L4-Governance
tags:
  - cryptobot
  - rncp
  - bloc4
  - pilotage
  - retrospective
  - scrum
created: 2026-04-14
ingested_by: agent-L4-Governance
related:
  - "[[CryptoBot/avril/planning/sprint-plan]]"
  - "[[CryptoBot/avril/planning/sprint-summary]]"
  - "[[CryptoBot/avril/planning/risks]]"
  - "[[rncp/bloc4-pilotage/change-management]]"
  - "[[rncp/bloc4-pilotage/kpi-performance]]"
---

# Rétrospectives — CryptoBot S11-S16

RNCP38919 Bloc 4 — Piloter un projet informatique.

## 1. Rôle des rétrospectives

La rétrospective est le moment Scrum de **clôture réflexive** du sprint. Elle n'est pas une réunion d'audit ni de blâme : c'est l'instrument de la **boucle d'amélioration continue** (Kaizen) qui transforme l'expérience vécue en règles de fonctionnement pour le sprint suivant.

**Cadence** — fin de chaque sprint, vendredi 17:00 (après sprint review 16:00 et risk review 16:30 — cf. [[CryptoBot/avril/planning/sprint-plan]]), **durée 45 min** (équipe 2 pers. → timeboxing court justifié).

**Facilitateur rotatif** — Jules sur S11, S13, S15 ; Mikael sur S12, S14, S16. Le facilitateur **ne participe pas** au fond, il garantit le timebox, distribue la parole et consigne les actions.

**Output obligatoire** — 1 fichier `retro-S{n}.md` par sprint dans ce document, avec :
- `Start / Stop / Continue` (format court, lisible en 2 min)
- **Actions SMART** (Specific, Measurable, Achievable, Relevant, Time-bound) avec owner et échéance
- Report dans la rétro suivante de l'état des actions précédentes

**Lien amont/aval** — les actions ouvertes alimentent le tableau `§7 Action items` (SSOT). Les thèmes récurrents remontent dans la `§6 Synthèse transversale` et deviennent input pour les revues mensuelles de [[CryptoBot/avril/rncp/livrables/L4-pilotage/change-management]].

## 2. Template rétro

```markdown
## Retro Sprint S{n} — {date début} → {date fin}

**Facilitateur** : {Jules | Mikael}
**Participants** : Jules, Mikael
**Delivered** : {pts livrés} / {pts cibles} ({%})

### Start (ce qu'on veut commencer)
- ...

### Stop (ce qu'on veut arrêter)
- ...

### Continue (ce qui marche et qu'on garde)
- ...

### Actions SMART
| # | Action | Owner | Échéance | Mesure de succès |
|---|--------|-------|----------|------------------|
| A-S{n}-01 | ... | ... | ... | ... |
```

Une action **SMART** passe le test : *« Est-ce qu'un observateur extérieur saurait dire, à la date X, si l'action est faite ? »*. Si la réponse est non, l'action est reformulée.

## 3. Retro Sprint S11 — 14-28 mars 2026 (RÉEL)

**Facilitateur** : Jules
**Participants** : Jules, Mikael
**Delivered** : **12 pts** / 16 cibles (**75%**)

**Diagnostic sous-livraison** : onboarding Claude Code + mise en place du workflow multi-agent (tmux + claude-mem + hex-line) a consommé ~5h imprévues côté Jules la première semaine. La feature F3 (K-Means, owner Mikael) a été livrée à 100% (3 pts) ; F1 a été livrée à 100% (3 pts) ; F2 livrée à 100% (2 pts) ; le reliquat concerne 4 pts de scaffolding partagé (ADRs, structure vault, diagrammes) qui n'étaient pas formellement dans le backlog S11 mais ont été exécutés hors-sprint.

### Start
- **Formaliser les ADRs** dans `[[history/decisions]]` (ADR-01 à ADR-05 ont émergé rétroactivement — les décisions n'étaient pas tracées au moment de la prise)
- **Daily tmux debug** 10 min le matin avant daily standup — vérification que les 10 sessions tmux sont up (incident WezTerm/sap-supervisor d'avril a montré la fragilité)

### Stop
- **Grep brute-force** sur les fichiers du vault — Jules a consommé >3k tokens en `grep` récursif avant l'introduction de hex-line. Décision : hex-line `grep_search` + `inspect_path` obligatoires pour l'exploration vault.
- **Lire des fichiers entiers** quand on cherche un symbole — `get_file_outline` d'abord.

### Continue
- **TDD sur les rules Phase 1** — Mikael a écrit les tests K-Means avant le code, coverage 92% sur F3. À généraliser.
- **Wikilinks Obsidian** systématiques dans le vault — facilite la navigation inter-équipes.

### Actions SMART
| # | Action | Owner | Échéance | Mesure de succès |
|---|--------|-------|----------|------------------|
| A-S11-01 | Introduire hex-line dans `~/.claude/hex-skills/` + hook bloquant sur grep/find/cat en mémoire projet | Jules | S12-w1 | Hook actif, `rtk gain` montre ≥50% économie tokens sur ops fichier |
| A-S11-02 | Créer `agents/observations/` timeline (claude-mem ingestion) | Jules | S12-w1 | Fichier `observations-summary.md` généré, >=50 obs indexées |
| A-S11-03 | Extraire les 5 premiers ADR depuis claude-mem | Jules | S12-w2 | `history/decisions.md` contient ADR-01 à ADR-05 |
| A-S11-04 | Backfill coverage tests F1 (scraping ESMA) | Jules | S12-w1 | Coverage `src/etl/scrapers/esma.py` ≥ 80% |

## 4. Retro Sprint S12 — 29 mars - 12 avril 2026 (RÉEL)

**Facilitateur** : Mikael
**Participants** : Jules, Mikael
**Delivered** : **18 pts** / 16 cibles (**+12%**, 112%)

**Diagnostic sur-livraison** : effet de rattrapage S11 (scaffolding terminé en S12-w1) + productivité accrue grâce aux worktrees git par agent (plus de conflits de branche) + les 22 diagrammes PlantUML ont été produits en 3 jours grâce au workflow dédié (plantweb local + Makefile).

### Start
- **Worktree par agent** — `git worktree add` isolé par feature branch, un agent Claude Code par worktree. Permet parallélisme F4/F5 sans interférence.
- **Validation cross-équipe via `src/shared/`** — toute modification de Pydantic model commune déclenche revue par l'autre lead.

### Stop
- **Modifier du code hors frontière d'équipe** — Mikael a patché `src/etl/scrapers/rss.py` pour corriger un typage Pydantic : viole la règle CLAUDE.md. Correctif : issuer un CR niveau 2 (cf. [[CryptoBot/avril/rncp/livrables/L4-pilotage/change-management]]) à la place.
- **Commits de fin de journée non-atomiques** — 3 commits S12 ont mélangé refactor + feature + tests. Décision : `git add -p` obligatoire.

### Continue
- **22 diagrammes PlantUML** comme ground truth d'architecture (ADR-03) — à maintenir à chaque change de schéma ou d'interface partagée.
- **Daily standup 15 min** avec yesterday/today/blockers — efficace, pas de dérive vers 30 min.

### Actions SMART
| # | Action | Owner | Échéance | Mesure de succès |
|---|--------|-------|----------|------------------|
| A-S12-01 | Workflow `ln-*` dédié (Linear → Story → Tasks) | Jules | S13-w1 | Story CRY-5 (F6 LSTM) créée via `/ln-220-story-coordinator`, 5-10 tasks générées |
| A-S12-02 | Installer agent-mail MCP pour notifications cross-team | Jules | S13-w1 | `mcp__agent-mail__health_check` retourne OK, 1 message test envoyé Jules→Mikael |
| A-S12-03 | Introduire règle `git add -p` dans `.claude/rules/common.md` | Mikael | S13-w1 | Règle présente, rappelée en daily S13-D1 |
| A-S12-04 | CR niveau 2 obligatoire pour toute modif cross-team | Jules + Mikael | S13-w1 | Template CR disponible dans [[CryptoBot/avril/rncp/livrables/L4-pilotage/change-management]] |

## 5. Retros Sprint S13-S16 — squelettes (à remplir fin de sprint)

### 5.1. Retro Sprint S13 — 13-27 avril 2026

**Facilitateur** : Jules
**Delivered** : `[À REMPLIR fin sprint]` / 15 pts cibles
**Features planifiées** : F6 LSTM (5 pts), F7.1 Paper Trading modèle (5 pts), F7.2 Paper Trading API (5 pts) — cf. [[CryptoBot/avril/planning/sprint-plan]]

**Points d'attention anticipés** (à challenger en retro) :
- Surcharge Mikael 35h > capacité 25h — split LSTM S13-S14 tenu ?
- Freeze schema F7.2 S13-w1 tenu ? (mitigation R4)
- Pair programming F7 activé ? (mitigation R2)

```markdown
### Start
[À REMPLIR fin sprint]

### Stop
[À REMPLIR fin sprint]

### Continue
[À REMPLIR fin sprint]

### Actions SMART
| # | Action | Owner | Échéance | Mesure |
|---|--------|-------|----------|--------|
| A-S13-01 | [À REMPLIR] | | | |
```

### 5.2. Retro Sprint S14 — 28 avril - 12 mai 2026

**Facilitateur** : Mikael
**Delivered** : `[À REMPLIR fin sprint]` / 16 pts cibles
**Features planifiées** : F7.3 Paper Trading frontend (3 pts), F6 LSTM tuning final (split), Intégration E2E (8 pts)

**Points d'attention anticipés** :
- Load test (100 req/s) exécuté avant fin S14 ? (mitigation R6)
- E2E staging OK avant S15 ? (mitigation R2)
- Coverage globale ≥ 78% (cf. [[CryptoBot/avril/rncp/livrables/L4-pilotage/kpi-performance]]) ?

```markdown
### Start / Stop / Continue / Actions SMART
[À REMPLIR fin sprint]
```

### 5.3. Retro Sprint S15 — 13-27 mai 2026 (critique)

**Facilitateur** : Jules
**Delivered** : `[À REMPLIR fin sprint]` / 18 pts cibles
**Features planifiées** : F8 RL env (5 pts), DQN agent (5 pts), PPO agent (5 pts), Training parallèle (3 pts)

**Points d'attention anticipés (critical)** :
- Convergence DQN atteinte S15-mid ? Sinon **Plan B-1b** (DQN only) déclenché ?
- Escalation quotidienne sur R1 (RL convergence) — daily check loss curve
- Baseline random agent en place ? (mitigation R1)

```markdown
### Start / Stop / Continue / Actions SMART
[À REMPLIR fin sprint]
```

### 5.4. Retro Sprint S16 — 28 mai - 11 juin 2026 (soutenance)

**Facilitateur** : Mikael
**Delivered** : `[À REMPLIR fin sprint]` / 15 pts cibles
**Features planifiées** : F8 Walk-forward validation (7 pts), Bug fixes + polish (5 pts), Doc + deploy staging (3 pts), **Soutenance 11 juin**

**Points d'attention anticipés** :
- Go/No-Go checklist (cf. [[CryptoBot/avril/planning/sprint-summary]]) entièrement cochée ?
- 62 pts livrés OU Plan B assumé et documenté ?
- Team debriefed soutenance (répétition + Q/R) ?

**Retro spéciale post-soutenance** (lessons learned RNCP) à programmer mi-juin, séparée de la retro S16 classique.

```markdown
### Start / Stop / Continue / Actions SMART
[À REMPLIR fin sprint]
```

## 6. Synthèse transversale

Trois thèmes récurrents émergent déjà de S11 + S12 et seront monitorés jusqu'en S16 :

### Thème 1 — Frontières d'équipes (CLAUDE.md boundary)

**Observation** : un incident S12 (Mikael modifiant `src/etl/`) a révélé que la règle *« NEVER modify code outside your team's directory »* du `CLAUDE.md` racine n'est pas appliquée spontanément par les agents Claude Code quand le fix est trivial. Le coût perçu d'un CR niveau 2 semble supérieur au coût d'un patch direct — c'est une erreur de jugement car ça casse la traçabilité et l'auditabilité RNCP Bloc 4.

**Action structurelle** : template CR niveau 2 low-friction (3 lignes, 30 sec à remplir) + hook pre-commit qui refuse les commits cross-team non taggés `cr:niv2`.

### Thème 2 — PlantUML comme ground truth (ADR-03)

**Observation** : les 22 diagrammes produits en S12 ont révélé ≥3 contradictions entre code, specs markdown et schémas initiaux Mermaid. La règle ADR-03 (*« PlantUML > code > specs en cas de divergence »*) a été adoptée mais nécessite une discipline de mise à jour : chaque changement de schéma DB (cf. `er01-database-schema.md`) ou d'interface partagée (cf. `cl01-pydantic-models.md`) doit déclencher une régénération du `.puml` concerné.

**Action structurelle** : ajouter au DoD (Definition of Done) du sprint *« PlantUML à jour si touché `src/shared/models/**` ou schéma DB »*.

### Thème 3 — Mémoire persistante (claude-mem + vault)

**Observation** : les ADRs S11 ont été reconstruits rétroactivement depuis claude-mem (obs-51, obs-111, obs-215…) parce qu'ils n'étaient pas écrits sur le moment. Sans claude-mem, la décision serait perdue. Le vault Obsidian (`_vault/common/projects/cryptobot/`) + claude-mem forme la **mémoire projet de Bloc 4** et doit être considéré comme artefact de livraison.

**Action structurelle** : ajout au DoD *« toute décision ADR-worthy est écrite dans `history/decisions.md` dans le commit où elle est prise »*.

## 7. Action items ouverts (SSOT)

Source de vérité unique des actions retro. Synchronisée avec Linear (label `retro-action`).

| ID | Sprint origine | Owner | Status | Échéance | Description |
|----|----------------|-------|--------|----------|-------------|
| A-S11-01 | S11 | Jules | **DONE** (S12-w1) | 2026-04-05 | Hex-line + hook bloquant |
| A-S11-02 | S11 | Jules | **DONE** (S12-w1) | 2026-04-05 | Timeline `agents/observations/` |
| A-S11-03 | S11 | Jules | **DONE** (S12-w2) | 2026-04-12 | ADR-01 à ADR-05 dans `history/decisions.md` |
| A-S11-04 | S11 | Jules | **IN PROGRESS** | 2026-04-18 | Coverage ESMA scraper ≥ 80% |
| A-S12-01 | S12 | Jules | **TODO** | 2026-04-20 | Workflow `ln-*` opérationnel |
| A-S12-02 | S12 | Jules | **TODO** | 2026-04-20 | agent-mail MCP + premier message test |
| A-S12-03 | S12 | Mikael | **TODO** | 2026-04-18 | Règle `git add -p` dans `.claude/rules/common.md` |
| A-S12-04 | S12 | Jules + Mikael | **DONE** (ce doc) | 2026-04-14 | Template CR niveau 2 disponible |
| A-S13-01..N | S13 | — | [À REMPLIR] | 2026-05-02 | |
| A-S14-01..N | S14 | — | [À REMPLIR] | 2026-05-16 | |
| A-S15-01..N | S15 | — | [À REMPLIR] | 2026-05-30 | |
| A-S16-01..N | S16 | — | [À REMPLIR] | 2026-06-13 | |

**Règle de clôture** : une action est **DONE** seulement si le critère de mesure est atteint **ET** validé par le facilitateur du sprint suivant en ouverture de retro. Sinon elle est reconduite avec nouvelle échéance (max 2 reconductions → escalation CR niveau 3).

## 8. Liens

- [[CryptoBot/avril/planning/sprint-plan]] — plan des 6 sprints
- [[CryptoBot/avril/planning/sprint-summary]] — résumé exécutif
- [[CryptoBot/avril/planning/gantt]] — Gantt Mermaid
- [[CryptoBot/avril/planning/risks]] — registre risques (R1-R10)
- [[CryptoBot/avril/history/decisions]] — ADRs
- [[rncp/bloc4-pilotage/change-management]] — gestion du changement
- [[rncp/bloc4-pilotage/kpi-performance]] — KPI de pilotage
