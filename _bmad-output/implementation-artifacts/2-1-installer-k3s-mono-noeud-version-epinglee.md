# Story 2.1: Installer K3s mono-noeud version epinglee

Status: ready-for-dev

<!-- Note: Validation optionnelle. Utiliser le workflow de validation si besoin avant dev-story. -->

## Story

En tant que operateur,
Je veux installer K3s mono-noeud avec versions controlees,
Afin de obtenir une base cluster stable et reproductible.

## Acceptance Criteria

1. Etant donne un hote durci et accessible via VPN
   Quand le role bootstrap cluster est execute
   Alors K3s `v1.35.0+k3s3` est installe avec Traefik, ServiceLB et local-path
   Et les composants coeur deviennent sains.

2. Etant donne le cluster demarre
   Quand l'etat node/addons est verifie
   Alors le noeud est Ready
   Et les preuves de validation sont journalisees.

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

- Maintenir les versions epinglees K3s/Argo CD definies dans l'architecture.
- Appliquer le pattern GitOps App-of-Apps sans contournement manuel durable.
- Toute remediation de derive doit repasser par Git (source of truth).

### Project Structure Notes

- Respecter la separation de responsabilites: `infra/ansible`, `gitops`, `scripts`, `docs`.
- Conserver les conventions de nommage definies dans l'architecture.
- Aucun secret en clair dans les fichiers versionnes.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Installer K3s mono-noeud version epinglee]
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
