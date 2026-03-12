# 05 — Equipe DevOps / Infra

> **Lisez d'abord** `docs/00-overview.md` pour le contexte global du projet.

---

## Votre perimetre

Vous etes responsables de **tout ce qui fait tourner le projet** : Docker, CI/CD, Nginx, monitoring, backups.

| Vous gerez | Vous NE gerez PAS |
|-----------|-------------------|
| `docker-compose.yml` et tous les Dockerfiles | Le code applicatif (chaque equipe gere le sien) |
| Nginx (reverse proxy, HTTPS) | Les endpoints API (equipe Backend) |
| GitHub Actions (CI/CD pipeline) | Les modeles ML (equipe ML) |
| Monitoring et alertes systeme | Le schema BDD (equipe Data Eng) |
| Backups | L'interface utilisateur (equipe Frontend) |
| Configuration du VPS OVH | |
| `.env.example` et gestion des secrets | |
| **Ansible** (provisioning et deploiement) | |
| **IaC** (infrastructure as code) | |

**Votre code va dans** : racine du projet (`docker-compose.yml`, `infra/`, `.github/workflows/`)
**Votre branche** : `devops/xxx`

---

## Ce que les autres equipes attendent de vous

| Equipe | Ce qu'elle attend | Interface |
|--------|------------------|-----------|
| **Toutes** | `docker-compose up -d` doit tout lancer sans config manuelle | `docker-compose.yml` + `.env.example` |
| **Toutes** | CI/CD qui lint, teste et deploie automatiquement | `.github/workflows/ci.yml` |
| **Data Eng** | TimescaleDB et MinIO accessibles dans le reseau Docker | Services `timescaledb` et `minio` |
| **Backend** | Nginx route le trafic HTTPS vers FastAPI | Config Nginx |
| **Frontend** | Nginx route le trafic HTTPS vers Streamlit | Config Nginx |
| **ML** | MLflow accessible dans le reseau Docker | Service `mlflow` |

---

## Architecture Docker

### docker-compose.yml

```yaml
version: "3.8"

services:
  # ========================
  # REVERSE PROXY
  # ========================
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro          # Certs Let's Encrypt
    depends_on:
      - api
      - frontend
    networks:
      - frontend-net
    restart: unless-stopped

  # ========================
  # BACKEND API
  # ========================
  api:
    build: ./src/api
    env_file: .env
    depends_on:
      - timescaledb
    networks:
      - frontend-net
      - backend-net
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 5s
      retries: 3

  # ========================
  # FRONTEND
  # ========================
  frontend:
    build: ./src/frontend
    env_file: .env
    depends_on:
      - api
    networks:
      - frontend-net
    restart: unless-stopped

  # ========================
  # BASE DE DONNEES
  # ========================
  timescaledb:
    image: timescale/timescaledb:latest-pg16
    env_file: .env
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - timescaledb-data:/var/lib/postgresql/data
    networks:
      - backend-net
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5

  # ========================
  # STOCKAGE OBJET S3
  # ========================
  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    env_file: .env
    environment:
      MINIO_ROOT_USER: ${MINIO_ROOT_USER}
      MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD}
    volumes:
      - minio-data:/data
    ports:
      - "9001:9001"   # Console MinIO (dev only, retirer en prod)
    networks:
      - backend-net
    restart: unless-stopped

  # ========================
  # MLFLOW
  # ========================
  mlflow:
    image: ghcr.io/mlflow/mlflow:latest
    command: >
      mlflow server
      --backend-store-uri postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@timescaledb:5432/${POSTGRES_DB}
      --default-artifact-root s3://mlflow-artifacts/
      --host 0.0.0.0
    env_file: .env
    environment:
      MLFLOW_S3_ENDPOINT_URL: http://minio:9000
      AWS_ACCESS_KEY_ID: ${MINIO_ROOT_USER}
      AWS_SECRET_ACCESS_KEY: ${MINIO_ROOT_PASSWORD}
    depends_on:
      - timescaledb
      - minio
    networks:
      - backend-net
    restart: unless-stopped

  # ========================
  # ETL WORKER
  # ========================
  etl-worker:
    build: ./src/etl
    env_file: .env
    depends_on:
      - timescaledb
      - minio
    networks:
      - backend-net
    restart: unless-stopped

volumes:
  timescaledb-data:
  minio-data:

networks:
  frontend-net:
    driver: bridge
  backend-net:
    driver: bridge
```

