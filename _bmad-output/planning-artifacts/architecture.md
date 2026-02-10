---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
inputDocuments:
  - '_bmad-output/planning-artifacts/prd.md'
  - '_bmad-output/planning-artifacts/product-brief-k3s-mono-pgsql-2026-02-10.md'
  - '_bmad-output/planning-artifacts/research/technical-k3s-mono-noeud-ovh-vpn-monitoring-postgresql-standard-research-2026-02-10.md'
  - 'brainstorm.md'
workflowType: 'architecture'
project_name: 'k3s-mono-pgsql'
user_name: 'Jules'
date: '2026-02-10'
lastStep: 8
status: 'complete'
completedAt: '2026-02-10'
---

# Architecture Decision Document

Ce document fige les decisions architecturales pour garantir une implementation coherente par plusieurs agents AI, sans divergence de patterns ni conflits structurels.

## Project Context Analysis

### Requirements Overview

**Functional Requirements (PRD):**
- Provisioning et baseline operations
- Security et access control
- Deployment et configuration management GitOps
- Observability et alerting
- Data service operations (PostgreSQL)
- Backup et recovery
- Governance et compliance basics

**Non-Functional Requirements (PRD):**
- Performance de verification et convergence
- Securite des acces et secrets
- Fiabilite (disponibilite, succes backup, restore drill)
- Scalabilite moderee
- Integration email et compatibilite schemas

**Scale & Complexity:**
- Primary domain: infrastructure / api_backend operations
- Complexity level: low-to-medium (mono-node assume, pas de HA)
- Estimated architectural components: 9 (provisioning, network security, cluster control plane, ingress, GitOps, observability, data plane, backup plane, governance)

### Technical Constraints & Dependencies

- Mono-node impose: pas de tolerance de panne HA native.
- VPN-first impose: interfaces admin et DB non exposees publiquement.
- GitOps impose: etat cible versionne et reconciliation continue.
- Local-path storage impose: strategie backup/restore disciplinée.
- OVH VPS impose: limites CPU/RAM/disque a surveiller.

### Cross-Cutting Concerns Identified

- Gestion des secrets et rotation
- Auditabilite des changements infra
- Limitation de bruit d'alerte
- Reproductibilite des runs Ansible
- Traçabilite PRD -> architecture -> implementation

## Starter Template Evaluation

### Primary Technology Domain

api_backend oriente operations et infrastructure as code.

### Starter Options Considered

1. **NestJS Starter** (nestjs/nest-cli) - bon pour API produit riche, mais surdimensionne pour un socle infra-first.
2. **Fastify Starter** (fastify-cli) - performant pour API legere, mais ne couvre pas le besoin principal d'orchestration infra GitOps/Ansible.
3. **Express Starter** (express-generator) - simple, mais valeur limitee pour les besoins d'architecture plateforme.
4. **Custom IaC Scaffold** - cible exact du projet: ansible + gitops + policies + runbooks.

### Selected Starter: Custom IaC Scaffold

**Rationale for Selection:**
- Le projet ne vise pas un produit frontend/backend classique.
- Le besoin principal est de standardiser provisioning, securite, deploiement et exploitation.
- Un scaffold custom reduit la dette de conventions hors-sujet et cadre les agents AI sur les bons artefacts.

**Initialization Command:**

```bash
mkdir -p infra/ansible/{inventory/prod,group_vars,roles/{base_hardening,wireguard,k3s,argocd_bootstrap,backup_pg_dump},playbooks} \
  gitops/{bootstrap,apps/{argocd,monitoring,postgres,policies},clusters/prod} \
  scripts/{backup,restore,ops} docs/{runbooks,adrs} .github/workflows
```

**Architectural Decisions Provided by Starter:**

**Language & Runtime:**
- YAML-first (Ansible, Kubernetes manifests, Helm values)
- Bash utilitaire minimal pour operations

**Styling Solution:**
- N/A (pas de perimetre UX/UI)

**Build Tooling:**
- Validation YAML, checks statiques, pipelines CI sur manifests/playbooks

**Testing Framework:**
- Tests d'idempotence Ansible
- Validation manifests Kubernetes (schema/lint)
- Scenarios restore drill automatisables

**Code Organization:**
- Separation nette `infra/`, `gitops/`, `scripts/`, `docs/`

**Development Experience:**
- Workflow declaratif, revisions PR, evidence logs et runbooks

## Core Architectural Decisions

### Decision Priority Analysis

**Critical Decisions (Block Implementation):**
- VPN-first pour admin + DB
- K3s mono-node comme socle cible
- GitOps Argo CD App-of-Apps
- PostgreSQL standard sur chart Helm avec persistence
- Strategie backup + restore drill obligatoire

