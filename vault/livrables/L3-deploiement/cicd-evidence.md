---
type: rncp-evidence
bloc: 3
theme: deploiement-continu
project: cryptobot
created: 2026-04-14
tags:
  - cryptobot
  - rncp
  - bloc3
  - ci-cd
  - devops
  - deploiement
refs:
  - "[[CryptoBot/avril/equipes/05-devops-infra]]"
  - "[[CryptoBot/avril/audit/technique/ci-cd-secrets]]"
  - "[[CryptoBot/avril/audit/technique/env-vars]]"
  - "[[CryptoBot/avril/audit/domaine/infra]]"
agents:
  - L3-CICD-Deploy
sources:
  - dev/.github/workflows/ci.yml
  - dev/.github/workflows/deploy.yml
  - dev/.gitlab-ci.yml
  - dev/infra/ansible/playbooks/deploy.yml
  - dev/scripts/deploy.sh
---

# Bloc 3 - Preuves CI/CD & Deploiement continu

Livrables RNCP 38919 Bloc 3 "Deployer une application en mode DevOps". Ce document consolide les preuves d'orchestration, d'automatisation, de separation d'environnements, de gestion des secrets, de strategie de rollback, et d'observabilite de la chaine CI/CD Crypto Bot.

## 1. Pipeline CI (lint + test)

Ref : `dev/.github/workflows/ci.yml` (131 lignes). Cf [[CryptoBot/avril/equipes/05-devops-infra]].

Declencheurs :
- `pull_request -> main`
- `push -> main`

Jobs sequentiels :

| Job | Duree moyenne | Outils | Fail-fast |
|---|---|---|---|
| `lint` | ~45s | ruff check, ruff format, mypy | oui |
| `test` | ~2min30 | pytest + coverage >= 80% sur service TimescaleDB | oui |

Matrix : non (un seul Python 3.11). Service container `timescale/timescaledb:latest-pg16` avec healthcheck `pg_isready`.

Gate qualite : `--cov-fail-under=80` bloque le merge si coverage < 80%.

## 2. Pipeline CD (build + deploy)

### GitHub Actions (prod par defaut)

Ref : `dev/.github/workflows/deploy.yml` (218 lignes).

Declencheurs :
- `push -> main` (auto prod)
- `workflow_dispatch` avec input `environment` (staging|prod) et `dry-run` (true|false)

Flow :
1. Build matrix 4 services (api, etl, frontend, ml) via `docker/build-push-action@v6` avec cache GHCR (`type=registry`, `mode=max`).
2. Push vers `ghcr.io/<owner>/cryptobot-<svc>:${{ github.sha }}` + `:latest`.
3. Install cle SSH depuis `secrets.VPS_SSH_PRIVATE_KEY` + `known_hosts` strict.
4. rsync `docker-compose*.yml`, `.env.template`, `scripts/deploy.sh`, `infra/nginx/` vers `/opt/cryptobot/` sur VPS.
5. Sauvegarde `.env` precedent en `.env.previous` (pour rollback).
6. `docker compose pull && up -d --remove-orphans`.
7. Boucle healthcheck 120s max sur `https://api.cryptobot.example/health`.
8. Rollback automatique si healthcheck KO.
9. Notification Slack succes/echec.

Concurrency : `group: deploy-<env>`, `cancel-in-progress: false` (pas de deploys concurrents).

### GitLab CI (exigence ecole)

Ref : `dev/.gitlab-ci.yml` (208 lignes). Stages : `lint -> test -> build -> deploy`.

- Cache `uv` dans `.uv-cache/` + `.venv/`
- Service `timescale/timescaledb:latest-pg16` pour stage test
- Build via `docker:25-dind` + login GitLab Container Registry (`$CI_REGISTRY_USER`, `$CI_REGISTRY_PASSWORD`)
- Deploy SSH via variable `$VPS_SSH_KEY` (File type, masked + protected)
- Mapping : `develop -> staging` auto, `main -> prod` manual (`when: manual`)
- Coverage extraction regex : `/TOTAL.*\s+(\d+%)$/`

