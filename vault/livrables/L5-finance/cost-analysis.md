---
type: rncp-livrable
bloc: 4
livrable: 5
titre: Analyse financière du projet CryptoBot
diplome: RNCP38919
projet: cryptobot
statut: draft-v1
tags:
  - cryptobot
  - rncp
  - bloc4
  - finance
  - livrable5
created: 2026-04-14
owner: L5-Finance-Soutenance
sources:
  - "[[CryptoBot/avril/planning/sprint-plan]]"
  - "[[CryptoBot/avril/planning/sprint-summary]]"
  - "[[_other/common/projects/SAP/planning/roadmap]]"
  - "[[CryptoBot/avril/equipes/05-devops-infra]]"
  - "[[CryptoBot/avril/architecture/dp01-docker-infrastructure]]"
  - "[[CryptoBot/avril/history/decisions]]"
---

# Livrable 5 — Analyse financière CryptoBot (Bloc 4 RNCP38919)

> **Disclaimer.** Tous les chiffres ci-dessous sont des **hypothèses de travail** établies par l'agent L5-Finance pour la soutenance RNCP. Les TJM, les volumes d'effort et les coûts infra doivent être **validés par Jules (PO)** avant publication officielle. Les chiffres marqués `HYPOTHÈSE` sont flaggés explicitement dans le texte.

Le document suit la structure RNCP Bloc 4 « Piloter un projet » : méthode de chiffrage, décomposition CAPEX/OPEX, scénarios et plan de financement. Les sources sont des pages Obsidian du vault (wikilinks) qui constituent la source de vérité technique du projet.

---

## 1. Méthode de chiffrage

### 1.1 Approche

Le coût total du projet est modélisé comme :

```
Coût total HT = Capacité humaine
              + Infrastructure (récurrent + one-shot)
              + Outils & services
              + Équipement dev
              + Buffer risque (20 %)
```

L'horizon retenu est **6 sprints** (S11 -> S16, cf. [[CryptoBot/avril/planning/sprint-plan]]), soit **~12 semaines calendaires** du 14 mars 2026 au 11 juin 2026 (soutenance).

### 1.2 Hypothèses structurantes

| # | Hypothèse | Valeur | Source |
|---|-----------|--------|--------|
| H1 | TJM junior Data Eng (marché FR 2026) | 400 € HT | `HYPOTHÈSE` — benchmark Malt / Free-Work Q1 2026 |
| H2 | TJM lead archi / PO junior | 500 € HT | `HYPOTHÈSE` — surcote 25 % vs H1 (responsabilité + archi) |
| H3 | TJM DevOps ponctuel (Ansible / monitoring) | 500 € HT | `HYPOTHÈSE` — tarif renfort freelance |
| H4 | Capacité effective par dev | 20-25 HJ / sprint (soit ~25 h / semaine) | [[CryptoBot/avril/planning/sprint-summary]] §Vélocité |
| H5 | 1 sprint = 2 semaines calendaires | 10 jours ouvrés | [[CryptoBot/avril/planning/sprint-plan]] |
| H6 | Contexte académique, pas de facturation réelle | coût = coût d'opportunité | Interne |
| H7 | Buffer risque contingence | 20 % | [[CryptoBot/avril/planning/risks]] — R1/R2/R7 = proba ≥ 50 % |
| H8 | TVA 20 % (taux normal FR) | applicable hors école | Standard |

### 1.3 Périmètre

**Inclus** : développement S11-S16 (ETL, ML Phase 1, API, frontend, infra Docker, monitoring, tests, documentation, 22 diagrammes PlantUML, livrables RNCP 7+).

**Exclus** : coûts amont (sprints S1-S10 déjà réalisés en contexte école, non refacturés), maintenance post-soutenance, marketing, acquisition utilisateurs.

---

## 2. Capacité humaine

### 2.1 Tableau de charge

