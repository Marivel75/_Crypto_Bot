# Story 4.2: Restreindre l'acces DB au reseau prive

Status: ready-for-dev

<!-- Note: Validation optionnelle. Utiliser le workflow de validation si besoin avant dev-story. -->

## Story

En tant que responsable plateforme,
Je veux bloquer les acces DB non autorises,
Afin de reduire le risque d'exposition donnees.

## Acceptance Criteria

1. Etant donne les network policies et regles firewall appliquees
   Quand une tentative d'acces non autorisee est faite
   Alors la connexion est refusee
   Et le port `5432` reste non public.

2. Etant donne une operation privilegiee DB
   Quand l'authentification/autorisation est evaluee
   Alors seuls les identifiants autorises passent
   Et acteur et horodatage sont traces.

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

- [Source: _bmad-output/planning-artifacts/epics.md#Restreindre l'acces DB au reseau prive]
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