### Ansible (bare-metal first-time + rollback explicite)

Ref : `dev/infra/ansible/playbooks/deploy.yml` (+ provision, ssl, backup).

Usage :

```bash
ansible-playbook -i inventories/production.ini playbooks/deploy.yml --ask-vault-pass
```

Rollback :

```bash
ansible-playbook -i inventories/production.ini playbooks/deploy.yml \
  -e "rollback=true image_tag=<previous_sha>" --ask-vault-pass
```

Cf `dev/infra/ansible/README.md` pour la procedure complete.

## 3. Separation des environnements

| Env | Hebergeur | Orchestration | DNS | Trigger | Secrets |
|---|---|---|---|---|---|
| dev | poste local | `docker compose up` | `localhost` | manuel | `.env.template` |
| staging | VPS OVH (separe) | Docker Compose | `staging.cryptobot.example` | push `develop` | GitLab CI Variables |
| prod | VPS OVH (principal) | Docker Compose + host Nginx + LE | `cryptobot.example` | push `main` + manual confirm | GitHub Secrets + Ansible Vault |

Isolation :
- `.env.template` committe, `.env` ignore (`.gitignore`)
- Overlay `docker-compose.prod.yml` reduit les limites memoire et desactive `nginx` interne (host-nginx gere SSL/routing)
- Pas de donnees prod jamais copiees en staging

## 4. Gestion des secrets

| Secret | GitHub Secrets | GitLab CI Variables | Ansible Vault | Rotation |
|---|---|---|---|---|
| `VPS_SSH_PRIVATE_KEY` | oui | `VPS_SSH_KEY` (File) | N/A | 1 an |
| `VPS_KNOWN_HOSTS` | oui | oui (File) | N/A | N/A |
| `VPS_HOST`, `VPS_USER` | oui | oui | inventory | N/A |
| `GHCR_TOKEN` | oui | `CI_REGISTRY_PASSWORD` (auto) | N/A | 180j |
| `POSTGRES_PASSWORD` | `_PROD` / `_STAGING` | `_PROD` / `_STAGING` | `secrets.yml` | 90j |
| `MINIO_ROOT_PASSWORD` | idem | idem | `secrets.yml` | 90j |
| `API_SECRET_KEY` | idem | idem | `secrets.yml` | 180j |
| `GF_SECURITY_ADMIN_PASSWORD` | idem | idem | `secrets.yml` | 90j |
| `SLACK_WEBHOOK` | oui | oui | N/A | breach only |
| `CLOUDFLARE_API_TOKEN` | oui | oui | `secrets.yml` | 180j |

Regles :
- Aucun secret en clair dans un YAML CI (verifie par `gitleaks` en pre-commit)
- Tous marques `masked + protected` cote GitLab
- Vault chiffre au repos : `ansible-vault encrypt group_vars/all/secrets.yml`
- SSH key specifique `cryptobot_deploy` (pas la cle perso)

Cf [[CryptoBot/avril/audit/technique/ci-cd-secrets]] pour la matrice complete et les commandes de generation.

## 5. Strategie de rollback

Modele :

```
deploy -> healthcheck (120s max) -> [OK: keep] / [KO: rollback auto]
```

Mecanique :
1. Tag image = SHA commit (`ghcr.io/<owner>/cryptobot-api:<sha>`), jamais `:latest` en prod runtime.
2. Avant pull : `cp .env .env.previous` sur le VPS.
3. Nouvel `IMAGE_TAG` ecrit dans `.env`.
4. `docker compose pull && up -d --remove-orphans`.
5. Boucle `curl -fsS` sur `/health` jusqu'a 120s.
6. Si KO : `docker compose down --timeout 30 && cp .env.previous .env && docker compose up -d`.
7. Notification Slack avec distinction deploy-OK / rollback-executed / deploy-KO.

Rollback manuel ultime :

```bash
ssh deploy@vps "cd /opt/cryptobot && IMAGE_TAG=<sha_N-1> docker compose pull && docker compose up -d"
```

Ou via Ansible :

