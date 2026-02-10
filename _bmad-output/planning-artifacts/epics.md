---
stepsCompleted: [1, 2, 3, 4]
inputDocuments:
  - '_bmad-output/planning-artifacts/prd.md'
  - '_bmad-output/planning-artifacts/architecture.md'
  - '_bmad-output/planning-artifacts/product-brief-k3s-mono-pgsql-2026-02-10.md'
  - '_bmad-output/planning-artifacts/research/technical-k3s-mono-noeud-ovh-vpn-monitoring-postgresql-standard-research-2026-02-10.md'
workflowType: 'create-epics-and-stories'
project_name: 'k3s-mono-pgsql'
user_name: 'Jules'
date: '2026-02-10'
lastStep: 4
status: 'complete'
completedAt: '2026-02-10'
communication_language: 'French'
document_output_language: 'French'
---

# k3s-mono-pgsql - Decoupage Epics & Stories

## Vue d'ensemble

Ce document transforme le PRD et l'architecture en epics et stories exploitables par l'equipe implementation, sans perimetre UX/UI.

## Inventaire des exigences

### Exigences fonctionnelles

FR1: Les operateurs peuvent provisionner l'environnement cible via une execution unique reproductible.
FR2: Les operateurs peuvent rejouer le provisioning sans perte d'etat operationnel.
FR3: Les operateurs peuvent executer le provisioning par sous-domaines (reseau, orchestration, observabilite, base).
FR4: Les operateurs peuvent verifier automatiquement la conformite de baseline apres provisioning.
FR5: Les operateurs peuvent administrer la plateforme uniquement via un canal prive chiffre.
FR6: Les operateurs peuvent limiter l'exposition publique aux seuls ports necessaires.
FR7: Les operateurs peuvent garantir qu'aucune interface admin/DB n'est exposee publiquement.
FR8: Les operateurs peuvent gerer les secrets sans stockage en clair dans Git.
FR9: Les equipes peuvent decrire l'etat cible en mode declaratif versionne.
FR10: Les equipes peuvent synchroniser automatiquement l'etat Git vers l'etat deploye.
FR11: Les equipes peuvent suivre la convergence et diagnostiquer la derive de configuration.
FR12: Les equipes peuvent revenir a un etat valide precedent en cas de regression.
FR13: Les operateurs peuvent collecter les metriques plateforme et base de donnees.
FR14: Les operateurs peuvent visualiser la sante via des tableaux de bord operationnels.
FR15: Les operateurs peuvent recevoir des alertes email sur indisponibilite et saturation disque.
FR16: Les operateurs peuvent reduire le bruit d'alerte (grouping, repeat control).
FR17: Les operateurs peuvent deployer PostgreSQL standard persistant dans le cluster.
FR18: Les operateurs peuvent acceder a PostgreSQL uniquement via reseau prive d'administration.
FR19: Les operateurs peuvent verifier la persistence des donnees apres redemarrages.
FR20: Les operateurs peuvent monitorer la disponibilite et les signaux critiques de PostgreSQL.
FR21: Les operateurs peuvent executer des sauvegardes logiques planifiees avec retention.
FR22: Les operateurs peuvent verifier l'integrite et la presence des artefacts de sauvegarde.
FR23: Les operateurs peuvent executer un restore drill complet sur base de test vide.
FR24: Les operateurs peuvent mesurer et enregistrer duree de restauration et perte de donnees.
FR25: Les equipes peuvent tracer les decisions operations majeures dans un journal versionne.
FR26: Les equipes peuvent lier chaque exigence critique a un critere de validation observable.
FR27: Les equipes peuvent auditer les changements de configuration impactant la plateforme.

### Exigences non fonctionnelles

