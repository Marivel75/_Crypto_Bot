# Story 2.3: Mettre en place derive et rollback

Status: ready-for-dev

<!-- Note: Validation optionnelle. Utiliser le workflow de validation si besoin avant dev-story. -->

## Story

En tant que operateur,
Je veux detecter la derive et restaurer rapidement un etat valide,
Afin de contenir les regressions de configuration.

## Acceptance Criteria

1. Etant donne un changement manuel hors Git
   Quand Argo compare etat live et desired
   Alors la derive est marquee OutOfSync
   Et une resync permet le retour a l'etat cible.

2. Etant donne un commit de configuration defectueux
   Quand le commit est revert puis resync
   Alors l'etat precedent stable est restaure
   Et l'action est tracee avec correlation id.

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

- [Source: _bmad-output/planning-artifacts/epics.md#Mettre en place derive et rollback]
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
