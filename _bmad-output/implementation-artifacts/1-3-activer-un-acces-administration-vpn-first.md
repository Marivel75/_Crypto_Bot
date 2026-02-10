# Story 1.3: Activer un acces administration VPN-first

Status: ready-for-dev

<!-- Note: Validation optionnelle. Utiliser le workflow de validation si besoin avant dev-story. -->

## Story

En tant que operateur,
Je veux administrer la plateforme uniquement via WireGuard,
Afin de eviter toute exposition internet des surfaces sensibles.

## Acceptance Criteria

1. Etant donne la configuration serveur/client WireGuard appliquee
   Quand un client autorise se connecte
   Alors les interfaces admin privees sont accessibles via VPN
   Et l'acces est refuse hors VPN.

2. Etant donne un scan depuis internet public
   Quand les ports sont verifies
   Alors seuls `22/80/443/51820` sont ouverts
   Et PostgreSQL et les interfaces admin ne sont pas exposes.

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

- [Source: _bmad-output/planning-artifacts/epics.md#Activer un acces administration VPN-first]
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