NFR1: Les checks de sante repondent en <= 2s au p95.
NFR2: Les changements critiques convergent en <= 5 minutes pour 95% des cas planifies.
NFR3: Les canaux d'administration restent prives/chiffres avec controle d'acces actif.
NFR4: Aucune credentielle critique n'apparait en clair dans Git.
NFR5: Les logs d'erreur n'exposent aucun secret en clair.
NFR6: Les composants critiques maintiennent >= 99.5% de disponibilite mensuelle.
NFR7: Les sauvegardes planifiees atteignent >= 99% de succes mensuel.
NFR8: Le restore drill mensuel respecte un RTO cible <= 60 minutes.
NFR9: La collecte supporte x3 volume metriques sans perte de series critiques.
NFR10: La plateforme supporte x2 services deployes sans degradation convergence > 15%.
NFR11: Les alertes critiques email gardent >= 99% de livraison.
NFR12: Les schemas des interfaces ops restent compatibles entre versions mineures consecutives.

### Exigences complementaires

- Structure projet imposant des frontieres claires: `infra/`, `gitops/`, `scripts/`, `docs/`.
- Initialisation du scaffold IaC avant execution des stories fonctionnelles.
- Versions epinglees: ansible-core `2.20.2`, K3s `v1.35.0+k3s3`, Argo CD `v3.3.0`, kube-prometheus-stack `81.6.1`, PostgreSQL chart `17.0.2`.
- Politique securite: SSH key-only, root disabled, VPN-first, DB/admin non exposees.
- Secrets obligatoirement chiffres avec SOPS `v3.11.0` + age `v1.3.1`.
- Politique ports publics: `22/80/443/51820` uniquement; `5432` prive.
- CI bloque toute violation lint/schema/secrets/traceabilite.
- Aucun livrable UX/UI dans ce projet.

### FR Coverage Map

FR1: Epic 1 - Provisioning reproductible.
FR2: Epic 1 - Rejeu idempotent.
FR3: Epic 1 - Execution par domaine.
FR4: Epic 1 - Verification baseline.
FR5: Epic 1 - Acces admin prive chiffre.
FR6: Epic 1 - Limitation exposition publique.
FR7: Epic 1 - Isolation admin/DB.
FR8: Epic 1 - Gestion secrets chiffree.
FR9: Epic 2 - Source of truth Git declarative.
FR10: Epic 2 - Synchronisation GitOps automatique.
FR11: Epic 2 - Detection derive et diagnostic.
FR12: Epic 2 - Rollback controle.
FR13: Epic 3 - Collecte metriques.
FR14: Epic 3 - Dashboards operations.
FR15: Epic 3 - Alertes email critiques.
FR16: Epic 3 - Reduction bruit d'alerte.
FR17: Epic 4 - Deploiement PostgreSQL persistant.
FR18: Epic 4 - Acces DB prive.
FR19: Epic 4 - Verification durabilite donnees.
FR20: Epic 4 - Monitoring signaux DB.
FR21: Epic 5 - Sauvegardes planifiees.
FR22: Epic 5 - Verification integrite sauvegardes.
FR23: Epic 5 - Restore drill complet.
FR24: Epic 5 - Mesure RTO/perte.
FR25: Epic 5 - Journal decisions ops.
FR26: Epic 5 - Traceabilite exigences/validation.
FR27: Epic 5 - Audit changements configuration.

## Epic List

### Epic 1: Fondation Securisee de la Plateforme
Livrer un socle VPS durci, administrable en prive, rejouable et sans secrets en clair.
**FRs covered:** FR1, FR2, FR3, FR4, FR5, FR6, FR7, FR8

### Epic 2: Livraison Cluster Pilotee par GitOps
Mettre en place un cluster mono-noeud et une chaine GitOps deterministe avec rollback.
**FRs covered:** FR9, FR10, FR11, FR12

### Epic 3: Observabilite et Alerting Operationnels
Fournir visibilite temps reel et alertes actionnables des le jour 1.
**FRs covered:** FR13, FR14, FR15, FR16

### Epic 4: Service PostgreSQL Securise
Fournir une base PostgreSQL persistante, privee et monitorable dans le cluster.
**FRs covered:** FR17, FR18, FR19, FR20

### Epic 5: Assurance Recovery et Gouvernance
Garantir backup/restore mesurables et une gouvernance operationnelle auditable.
**FRs covered:** FR21, FR22, FR23, FR24, FR25, FR26, FR27

