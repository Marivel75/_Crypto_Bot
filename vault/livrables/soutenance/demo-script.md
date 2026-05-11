---
type: rncp-livrable
bloc: soutenance
titre: Script démo live CryptoBot
diplome: RNCP38919
projet: cryptobot
duree_cible: 8 minutes
date_soutenance: 2026-06-11
statut: draft-v1
tags: [cryptobot, rncp, soutenance, demo, script]
created: 2026-04-14
owner: L5-Finance-Soutenance
---

# Script démo live — CryptoBot RNCP38919

**Durée cible** : 8 minutes chrono.
**Format** : démo end-to-end, du dashboard jusqu'à la base, avec observabilité et lineage.
**Règle** : chaque étape a une commande / clic précis, une valeur attendue, et un plan B screenshot.

---

## Checklist pré-démo (à faire J-1 et H-30)

- [ ] **J-1** : `docker compose pull && docker compose up -d` sur VPS staging
- [ ] **J-1** : ETL worker a inséré ≥ 1000 OHLCV BTC/USDT sur dernières 24h
- [ ] **J-1** : Rule engine a émis ≥ 1 signal BUY ou SELL BTCUSDT 4h
- [ ] **J-1** : MLflow contient ≥ 1 run `RuleEngine` avec `hit_rate`
- [ ] **J-1** : Grafana dashboards "API latency p95" et "ETL runs" accessibles
- [ ] **H-30** : `docker compose ps` -> tous les services `healthy` (pas `starting`)
- [ ] **H-30** : user persona `noah@demo.com` / `Alex123!` créé en DB
- [ ] **H-30** : navigateur Firefox avec 6 onglets préchargés :
  1. `https://cryptobot.local/login` (Streamlit)
  2. `https://cryptobot.local/api/docs` (Swagger)
  3. `https://mlflow.cryptobot.local` (MLflow UI)
  4. `https://grafana.cryptobot.local` (Grafana)
  5. `https://cryptobot.local/crypto` (Dashboard Plotly)
  6. Terminal avec `docker compose ps` prêt
- [ ] **H-30** : screenshots fallback dans `infra/screenshots/demo-soutenance/` (8 images numérotées)
- [ ] **H-30** : chronomètre phone/montre visible
- [ ] **H-30** : charger le câble HDMI écran jury

---

## Script minuté

### Étape 0 — Intro (30 s)

**Dire** :
> « Je vais démontrer une requête de signal end-to-end. On partira du dashboard, on remontera jusqu'à la base de données, et on finira par l'observabilité. 8 minutes chrono. »

**Action** : afficher slide 22 "DÉMO LIVE" + lancer chronomètre.

---

### Étape 1 — Démarrage infra (1 min)

**Objectif** : montrer que la plateforme tourne vraiment, 12 services healthy.

**Commande** (terminal onglet 6) :
```bash
docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
```

**Valeur attendue** :
```
NAME                STATUS              PORTS
cb-timescaledb      Up 2 days (healthy) 5432/tcp
cb-minio            Up 2 days (healthy) 9000-9001/tcp
cb-mlflow           Up 2 days (healthy) 5000/tcp
cb-api              Up 2 days (healthy) 8000/tcp
cb-frontend         Up 2 days (healthy) 8501/tcp
cb-etl-worker       Up 2 days (healthy)
cb-nginx            Up 2 days (healthy) 80/tcp, 443/tcp
cb-prometheus       Up 2 days (healthy) 9090/tcp
cb-grafana          Up 2 days (healthy) 3000/tcp
cb-loki             Up 2 days (healthy) 3100/tcp
cb-redis            Up 2 days (healthy) 6379/tcp
cb-certbot          Up 2 days
```

**Dire** :
> « 12 services, tous healthy depuis 2 jours. C'est le déploiement staging réel sur VPS OVH. »

**Plan B** : screenshot `infra/screenshots/demo-soutenance/01-docker-ps.png`.

---

### Étape 2 — Authentification persona (1 min)

**Objectif** : démontrer le flow JWT et la différenciation persona Noah.

