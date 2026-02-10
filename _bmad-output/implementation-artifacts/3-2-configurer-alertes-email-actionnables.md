# Story 3.2: Configurer alertes email actionnables

Status: ready-for-dev

<!-- Note: Validation optionnelle. Utiliser le workflow de validation si besoin avant dev-story. -->

## Story

En tant que operateur,
Je veux recevoir des alertes email critiques avec dedup,
Afin de etre notifie sans bruit inutile.

## Acceptance Criteria

1. Etant donne un SMTP configure de facon securisee
   Quand un incident critique est simule (node down ou disk pressure)
   Alors une alerte email est envoyee dans la fenetre attendue
   Et le message contient source, severite et correlation id.

2. Etant donne des alertes repetitives
   Quand les regles de grouping/inhibition s'appliquent
   Alors le spam d'alertes est reduit
   Et le comportement suit le runbook incident.

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

- [Source: _bmad-output/planning-artifacts/epics.md#Configurer alertes email actionnables]
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
