---
stepsCompleted: [1, 2, 3, 4, 5, 6]
inputDocuments:
  - final/besoin.md
  - prompt/prompt.md
  - prompt/prompt-pgsql-ha-prom-graf.md
workflowType: 'research'
lastStep: 6
research_type: 'technical'
research_topic: 'PostgreSQL sur K3s (mono-noeud) via Helm, automatise avec Ansible, monitoring Prometheus/Grafana'
research_goals: 'Identifier les briques techniques et objets Ansible necessaires (prerequis, modules, charts, valeurs, patterns) pour deployer et operer K3s + PostgreSQL Helm + kube-prometheus-stack sur VPS mono-noeud, avec trajectoire d evolution vers HA multi-noeuds.'
user_name: 'Jules'
date: '2026-02-15T17:12:35+01:00'
web_research_enabled: true
source_verification: true
---

# Research Report: technical

**Date:** 2026-02-15T17:12:35+01:00
**Author:** Jules
**Research Type:** technical

---

## Research Overview

Objectif: cadrer les choix techniques et, surtout, les "objets Ansible" utiles pour automatiser un cluster K3s mono-noeud avec PostgreSQL via Helm et observabilite Prometheus/Grafana.

Methodologie:
- Lecture des documents internes (besoin + prompts).
- Recherche web sur docs officielles (K3s, charts Helm, docs Ansible collections).
- Extraction des implications concretes: prerequis (binaires/CRDs), objets Ansible a privilegier, variables et valeurs Helm utiles, points d attention mono-noeud.

---

## Technical Research Scope Confirmation

**Research Topic:** PostgreSQL sur K3s (mono-noeud) via Helm, automatise avec Ansible, monitoring Prometheus/Grafana
**Research Goals:** Identifier les briques techniques et objets Ansible necessaires (prerequis, modules, charts, valeurs, patterns) pour deployer et operer K3s + PostgreSQL Helm + kube-prometheus-stack sur VPS mono-noeud, avec trajectoire d evolution vers HA multi-noeuds.

**Technical Research Scope:**

- Architecture Analysis - design patterns, system architecture
- Implementation Approaches - automation patterns, best practices
- Technology Stack - K3s/K8s, Helm charts, Ansible collections
- Integration Patterns - services, network policies, monitoring integration
- Performance Considerations - sizing mono-noeud, stockage local, limites/risques

**Research Methodology:**

- Current web data with rigorous source verification
- Multi-source validation for critical technical claims
- Confidence level framework for uncertain technical information
- Comprehensive technical coverage with architecture-specific insights

**Scope Confirmed:** 2026-02-15T17:12:35+01:00

## Technology Stack Analysis

### Programming Languages

Dans ce sujet, le "code" est surtout de l IaC declaratif:
- **YAML**: manifests Kubernetes, inventaires/vars Ansible, values Helm.
- **Jinja2**: templating Ansible (generation de fichiers de conf / manifests parametrises).
- **Bash**: souvent utilise pour bootstrap K3s (script d installation) et glue scripts.
- **Go templates**: Helm chart templating (consomme via `values.yaml`).

Sources:
- K3s networking docs (flags et recommandations pour CNI externes): https://docs.k3s.io/networking/basic-network-options

### Development Frameworks and Libraries

Frameworks/outils structurants:
- **Kubernetes (API + objets)**: Deployments/StatefulSets/Services/PVC/Secrets/Ingress, etc.
- **K3s**: distribution Kubernetes "light" pour VPS; en cas de CNI externe il faut des flags de demarrage adaptes (ex: flannel off).
- **Helm**: packaging et parametrage d apps K8s (PostgreSQL, kube-prometheus-stack).

Points verifiables:
- Pour utiliser un CNI externe sur K3s, demarrer avec `--flannel-backend=none`, et c est souvent recommande d activer `--disable-network-policy` pour eviter les conflits avec les moteurs de policy des CNIs. Source: https://docs.k3s.io/networking/basic-network-options

### Database and Storage Technologies

Database:
- **PostgreSQL via Helm chart** (mono instance pour mono-noeud).
- Recommandation pragmatique: chart **bitnami/postgresql** (simple), en gardant en tete la trajectoire multi-noeuds (operator ou chart HA) plus tard.

Storage:
- En mono-noeud K3s, **local-path-provisioner** est typiquement le StorageClass par defaut.
- Pour PostgreSQL: **PVC RWO** obligatoire (stateful). Attention a l I/O disque du VPS et au risque "single disk".

Observabilite PostgreSQL:
- Le chart Bitnami PostgreSQL supporte l integration Prometheus via `metrics.enabled=true` (postgres_exporter) et peut creer des objets `ServiceMonitor` via `metrics.serviceMonitor.enabled=true` pour Prometheus Operator. Source: https://raw.githubusercontent.com/bitnami/charts/main/bitnami/postgresql/README.md

### Development Tools and Platforms

