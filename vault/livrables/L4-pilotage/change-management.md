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
  - change-management
  - governance
created: 2026-04-14
ingested_by: agent-L4-Governance
related:
  - "[[CryptoBot/avril/history/decisions]]"
  - "[[CryptoBot/avril/planning/risks]]"
  - "[[rncp/bloc4-pilotage/retrospectives]]"
  - "[[rncp/bloc4-pilotage/kpi-performance]]"
  - "[[CryptoBot/avril/audit/audit-global]]"
---

# Change Management — CryptoBot S11-S16

RNCP38919 Bloc 4 — Piloter un projet informatique : gestion du changement.

## 1. Périmètre

Un **Change Request (CR)** est requis pour tout changement qui affecte au moins un de ces périmètres :

| Périmètre | Exemples |
|-----------|----------|
| **Architecture** | Ajout/suppression d'un service Docker, changement de base de données, introduction d'un broker |
| **Dépendances** | Upgrade majeur (Python 3.11→3.12, FastAPI 0.x→1.x), ajout d'une lib non triviale, retrait d'une dépendance partagée |
| **Interfaces `src/shared/`** | Modif d'un Pydantic model cross-équipes (`CryptoRecord`, `Signal`, `User`), changement de signature de config |
| **Sécurité** | Auth, JWT, bcrypt rounds, CORS, secrets, politique RBAC |
| **SLA / qualité** | Coverage cible, seuil confidence signaux, latence API cible |
| **Données** | Schéma TimescaleDB, rétention, compression hypertables, layout MinIO |
| **CI/CD & Infra prod** | Pipeline, image base, reverse proxy, DNS, monitoring stack |

**Hors périmètre CR** (pas de formalisme) : refactor interne à une équipe sans impact d'interface, fix typo, test ajouté, log level modifié, doc mise à jour.

**Règle simple** : *« Si mon change peut casser le code ou le workflow d'un autre (humain ou agent), c'est un CR. »*

## 2. Template Change Request

```markdown
## CR-{YYYYMMDD}-{nn} — {titre court}

- **Demandeur** : {Jules | Mikael | agent}
- **Date ouverture** : YYYY-MM-DD
- **Niveau** : {1 | 2 | 3}
- **Statut** : {PROPOSED | UNDER_REVIEW | ACCEPTED | DEFERRED | REJECTED | IMPLEMENTED | CLOSED}

### Contexte
{Problème observé, contrainte, opportunité. Pourquoi le statu quo ne suffit pas.}

### Proposition
{Solution proposée, en 3-5 lignes, concrète.}

### Alternatives considérées
- Alt 1 : {description} — rejetée car {raison}
- Alt 2 : {description} — rejetée car {raison}

### Impact
- **Code** : {fichiers/modules touchés, breaking change ? migration ?}
- **Infra** : {services Docker, volumes, ports, secrets}
- **Sécurité** : {surface d'attaque modifiée ? audit requis ?}
- **Coût** : {EUR/mois si infra, sinon HJ effort}
- **Utilisateur** : {UX affectée ? doc à mettre à jour ?}

### Risque (matrice §3)
- Probabilité : {Low | Medium | High | Very High | Critical}
- Impact : {Low | Medium | High | Very High | Critical}
- Cellule : {cf. §3}
- Mitigation : {actions préventives}

### Effort
{HJ estimés, répartis par personne}

### Décision
- **Verdict** : {ACCEPTED | DEFERRED | REJECTED}
- **Par** : {lead équipe | orchestrator | Jules}
- **Date** : YYYY-MM-DD
- **Commentaire** : {justification ≤ 5 lignes}

### Suivi d'exécution
- Branche : `{team}/cr-{id}`
- PR : {lien}
- ADR généré ? : {oui → [[history/decisions#ADR-XX]] | non}
- Commit final : {sha}
- CR clos le : YYYY-MM-DD
```

## 3. Matrice d'impact (5×5)

Grille croisant **Probabilité** (d'occurrence d'un effet négatif lors de l'exécution du change) et **Impact** (gravité si l'effet survient).