## Epic 1: Fondation Securisee de la Plateforme

Livrer un socle VPS durci, administrable en prive, rejouable et sans secrets en clair.

### Story 1.1: Provisionner le socle hote durci

En tant qu'operateur,
Je veux lancer un playbook baseline sur un VPS neuf,
Afin d'obtenir un hote securise pret pour le bootstrap cluster.

**Acceptance Criteria:**

**Etant donne** un VPS OVH neuf et un inventory Ansible valide
**Quand** le playbook baseline est execute
**Alors** SSH key-only est impose, root login est desactive et le firewall est actif
**Et** les prerequis systeme sont installes correctement.

**Etant donne** la fin du provisioning baseline
**Quand** les checks de conformite sont lances
**Alors** les controles de hardening passent
**Et** les preuves sont conservees pour audit.

### Story 1.2: Garantir idempotence et execution par tags

En tant qu'operateur,
Je veux rejouer les playbooks sans derive et cibler des domaines,
Afin de maintenir la plateforme sans effets de bord.

**Acceptance Criteria:**

**Etant donne** un environnement deja provisionne
**Quand** le meme playbook est rejoue sans changement
**Alors** aucun changement inattendu n'est applique
**Et** la disponibilite des services n'est pas degradee.

**Etant donne** un besoin limite a un domaine
**Quand** l'operateur lance une execution taggee
**Alors** seuls les roles cibles sont executes
**Et** les autres domaines restent inchanges.

### Story 1.3: Activer un acces administration VPN-first

En tant qu'operateur,
Je veux administrer la plateforme uniquement via WireGuard,
Afin d'eviter toute exposition internet des surfaces sensibles.

**Acceptance Criteria:**

**Etant donne** la configuration serveur/client WireGuard appliquee
**Quand** un client autorise se connecte
**Alors** les interfaces admin privees sont accessibles via VPN
**Et** l'acces est refuse hors VPN.

**Etant donne** un scan depuis internet public
**Quand** les ports sont verifies
**Alors** seuls `22/80/443/51820` sont ouverts
**Et** PostgreSQL et les interfaces admin ne sont pas exposes.

### Story 1.4: Initialiser la gestion des secrets chiffres

En tant qu'ingenieur plateforme,
Je veux stocker les secrets via SOPS+age,
Afin d'eliminer les secrets en clair dans Git.

**Acceptance Criteria:**

**Etant donne** des fichiers secrets infra/cluster
**Quand** ils sont commites
**Alors** les valeurs sont chiffrees avec age et metadata SOPS
**Et** la lecture en clair requiert une cle autorisee.

**Etant donne** les controles CI secrets
**Quand** un secret en clair est detecte
**Alors** la pipeline echoue
**Et** le merge est bloque jusqu'a correction.

## Epic 2: Livraison Cluster Pilotee par GitOps

Mettre en place un cluster mono-noeud et une chaine GitOps deterministe avec rollback.

### Story 2.1: Installer K3s mono-noeud version epinglee

En tant qu'operateur,
Je veux installer K3s mono-noeud avec versions controlees,
Afin d'obtenir une base cluster stable et reproductible.

**Acceptance Criteria:**

**Etant donne** un hote durci et accessible via VPN
**Quand** le role bootstrap cluster est execute
**Alors** K3s `v1.35.0+k3s3` est installe avec Traefik, ServiceLB et local-path
**Et** les composants coeur deviennent sains.

**Etant donne** le cluster demarre
**Quand** l'etat node/addons est verifie
**Alors** le noeud est Ready
**Et** les preuves de validation sont journalisees.

### Story 2.2: Bootstrap Argo CD en App-of-Apps

En tant qu'operateur plateforme,
Je veux initialiser Argo CD avec une root app,
Afin de piloter les deploiements depuis Git.

**Acceptance Criteria:**

**Etant donne** les manifests bootstrap Argo disponibles
**Quand** ils sont appliques
**Alors** Argo CD est installe et la root app est creee
**Et** les applications filles convergent vers l'etat desire.