Outils deploiement:
- **Ansible** pour orchestrer l installation OS + K3s + Helm.
- **Collections Ansible Kubernetes** (recommande):
  - `kubernetes.core.k8s`: gerer les objets Kubernetes declarativement (apply/delete). Doc: https://docs.ansible.com/ansible/latest/collections/kubernetes/core/k8s_module.html
  - `kubernetes.core.helm`: installer/upgrade des charts Helm dans le cluster. Doc: https://docs.ansible.com/ansible/latest/collections/kubernetes/core/helm_module.html

Pre-requis importants (a mettre dans la spec/provisioning controller):
- `kubernetes.core.k8s` s appuie sur le **Kubernetes Python client** (et Python >= 3.9). Doc: https://docs.ansible.com/ansible/latest/collections/kubernetes/core/k8s_module.html
- `kubernetes.core.helm` requiert le binaire **helm** installe sur la machine qui execute Ansible (controller) et les deps Python associees. Doc: https://docs.ansible.com/ansible/latest/collections/kubernetes/core/helm_module.html

Objets Ansible (brainstorm "ce qu on utilise vraiment"):
- **Inventaire** (hosts + groupes) pour separer `server` et futurs `agents`.
- **Playbooks** par "phase" (`provisioning`, `upgrade`, `reset`, `validation`).
- **Roles** par domaine (base OS, k3s, cni, ingress, monitoring, postgresql).
- **Vars** (`group_vars/all.yml`, `host_vars/*.yml`) pour piloter la config.
- **Templates** (Jinja2) pour generer `config.yaml` K3s, values Helm, manifests.
- **Handlers** pour restart services (sshd, k3s) quand fichiers changes.
Ces objets sont le coeur d Ansible (modules/playbooks/inventory/roles). Source: https://blog.stephane-robert.info/docs/infra-as-code/gestion-de-configuration/ansible/

### Cloud Infrastructure and Deployment

Plateforme cible:
- **VPS Ubuntu + systemd**.
- Exposition reseau:
  - SSH 22, HTTP 80, HTTPS 443.
  - API K8s 6443 a garder ferme au WAN (acces via SSH tunnel) tant que possible.

Deploiement Observabilite:
- **kube-prometheus-stack** installe Prometheus Operator + Prometheus + Grafana + rules/dashboards, et dependances node-exporter/kube-state-metrics. Source: https://raw.githubusercontent.com/prometheus-community/helm-charts/main/charts/kube-prometheus-stack/README.md

### Technology Adoption Trends

Tendances pratiques (orientee exploitation):
- **Helm charts Bitnami** restent une option simple et largement adoptee pour demarrer vite (mono instance), surtout en mono-noeud.
- Pour HA "vraie" PostgreSQL sur Kubernetes, la tendance est plutot aux **operators** (ex: CNPG) des que le cluster devient multi-noeuds et qu on veut automatiser backups/failover proprement. (A investiguer plus en detail en step integration/follow-up si besoin.)

## Integration Patterns Analysis

### API Design Patterns

Dans notre contexte, "API" = surtout **Kubernetes API** (et Helm par-dessus):

- **Pattern declaratif**: decrire l etat souhaite (manifests/values) et laisser le control plane converger.
- **Separation des concerns**:
  - Bootstrap machine/OS + installation K3s via SSH (Ansible classique).
  - Gestion des objets K8s + charts via appels Kubernetes API (kubeconfig).

Objets/Modules Ansible cote Kubernetes:

- `kubernetes.core.k8s`:
  - Gere des objets Kubernetes (create/patch/delete) depuis YAML inline ou fichiers.
  - Supporte plusieurs methodes d auth (kubeconfig, certificats, token, etc.).
  - S appuie sur le client Python Kubernetes. Source: https://docs.ansible.com/ansible/latest/collections/kubernetes/core/k8s_module.html
- `kubernetes.core.helm`:
  - Installe/upgrade des releases Helm sur un cluster via kubeconfig + contexte.
  - Points utiles: `kubeconfig` (path ou dict), `context`. Source: https://docs.ansible.com/ansible/latest/collections/kubernetes/core/helm_module.html
- `kubernetes.core.helm_repository`:
  - Ajoute/retire des repos Helm. Source: https://docs.ansible.com/ansible/latest/collections/kubernetes/core/helm_repository_module.html

Pattern "Helm vs k8s module":
- Helm pour les "gros packages" (kube-prometheus-stack, postgresql).
- `k8s` pour les ressources de glue (Namespaces, Ingress Grafana, NetworkPolicy Cilium, Secrets pre-provisionnes, etc.).

### Communication Protocols

Protocoles d integration a prevoir (concrets):

- **SSH**: protocole de transport Ansible (agentless) pour configurer le VPS et installer K3s. Source: https://blog.stephane-robert.info/docs/infra-as-code/gestion-de-configuration/ansible/
- **HTTPS vers l API Kubernetes (6443)**: utilise par `kubectl`, Helm et les modules Ansible Kubernetes (via kubeconfig).
- **HTTP in-cluster**:
  - Scraping Prometheus des endpoints metrics (kube components + postgres_exporter).
  - Decouverte via `ServiceMonitor` (Prometheus Operator).
