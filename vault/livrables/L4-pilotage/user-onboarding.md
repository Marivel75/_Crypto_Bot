---
type: rncp
bloc: 4
competence: C4.2.1
title: Plan d'accompagnement et d'onboarding utilisateurs finaux
project: cryptobot
tags: [cryptobot, rncp38919, bloc4, pilotage, onboarding, formation, ux]
created: 2026-04-14
source_of_truth: architecture/uc01-personas.md
related: [[architecture/uc01-personas]], [[architecture/sq01-auth-jwt-flow]], [[architecture/sq02-dashboard-request]], [[specs/ux-design-nouvelles-features]], [[rncp/bloc4-pilotage/faq-utilisateurs]]
---

# Plan d'accompagnement utilisateurs finaux — CryptoBot

## 1. Objectif formation

Rendre autonomes les trois personas cibles (trader, journaliste, investisseur debutant) en **moins de 15 minutes** d'onboarding actif, tout en ancrant le positionnement **strictement informationnel** de la plateforme : CryptoBot genere des signaux, calcule des indicateurs, agrege des news et suggere des parametres de trade ; **aucune execution automatique n'est ni effectuee ni propose**.

Criteres de reussite formation :
- L'utilisateur termine l'inscription + configuration watchlist sans support en ≤ 10 min.
- L'utilisateur sait lire un signal (direction, confidence, entry, SL, TP) sans aide.
- L'utilisateur a lu et valide le disclaimer "informationnel, non conseil d'investissement".

## 2. Personas cibles

Resume factuel depuis [[_other/common/projects/MPP/architecture/UC01-personas]] :

| Persona | Profil | Seuil confidence | Use cases primaires |
|---------|--------|------------------|---------------------|
| **Noah** | Trader actif, scalping 5 min a 4 h, experience ≥ 3 ans | 0.70 | Dashboard multi-TF, signaux BUY/SELL, heatmap, historique, Sharpe |
| **Sarah** | Journaliste crypto, redaction d'articles de veille | 0.60 | Flux news temps reel, sentiment par source, alertes reglementaires, heatmap |
| **Aleksandar** | Investisseur debutant, DCA long terme | 0.75 | Portfolio P&L simule, chatbot assistant, signaux simplifies, historique |

## 3. Runbook Noah (trader actif)

1. **Creer un compte** — page `/register` : email + password (8+ caracteres, 1 maj + 1 chiffre + 1 special), persona_type `trader`.
2. **Lier la watchlist** — page `/watchlist` : ajouter `BTCUSDT`, `ETHUSDT`, `SOLUSDT` (priority 13).
3. **Configurer le seuil** — page `/settings` : confidence min = `0.70`, timeframes primaires `1h/2h/4h`.
4. **Ouvrir le dashboard** — page `/dashboard` : candlesticks multi-TF + indicateurs RSI/Bollinger/Harmonic.
5. **Recevoir un signal WebSocket** — notification push en haut de page : direction, confidence, timeframes alignes, entry.
6. **Lire le signal** — carte de signal : `entry_price`, `stop_loss`, `take_profit[]`, `leverage_suggested` (verification automatique marge 2×).
7. **Exporter l'historique** — page `/performance` : CSV des signaux des 30 derniers jours pour backtesting perso.

Duree cible : 8 min.

## 4. Runbook Sarah (journaliste)

1. **Creer un compte** persona_type `journalist`, seuil 0.60.
2. **Activer le flux news** — page `/veille` : selection des sources (Decrypt, Cointelegraph, PhoenixNews, Alternative.me Fear & Greed).
3. **Filtrer par sentiment** — toggle "sentiment ≤ -0.3 OR ≥ 0.3", fraicheur ≤ 30 min.
4. **Voir le signal enrichi NLP** — pondere par sentiment (±5pp cap 0.95).
5. **Ouvrir le chatbot LLM** — page `/chat` : requete "resume marche BTC 24 h", reponse contextualisee avec citations d'articles.
6. **Exporter pour article** — bouton "export markdown" : genere un brief avec les 10 news top, heatmap de correlation et sentiment agrege.

Duree cible : 10 min.

## 5. Runbook Aleksandar (debutant)

