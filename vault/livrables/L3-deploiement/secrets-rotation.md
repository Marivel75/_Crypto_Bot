---
type: rncp
bloc: 3
competence: C3.4-C3.5
source: .env.example + audit/technique/ci-cd-secrets.md
tags: [cryptobot, rncp, bloc3, secrets, rotation, ansible-vault, ci-cd]
created: 2026-04-14
ingested_by: L3-Containers-Sec
certif: RNCP38919
---

# Rotation des secrets — Procedures & runbook

Livrable Bloc 3 — Deployer et securiser. Reference [[../../audit/technique/ci-cd-secrets]], [[../../audit/technique/env-vars]], [[CryptoBot/avril/rncp/livrables/L3-deploiement/container-images]], [[CryptoBot/avril/rncp/livrables/L3-deploiement/rgpd-compliance]].

## 1. Inventaire des secrets

Source de verite : `/home/jules/Documents/3-git/CryptoBot/dev/.env.example` + `[[../../audit/technique/ci-cd-secrets]]`. Total **14 secrets** (9 core + 5 CI/CD/deploy).

| # | Secret | Service concerne | Mode stockage dev | Mode stockage prod | TTL / Rotation |
|---|--------|-----------------|-------------------|--------------------|----------------|
| 1 | `POSTGRES_PASSWORD` | timescaledb, api, etl, ml, mlflow, postgres-exporter | `.env` local | Ansible Vault + GitHub Secrets (`POSTGRES_PASSWORD_PROD`) | **90 jours** |
| 2 | `POSTGRES_USER` | idem | `.env` (non sensible mais pair) | idem | Static (never) |
| 3 | `MINIO_ROOT_PASSWORD` | minio, mlflow, api (via AWS creds) | `.env` | GitHub Secrets (`MINIO_ROOT_PASSWORD_PROD`) | **90 jours** |
| 4 | `MINIO_ROOT_USER` | idem | `.env` | idem | Static (default `minioadmin`) |
| 5 | `API_SECRET_KEY` | api (JWT HS256 signing) | `.env` | GitHub Secrets (`API_SECRET_KEY_PROD`) | **180 jours** — dual-key rollover |
| 6 | `AWS_ACCESS_KEY_ID` | mlflow, api (alias MinIO) | `.env` | suit `MINIO_ROOT_USER` | suit MinIO |
| 7 | `AWS_SECRET_ACCESS_KEY` | idem | `.env` | suit `MINIO_ROOT_PASSWORD` | suit MinIO |
| 8 | `GF_SECURITY_ADMIN_PASSWORD` | grafana | `.env` | GitHub Secrets (`GF_SECURITY_ADMIN_PASSWORD_PROD`) | **90 jours** |
| 9 | `COINGECKO_API_KEY` | etl (collector) | `.env` | GitHub Secrets | **365 jours** ou revoke CoinGecko |
| 10 | `OPENAI_API_KEY` | api (chat LLM, opt-in) | `.env` | GitHub Secrets | **90 jours** ou quarterly |
| 11 | `ANTHROPIC_API_KEY` | api (chat LLM, alternative) | `.env` | GitHub Secrets | **90 jours** |
| 12 | `VPS_SSH_PRIVATE_KEY` | GitHub Actions deploy | N/A | GitHub Secrets (4096-bit RSA) | **365 jours** |
| 13 | `VPS_SSH_PASSPHRASE` | idem (si key chiffree) | N/A | GitHub Secrets | **365 jours** |
| 14 | `SLACK_WEBHOOK_URL` (optionnel alerting) | api / Grafana | `.env` | GitHub Secrets | ad-hoc (rotation si compromission) |

Secrets **non-sensibles** (pairs pour identification) : `POSTGRES_USER`, `POSTGRES_DB`, `MINIO_ROOT_USER`, `API_HOST`, `API_PORT`, `MLFLOW_TRACKING_URI`, `MLFLOW_S3_ENDPOINT_URL`, `MINIO_ENDPOINT`, `API_URL`, `CORS_ORIGINS`, `LOG_LEVEL`, `JWT_EXPIRATION_HOURS` — versionnables dans `.env.example`.

## 2. Stockage

### 2.1 Developpement local

- Fichier `.env` a la racine du repo.
- **`.gitignore`** contient `.env`, `.env.local`, `.env.production`, `*.vault` → jamais commit.
- Permissions : `chmod 600 .env` (lecture proprio uniquement).
- Pre-commit hook `gitleaks` (voir §5).

### 2.2 Production (VPS)

Trois options combinees, par ordre de preference :

1. **Ansible Vault** : `infra/ansible/group_vars/production/vault.yml` chiffre AES-256-CTR.
   ```bash
   ansible-vault create infra/ansible/group_vars/production/vault.yml
   ansible-vault edit infra/ansible/group_vars/production/vault.yml
   ansible-playbook -i infra/ansible/inventories/production.ini deploy.yml \
     --ask-vault-pass
   ```
   Mot de passe vault dans GitHub Secret `ANSIBLE_VAULT_PASSWORD`.

