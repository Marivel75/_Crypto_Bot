# 03 — Equipe Backend / API

> **Lisez d'abord** `docs/00-overview.md` pour le contexte global du projet.

---

## Votre perimetre

Vous etes responsables de **l'API REST** qui sert de colonne vertebrale entre la BDD et le frontend.

| Vous gerez | Vous NE gerez PAS |
|-----------|-------------------|
| FastAPI : tous les endpoints REST | La collecte de donnees (equipe Data Eng) |
| Authentification (login, sessions, JWT) | Les modeles ML (equipe ML) |
| Logique metier des endpoints | L'interface Streamlit (equipe Frontend) |
| Validation des requetes entrantes (pydantic) | Le schema BDD / migrations (equipe Data Eng) |
| Documentation API (Swagger auto) | Docker/CI/CD (equipe DevOps) |

**Votre code va dans** : `src/api/`
**Votre branche** : `backend/xxx`

---

## Ce que les autres equipes attendent de vous

| Equipe | Ce qu'elle attend | Interface |
|--------|------------------|-----------|
| **Frontend** | Des endpoints REST stables, documentes, avec Swagger | `GET /api/v1/...`, documentation auto FastAPI |
| **ML** | Rien directement — le ML insert dans la BDD, vous servez les signaux | Table `trading_signals` |
| **Data Eng** | Un endpoint de healthcheck | `GET /health` |
| **DevOps** | Un Dockerfile fonctionnel, un healthcheck HTTP | `Dockerfile` dans `src/api/` |

## Ce que vous consommez

| Source | Quoi | Ou |
|--------|------|-----|
| **Data Eng** | Schema BDD (TimescaleDB) | Models SQLAlchemy dans `src/shared/` |
| **Data Eng** | Models pydantic partages | `src/shared/models/` |
| **ML** | Signaux dans `trading_signals` | Vous les lisez, pas les ecrivez |

---

## Endpoints API

### Auth

| Methode | Endpoint | Description |
|---------|----------|-------------|
| `POST` | `/api/v1/auth/register` | Creer un compte (username, email, password, persona_type) |
| `POST` | `/api/v1/auth/login` | Login → retourne un JWT |
| `GET` | `/api/v1/auth/me` | Info utilisateur courant (JWT requis) |

### Crypto / Prix

| Methode | Endpoint | Description |
|---------|----------|-------------|
| `GET` | `/api/v1/crypto/list` | Liste des cryptos suivies |
| `GET` | `/api/v1/crypto/{symbol}/prices` | OHLCV pour un symbol (params: timeframe, start, end, limit) |
| `GET` | `/api/v1/crypto/{symbol}/indicators` | Indicateurs techniques (params: timeframe) |
| `GET` | `/api/v1/crypto/{symbol}/latest` | Dernier prix + indicateurs |
| `GET` | `/api/v1/crypto/market-overview` | Resume marche : top movers, fear & greed, market cap total |

### Signaux

| Methode | Endpoint | Description |
|---------|----------|-------------|
| `GET` | `/api/v1/signals/active` | Signaux actifs (derniers 24h) |
| `GET` | `/api/v1/signals/{symbol}` | Signaux pour une crypto (params: timeframe, limit) |
| `GET` | `/api/v1/signals/{id}/detail` | Detail d'un signal (regles, TF alignes, confiance) |
| `GET` | `/api/v1/signals/performance` | Taux de reussite des signaux passes |

### News

| Methode | Endpoint | Description |
|---------|----------|-------------|
| `GET` | `/api/v1/news/latest` | Dernieres news (params: source, keyword, limit) |
| `GET` | `/api/v1/news/{id}` | Detail d'un article + sentiment + text mining |
| `GET` | `/api/v1/news/sentiment` | Score de sentiment agrege par crypto |

### Portfolio

| Methode | Endpoint | Description |
|---------|----------|-------------|
| `GET` | `/api/v1/portfolio` | Portefeuille de l'utilisateur (JWT requis) |
| `POST` | `/api/v1/portfolio` | Ajouter une position |
| `PUT` | `/api/v1/portfolio/{id}` | Modifier une position |
| `DELETE` | `/api/v1/portfolio/{id}` | Supprimer une position |

### Watchlist

| Methode | Endpoint | Description |
|---------|----------|-------------|
| `GET` | `/api/v1/watchlist` | Watchlist de l'utilisateur |
| `POST` | `/api/v1/watchlist` | Ajouter un symbol |
| `DELETE` | `/api/v1/watchlist/{symbol}` | Retirer un symbol |

