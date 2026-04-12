# CryptoBot — PlantUML Diagrams

22 diagrammes UML couvrant l'architecture Phase 1 (actuelle) et Phase 2 (planifiee).

## Build

```bash
make diagrams        # Generer tous les SVG dans docs/diagrams/svg/
make diagrams-png    # Generer tous les PNG dans docs/diagrams/png/
make diagrams-clean  # Supprimer les fichiers generes
make diagrams-list   # Lister les sources .puml
```

Prerequis : `plantweb >= 1.3.0` (`uv tool install plantweb`)

## Index

### Groupe A — Architecture (Composants)

| # | Fichier | Description |
|---|---------|-------------|
| 1 | `C01-architecture-macro.puml` | Vue systeme globale |
| 2 | `C02-etl-components.puml` | Sous-systeme ETL |
| 3 | `C03-ml-components.puml` | Sous-systeme ML |
| 4 | `C04-api-components.puml` | FastAPI |
| 5 | `C05-frontend-components.puml` | Streamlit |

### Groupe B — Classes

| # | Fichier | Description |
|---|---------|-------------|
| 6 | `CL01-pydantic-models.puml` | Modeles domaine Pydantic |
| 7 | `CL02-orm-models.puml` | Classes SQLAlchemy ORM |
| 8 | `CL03-api-schemas.puml` | Schemas API request/response |
| 9 | `CL04-ml-rules-models.puml` | Hierarchie rules engine |
| 10 | `CL05-exceptions.puml` | Arbre d'exceptions |

### Groupe C — Sequences

| # | Fichier | Description |
|---|---------|-------------|
| 11 | `SQ01-auth-jwt-flow.puml` | Authentification JWT |
| 12 | `SQ02-dashboard-request.puml` | Chargement page Dashboard |
| 13 | `SQ03-signal-generation.puml` | Pipeline generation de signaux |
| 14 | `SQ04-chat-llm-flow.puml` | Flux chatbot LLM |

### Groupe D — Activite

| # | Fichier | Description |
|---|---------|-------------|
| 15 | `AC01-etl-pipeline.puml` | Pipeline ETL complet |
| 16 | `AC02-signal-lifecycle.puml` | Cycle de vie d'un signal |

### Groupe E — Deploiement

| # | Fichier | Description |
|---|---------|-------------|
| 17 | `DP01-docker-infrastructure.puml` | Infrastructure Docker Compose |

### Groupe F — Base de donnees

| # | Fichier | Description |
|---|---------|-------------|
| 18 | `ER01-database-schema.puml` | Schema ER complet TimescaleDB |

### Groupe G — Phase 2

| # | Fichier | Description |
|---|---------|-------------|
| 19 | `C06-phase2-ml-pipeline.puml` | Architecture ML Phase 2 |
| 20 | `C07-phase2-features.puml` | Roadmap features F1-F8 |

### Groupe H — Cas d'utilisation + Etat

| # | Fichier | Description |
|---|---------|-------------|
| 21 | `UC01-personas.puml` | Use cases par persona |
| 22 | `ST01-signal-states.puml` | Machine a etats d'un signal |

## Structure

```
docs/diagrams/
  _common.puml          # Skinparams partages
  README.md             # Ce fichier
  C01-*.puml ... ST01-*.puml   # 22 sources
  svg/                  # SVG generes (gitignored)
  png/                  # PNG generes (gitignored)
```