### Reseaux Docker

| Reseau | Services | Acces |
|--------|----------|-------|
| `frontend-net` | nginx, api, frontend | Expose aux utilisateurs (ports 80, 443) |
| `backend-net` | api, timescaledb, minio, mlflow, etl-worker | Interne uniquement |

> **Securite** : le frontend et nginx ne sont PAS dans `backend-net`. Ils ne peuvent pas acceder directement a TimescaleDB ou MinIO. Tout passe par l'API.

---

## Nginx

### Configuration de base

```nginx
# nginx/nginx.conf
events {
    worker_connections 1024;
}

http {
    # Redirect HTTP -> HTTPS
    server {
        listen 80;
        server_name cryptobot.example.com;
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl;
        server_name cryptobot.example.com;

        ssl_certificate     /etc/nginx/ssl/fullchain.pem;
        ssl_certificate_key /etc/nginx/ssl/privkey.pem;
        ssl_protocols       TLSv1.2 TLSv1.3;

        # Frontend (Streamlit)
        location / {
            proxy_pass http://frontend:8501;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }

        # API Backend (FastAPI)
        location /api/ {
            proxy_pass http://api:8000/api/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }

        # Healthcheck
        location /health {
            proxy_pass http://api:8000/health;
        }
    }
}
```

### HTTPS avec Let's Encrypt

```bash
# Sur le VPS, installer certbot et obtenir le certificat :
sudo apt install certbot
sudo certbot certonly --standalone -d cryptobot.example.com

# Les certs vont dans /etc/letsencrypt/live/cryptobot.example.com/
# Monter ce dossier dans le container Nginx

# Renouvellement auto : cron job
0 0 1 * * certbot renew --quiet && docker-compose restart nginx
```

---

## CI/CD (GitHub Actions)

```yaml
# .github/workflows/ci.yml
name: CI/CD

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install ruff mypy
      - run: ruff check src/
      - run: mypy src/ --ignore-missing-imports

  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: timescale/timescaledb:latest-pg16
        env:
          POSTGRES_DB: test_cryptobot
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -r requirements-dev.txt
      - run: pytest tests/ --cov=src --cov-report=xml
      - name: Check coverage >= 80%
        run: coverage report --fail-under=80

  deploy:
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    needs: [lint, test]
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to VPS
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.VPS_HOST }}
          username: ${{ secrets.VPS_USER }}
          key: ${{ secrets.VPS_SSH_KEY }}
          script: |
            cd /opt/crypto-bot
            git pull origin main
            docker-compose pull
            docker-compose up -d --build
            sleep 10
            curl -f http://localhost:8000/health || exit 1
```

---

## Configuration VPS OVH

### Setup initial

```bash
# 1. Creer un user dedie (pas root)
adduser deploy
usermod -aG docker deploy

# 2. SSH par cle uniquement
# Copier la cle publique dans ~/.ssh/authorized_keys
# Desactiver le login par password dans /etc/ssh/sshd_config :
# PasswordAuthentication no
# PermitRootLogin no

# 3. Firewall
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP (redirect)
ufw allow 443/tcp   # HTTPS
ufw enable

# 4. Installer Docker + Docker Compose
curl -fsSL https://get.docker.com | sh
apt install docker-compose-plugin

# 5. Cloner le repo
cd /opt
git clone https://github.com/votre-org/crypto-bot.git
cd crypto-bot
cp .env.example .env
# Editer .env avec les vrais secrets

# 6. Lancer
docker compose up -d
```

### Mises a jour

- Mises a jour OS : `unattended-upgrades` pour les patchs de securite
- Docker images : rebuild au deploy via CI/CD

