---
title: 'Homelab VPS: K3s mono-noeud + PostgreSQL Helm + Prometheus/Grafana (Ansible)'
slug: 'homelab-vps-k3s-mono-postgresql-helm-prom-graf-ansible'
created: '2026-02-15T21:21:49+01:00'
status: 'ready-for-dev'
stepsCompleted: [1, 2, 3, 4]
tech_stack:
  - Ubuntu (VPS)
  - Ansible
  - Ansible collection kubernetes.core
  - K3s
  - Kubernetes
  - Helm
  - Cilium (CNI)
  - Traefik (Ingress)
  - prometheus-community/kube-prometheus-stack
  - bitnami/postgresql
  - UFW (firewall)
files_to_modify:
  - ansible/ansible.cfg
  - ansible/requirements.yml
  - ansible/inventories/host.ini
  - ansible/inventories/group_vars/all.yml
  - ansible/inventories/host_vars/vps0.yml
  - ansible/playbooks/provisioning.yml
  - ansible/playbooks/validation.yml
  - ansible/playbooks/upgrade.yml
  - ansible/playbooks/reset.yml
  - ansible/roles/base_os/tasks/main.yml
  - ansible/roles/base_os/templates/sshd-hardening.conf.j2
  - ansible/roles/base_os/templates/journald-persistent.conf.j2
  - ansible/roles/k3s_server/tasks/main.yml
  - ansible/roles/k3s_server/templates/k3s-config.yaml.j2
  - ansible/roles/cilium/tasks/main.yml
  - ansible/roles/monitoring_prom_graf/tasks/main.yml
  - ansible/roles/postgresql_helm/tasks/main.yml
  - ansible/roles/postgresql_helm/templates/values-postgresql.yaml.j2
  - ansible/roles/validation/tasks/main.yml
code_patterns:
  - Repo Ansible role-based (base_os, k3s_server, cilium, monitoring_prom_graf, postgresql_helm, validation)
  - Ansible isole dans `ansible/` (inventories, roles, playbooks)
  - Values Helm et templates Jinja2 versionnes (no clickops)
  - Execution par tags + idempotence + playbook validation
  - Orchestration K8s via kubernetes.core (helm/k8s/k8s_info)
  - db_access_mode (direct_homelab vs tunnel) pilote l exposition du service PostgreSQL
test_patterns:
  - ansible-lint (statique)
  - playbook validation post-deploiement (smoke tests K8s + connectivite)
  - helm template (dry run) optionnel
---

# Tech-Spec: Homelab VPS: K3s mono-noeud + PostgreSQL Helm + Prometheus/Grafana (Ansible)

**Created:** 2026-02-15T21:21:49+01:00

## Overview

### Problem Statement

On veut un environnement Kubernetes **maitrise** sur un VPS Ubuntu (K3s mono-noeud) avec:
- une DB **PostgreSQL** (Helm) pour les workloads du cluster
- une observabilite **Prometheus + Grafana**
- une automatisation **Ansible** idempotente
- et un besoin cle homelab: permettre a **DBeaver** + une **app Python en local (PC maison)** de se connecter a la DB sur le VPS.

### Solution

Automatiser avec Ansible:
- bootstrap/hardening du VPS
- installation de K3s avec **Cilium** (Flannel desactive) et **Traefik** (Ingress HTTP/HTTPS)
- deploiement Helm de `kube-prometheus-stack` + `bitnami/postgresql`
- deux modes d'acces DB depuis le PC:
  - `direct_homelab` (defaut): exposer `5432` via Service `LoadBalancer` (K3s ServiceLB) + firewall restreint a l'IP maison + TLS active
  - `tunnel` (supporte): SSH tunnel + port-forward (ne pas exposer 5432 au WAN)

### Scope

