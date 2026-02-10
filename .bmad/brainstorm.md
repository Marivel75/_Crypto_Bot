# Research Dossier v1.0 — K3s mono‑nœud OVH + VPN + Monitoring + PostgreSQL “standard”
> Document **d’étude** (options, hypothèses, tests, décisions).  
> But: obtenir un environnement **reproductible**, **observable** et **restaurable** sur **un seul VPS**.

---

## 0) Résumé (ce qu’on cherche à valider)
**Objectif final**: un VPS OVH (Ubuntu) provisionné via **Ansible** qui héberge un **cluster K3s mono‑nœud** avec:
- **VPN WireGuard** pour l’administration (UI + DB)
- **Ingress Traefik** pour HTTP/HTTPS
- **GitOps Argo CD** pour déployer et maintenir l’état du cluster
- **Monitoring** via kube‑prometheus‑stack (Prometheus + Alertmanager + Grafana) + **alertes e‑mail**
- **PostgreSQL “standard”** déployé dans le cluster (1 instance) avec **auth password** (VPN‑first)
- **Backups**: sauvegarde OVH quotidienne + **pg_dump** local (rotation) + un mini test de restore

**Contrainte structurante**: **mono‑nœud** ⇒ pas de haute disponibilité. On vise la simplicité + la discipline ops (restore, alertes).

---

## 1) Périmètre de l’étude

### 1.1 In‑scope (à obtenir)
1) Provisioning VPS via Ansible (rejouable)
2) VPN WireGuard opérationnel (accès admin)
3) K3s mono‑nœud opérationnel (Traefik + ServiceLB + local‑path)
4) Argo CD bootstrappé (App‑of‑Apps)
5) Monitoring + alertes e‑mail (Alertmanager SMTP)
6) PostgreSQL déployé + accessible via VPN (DBeaver)
7) Backups DB via pg_dump (rotation + restore drill minimal)

### 1.2 Out‑of‑scope (explicitement)
- Multi‑node / HA / etcd HA
- Longhorn / stockage distribué
- PITR/WAL archiving (piste future)
- 5432 exposé publiquement (refusé par design VPN‑first)

---

## 2) Références (sources à privilégier)
- K3s (guide en FR, vue d’ensemble): blog.stephane-robert.info  
- K3s (docs officielles): docs.k3s.io  
- Argo CD (docs officielles): argo-cd.readthedocs.io  
- kube‑prometheus‑stack (values/Chart): prometheus-community/helm-charts + ArtifactHub  
- Alertmanager config (docs officielles): prometheus.io  
- Grafana email/SMTP (docs officielles): grafana.com  
- WireGuard (Ubuntu Server docs): documentation.ubuntu.com

---

## 3) Hypothèses & risques (à tester)

### 3.1 Hypothèses
- H1: **VPN‑only** pour UI + DB réduit drastiquement la surface d’attaque sans nuire à l’ergonomie.
- H2: K3s mono‑nœud (SQLite datastore) est acceptable en homelab, sous réserve de **backup/restore** documenté.
- H3: kube‑prometheus‑stack est viable si on limite rétention, ressources et volume.
- H4: Postgres “standard” peut être opéré simplement avec password auth si accès limité au VPN.

### 3.2 Risques principaux
- R1: **Disque** (SSD) saturé par métriques + logs + dumps
- R2: **Restore** non testé ⇒ backup inutile
- R3: **Secrets** (SMTP, DB, Argo) mal gérés ⇒ fuite ou drift
- R4: Upgrades K3s/charts ⇒ incident si pas de pin de versions et rollback plan
- R5: Mono‑nœud ⇒ indisponibilité si reboot/maintenance

---

## 4) Topologie & architecture candidate (baseline)
### 4.1 Ports “Internet” (public)
- 22/tcp (SSH)
- 80/tcp (HTTP)
- 443/tcp (HTTPS)
- 51820/udp (WireGuard)

### 4.2 Services “privés via VPN”
- 5432/tcp (PostgreSQL) — **VPN only**
- UI: Argo CD, Grafana — **VPN only**
- 6443/tcp (API K8s): **bloqué Internet**, option via VPN uniquement

