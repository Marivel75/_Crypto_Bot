# Story 5.1: Mettre en place backups planifies avec retention

Status: ready-for-dev

<!-- Note: Validation optionnelle. Utiliser le workflow de validation si besoin avant dev-story. -->

## Story

En tant que operateur,
Je veux des backups pg_dump planifies avec rotation,
Afin de disposer d'artefacts de restauration fiables.

## Acceptance Criteria

1. Etant donne la configuration de planification backup
   Quand la fenetre planifiee s'execute
   Alors des dumps horodates sont generes
   Et la retention supprime les sauvegardes expirees sans impact.

2. Etant donne un nouvel artefact backup
   Quand les verifications d'integrite tournent
   Alors les checks (taille/checksum/metadata) passent
   Et le statut backup est expose via endpoint ops.

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

- Backups et restore drills doivent produire des preuves exploitables (date, duree, resultat).
- Tracer les decisions ops et impacts via ADR/runbooks.
- Maintenir la matrice exigences -> validations a jour avant release.

### Project Structure Notes

- Respecter la separation de responsabilites: `infra/ansible`, `gitops`, `scripts`, `docs`.
- Conserver les conventions de nommage definies dans l'architecture.
- Aucun secret en clair dans les fichiers versionnes.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Mettre en place backups planifies avec retention]
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