**In Scope:**
- Structure repo Ansible (inventaire, roles, playbooks, vars, templates)
- Role `base_os`: SSH key only, root SSH off, firewall, prerequis
- Role `k3s_server`: config file `/etc/rancher/k3s/config.yaml`, flags Cilium (`--flannel-backend=none`, `--disable-network-policy`)
- Role `cilium`: installer Cilium via Helm (config minimale, kube-proxy conserve)
- Deployer `prometheus-community/kube-prometheus-stack` + verifs
- Deployer PostgreSQL via Helm (PVC, secrets, exporter, ServiceMonitor)
- Mode `direct_homelab`: exposer `<vps_ip>:5432` + firewall restreint + TLS
- Playbook `validation`: checks post-run (pods ready, pvc bound, scrape targets, connectivite postgres)

**Out of Scope:**
- HA PostgreSQL (multi-noeuds) / operator HA (CNPG) en v1
- exposition de l'API K8s 6443 au WAN
- stack logs (Loki/ELK/VictoriaLogs)
- GitOps complet (ArgoCD/Flux)
- chantier runtime (Docker/containerd)

## Context for Development

### Codebase Patterns

Pas de code Ansible existant a reutiliser (on repart "from scratch"). Les documents de cadrage sont deja presents (besoin/CDC/prompt/research/handoff).

### Files to Reference

| File | Purpose |
| ---- | ------- |
| `final/besoin.md` | besoin fonctionnel/non-fonctionnel (incl. acces PC maison) |
| `cdc.md` | cadrage technique v1 (Cilium+Traefik, acces DB, homelab 5432 optionnel) |
| `prompt/prompt-pgsql-ha-prom-graf.md` | CDC detaille (roles, phases, DoD) |
| `final/handoff-solo-dev.md` | decisions verrouillees + variables proposees |
| `_bmad-output/planning-artifacts/research/technical-postgresql-k3s-helm-ansible-research-2026-02-15T17:12:35+01:00.md` | nuances techniques (selectors ServiceMonitor, prerequis Ansible/Helm, patterns Day-0/1/2) |

### Technical Decisions

- K3s mono-noeud sur VPS Ubuntu
- CNI: Cilium (Flannel desactive, K3s network-policy desactive)
- Ingress: Traefik (par defaut K3s) pour HTTP/HTTPS
- Observabilite: kube-prometheus-stack
- DB: bitnami/postgresql Helm (mono-instance) + metrics + ServiceMonitor
- Acces dev PC:
  - default: direct_homelab (5432 expose + whitelist + TLS)
  - option: tunnel (SSH + port-forward)

## Implementation Plan

### Tasks

- [ ] Task 1: Scaffold projet Ansible dans `ansible/`
  - File: `ansible/ansible.cfg`
  - Action: definir inventory par defaut, activer pipelining, control_path, et `interpreter_python=auto_silent`
  - Notes: l IaC doit vivre sous `ansible/` (pas a la racine)
- [ ] Task 2: Declarer deps Ansible (collections) et standard de run
  - File: `ansible/requirements.yml`
  - Action: ajouter au minimum `kubernetes.core` (helm/k8s) et `community.general` (ufw)
  - Notes: documenter la commande `ansible-galaxy collection install -r ansible/requirements.yml`
- [ ] Task 3: Creer inventaire + variables (incl. acces DB homelab)
  - File: `ansible/inventories/host.ini`
  - Action: declarer le VPS (groupe `servers`) et activer `become`
  - Notes: mono-noeud aujourd hui, structure extensible
- [ ] Task 4: Centraliser les variables (K3s/Cilium/Helm/DB/Monitoring)
  - File: `ansible/inventories/group_vars/all.yml`
  - Action: definir les defaults:
    - `k3s_version` (pinned)
    - `k3s_kubeconfig_path: /etc/rancher/k3s/k3s.yaml` (utilise par `kubernetes.core.*`)
    - `db_access_mode: direct_homelab`
    - `db_allowed_cidr` (obligatoire, ex: `x.x.x.x/32`)
    - `postgres_namespace`, `postgres_release_name`, `postgres_storage_size`, `postgres_username`, `postgres_database`
    - `kube_prom_stack_release`, `monitoring_namespace`
  - Notes: les secrets (passwords) doivent etre stockes via Ansible Vault (fichier vault ou variables chiffrees)