```
                    PROBABILITÉ
              Low    Medium   High   V.High  Critical
           ┌───────┬────────┬──────┬────────┬──────────┐
Critical   │  M2   │  H1    │ VH1  │  VH2   │   X1     │
           ├───────┼────────┼──────┼────────┼──────────┤
Very High  │  M1   │  H2    │ H3   │  VH3   │   VH4    │
           ├───────┼────────┼──────┼────────┼──────────┤
IMPACT   H │  L2   │  M3    │ H4   │  H5    │   VH5    │
           ├───────┼────────┼──────┼────────┼──────────┤
Medium     │  L1   │  M4    │ M5   │  H6    │   H7     │
           ├───────┼────────┼──────┼────────┼──────────┤
Low        │  L3   │  L4    │ L5   │  M6    │   M7     │
           └───────┴────────┴──────┴────────┴──────────┘
```

**Actions par cellule** :

| Zone | Cellules | Action requise | Approbation |
|------|----------|----------------|-------------|
| **X** (inacceptable) | X1 | **REJECT par défaut**. Chercher alternative. Si indispensable → CR niveau 3 + Plan B documenté + go/no-go Jules | Jules |
| **VH** (très haute) | VH1-VH5 | CR niveau 3, ADR obligatoire, plan de rollback documenté, test staging pre-merge | Jules + orchestrator |
| **H** (haute) | H1-H7 | CR niveau 2 ou 3, revue croisée cross-team, monitoring post-déploiement 48h | Orchestrator + lead impacté |
| **M** (moyenne) | M1-M7 | CR niveau 1 ou 2, test ciblé, validation PR | Lead équipe |
| **L** (basse) | L1-L5 | CR niveau 1, revue allégée | Lead équipe |

**Lecture croisée avec [[CryptoBot/avril/planning/risks]]** : un CR qui matérialise ou aggrave un risque R1-R10 hérite automatiquement du niveau de sévérité du risque (ex. CR touchant le pipeline RL → VH automatique via R1).

## 4. Workflow d'approbation (3 niveaux)

### Niveau 1 — Interne équipe

**Critères cumulatifs** :
- Périmètre limité à une seule équipe (data-eng OU ml OU api OU frontend OU infra)
- Effort ≤ 2 HJ
- Aucun impact sur `src/shared/`
- Pas de breaking change d'interface externe

**Approbateur** : lead de l'équipe (Jules pour data-eng/api/infra, Mikael pour ml/frontend)
**Délai cible** : 24h
**Artefact** : issue Linear label `change-request` + `niv1` + lead équipe en assignee

### Niveau 2 — Cross-team ou sécurité

**Critères** (au moins un) :
- Change impacte ≥ 2 équipes
- Modification d'un modèle `src/shared/`
- Impact sécurité (auth, secrets, CORS, RBAC)
- Effort 2-5 HJ

**Approbateurs** : orchestrator (Jules) + lead de chaque équipe impactée
**Délai cible** : 48h
**Artefact** : issue Linear `change-request` + `niv2` + assignees multiples + doc CR complète dans ce fichier

### Niveau 3 — Architecture / breaking / DB

**Critères** (au moins un) :
- Change architectural (nouveau service, retrait service, changement de pattern)
- Breaking change API publique (endpoint supprimé/signature modifiée)
- Migration schéma DB (ajout/suppression colonne, nouvelle table critique)
- Effort > 5 HJ
- Impact financier (coût infra)

**Approbateur final** : Jules (owner projet)
**ADR obligatoire** dans `[[history/decisions]]` avant merge
**Délai cible** : 5 jours (incluant revue async)
**Artefact** : issue Linear `change-request` + `niv3` + PR taggée `adr-required` + blocage merge via branch protection

## 5. Circuit complet

```
1. OUVERTURE
   └─ Linear issue créée (label change-request, niveau 1/2/3)
      └─ Template CR rempli en commentaire initial

2. REVUE
   ├─ Niv1 : lead équipe self-review
   ├─ Niv2 : orchestrator + lead impacté (async ≤48h)
   └─ Niv3 : Jules + ADR draft soumis

3. DÉCISION
   └─ Commentaire Linear avec verdict + justification
      ├─ ACCEPTED → statut In Progress, branche créée
      ├─ DEFERRED → statut Backlog + date de réévaluation
      └─ REJECTED → statut Done (closed as won't fix) + justification

4. EXÉCUTION
   └─ Développement sur branche `{team}/cr-{id}`
      └─ PR créée, CI verte, revue PR par approbateur

5. CLÔTURE
   └─ Merge PR → commentaire Linear avec SHA final
      └─ CR marqué CLOSED dans ce document
         └─ ADR publié (si niv3) dans history/decisions.md
```

