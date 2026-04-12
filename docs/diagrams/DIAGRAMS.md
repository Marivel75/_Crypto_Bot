# CryptoBot — Diagrammes UML

> 22 diagrammes PlantUML couvrant l'architecture Phase 1 (actuelle) et Phase 2 (planifiee).
> Build : `make diagrams` (plantuml-local-client + Java 21)

---

## A — Architecture Systeme

### C01 — Vue Globale

![Architecture Macro](png/C01-architecture-macro.png)

### C02 — Sous-systeme ETL

![ETL Components](png/C02-etl-components.png)

### C03 — Sous-systeme ML

![ML Components](png/C03-ml-components.png)

### C04 — FastAPI Backend

![API Components](png/C04-api-components.png)

### C05 — Frontend Streamlit

![Frontend Components](png/C05-frontend-components.png)

---

## B — Diagrammes de Classes

### CL01 — Modeles Pydantic

![Pydantic Models](png/CL01-pydantic-models.png)

### CL02 — ORM SQLAlchemy

![ORM Models](png/CL02-orm-models.png)

### CL03 — Schemas API

![API Schemas](png/CL03-api-schemas.png)

### CL04 — ML Rules Engine

![ML Rules](png/CL04-ml-rules-models.png)

### CL05 — Arbre d'Exceptions

![Exceptions](png/CL05-exceptions.png)

---

## C — Diagrammes de Sequence

### SQ01 — Authentification JWT

![Auth JWT](png/SQ01-auth-jwt-flow.png)

### SQ02 — Chargement Dashboard

![Dashboard Request](png/SQ02-dashboard-request.png)

### SQ03 — Generation de Signaux

![Signal Generation](png/SQ03-signal-generation.png)

### SQ04 — Chatbot LLM

![Chat Flow](png/SQ04-chat-llm-flow.png)

---

## D — Diagrammes d'Activite

### AC01 — Pipeline ETL

![ETL Pipeline](png/AC01-etl-pipeline.png)

### AC02 — Cycle de Vie d'un Signal

![Signal Lifecycle](png/AC02-signal-lifecycle.png)

---

## E — Deploiement

### DP01 — Infrastructure Docker Compose

![Docker Infrastructure](png/DP01-docker-infrastructure.png)

---

## F — Base de Donnees

### ER01 — Schema TimescaleDB

![Database Schema](png/ER01-database-schema.png)

---

## G — Phase 2

### C06 — Pipeline ML Phase 2

![Phase 2 ML](png/C06-phase2-ml-pipeline.png)

### C07 — Roadmap Features F1-F8

![Phase 2 Features](png/C07-phase2-features.png)

---

## H — Cas d'Utilisation et Etats

### UC01 — Personas

![Personas](png/UC01-personas.png)

### ST01 — Machine a Etats Signal

![Signal States](png/ST01-signal-states.png)

---

## Build

```bash
make diagrams        # .puml -> .svg + .png (22 diagrammes)
make diagrams-clean  # supprimer les fichiers generes
make diagrams-list   # lister les sources
```

Prerequis : `plantuml-local-client` (`uv tool install plantuml-local-client`) + Java 21