---

## Backups

| Donnee | Methode | Frequence | Retention |
|--------|---------|-----------|-----------|
| TimescaleDB | `pg_dump` compresse → stockage distant | Quotidien (3h UTC) | 30 jours |
| MinIO | Copie `/data` → stockage distant | Hebdomadaire | 4 semaines |
| Configuration | Git (tout est dans le repo) | A chaque commit | Indefini |

### Script de backup TimescaleDB

```bash
#!/bin/bash
# scripts/backup-db.sh
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR=/opt/backups/timescaledb

mkdir -p $BACKUP_DIR

docker exec timescaledb pg_dump -U $POSTGRES_USER $POSTGRES_DB \
  | gzip > $BACKUP_DIR/cryptobot_$DATE.sql.gz

# Supprimer les backups de plus de 30 jours
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete

echo "Backup done: cryptobot_$DATE.sql.gz"
```

Ajouter au cron : `0 3 * * * /opt/crypto-bot/scripts/backup-db.sh`

---

## Monitoring

### V1 (simple)

- **Docker logs** : `docker compose logs -f --tail=100 api`
- **Healthchecks** : chaque service a un healthcheck dans docker-compose
- **Uptime** : cron job qui verifie `/health` toutes les 5 min et alerte si down

### V2 (si besoin)

Si le monitoring basique ne suffit pas, ajouter Prometheus + Grafana comme services Docker.

---

## Fichier .env.example

```bash
# === Base de donnees ===
POSTGRES_DB=cryptobot
POSTGRES_USER=cryptobot
POSTGRES_PASSWORD=CHANGE_ME_strong_password_here
DATABASE_URL=postgresql://cryptobot:CHANGE_ME@timescaledb:5432/cryptobot

# === MinIO (S3) ===
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=CHANGE_ME_strong_password_here
MINIO_ENDPOINT=http://minio:9000

# === API ===
API_SECRET_KEY=CHANGE_ME_random_string_for_jwt
API_HOST=0.0.0.0
API_PORT=8000

# === Frontend ===
API_URL=http://api:8000

# === CoinGecko ===
COINGECKO_API_KEY=your_demo_api_key_here

# === Chatbot (optionnel) ===
OPENAI_API_KEY=sk-your-key-here
# ou
ANTHROPIC_API_KEY=sk-ant-your-key-here

# === MLflow ===
MLFLOW_TRACKING_URI=http://mlflow:5000
MLFLOW_S3_ENDPOINT_URL=http://minio:9000
AWS_ACCESS_KEY_ID=${MINIO_ROOT_USER}
AWS_SECRET_ACCESS_KEY=${MINIO_ROOT_PASSWORD}
```

---

## Taches

