---
stepsCompleted: [1, 2, 3, 4, 5]
inputDocuments:
  - '_bmad-output/planning-artifacts/prd.md'
  - '_bmad-output/planning-artifacts/architecture.md'
  - '_bmad-output/planning-artifacts/epics.md'
workflowType: 'test-design'
project_name: 'k3s-mono-pgsql'
scope: 'functional-only'
user_name: 'Jules'
date: '2026-02-10'
status: 'complete'
completedAt: '2026-02-10'
communication_language: 'French'
document_output_language: 'French'
---

# Test Design - K3s Mono-Noeud Ops Platform

## 1. Objectif

Definir le design de tests fonctionnels du MVP pour valider les capacites operateur de bout en bout:

- provisioning reproductible
- securite VPN-first
- deploiement GitOps
- observabilite + alerting
- PostgreSQL prive persistant
- backup + restore drill

## 2. Perimetre

### In Scope (fonctionnel)

- Validation des 5 epics et 18 stories de `_bmad-output/planning-artifacts/epics.md`.
- Verification des comportements attendus et des resultats observables cote operateur.
- Verifications de flux complets (setup -> usage -> verification).

### Out of Scope (pour ce cycle)

- UX/UI (hors perimetre produit).
- Campagnes performance avancees / charge.
- Pentest complet / audit securite externe.
- DR multi-region / HA multi-noeud.

## 3. Strategie de test fonctionnel

### Niveaux de test

1. Smoke tests ops: verification rapide de disponibilite des composants critiques.
2. Tests fonctionnels integration: validation des flux par domaine (infra, gitops, db, monitoring).
3. Tests e2e ops: scenarios complets backup -> restore -> preuve.

### Approche

- Priorite P1: scenarios critiques de mise en service et recovery.
- Priorite P2: scenarios de robustesse fonctionnelle (rerun, rollback, derive).
- Evidence obligatoire: logs, sorties commandes, captures d'etat des ressources.

### Outils d'execution

- Ansible (`ansible-playbook`) pour setup/verifications infra.
- `kubectl` / `helm` / `argocd` CLI pour verification etat cluster/GitOps.
- Scripts ops du repo (`scripts/backup`, `scripts/restore`, `scripts/ops`).

## 4. Environnements et prerequis

### Environnement cible test

- 1 VPS OVH mono-noeud.
- K3s `v1.35.0+k3s3`.
- Argo CD `v3.3.0`.
- kube-prometheus-stack chart `81.6.1`.
- PostgreSQL chart `17.0.2`.

### Prerequis execution

- Acces SSH par cle.
- Acces WireGuard operationnel.
- Repo GitOps configure.
- Secrets SOPS+age disponibles pour decrypt en environnement de test.

## 5. Criteres d'entree / sortie

### Entree

- PRD, Architecture et Epics valides.
- Infrastructure de test disponible.
- Variables d'environnement et secrets valides.

### Sortie

- 100% des cas P1 passes.
- 0 defect bloquant ouvert.
- Restore drill execute avec succes et trace.
- Traceabilite FR -> tests complete.

## 6. Catalogue des scenarios (fonctionnel)

### Epic 1 - Fondation securisee

- TD-1.1 (P1) Story 1.1: Provisioning baseline durci.
  - Verification: ssh key-only, root disabled, firewall actif, checks conformite OK.
- TD-1.2 (P1) Story 1.2: Idempotence et execution par tags.
  - Verification: rerun sans changements inattendus, execution taggee isolee.
- TD-1.3 (P1) Story 1.3: Acces admin VPN-first.
  - Verification: acces admin uniquement via VPN, ports publics limites.
- TD-1.4 (P1) Story 1.4: Secrets chiffres.
  - Verification: secrets en clair absents, CI bloque toute fuite.

### Epic 2 - Livraison GitOps

- TD-2.1 (P1) Story 2.1: Installation K3s mono-noeud.
  - Verification: node Ready, composants coeur healthy.
- TD-2.2 (P1) Story 2.2: Bootstrap Argo CD App-of-Apps.
  - Verification: root app + child apps convergents.
- TD-2.3 (P1) Story 2.3: Detection derive + rollback.
  - Verification: derive detectee OutOfSync, rollback par revert Git valide.
- TD-2.4 (P2) Story 2.4: Gates CI qualite.
  - Verification: lint/schema/secrets/traceabilite bloquent en cas d'erreur.

### Epic 3 - Observabilite et alerting

- TD-3.1 (P1) Story 3.1: Stack monitoring + dashboards.
  - Verification: Prometheus/Alertmanager/Grafana healthy + metriques presentes.
- TD-3.2 (P1) Story 3.2: Alertes email actionnables.
  - Verification: alertes critiques recues, dedup/grouping actifs.
- TD-3.3 (P1) Story 3.3: Endpoints statut et contrat d'erreur.
  - Verification: schemas stables, correlation id, aucune fuite de secret.

### Epic 4 - PostgreSQL securise

- TD-4.1 (P1) Story 4.1: Deploiement PostgreSQL persistant.
  - Verification: chart deploye, PVC relies, DB ready.
- TD-4.2 (P1) Story 4.2: Restriction acces DB.
  - Verification: 5432 non public, acces non autorise bloque.
- TD-4.3 (P1) Story 4.3: Durabilite donnees + monitoring DB.
  - Verification: donnees persistent apres restart, alertes DB fonctionnelles.

### Epic 5 - Recovery et gouvernance

- TD-5.1 (P1) Story 5.1: Backups planifies avec retention.
  - Verification: dumps horodates, rotation, integrite validee.
- TD-5.2 (P1) Story 5.2: Restore drill mesure.
  - Verification: restauration complete, RTO/perte mesures.
- TD-5.3 (P2) Story 5.3: Gouvernance et audit trail.
  - Verification: ADR et traces operations exploitables.
- TD-5.4 (P2) Story 5.4: Documentation ops + matrice validation.
  - Verification: docs API/runbooks completes, mapping FR/NFR present.

## 7. Matrice de traceabilite FR -> Test Design

- FR1 -> TD-1.1
- FR2 -> TD-1.2
- FR3 -> TD-1.2
- FR4 -> TD-1.1
- FR5 -> TD-1.3
- FR6 -> TD-1.3
- FR7 -> TD-1.3
- FR8 -> TD-1.4
- FR9 -> TD-2.2
- FR10 -> TD-2.2
- FR11 -> TD-2.3
- FR12 -> TD-2.3
- FR13 -> TD-3.1
- FR14 -> TD-3.1
- FR15 -> TD-3.2
- FR16 -> TD-3.2
- FR17 -> TD-4.1
- FR18 -> TD-4.2
- FR19 -> TD-4.3
- FR20 -> TD-4.3
- FR21 -> TD-5.1
- FR22 -> TD-5.1
- FR23 -> TD-5.2
- FR24 -> TD-5.2
- FR25 -> TD-5.3
- FR26 -> TD-5.4
- FR27 -> TD-5.3

## 8. Ordre d'execution recommande

1. TD-1.1 -> TD-1.4
2. TD-2.1 -> TD-2.4
3. TD-3.1 -> TD-3.3
4. TD-4.1 -> TD-4.3
5. TD-5.1 -> TD-5.4

## 9. Livrables de preuve attendus

- Journal d'execution de chaque TD-x.y (date, executant, resultat).
- Captures/sorties de commandes critiques (cluster health, argo sync, backup/restore).
- Rapport final de campagne: taux de succes, defects ouverts, blocants restants.
