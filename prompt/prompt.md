# Cahier des charges
## Cluster Kubernetes (K3s) mono-nœud sur VPS

- **Version** : v1.1  
- **Date** : 11/02/2026  
- **Cible** : 1 VPS Ubuntu (mono-nœud), évolutif vers multi-nœuds plus tard

---

## 1) Contexte & objectifs

### 1.1 Contexte
Déployer un cluster Kubernetes léger sur **VPS mono-nœud** avec :

- Runtime : **containerd** (pas Docker)
- Datastore : **SQLite** (par défaut K3s en mono-serveur)
- CNI : **Cilium** (donc Flannel désactivé)
- Stockage persistant : **local-path-provisioner** (packagé K3s)
- Ingress : **Caddy** (avec plan de repli)
- Observabilité :
  - métriques : **VictoriaMetrics**
  - logs : **VictoriaLogs**

### 1.2 Objectifs
- Cluster opérationnel en **1 commande** de provisioning (Ansible).
- Sécurisé (**SSH key only**, root SSH off, firewall strict, audit basique).
- Reproductible (idempotent, versionné, rollback/upgrade/reset outillés).
- Évolutif vers multi-nœuds (sans refaire toute l’archi).

---

## 2) Périmètre

### 2.1 Inclus
- Provision OS (utilisateur sudo, SSH durci, firewall, journald)
- Installation K3s avec containerd (par défaut)
- Datastore **SQLite** (mode par défaut mono-serveur K3s)
- Cilium en CNI (Flannel désactivé)
- Stockage persistant via `local-path-provisioner` (packagé K3s)
- Caddy Ingress Controller
- VictoriaMetrics (stack k8s)
- VictoriaLogs (single)
- Sauvegarde/restauration datastore SQLite (dump + archive + restauration test)
- Playbooks : `provisioning`, `reset`, `upgrade`, `validation`

### 2.2 Hors périmètre (optionnel)
- ArgoCD / GitOps complet (possible plus tard)
- Vault “full” (secrets via SOPS/age ou sealed secrets plus tard)
- Multi-nœuds immédiat (mais design compatible)
- Longhorn (réintroduit plus tard si besoin RWX/backup avancé)

---

## 3) Contraintes & choix techniques (non négociables)

### 3.1 Container runtime
- **containerd** (K3s embarque containerd par défaut)

### 3.2 Datastore
- **SQLite** en phase mono-nœud (choix simplicité).
- Chemin attendu : `/var/lib/rancher/k3s/server/db/`.
- Préparer migration vers **embedded etcd** avant passage multi-nœuds HA.

### 3.3 Réseau
- **Cilium** comme CNI primaire.
- Flannel **désactivé** (`--flannel-backend=none`).
- NetworkPolicy : K3s built-in **désactivé** pour laisser Cilium gérer  
  (recommandation Cilium pour K3s).
- Option future : kube-proxy replacement (si besoin), mais par défaut on garde kube-proxy
  pour réduire la complexité.

### 3.4 Stockage
- `local-path-provisioner` pour PVC en mono-nœud.
- Pas de Longhorn en phase 1 (complexité inutile en mono-nœud).

### 3.5 Ingress
- Caddy Ingress Controller.
- Le composant Caddy doit rester **swappable** via variable Ansible (`ingress_controller`),
  avec **plan B Traefik** prêt.

### 3.6 Observabilité
- Metrics : chart `victoria-metrics-k8s-stack` (operator + vmagent + dashboards selon config)
- Logs : `victoria-logs-single` + collector (selon choix)

### 3.7 GitOps & état
- GitOps porte les **manifests** et la configuration.
- Le fichier SQLite et le token K3s ne sont **pas commités dans Git**.
- Les backups SQLite sont stockés hors Git (chiffrés), référencés par métadonnées dans GitOps.

---

## 4) Exigences sécurité (OS + cluster)

### 4.1 Accès SSH / comptes
- SSH key only
- Création d’un utilisateur sudo (opérateur)
- Root SSH désactivé
- (Recommandé) `AllowUsers`/`AllowGroups`, `PasswordAuthentication no`

### 4.2 Firewall (WAN)
Ouvrir :
- 22/tcp (SSH)
- 80/tcp (HTTP)
- 443/tcp (HTTPS)

Bloquer depuis Internet (WAN) :
- 6443/tcp (Kubernetes API) tant qu’aucun agent externe n’est requis
- Ports NodePort (30000-32767) sauf besoin explicite
- Tout le reste

Rappel K3s :
- Le serveur doit avoir 6443 accessible par les nœuds (si multi-nœuds).

### 4.3 Journalisation / audit
- Activer persistance journald
- Rotation logs
- Surveiller connexions SSH via journald (et éventuellement fail2ban)

---

## 5) Architecture cible

### 5.1 Schéma logique
- VPS (Ubuntu)
  - K3s Server (control plane + worker)
    - datastore : SQLite
    - runtime : containerd
    - CNI : Cilium
    - Storage : local-path
    - Ingress : Caddy
    - Metrics : VictoriaMetrics stack
    - Logs : VictoriaLogs single

