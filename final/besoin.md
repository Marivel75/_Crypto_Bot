# Besoin

## Objectif
Mettre en place une base **PostgreSQL** dans un environnement **Kubernetes maitrise** sur un **VPS Ubuntu** (demarrage en **mono-noeud**), avec une **observabilite metrics** standard.

## Contexte
- Cluster cible: **K3s** sur VPS (mono-noeud pour commencer)
- Contrainte: rester simple, reproductible, et evolutif vers multi-noeuds plus tard

## Besoin fonctionnel
- Disposer d'un **PostgreSQL** utilisable par les workloads du cluster (read/write, Service stable)
- Deployer PostgreSQL **via Helm chart** (approche pragmatique en mono-noeud)
- Exposer l'acces DB en **interne cluster** (ClusterIP) par defaut
- Permettre l'acces **depuis un poste local (DBeaver + app Python)** pour le dev homelab (sans VPN au debut)

## Besoin non-fonctionnel
- Provisioning automatise et rejouable (idempotent)
- Securite de base (SSH key only, root SSH off, firewall strict)
- Stockage persistant (PVC via storage par defaut K3s)
- Acces dev sans VPN (homelab):
  - option: SSH tunnel / port-forward (recommande)
  - option: exposer 5432 sur le VPS avec user/mdp (idealement TLS) et firewall restreint a l'IP maison
- Monitoring:
  - **Prometheus + Grafana** (kube-prometheus-stack)
  - Metriques K8s + metriques PostgreSQL (via exporter/ServiceMonitor)

## Evolution (future)
- HA reelle PostgreSQL: uniquement quand on passera a **3+ noeuds** (anti-affinite, PDB, storage adapte)
- Backups/PITR: optionnel au debut, a cadrer ensuite (S3 compatible, tests de restore)

## Hors perimetre
- Changer/forcer le runtime (Docker/containerd) ou "rajouter containerd" comme chantier
- HA reelle sur mono-noeud
- Stack logs complete (Loki/ELK/VictoriaLogs)
