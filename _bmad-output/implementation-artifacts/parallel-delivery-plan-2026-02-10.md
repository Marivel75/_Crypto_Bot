# Plan De Livraison Parallele - k3s-mono-pgsql

Date: 2026-02-10
Scope: fonctionnel uniquement

## 1) Vision execution

Objectif: livrer vite sans casser la prod en respectant les verrous techniques.

Verrous critiques (gates):
1. Story 1.1 (baseline hardening) est le gate d'entree.
2. Story 2.2 (Argo App-of-Apps) est le gate d'acceleration.
3. Story 4.1 (PostgreSQL persistant) est le gate data.
4. Story 5.1 (backups) est le gate recovery avant 5.2.

Chemin critique:
`1.1 -> 1.3 -> 2.1 -> 2.2 -> 4.1 -> 5.1 -> 5.2`

## 2) Stories parallelisables

Apres 1.1:
- 1.3, 1.4, 2.4, 5.3

Apres 1.3 + 1.4:
- 1.2

Apres 2.2:
- 2.3, 3.1, 3.3, 4.1

Apres 3.1:
- 3.2

Apres 4.1:
- 4.2, 4.3, 5.1

Apres 5.1:
- 5.2

Peut tourner en flux quasi continu:
- 5.4 (documentation/matrice, finalisation en fin de lot)

## 3) Plan 2 dev

Dev A (critical path):
- 1.1 -> 1.3 -> 2.1 -> 2.2 -> 4.1 -> 5.1 -> 5.2

Dev B (support + hardening):
- 1.4 -> 1.2 -> 2.4 -> 2.3 -> 3.1 -> 3.2 -> 4.2 -> 4.3 -> 5.3 -> 5.4

Rythme:
- Sprint 1: Epic 1 complet
- Sprint 2: Epic 2 + 3.1
- Sprint 3: Epic 4 + 5.1
- Sprint 4: 5.2 + 5.3 + 5.4 + stabilisation

## 4) Plan 3 dev (recommande)

Dev A (platform core):
- 1.1 -> 1.3 -> 2.1 -> 2.2 -> 2.3

Dev B (security + compliance):
- 1.4 -> 1.2 -> 2.4 -> 4.2 -> 5.3 -> 5.4

Dev C (observability + data + recovery):
- 3.1 -> 3.2 -> 3.3 -> 4.1 -> 4.3 -> 5.1 -> 5.2

Gain attendu:
- meilleur throughput apres gate 2.2
- reduction du risque "single-thread" sur recovery

## 5) Plan 4 dev (mode rocket)

Dev A:
- 1.1 -> 2.1 -> 2.2

Dev B:
- 1.3 -> 1.4 -> 1.2 -> 2.4

Dev C:
- 3.1 -> 3.2 -> 3.3

Dev D:
- 4.1 -> 4.2 -> 4.3 -> 5.1 -> 5.2

En fil rouge:
- 5.3 + 5.4 par Dev B/C selon charge

## 6) Points de controle (Definition of Progress)

Checkpoint A:
- 1.1, 1.3, 1.4 done
- preuves hardening + VPN + secrets

Checkpoint B:
- 2.1, 2.2, 2.4 done
- GitOps stable + gates CI actives

Checkpoint C:
- 3.1, 3.2, 4.1, 4.2 done
- monitoring + alerting + DB privee

Checkpoint D:
- 5.1, 5.2 done
- backup/restore drill valide

## 7) Regles anti-chaos

- Pas de merge sans preuve AC.
- Pas de bypass GitOps durable.
- Tout incident critique => correction + runbook.
- Story en `review` obligatoire avant `done`.

## 8) Execution immediate proposee

Si go maintenant:
1. Lancer Dev A sur 1.1.
2. Preparer Dev B sur 1.4 (branche + variables + secrets).
3. Preparer Dev C sur 3.1 (monitoring values + alert routes).
4. Passer en full parallele des que 1.1 est validee.
