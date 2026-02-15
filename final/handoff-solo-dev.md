# Handoff vers Solo Dev (Quick Spec)

## Contexte

Objectif: provisionner un **homelab sur VPS Ubuntu** avec un cluster **K3s mono-noeud**, une base **PostgreSQL via Helm**, et l'observabilite **Prometheus + Grafana** (kube-prometheus-stack), le tout automatise via **Ansible**.

Docs source:
- Besoin: `final/besoin.md`
- CDC: `cdc.md`
- CDC detaille (prompt): `prompt/prompt-pgsql-ha-prom-graf.md`
- Recherche technique: `_bmad-output/planning-artifacts/research/technical-postgresql-k3s-helm-ansible-research-2026-02-15T17:12:35+01:00.md`

## Decisions verrouillees (non-negociables v1)

- Cluster: **K3s** sur 1 VPS Ubuntu (mono-noeud)
- Runtime: **K3s par defaut** (pas de chantier Docker/containerd)
- CNI: **Cilium** (Flannel desactive)
- Ingress HTTP/HTTPS: **Traefik** (packaged component K3s)
- Observabilite: **Prometheus + Grafana** via `kube-prometheus-stack`
- DB: **PostgreSQL via Helm chart** (ex: `bitnami/postgresql`) en mono-instance

## Besoin cle "dev depuis PC"

On doit pouvoir utiliser:
- DBeaver (PC maison) vers la DB sur VPS
- une application Python locale (PC maison) vers la DB sur VPS

Deux modes acceptes (le code doit supporter les 2 via variable):
- Mode par defaut (homelab): **exposer 5432** sur le VPS avec user/mdp + whitelist IP maison + **TLS active**
- Mode alternatif: **SSH tunnel + port-forward** (ne pas exposer 5432 au WAN)

## Exigences techniques a specifier

Ansible:
- repo structure classique (inventaire, roles, playbooks)
- idempotence + tags + playbook `validation`
- modules: `kubernetes.core.helm`, `kubernetes.core.k8s`, `kubernetes.core.k8s_info`

K3s:
- config par fichier (`/etc/rancher/k3s/config.yaml`)
- flags Cilium: `--flannel-backend=none` + `--disable-network-policy`

PostgreSQL (Helm):
- namespace `database`
- secrets maitrises (preferer `auth.existingSecret` + Ansible Vault)
  - cles Secret attendues (Bitnami): `postgres-password`, `password`, `replication-password`
- hardening remote: `auth.enablePostgresUser=false` (pas de login remote pour `postgres`)
- metrics exporter + `ServiceMonitor`
  - label obligatoire pour kube-prometheus-stack: `release: <kube_prom_stack_release>`
- exposition:
  - default: `ClusterIP`
  - homelab: `primary.service.type=LoadBalancer` (K3s ServiceLB) + `loadBalancerSourceRanges=[db_allowed_cidr]` + firewall 5432 restreint
  - TLS actif quand exposition homelab (`tls.enabled=true`, auto-signe OK)

## Variables (proposition)

- `postgres_namespace` (default: `database`)
- `postgres_release_name` (default: `postgresql`)
- `postgres_chart` (default: `bitnami/postgresql`)
- `postgres_values` (dict/templated)
- `k3s_kubeconfig_path` (default: `/etc/rancher/k3s/k3s.yaml`)
- `db_access_mode`:
  - `direct_homelab` (default)
  - `tunnel`
- `db_allowed_cidr` (obligatoire si `direct_homelab`, ex: `x.x.x.x/32`)
- `postgres_tls_enabled` (default: true si `direct_homelab`)

## Definition of Done (v1)

- K3s Ready, Cilium Ready
- kube-prometheus-stack deployee (Prometheus + Grafana up)
- PostgreSQL deployee (PVC Bound, Pod Ready, Service OK)
- Metrics PostgreSQL scrape OK (targets OK)
- Acces depuis PC:
  - `tunnel`: DBeaver connecte via `127.0.0.1:5432` (SSH)
  - `direct_homelab`: DBeaver connecte sur `<vps_ip>:5432` (firewall restreint)
- Playbook `validation` passe

## Hors perimetre v1

- HA PostgreSQL (multi-noeuds) et operator HA (CNPG) en prod
- exposition K8s API 6443 au WAN
- stack logs
