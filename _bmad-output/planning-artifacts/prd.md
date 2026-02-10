---
stepsCompleted:
  - step-01-init.md
  - step-02-discovery.md
  - step-03-success.md
  - step-05-domain.md
  - step-06-innovation.md
  - step-07-project-type.md
  - step-08-scoping.md
  - step-09-functional.md
  - step-10-nonfunctional.md
  - step-11-polish.md
  - step-12-complete.md
skippedSteps:
  - step-04-journeys.md
inputDocuments:
  - 'brainstorm.md'
  - '_bmad-output/planning-artifacts/product-brief-k3s-mono-pgsql-2026-02-10.md'
  - '_bmad-output/planning-artifacts/research/technical-k3s-mono-noeud-ovh-vpn-monitoring-postgresql-standard-research-2026-02-10.md'
workflowType: 'prd'
documentCounts:
  briefCount: 1
  researchCount: 1
  brainstormingCount: 1
  projectDocsCount: 0
classification:
  projectType: api_backend
  domain: general
  complexity: low
  projectContext: greenfield
author: 'Jules'
date: '2026-02-10'
---

# Product Requirements Document - K3s Mono-Noeud Ops Platform

**Author:** Jules
**Date:** 2026-02-10
**Project Type:** api_backend
**Note:** Ce projet ne contient pas de perimetre UX/UI. Les exigences concernent les capacites backend, operations et securite.

## Executive Summary

K3s Mono-Noeud Ops Platform fournit un socle d'hebergement auto-gere sur VPS OVH pour equipes techniques qui veulent deployer, observer et restaurer des services sans complexite HA prematuree.

Le produit doit livrer un chemin fiable et reproductible:
- VPS nu -> plateforme operationnelle
- securite admin/DB VPN-first
- exploitation GitOps standardisee
- supervision actionable avec alertes
- restauration verifiee par exercice reel

Le differenciateur principal est operationnel: preuve de restaurabilite et discipline d'exploitation des la V1.

## Success Criteria

### User Success

- Operateur peut provisionner un environnement complet en <= 120 minutes.
- Operateur peut relancer le provisioning sans derive de configuration non attendue.
- Operateur peut administrer les composants critiques sans exposition publique des interfaces admin/DB.
- Operateur peut executer un restore drill documente avec resultat reproductible.

### Business Success

- Reduction du temps de mise en route d'une plateforme technique standard.
- Reduction des incidents lies aux operations manuelles non versionnees.
- Base reutilisable pour nouveaux projets sans reconstruire le socle.

### Technical Success

- Flux commit -> sync -> etat cible fonctionne de maniere stable.
- Alertes critiques (disponibilite/disque) declenchees et recues sur canal email.
- Sauvegardes executes selon planning avec retention conforme.

### Measurable Outcomes

- MO-1: Temps VPS nu -> plateforme operationnelle <= 120 min.
- MO-2: Taux de runs Ansible sans changement inattendu >= 95% sur 5 executions consecutives.
- MO-3: Taux d'alertes actionnables >= 80% sur 30 jours.
- MO-4: Taux de restore drill reussi = 100% sur environnement test.
- MO-5: Nombre de secrets sensibles en clair dans Git = 0.

## Product Scope

### MVP - Minimum Viable Product

- Provisioning idempotent du VPS (hardening, firewall, prerequis).
- Acces prive via VPN pour administration et base de donnees.
- Orchestration mono-noeud operationnelle avec ingress et persistence locale.
- Deploiement declaratif des composants via GitOps.
- Monitoring + alerting email de niveau production legere.
- Base PostgreSQL standard avec sauvegarde et restauration testee.

### Growth Features (Post-MVP)

- Durcissement avance (rotation secrets, audit securite automatise).
- Evolution du socle donnees vers primitives ops plus avancees.
- Runbooks d'exploitation et SLO formels.
- Multi-environnements (dev/staging/prod) avec conventions unifiees.

### Vision (Future)

- Migration vers architecture haute disponibilite.
- Strategie disaster recovery et objectifs RPO/RTO contractualises.
- Observabilite et gouvernance a l'echelle multi-projets.

## API Backend Specific Requirements

### Project-Type Overview

Le produit est traite comme un backend d'orchestration et d'exploitation. Les exigences portent sur la gestion d'etat, l'acces securise, la supervision et les operations de sauvegarde/restauration.

Les sections UX/UI, design visuel et experience front sont explicitement hors perimetre.

### Endpoint Specs (`endpoint_specs`)

Le systeme doit exposer des capacites backend testables pour:
- etat de sante plateforme
- etat des composants critiques
- etat des sauvegardes
- etat de restauration

Exigences:
- ES-1: Le backend doit fournir un endpoint de health global retournant statut agrege et horodatage.
- ES-2: Le backend doit fournir un endpoint de readiness par composant critique.
- ES-3: Le backend doit fournir un endpoint de statut des dernieres sauvegardes.
- ES-4: Le backend doit fournir un endpoint de statut de dernier restore drill.

### Auth Model (`auth_model`)

- AM-1: Les operations d'administration backend doivent etre accessibles uniquement depuis le reseau VPN prive.
- AM-2: Le backend doit appliquer une authentification explicite pour les operations privilegiees.
- AM-3: Le backend doit tracer chaque action d'administration avec identite d'acteur et horodatage.
- AM-4: Les credentials d'administration ne doivent jamais etre stockes en clair dans le repository.

### Data Schemas (`data_schemas`)

- DS-1: Le systeme doit definir un schema pour les metadonnees de sauvegarde (id, timestamp, statut, taille, retention).
- DS-2: Le systeme doit definir un schema pour les evenements d'alerte (source, severite, timestamp, statut).
- DS-3: Le systeme doit definir un schema pour les traces d'operations critiques (action, acteur, resultat, duree).

