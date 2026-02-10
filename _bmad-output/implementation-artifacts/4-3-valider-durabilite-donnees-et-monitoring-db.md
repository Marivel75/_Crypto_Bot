# Story 4.3: Valider durabilite donnees et monitoring DB

Status: ready-for-dev

<!-- Note: Validation optionnelle. Utiliser le workflow de validation si besoin avant dev-story. -->

## Story

En tant que operateur,
Je veux prouver la persistence apres redemarrage et surveiller la DB,
Afin de confirmer la fiabilite du service.

## Acceptance Criteria

1. Etant donne un jeu de donnees de test present
   Quand le pod DB ou le noeud est redemarre
   Alors les donnees persistent apres reprise
   Et le resultat est documente.

2. Etant donne les metriques DB branchees au monitoring
   Quand un scenario de stress/incident est simule
   Alors les signaux critiques sont visibles sur dashboard
   Et les alertes attendues se declenchent.

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

- [Source: _bmad-output/planning-artifacts/epics.md#Valider durabilite donnees et monitoring DB]
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