- [ ] Task 5: Hardening OS + firewall (UFW) avec ouverture 5432 whitelistee
  - File: `ansible/roles/base_os/tasks/main.yml`
  - Action: durcir SSH (key-only, root off), journald persistant, UFW default deny incoming, allow 22/80/443, et allow 5432 UNIQUEMENT depuis `db_allowed_cidr` si `db_access_mode=direct_homelab`
  - Notes:
    - fail-fast: si `db_access_mode=direct_homelab`, le role doit `assert` que `db_allowed_cidr` est defini (sinon stop avant d ouvrir 5432)
    - Kubernetes/Cilium: configurer le forwarding, sinon reseau/ServiceLB peuvent casser:
      - `net.ipv4.ip_forward=1` (persistant via `ansible.builtin.sysctl`)
      - UFW `DEFAULT_FORWARD_POLICY=\"ACCEPT\"` dans `/etc/default/ufw` (puis reload)
    - si IP maison dynamique, il faudra mettre a jour `db_allowed_cidr`
- [ ] Task 6: Installer K3s server avec config file (Cilium-ready) et conserver Traefik + ServiceLB
  - File: `ansible/roles/k3s_server/templates/k3s-config.yaml.j2`
  - Action: generer `/etc/rancher/k3s/config.yaml` avec:
    - `flannel-backend: none`
    - `disable-network-policy: true`
    - ne PAS desactiver `traefik` ni `servicelb`
  - Notes: gerer `write-kubeconfig-mode` (ex: `0644`) selon besoin d acces admin local
- [ ] Task 7: Installer/mettre a jour K3s (version epinglee) et valider le cluster
  - File: `ansible/roles/k3s_server/tasks/main.yml`
  - Action: installer K3s via script officiel avec `INSTALL_K3S_VERSION={{ k3s_version }}`, demarrer `k3s`, attendre node Ready
  - Notes: ne pas exposer 6443 au WAN (firewall)
- [ ] Task 8: Installer tooling sur le VPS pour piloter le cluster via Ansible
  - File: `ansible/roles/k3s_server/tasks/main.yml`
  - Action: installer `helm` + deps Python du client Kubernetes (necessaires a `kubernetes.core.*`)
  - Notes:
    - on execute les modules `kubernetes.core` sur le VPS (kubeconfig local `{{ k3s_kubeconfig_path }}`)
    - dans les tasks `kubernetes.core.*`, passer explicitement `kubeconfig: \"{{ k3s_kubeconfig_path }}\"` (ne pas dependre de `~/.kube/config`)
- [ ] Task 9: Deployer Cilium via Helm et verifier qu il est Ready
  - File: `ansible/roles/cilium/tasks/main.yml`
  - Action: `kubernetes.core.helm_repository` (repo cilium), puis `kubernetes.core.helm` (release `cilium` en `kube-system`, `wait=true`, `atomic=true`)
  - Notes:
    - utiliser `kubeconfig: \"{{ k3s_kubeconfig_path }}\"`
    - garder kube-proxy (ne pas activer kubeProxyReplacement en v1)
- [ ] Task 10: Deployer kube-prometheus-stack (Prometheus + Grafana)
  - File: `ansible/roles/monitoring_prom_graf/tasks/main.yml`
  - Action: installer `prometheus-community/kube-prometheus-stack` dans `monitoring_namespace` (CRDs comprises), avec ressources raisonnables et un admin password Grafana fourni via Vault/Secret
  - Notes:
    - utiliser `kubeconfig: \"{{ k3s_kubeconfig_path }}\"`
    - strategie ServiceMonitor (explicite, no guess):
      - conserver le defaut kube-prometheus-stack: Prometheus selectionne les ServiceMonitors avec le label `release: {{ kube_prom_stack_release }}`
      - donc, forcer le ServiceMonitor PostgreSQL a porter le label `release: {{ kube_prom_stack_release }}` via `metrics.serviceMonitor.labels` dans les values Postgres