| Rôle | Personne | TJM HT | HJ / sprint | Sprints | HJ total | Coût HT |
|------|----------|--------|-------------|---------|----------|---------|
| PO + lead archi + Data Eng | Jules | 500 € | 10 | 6 | 60 | **30 000 €** |
| Dev backend / ML part-time | Mikael | 400 € | 5 | 6 | 30 | **12 000 €** |
| Renfort DevOps ponctuel | External | 500 € | — | spot | 5 | **2 500 €** |
| **Sous-total humain** | | | | | **95 HJ** | **44 500 € HT** |

> Note : le texte de brief évoquait 2 000 € pour le renfort DevOps, mais à 500 €/j × 5 j = 2 500 €. On retient **2 500 €** (cohérence arithmétique) et on documente l'écart comme `HYPOTHÈSE-A1` à valider.

### 2.2 Répartition effort par équipe

| Équipe | % effort | HJ | Commentaire |
|--------|---------|----|-------------|
| Data Engineering | 35 % | 33 | ETL F1/F2/F5, schéma BDD, scraping réglementaire |
| ML / Data Science | 30 % | 28 | F3 K-Means, F6 LSTM, F8 RL |
| Backend API | 15 % | 14 | F4 alertes, F7.2 paper trading API |
| Frontend UI | 10 % | 10 | F7.3 dashboards paper trading, UX personas |
| DevOps / Infra | 10 % | 10 | Docker, CI/CD, Ansible, monitoring |
| **Total** | **100 %** | **95** | Cohérent avec [[_other/common/projects/SAP/equipes/_index]] |

### 2.3 Validation vs vélocité

- Vélocité cible [[CryptoBot/avril/planning/sprint-plan]] : **16 pts / sprint**.
- Total : **62 pts** sur 6 sprints = 10,3 pts / sprint en moyenne, avec pic S15-S16 (RL) à 18 pts.
- 95 HJ / 62 pts = **1,53 HJ / pt**, ratio cohérent pour projet école (benchmarks industriels : 0,8-1,2 HJ/pt).
- L'écart de 30 % s'explique par le temps de documentation RNCP (22 diagrammes, 7 livrables) non productif.

---

## 3. Infrastructure

### 3.1 Récurrent mensuel

| Poste | Provider | Spec | Coût mensuel HT | Justification |
|-------|----------|------|-----------------|---------------|
| VPS dev/staging | OVH | VPS-2 : 4 vCPU, 8 GB RAM, 160 GB NVMe | **18 €** | Dev + CI runners + staging Docker Compose |
| VPS prod (post-S15) | OVH | VPS-4 : 8 vCPU, 32 GB RAM, 320 GB NVMe | **35 €** | Prod réelle si go-live ; optionnel école |
| Nom de domaine | OVH Registrar | `cryptobot.example` | **1 €** | 12 €/an amorti mensuellement |
| Reverse proxy CDN | Cloudflare Free | DNS + proxy + cache | **0 €** | Cf. `.claude/rules/devops-prod.md` |
| Cloudflare Pro (optionnel) | Cloudflare | Rate Limiting avancé, WAF | **20 €** | `HYPOTHÈSE` — seulement si go prod commercial |
| Certificats TLS | Let's Encrypt | Auto-renouvellement certbot | **0 €** | Sidecar docker-compose |
| GitHub Team | GitHub | 2 comptes privés | **8 €** | 4 €/user × 2 |
| MinIO (object storage) | Self-hosted VPS | Inclus VPS | **0 €** | [[CryptoBot/avril/architecture/dp01-docker-infrastructure]] |
| MLflow tracking | Self-hosted VPS | Inclus VPS | **0 €** | Postgres backend |
| Grafana + Prometheus + Loki | Self-hosted VPS | Inclus VPS | **0 €** | `.claude/rules/devops-prod.md` |
| **Sous-total mensuel** | | | **62 €** (dev only) / **97 €** (dev + prod) | |

### 3.2 Profil temporel

