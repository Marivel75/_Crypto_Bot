# Story 1.4: Initialiser la gestion des secrets chiffres

Status: ready-for-dev

<!-- Note: Validation optionnelle. Utiliser le workflow de validation si besoin avant dev-story. -->

## Story

En tant que ingenieur plateforme,
Je veux stocker les secrets via SOPS+age,
Afin de eliminer les secrets en clair dans Git.

## Acceptance Criteria

1. Etant donne des fichiers secrets infra/cluster
   Quand ils sont commites
   Alors les valeurs sont chiffrees avec age et metadata SOPS
   Et la lecture en clair requiert une cle autorisee.

2. Etant donne les controles CI secrets
   Quand un secret en clair est detecte
   Alors la pipeline echoue
   Et le merge est bloque jusqu'a correction.

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

- Respecter les roles Ansible existants dans `infra/ansible/roles/`.
- Ne jamais exposer d'interface admin ou DB hors VPN (policy ports publics limites).
- Secrets obligatoirement geres via SOPS+age; aucun secret en clair dans Git.

### Project Structure Notes

- Respecter la separation de responsabilites: `infra/ansible`, `gitops`, `scripts`, `docs`.
- Conserver les conventions de nommage definies dans l'architecture.
- Aucun secret en clair dans les fichiers versionnes.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Initialiser la gestion des secrets chiffres]
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