### Sprint 1 (Novembre)
- [ ] `docker-compose.yml` avec tous les services
- [ ] Dockerfile pour chaque service (`src/api/`, `src/etl/`, `src/frontend/`)
- [ ] `.env.example`
- [ ] `.gitignore` (inclure `.env`, `*.pyc`, `__pycache__`, volumes Docker)
- [ ] Config Nginx basique (HTTP d'abord)
- [ ] GitHub Actions : lint + test
- [ ] README avec instructions de demarrage

### Sprint 2-3 (Decembre)
- [ ] HTTPS (Let's Encrypt + Nginx)
- [ ] Setup VPS OVH
- [ ] Deploy automatise via GitHub Actions
- [ ] Script de backup TimescaleDB
- [ ] Healthchecks sur tous les services

### Sprint 8-9 (Mai)
- [ ] Monitoring (healthcheck cron + alertes)
- [ ] Backup MinIO
- [ ] Hardening VPS (fail2ban optionnel)
- [ ] Documentation de deploiement (runbook)

---

## Ansible (Infrastructure as Code)

Le provisioning et le deploiement du VPS sont automatises avec **Ansible**. Tous les fichiers sont dans `infra/ansible/`.

### Structure

```
infra/
├── ansible/
│   ├── ansible.cfg              # Configuration Ansible
│   ├── inventories/
│   │   └── production.ini       # Inventaire VPS (IP, user SSH)
│   ├── group_vars/
│   │   └── vps.yml              # Variables partagees (ports, retention, etc.)
│   ├── playbooks/
│   │   ├── provision.yml        # Setup initial VPS (Docker, UFW, fail2ban, swap)
│   │   ├── deploy.yml           # Deployer l'application (sync, build, up, healthcheck)
│   │   ├── backup.yml           # Backup TimescaleDB -> MinIO
│   │   └── ssl.yml              # Setup Let's Encrypt SSL
│   └── templates/
│       └── jail.local.j2        # Template fail2ban
├── docker/                      # Configs Docker additionnelles
├── nginx/
│   └── nginx.conf               # Config Nginx reverse proxy
└── scripts/
    └── healthcheck.sh           # Script de verification sante des services
```

### Usage

```bash
# 1. Configurer l'inventaire
# Editer infra/ansible/inventories/production.ini avec l'IP du VPS

# 2. Provisioner un VPS vierge (une seule fois)
cd infra/ansible
ansible-playbook playbooks/provision.yml

# 3. Setup SSL
ansible-playbook playbooks/ssl.yml

# 4. Deployer l'application
ansible-playbook playbooks/deploy.yml

# 5. Backup manuel
ansible-playbook playbooks/backup.yml

# 6. Health check local
./infra/scripts/healthcheck.sh
```

### Playbooks

| Playbook | Quand l'utiliser | Ce qu'il fait |
|----------|-----------------|---------------|
| `provision.yml` | VPS neuf | Installe Docker, UFW, fail2ban, swap, user deploy, Nginx, certbot |
| `deploy.yml` | A chaque release | Sync fichiers, build images, `docker compose up`, healthcheck |
| `backup.yml` | Quotidien (cron) | pg_dump TimescaleDB, upload vers MinIO, rotation des anciens backups |
| `ssl.yml` | Setup initial | Obtient certificat Let's Encrypt, configure renouvellement auto |

### Variables importantes (`group_vars/vps.yml`)

| Variable | Valeur par defaut | Description |
|----------|-------------------|-------------|
| `deploy_user` | `deploy` | User systeme pour le deploiement |
| `docker_compose_dir` | `/opt/crypto-bot` | Repertoire de l'app sur le VPS |
| `ufw_allowed_ports` | `22, 80, 443` | Ports ouverts dans le firewall |
| `fail2ban_maxretry` | `5` | Tentatives avant ban |
| `backup_retention_days` | `7` | Retention des backups quotidiens |
| `backup_schedule` | `0 3 * * *` | Cron backup (3h du matin) |

---

## CI/CD Pipeline (GitHub Actions)

Le pipeline complet est dans `.github/workflows/ci.yml` :

```
PR ouverte ──> [Lint (ruff)] ──> [Type Check (mypy)] ──> [Tests (pytest + couverture)] ──> [Build Docker]
                                                                                               │
Merge sur main ──────────────────────────────────────────────────────────────────────> [Deploy via Ansible]
```

### Secrets GitHub necessaires

| Secret | Description |
|--------|-------------|
| `VPS_IP` | Adresse IP du VPS OVH |
| `VPS_SSH_KEY` | Cle SSH privee (ed25519) pour le user `deploy` |

---

## Configuration du projet

### `pyproject.toml`

Le fichier `pyproject.toml` a la racine configure :
- **ruff** : linting + formatting (line-length=120, Python 3.11)
- **mypy** : type checking strict
- **pytest** : test paths, coverage minimum 80%

### `.claude/` (Configuration Claude Code)

Le dossier `.claude/` contient la configuration pour les agents Claude Code :
- `settings.json` : permissions et variables d'environnement
- `rules/` : regles par equipe (python, data-eng, ml, backend, frontend, devops)
- `commands/` : commandes personnalisees (deploy, lint, test, db-migrate)

Les agents Claude Code utilisent `CLAUDE.md` a la racine pour comprendre le projet.