**Communication hors Linear** : pour les CR niveau 2 et 3, annonce automatique via `mcp__agent-mail__send_message` aux équipes impactées (cf. §7).

## 6. Exemples de CR passés (dérivés des ADRs)

| CR ID | Titre | Niveau | Statut | Référence ADR |
|-------|-------|--------|--------|---------------|
| CR-20260411-01 | Rendre Linear obligatoire pour tout projet IT, créer équipe CryptoBot (CRY) | 3 | **CLOSED** (implémenté, double rattachement CRY + SAP) | [[CryptoBot/avril/history/decisions#ADR-01]] |
| CR-20260412-01 | Migrer la doc visuelle de 10 diagrammes Mermaid vers 22 diagrammes PlantUML | 3 | **CLOSED** (22 .puml + SVG/PNG générés, commit `2573883`) | [[CryptoBot/avril/history/decisions#ADR-02]] |
| CR-20260412-02 | Stack prod OVH VPS + Docker Compose + Grafana/Prometheus/Loki (rejeter archive AWS/Terraform) | 3 | **CLOSED** (`.claude/rules/devops-prod.md` en place, `legacy-aws.md` archivé) | [[CryptoBot/avril/history/decisions#ADR-04]] |

**Lecture** : ces 3 CR auraient été formalisés en amont si le workflow `niveau 3 + ADR` avait été en place dès S11. Ils ont été reconstitués rétroactivement en S12 à partir de claude-mem — c'est la raison d'être du thème 3 de [[CryptoBot/avril/rncp/livrables/L4-pilotage/retrospectives#synthèse-transversale]].

## 7. Communication

### Annonce accept / reject

Pour tout CR **niveau 2 ou 3**, un message `mcp__agent-mail__send_message` est envoyé dans les 2h suivant la décision :

```
To: {équipes impactées, ex: cryptobot-dev, cryptobot-tests, cryptobot-ops}
Subject: [CR-{id}] {verdict} — {titre}

{Résumé décision + lien Linear + impact concret sur votre équipe + échéance}
```

**Pour les ACCEPTED niv3** : message secondaire aux équipes non directement impactées pour information, sans attente d'action.

**Pour les REJECTED** : justification publique (thread Linear + agent-mail) — pas de décision cachée.

### Weekly digest

Tous les vendredis 17:30, après retro, un digest est publié dans `#cryptobot-weekly` (cf. [[CryptoBot/avril/rncp/livrables/L4-pilotage/kpi-performance#gouvernance]]) :
- CRs ouverts cette semaine (count + liste)
- CRs clos cette semaine (count + verdict)
- CRs deferred à réévaluer

## 8. Révision périodique

**Mensuelle** — le premier vendredi du mois, revue des CR `DEFERRED` :
- Le contexte a-t-il changé ?
- La raison du défer est-elle encore valide ?
- Doit-on : (a) réouvrir, (b) re-deferrer avec nouvelle date, (c) rejeter définitivement ?

**En fin de cycle (après S16)** — audit complet du circuit :
- Nombre de CR par niveau
- Délai moyen de décision par niveau
- % CR ACCEPTED, DEFERRED, REJECTED
- Corrélation avec les risques matérialisés ([[CryptoBot/avril/planning/risks]])

Ces métriques alimentent la section §5 KPI Qualité de [[CryptoBot/avril/rncp/livrables/L4-pilotage/kpi-performance]].

## 9. Anti-patterns à prévenir

- **CR a posteriori** (« j'ai déjà merge, je remplis le CR après ») → rejet systématique, revert obligatoire
- **CR fleuve** (ticket > 200 lignes, scope flou) → découper en sous-CR
- **CR contourné par hotfix** → un hotfix prod justifie un CR niv2 rétroactif dans les 24h suivant le fix, sous peine de sanction trace Bloc 4
- **Approbateur absent** → SLA 48h niv2 / 5j niv3 ; si dépassement, escalation automatique au niveau supérieur

## 10. Liens

- [[CryptoBot/avril/history/decisions]] — registre ADR (sortie des CR niv3)
- [[CryptoBot/avril/planning/risks]] — risques R1-R10 (input de la matrice §3)
- [[CryptoBot/avril/audit/audit-global]] — 8 findings CRITICAL qui génèrent des CR niv3 prioritaires
- [[rncp/bloc4-pilotage/retrospectives]] — actions retro qui peuvent se muer en CR
- [[rncp/bloc4-pilotage/kpi-performance]] — KPI de gouvernance des CR