**Etant donne** une modification mergee dans gitops
**Quand** la reconciliation Argo tourne
**Alors** le cluster converge automatiquement
**Et** l'etat de sync est visible pour l'operateur.

### Story 2.3: Mettre en place derive et rollback

En tant qu'operateur,
Je veux detecter la derive et restaurer rapidement un etat valide,
Afin de contenir les regressions de configuration.

**Acceptance Criteria:**

**Etant donne** un changement manuel hors Git
**Quand** Argo compare etat live et desired
**Alors** la derive est marquee OutOfSync
**Et** une resync permet le retour a l'etat cible.

**Etant donne** un commit de configuration defectueux
**Quand** le commit est revert puis resync
**Alors** l'etat precedent stable est restaure
**Et** l'action est tracee avec correlation id.

### Story 2.4: Appliquer les gates CI de qualite

En tant qu'equipe,
Je veux des gates CI sur manifests/playbooks/secrets/traceabilite,
Afin d'empecher l'introduction de changements dangereux.

**Acceptance Criteria:**

**Etant donne** une pull request infra ou gitops
**Quand** la CI est executee
**Alors** lint YAML, validation schema et scan secrets tournent
**Et** le merge est bloque en cas d'echec.

**Etant donne** un changement critique
**Quand** la verification de traceabilite est effectuee
**Alors** les references exigences/ADR sont obligatoires
**Et** leur absence est remontee en erreur bloquante.

## Epic 3: Observabilite et Alerting Operationnels

Fournir visibilite temps reel et alertes actionnables des le jour 1.

### Story 3.1: Deployer metriques et dashboards de base

En tant qu'operateur,
Je veux deployer la stack monitoring avec tableaux de bord,
Afin de visualiser la sante plateforme et DB en continu.

**Acceptance Criteria:**

**Etant donne** les manifests monitoring synchronises
**Quand** kube-prometheus-stack est deploye
**Alors** Prometheus, Alertmanager et Grafana sont healthy
**Et** les metriques node/cluster/postgres sont collectees.

**Etant donne** un acces operateur via VPN
**Quand** les dashboards standards sont ouverts
**Alors** les indicateurs critiques sont visibles
**Et** l'affichage reste exploitable en charge nominale.

### Story 3.2: Configurer alertes email actionnables

En tant qu'operateur,
Je veux recevoir des alertes email critiques avec dedup,
Afin d'etre notifie sans bruit inutile.

**Acceptance Criteria:**

**Etant donne** un SMTP configure de facon securisee
**Quand** un incident critique est simule (node down ou disk pressure)
**Alors** une alerte email est envoyee dans la fenetre attendue
**Et** le message contient source, severite et correlation id.

**Etant donne** des alertes repetitives
**Quand** les regles de grouping/inhibition s'appliquent
**Alors** le spam d'alertes est reduit
**Et** le comportement suit le runbook incident.

### Story 3.3: Exposer statuts ops et contrat d'erreur

En tant qu'operateur,
Je veux des endpoints de statut et erreurs standardises,
Afin de fiabiliser diagnostic et automatisation.

**Acceptance Criteria:**

**Etant donne** les endpoints `/health`, `/readiness`, `/backups/status`, `/restore/status`
**Quand** ils sont appeles
**Alors** les reponses suivent un schema stable avec horodatage
**Et** le p95 health reste <= 2 secondes.

**Etant donne** une erreur validation/auth/dependance/timeout
**Quand** la reponse est retournee
**Alors** un code stable et un correlation id sont presents
**Et** aucune information sensible n'est exposee.

## Epic 4: Service PostgreSQL Securise

Fournir une base PostgreSQL persistante, privee et monitorable dans le cluster.

### Story 4.1: Deployer PostgreSQL persistant

En tant qu'operateur,
Je veux deployer PostgreSQL via chart epingle avec PVC,
Afin de fournir un service donnees stable.

**Acceptance Criteria:**

**Etant donne** les manifests postgres gitops prets
**Quand** la release est synchronisee
**Alors** le chart `17.0.2` est deploye avec succes
**Et** les PVC local-path sont bien relies.

