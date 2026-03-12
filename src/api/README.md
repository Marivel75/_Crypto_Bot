# API — Equipe Backend

Voir `docs/03-backend-api.md` pour le detail des taches, endpoints et specifications.

## Structure attendue

```
src/api/
├── __init__.py
├── main.py                 # App FastAPI, CORS, middleware
├── config.py               # Settings (pydantic-settings)
├── dependencies.py         # Dependency injection (DB session, current_user)
├── routers/
│   ├── auth.py             # Register, login, me
│   ├── crypto.py           # Prix, indicateurs, market overview
│   ├── signals.py          # Signaux actifs, par symbol, performance
│   ├── news.py             # Articles, sentiment
│   ├── portfolio.py        # CRUD portfolio
│   ├── watchlist.py        # CRUD watchlist
│   ├── chat.py             # Chatbot IA
│   └── system.py           # Health, sources status
├── services/
│   ├── auth_service.py
│   ├── crypto_service.py
│   ├── signal_service.py
│   └── chat_service.py
├── Dockerfile
└── requirements.txt
```