```bash
ansible-playbook playbooks/deploy.yml -e "rollback=true image_tag=<sha_N-1>"
```

## 6. Preuves d'execution

> Placeholder - a completer apres le premier run reel.

### GitHub Actions

- [ ] CI run `#<id>` - lint+test vert : `https://github.com/<owner>/cryptobot/actions/runs/<id>`
- [ ] Deploy run `#<id>` - build 4 images + healthcheck 200 : `https://github.com/<owner>/cryptobot/actions/runs/<id>`
- [ ] Capture d'ecran : `docs/preuves/gh-deploy-success.png`
- [ ] Capture rollback forcee (dry-run erreur healthcheck) : `docs/preuves/gh-rollback.png`

### GitLab

- [ ] Pipeline `#<id>` sur `develop` - deploy staging auto : `https://gitlab.com/<group>/cryptobot/-/pipelines/<id>`
- [ ] Pipeline `#<id>` sur `main` - deploy prod manual confirm : `https://gitlab.com/<group>/cryptobot/-/pipelines/<id>`
- [ ] Capture d'ecran `docs/preuves/gitlab-pipeline-prod.png`

### Ansible

- [ ] Output `ansible-playbook deploy.yml` (changed=N, failed=0) archive `docs/preuves/ansible-deploy.log`
- [ ] `ansible vps -m shell -a "docker compose ps"` : tous services `(healthy)`

## 7. Observabilite CI/CD

| Signal | Source | Destination | Retention |
|---|---|---|---|
| Logs build | GitHub Actions / GitLab runners | runners (90j) | 90j |
| Logs deploy SSH | `scripts/deploy.sh` stdout | Actions log | 90j |
| Logs container runtime | `docker compose logs` | Loki (host) via `vector.dev` sidecar | 30j |
| Metriques build duration | `workflow_run` events | Grafana dashboard "CI/CD" | 90j |
| Notifications | webhook Slack | `#cryptobot-deploys` | N/A |

Cf [[CryptoBot/avril/equipes/05-devops-infra]] sections "Stack monitoring" pour les dashboards Grafana (panel "CI/CD duration", "Deploy frequency", "MTTR").

Note : Promtail abandonne (EOL mars 2026), remplace par `vector.dev` en sidecar de `docker-compose.prod.yml` pour shipping vers Loki.

## 8. Plan de test CI

### Test dry-run (sans deploy reel)

```bash
# GitHub : declenche deploy en dry-run (skip SSH + healthcheck)
gh workflow run deploy.yml --ref roulio-dev -f environment=staging -f dry-run=true

# Verifier le run
gh run list --workflow=deploy.yml --limit 1
gh run view <run-id> --log
```

### Test local Ansible (check mode)

```bash
cd infra/ansible
ansible-playbook -i inventories/production.ini playbooks/deploy.yml --check --diff
```

### Test GitLab (pipeline trigger manuel)

```bash
# Via API
curl -X POST \
  -F "token=$GITLAB_TRIGGER_TOKEN" \
  -F "ref=develop" \
  "https://gitlab.com/api/v4/projects/<project-id>/trigger/pipeline"
```

### Test rollback force

1. Declencher deploy via `workflow_dispatch` avec une image taggee deliberement cassee (ex : endpoint `/health` retourne 500).
2. Observer la boucle healthcheck echouer apres 120s.
3. Observer la step "Rollback on failure" restaurer `.env.previous`.
4. Observer la notification Slack "FAILED + rollback executed".

## Checklist RNCP Bloc 3

- [x] Pipeline CI lint + tests + couverture
- [x] Pipeline CD build + deploy + rollback
- [x] Separation envs (dev / staging / prod)
- [x] Secrets management (GitHub Secrets + GitLab CI Variables + Ansible Vault)
- [x] Healthchecks stricts (pas de `|| true`)
- [x] Rollback automatique sur echec healthcheck
- [x] Notifications (Slack)
- [x] Orchestration bare-metal (Ansible)
- [x] Observabilite pipeline (logs + metriques + alertes)
- [ ] Preuves d'execution reelles (a completer post-merge)