1. **Creer un compte** persona_type `investor`, seuil 0.75.
2. **Activer le mode debutant** — toggle `/settings` > "mode simple" : affichage pedagogique.
3. **Voir un signal** — carte avec bulles explicatives : "RSI = indicateur de surachat/survente", "Bollinger = volatilite".
4. **Lire la suggestion de levier** — plafonnee a 5× max en mode debutant (vs 20× Noah), avec tooltip "risque eleve au-dela".
5. **Lire le disclaimer** — banner rouge persistant : "CryptoBot ne passe aucun ordre. Toute decision de trade vous incombe."
6. **Ouvrir le portfolio simule** — page `/portfolio` : saisir une position fictive, voir le P&L calcule sans flux reel de fonds.
7. **Questionner le chatbot** — requetes type "pourquoi RSI > 70 ?", reponse niveau debutant.

Duree cible : 12 min.

## 6. Parcours commun — Authentification

Le flux d'inscription/connexion suit le diagramme [[CryptoBot/avril/architecture/sq01-auth-jwt-flow]] :

- `POST /auth/register` — creation utilisateur, hash bcrypt, envoi email verification.
- `POST /auth/login` — validation credentials, emission JWT (HS256, expiration 24 h).
- `GET /auth/me` — verification token sur chaque page protegee.
- **MFA** — roadmap S14 (sprint 14), TOTP via applications authenticator. Prerequis : stockage secret chiffre, endpoint `/auth/mfa/enroll`, `/auth/mfa/verify`.

Reset password via `POST /auth/password-reset` (email token 30 min). Suppression de compte via `DELETE /auth/me` avec cascade RGPD (voir [[rncp/bloc3-deploiement/rgpd-compliance]]).

## 7. Format de formation

| Support | Volume | Duree | Cible |
|---------|--------|-------|-------|
| Video tutoriel par persona | 3 videos (Noah / Sarah / Aleksandar) | 3-5 min chacune | Autonomie rapide |
| Livret PDF | 10 pages, illustre | Lecture 15 min | Reference a garder |
| Session Q&A live | 1 session / mois | 60 min | Beta users, feedback direct |
| FAQ interactive | ~20 Q/R | a la demande | Self-service |

Videos hebergees sur l'instance Nginx (volume statique `/static/tutorials/`), livret PDF genere via `weasyprint` depuis markdown source.

## 8. Livrables formation

- **Scripts video** — 3 markdown dans `docs/formation/scripts/` (un par persona).
- **Slides** — deck Marp 20 pages, format `16:9`, exporte HTML + PDF.
- **FAQ structuree** — [[rncp/bloc4-pilotage/faq-utilisateurs]].
- **Livret PDF** — `docs/formation/livret-cryptobot.pdf`.
- **Checklist onboarding** — liste de 8 items integree dans l'UI (progression visuelle).

## 9. Mesure du succes

Indicateurs suivis via Prometheus + Grafana dashboard "User Onboarding" :

| KPI | Source | Cible phase ramp-up | Cible steady state |
|-----|--------|---------------------|--------------------|
| Taux d'activation 7 j (login + watchlist + signal lu) | evenements API | ≥ 50 % | ≥ 60 % |
| Duree mediane onboarding | frontend timing | ≤ 15 min | ≤ 10 min |
| NPS post-formation | sondage in-app J+30 | ≥ 30 | ≥ 40 |
| Support tickets / semaine | boite `support@` | ≤ 15 | ≤ 10 |
| Taux d'abandon au register | funnel frontend | ≤ 40 % | ≤ 25 % |

Revue mensuelle des KPI par le lead produit (Jules), ajustement des runbooks si abandon > 40 %.

## 10. Handoff support

- **Canal primaire** : `support@cryptobot.example` (adresse fictive projet ecole).
- **SLA** : reponse premiere ≤ 48 h ouvrees, resolution ≤ 5 jours pour bugs mineurs, 24 h pour incidents bloquants (P1).
- **Escalation** :
  - niveau 1 : equipe produit (Jules) — reponse fonctionnelle, onboarding, FAQ.
  - niveau 2 : equipe Backend (`src/api/`) — bugs API, auth, signaux.
  - niveau 3 : equipe DevOps — incidents infra (timescaledb, nginx, certificats).
- **Tracking** : Linear, label `support-ticket`, priorite automatique selon mot-cle ("down", "500", "ne marche pas" → P1).

## Diagrammes lies

[[_other/common/projects/MPP/architecture/UC01-personas]] | [[CryptoBot/avril/architecture/sq01-auth-jwt-flow]] | [[CryptoBot/avril/architecture/sq02-dashboard-request]] | [[CryptoBot/avril/specs/ux-design-nouvelles-features]]
