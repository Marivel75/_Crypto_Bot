# CryptoBot — Diagrams V2

Ce dossier contient le catalogue UML V2 de CryptoBot, aligné sur l'état réel de la branche `main`.

## Contenu

| Fichier | Description |
|---------|-------------|
| `_all-diagrams.md` | Catalogue principal — 22 diagrammes PlantUML intégrés |
| `parts/` | Fragments sources `.puml` (un fichier par diagramme) |
| `_v1/` | Catalogue V1 archivé (features fantômes — ne pas modifier) |

## Table de correspondance V1 → V2 (22 diagrammes)

| ID | Slug V2 | Titre V2 | Pivot V2 ? | Titre V1 (si différent) |
|----|---------|----------|------------|------------------------|
| AC01 | etl-pipeline | Pipeline ETL V2 | | Pipeline ETL |
| AC02 | signal-lifecycle | Cycle de vie Signal V2 | | Cycle de vie Signal |
| C01 | macro-architecture | Architecture Macro V2 | | Architecture Macro |
| C02 | etl-components | Composants ETL V2 | | Composants ETL |
| C03 | ml-components | Composants ML V2 | | Composants ML |
| C04 | api-components | Composants API FastAPI V2 | | Composants API |
| C05 | frontend-components | Composants Frontend V2 | | Composants Frontend |
| C06 | ml-backtesting-pipeline | Pipeline ML Backtesting V2 | | Pipeline ML Backtesting |
| **C07** | **backlog-v3** | **Backlog V3** | **OUI** | Phase 2 Roadmap |
| CL01 | pydantic-models | Modèles Pydantic V2 | | Modèles Pydantic |
| CL02 | orm-models | Modèles ORM SQLAlchemy V2 | | Modèles ORM |
| CL03 | fastapi-schemas | Schemas FastAPI V2 | | Schemas FastAPI |
| CL04 | ml-evaluators | Evaluateurs ML V2 | | Evaluateurs ML |
| CL05 | exceptions | Hiérarchie Exceptions V2 | | Exceptions |
| DP01 | docker-compose | Déploiement Docker Compose V2 | | Déploiement Docker |
| ER01 | database-schema | Schema BDD SQLite V2 | | Schema BDD |
| **SQ01** | **health-and-alerts-flow** | **Healthcheck + Alerts Flow V2** | **OUI** | JWT Auth Flow |
| SQ02 | dashboard-data-flow | Dashboard Data Flow V2 | | Dashboard Data Flow |
| SQ03 | signal-generation-flow | Signal Generation Flow V2 | | Signal Generation Flow |
| **SQ04** | **paper-trading-order-flow** | **Paper Trading Order Flow V2** | **OUI** | Chatbot LLM Flow |
| ST01 | signal-state | Etat Signal V2 | | Signal State |
| UC01 | personas-usecases | Personas & Cas d'usage V2 | | Personas & Use Cases |

Les 3 pivots V2 (en gras) ont subi un changement sémantique majeur par rapport à V1 : SQ01, SQ04, C07.

## Rendu

### Plugin Obsidian PlantUML

Installer le plugin [PlantUML](https://github.com/joethei/obsidian-plantuml) dans Obsidian.
Ouvrir `_all-diagrams.md` — les blocs ` ```plantuml ` sont rendus automatiquement.

### CLI PlantUML

```bash
# Vérification syntaxe (tous les fragments)
plantuml -checkonly docs/diagrams/parts/*.puml

# Génération PNG
plantuml -tpng docs/diagrams/parts/AC01-etl-pipeline.puml

# Génération SVG (tous)
plantuml -tsvg docs/diagrams/parts/*.puml
```

## Note sur `parts/`

Le dossier `parts/` contient les 22 fragments sources `.puml`. Chaque fichier :

- Commence par `@startuml {ID}-{slug}` (ligne 1)
- Intègre le bloc skin partagé `_common` (lignes 2–143/144)
- Se termine par `@enduml`

Ne pas modifier les fragments directement — ils constituent la source de vérité pour le catalogue.