- **TCP 5432**: protocole Postgres interne cluster (Service ClusterIP).

### Data Formats and Standards

- **YAML** partout:
  - Ansible (playbooks, inventaire, vars)
  - kubeconfig (YAML)
  - manifests Kubernetes (YAML)
  - values Helm (YAML)
- **CRDs** (CustomResourceDefinitions): introduisent de nouveaux types d objets (ex: `ServiceMonitor`) consommes par Prometheus Operator.
- **Prometheus exposition format** pour les metrics (texte).

### System Interoperability Approaches

Integration "bout en bout" (ordre et dependances):

1. Installer/Configurer K3s.
2. Installer le CNI (Cilium) et valider le reseau/pods.
3. Recuperer le kubeconfig K3s, puis deployer des charts Helm (monitoring, DB) via kubeconfig.
4. Installer `kube-prometheus-stack` (CRDs + Prometheus + Grafana).
5. Installer PostgreSQL via Helm avec metrics (exporter) + `ServiceMonitor` si Prometheus Operator est en place.

Details d interop importants:

- **CNI externe sur K3s**: demarrer avec `--flannel-backend=none` et il est recommande d ajouter `--disable-network-policy` pour eviter des conflits avec le moteur de policy du CNI. Source: https://docs.k3s.io/networking/basic-network-options

- **Kubeconfig K3s**:
  - Par defaut: `/etc/rancher/k3s/k3s.yaml`.
  - Donne acces admin (garder comme secret).
  - Pour acceder au cluster depuis l exterieur: copier le fichier et remplacer `server: https://127.0.0.1:6443` par l IP/DNS du serveur. Source: https://docs.k3s.io/cluster-access
  - Permissions kubeconfig: on peut fixer via `--write-kubeconfig-mode` / `K3S_KUBECONFIG_MODE`. Source: https://docs.k3s.io/installation/configuration

- **ServiceMonitor (Prometheus Operator)**:
  - `kube-prometheus-stack` installe Prometheus Operator et utilise les CRDs `ServiceMonitor`/`PodMonitor`. Source: https://raw.githubusercontent.com/prometheus-community/helm-charts/main/charts/kube-prometheus-stack/README.md
  - La decouverte depend de `prometheus.prometheusSpec.serviceMonitorSelector` et de `serviceMonitorSelectorNilUsesHelmValues`. Par defaut, ce dernier est a `true`, ce qui fait qu un selector vide/nil peut etre remplace par un selector "base sur les valeurs Helm" qui match les ServiceMonitors crees par la release. Source: https://raw.githubusercontent.com/prometheus-community/helm-charts/main/charts/kube-prometheus-stack/values.yaml
  - Pour des ServiceMonitors externes (ex: chart PostgreSQL), on a 2 patterns:
    - aligner les labels/selector du ServiceMonitor avec ceux attendus par Prometheus (ex: `metrics.serviceMonitor.labels` / `metrics.serviceMonitor.selector` cote Bitnami PostgreSQL)
    - ou definir explicitement un selector plus large (`serviceMonitorSelector: {}` ou `matchLabels` cible). Sources: https://raw.githubusercontent.com/prometheus-community/helm-charts/main/charts/kube-prometheus-stack/values.yaml , https://raw.githubusercontent.com/bitnami/charts/main/bitnami/postgresql/values.yaml

- **PostgreSQL Helm + metrics**:
  - Pattern: installer PostgreSQL via Helm, activer `metrics.enabled=true` et, si Prometheus Operator present, activer `metrics.serviceMonitor.enabled=true`.
  - Attention sequencing: activer `ServiceMonitor` seulement APRES installation des CRDs Prometheus Operator (donc apres kube-prometheus-stack).
  - Source chart: https://raw.githubusercontent.com/bitnami/charts/main/bitnami/postgresql/README.md

### Microservices Integration Patterns

Pour les workloads applicatifs:
- Acces DB via **Service ClusterIP** (ex: `postgresql.<ns>.svc.cluster.local:5432`).
- Credentials via **Secret**:
  - Soit secrets generes par le chart.
  - Soit secret gere par Ansible/Vault et reference via `auth.existingSecret` (pattern prefere pour reproductibilite). Source: https://raw.githubusercontent.com/bitnami/charts/main/bitnami/postgresql/README.md
- Options de durcissement:
  - NetworkPolicy (Cilium) pour limiter qui peut parler a Postgres.
  - Ressources (requests/limits) et probes adaptees.

### Event-Driven Integration

Deux usages "event-driven" utiles ici:

- **Alerting**: Alertmanager (installe via kube-prometheus-stack) route des alertes vers des recepteurs (webhook/email/etc.) selon config.
- **Ansible notify/handlers**: pattern natif pour declencher un restart uniquement si un fichier de config a change. Source: https://blog.stephane-robert.info/docs/infra-as-code/gestion-de-configuration/ansible/

### Integration Security Patterns