2. **GitHub Secrets** (CI/CD GitHub Actions) : repository → Settings → Secrets. Encrypt at rest, accessible uniquement via `${{ secrets.NAME }}` dans workflows. Logs runners automatiquement masked.

3. **GitLab CI variables** (projet ecole impose) : variables "masked" + "protected" (protected = push vers branche protegee seulement). Jamais de `printf` ou `env | grep` dans un job.

Le playbook Ansible materialise `.env` sur le VPS a partir des variables vault :
```yaml
- name: Generate .env from vault
  ansible.builtin.template:
    src: env.j2
    dest: /opt/cryptobot/.env
    owner: deploy
    group: deploy
    mode: '0600'
  no_log: true   # jamais dans logs Ansible
```

## 3. Rotation planifiee

### 3.1 Calendrier par type de secret

| Categorie | Frequence | Declencheur | Procedure |
|-----------|-----------|-------------|-----------|
| Mot de passe DB (`POSTGRES_PASSWORD`, `MINIO_ROOT_PASSWORD`, `GF_SECURITY_ADMIN_PASSWORD`) | 90j | cron calendrier | §4 procedure DB |
| JWT signing key (`API_SECRET_KEY`) | 180j | cron calendrier | §7 dual-key |
| API keys tiers (`OPENAI`, `ANTHROPIC`, `COINGECKO`) | 90j | calendrier ou breach tiers | Regenerate chez le fournisseur + MAJ vault |
| SSH deploy (`VPS_SSH_PRIVATE_KEY`) | 365j | calendrier | `ssh-keygen -t ed25519 -f cryptobot_deploy_new` + ajout `authorized_keys` avant revoke ancien |
| Webhook (`SLACK_WEBHOOK_URL`) | ad-hoc | breach suspecte | Revoke Slack admin + nouveau webhook |

Calendrier materialise dans `.github/workflows/rotation-reminder.yml` (cron mensuel, cree issue `secret-rotation-due`).

### 3.2 Entree d'agenda type

```
90j POSTGRES_PASSWORD :
  - 2026-04-14 (initial)
  - 2026-07-13
  - 2026-10-11
  - 2027-01-09
180j API_SECRET_KEY :
  - 2026-04-14 (initial)
  - 2026-10-11
  - 2027-04-09
```

## 4. Procedure rotation `POSTGRES_PASSWORD` (zero-downtime)

Objectif : changer le password PostgreSQL sans interrompre l'API. Pattern "create-new → switch → revoke-old".

```bash
# 1. Generer nouveau password (32 chars base64 url-safe)
NEW_PASS=$(openssl rand -base64 24)
echo "$NEW_PASS"   # a stocker temporairement

# 2. Creer un nouveau user ou changer le password atomiquement
docker compose exec timescaledb psql -U cryptobot -d cryptobot -c \
  "ALTER USER cryptobot WITH PASSWORD '$NEW_PASS';"

# Option B (plus safe) : creer cryptobot_v2, grant les memes droits,
# basculer, puis drop cryptobot.
docker compose exec timescaledb psql -U postgres -c \
  "CREATE USER cryptobot_v2 WITH PASSWORD '$NEW_PASS';
   GRANT ALL PRIVILEGES ON DATABASE cryptobot TO cryptobot_v2;
   GRANT ALL ON ALL TABLES IN SCHEMA public TO cryptobot_v2;
   GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO cryptobot_v2;"

# 3. Mettre a jour Ansible Vault + GitHub Secrets
ansible-vault edit infra/ansible/group_vars/production/vault.yml
# -> vault_postgres_password: "<NEW_PASS>"
gh secret set POSTGRES_PASSWORD_PROD --body "$NEW_PASS"

# 4. Deployer le nouveau .env (pas de rebuild image necessaire)
ansible-playbook deploy.yml --tags env --ask-vault-pass

# 5. Rolling restart des services consommateurs (api, etl, ml, mlflow, postgres-exporter)
docker compose up -d --force-recreate api etl-worker ml-worker mlflow postgres-exporter

# 6. Verifier healthchecks
docker compose ps --format "{{.Name}} {{.Status}}"
curl -f https://crypto-bot.example.com/api/v1/health

# 7. Revoker l'ancien user (option B)
docker compose exec timescaledb psql -U postgres -c "DROP USER cryptobot;"
# Renommer cryptobot_v2 en cryptobot si souhaite
```

Downtime estime : **0 seconde** (option A : redemarrage en rolling avec `depends_on: service_healthy`). ~5 secondes d'erreurs 500 tolerees si redemarrage simultane, sinon 0.

Backup pre-rotation obligatoire : `pg_dump > backups/pre-rotation-$(date +%F).sql.gz` (cf `infra/scripts/rollback.sh`).

## 5. Detection de compromission

### 5.1 Pre-commit — gitleaks

`.pre-commit-config.yaml` :
```yaml
- repo: https://github.com/gitleaks/gitleaks
  rev: v8.18.0
  hooks:
    - id: gitleaks
      name: Detect hardcoded secrets
```

