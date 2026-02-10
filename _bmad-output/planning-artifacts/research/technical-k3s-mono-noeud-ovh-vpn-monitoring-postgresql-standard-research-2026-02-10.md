---
stepsCompleted: [1]
inputDocuments:
  - 'brainstorm.md'
workflowType: 'research'
lastStep: 1
research_type: 'technical'
research_topic: 'K3s mono-noeud OVH + VPN + Monitoring + PostgreSQL standard'
research_goals: 'Valider un socle mono-noeud reproductible, observable et restaurable avec un risque operationnel maitrise'
user_name: 'Jules'
date: '2026-02-10'
web_research_enabled: true
source_verification: true
---

# Research Report: technical

**Date:** 2026-02-10
**Author:** Jules
**Research Type:** technical
**Research Topic:** K3s mono-noeud OVH + VPN + Monitoring + PostgreSQL standard
**Primary Input:** brainstorm.md

---

## Research Overview

Ce document adapte le brief de recherche au format BMAD pour servir de base de travail compatible workflow.

**Contexte:** plateforme unique sur VPS OVH (Ubuntu), provisionnee par Ansible, avec K3s mono-noeud, WireGuard, Traefik, Argo CD, monitoring et PostgreSQL.

**Objectif principal:** valider qu'une architecture mono-noeud peut rester simple a operer tout en etant observable et restaurable.

## Technical Research Scope Confirmation

### In-Scope

- Provisioning idempotent via Ansible
- Acces admin VPN-first (UI + DB + API K8s)
- GitOps Argo CD (App-of-Apps + autosync)
- Monitoring cluster/DB avec alerting email
- PostgreSQL standard dans le cluster avec persistence
- Backups + restore drill minimal

### Out-of-Scope

- Multi-node / HA / etcd HA
- Stockage distribue (Longhorn)
- PITR/WAL archiving avance
- Exposition publique de PostgreSQL (5432)

### Decision Candidates (a confirmer)

1. VPN-only pour l'administration.
2. Datastore K3s SQLite pour limiter la complexite.
3. PostgreSQL via chart Helm standard (Bitnami) en phase initiale.
4. Monitoring par paliers: Niveau 1 obligatoire, Niveau 2 sur symptomes.
5. Backup combine: snapshot OVH + pg_dump + restore drill.
6. Gestion des secrets via SOPS + age.
7. Pinning explicite des versions K3s/charts avec rollback simple.

## Research Questions

1. Comment structurer Ansible pour garantir idempotence, relance sure et audit?
2. VPN-only couvre-t-il les besoins admin sans friction operationnelle excessive?
3. Le chart PostgreSQL standard est-il suffisant pour backup/restore/monitoring?
4. Quel socle d'alertes minimise le bruit tout en detectant les incidents critiques?
5. Le couple snapshot OVH + pg_dump atteint-il les cibles RTO/RPO attendues?

## Validation Plan

### Phase 1 - Baseline VPS

- Durcissement OS, UFW, SSH key only.
- Preuve: ports publics limites a `22/80/443/51820`.

### Phase 2 - WireGuard

- Tunnel stable et persistant apres reboot.
- Preuve: acces a un service prive via IP VPN.

### Phase 3 - K3s

- Cluster Ready, Traefik et ServiceLB actifs.
- Preuve: ingress de test fonctionnel.

### Phase 4 - Argo CD

- App-of-Apps + autosync.
- Preuve: propagation commit -> sync -> etat attendu.

### Phase 5 - Monitoring / Alerting

- Prometheus, Grafana, Alertmanager operationnels.
- Preuve: alerte test recue par email.

### Phase 6 - PostgreSQL

- Instance persistante, acces DBeaver via VPN.
- Preuve: lecture/ecriture validees apres restart pod et reboot noeud.

### Phase 7 - Backup / Restore

- Dumps compresses avec rotation.
- Preuve: restauration complete d'une base test.

## Risk Register and Mitigations

- **R1 Saturation disque:** quotas retention + alertes disque.
- **R2 Backup non teste:** restore drill periodique obligatoire.
- **R3 Secrets mal geres:** pas de secret en clair, SOPS + age.
- **R4 Upgrade incident:** pinning versions + procedure rollback.
- **R5 Limite mono-noeud:** procedure de reprise et fenetres de maintenance.

## Go / No-Go Criteria

### Go

- Phases 1 a 7 validees avec preuves.
- Restore drill repetable dans la cible de temps.
- Alerting exploitable avec bruit controle.
- Aucun secret sensible en clair dans le repo.

### No-Go

- Restore non fiable ou non repetable.
- Monitoring non exploitable.
- Exposition publique involontaire de services admin/DB.

## Immediate Execution Plan

1. Valider le squelette Ansible (`roles`, `inventory`, tags).
2. Implementer WireGuard + firewall VPN-first.
3. Deployer K3s puis bootstrap Argo CD App-of-Apps.
4. Deployer kube-prometheus-stack avec profil de ressources contraint.
5. Deployer PostgreSQL Helm + job/script pg_dump avec rotation.
6. Ecrire et executer le premier restore drill documente.

## Research Methodology and Source Verification

### Methodology

- Source primaire: `brainstorm.md`.
- Les points techniques sont formules comme hypotheses/decisions candidates a verifier en execution.
- Le plan privilegie des preuves observables (commandes, tests, restore drill).

### Priority Sources

- K3s docs: https://docs.k3s.io
- K3s networking services: https://docs.k3s.io/networking/networking-services
- K3s datastore + backup/restore SQLite: https://docs.k3s.io/datastore
- Argo CD auto-sync: https://argo-cd.readthedocs.io/en/stable/user-guide/auto_sync/
- kube-prometheus-stack: https://artifacthub.io/packages/helm/prometheus-community/kube-prometheus-stack
- Alertmanager config: https://prometheus.io/docs/alerting/latest/configuration/
- WireGuard Ubuntu: https://documentation.ubuntu.com/server/how-to/wireguard-vpn/common-tasks/
- Bitnami PostgreSQL chart: https://artifacthub.io/packages/helm/bitnami/postgresql

### Research Status

- Statut: pre-research brief BMAD adapte.
- Prochaine etape: execution du workflow de recherche technique avec validation web source par source.
