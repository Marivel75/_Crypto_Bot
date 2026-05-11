---
type: rncp-index
source: rncp-agent-supervisor
tags: [cryptobot, rncp, index]
created: 2026-04-14
updated: 2026-04-14
---

# RNCP38919 — CryptoBot — Index

Deux vues parallèles du même contenu — choisis selon ton besoin :

## Vue 1 — Livrables officiels du référentiel

Les 5 livrables + soutenance exigés par le référentiel RNCP38919.

```
livrables/
├── L2-infrastructure/   # Livrable 2 (blocs B2+B3)
├── L3-deploiement/      # Livrable 3 (bloc B3)
├── L4-pilotage/         # Livrable 4 (bloc B4)
├── L5-finance/          # Livrable 5 (bloc B4)
└── soutenance/          # Soutenance orale
```

### L2 — Infrastructure de données (Livrable 2)
- `[[etl-execution-report]]` (258 L) — procédures ETL + rapport exécution
- `[[etl-data-quality]]` (203 L) — 6 dimensions DAMA + métriques qualité
- `[[db-normalization-3nf]]` (307 L) — MCD/MPD/3NF + dénormalisations
- `[[db-ddl-init]]` (285 L SQL) — script DDL exécutable
- `[[db-backup-recovery]]` (369 L) — pg_dump + MinIO + RPO/RTO
- `[[ml-justification-phase1]]` (200 L) — rules RSI/Bollinger/Harmonic/Trend
- `[[ml-phase2-scope-revise]]` (141 L) — scope XGBoost+LightGBM vs roadmap

### L3 — Déploiement solution (Livrable 3)
- `[[api-contract-v1]]` (491 L) + `[[api-openapi]]` (JSON stub)
- `[[cicd-evidence]]` (249 L) + workflows `deploy.yml` + `.gitlab-ci.yml` + `infra/ansible/README.md`
- `[[container-images]]` (335 L) — 4 Dockerfiles + Trivy + sécurité container
- `[[rgpd-compliance]]` (218 L) — RGPD + TLS 1.3 + endpoints droits
- `[[secrets-rotation]]` (263 L) — 14 secrets inventoriés, rotation JWT dual-key
- `[[test-coverage-report]]` (331 L) — 1200 tests, ~81.5% couverture
- `[[prod-run-evidence]]` (266 L) — 7 screenshots, healthchecks, Grafana

### L4 — Pilotage projet (Livrable 4)
- `[[retrospectives]]` (249 L) — S11/S12 réels + squelettes S13-S16
- `[[change-management]]` (254 L) — CR template + matrice impact + 3 niveaux
- `[[kpi-performance]]` (340 L) — 5 catégories KPI + DORA adaptés
- `[[user-onboarding]]` (126 L) — runbooks par persona
- `[[faq-utilisateurs]]` (108 L) — ~20 Q/R utilisateurs
- `[[tech-radar]]` (125 L) — 46 technos Adopt/Trial/Assess/Hold
- `[[veille-reglementaire]]` (142 L) — RGPD + MiCA + DORA + MiFID II

### L5 — Analyse financière (Livrable 5)
- `[[cost-analysis]]` (386 L) — ~65 116 € TTC, 14 hypothèses à valider

### Soutenance
- `[[slides-outline]]` (422 L) — 30 slides
- `[[demo-script]]` (298 L) — démo live 8 min

---

## Vue 2 — Compétences du référentiel

Les 25 compétences officielles regroupées par bloc, avec **mapping vers les livrables qui les prouvent**.

```
competences/
├── _index.md         # Matrice globale compétences × livrables
├── B2-concevoir.md   # 6 compétences
├── B3-deployer.md    # 13 compétences
└── B4-piloter.md     # 6 compétences
```

- `[[competences/_index]]` — **entrée jury** (matrice synoptique)
- `[[B2-concevoir]]` — identifier besoins + veille + périmètre + recommandations + architecture
- `[[B3-deployer]]` — collecter + stocker + ETL + analyser + IA + API + conteneurs + déploiement + CI/CD
- `[[B4-piloter]]` — structure + encadrement + budget + communication + évaluation + formation

---

## Statut global

| Bloc | Compétences | Livrables produits | Statut |
|------|-------------|--------------------|--------|
| B2 | 6 | 7 (L2 partiel) | 🟢 |
| B3 | 13 | 8 (L3) + artefacts repo | 🟢 LSTM/RL roadmap |
| B4 | 6 | 7 (L4) + 1 (L5) + 2 (soutenance) | 🟢 |

Total : **24 livrables**, ~5 800 lignes, **25 compétences couvertes**.

## Points d'arbitrage avec Jules

1. **`etl-execution-report`** : flag `--once --report-json` à implémenter, sinon `[À MESURER]` restent vides
2. **`api-openapi.json`** : stub, à régénérer sur machine avec deps : `uv run python -c "from src.api.main import app; import json; print(json.dumps(app.openapi(), indent=2))" > livrables/L3-deploiement/api-openapi.json`
3. **`prod-run-evidence`** : prod SSH désactivé → captures existantes `/home/jules/Documents/3-git/CryptoBot/dev/screenshots/` (7 PNG)
4. **`cost-analysis`** : 14 hypothèses à valider (TJM, VPS modèle, buffer 20%, LLM, Cloudflare Pro)
5. **Contradictions restantes** : 10 lignes ouvertes dans `[[contradictions]]` (19-22 résolues par ADR-010)

## Export bundle jury

```bash
cd /home/jules/Documents/3-git/_vault/common/projects/cryptobot
zip -r rncp38919-livrables.zip rncp/
```