Regles custom pour secrets projet (`.gitleaks.toml`) :
```toml
[[rules]]
id = "cryptobot-postgres-password"
description = "Postgres password hardcoded"
regex = '''POSTGRES_PASSWORD\s*=\s*[^C]'''   # tolere CHANGE_ME* uniquement
[[rules]]
id = "jwt-secret"
regex = '''API_SECRET_KEY\s*=\s*[A-Za-z0-9+/=]{20,}'''
```

### 5.2 CI — scan secrets a chaque push

`.github/workflows/security-scan.yml` :
```yaml
- uses: gitleaks/gitleaks-action@v2
  env:
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

+ `trufflehog filesystem --no-verification .` en fallback.

### 5.3 GitHub Secret Scanning

Active par defaut sur le repo (public ou Advanced Security) : detecte automatiquement les tokens connus (AWS, Stripe, OpenAI, Anthropic, Slack). Alerte par email admin + notification push.

### 5.4 Monitoring runtime

Grafana alerte sur :
- pattern `password|secret|api_key` dans logs Loki (query LogQL `{service="api"} |~ "(?i)(password|api_key)=[^ ]+"`)
- echecs d'auth > 10/min sur `/api/v1/auth/login` (metrique `auth_login_failures_total`)

## 6. Post-incident — checklist breach

En cas de fuite soupconnee :

1. **Isoler** : `docker compose stop api frontend` si compromission API confirmee.
2. **Revoker** le secret compromis chez l'emetteur :
   - DB : `ALTER USER ... WITH PASSWORD '<new>'` immediat
   - OpenAI / Anthropic : UI console → revoke key
   - GitHub deploy key : `/settings/keys` → delete
   - Cloudflare : `Tokens` → revoke
3. **Rotation** de tous les secrets derives (ex: fuite `.env` → rotation des 14 secrets).
4. **Audit** : parcourir logs `audit_events` 90 derniers jours : qui a utilise quoi, a partir de quel IP hash.
5. **Notification utilisateurs** (art. 33-34 RGPD) : si donnees perso impactees, informer sous **72h** via email + banniere plateforme. CNIL notifiee via teleservice.
6. **Post-mortem** : document `docs/incidents/INC-<YYYY-MM-DD>-breach.md` avec timeline, cause racine, actions correctives.
7. **Rotation preventive** des credentials associes (sessions actives JWT : forcer expiration via rotation `API_SECRET_KEY`, cf §7).

## 7. Zero-downtime rotation `API_SECRET_KEY` — pattern dual-key

Specifique JWT HS256 : une rotation naive invalide **toutes** les sessions actives. Pattern dual-key accepte ancien + nouveau token pendant une fenetre de transition.

### 7.1 Config Pydantic etendue

```python
# src/shared/config.py (extrait cible Phase 2)
class Settings(BaseSettings):
    api_secret_key: SecretStr              # Signing key actuelle (emission)
    api_secret_key_previous: SecretStr | None = None   # Verification seulement
    jwt_expiration_hours: int = 24
```

### 7.2 Verification multi-key

```python
# src/api/dependencies/auth.py
def decode_jwt(token: str) -> dict:
    keys_to_try = [settings.api_secret_key.get_secret_value()]
    if settings.api_secret_key_previous:
        keys_to_try.append(settings.api_secret_key_previous.get_secret_value())
    for key in keys_to_try:
        try:
            return jwt.decode(token, key, algorithms=["HS256"])
        except jwt.InvalidSignatureError:
            continue
    raise HTTPException(401, "Invalid token")
```

### 7.3 Procedure

| T+ | Action |
|----|--------|
| T=0 | `API_SECRET_KEY_PREVIOUS = API_SECRET_KEY` ; `API_SECRET_KEY = <new>` ; deploy |
| T=0 | Tokens emis depuis T=0 signes avec la nouvelle ; tokens anciens verifies avec previous |
| T+24h | `JWT_EXPIRATION_HOURS=24` garantit l'expiration naturelle des tokens anciens |
| T+26h | Suppression de `API_SECRET_KEY_PREVIOUS` ; redeploy |
| T+26h | Toute token emis avant T=0 est invalide (mais tous expires de toute facon) |

Downtime : **0s**. Aucun user force deconnecte.

Procedure utilisable en mode **emergency** (T+0 a T+26h reduit a T+0 a T+5min si breach confirme, en acceptant la deconnexion forcee).

## Sources

- `/home/jules/Documents/3-git/CryptoBot/dev/.env.example` (41 l) — 14 secrets identifies
- [[../../audit/technique/ci-cd-secrets]] — secrets GitHub Actions requis
- [[../../audit/technique/env-vars]] — guide variables d'environnement
- [[../../audit/remediation/phase1]] (S1-S3 : defaults supprimes, fail-fast startup)

Lies : [[CryptoBot/avril/rncp/livrables/L3-deploiement/container-images]] | [[CryptoBot/avril/rncp/livrables/L3-deploiement/rgpd-compliance]].