- SSH: key-only, root off, firewall strict (base).
- Kubeconfig: traiter comme secret admin; permissions strictes; eviter de l exposer sur le WAN. Sources: https://docs.k3s.io/cluster-access , https://docs.k3s.io/installation/configuration
- Secrets PostgreSQL:
  - Stocker le password en Ansible Vault/SOPS, injecter via Secret K8s, et utiliser `auth.existingSecret` dans Helm values (evite les secrets aleatoires). Source: https://raw.githubusercontent.com/bitnami/charts/main/bitnami/postgresql/README.md

## Architectural Patterns and Design

### System Architecture Patterns

Pattern d architecture recommande (simple, evolutif):

- **Layering "Day 0 -> Day 1 -> Day 2"**:
  - Day 0: hardening OS + prerequis (paquets, firewall, sshd, kernel args si besoin)
  - Day 1: installation K3s + config (CNI externe, composants K3s desactives)
  - Day 2: deploiement des add-ons (monitoring) puis des apps stateful (PostgreSQL)
- **Separation des plans**:
  - "Machine config" via Ansible (systemd, fichiers, packages).
  - "Cluster state" via API Kubernetes (Ansible `kubernetes.core.*` + Helm).
- **Namespace boundaries**:
  - `monitoring`: kube-prometheus-stack
  - `database`: PostgreSQL et objets associes (Secrets, ServiceMonitor)
  - (option) `ingress`: controllers, certificates, etc.
- **Stateful workload pattern**:
  - PostgreSQL doit reposer sur un pattern **StatefulSet + PVC** (stable identity + stockage persistant). Source: https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/

_Source: https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/_

### Design Principles and Best Practices

Principes de conception pour un cluster "maitrise":

- **Idempotence partout**:
  - roles Ansible deterministes (vars explicites, templates versionnes).
  - Helm deploy/upgrade pilote via `kubernetes.core.helm` (eviter l execution manuelle de `helm`).
  - Attention: l idempotency check de `kubernetes.core.helm` peut echouer dans certains cas (a traiter par validation fonctionnelle plutot que "changed/no-changed"). Source: https://docs.ansible.com/ansible/latest/collections/kubernetes/core/helm_module.html
- **Ordonnancement explicite des dependances**:
  - CRDs Prometheus Operator doivent exister avant de creer des `ServiceMonitor`.
  - CNI ready avant de deployer des composants qui creent des Pods.
- **Single Source of Truth**:
  - `values.yaml` Helm et manifests K8s versionnes, pas de "clickops".
- **Observabilite by design**:
  - Activer metrics Postgres des le debut (exporter + ServiceMonitor) et garder Grafana disponible.

_Source: https://docs.ansible.com/ansible/latest/collections/kubernetes/core/helm_module.html_

### Scalability and Performance Patterns

En mono-noeud, l architecture doit assumer:

- **Scaling Postgres vertical** (CPU/RAM/IOPS), pas horizontal.
- **Stockage local = single point of failure** (disque VPS). D ou:
  - sizing PVC prudent
  - backups (meme basiques) des que l env devient "important"
- **Trajectoire vers HA** (quand 3+ noeuds):
  - Postgres HA reelle necessite multi-noeuds + anti-affinite + stockage adapte (hors scope initial).
  - Cote K3s control-plane, la base K3s SQLite n est pas viable en multi-serveur: il faut migrer vers embedded etcd ou datastore externe. Source: https://docs.k3s.io/datastore

_Source: https://docs.k3s.io/datastore_

### Integration and Communication Patterns

Patterns d integration au niveau architecture:

- **Cluster-internal first**:
  - PostgreSQL expose en `ClusterIP` (pas d exposition WAN).
  - Grafana expose via Ingress seulement si necessaire; sinon port-forward.
- **Prometheus Operator pattern**:
  - `kube-prometheus-stack` installe Prometheus Operator, CRDs et Grafana. Source: https://raw.githubusercontent.com/prometheus-community/helm-charts/main/charts/kube-prometheus-stack/README.md
  - `ServiceMonitor` pour brancher postgres_exporter (selon labels/selector de la release).
- **CNI externe**:
  - demarrer K3s avec `--flannel-backend=none` et il est recommande d utiliser `--disable-network-policy` pour eviter des conflits. Source: https://docs.k3s.io/networking/basic-network-options

_Source: https://raw.githubusercontent.com/prometheus-community/helm-charts/main/charts/kube-prometheus-stack/README.md_

### Security Architecture Patterns

Patterns de securite pragmatiques:

- **Kubeconfig = secret admin**:
  - kubeconfig par defaut: `/etc/rancher/k3s/k3s.yaml`
  - si copie hors serveur, il faut ajuster l endpoint `server:`; garder permissions strictes. Source: https://docs.k3s.io/cluster-access
- **Secrets Postgres geres**:
  - preferer `auth.existingSecret` (secret cree par Ansible/Vault) plutot que secrets aleatoires, pour reproductibilite. Source: https://raw.githubusercontent.com/bitnami/charts/main/bitnami/postgresql/README.md
- **NetworkPolicies (Cilium)**:
  - n autoriser l acces TCP 5432 qu aux namespaces/workloads autorises.

_Source: https://docs.k3s.io/cluster-access_