| Période | Configuration | Coût |
|---------|--------------|------|
| S11-S14 (mars-mai 2026, ~3 mois) | VPS-2 + domaine + GitHub | 27 € × 3 = **81 €** |
| S15-S16 (mai-juin 2026, ~1 mois chevauchement) | VPS-2 + VPS-4 + domaine + GitHub | 62 € × 1 = **62 €** |
| Post-soutenance buffer (juin-sept 2026, 3 mois pour jury) | VPS-2 seul | 27 € × 3 = **81 €** |
| **Sous-total infra récurrent** | | **224 €** |

> `HYPOTHÈSE-A2` : le brief initial indiquait 370 € (62 € × 6 mois). On retient 224 € en profil décroissant car la prod ne tourne qu'en fin de projet. Si Jules souhaite le plafond 370 €, flagger.

### 3.3 One-shot (inclus dans capacité humaine)

| Poste | Effort | Coût séparé |
|-------|--------|-------------|
| Provisioning Ansible initial (VPS, firewall, Docker, certbot) | 1 HJ | inclus ligne DevOps §2.1 |
| Setup dashboards Grafana + Loki queries | 2 HJ | inclus ligne DevOps §2.1 |
| Bootstrap CI/CD GitHub Actions + GitLab | 1 HJ | inclus ligne DevOps §2.1 |
| Hardening sécurité (fail2ban, SSH keys, UFW) | 1 HJ | inclus ligne DevOps §2.1 |

Les 5 HJ de renfort DevOps (§2.1) couvrent l'intégralité du one-shot infra.

---

## 4. Outils & services

| Poste | Provider | Coût mensuel | Durée | Total HT | Justification |
|-------|----------|--------------|-------|----------|---------------|
| API exchanges (OHLCV, orderbook) | Binance public + CCXT | 0 € | 6 mois | **0 €** | Free tier public |
| Market data + metadata | CoinGecko Demo | 0 € | 6 mois | **0 €** | 30 req/min gratuit |
| Fear & Greed Index | Alternative.me | 0 € | 6 mois | **0 €** | Public |
| News RSS (Decrypt, CT, PhoenixNews) | RSS direct | 0 € | 6 mois | **0 €** | Parsing feedparser |
| Regulatory scraping | ESMA + SEC | 0 € | 6 mois | **0 €** | Public |
| LLM chat (optionnel) | OpenAI API | 20 € | 3 mois | **60 €** | `HYPOTHÈSE` — plafond crédits persona chat |
| LLM chat premium | Anthropic Claude API | 30 € | 3 mois | **90 €** | `HYPOTHÈSE` — qualité supérieure persona Noah |
| Email transactionnel | SendGrid Free tier | 0 € | 6 mois | **0 €** | 100 emails/jour |
| SMTP pro (optionnel) | Mailgun | 15 € | 3 mois | **45 €** | `HYPOTHÈSE` — si alertes F4 > 100/jour |
| Telegram Bot API | Telegram | 0 € | 6 mois | **0 €** | Gratuit illimité |
| **Sous-total outils** | | | | **195 €** | |

> `HYPOTHÈSE-A3` : le brief mentionnait 150 €. On retient **195 €** en ajoutant la ligne Mailgun, qui est dans F4 alertes. À arbitrer.

---

## 5. Équipement dev (coûts académiques)

Ces coûts sont pris en charge par Jules à titre personnel / pédagogique et ne sont pas refacturés au projet.

| Poste | Coût mensuel | Durée | Total HT |
|-------|--------------|-------|----------|
| Linear (task tracker) | 0 € | 6 mois | **0 €** (Free tier suffisant) |
| Obsidian | 0 € | 6 mois | **0 €** (gratuit usage perso) |
| Claude Code Max (abonnement dev) | 100 € | 3 mois actifs dev intensif | **300 €** |
| JetBrains PyCharm (licence perso) | 0 € | 6 mois | **0 €** (licence existante) |
| **Sous-total équipement** | | | **300 €** |

---

