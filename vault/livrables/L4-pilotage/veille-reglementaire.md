---
type: rncp
bloc: 4
competence: C4.3.2
title: Veille reglementaire CryptoBot
project: cryptobot
tags: [cryptobot, rncp, bloc4, veille, reglementaire]
created: 2026-04-14
source_of_truth: rncp/bloc3-deploiement/rgpd-compliance.md
related: [[rncp/bloc3-deploiement/rgpd-compliance]], [[rncp/bloc4-pilotage/tech-radar]], [[specs/data-sources-roadmap]], [[history/themes]]
---

# Veille reglementaire — CryptoBot

La veille reglementaire est une competence pilotage (bloc 4 RNCP38919). Ce document cadre le perimetre applicable, les obligations retenues, les sources, la frequence de revue et le processus d'impact.

## 1. Cadre applicable

### 1.1. RGPD (UE 2016/679)
Directement applicable : CryptoBot traite des donnees personnelles (email, password hash, preferences utilisateur, persona_type, historique de consultation signaux). Couvert exhaustivement dans [[rncp/bloc3-deploiement/rgpd-compliance]] : registre des traitements, DPIA allegee, droits des personnes (acces, rectification, effacement, portabilite art. 20), notification breach < 72 h, cascade suppression RGPD en DB.

### 1.2. MiCA (Markets in Crypto-Assets Regulation, UE 2023/1114)
Reglement entre en application complete le **30 decembre 2024**. Il regule les emetteurs de crypto-actifs (Title II-IV) et les prestataires de services sur crypto-actifs (CASP, Title V).

**Perimetre CryptoBot** : **hors perimetre CASP**. CryptoBot n'effectue aucun des services regules :
- pas de garde/custody de crypto-actifs,
- pas d'execution d'ordres pour le compte de tiers,
- pas de reception/transmission d'ordres,
- pas de conseil personnalise en investissement,
- pas d'echange crypto-fiat ni crypto-crypto,
- pas d'emission ni placement.

**Obligation residuelle** : MiCA art. 88 encadre les communications publicitaires des CASP, et par extension les plateformes qui pourraient etre assimilees a du conseil. **CryptoBot doit strictement eviter les termes "conseil d'investissement", "recommandation personnalisee", "garantie de gain"**. Le disclaimer banner obligatoire : "Informationnel uniquement. CryptoBot n'emet aucun conseil en investissement."

### 1.3. DORA (Digital Operational Resilience Act, UE 2022/2554)
Applicable depuis janvier 2025 aux entites financieres regulees (banques, assureurs, CASP MiCA). **Non applicable** a CryptoBot (projet ecole, hors perimetre CASP).

Neanmoins, les bonnes pratiques DORA inspirent la resilience : healthchecks Docker, retention Loki 30j, backups automatises TimescaleDB, RTO/RPO documentes dans [[rncp/bloc3-deploiement/rgpd-compliance]].

### 1.4. AMF / ACPR (France)
**PSAN** (Prestataire de Services sur Actifs Numeriques, obsolete depuis MiCA) et **PSCA** (Prestataire de Services sur Crypto-Actifs, regime MiCA transpose) : non applicables car CryptoBot n'execute aucun service regule.

Veille utile : **publications AMF "alerte investisseurs"** et "actualites crypto-actifs" — source d'information pour la partie news et sentiment de la plateforme.

### 1.5. MiFID II
Directive sur les marches d'instruments financiers. **N/A** : les crypto-actifs n'y sont pas soumis (exclus explicitement), et CryptoBot n'intermedie aucun instrument financier classique.

### 1.6. KYC / AML (LCB-FT)
Lutte contre le blanchiment et le financement du terrorisme. **N/A** car pas de flux de fonds, pas de compte client credite/debitable, pas de paiement.

Si la roadmap ajoute un jour un systeme d'abonnement payant (Stripe/PayPal), le prestataire de paiement porte l'obligation KYC — pas CryptoBot.

### 1.7. LCEN (France, Loi Confiance Economie Numerique 2004)
Applicable a toute plateforme web hebergee en France. **Obligations** : mentions legales identifiant l'editeur, politique de confidentialite, CGU, hebergeur (OVH). Publiees sur `/legal/mentions`, `/legal/privacy`, `/legal/cgu`.

## 2. Obligations retenues

Liste operationnelle des livrables conformite :