**Important Decisions (Shape Architecture):**
- Gestion des secrets SOPS + age
- Kube-prometheus-stack pour observabilite
- Structuration repo IaC-first

**Deferred Decisions (Post-MVP):**
- HA multi-node
- PITR/WAL archiving avance
- SSO/IdP global

### Data Architecture

- **Engine:** PostgreSQL chart Bitnami `17.0.2` (appVersion `17.6.0`).
- **Persistence:** PVC local-path (mono-node).
- **Backup model:** pg_dump planifie + retention + verification + restore drill documente.
- **Data contracts:** schemas explicites pour metadonnees backup, alertes et traces ops.
- **Data access boundary:** acces DB uniquement via VPN.

### Authentication & Security

- **Access plane:** WireGuard obligatoire pour acces admin.
- **SSH policy:** key-only, root login desactive.
- **Secrets:** SOPS `v3.11.0` + age `v1.3.1`.
- **Cluster authz:** RBAC minimal privilege + service accounts dedies.
- **Exposure policy:** public strictement 22/80/443/51820; 5432 prive.

### API & Communication Patterns

- **Control API style:** endpoints d'etat standardises (health/readiness/backup/restore status).
- **GitOps flow:** source of truth Git -> Argo CD sync -> drift detection.
- **Error contract:** codes stables + correlation id + zero secret leakage.
- **Alerting channel:** Alertmanager vers email, dedup et repeat control.

### Frontend Architecture

- N/A par decision explicite de perimetre (aucun livrable UX/UI).

### Infrastructure & Deployment

- **Provisioning:** ansible-core `2.20.2`.
- **Cluster:** K3s `v1.35.0+k3s3`.
- **GitOps controller:** Argo CD `v3.3.0`.
- **Observability stack:** kube-prometheus-stack chart `81.6.1`.
- **Release control:** pinning versions par environnement avec promotion explicite.
- **Execution boundary:** aucune estimation temporelle; readiness basee sur preuves de validation.

### Decision Impact Analysis

**Implementation Sequence:**
1. Baseline infra (hardening + firewall + ssh)
2. WireGuard + verification access path
3. K3s + ingress/service lb + storage
4. Argo CD bootstrap + app-of-apps
5. Monitoring/alerting
6. PostgreSQL + policies d'acces
7. Backup + restore drill

**Cross-Component Dependencies:**
- GitOps depend de cluster ready.
- PostgreSQL depend du storage local-path disponible.
- Alerting depend des routes SMTP et policies.
- Restore drill depend de backup pipeline et procedures runbookees.

## Implementation Patterns & Consistency Rules

### Pattern Categories Defined

**Critical Conflict Points Identified:** 18 zones ou des agents AI peuvent diverger sans regles explicites.

### Naming Patterns

**Database Naming Conventions:**
- Tables en `snake_case` pluriel.
- Colonnes en `snake_case`.
- PK standard `id`, FK standard `<entity>_id`.

**API Naming Conventions:**
- Endpoints REST en pluriel (`/backups`, `/components`, `/health`).
- Query params en `snake_case`.
- Reponses JSON en `snake_case`.

**Code Naming Conventions:**
- Fichiers manifests: `kebab-case`.
- Roles Ansible: `snake_case`.
- Dossiers de domaines: `kebab-case`.

### Structure Patterns

**Project Organization:**
- `infra/ansible` pour provisioning host + bootstrap cluster.
- `gitops/` pour applications cluster et policies.
- `scripts/` pour operations reproductibles (backup/restore/checks).
- `docs/runbooks` pour procedures operations.

**File Structure Patterns:**
- 1 domaine = 1 dossier + README domaine.
- Valeurs Helm separees par environnement.
- Secrets chiffres dans dossiers aligns avec app cible.

### Format Patterns

**API Response Formats:**
- Wrapper standard `{ "status": "ok|error", "data": ..., "error": ..., "correlation_id": ... }`.

**Data Exchange Formats:**
- Dates en ISO 8601 UTC.
- Aucun boolen represente en entier.
- Null explicite autorise pour champs optionnels seulement.

### Communication Patterns

**Event System Patterns:**
- Evenements ops en `domain.action` (ex: `backup.completed`).
- Payload event avec `timestamp`, `source`, `severity`, `correlation_id`.

**State Management Patterns:**
- Etat declare dans Git.
- Etat runtime observe via metrics + status endpoints.
- Toute correction manuelle doit etre retro-portee dans Git.

### Process Patterns

**Error Handling Patterns:**
- Erreurs classees: validation/authz/dependency/timeout/internal.
- Message user-friendly + details techniques en logs structurés.

**Loading State Patterns:**
- Operations longues publient statut intermediaire (`pending`, `running`, `completed`, `failed`).
- Reprise idempotente sur echec partiel.

### Enforcement Guidelines