### Data Architecture Patterns

Patterns data/DB sur Kubernetes (mono-noeud):

- **StatefulSet + PVC** pour Postgres:
  - identite stable, stockage persistant, ordonnancement de demarrage/arret. Source: https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/
- **Secrets + Service stable**:
  - un Service "primary" stable pour les apps, credentials via Secret.
- **Backups (optionnel au debut, mais a prevoir)**:
  - au minimum: dump logique + archive; idealement: WAL archiving/PITR (quand S3 dispo).

_Source: https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/_

### Deployment and Operations Architecture

Pattern ops "rejouable":

- **Configuration K3s par fichier**:
  - centraliser dans `/etc/rancher/k3s/config.yaml` (template Ansible), plutot que multiplier les flags ad-hoc.
  - Source: https://docs.k3s.io/installation/configuration
- **Gestion des composants K3s**:
  - desactiver Traefik si Caddy est choisi; comprendre les composants packages. Source: https://docs.k3s.io/installation/packaged-components
- **Helm deployments robustes** (Ansible):
  - utiliser `kubernetes.core.helm` avec `wait: true`, `timeout`, et `atomic: true` pour rollback automatique en cas d echec. Source: https://docs.ansible.com/ansible/latest/collections/kubernetes/core/helm_module.html
- **Glue resources via `k8s`**:
  - namespaces, secrets, ingress, networkpolicies, etc. Source: https://docs.ansible.com/ansible/latest/collections/kubernetes/core/k8s_module.html

_Source: https://docs.ansible.com/ansible/latest/collections/kubernetes/core/helm_module.html_

## Implementation Approaches and Technology Adoption

### Technology Adoption Strategies

Approche conseillee (mono-noeud, helm-first, HA plus tard):

- **Adoption progressive (Day-0/Day-1/Day-2)**: installer d abord la base (OS + K3s), puis ajouter les briques Kubernetes via Helm (monitoring, PostgreSQL), puis seulement ensuite les sujets "ops" (upgrades, backups, tests de restore, durcissement).
- **"Config as code"**: tout ce qui est parametrage (K3s `config.yaml`, `values.yaml` Helm, manifests de glue) reste versionne dans Git. L execution Ansible doit rester idempotente et rejouable.
- **Convergence vers HA**: en mono-noeud, on assume une instance PostgreSQL unique (pas de HA possible). La trajectoire multi-noeuds passera plutot par un operator (ex: CloudNativePG) quand on aura 3+ noeuds et un stockage/CSI adequat.

Points concrets a derisquer des le debut:
- Secrets: basculer sur `auth.existingSecret` (ou equivalent) et gerer les credentials via Ansible Vault / secret management, plutot que laisser le chart generer des mots de passe non maitrises.
- Monitoring: activer les metrics PostgreSQL (exporter) et integrer au Prometheus Operator via `ServiceMonitor`, en alignant labels/selector avec `kube-prometheus-stack` (selon sa configuration).

_Source: https://docs.ansible.com/ansible/2.7/user_guide/playbooks_best_practices.html_

### Development Workflows and Tooling

Workflow minimal, robuste, et compatible "solo-dev" :

- **Repo structure**: inventaire + `group_vars/host_vars`, roles par domaine (os, k3s, helm, monitoring, postgresql), et playbooks "phase" (bootstrap, deploy, upgrade, validate).
- **Collections explicites + FQCN**: utiliser la collection `kubernetes.core` pour piloter le cluster et ecrire les modules en FQCN (`kubernetes.core.helm`, `kubernetes.core.k8s`, etc.) pour eviter les ambiguitees.
- **Linting local + CI**:
  - `ansible-lint` (config `.ansible-lint.yml` ou `.config/ansible-lint.yml`) + exceptions documentees.
  - pre-commit pour imposer les checks avant PR/merge.

_Source: https://docs.ansible.com/projects/lint/configuring/_

### Testing and Quality Assurance

Strate de tests pragmatique (IaC):

- **Statique**:
  - `ansible-lint` + validation YAML.
  - rendu Helm en "dry" via `kubernetes.core.helm_template` pour detecter des regressions de values avant de toucher le cluster.
- **Role testing**:
  - Molecule pour tester roles/playbooks (au moins: syntax, converge, idempotence), avec des scenarios Docker/VM selon faisabilite.
- **Smoke tests cluster** (post-deploy):
  - `kubernetes.core.k8s_info` / `helm_info` pour verifier que les releases sont "deployed", que les Pods sont Ready, PVC Bound, Services presents.
  - checks fonctionnels: un `psql` depuis un Pod "debug" dans le namespace pour valider connectivite/auth (optionnel mais utile).

_Source: https://docs.ansible.com/projects/molecule/_

### Deployment and Operations Practices

Deploiements Helm via Ansible:
- utiliser `kubernetes.core.helm` avec `wait: true`, `timeout`, et idealement `atomic: true` pour limiter les etats "a moitie deployes" (rollback automatique en cas d echec).
- separer les dependances:
  1. kube-prometheus-stack (CRDs + Prometheus Operator)
  2. PostgreSQL (avec metrics + ServiceMonitor)