**Action** :
1. Onglet 1 → `https://cryptobot.local/login`
2. Saisir `noah@demo.com` / `Alex123!`
3. Cliquer "Se connecter"
4. Ouvrir DevTools (F12) → onglet Network → cliquer la requête `POST /api/auth/login`
5. Montrer la réponse : `{"access_token": "eyJ...", "token_type": "bearer", "expires_in": 900, "persona": "noah"}`
6. Copier le token (Ctrl+C) pour étape 6

**Dire** :
> « JWT 15 minutes, refresh 7 jours. Le payload contient `persona: noah` qui conditionne l'UI et les features exposées. »

**Valeur attendue** : redirection vers `/crypto` avec bandeau "Bienvenue Noah — mode simplifié".

**Plan B** : screenshot `02-login-jwt.png`.

---

### Étape 3 — Dashboard crypto (1 min)

**Objectif** : montrer la veille en temps réel avec indicateurs Plotly.

**Action** :
1. Onglet 5 → `https://cryptobot.local/crypto`
2. Dans la sidebar : sélectionner **BTCUSDT**, timeframe **4h**, période **30j**
3. Cliquer "Afficher"
4. Pointer : chandelier OHLCV, overlay Bollinger Bands, sub-chart RSI 14
5. Scroller jusqu'au panneau "News récentes" — montrer 3 articles avec source + timestamp
6. Scroller jusqu'au panneau "Régulation" — montrer 1 document ESMA récent

**Dire** :
> « BTC/USDT 4h. Bollinger Bands en squeeze sur les 5 dernières bougies, RSI à 58. Les news et la régulation sont scrapées en continu par le worker ETL. »

**Valeur attendue** : chart Plotly interactif, hover affiche OHLC + volume.

**Plan B** : screenshot `03-dashboard-btc.png`.

---

### Étape 4 — Consultation signal (1 min 30)

**Objectif** : afficher un signal concret avec tous ses champs.

**Action** :
1. Menu latéral → "Signaux"
2. Liste filtrée : cliquer colonne "timestamp" pour tri desc
3. Ouvrir le dernier signal BUY BTCUSDT 4h
4. Pointer les champs affichés :
   - **Direction** : BUY
   - **Confidence** : 0,73
   - **Entry price** : 67 450 USD
   - **Stop loss** : 66 100 USD (-2,0 %)
   - **Take profit** : [68 800, 70 200, 72 500]
   - **Leverage suggested** : 2× (règle de marge 2x vérifiée)
   - **Indicators used** : ["RSI 4h", "Bollinger 4h", "Trend line weekly"]
   - **Timestamp** : 2026-06-10T14:00:00Z

**Dire** :
> « Signal BUY à confidence 0,73 — au-dessus du seuil 0,6. Entry, stop, 3 TP, effet de levier 2× validé. Pas d'exécution automatique : l'utilisateur décide. »

**Plan B** : screenshot `04-signal-detail.png`.

---

### Étape 5 — API brute (1 min)

**Objectif** : montrer que la même donnée est accessible via API REST, avec auth JWT.

**Action** :
1. Onglet 2 → `https://cryptobot.local/api/docs` (Swagger UI)
2. Cliquer en haut "Authorize" → coller le JWT (copié étape 2) → "Authorize"
3. Scroller jusqu'à `GET /signals`
4. Cliquer "Try it out"
5. Paramètres : `symbol=BTCUSDT`, `tf=4h`, `limit=5`
6. "Execute"
7. Montrer la réponse JSON (200 OK) avec 5 signaux récents

**Dire** :
> « L'API FastAPI expose la même donnée. OpenAPI 3.1 auto-documenté. Les persona Sam traders utilisent l'API raw, les persona Noah l'UI simplifiée. »

**Valeur attendue** : réponse JSON 200, `len(data) == 5`, latence affichée < 100 ms.

**Plan B** : screenshot `05-swagger-signals.png`.

---

### Étape 6 — Data lineage MLflow (1 min)

**Objectif** : démontrer la traçabilité ML avec MLflow.

**Action** :
1. Onglet 3 → `https://mlflow.cryptobot.local`
2. Experiment "CryptoBot / RuleEngine"
3. Cliquer le run le plus récent (runid en header, ex. `a3f2e91b`)
4. Onglet "Metrics" → montrer `hit_rate: 0.68`, `precision: 0.71`, `recall: 0.64`, `sharpe: 1.12`
5. Onglet "Artifacts" → ouvrir `feature_importance.png`
6. Pointer les 3 features top : RSI_4h (0,24), BB_squeeze_4h (0,19), Trend_weekly (0,15)