### 5.2 Composants packagés K3s
Désactiver :
- `traefik` (remplacé par Caddy)

Laisser :
- `local-storage` (local-path-provisioner)
- `coredns`
- `metrics-server` (optionnel selon choix VM stack)

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
  - `cilium/`
  - `storage_local_path/`
  - `ingress_caddy/`
  - `backup_k3s_sqlite/`
  - `victoria_metrics/`
  - `victoria_logs/`
- `playbooks/`
  - `provisioning.yml`
  - `reset.yml`
  - `upgrade.yml`
  - `validation.yml`

### 6.2 Principes
- Idempotent
- Variables centralisées (`group_vars/all.yml` + `host_vars/*`)
- Tags Ansible (`base`, `k3s`, `cni`, `storage`, `ingress`, `backup`, `obs`)
- Validation systématique post-déploiement

---

## 7) Spécifications d’implémentation

### 7.1 Rôle `base_os`
- Installer paquets :
  - utilitaires (`curl`, `jq`, etc.)
  - outils backup (`tar`, `gzip`, `rsync`, optionnel `restic`)
- Créer user sudo + clés SSH
- Durcir sshd (root off, password off)
- Firewall (ufw/iptables/nftables)
- journald persistance + rotation

### 7.2 Rôle `k3s_server`
Installer K3s avec :
- datastore SQLite par défaut (ne pas activer `--cluster-init`)
- flannel off : `--flannel-backend=none`
- `--disable-network-policy` (recommandé côté Cilium sur K3s)
- `--disable=traefik`
- ne pas désactiver `local-storage`

Export kubeconfig (mode 600 ou 644 selon besoin).

### 7.3 Rôle `cilium`
- Installer Cilium selon doc K3s (helm/cli)
- Valider :
  - pods Cilium Ready
  - services ClusterIP fonctionnels
  - DNS OK

### 7.4 Rôle `storage_local_path`
- Vérifier que `local-path` est StorageClass par défaut
- Valider PVC/PV (write/read test)

### 7.5 Rôle `ingress_caddy`
- Déployer Caddy Ingress Controller (helm/manifests)
- Exposition :
  - soit Service `LoadBalancer` (si LB disponible)
  - soit NodePort / hostPort
- Valider :
  - ingress simple 80/443
  - terminaison TLS
- Prévoir fallback opérationnel vers Traefik si blocage de compatibilité.

### 7.6 Rôle `backup_k3s_sqlite`
- Sauvegarder :
  - `/var/lib/rancher/k3s/server/db/`
  - `/var/lib/rancher/k3s/server/token`
- Produire archives horodatées
- Chiffrer les archives (gpg/age/restic selon standard retenu)
- Tester restauration sur environnement de validation
- Publier uniquement métadonnées/rétention dans GitOps, pas les binaires DB

### 7.7 Rôle `victoria_metrics`
- Déployer `victoria-metrics-k8s-stack`
- Activer scrapes nécessaires (kubelet, apiserver, etc.) selon valeurs
- Valider dashboards + alert rules minimales

### 7.8 Rôle `victoria_logs`
- Déployer `victoria-logs-single`
- Déployer collector (selon chart recommandé)
- Valider ingestion logs (pod test + query)

---

## 8) Critères d’acceptation (Definition of Done)

### 8.1 Infra & sécurité
- SSH key only, root SSH off, user sudo OK
- Firewall : uniquement 22/80/443 ouverts WAN
- journald persistant, rotation OK

### 8.2 Cluster
- `kubectl get nodes` = Ready
- CoreDNS fonctionne
- Cilium Ready
- StorageClass `local-path` par défaut + PVC test OK
- Ingress Caddy répond sur 80/443
- VictoriaMetrics reçoit des métriques
- VictoriaLogs reçoit des logs
- Backup SQLite + restore test = OK

### 8.3 Maintenabilité
- `provisioning.yml` rejouable sans casser
- `reset.yml` purge cluster proprement
- `upgrade.yml` upgrade K3s + vérifs
- `validation.yml` sort un rapport clair (OK/KO)

---

## 9) Risques & mitigations

### 9.1 Maturité Caddy Ingress Controller
- Risque : couverture fonctionnelle/écosystème plus limitée que Traefik/NGINX.
- Mitigation : fallback Traefik prêt et activable par variable.

### 9.2 SQLite sur K3s
- Risque : pas de HA datastore, risque de perte si disque VPS KO.
- Mitigation : backups fréquents + restauration testée + stockage externe chiffré.

### 9.3 Backup SQLite “dans Git”
- Risque : fuite de secrets (token), dépôts lourds/binaires, historique difficile.
- Mitigation : GitOps pour manifests uniquement, backups hors Git avec rétention.

---

## 10) Roadmap (pragmatique)
- Phase 1 : base_os + K3s(SQLite) + Cilium + Caddy + local-path (MVP)
- Phase 2 : VictoriaMetrics + VictoriaLogs
- Phase 3 : backup/restore SQLite industrialisé (tests réguliers)
- Phase 4 : migration embedded etcd + stockage distribué (Longhorn ou autre) pour multi-nœuds