**All AI Agents MUST:**
- Respecter les conventions de nommage sans exception.
- Ajouter/mettre a jour tests de validation a chaque changement infra.
- Documenter tout choix non-trivial en ADR dans `docs/adrs/`.
- Ne jamais introduire de secret en clair.

**Pattern Enforcement:**
- CI bloque merge sur violation lint/schema/secrets.
- Revue PR avec checklist architecture obligatoire.
- Exceptions documentees uniquement via ADR approuvee.

### Pattern Examples

- Nom release Helm: `postgres-prod`.
- Nom namespace: `platform-monitoring`, `platform-data`.
- Nom role Ansible: `backup_pg_dump`.
- Nom runbook: `restore-drill-postgres.md`.

## Project Structure & Boundaries

### Complete Project Directory Structure

```text
k3s-mono-pgsql/
├── README.md
├── .gitignore
├── .github/
│   └── workflows/
│       ├── ci-infra.yml
│       ├── validate-gitops.yml
│       └── restore-drill-check.yml
├── infra/
│   └── ansible/
│       ├── ansible.cfg
│       ├── inventory/
│       │   └── prod/
│       │       └── hosts.yml
│       ├── group_vars/
│       │   └── all.yml
│       ├── playbooks/
│       │   ├── site.yml
│       │   ├── bootstrap.yml
│       │   └── backup.yml
│       └── roles/
│           ├── base_hardening/
│           ├── wireguard/
│           ├── k3s/
│           ├── argocd_bootstrap/
│           └── backup_pg_dump/
├── gitops/
│   ├── bootstrap/
│   │   ├── argocd-install.yaml
│   │   └── root-app.yaml
│   ├── clusters/
│   │   └── prod/
│   │       ├── kustomization.yaml
│   │       └── policies/
│   └── apps/
│       ├── argocd/
│       ├── monitoring/
│       │   ├── helmrelease.yaml
│       │   └── values-prod.yaml
│       ├── postgres/
│       │   ├── helmrelease.yaml
│       │   ├── values-prod.yaml
│       │   └── network-policy.yaml
│       └── policies/
│           ├── namespaces.yaml
│           └── rbac.yaml
├── scripts/
│   ├── backup/
│   │   ├── run-pgdump.sh
│   │   └── rotate-backups.sh
│   ├── restore/
│   │   └── restore-drill.sh
│   └── ops/
│       ├── health-check.sh
│       └── collect-diagnostics.sh
├── docs/
│   ├── runbooks/
│   │   ├── backup.md
│   │   ├── restore-drill-postgres.md
│   │   ├── incident-alerts.md
│   │   └── upgrade-playbook.md
│   └── adrs/
│       ├── 0001-vpn-first.md
│       ├── 0002-k3s-mono-node.md
│       ├── 0003-gitops-argo.md
│       └── 0004-postgres-standard.md
└── _bmad-output/
    └── planning-artifacts/
        ├── prd.md
        ├── architecture.md
        └── research/
```

### Architectural Boundaries

**API Boundaries:**
- Endpoints d'etat exposes par services ops internes.
- Aucun endpoint d'administration expose en public internet.

**Component Boundaries:**
- Provisioning host (Ansible) separe du runtime cluster (GitOps).
- Monitoring separe du plan de donnees (PostgreSQL).

**Service Boundaries:**
- Argo CD: reconciliation uniquement.
- Monitoring stack: collecte et alerting uniquement.
- PostgreSQL: service data stateful dedie.

**Data Boundaries:**
- Donnees metier dans PostgreSQL.
- Metriques/time-series dans Prometheus.
- Artefacts backup hors DB active avec retention.

### Requirements to Structure Mapping

**Feature/FR Mapping:**
- Provisioning & Baseline Operations -> `infra/ansible/roles/base_hardening`, `infra/ansible/playbooks/site.yml`
- Security & Access Control -> `infra/ansible/roles/wireguard`, `gitops/apps/policies/`
- Deployment & Config Management -> `gitops/bootstrap/`, `gitops/apps/`
- Observability & Alerting -> `gitops/apps/monitoring/`, `docs/runbooks/incident-alerts.md`
- Data Service Operations -> `gitops/apps/postgres/`
- Backup & Recovery -> `scripts/backup/`, `scripts/restore/`, `docs/runbooks/restore-drill-postgres.md`

**Cross-Cutting Concerns:**
- Secrets management -> SOPS files co-localises aux manifests cibles
- Compliance/audit -> `docs/adrs/` + logs operations
- Validation -> `.github/workflows/*.yml`

### Integration Points

**Internal Communication:**
- Argo CD synchronise manifests vers cluster.
- Alertmanager notifie via SMTP.
- Scripts ops interrogent endpoints health/readiness.

**External Integrations:**
- OVH VPS et snapshots.
- SMTP provider pour notifications.
- Client VPN WireGuard pour acces admin.

