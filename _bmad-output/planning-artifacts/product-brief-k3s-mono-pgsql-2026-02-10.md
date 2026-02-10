---
stepsCompleted: [1, 2, 3, 4, 5]
inputDocuments:
  - 'brainstorm.md'
  - '_bmad-output/planning-artifacts/research/technical-k3s-mono-noeud-ovh-vpn-monitoring-postgresql-standard-research-2026-02-10.md'
date: '2026-02-10'
author: 'Jules'
---

# Product Brief: K3s Mono-Noeud Ops Platform

## Executive Summary

K3s Mono-Noeud Ops Platform est un socle d'infrastructure auto-heberge qui permet a un profil technique (solo ou petite equipe) de deployer des applications de facon reproductible et exploitable sur un seul VPS OVH.

Le produit combine provisioning Ansible, securite VPN-first, GitOps Argo CD, monitoring/alerting et PostgreSQL standard dans une approche volontairement pragmatique: moins de complexite, plus de discipline operationnelle.

L'objectif est de reduire le temps et le risque pour passer d'un VPS nu a une plateforme utilisable en production legere, avec restauration testee et visibilite operationnelle native.

---

## Core Vision

### Problem Statement

Les equipes techniques qui veulent heberger une stack Kubernetes simple et economique se retrouvent entre deux extremes:
- solutions gerees puissantes mais couteuses ou surdimensionnees
- auto-hebergement fragile, peu standardise et difficile a maintenir dans le temps

Le probleme principal n'est pas seulement de "faire tourner K3s", mais d'obtenir un environnement completement exploitable: securise, observable, sauvegardable et rejouable.

### Problem Impact

Sans cadre produit clair:
- le setup prend trop de temps et depend d'actions manuelles
- la securite est incoherente (exposition inutile des interfaces admin/DB)
- les incidents sont detectes trop tard (alerting absent ou bruit excessif)
- les backups existent parfois, mais le restore n'est pas prouve

Impact business/ops: retard de livraison, perte de confiance, cout de maintenance eleve, risque de perte de donnees.

### Why Existing Solutions Fall Short

- Les guides "quick start" couvrent rarement le cycle complet exploitation + restauration.
- Les stacks communautaires sont souvent non opinionated sur la securite et la gouvernance des secrets.
- Beaucoup d'exemples visent la demo locale, pas un VPS distant operationnel.
- Les solutions HA sont pertinentes mais trop complexes pour un besoin mono-noeud initial.

### Proposed Solution

Un blueprint produit end-to-end, versionne, orientee execution:
- provisioning Ansible idempotent (OS, hardening, firewall, prerequis)
- acces administration via WireGuard (VPN-first)
- cluster K3s mono-noeud (Traefik, ServiceLB, local-path)
- deploiement applicatif via Argo CD App-of-Apps
- monitoring via kube-prometheus-stack + alertes email
- PostgreSQL standard en cluster, accessible uniquement via VPN
- backups combines (snapshot OVH + pg_dump + restore drill documente)

### Key Differentiators

- Security by default: interfaces admin et DB privees via VPN.
- Operational proof over promises: restore drill explicite des la V1.
- Reproducibility: architecture GitOps + Ansible rejouable.
- Pragmatic scope: mono-noeud assume, limites explicites, pas de sur-engineering.
- Upgrade discipline: pinning de versions et rollback simple.

## Target Users

### Primary Users

1. Ingenieur DevOps/SRE solo (homelab ou side-project)
- Cherche une plateforme simple, peu couteuse, mais serieuse operationnellement.
- A besoin de standardiser son setup sans construire un framework interne complet.
- Veut des procedures concretes de backup/restore et un monitoring utile.

2. Tech Lead d'une petite equipe produit
- Doit fournir un environnement de staging/preprod auto-heberge.
- Veut limiter les dependances cloud gerees au debut.
- Besoin prioritaire: vitesse de mise en place + gouvernance minimale.

### Secondary Users

1. Developpeur applicatif
- Consomme la plateforme pour deployer ses services via GitOps.
- Attend un chemin clair commit -> deploiement -> observabilite.

2. Responsable ops/owner produit
- Suit disponibilite, incidents et risque operationnel.
- Attend des indicateurs factuels pour decider d'evolution (MVP -> V2).

### User Journey

1. Discovery
- L'utilisateur identifie le besoin d'un socle infra auto-heberge exploitable.

2. Onboarding
- Il renseigne inventory/variables, lance Ansible et active WireGuard.

3. Core Usage
- Il deploie la stack de base K3s + Argo + monitoring + PostgreSQL.

4. Success Moment
- Premier deploiement applicatif reussi et alertes operationnelles actives.

5. Long-Term Value
- Il execute un restore drill valide et industrialise ses evolutions via GitOps.

## Success Metrics

### User Success Metrics

- Time-to-first-platform: plateforme fonctionnelle en moins de 2 heures apres provision VPS.
- Reproducibilite: 100% des runs Ansible critiques sans changement inattendu (idempotence).
- Exploitabilite: monitoring et alerting operationnels le jour 1.
- Confiance recovery: au moins un restore drill reussi par cycle de changement majeur.

### Business Objectives

- Reduire le cout d'entree d'une plateforme Kubernetes exploitable.
- Accelerer la mise a disposition d'un environnement de test/deploiement.
- Diminuer les incidents lies aux erreurs manuelles de configuration.
- Formaliser une base technique reutilisable pour futurs projets.

### Key Performance Indicators

- KPI-1: Temps moyen VPS nu -> cluster operationnel <= 120 min.
- KPI-2: Taux de deploiements GitOps sans intervention manuelle >= 95%.
- KPI-3: Taux d'alertes actionnables (non bruit) >= 80%.
- KPI-4: Taux de restore drill reussi = 100% sur environnement test.
- KPI-5: Nombre de secrets en clair dans Git = 0.

## MVP Scope

### Core Features

1. Provisioning Ansible baseline
- durcissement OS, SSH key only, UFW, prerequis systeme.

2. Securite reseau VPN-first
- WireGuard serveur/client et politique firewall associee.

3. Socle K3s mono-noeud
- installation K3s, Traefik, ServiceLB, stockage local-path.

4. GitOps Argo CD
- bootstrap Argo CD et structure App-of-Apps.

5. Monitoring et alerting
- kube-prometheus-stack + alertes email minimales.

6. PostgreSQL standard
- deploiement chart Helm, persistence locale, acces DB via VPN.

7. Backup and restore
- pg_dump + rotation + procedure restore testee.

### Out of Scope for MVP

- HA multi-node et external datastore.
- Stockage distribue type Longhorn.
- PITR/WAL archiving avance et DR multi-region.
- Exposition publique de PostgreSQL ou des interfaces admin.
- SSO/IdP avance pour les outils internes.

### MVP Success Criteria

- Toutes les etapes du plan de validation (1 a 7) sont executees avec preuves.
- Les ports publics restent limites a 22/80/443/51820.
- Argo CD sync automatique valide sur au moins un cycle de changement.
- Alertes critiques (indisponibilite/disque) testees et recues.
- Restore d'une base test valide sans ambiguite procedurelle.

### Future Vision

- Evolution vers architecture HA (multi-noeud + datastore externe).
- Adoption d'un operator PostgreSQL (CNPG) avec strategie backup avancee.
- Gouvernance securite et identite renforcee (OIDC/SSO, RBAC plus fin).
- Observabilite et operations avancees (logs centralises, SLO/SLA, runbooks enrichis).
- Industrialisation multi-environnements (dev/staging/prod) avec conventions GitOps.