### 4.3 K3s (mono‑nœud)
- Datastore: SQLite (par défaut si aucune conf datastore n’est présente)
- Ingress: Traefik
- LoadBalancer: ServiceLB K3s
- PV: local‑path (mono‑nœud)

---

## 5) Questions de recherche (Research Questions)

### RQ‑A — Ansible
> Comment structurer Ansible pour obtenir un provisioning idempotent, versionné, rejouable?

**Critères**: idempotence, lisibilité, séparation des responsabilités, audit (logs).

### RQ‑B — Accès admin
> VPN‑only ou UI exposées (Ingress + allowlist)?

**Décision pressentie**: VPN‑only (surface minimale).  
Option alternative: allowlist Traefik IPAllowList (à documenter).

### RQ‑C — PostgreSQL “standard” sur K3s
> Quel mode de déploiement est le meilleur compromis en mono‑nœud?

Options candidates:
- Option 1: Helm chart “PostgreSQL” (ex: Bitnami) — simple, standard, rapide
- Option 2: Operator (CloudNativePG / CNPG) — plus “k8s‑native”, meilleures primitives ops
- Option 3: StatefulSet maison — contrôle total, mais plus d’ops

**Critères**: simplicité install/upgrade, backup/restore, monitoring, risque de foot‑gun.

### RQ‑D — Monitoring DB
> Quel monitoring minimal donne du signal sans surcharge?

**Objectif**: Niveau 1 obligatoire (availability/disk/connexions) + Niveau 2 optionnel (perf SQL).

### RQ‑E — Backup
> Snapshot OVH + pg_dump local donne‑t‑il un restore crédible?

**Critères**: temps de restore (RTO), perte de données acceptable (RPO), facilité de procédure.

---

## 6) Plan d’expérimentation (phases + preuves)

### Phase 1 — Baseline VPS (Ansible)
**But**: OS durci + firewall + SSH key only + prérequis (curl, jq, etc.).  
**Preuves**:
- SSH key only OK (root off)
- UFW: seuls ports publics autorisés (22/80/443/51820)

### Phase 2 — VPN WireGuard (Ansible)
**But**: tunnel stable + reboot‑safe.  
**Preuves**:
- `wg show` sur serveur
- connexion client OK après reboot (service systemd wg‑quick)
- accès à un service interne via IP VPN

### Phase 3 — K3s mono‑nœud (Ansible)
**But**: cluster up, Traefik + ServiceLB présents, kubeconfig prêt.  
**Preuves**:
- `kubectl get nodes` = Ready
- `kubectl get pods -A` stable
- déploiement d’un ingress de test OK

### Phase 4 — GitOps Argo CD (Ansible ou GitOps bootstrap)
**But**: “commit → sync” (auto‑sync) + structure repo stable.  
**Preuves**:
- App‑of‑Apps
- auto‑sync activé
- rollback (changement manifest) observé

### Phase 5 — Monitoring + alertes mail (GitOps)
**But**: prometheus/grafana/alertmanager + e‑mail.  
**Preuves**:
- dashboard node OK
- alerte test “firing” reçue par mail
- alertes disque > seuil configurées

### Phase 6 — PostgreSQL (GitOps)
**But**: Postgres up + PV + accès VPN + password auth.  
**Preuves**:
- connexion DBeaver via IP VPN
- écriture/lecture OK après restart pod/node

### Phase 7 — pg_dump + rotation + restore drill
**But**: dump automatique + restore minimal.  
**Preuves**:
- dumps présents, compressés, rotation OK
- restore sur DB vide validé (procédure écrite)

---

## 7) Organisation Ansible (référence)

### 7.1 Inputs (IP / user / clé)
- `ansible_host`: IP VPS
- `ansible_user`: user sudo OVH
- `ansible_ssh_private_key_file`: clé locale
- `become: true`

### 7.2 Structure recommandée
```
infra/ansible/
  ansible.cfg
  inventory/prod/hosts.yml
  group_vars/all.yml
  roles/
    base_hardening/        # UFW + paquets + sysctl
    wireguard/             # wg0 + peers + systemd
    k3s/                   # install + config K3s
    argocd_bootstrap/      # install Argo + root app (option)
  site.yml
```