## 6. Récapitulatif financier

### 6.1 Total projet (école, hors TVA)

| Poste | Montant HT |
|-------|-----------:|
| Capacité humaine (§2) | 44 500 € |
| Infrastructure récurrente (§3) | 224 € |
| Outils & services (§4) | 195 € |
| Équipement dev (§5) | 300 € |
| **Sous-total avant buffer** | **45 219 €** |
| Buffer risque 20 % (§1.2 H7) | **9 044 €** |
| **TOTAL HT** | **54 263 €** |

### 6.2 Avec TVA 20 %

| Rubrique | Montant TTC |
|----------|-------------:|
| Total HT | 54 263 € |
| TVA 20 % | 10 853 € |
| **TOTAL TTC** | **65 116 €** |

> Note : le brief visait ~64 540 € TTC. L'écart de +576 € vient de l'ajustement +500 € sur renfort DevOps (§2.1) et +45 € Mailgun (§4). Tous flaggés `HYPOTHÈSE-A*`.

### 6.3 Décomposition CAPEX / OPEX

| Catégorie | Montant HT | % |
|-----------|-----------:|--:|
| CAPEX (dev initial, one-shot) | 44 800 € | 99,1 % |
| OPEX (infra + outils récurrents) | 419 € | 0,9 % |

Le projet est **dominé par les coûts humains**, ce qui est attendu pour un développement greenfield sans tiers payants.

---

## 7. Comparatif SaaS équivalent (ROI)

### 7.1 Alternatives marché

| Outil SaaS | Coût mensuel | Équivalent CryptoBot | Gap fonctionnel |
|------------|--------------|----------------------|-----------------|
| TradingView Premium | 60 €/mois | Dashboard + indicateurs | Pas de signaux custom multi-TF |
| CoinGlass Plus | 40 €/mois | On-chain + derivatives data | Pas de ML, pas d'alertes personnalisées |
| Santiment Pro | 135 €/mois | ML signals + social | Pas de backtesting interne, pas de personas |
| **Total stack SaaS équivalent** | **235 €/mois** | | |

### 7.2 Coût annuel comparé

| Option | An 1 | An 2 | An 3 | Cumul 3 ans |
|--------|-----:|-----:|-----:|-------------:|
| Stack SaaS (235 €/mois × 12) | 2 820 € | 2 820 € | 2 820 € | **8 460 €** |
| CryptoBot école (one-shot) | 45 219 € | 744 € | 744 € | **46 707 €** |
| CryptoBot école (dev amorti 3 ans) | 15 815 € | 15 815 € | 15 815 € | 46 707 € |

### 7.3 Break-even

- Pour un usage **individuel** : CryptoBot n'est **jamais rentable** vs SaaS (44 500 € de dev incompressible).
- Pour un **collectif de N utilisateurs** engagés 2+ ans : break-even si `N × 235 × 24 ≥ 45 219`, soit **N ≥ 8 utilisateurs**.
- Pour une **école / formation** : le projet a une valeur pédagogique qui ne se chiffre pas en €.

**Conclusion ROI** : CryptoBot se justifie économiquement seulement dans un scénario de mutualisation (8+ utilisateurs) ou de formation. Sinon, c'est un produit d'apprentissage.

---

## 8. Scénarios

| Scénario | Périmètre | Coût HT | Livrables RNCP |
|----------|-----------|--------:|----------------|
| **S0** MVP école Phase 1 (rules uniquement) | ETL + DB + rule engine + API + UI basique | **20 000 €** | Bloc 2 minimal |
| **S1** Phase 1 complète (école actuelle) | S0 + tests 80 % + CI/CD + prod deploy + docs | **45 219 €** | Bloc 2 + 3 + 4 ✅ |
| **S2** Phase 2 ML complète | S1 + LSTM + K-Means + RL (F6/F3/F8) | **+15 000 €** | Bloc 2 étendu |
| **S3** V1 commerciale | S2 + paper trading + alertes + 100 users + auth OAuth | **+25 000 €** | Post-école |
| **S4** Incubation (12 mois) | S3 + support + marketing + growth | **+80 000 €** | Post-école commercial |

