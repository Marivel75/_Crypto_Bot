# Cahier des charges
## Cluster Kubernetes (K3s) sur VPS + PostgreSQL (Helm) + Prometheus/Grafana

- **Version** : v1.0
- **Date** : 15/02/2026
- **Cible** : 1 VPS Ubuntu (mono-nœud) pour commencer, évolutif vers 3+ nœuds pour HA réelle

---

## 1) Contexte & objectifs

### 1.1 Contexte
Déployer un cluster Kubernetes léger sur VPS (K3s) avec :

- Runtime : **K3s par défaut** (on ne pilote pas le runtime explicitement)
- Datastore K3s : **SQLite** (par défaut K3s en mono-serveur)
- CNI : **Cilium** (Flannel desactive)
- Stockage persistant : **local-path-provisioner** (packagé K3s)
- Ingress : **Traefik** (par défaut K3s) (Caddy optionnel plus tard)
- Observabilité (metrics) : **Prometheus + Grafana**
- Objectif applicatif : **PostgreSQL via Helm** (mono-noeud) avec trajectoire d evolution vers HA plus tard

### 1.2 Objectifs
- Cluster opérationnel en **1 commande** de provisioning (Ansible).
- Sécurisé (SSH key only, root SSH off, firewall strict, audit basique).
- Reproductible (idempotent, versionné, rollback/upgrade/reset outillés).
- PostgreSQL prêt pour les workloads (read/write, Service stable) en **mono-instance** sur mono-noeud.
- **HA réelle** uniquement quand on passera a **3+ noeuds** (hors v1, mais la spec prepare la trajectoire).
- Observabilité : dashboards Grafana + métriques Prometheus prêtes (K8s + PostgreSQL).

---

## 2) Périmètre

### 2.1 Inclus
- Provision OS (utilisateur sudo, SSH durci, firewall, journald)
- Installation K3s **sans custom runtime** (par défaut)
- Datastore K3s : SQLite
- CNI : Cilium (Flannel desactive)
- Stockage persistant via `local-path-provisioner`
- Ingress controller par défaut K3s (Traefik) (swappable plus tard)
- Prometheus + Grafana (via `kube-prometheus-stack`)
- PostgreSQL via Helm chart (mono-instance) :
  - Installation du chart (ex: `bitnami/postgresql`)
  - Accès applicatif via Service (ClusterIP)
  - (Optionnel) activation metrics + `ServiceMonitor` (Prometheus Operator)
  - (Optionnel) backups (a cadrer) et tests de restore
- Playbooks : `provisioning`, `reset`, `upgrade`, `validation`

### 2.2 Hors périmètre (optionnel)
- Changement/ajout de runtime (Docker, containerd, etc.) : **hors périmètre** (K3s gère)
- GitOps complet (ArgoCD) (possible plus tard)
- Stack logs (Loki/ELK/VictoriaLogs) (possible plus tard)
- Longhorn/Ceph/stockage distribué (possible plus tard)
- Multi-région / DR avancé (possible plus tard)

---

## 3) Contraintes & choix techniques (non négociables)

### 3.1 Runtime
- **K3s runtime par défaut**.
- On ne met pas en place Docker/containerd manuellement (pas de “runtime engineering”).

### 3.2 PostgreSQL HA
V1 (mono-noeud):
- PostgreSQL en **mono-instance** via Helm chart.
- Stockage persistant via PVC (RWO) sur `local-path`.
- Secrets maitrises (preferer `existingSecret` si le chart le supporte).

Trajectoire HA (multi-noeuds, plus tard):
- HA reelle quand 3+ noeuds + anti-affinite + PDB + stockage adapte.
- Recommandation: bascule vers un operator type **CloudNativePG (CNPG)** quand HA/backups declaratifs deviennent un besoin.

### 3.3 Observabilité (metrics)
- Déployer `kube-prometheus-stack` (Prometheus Operator + Grafana + Alertmanager).
- Scrapes activés : apiserver, kubelet, etcd/metrics K3s si exposé, coredns, nodes, pods.
- PostgreSQL : métriques via exporter du chart + `ServiceMonitor` (si Prometheus Operator).

### 3.4 Réseau
- V1 : **Cilium** comme CNI primaire.
- Flannel desactive : `--flannel-backend=none`
- NetworkPolicy K3s built-in desactive pour laisser Cilium gerer : `--disable-network-policy`

### 3.5 Stockage
- `local-path-provisioner` pour PVC.
- Mono-noeud: un seul PVC (SPOF disque). Backups a prevoir des que l env devient important.

---

## 4) Exigences sécurité (OS + cluster)

### 4.1 Accès SSH / comptes
- SSH key only
- Création d’un utilisateur sudo (opérateur)
- Root SSH désactivé
- `PasswordAuthentication no`

### 4.2 Firewall (WAN)
Ouvrir :
- 22/tcp (SSH)
- 80/tcp (HTTP)
- 443/tcp (HTTPS)

Option homelab (autorise) :
- 5432/tcp (PostgreSQL) UNIQUEMENT depuis une IP/CIDR autorise (ex: IP maison)

Bloquer depuis Internet (WAN) :
- 6443/tcp (Kubernetes API) tant qu’aucun agent externe n’est requis
- 5432/tcp (PostgreSQL) par defaut (sauf mode homelab ci-dessus)
- Ports NodePort (30000-32767) sauf besoin explicite
- Tout le reste