### 7.3 “Done” minimal
- 1 commande exécute l’ensemble: `ansible-playbook site.yml`
- tags possibles: `--tags vpn`, `--tags k3s`, etc.
- aucun secret en clair dans Git (voir section 10)

---

## 8) GitOps (Argo CD) — baseline de recherche
- Auto‑sync (déploiement = commit)
- App‑of‑Apps (racine) + apps par domaine (monitoring, db, tooling)
- Pin versions Helm + chart repos
- Stratégie rollback simple

---

## 9) Monitoring & alerting (cluster + DB)

### 9.1 Stack proposée
- kube‑prometheus‑stack (Prometheus Operator + Alertmanager + Grafana)

### 9.2 Alerting e‑mail (Alertmanager)
- SMTP configuré côté Alertmanager
- règles “anti spam”: group_wait, repeat_interval, inhibitions

### 9.3 Monitoring DB — “challenge” (approche graduée)
**Niveau 1 (obligatoire)**
- DB instance down / pod restart
- Disk usage PV + filesystem node
- Connexions actives vs max (si dispo)
- Erreurs/log rate

**Niveau 2 (optionnel)**
- latence requêtes, top queries (`pg_stat_statements`)
- locks/deadlocks
- autovacuum retard

**Décision de recherche (recommandation)**
- Démarrer Niveau 1 uniquement.
- N’activer Niveau 2 que si symptômes (latence, erreurs, saturation).

---

## 10) Secrets (sinon GitOps est un piège)
Secrets concernés:
- SMTP password (Alertmanager/Grafana)
- admin passwords (Grafana/Argo)
- WireGuard private keys
- Postgres password

Pistes (à comparer):
- SOPS + age (recommandé)
- Sealed‑Secrets
- Secrets manuels (à éviter: drift)

---

## 11) Backups & restore

### 11.1 Kubernetes state (K3s SQLite)
- OVH snapshot couvre le disque
- Complément: savoir quoi sauvegarder (datastore + token)

### 11.2 PostgreSQL
- pg_dump (cron) + rotation + compression
- un restore drill minimal documenté

---

## 12) Journal des décisions (Decision Log)
Format:
- Date
- Décision
- Alternatives
- Justification
- Impact

---

## 13) Annexe — liens de référence (sources)
> Ces liens servent de “preuves” et de points d’appui pour le dossier.

### K3s
- Guide FR K3s (Stephane Robert): https://blog.stephane-robert.info/docs/conteneurs/orchestrateurs/k3s/
- Networking Services (Traefik, ServiceLB): https://docs.k3s.io/networking/networking-services
- Datastore (SQLite par défaut): https://docs.k3s.io/datastore
- Backup/Restore SQLite: https://docs.k3s.io/datastore/backup-restore

### Argo CD
- Auto Sync: https://argo-cd.readthedocs.io/en/stable/user-guide/auto_sync/

### Monitoring
- kube‑prometheus‑stack (ArtifactHub): https://artifacthub.io/packages/helm/prometheus-community/kube-prometheus-stack
- values.yaml chart: https://github.com/prometheus-community/helm-charts/blob/main/charts/kube-prometheus-stack/values.yaml
- Alertmanager configuration: https://prometheus.io/docs/alerting/latest/configuration/
- Grafana email notifications: https://grafana.com/docs/grafana/latest/alerting/configure-notifications/manage-contact-points/integrations/configure-email/

### VPN (WireGuard)
- Ubuntu Server (intro): https://documentation.ubuntu.com/server/explanation/intro-to/wireguard-vpn/
- Ubuntu Server (wg-quick + systemd): https://documentation.ubuntu.com/server/how-to/wireguard-vpn/common-tasks/

### PostgreSQL (standard)
- Helm chart PostgreSQL (Bitnami) — package: https://artifacthub.io/packages/helm/bitnami/postgresql
- values.yaml chart: https://github.com/bitnami/charts/blob/main/bitnami/postgresql/values.yaml

### CloudNativePG (option operator)
- Monitoring CNPG (enablePodMonitor): https://cloudnative-pg.io/documentation/1.17/monitoring/
- Dashboard Grafana CNPG: https://grafana.com/grafana/dashboards/20417-cloudnativepg/
