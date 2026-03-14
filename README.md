# Crypto Bot

Plateforme de veille, analytics et aide au trading crypto.

## Equipes

| Equipe | Dossier code | Documentation | Perimetre |
|--------|-------------|---------------|-----------|
| **Data Engineering** | `src/etl/` | `docs/01-data-engineering.md` | Pipeline ETL, TimescaleDB, MinIO, collecte de donnees |
| **ML / Data Science** | `src/ml/` | `docs/02-ml-data-science.md` | Regles multi-TF, modeles ML, backtesting, MLflow |
| **Backend / API** | `src/api/` | `docs/03-backend-api.md` | FastAPI, endpoints REST, auth, signaux |
| **Frontend / UI** | `src/frontend/` | `docs/04-frontend-ui.md` | Streamlit, dashboards Plotly, chatbot |
| **DevOps / Infra** | racine (`docker-compose.yml`, `nginx/`) | `docs/05-devops-infra.md` | Docker, CI/CD, Nginx, monitoring, backups |

## Stack technique

```
Python 3.11+ | FastAPI | Streamlit | Plotly
PostgreSQL + TimescaleDB | MinIO (S3) | MLflow + DVC
Docker Compose | Nginx | GitHub Actions
```

## Architecture

```
[Binance/CoinGecko/CCXT] → [ETL Python] → [TimescaleDB] → [FastAPI] → [Streamlit]
                                          → [MinIO]       → [MLflow]
```

## Demarrage rapide

```bash
cp .env.example .env        # Configurer les variables
docker-compose up -d         # Lancer tous les services
```

## Regles communes (TOUTES les equipes)

1. **Pas de secrets dans le code** — `.env` uniquement, jamais committe
2. **Code partage** dans `src/shared/` — models pydantic, config, constantes
3. **Ne touchez PAS au code des autres equipes** — communiquez via les interfaces definies
4. **Tests obligatoires** — pytest, couverture > 80% sur votre perimetre
5. **Commits** : `type(scope): description` — ex: `feat(etl): add binance OHLCV collector`
6. **Branches** : `equipe/feature-name` — ex: `data-eng/binance-collector`
7. **PR obligatoire** pour merge sur `main`
8. **Python** : ruff pour le lint, mypy pour les types, pydantic pour la validation

## Documentation

- `docs/00-overview.md` — Vision, personas, fonctionnalites (lu par TOUTES les equipes)
- `docs/01-data-engineering.md` — Equipe Data Engineering
- `docs/02-ml-data-science.md` — Equipe ML / Data Science
- `docs/03-backend-api.md` — Equipe Backend / API
- `docs/04-frontend-ui.md` — Equipe Frontend / UI
- `docs/05-devops-infra.md` — Equipe DevOps / Infra
- `docs/06-roadmap.md` — Planning, sprints, KPIs (lu par TOUTES les equipes)
- `docs/glossaire.md` — Glossaire commun
