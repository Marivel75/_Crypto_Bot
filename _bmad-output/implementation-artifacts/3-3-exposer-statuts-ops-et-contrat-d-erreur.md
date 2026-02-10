# Story 3.3: Exposer statuts ops et contrat d'erreur

Status: ready-for-dev

<!-- Note: Validation optionnelle. Utiliser le workflow de validation si besoin avant dev-story. -->

## Story

En tant que operateur,
Je veux des endpoints de statut et erreurs standardises,
Afin de fiabiliser diagnostic et automatisation.

## Acceptance Criteria

1. Etant donne les endpoints `/health`, `/readiness`, `/backups/status`, `/restore/status`
   Quand ils sont appeles
   Alors les reponses suivent un schema stable avec horodatage
   Et le p95 health reste <= 2 secondes.

2. Etant donne une erreur validation/auth/dependance/timeout
   Quand la reponse est retournee
   Alors un code stable et un correlation id sont presents
   Et aucune information sensible n'est exposee.

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

- Conserver une alerting policy actionnable (dedup/inhibition/repeat control).
- Standardiser les contrats de statut/erreur avec correlation id.
- Aucune fuite de secret dans logs ou payloads d'erreur.

### Project Structure Notes

- Respecter la separation de responsabilites: `infra/ansible`, `gitops`, `scripts`, `docs`.
- Conserver les conventions de nommage definies dans l'architecture.
- Aucun secret en clair dans les fichiers versionnes.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Exposer statuts ops et contrat d'erreur]
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