| Obligation | Origine | Etat | Livrable |
|------------|---------|------|----------|
| Mentions legales FR | LCEN | a publier | `/legal/mentions` |
| Politique de confidentialite FR | RGPD + LCEN | a publier | `/legal/privacy` |
| CGU FR | LCEN | a publier | `/legal/cgu` |
| Banner cookies opt-in | RGPD + CNIL | a publier | composant frontend + Cloudflare analytics |
| Registre des traitements | RGPD art. 30 | partiel | `docs/rgpd/registre.md` |
| Disclaimer "informationnel" | MiCA art. 88 | partiel | banner permanent + pied de page signal |
| Droit d'acces/portabilite | RGPD art. 15/20 | implemente | `/settings/export` |
| Droit d'effacement | RGPD art. 17 | implemente | cascade DB |
| Notification breach 72 h | RGPD art. 33 | procedure | runbook DevOps |

## 3. Sources de veille reglementaire

Suivi via flux RSS et revue mensuelle :

| Source | URL | Frequence |
|--------|-----|-----------|
| ESMA (European Securities and Markets Authority) | esma.europa.eu — feeds "Press releases" et "Publications" | mensuel |
| AMF France | amf-france.org — alertes investisseurs et publications crypto | mensuel |
| ACPR | acpr.banque-france.fr — communiques | trimestriel |
| CNIL | cnil.fr/fr/ajouts-recents + RSS "Actualites" | mensuel |
| Journal Officiel UE | eur-lex.europa.eu — feed L (legislation) | mensuel |
| Journal Officiel FR (Legifrance) | legifrance.gouv.fr — codes monetaire/numerique | trimestriel |
| SEC (US, en cas d'expansion) | sec.gov — RSS press releases | trimestriel |

Les feeds sont configures dans le scheduler ETL (voir [[CryptoBot/avril/specs/data-sources-roadmap]]) pour integrer les alertes reglementaires directement dans le flux news utilisateur (utile pour Sarah, persona journaliste).

## 4. Frequence et synthese

- **Revue mensuelle** : le lead DevOps parcourt les flux RSS, consigne les entrees pertinentes dans un journal hebdomadaire (voir section 6).
- **Synthese trimestrielle** : production d'une note dans [[CryptoBot/avril/history/themes]] avec les evolutions, actions prises, items reportes.
- **Revue annuelle** : audit conformite complet aligne sur le calendrier RGPD (registre, DPIA si pertinent).

## 5. Processus d'impact reglementaire

Cinq etapes standardisees en cas d'alerte :

1. **Alerte** — ajout automatique d'un ticket Linear label `veille-reglementaire` (collect ETL RSS ou saisie manuelle).
2. **Analyse impact 48 h** — le lead DevOps + Jules (PO) evaluent : applicabilite, perimetre touche (auth, donnees, UI, infra), urgence.
3. **Decision** — 3 verdicts possibles :
   - **action** : redaction d'un CR de changement referencant [[rncp/bloc4-pilotage/change-management]] et creation des stories associees.
   - **monitor** : pas d'action immediate, ajout au backlog surveillance trimestrielle.
   - **ignore** : hors perimetre documente, cloture du ticket.
4. **Execution** (si action) — sprint planning, developpement, tests, deploiement.
5. **Cloture** — mise a jour du registre + synthese [[CryptoBot/avril/history/themes]].

## 6. Journal de veille

Template hebdomadaire stocke dans `docs/rgpd/journal/YYYY-WW.md` :

```markdown
# Veille reglementaire — semaine YYYY-WW

## Sources consultees
- ESMA : N publications
- AMF : N alertes
- CNIL : N actualites
- JO UE : N textes

## Elements remarques
- [source] [date] [titre] — [resume] — [verdict: action/monitor/ignore]

## Tickets crees
- LIN-XXX — [titre]

## Synthese
[2-3 lignes]
```

Le backlog Linear utilise le label `veille-reglementaire` et la priorite est alignee sur l'urgence (P1 si breach ou non-conformite immediate, P3 si surveillance).

## 7. Responsabilite

- **Lead veille** : lead DevOps (execution hebdo, synthese trimestrielle).
- **PO / decideur** : Jules — arbitrage action/monitor/ignore, signature CR.
- **Contributeurs** : chaque team lead fournit un avis impact (Data Eng, ML, Backend, Frontend) sous 48 h pour toute alerte de niveau action.
- **Externe** : en cas de doute juridique majeur (ex. requalification en conseil financier), consultation d'un cabinet specialise avant action.

## Documents lies

[[rncp/bloc3-deploiement/rgpd-compliance]] | [[rncp/bloc4-pilotage/tech-radar]] | [[CryptoBot/avril/specs/data-sources-roadmap]] | [[CryptoBot/avril/history/themes]]