Upgrade K3s:
- documenter et rejouer les options de l install initiale (variables `INSTALL_K3S_*`, `K3S_*`), car re-executer le script d install pour upgrade peut ecraser des parametres si on ne les repasse pas.
- prevoir une routine "upgrade" (dry run + backup datastore + upgrade + checks).

_Source: https://docs.k3s.io/upgrades/manual_

### Team Organization and Skills

Competences minimales a couvrir (meme en solo):
- Linux (systemd, reseau, firewall)
- Kubernetes/K3s (objets de base, kubeconfig, namespaces, troubleshooting)
- Helm (values, upgrades, rollback)
- Ansible (inventory/vars/roles, idempotence, vault, tags)
- Observabilite (Prometheus Operator, ServiceMonitor, dashboards Grafana)
- Postgres (sizing, connexions, sauvegardes, restore)

_Source: https://docs.ansible.com/projects/ansible/latest/playbook_guide/index.html_

### Cost Optimization and Resource Management

Mono-VPS = arbitrages clairs:
- fixer des **requests/limits** raisonnables pour Prometheus/Grafana et Postgres (eviter l eviction / l OOM en charge).
- ajuster la **retention Prometheus** et limiter les components non necessaires (ex: certains exporters/dashboards) si la RAM est limitee.
- surveiller IOPS et espace disque (PVC Postgres + TSDB Prometheus).

_Source: https://raw.githubusercontent.com/prometheus-community/helm-charts/main/charts/kube-prometheus-stack/values.yaml_

### Risk Assessment and Mitigation

Risques majeurs et mitigations:

- **SPOF mono-noeud (disque/host)**: pas de HA possible. Mitigation: backups + tests de restore, et trajectoire vers multi-noeuds.
- **Upgrades**:
  - Upgrade K3s sans snapshot datastore = rollback complique. Mitigation: snapshot/backup avant upgrade (meme en mono-noeud).
  - Rollback K3s implique downgrade binaire + restauration du datastore (contrainte forte).
- **Monitoring "non scrape"**: `ServiceMonitor` non match par selector Prometheus. Mitigation: maitriser selectors/labels cote kube-prometheus-stack + chart PostgreSQL.
- **Secrets**: fuite kubeconfig/admin ou credentials DB. Mitigation: permissions strictes + Ansible Vault + RBAC minimal (evolution).

_Source: https://docs.k3s.io/upgrades/roll-back_

## Technical Research Recommendations

### Implementation Roadmap

1. **Socle VPS**: hardening (SSH keys only, firewall), prerequis (curl, python3/pip), utilisateurs.
2. **K3s mono-noeud**: install + config file `/etc/rancher/k3s/config.yaml`, kubeconfig accessible en securise.
3. **Acces cluster depuis Ansible**: recuperation kubeconfig, installation `kubernetes.core` + client python, installation binaire `helm` sur le controller.
4. **Monitoring**: deploy `kube-prometheus-stack` (namespace `monitoring`) + verifs (Prometheus up, Grafana up).
5. **PostgreSQL Helm**: deploy bitnami/postgresql (namespace `database`), PVC, secrets geres (`existingSecret`), metrics + ServiceMonitor.
6. **Ops**: runbooks (upgrade K3s, upgrade charts), alerting minimal (disk, pod restarts, exporter down), et "validate" playbook.
7. **Backups (optionnel)**: dump logique au debut, puis (quand multi-noeuds + object storage) bascule vers un operator type CNPG pour PITR/WAL archiving.

### Technology Stack Recommendations

- Cluster: K3s (runtime par defaut, pas de chantier Docker/containerd).
- DB (mono): Helm chart PostgreSQL (bitnami/postgresql) + PVC.
- Observabilite: `kube-prometheus-stack` + `ServiceMonitor` Postgres.
- IaC: Ansible + collection `kubernetes.core` (modules `helm`, `k8s`, `k8s_info`) + `ansible-lint`.
- Trajectoire HA: CloudNativePG quand multi-noeuds (replicas, failover, backups).

_Source: https://cloudnative-pg.io/documentation/current/_

### Skill Development Requirements

- Maitriser `kubernetes.core.helm` / `kubernetes.core.k8s` (kubeconfig, idempotence, gestion CRDs).
- Maitriser troubleshooting K3s (logs systemd, kube-system pods, reseau/CNI).
- Maitriser Prometheus Operator (ServiceMonitor selectors, alerting basique).
- Maitriser basiques Postgres (auth, connexions, vacuum/maintenance, backups/restore).

### Success Metrics and KPIs

- **Provisioning**: temps pour (re)deployer from-scratch, et taux de reussite d un run Ansible idempotent.
- **Disponibilite**: uptime DB (sur mono-noeud), taux d erreurs applicatives liees a la DB.
- **Sante storage**: occupation disque, croissance PVC, alerts de saturation.
- **Monitoring**: taux de targets scrape OK (kube + postgres_exporter), disponibilite Grafana.
- **Backups** (si actives): RPO (age dernier backup), RTO (temps de restore teste), taux de restores reussis (tests reguliers).