- [ ] Task 11: Deployer PostgreSQL via Helm (TLS + metrics + exposition 5432 en direct_homelab)
  - File: `ansible/roles/postgresql_helm/templates/values-postgresql.yaml.j2`
  - Action: templater les values:
    - hardening acces remote:
      - `auth.enablePostgresUser=false` (ne pas autoriser le login remote du user admin `postgres`)
      - creer un user applicatif (`auth.username`) et une DB (`auth.database`)
    - credentials via `auth.existingSecret` (Ansible cree le Secret)
      - cles attendues par le chart Bitnami: `postgres-password`, `password`, `replication-password`
    - `tls.enabled=true` + `tls.autoGenerated=true`
    - `metrics.enabled=true` + `metrics.serviceMonitor.enabled=true`
    - `metrics.serviceMonitor.labels.release={{ kube_prom_stack_release }}` (pour etre scrappe par Prometheus)
    - `primary.service.type=LoadBalancer` si `db_access_mode=direct_homelab`, sinon `ClusterIP`
    - en `direct_homelab` (defense-in-depth):
      - `primary.service.externalTrafficPolicy=Local`
      - `primary.service.loadBalancerSourceRanges=[\"{{ db_allowed_cidr }}\"]`
  - Notes:
    - le firewall VPS reste la barriere principale (whitelist 5432)
    - TLS auto-signe chiffre le trafic mais n apporte pas de chaine de confiance: cote clients, utiliser `sslmode=require` (ou fournir un CA propre plus tard via `tls.certificatesSecret`)
- [ ] Task 12: Appliquer les releases Helm + manifests glue (Namespace/Secrets) dans l ordre
  - File: `ansible/roles/postgresql_helm/tasks/main.yml`
  - Action:
    - creer Namespace `database`
    - creer Secret creds (via `kubernetes.core.k8s`) contenant au minimum:
      - `postgres-password` (admin postgres)
      - `password` (user applicatif `auth.username`)
      - `replication-password` (meme si `architecture=standalone`, garder une valeur forte)
    - installer/upgrade release PostgreSQL avec `kubernetes.core.helm` (`wait`, `timeout`, `atomic`) et `kubeconfig: \"{{ k3s_kubeconfig_path }}\"`
  - Notes:
    - deployer d abord monitoring (CRDs ServiceMonitor) puis Postgres
    - si `db_access_mode=direct_homelab`, ne jamais creer une regle UFW “0.0.0.0/0” par accident: la whitelist est obligatoire
- [ ] Task 13: Implementer les playbooks (provisioning/validation/upgrade/reset) avec tags
  - File: `ansible/playbooks/provisioning.yml`
  - Action: orchestrer `base_os` -> `k3s_server` -> `cilium` -> `monitoring_prom_graf` -> `postgresql_helm` -> `validation`
  - Notes: `reset.yml` doit desinstaller releases Helm + k3s proprement (sans `rm -rf` aveugle)
- [ ] Task 14: Playbook/role validation (smoke tests)
  - File: `ansible/roles/validation/tasks/main.yml`
  - Action: verifier:
    - node Ready
    - pods Ready (kube-system/monitoring/database)
    - PVC Bound pour Postgres
    - Service Postgres (type LB si direct_homelab) present
    - ServiceMonitor Postgres present
    - UFW: regle 5432 uniquement depuis `db_allowed_cidr` (si direct_homelab)
    - prerequis reseau:
      - `net.ipv4.ip_forward=1`
      - `/etc/default/ufw` contient `DEFAULT_FORWARD_POLICY=\"ACCEPT\"`
  - Notes: la connectivite DBeaver/Python reste un test manuel (depuis la maison)