Le scénario **S1** est celui effectivement livré pour la soutenance RNCP38919.

---

## 9. Hypothèses détaillées & risques financiers

### 9.1 Registre des hypothèses

| # | Hypothèse | Impact si fausse | À valider avec |
|---|-----------|------------------|----------------|
| H1 | TJM Mikael 400 € HT | +/- 2 400 € sur 30 HJ | Jules + Mikael |
| H2 | TJM Jules 500 € HT | +/- 6 000 € sur 60 HJ | Jules |
| H3 | 5 HJ suffisent DevOps | +10 HJ = +5 000 € | renfort externe |
| H4 | VPS OVH stable -> 0 € incident | incident crash = +200 € (backup + migration) | OVH SLA |
| H5 | LLM usage ≤ 20 €/mois | dépassement = +50 €/mois | métriques usage |
| H6 | Buffer 20 % suffit | R1 (RL fail) déclenche +10 HJ = +5 000 € | [[CryptoBot/avril/planning/risks]] |
| H7 | Let's Encrypt cert renewal | cold-start cassé = +1 HJ remédiation | monitoring |
| H8 | MinIO storage reste < 50 GB | upgrade 200 GB en S15 = +5 €/mois VPS | métriques MinIO |

### 9.2 Scénario worst-case

Si H1-H3 + H6 se réalisent défavorablement :

```
+2 400 € TJM Mikael actualisé (à 480 €/j)
+10 HJ DevOps = +5 000 €
+10 HJ LSTM refait = +5 000 €
------
= +12 400 € sur total HT
```

Total worst-case : **45 219 + 12 400 = 57 619 € HT** (+27 %). Le buffer 20 % (9 044 €) **ne couvre pas** ce scénario ; il faudrait remonter à 30 %. Recommandation : activer **Plan B-1** ([[CryptoBot/avril/planning/sprint-summary]]) si R1 ≥ 60 % proba.

### 9.3 Risques financiers majeurs

| Risque | Proba | Impact € | Mitigation |
|--------|------:|---------:|------------|
| RL ne converge pas (R1) | 60 % | +5 000 € rework | Plan B-1 (DQN only ou skip) |
| Paper trading bugs (R2) | 50 % | +3 000 € rework | Pair programming + 50 unit tests |
| Scraper fragile (R7) | 50 % | +1 500 € | Fallback selectors |
| VPS crash | 10 % | +500 € | Backup MinIO + snapshot OVH |
| LLM price hike | 20 % | +150 € | Switch local Ollama |

---

## 10. Plan de financement

### 10.1 Contexte école

Le projet CryptoBot est un **projet pédagogique** dans le cadre du RNCP38919 :

- **Pas de financement externe** sollicité pendant l'école.
- **Coût porté par** : temps étudiant (Jules + Mikael) + équipement perso + crédits LLM persos.
- **Infra VPS** : payée par Jules sur budget personnel, ~30 €/mois pendant 6 mois = ~180 €.

### 10.2 Post-école : scénarios de financement

Si le projet évolue en produit commercial (scénario **S3**), pistes de financement envisageables :

| Piste | Montant | Horizon | Probabilité |
|-------|--------:|---------|-------------|
| **Grant OVH Startup Program** | crédits VPS 12 mois (~400 €) | T+0 | Haute (sur dossier) |
| **Bpifrance Bourse French Tech** | 30 000 € | T+3 mois | Moyenne (dossier lourd) |
| **Incubateur local (Station F, The Bridge)** | 0 € loyer + mentorat | T+6 mois | Moyenne |
| **Love money / 3F (family, friends, fools)** | 10 000-50 000 € | T+6 mois | Variable |
| **Seed VC (Kima, OneRagtime)** | 300 000-800 000 € | T+12 mois | Basse sans MRR |