---

# Deployer PostgreSQL sur K3s (mono-noeud) via Helm: Recherche technique complete (Ansible + Prometheus/Grafana)

## Executive Summary

Ce rapport decrit une approche **helm-first** pour deployer PostgreSQL sur un cluster **K3s mono-noeud** (VPS Ubuntu), automatisee avec **Ansible**, et instrumentee avec **Prometheus + Grafana** via `kube-prometheus-stack`. Le design assume les contraintes d un mono-noeud: **pas de HA reelle**, stockage local comme SPOF, et un focus sur la **reproductibilite** (idempotence) + les **patterns d exploitation** (monitoring, upgrades, backups optionnels).

La recommendation pragmatique est d installer PostgreSQL via un chart Helm (ex: Bitnami), d activer l exporter Prometheus et de brancher les metriques a Prometheus Operator via `ServiceMonitor`, puis de construire une trajectoire d evolution (multi-noeuds, operator Postgres type CloudNativePG) quand les prerequis HA sont reunis.

**Key Technical Findings:**

- K3s se pilote proprement via un fichier `/etc/rancher/k3s/config.yaml` et expose un kubeconfig admin par defaut a `/etc/rancher/k3s/k3s.yaml` (a traiter comme un secret).  
- L automation Ansible cote cluster passe surtout par la collection `kubernetes.core` (`helm`, `k8s`, `k8s_info`), avec prerequis "controller" (helm binaire + client python kubernetes).  
- `kube-prometheus-stack` apporte Prometheus Operator (CRDs `ServiceMonitor`/`PodMonitor`) et Grafana; la selection des ServiceMonitors est gouvernee par la config du Prometheus spec (selector/labels).  
- Sur mono-noeud, la scalabilite DB est d abord verticale; la fiabilite depend des backups et de la discipline d upgrade (snapshots datastore K3s, runbooks).

**Technical Recommendations:**

- Structurer l IaC en roles Ansible par domaine + playbooks "phase" + values Helm versionnes.
- Deployer dans l ordre: K3s -> kube-prometheus-stack -> PostgreSQL (metrics+ServiceMonitor) -> hardening/ops.
- Mettre en place des KPIs d exploitation (scrape OK, saturation disque, restarts) des le depart.
- Preparer la trajectoire HA (multi-noeuds + operator CNPG) sans l implementer tant que le cluster reste mono-noeud.

## Table of Contents

1. Introduction et methodologie
2. Paysage technique et patterns d architecture
3. Approches d implementation et bonnes pratiques
4. Stack technique, evolution et tendances
5. Patterns d integration et interop
6. Performance et scalabilite (mono-noeud)
7. Securite et conformite (baseline)
8. Recommandations techniques strategiques
9. Roadmap d implementation et risques
10. Future outlook (vers multi-noeuds/HA)
11. Methodologie et sources
12. Annexes (checklists + snippets)

## 1. Introduction et methodologie

### Significance

L objectif est de construire un environnement K8s **maitrise** sur VPS, avec une DB PostgreSQL pour des workloads applicatifs, et une observabilite standard. Le choix K3s + Helm + Ansible privilegie une mise en route rapide, mais necessite de cadrer les pre-requis (kubeconfig, helm binaire, libs python) et les pratiques d exploitation (upgrades, monitoring, backups).

_Source: https://docs.k3s.io/cluster-access_

### Methodologie

- Analyse des besoins (`final/besoin.md`) et des contraintes (mono-noeud, runtime par defaut, HA future).
- Verification sur docs officielles: K3s, Kubernetes objets (StatefulSet), Ansible `kubernetes.core`, charts Helm (Postgres, kube-prometheus-stack).
- Extraction des "objets Ansible" et du sequencing pour obtenir un deploiement rejouable + observable.

## 2. Paysage technique et patterns d architecture

### Current Technical Architecture Patterns

- **K3s mono-noeud** sur VPS Ubuntu.
- **Helm** pour les composants applicatifs "packaged" (monitoring, PostgreSQL).
- **Stateful workload**: Postgres en StatefulSet/PVC (RWO) et Service stable.

_Source: https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/_

### System Design Principles and Best Practices

- Separation bootstrap (OS/K3s) vs deploiement cluster (Helm/K8s).
- Idempotence Ansible (roles, vars, templates, handlers).
- "Values as code" + environnementalisation (dev/prod) via `values.yaml`.

_Source: https://docs.ansible.com/ansible/2.7/user_guide/playbooks_best_practices.html_

## 3. Approches d implementation et bonnes pratiques

### Current Implementation Methodologies

- Automatiser l installation/upgrade de charts avec `kubernetes.core.helm` (attente readiness, timeouts, rollback en cas d echec).
- Utiliser `kubernetes.core.k8s` pour les ressources "glue" (Namespaces, Secrets, Ingress, NetworkPolicies).
- Tests: lint + rendu templates + smoke tests via `k8s_info`.

_Source: https://docs.ansible.com/ansible/latest/collections/kubernetes/core/helm_module.html_