---

## 5) Architecture cible

### 5.1 Schéma logique
- VPS (Ubuntu)
    - K3s Server (control plane + worker)
      - datastore : SQLite
      - CNI : Cilium
      - Storage : local-path
      - Ingress : Traefik (defaut K3s)
      - Monitoring : Prometheus + Grafana
      - Database : PostgreSQL (Helm)

### 5.2 Topologies
- **V1 (mono-noeud)** : 1 instance PostgreSQL via Helm.
- **Future (HA)** : 3+ noeuds + operator (CNPG) ou solution HA equivalente.

---

## 6) Exigences Ansible (repo & standard)

### 6.1 Arborescence attendue
- `ansible.cfg`
- `requirements.yml` (collections/roles)
- `inventories/`
  - `host.ini`
  - `group_vars/all.yml`
  - `host_vars/vps0.yml`
- `roles/`
  - `base_os/`
  - `k3s_server/`
  - `k3s_agents/` (optionnel, pour HA réelle)
  - `cilium/` (optionnel)
  - `storage_local_path/`
  - `ingress_caddy/` (optionnel)
  - `monitoring_prom_graf/`
  - `postgresql_helm/`
  - `backup_postgres/` (optionnel)
  - `validation/`
- `playbooks/`
  - `provisioning.yml`
  - `reset.yml`
  - `upgrade.yml`
  - `validation.yml`

### 6.2 Principes
- Idempotent
- Variables centralisées (`group_vars/all.yml` + `host_vars/*`)
- Tags Ansible : `base`, `k3s`, `cni`, `storage`, `ingress`, `monitoring`, `db`, `backup`, `validation`
- Validation systématique post-déploiement

---

## 7) Spécifications d’implémentation

### 7.1 Rôle `k3s_server`
Installer K3s avec :
- datastore SQLite par défaut (mono-serveur)
- Cilium : `--flannel-backend=none` + `--disable-network-policy`
- Ingress par défaut (Traefik) en v1
- (Option) Caddy : `--disable=traefik`
- ne pas désactiver `local-storage`

### 7.2 Rôle `monitoring_prom_graf`
- Déployer `kube-prometheus-stack`
- Grafana :
  - accès sécurisé (au minimum password admin non défaut + Secret)
  - exposition via Ingress (optionnel)
- Valider :
  - Prometheus scrapes OK
  - Dashboards K8s visibles

### 7.3 Role `postgresql_helm`
- Deployer PostgreSQL via Helm chart (ex: Bitnami).
- Parametrage attendu (values):
  - persistance PVC (size, storageClass si besoin)
  - `auth.existingSecret` (recommande) ou secret gere par chart
  - ressources (requests/limits)
  - metrics: activer exporter + `ServiceMonitor` si Prometheus Operator
- Exposer un Service stable (ClusterIP) pour les workloads.
- Mode homelab (optionnel): exposer `<vps_ip>:5432` via `primary.service.type=LoadBalancer` + firewall restreint + TLS recommande.

### 7.4 Role `backup_postgres` (optionnel)
- V1: dump logique (cronjob ou externe) + retention + test de restore
- Future HA: backups physiques + WAL archiving (via operator type CNPG) vers bucket S3 compatible
- Politique :
  - full backup quotidien
  - rétention (ex: 7/14/30 jours selon besoin)
  - test de restauration (PITR) en environnement de validation

---

## 8) Critères d’acceptation (Definition of Done)

### 8.1 Infra & sécurité
- SSH key only, root SSH off, user sudo OK
- Firewall : uniquement 22/80/443 ouverts WAN
- journald persistant, rotation OK

### 8.2 Cluster
- `kubectl get nodes` = Ready
- CoreDNS fonctionne
- CNI Ready
- StorageClass `local-path` par défaut + PVC test OK
- Ingress Traefik répond sur 80/443

### 8.3 Monitoring
- Prometheus UP et scrape des métriques K8s
- Grafana UP, dashboards visibles
- (Si activé) métriques PostgreSQL visibles dans Prometheus/Grafana

### 8.4 PostgreSQL
- 1 instance prete, Service accessible, test read/write OK
- (Si active) metrics PostgreSQL scrape OK
- (Si active) backup/restore test = OK

---

## 9) Risques & mitigations

### 9.1 “HA” sur mono-nœud
- Risque : pas de HA réelle (un seul hôte).
- Mitigation : assumer 1 instance + backups + tests de restore ; HA exige 3+ noeuds.

### 9.2 Stockage local et perte de nœud
- Risque : perte disque/host => perte du PVC PostgreSQL.
- Mitigation : backups + tests de restauration + trajectoire vers stockage/cluster multi-noeuds.

### 9.3 Complexité opérateur
- Risque : courbe d'apprentissage (quand on passera a un operator HA type CNPG).
- Mitigation : adoption progressive, defaults simples, validation automatisee, runbooks.

---

## 10) Roadmap (pragmatique)
- Phase 1 : base_os + K3s + Cilium + local-path (MVP)
- Phase 2 : Prometheus + Grafana
- Phase 3 : PostgreSQL Helm (1 instance) + metriques
- Phase 4 : backups (dump logique) + tests de restore + runbooks upgrade
- Phase 5 : (future) multi-noeuds + HA PostgreSQL via operator (CNPG) + PITR/WAL