**Data Flow:**
- Git commit -> Argo sync -> deploiement cluster.
- Cluster metrics -> Prometheus -> Alertmanager/Grafana.
- DB dump -> stockage backup -> restore drill verification.

### File Organization Patterns

**Configuration Files:**
- Variables infra dans `infra/ansible/group_vars/all.yml`.
- Valeurs app par domaine dans `gitops/apps/*/values-prod.yaml`.

**Source Organization:**
- Infra declarative en YAML; scripts shell uniquement pour orchestration ops.

**Test Organization:**
- Checks CI pour lint/validation manifests.
- Scripts de verification de restore executes regulierement.

**Asset Organization:**
- Artefacts ops et logs structures sous `scripts/` et `docs/runbooks/`.

### Development Workflow Integration

**Development Server Structure:**
- N/A (pas d'application frontend/backend interactive a lancer localement).

**Build Process Structure:**
- Validation statique puis application incremental des playbooks/manifests.

**Deployment Structure:**
- Promotion Git-based par environnement.
- Rollback par revert Git + resync Argo.

## Architecture Validation Results

### Coherence Validation ✅

**Decision Compatibility:**
- Les choix K3s, Argo CD, monitoring et PostgreSQL sont compatibles dans un mode mono-node.
- Les versions critiques sont epinglees pour limiter les regressions de compatibilite.

**Pattern Consistency:**
- Conventions de nommage, structure et formats unifiees.
- Regles d'implementation anti-derive explicites pour agents AI.

**Structure Alignment:**
- La structure repo separe correctement provisioning, runtime, operations et documentation.

### Requirements Coverage Validation ✅

**Epic/Feature Coverage:**
- Couverture complete des categories FR du PRD.

**Functional Requirements Coverage:**
- Toutes les categories FR (provisioning, security, gitops, observability, data, backup, governance) sont supportees par decisions + structure.

**Non-Functional Requirements Coverage:**
- Performance: check endpoints/convergence.
- Security: VPN-first + secrets chiffrés.
- Reliability: backup success + restore drill.
- Scalability: limites explicites mono-node + croissance controlee.

### Implementation Readiness Validation ✅

**Decision Completeness:**
- Decisons critiques documentees avec rationale.
- Versions cibles explicites pour composants principaux.

**Structure Completeness:**
- Arborescence complete et directement executable par agents.

**Pattern Completeness:**
- Regles suffisantes pour eviter conflits de style, structure et interfaces.

### Gap Analysis Results

**Critical Gaps:**
- Aucun gap bloquant identifie pour demarrage implementation.

**Important Gaps:**
- Definir seuils finaux d'alerte par environnement.
- Formaliser checklist d'upgrade K3s/charts en runbook detaille.

**Nice-to-Have Gaps:**
- Ajouter validation automatique de restauration sur data set plus realiste.
- Enrichir dashboard standard SLO operations.

### Validation Issues Addressed

- Absence de perimetre UX/UI traitee explicitement: aucune decision frontend requise.
- Risque de derive secrets traite par pattern SOPS+age obligatoire.
- Risque de restauration non prouve traite par restore drill standardise.

### Architecture Completeness Checklist

**✅ Requirements Analysis**
- [x] Project context analyzed
- [x] Scale and complexity assessed
- [x] Technical constraints identified
- [x] Cross-cutting concerns mapped

**✅ Architectural Decisions**
- [x] Critical decisions documented with versions
- [x] Technology stack fully specified
- [x] Integration patterns defined
- [x] Performance considerations addressed

**✅ Implementation Patterns**
- [x] Naming conventions established
- [x] Structure patterns defined
- [x] Communication patterns specified
- [x] Process patterns documented

**✅ Project Structure**
- [x] Complete directory structure defined
- [x] Component boundaries established
- [x] Integration points mapped
- [x] Requirements-to-structure mapping complete

### Architecture Readiness Assessment

**Overall Status:** READY FOR IMPLEMENTATION

**Confidence Level:** high

**Key Strengths:**
- Architecture simple, contraintee, actionnable.
- Decisions orientees exploitation/recovery, pas uniquement deploiement.
- Patterns explicites pour execution multi-agents coherente.

**Areas for Future Enhancement:**
- Mode HA et DR avance hors MVP.
- Maturite SLO/SLA operations.
- Automatisation compliance/security plus poussee.

### Implementation Handoff

**AI Agent Guidelines:**
- Appliquer strictement les decisions et conventions de ce document.
- Toute deviation doit passer par ADR.
- Prioriser la preuve operationnelle (tests, restore, alertes) a chaque increment.

**First Implementation Priority:**
- Initialiser le scaffold IaC, puis enchaîner baseline security -> cluster -> gitops -> observability -> postgres -> backup/restore.