### Error Codes (`error_codes`)

- EC-1: Les erreurs backend doivent etre classees en categories explicites (validation, autorisation, indisponibilite, timeout, dependance externe).
- EC-2: Chaque erreur doit fournir code stable, message actionnable et correlation id.
- EC-3: Les erreurs ne doivent pas exposer de secrets ni de details sensibles.

### Rate Limits (`rate_limits`)

- RL-1: Les endpoints backend critiques doivent supporter des limites de requetes configurables.
- RL-2: Le backend doit retourner un signal explicite en cas de depassement de limite.
- RL-3: Les limites doivent etre ajustables sans redeploiement complet du systeme.

### API Docs (`api_docs`)

- AD-1: Les endpoints backend doivent etre documentes avec entree/sortie, codes d'erreur et exemples.
- AD-2: La documentation doit inclure preconditions de securite (VPN, roles, droits).
- AD-3: La documentation doit decrire les scenarios de diagnostic et de remediation standards.

## Functional Requirements

### Provisioning & Baseline Operations

- FR1: Operateurs peuvent provisionner un environnement cible via une execution unique reproductible.
- FR2: Operateurs peuvent rejouer le provisioning sans perte d'etat operationnel.
- FR3: Operateurs peuvent executer des sous-ensembles de provisioning par domaine (reseau, orchestration, observabilite, base).
- FR4: Operateurs peuvent verifier automatiquement la conformite de baseline apres provisioning.

### Security & Access Control

- FR5: Operateurs peuvent administrer la plateforme via un canal prive chiffre.
- FR6: Operateurs peuvent restreindre l'exposition publique aux seuls ports necessaires au trafic applicatif et VPN.
- FR7: Operateurs peuvent garantir que les interfaces admin et la base de donnees ne sont pas accessibles depuis Internet public.
- FR8: Operateurs peuvent gerer les secrets d'exploitation sans stockage en clair dans les manifests versionnes.

### Deployment & Configuration Management

- FR9: Equipes peuvent decrire l'etat cible plateforme en mode declaratif versionne.
- FR10: Equipes peuvent declencher une synchronisation automatique entre etat Git et etat deploiement.
- FR11: Equipes peuvent suivre l'etat de convergence et diagnostiquer les ecarts de configuration.
- FR12: Equipes peuvent revenir a un etat precedent valide en cas de regression de configuration.

### Observability & Alerting

- FR13: Operateurs peuvent collecter metriques plateforme et composant de base de donnees.
- FR14: Operateurs peuvent visualiser la sante plateforme via tableaux de bord operationnels.
- FR15: Operateurs peuvent recevoir des alertes email sur indisponibilite et saturation disque.
- FR16: Operateurs peuvent reduire le bruit d'alerte via regroupement et repetition controles.

### Data Service Operations

- FR17: Operateurs peuvent deployer une instance PostgreSQL standard persistante dans le cluster.
- FR18: Operateurs peuvent acceder a PostgreSQL uniquement depuis le reseau prive d'administration.
- FR19: Operateurs peuvent verifier la persistence des donnees apres redemarrage service ou noeud.
- FR20: Operateurs peuvent monitorer l'etat de disponibilite de la base et ses signaux critiques.

### Backup & Recovery

- FR21: Operateurs peuvent executer des sauvegardes logiques periodiques avec retention definie.
- FR22: Operateurs peuvent verifier l'integrite et la presence des artefacts de sauvegarde.
- FR23: Operateurs peuvent executer un restore drill complet sur base de test vide.
- FR24: Operateurs peuvent mesurer et enregistrer la duree de restauration et la perte de donnees observee.

### Governance & Compliance Basics

- FR25: Equipes peuvent tracer les decisions d'exploitation majeures dans un journal versionne.
- FR26: Equipes peuvent lier chaque exigence critique a un critere de validation observables.
- FR27: Equipes peuvent auditer les changements de configuration ayant impacte la plateforme.

## Non-Functional Requirements

### Performance

- NFR-1: Les operations de verification de sante backend doivent repondre en <= 2 secondes pour le 95e percentile, mesurees sur 7 jours glissants.
- NFR-2: La synchronisation d'une modification de configuration critique doit etre visible en etat convergent en <= 5 minutes pour 95% des changements planifies.

### Security

- NFR-3: Les canaux d'administration doivent etre accessibles uniquement via reseau prive chiffre et controles d'acces actifs 100% du temps.
- NFR-4: Aucune credentielle critique ne doit apparaitre en clair dans le repository sur l'ensemble des revisions valides.
- NFR-5: Les journaux d'erreur ne doivent contenir aucun secret en clair sur 100% des evenements inspectes.

### Reliability

- NFR-6: Les composants critiques plateforme doivent maintenir une disponibilite >= 99.5% sur fenetre mensuelle.
- NFR-7: Les sauvegardes planifiees doivent atteindre un taux de succes >= 99% par mois.
- NFR-8: Le restore drill mensuel doit etre complete avec succes dans le RTO cible <= 60 minutes.

### Scalability

- NFR-9: Le socle doit supporter une augmentation x3 du volume de metriques sans rupture de collecte ni perte de series critiques.
- NFR-10: Le socle doit supporter une augmentation x2 du nombre de services deploies sans degradation > 15% du temps de convergence configuration.

### Integration

- NFR-11: Les integrations d'alerte email doivent conserver un taux de livraison >= 99% pour les alertes critiques.
- NFR-12: Les interfaces de supervision et d'administration doivent conserver des schemas de donnees compatibles entre versions mineures consecutives.

### Accessibility

- Hors perimetre explicite: aucun livrable interface utilisateur n'est requis dans ce projet.
- Les exigences d'interaction portent uniquement sur API/backend/operations.