### Implementation Framework and Tooling

- `ansible-lint` + pre-commit + CI pour garder l IaC propre.
- Molecule pour tester roles/playbooks (au moins: converge + idempotence).

_Source: https://docs.ansible.com/projects/molecule/_

## 4. Stack technique, evolution et tendances

### Current Technology Stack Landscape

- K3s: distribution Kubernetes "light" et opinionnee (packaged components, config file).
- kube-prometheus-stack: Prometheus Operator + Prometheus + Grafana, CRDs `ServiceMonitor`.
- PostgreSQL: chart Helm (mono), exporter Prometheus active.

_Source: https://raw.githubusercontent.com/prometheus-community/helm-charts/main/charts/kube-prometheus-stack/README.md_

### Technology Adoption Patterns

- Demarrage via chart Helm en mono-noeud (simplicite).
- Bascule vers operator (CNPG) lorsque HA/backups declaratifs deviennent un besoin (multi-noeuds + storage/CSI).

_Source: https://cloudnative-pg.io/documentation/current/_

## 5. Patterns d integration et interop

### Current Integration Approaches

- Acces cluster: kubeconfig K3s par defaut; si acces distant, ajuster l endpoint `server:` et verrouiller les permissions.
- Observabilite: ServiceMonitor pour brancher l exporter Postgres a Prometheus Operator; la selection depend de selectors/labels.
- Secrets: preferer secrets fournis par IaC (`existingSecret`) pour reproductibilite.

_Source: https://docs.k3s.io/cluster-access_

### Interoperability Standards and Protocols

- Kubernetes API (HTTPS) via kubeconfig.
- Scrape Prometheus (HTTP) via Service/ServiceMonitor.
- PostgreSQL TCP 5432 via Service ClusterIP.

_Source: https://docs.ansible.com/projects/ansible/latest/collections/kubernetes/core/k8s_module.html_

## 6. Performance et scalabilite (mono-noeud)

### Performance Characteristics and Optimization

- Postgres: scaling vertical; attention a l I/O disque et a la memoire.
- Prometheus: retention et ressources a calibrer, sinon effet de bord sur le noeud unique.

_Source: https://raw.githubusercontent.com/prometheus-community/helm-charts/main/charts/kube-prometheus-stack/values.yaml_

### Scalability Patterns and Approaches

- Passage multi-noeuds = prerequis HA: anti-affinite, PDB, stockage distribue/CSI.
- K3s multi-serveur: prevoir datastore adapte (embedded etcd ou externe) au lieu de SQLite.

_Source: https://docs.k3s.io/datastore_

## 7. Securite et conformite (baseline)

### Security Best Practices and Frameworks

- Kubeconfig admin: permissions strictes et distribution minimale.
- Secrets DB: vault/secret management, rotation possible, pas de credentials en clair.
- NetworkPolicy (si CNI/policy engine): restreindre acces a 5432 aux workloads autorises.

_Source: https://docs.k3s.io/cluster-access_

## 8. Recommandations techniques strategiques

- Definir un "contrat" d environnements (namespaces, conventions de labels, secrets, ingress).
- Garder l ordre d installation stable (CRDs monitoring avant ServiceMonitor externes).
- Mettre des runbooks Day-2 (upgrade K3s, upgrade charts, restore).

_Source: https://docs.k3s.io/upgrades_

## 9. Roadmap d implementation et risques

### Technical Implementation Framework

Phases:
1) OS/K3s -> 2) Helm repos + monitoring -> 3) Postgres -> 4) durcissement -> 5) backups/tests -> 6) upgrades/standardisation.

### Implementation Risks

- Mono-noeud = SPOF (host/disk).
- Upgrades: rollback K3s necessite downgrade + restauration datastore, donc snapshots avant upgrade.
- ServiceMonitor non scrape si selectors mal alignes.

_Source: https://docs.k3s.io/upgrades/roll-back_

## 10. Future outlook (vers multi-noeuds/HA)

- K3s multi-noeuds (3+) + stockage CSI fiable.
- PostgreSQL HA via operator (CNPG): replicas, failover, rolling updates; backups physiques + WAL archiving (object storage / snapshots).

_Source: https://cloudnative-pg.io/documentation/1.24/operator_capability_levels/_

## 11. Methodologie et sources

Sources principales (docs officielles / upstream):
- K3s (cluster access, config, datastore, upgrades)
- Kubernetes docs (StatefulSet)
- Ansible `kubernetes.core` (modules helm/k8s) + Molecule + ansible-lint
- Helm charts (kube-prometheus-stack, Bitnami PostgreSQL, values/README)
- CloudNativePG (trajectoire HA/backups)

## 12. Annexes (checklists + snippets)

Checklist "validate" (post-run Ansible):
- `kubectl get nodes`, `kubectl get pods -A`
- `kubectl get pvc -A` (PVC Bound pour Postgres)
- `kubectl get svc -n database` (Service DB)
- `kubectl get servicemonitors -A` + verification targets Prometheus
- test connectivite `psql` depuis un Pod debug