### 10.3 Modèle économique cible (post-école)

Si pivot commercial :

- **Freemium** : signaux de base gratuits, alertes Premium 9 €/mois/user.
- **Break-even opérationnel** : 50 users Premium × 9 € = 450 €/mois couvre infra + LLM (150 €/mois) et dégage marge.
- **Break-even total** (amortissement dev 45 k€) : 500 users × 12 mois = 54 000 € -> atteint en **~18 mois**.

---

## 11. Matrice de compétences RNCP Bloc 4

| Compétence visée | Section justificative | Livrable associé |
|------------------|-----------------------|------------------|
| Chiffrer un projet numérique | §1, §2, §3, §4 | Ce document |
| Identifier les coûts CAPEX / OPEX | §6.3 | Ce document |
| Réaliser un comparatif make-or-buy | §7 | Ce document |
| Proposer un plan de financement | §10 | Ce document |
| Identifier risques financiers | §9 | Ce document + [[CryptoBot/avril/planning/risks]] |
| Proposer scénarios dégradés | §8 | Ce document + [[CryptoBot/avril/planning/sprint-summary]] §Plans B |

---

## 12. Chiffres à valider avec Jules (checklist)

- [ ] **TJM Jules 500 €** (H2) — statut marché freelance 2026
- [ ] **TJM Mikael 400 €** (H1) — statut junior, temps partiel
- [ ] **TJM renfort DevOps 500 €** (H3) — 2 000 € ou 2 500 €
- [ ] **VPS OVH réel** — VPS-2 18 € confirmé ou VPS Starter 6 €
- [ ] **Go / No-Go VPS prod** — S15 activation ou pas
- [ ] **Go / No-Go Cloudflare Pro** — 20 €/mois justifié ou Free suffit
- [ ] **Budget LLM réel** — 20 € + 30 €/mois ou plafonds différents
- [ ] **Buffer 20 %** suffisant ou passer à 30 %
- [ ] **Domain name** — `.com` 12 €/an ou autre TLD
- [ ] **Équipement Claude Code Max** — 100 €/mois × 3 ou autre durée

---

## 13. Annexes

### 13.1 Sources internes du vault

- [[CryptoBot/avril/planning/sprint-plan]] — détail 6 sprints S11-S16
- [[CryptoBot/avril/planning/sprint-summary]] — synthèse 1 page
- [[_other/common/projects/SAP/planning/roadmap]] — roadmap macro Nov 2025 - Mai 2026
- [[CryptoBot/avril/planning/risks]] — registre risques (R1-R7)
- [[CryptoBot/avril/equipes/05-devops-infra]] — spec infra équipe DevOps
- [[CryptoBot/avril/architecture/dp01-docker-infrastructure]] — diagramme 12 services Docker
- [[CryptoBot/avril/history/decisions]] — ADRs techniques (no K8s, no MongoDB, Streamlit)
- [[CryptoBot/avril/specs/PRD-phase2]] — scope Phase 2

### 13.2 Glossaire financier

- **CAPEX** (Capital Expenditure) — investissement initial (dev + matériel).
- **OPEX** (Operational Expenditure) — coûts récurrents (infra + outils).
- **TJM** — Taux Journalier Moyen (coût d'un jour de prestation).
- **HJ** — Homme-Jour (1 HJ = 1 personne pendant 1 jour travaillé).
- **Buffer risque** — marge ajoutée pour couvrir imprévus (20 % standard projets agiles).
- **ROI** (Return on Investment) — retour sur investissement.
- **Break-even** — point d'équilibre où les revenus cumulés égalent les coûts cumulés.

### 13.3 Révisions

| Version | Date | Auteur | Changement |
|---------|------|--------|------------|
| 0.1 draft | 2026-04-14 | L5-Finance-Soutenance | Création initiale, chiffres hypothèses |

---

*Fin du livrable 5 — Analyse financière CryptoBot.*