**Etant donne** la fin de deploiement
**Quand** les probes de readiness sont verifiees
**Alors** PostgreSQL est joignable par les workloads autorises
**Et** les credentials proviennent de secrets chiffres.

### Story 4.2: Restreindre l'acces DB au reseau prive

En tant que responsable plateforme,
Je veux bloquer les acces DB non autorises,
Afin de reduire le risque d'exposition donnees.

**Acceptance Criteria:**

**Etant donne** les network policies et regles firewall appliquees
**Quand** une tentative d'acces non autorisee est faite
**Alors** la connexion est refusee
**Et** le port `5432` reste non public.

**Etant donne** une operation privilegiee DB
**Quand** l'authentification/autorisation est evaluee
**Alors** seuls les identifiants autorises passent
**Et** acteur et horodatage sont traces.

### Story 4.3: Valider durabilite donnees et monitoring DB

En tant qu'operateur,
Je veux prouver la persistence apres redemarrage et surveiller la DB,
Afin de confirmer la fiabilite du service.

**Acceptance Criteria:**

**Etant donne** un jeu de donnees de test present
**Quand** le pod DB ou le noeud est redemarre
**Alors** les donnees persistent apres reprise
**Et** le resultat est documente.

**Etant donne** les metriques DB branchees au monitoring
**Quand** un scenario de stress/incident est simule
**Alors** les signaux critiques sont visibles sur dashboard
**Et** les alertes attendues se declenchent.

## Epic 5: Assurance Recovery et Gouvernance

Garantir backup/restore mesurables et une gouvernance operationnelle auditable.

### Story 5.1: Mettre en place backups planifies avec retention

En tant qu'operateur,
Je veux des backups pg_dump planifies avec rotation,
Afin de disposer d'artefacts de restauration fiables.

**Acceptance Criteria:**

**Etant donne** la configuration de planification backup
**Quand** la fenetre planifiee s'execute
**Alors** des dumps horodates sont generes
**Et** la retention supprime les sauvegardes expirees sans impact.

**Etant donne** un nouvel artefact backup
**Quand** les verifications d'integrite tournent
**Alors** les checks (taille/checksum/metadata) passent
**Et** le statut backup est expose via endpoint ops.

### Story 5.2: Executer un restore drill mesure

En tant qu'operateur,
Je veux executer un restore drill complet et mesure,
Afin de prouver la readiness de recovery.

**Acceptance Criteria:**

**Etant donne** une base test vide et un backup valide
**Quand** le runbook restore est execute
**Alors** la restauration se termine avec succes
**Et** l'integrite des donnees restaurees est verifiee.

**Etant donne** la fin du drill
**Quand** le rapport est produit
**Alors** RTO et perte observee sont mesures
**Et** les resultats sont historises pour comparaison mensuelle.

### Story 5.3: Structurer gouvernance et piste d'audit

En tant que tech lead,
Je veux tracer les decisions et operations critiques,
Afin de garantir auditabilite et pilotage du risque.

**Acceptance Criteria:**

**Etant donne** une decision operations/architecture majeure
**Quand** elle est validee
**Alors** une entree ADR est creee ou mise a jour
**Et** les commits lies sont references.

**Etant donne** une action admin privilegiee
**Quand** les evenements sont journalises
**Alors** action, acteur, horodatage, resultat et duree sont enregistres
**Et** l'historique est exploitable en post-mortem.

### Story 5.4: Publier la documentation ops et matrice de validation

En tant qu'equipe delivery,
Je veux documenter APIs, runbooks et matrice exigences->tests,
Afin de livrer sans ambiguite implementation et QA.

**Acceptance Criteria:**

**Etant donne** les contrats API et procedures finalises
**Quand** la documentation est publiee
**Alors** schemas, auth, codes erreur et limites sont explicitement decrits
**Et** les scenarios diagnostic/remediation sont couverts.

**Etant donne** la revue de release
**Quand** la matrice de validation est controlee
**Alors** chaque FR/NFR critique est mappe a un test observable
**Et** tout trou de couverture est traite comme blocant.
