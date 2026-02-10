# Story 1.2: Garantir idempotence et execution par tags

Status: ready-for-dev

<!-- Note: Validation optionnelle. Utiliser le workflow de validation si besoin avant dev-story. -->

## Story

En tant que operateur,
Je veux rejouer les playbooks sans derive et cibler des domaines,
Afin de maintenir la plateforme sans effets de bord.

## Acceptance Criteria

1. Etant donne un environnement deja provisionne
   Quand le meme playbook est rejoue sans changement
   Alors aucun changement inattendu n'est applique
   Et la disponibilite des services n'est pas degradee.

2. Etant donne un besoin limite a un domaine
   Quand l'operateur lance une execution taggee
   Alors seuls les roles cibles sont executes
   Et les autres domaines restent inchanges.

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

- [Source: _bmad-output/planning-artifacts/epics.md#Garantir idempotence et execution par tags]
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
