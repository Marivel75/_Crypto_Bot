# Story 1.1: Provisionner le socle hote durci

Status: ready-for-dev

<!-- Note: Validation optionnelle. Utiliser le workflow de validation si besoin avant dev-story. -->

## Story

En tant que operateur,
Je veux lancer un playbook baseline sur un VPS neuf,
Afin de obtenir un hote securise pret pour le bootstrap cluster.

## Acceptance Criteria

1. Etant donne un VPS OVH neuf et un inventory Ansible valide
   Quand le playbook baseline est execute
   Alors SSH key-only est impose, root login est desactive et le firewall est actif
   Et les prerequis systeme sont installes correctement.

2. Etant donne la fin du provisioning baseline
   Quand les checks de conformite sont lances
   Alors les controles de hardening passent
   Et les preuves sont conservees pour audit.

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

- [Source: _bmad-output/planning-artifacts/epics.md#Provisionner le socle hote durci]
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