### Acceptance Criteria

- [ ] AC 1: Given un VPS Ubuntu neuf et accessible en SSH, when je lance `ansible-playbook ansible/playbooks/provisioning.yml -i ansible/inventories/host.ini`, then le playbook termine sans erreur et le cluster K3s est Ready.
- [ ] AC 2: Given `db_access_mode=direct_homelab` et `db_allowed_cidr` defini, when le provisioning est termine, then le firewall autorise `5432/tcp` uniquement depuis `db_allowed_cidr` et refuse les autres IPs.
- [ ] AC 2b: Given `db_access_mode=direct_homelab` et `db_allowed_cidr` absent/vide, when je lance `provisioning.yml`, then le playbook echoue immediatement (assert) et n ouvre pas 5432.
- [ ] AC 3: Given `db_access_mode=direct_homelab`, when je fais `kubectl -n database get svc`, then le Service PostgreSQL est `LoadBalancer` et un endpoint externe est joignable via `<vps_ip>:5432`.
- [ ] AC 4: Given `db_access_mode=direct_homelab`, when je me connecte depuis mon IP maison whitelistee avec DBeaver, then la connexion PostgreSQL reussit avec user/mdp et TLS actif.
- [ ] AC 5: Given `db_access_mode=direct_homelab`, when je tente une connexion depuis une IP non whitelistee, then la connexion a `<vps_ip>:5432` echoue (timeout/refused).
- [ ] AC 6: Given kube-prometheus-stack est deploye, when je verifie les pods `monitoring`, then Prometheus et Grafana sont en etat Ready.
- [ ] AC 7: Given PostgreSQL est deploye avec metrics, when je liste les `ServiceMonitor`, then un ServiceMonitor PostgreSQL existe et Prometheus scrape les metrics (au moins: target presente/UP).
- [ ] AC 8: Given je relance `ansible-playbook .../provisioning.yml` une seconde fois, when aucune variable n a change, then l execution est idempotente (pas d erreurs, changements minimaux) et les checks validation passent toujours.
- [ ] AC 9: Given `ansible-playbook ansible/playbooks/reset.yml` est execute, when il termine, then les releases Helm (monitoring/postgres) et K3s sont retires proprement et le firewall revient a un etat attendu (22/80/443 uniquement, 5432 ferme).
- [ ] AC 10: Given `ansible-playbook ansible/playbooks/validation.yml` est execute, when le cluster est sain, then le playbook termine en success et remonte les infos utiles (services, LB, UFW rules, pods).

## Additional Context

### Dependencies

- Collections Ansible: `kubernetes.core`, `community.general`
- Binaire `helm` disponible sur le VPS (installe via role `k3s_server`)
- Python deps sur le VPS pour `kubernetes.core` (client Kubernetes)
- Acces SSH au VPS + privilege sudo

### Testing Strategy

- `ansible-lint` + checks YAML
- playbook `validation` post-deploiement
- tests manuels (homelab):
  - DBeaver: connexion sur `<vps_ip>:5432` (TLS)
  - Python: DSN ex: `postgresql://<user>:<password>@<vps_ip>:5432/<db>?sslmode=require`
  - reseau: verifier que 5432 est ferme depuis une IP non whitelistee

### Notes

- `db_access_mode` doit etre une variable (default `direct_homelab`)
- en `direct_homelab`, `db_allowed_cidr` doit etre obligatoire (ex: IP maison `/32`)
- TLS active en `direct_homelab` (auto-signed acceptable)
- Prometheus (kube-prometheus-stack) ne decouvrira pas le ServiceMonitor Postgres si le label `release: {{ kube_prom_stack_release }}` manque
- exposition 5432 = homelab uniquement (ne pas reproduire tel quel en HA/prod)
- ServiceMonitor: on aligne via labels plutot que d ouvrir globalement tous les selectors
