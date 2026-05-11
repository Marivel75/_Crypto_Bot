# `_v1/infra/` — Infrastructure as Code (Ansible)

Source of truth for VPS provisioning and host-level configuration of the
`dtsc-cryptobot.fr` production server.

## Reconciliation history

| Date       | Event                                                  |
|------------|--------------------------------------------------------|
| 2026-05-11 | Initial reconciliation with prod state (W-VPS-DEBUG). Pulled real configs from VPS into Ansible templates, fixed `domain_name`, fail2ban defaults, added missing templates (sshd, nginx host + vhost + proxy-params). |

## Layout

```
ansible/
├── ansible.cfg
├── inventories/
│   └── production.ini.example          # copy to production.ini, fill HOST + user
├── group_vars/
│   └── vps.yml                         # all tunables (domain, fail2ban, UFW, nginx, services)
├── templates/
│   ├── jail.local.j2                   # fail2ban jails (DEFAULT + sshd + nginx)
│   ├── sshd_config.j2                  # SSH hardened config
│   ├── nginx-host.conf.j2              # /etc/nginx/nginx.conf (workers, gzip, SSL, CF real_ip)
│   ├── nginx-proxy-params.conf.j2      # /etc/nginx/snippets/proxy-params.conf
│   └── nginx-vhost.conf.j2             # /etc/nginx/sites-enabled/{{ domain_name }}
└── playbooks/
    ├── provision.yml                   # full provision (idempotent)
    ├── deploy.yml                      # rsync code + docker compose up
    ├── ssl.yml                         # certbot issuance / renewal
    └── backup.yml                      # nightly backup job
nginx/                                  # NOT host nginx — this is the Docker container nginx (legacy, kept for v1)
prometheus/                             # prometheus.yml + prometheus.prod.yml (docker container)
grafana/                                # provisioning + dashboards (mounted into grafana container)
scripts/healthcheck.sh                  # host-level healthcheck cron script
```

## Two layers of nginx — don't confuse them

1. **`infra/nginx/nginx.conf`** — config for the **nginx container in docker-compose**
   (uses `upstream api { server api:8000 }` — docker DNS). Internal traffic only.
2. **`infra/ansible/templates/nginx-*.conf.j2`** — config for the **host nginx**
   (Ubuntu package, runs on the VPS itself). Terminates TLS, proxies to localhost
   ports exposed by docker containers (`127.0.0.1:8000`, `127.0.0.1:8501`, etc.).

The host nginx is the public entry point. The docker nginx is unused in prod
(historical artefact from v1, kept until removed by a future migration).

## Drifts kept under Ansible

| Item                                | Ansible source of truth                                  |
|-------------------------------------|----------------------------------------------------------|
| Domain name                         | `vps.yml: domain_name` (currently `dtsc-cryptobot.fr`)   |
| SSH allowed users                   | `vps.yml: deploy_user` (currently `ubuntu`)              |
| Fail2ban allowlist                  | `vps.yml: fail2ban_ignoreip`                             |
| Fail2ban bantime / retries          | `vps.yml: fail2ban_*`                                    |
| UFW rules (public + docker internal)| `vps.yml: ufw_allowed_ports` + `ufw_internal_rules`      |
| Cloudflare proxy IP ranges          | `vps.yml: cloudflare_ip_ranges` (refresh from CF docs)   |
| Nginx workers                       | `vps.yml: nginx_worker_processes` / `worker_connections` |
| Nginx routes (`/api/`, `/grafana/`, `/x/`, `/y/`) | `templates/nginx-vhost.conf.j2`             |
| Service list                        | `vps.yml: app_services`                                  |

## Drifts NOT yet under Ansible (TODO)

- TLS certificate issuance — done manually via `certbot --nginx`, not automated yet.
  `playbooks/ssl.yml` exists but is not wired into `provision.yml`.
- Backup cron — `playbooks/backup.yml` exists but no system cron is created.
- Prometheus / Grafana dashboards provisioning — handled by container mounts via
  `docker-compose.yml`, not Ansible.
- `.env` file — must be present on the VPS before `deploy.yml` runs; not managed
  by Ansible (and should not be — secrets layer).

## Run

Provision a fresh VPS (idempotent — safe to re-run):

```bash
cd _v1/infra/ansible
cp inventories/production.ini.example inventories/production.ini
# edit production.ini: replace HOST and ansible_user
ansible-playbook -i inventories/production.ini playbooks/provision.yml --check  # dry-run first
ansible-playbook -i inventories/production.ini playbooks/provision.yml
```

Deploy code:

```bash
ansible-playbook -i inventories/production.ini playbooks/deploy.yml
```

## Re-running `provision.yml` against current prod

Safe items (will not break prod):
- `vps.yml` aligned with prod values
- `sshd_config.j2` deployed via template with `validate: sshd -t -f %s` and rollback handler
- `nginx-*.conf.j2` deployed with `validate: nginx -t` and atomic reload

Unsafe items if blindly re-run (require manual review first):
- `Disable default nginx vhost` — already disabled on prod, idempotent. OK.
- `Add SSH key` — uses `~/.ssh/id_rsa.pub` from the **controller machine**. The
  current production key is `juleswillard@gmail.com` (RSA 4096). Verify
  `cat ~/.ssh/id_rsa.pub` matches before running. Use `exclusive: false` (already
  set) so existing keys are not removed.