### Chatbot

| Methode | Endpoint | Description |
|---------|----------|-------------|
| `POST` | `/api/v1/chat` | Envoyer un message au chatbot IA (JWT requis) |

### System

| Methode | Endpoint | Description |
|---------|----------|-------------|
| `GET` | `/health` | Healthcheck (status BDD, services) |
| `GET` | `/api/v1/system/sources-status` | Etat des sources de donnees (uptime, derniere collecte) |

---

## Authentification

### Option V1 : Auth legere dans FastAPI

```python
# Principes :
# - bcrypt pour le hashing des mots de passe
# - JWT (PyJWT) pour les sessions
# - Token dans le header Authorization: Bearer <token>
# - Expiration : 24h
# - Middleware FastAPI pour proteger les routes

# Dependances : passlib[bcrypt], python-jose[cryptography]
```

Suffisant si l'outil est prive et utilise par 2-3 personnes.

### Option V1.5 : Authelia

Si on veut un systeme plus propre plus tard :
- **Authelia** devant Nginx (SSO + MFA)
- Open source, s'integre comme middleware reverse proxy
- Dans ce cas, FastAPI ne gere plus l'auth, Authelia le fait en amont

**Pour l'instant, commencez par l'option V1.**

---

## Conventions

### Structure du code

```
src/api/
├── main.py                 # App FastAPI, CORS, middleware
├── config.py               # Settings (pydantic-settings, lit .env)
├── dependencies.py         # Dependency injection (DB session, current_user)
├── routers/
│   ├── auth.py
│   ├── crypto.py
│   ├── signals.py
│   ├── news.py
│   ├── portfolio.py
│   ├── watchlist.py
│   ├── chat.py
│   └── system.py
├── services/               # Logique metier
│   ├── auth_service.py
│   ├── crypto_service.py
│   ├── signal_service.py
│   └── chat_service.py
├── Dockerfile
└── requirements.txt
```

### Reponses API

Format standard pour toutes les reponses :

```json
{
  "data": { ... },
  "error": null,
  "meta": {
    "total": 100,
    "page": 1,
    "limit": 20
  }
}
```

En cas d'erreur :
```json
{
  "data": null,
  "error": {
    "code": "NOT_FOUND",
    "message": "Signal not found"
  },
  "meta": null
}
```

### Pagination

Tous les endpoints qui retournent des listes supportent :
- `?page=1&limit=20` (defaut)
- Retourner `meta.total`, `meta.page`, `meta.limit`

### CORS

Autoriser uniquement l'origine du frontend Streamlit (configurable via `.env`).

---

## Chatbot IA

Le chatbot utilise un LLM (OpenAI GPT-4o-mini ou Claude Haiku) pour repondre aux questions des utilisateurs sur les donnees crypto.

| Parametre | Valeur |
|-----------|--------|
| LLM | GPT-4o-mini (defaut) ou Claude Haiku |
| API | OpenAI API / Anthropic API |
| Cle API | Dans `.env` (`OPENAI_API_KEY` ou `ANTHROPIC_API_KEY`) |
| System prompt | Contexte injecte : derniers prix, signaux actifs, portefeuille utilisateur |
| Disclaimer | Chaque reponse commence par "Je ne suis pas un conseiller financier." si la question touche au trading |

```python
# Pseudo-code du service chatbot
async def chat(user_message: str, user_id: str) -> str:
    # 1. Recuperer le contexte (derniers prix, signaux, portfolio)
    context = await build_context(user_id)
    # 2. Appeler le LLM avec system prompt + contexte + message
    response = await llm_client.chat(
        system=SYSTEM_PROMPT + context,
        user=user_message
    )
    return response
```

---

## Taches

### Sprint 7 (Avril)
- [ ] Setup FastAPI (main.py, config, CORS)
- [ ] Auth : register, login, JWT, middleware
- [ ] Endpoints crypto : list, prices, indicators, latest, market-overview
- [ ] Endpoints signaux : active, par symbol, detail, performance
- [ ] Endpoints news : latest, detail, sentiment
- [ ] Endpoints portfolio : CRUD
- [ ] Endpoints watchlist : CRUD
- [ ] Healthcheck
- [ ] Documentation Swagger auto
- [ ] Tests unitaires + integration

### Sprint 8 (Mai)
- [ ] Chatbot IA (service + endpoint)
- [ ] Endpoint system/sources-status
- [ ] Pagination sur tous les endpoints de liste
- [ ] Optimisation des requetes BDD (indexes, limit)
- [ ] Tests fonctionnels
