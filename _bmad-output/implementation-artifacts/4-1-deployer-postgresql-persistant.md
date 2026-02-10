# Story 4.1: Deployer PostgreSQL persistant

Status: ready-for-dev

<!-- Note: Validation optionnelle. Utiliser le workflow de validation si besoin avant dev-story. -->

## Story

En tant que operateur,
Je veux deployer PostgreSQL via chart epingle avec PVC,
Afin de fournir un service donnees stable.

## Acceptance Criteria

1. Etant donne les manifests postgres gitops prets
   Quand la release est synchronisee
   Alors le chart `17.0.2` est deploye avec succes
   Et les PVC local-path sont bien relies.

2. Etant donne la fin de deploiement
   Quand les probes de readiness sont verifiees
   Alors PostgreSQL est joignable par les workloads autorises
   Et les credentials proviennent de secrets chiffres.

## Tasks / Subtasks

- [ ] Valider les preconditions techniques et metier de la story (AC: #1, 2)
  - [ ] Verifier les contraintes PRD/Architecture liees a cette story
- [ ] Implementer les changements necessaires pour satisfaire les AC (AC: #1, 2)
  - [ ] Appliquer les modifications dans les bons repertoires (`infra/`, `gitops/`, `scripts/`, `docs/`)
- [ ] Ajouter/mettre a jour la verification fonctionnelle de la story (AC: #1, 2)
  - [ ] Capturer les preuves d'execution (logs, sorties commandes, etat ressources)
- [ ] Mettre a jour la documentation operationnelle impactee (AC: #1, 2)
  - [ ] Completer runbook/ADR si decision non triviale

## Dev Notes

- PostgreSQL reste prive (VPN/NetworkPolicy), jamais expose publiquement.
- Verifier persistence locale et comportement apres restart pod/noeud.
- Coordonner metriques DB avec monitoring stack existante.

### Project Structure Notes

- Respecter la separation de responsabilites: `infra/ansible`, `gitops`, `scripts`, `docs`.
- Conserver les conventions de nommage definies dans l'architecture.
- Aucun secret en clair dans les fichiers versionnes.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Deployer PostgreSQL persistant]
- [Source: _bmad-output/planning-artifacts/prd.md]
- [Source: _bmad-output/planning-artifacts/architecture.md]
- [Source: _bmad-output/planning-artifacts/test-design-k3s-mono-pgsql-2026-02-10.md]

## Dev Agent Record

### Agent Model Used

gpt-5.3-codex

### Debug Log References

- N/A

### Completion Notes List

- Story context cree automatiquement a partir des artefacts valides.
- Story marquee ready-for-dev pour execution par dev-story.

### File List

- A completer par l'agent de developpement.