**Dire** :
> « Chaque génération de signal est un run MLflow. On voit le hit rate 68 %, Sharpe 1,12, et les features les plus contributives. C'est notre lineage data complet. »

**Plan B** : screenshot `06-mlflow-metrics.png`.

---

### Étape 7 — Observabilité Grafana (1 min)

**Objectif** : prouver la supervision temps réel.

**Action** :
1. Onglet 4 → `https://grafana.cryptobot.local`
2. Dashboard "CryptoBot — API latency"
3. Pointer : panel "p95 latency `/signals`" → ~80 ms
4. Switch dashboard "CryptoBot — ETL runs"
5. Pointer : panel "ETL success rate 24h" → 99,2 %
6. Pointer : panel "Rows ingested / min" → ~450
7. Ouvrir Explore → query Loki : `{service="api"} |= "ERROR"` → montrer "0 results last 1h"

**Dire** :
> « Grafana + Prometheus + Loki. p95 API à 80 ms, ETL success 99,2 %, zéro erreur API depuis 1 heure. Alerting configuré mais pas déclenché. »

**Plan B** : screenshot `07-grafana-dashboards.png`.

---

### Étape 8 — Clôture (30 s)

**Objectif** : boucler la démo sur la documentation.

**Action** :
1. Alt-Tab vers slide 22 (ou slide suivante 23 "Résultats obtenus")
2. Dire :
> « Tout ce que vous venez de voir est documenté : 94 pages Obsidian dans le vault, 22 diagrammes PlantUML qui sont notre source de vérité, 7 livrables RNCP dans le dossier `rncp/`. Fin de démo, je reprends la présentation. »

3. Arrêter chronomètre. Cible : entre 7:30 et 8:30.

**Plan B final** : si démo totalement crashée, basculer sur slides 23-24 et commenter les screenshots pré-enregistrés en mode "visite guidée".

---

## Tableau récap timing

| Étape | Durée cible | Cumul |
|-------|------------:|------:|
| 0 Intro | 0:30 | 0:30 |
| 1 Docker ps | 1:00 | 1:30 |
| 2 Auth JWT | 1:00 | 2:30 |
| 3 Dashboard | 1:00 | 3:30 |
| 4 Signal | 1:30 | 5:00 |
| 5 API Swagger | 1:00 | 6:00 |
| 6 MLflow | 1:00 | 7:00 |
| 7 Grafana | 1:00 | 8:00 |
| 8 Clôture | 0:30 | 8:30 |

---

## Plans B généraux

### B1 — Panne réseau VPS

Symptôme : `docker compose ps` timeout, urls inaccessibles.

Action : basculer sur Docker Compose local :
```bash
cd ~/Documents/3-git/CryptoBot/dev
docker compose -f docker-compose.demo.yml up -d
```

URLs deviennent `http://localhost:*`. Fonctionnellement équivalent, pas de TLS.

### B2 — Panne écran / projecteur

Action : continuer au tableau blanc en commentant les screenshots pré-imprimés (8 pages A4 dans pochette plastique).

### B3 — Bug pendant la démo

Règle : **ne jamais déboguer en live**. Dire « Je note le bug, je poursuis sur le plan B screenshot ». Passer à l'étape suivante.

### B4 — Dépassement temps

Seuil : à **6:00**, si pas à l'étape 5, couper les étapes 6 et 7 (MLflow + Grafana) et passer directement à la clôture. Mieux vaut finir propre qu'en retard.

### B5 — Question jury en cours de démo

Répondre brièvement (< 15 s) ou dire « Très bonne question, je la traite en Q&A ». Ne pas interrompre la démo.

---

## Ressources

- Screenshots fallback : `infra/screenshots/demo-soutenance/0[1-8]-*.png`
- `docker-compose.demo.yml` : variant local pour plan B1
- Credentials démo : `infra/demo-accounts.md` (gitignored, Vault)
- Chronomètre : phone + Apple Watch (redondance)

---

## Checklist post-démo

- [ ] Rebasculer slide suivante (23 "Résultats")
- [ ] Boire une gorgée d'eau
- [ ] Reprendre rythme présentation

---

*Fin du script démo.*
