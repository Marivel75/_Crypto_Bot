---
type: rncp-livrable
bloc: 3
livrable: api-contract
competences:
  - C3.1
  - C3.2
  - C3.3
  - C3.4
title: Contrat API v1 — FastAPI
version: 1.0.0
status: draft
tags:
  - cryptobot
  - rncp
  - bloc3
  - api
  - fastapi
  - openapi
  - swagger
  - jwt
created: 2026-04-14
produced_by: L3-API-Swagger
related:
  - "[[CryptoBot/avril/architecture/c04-api-components]]"
  - "[[CryptoBot/avril/architecture/cl03-api-schemas]]"
  - "[[CryptoBot/avril/architecture/sq01-auth-jwt-flow]]"
  - "[[CryptoBot/avril/code/api]]"
  - "[[rncp/bloc3-deploiement/api-openapi]]"
  - "[[rncp/bloc3-deploiement/test-coverage-report]]"
---

# Contrat API v1 — CryptoBot FastAPI

Ce document decrit l'interface de programmation exposee par le service `api` de CryptoBot. Il sert de reference stable pour les equipes Frontend, DevOps, QA et les partenaires tiers. Il est livre dans le bloc 3 RNCP38919 — **Deploiement continu** — et alimente la grille C3.1 (specs techniques), C3.2 (securite), C3.3 (observabilite), C3.4 (versioning).

Source de verite executable : `/api/openapi.json` (export FastAPI). Ce markdown en est la lecture humaine.

---

## 1. Stack & versions

| Composant | Version | Role |
|-----------|---------|------|
| Python | 3.11+ | Runtime serveur |
| FastAPI | `>=0.111,<1.0` | Framework ASGI, generation OpenAPI 3.1 |
| Uvicorn | `>=0.29,<1.0` | Serveur ASGI (workers `uvicorn.workers.UvicornWorker`) |
| Pydantic | v2 (`>=2,<3`) | Validation + serialisation des schemas |
| pydantic-settings | `>=2,<3` | Configuration via env vars |
| SQLAlchemy | `2.0.x` async + `asyncpg` | ORM TimescaleDB |
| python-jose[cryptography] | `>=3.3,<4` | Signature/verification JWT HS256 |
| bcrypt | `>=4,<5` | Hashage des mots de passe |
| httpx | `>=0.27,<1` | Client HTTP sortant (services tiers) |
| prometheus-fastapi-instrumentator | `>=6.1,<7` | Middleware metriques |

Reference code : `src/api/requirements.txt`, `src/api/main.py`, `src/api/config.py`.

---

## 2. Architecture en couches

Pattern Clean / Hexagonal allege. Chaque requete suit :

```
Client (Streamlit / Nginx)
  -> Nginx (TLS + rate limit + /api/ routing)
    -> FastAPI router (src/api/routers/*.py)
      -> Dependency (get_db, get_current_user)         # src/api/dependencies.py
        -> Service (src/api/services/*.py)             # regles metier
          -> Repository / ORM (SQLAlchemy AsyncSession)
            -> TimescaleDB (hypertables)
```

| Couche | Responsabilite | Fichiers |
|--------|----------------|----------|
| Router | Declaration HTTP, validation entree, enveloppe sortie | `src/api/routers/` (8 modules) |
| Dependencies | DI FastAPI : session DB, auth JWT, decodage `sub` | `src/api/dependencies.py` |
| Services | Logique metier, orchestration multi-repo | `src/api/services/` |
| ORM | Requetes SQL typees, transactions | `src/shared/models/orm.py` |
| Schemas | Contrats entree/sortie Pydantic v2 | `src/api/schemas.py` |
| Config | Settings singleton via pydantic-settings | `src/shared/config.py` |

Voir le diagramme de composants [[CryptoBot/avril/architecture/c04-api-components]].

Regles :

- Les routers ne touchent **jamais** a la DB directement — ils passent par un service.
- Les services n'importent **jamais** FastAPI — ils recoivent une `AsyncSession` typee.
- Les exceptions metier (`CryptoBotError` + sous-classes) sont capturees par un unique handler global (`src/api/main.py:75`) et converties en `ApiResponse` avec `status_code` approprie.

---

## 3. Authentification & autorisation

### 3.1 Schema retenu

| Element | Valeur |
|---------|--------|
| Type | Bearer JWT |
| Algorithme signature | HS256 (HMAC-SHA256) |
| Cle | `API_SECRET_KEY` env var (min. 32 bytes en prod) |
| Expiration | `JWT_EXPIRATION_HOURS` = 24 h |
| Claims | `sub` (user UUID), `exp` (timestamp), `iat` (issued at) |
| Stockage cote client | `localStorage` / session Streamlit |
| Header | `Authorization: Bearer <token>` |
| Token refresh | **Roadmap v2** (non implemente en v1) |
| Revocation | **Roadmap v2** (blacklist Redis prevue) |

Code de reference : `src/api/services/auth_service.py:105` (`create_access_token`), `src/api/dependencies.py:36` (`get_current_user`).

### 3.2 Politique mot de passe

Contraintes appliquees par `RegisterRequest` (`src/api/schemas.py:52`) :

| Regle | Implementation |
|-------|----------------|
| Longueur min. | 8 caracteres |
| Longueur max. | 128 caracteres |
| Majuscule | `re.search(r"[A-Z]", v)` |
| Chiffre | `re.search(r"\d", v)` |
| Caractere special | `re.search(r"[!@#$%^&*(),.?\":{}\|<>]", v)` |
| Hashage | bcrypt cost 12 (defaut) |

### 3.3 Endpoints auth

| Methode | Path | Auth | Rate-limit | Description |
|---------|------|------|-----------|-------------|
| POST | `/api/v1/auth/register` | — | `auth_limit` 5r/m burst=3 | Creer un compte. `201 Created` + `UserResponse`. |
| POST | `/api/v1/auth/login` | — | `auth_limit` 5r/m burst=3 | Authentifier et retourner un JWT. |
| GET | `/api/v1/auth/me` | Bearer | `api_limit` 30r/s | Retourner le profil courant. |

Voir flow detaille : [[CryptoBot/avril/architecture/sq01-auth-jwt-flow]].

---

## 4. Inventaire des endpoints (v1)

Prefixe global : `/api/v1`. Exception : `/health` et `/metrics` sont montes a la racine pour les probes Docker / Prometheus.

### 4.1 auth (tag `auth`)

Code : `src/api/routers/auth.py`.

| Methode | Path | Auth | Status OK | Rate-limit | Description |
|---------|------|------|-----------|-----------|-------------|
| POST | `/api/v1/auth/register` | non | 201 | 5r/m burst=3 | Creation de compte |
| POST | `/api/v1/auth/login` | non | 200 | 5r/m burst=3 | Login, retourne `LoginResponse` |
| GET | `/api/v1/auth/me` | oui | 200 | 30r/s burst=20 | Profil courant |

### 4.2 crypto (tag `crypto`)

Code : `src/api/routers/crypto.py`.

| Methode | Path | Auth | Status OK | Description |
|---------|------|------|-----------|-------------|
| GET | `/api/v1/crypto/list` | non | 200 | Liste des symboles suivis |
| GET | `/api/v1/crypto/market-overview` | non | 200 | Market cap, Fear&Greed, top movers |
| GET | `/api/v1/crypto/{symbol}/prices` | non | 200 | OHLCV paginee (`timeframe`, `start`, `end`, `limit<=1000`, `page`) |
| GET | `/api/v1/crypto/{symbol}/indicators` | non | 200 | RSI, Bollinger, pattern harmonique, trend |
| GET | `/api/v1/crypto/{symbol}/latest` | non | 200 | Dernier snapshot OHLCV + indicateurs |

Contraintes de path : `symbol` regex `^[A-Z0-9]+$`. Contrainte de query : `timeframe` regex `^\d+[mhDWM]$`.

### 4.3 signals (tag `signals`)

Code : `src/api/routers/signals.py`.

| Methode | Path | Auth | Status OK | Description |
|---------|------|------|-----------|-------------|
| GET | `/api/v1/signals/active` | non | 200 | Signaux des 24 dernieres heures |
| GET | `/api/v1/signals/performance` | non | 200 | Stats agregees (win_rate, total_pnl) |
| GET | `/api/v1/signals/{signal_id}/detail` | non | 200 | Detail + outcome post-hoc |
| GET | `/api/v1/signals/{symbol}` | non | 200 | Signaux par symbole, paginee |

Subscription WebSocket `/api/v1/signals/ws` : **roadmap v2** (actuellement poll 30 s cote frontend).

### 4.4 news (tag `news`)

Code : `src/api/routers/news.py`.

| Methode | Path | Auth | Status OK | Description |
|---------|------|------|-----------|-------------|
| GET | `/api/v1/news/latest` | non | 200 | Articles recents filtres par `source`, `keyword` |
| GET | `/api/v1/news/sentiment` | non | 200 | Sentiment agrege par source |
| GET | `/api/v1/news/{news_id}` | non | 200 | Article par UUID |

### 4.5 portfolio (tag `portfolio`)

Code : `src/api/routers/portfolio.py`. **Toutes les routes requierent Bearer JWT.**

| Methode | Path | Auth | Status OK | Description |
|---------|------|------|-----------|-------------|
| GET | `/api/v1/portfolio` | oui | 200 | Positions de l'utilisateur |
| POST | `/api/v1/portfolio` | oui | 201 | Ajouter une position |
| PUT | `/api/v1/portfolio/{entry_id}` | oui | 200 | Mettre a jour une position |
| DELETE | `/api/v1/portfolio/{entry_id}` | oui | 200 | Supprimer une position |

### 4.6 watchlist (tag `watchlist`)

Code : `src/api/routers/watchlist.py`. **Bearer requis.**

| Methode | Path | Auth | Status OK | Description |
|---------|------|------|-----------|-------------|
| GET | `/api/v1/watchlist` | oui | 200 | Watchlist de l'utilisateur |
| POST | `/api/v1/watchlist` | oui | 201 | Ajouter un symbole |
| DELETE | `/api/v1/watchlist/{symbol}` | oui | 200 | Retirer un symbole |

### 4.7 chat (tag `chat`)

Code : `src/api/routers/chat.py`. **Bearer requis.**

| Methode | Path | Auth | Status OK | Description |
|---------|------|------|-----------|-------------|
| POST | `/api/v1/chat` | oui | 200 | Proxy LLM, retour `reply` + `disclaimer` si keywords financiers |

Streaming SSE : **roadmap v2** (actuellement reponse synchrone).

### 4.8 system (tag `system`)

Code : `src/api/routers/system.py`.

| Methode | Path | Auth | Status OK | Description |
|---------|------|------|-----------|-------------|
| GET | `/health` | non | 200 | Healthcheck DB (`SELECT 1`), probe Docker/Nginx |
| GET | `/metrics` | non | 200 | Export Prometheus (exclu d'OpenAPI) |
| GET | `/api/v1/system/sources-status` | non | 200 | Derniere ingestion par source/symbol |

### 4.9 Documentation & meta

| Methode | Path | Description |
|---------|------|-------------|
| GET | `/api/docs` | Swagger UI interactive |
| GET | `/api/redoc` | ReDoc statique |
| GET | `/api/openapi.json` | Spec OpenAPI 3.1 en JSON (source de verite) |

---

## 5. Enveloppe de reponse standard

Toute reponse (succes ou erreur) est wrappee dans `ApiResponse[T]`. Reference : `src/api/schemas.py:37` et [[CryptoBot/avril/architecture/cl03-api-schemas]].

### 5.1 Schema

```json
{
  "data": "<T | null>",
  "error": {
    "code": "STRING_CODE",
    "message": "human-readable"
  },
  "meta": {
    "total": 0,
    "page": 1,
    "limit": 100
  }
}
```

| Champ | Type | Presence |
|-------|------|----------|
| `data` | `T \| null` | Present en succes, `null` en erreur |
| `error` | `ErrorDetail \| null` | Present seulement en erreur |
| `meta` | `PaginationMeta \| null` | Present seulement sur endpoints paginated |

Regle : `data` et `error` sont **mutuellement exclusifs**.

### 5.2 Exemple succes

```json
{
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer"
  }
}
```

### 5.3 Exemple erreur

```json
{
  "data": null,
  "error": {
    "code": "AuthenticationError",
    "message": "Invalid or expired token"
  }
}
```

### 5.4 Exemple paginee

```json
{
  "data": [
    {
      "symbol": "BTCUSDT",
      "timeframe": "1h",
      "timestamp": "2026-04-14T10:00:00Z",
      "price_open": 66900.0,
      "price_high": 67200.0,
      "price_low": 66800.0,
      "price_close": 67000.0,
      "volume_24h": 12000000000.0,
      "source": "binance"
    }
  ],
  "meta": { "total": 8421, "page": 1, "limit": 100 }
}
```

---

## 6. Codes d'erreur HTTP

Mapping exception -> status via `CryptoBotError.status_code` (`src/shared/exceptions.py`).

| Status | `error.code` typique | Cas |
|--------|----------------------|-----|
| 400 | `BadRequestError` | Requete malformee (non-JSON, charset invalide) |
| 401 | `AuthenticationError` | JWT absent, expire, signature invalide, user introuvable |
| 403 | `AuthorizationError` | User connecte mais sans droit sur la ressource |
| 404 | `NotFoundError` | UUID inexistant (signal, news, position) |
| 409 | `ConflictError` | Symbole deja dans la watchlist, email deja enregistre |
| 422 | `VALIDATION_ERROR` | Violation Pydantic (regex, length, password policy) |
| 429 | nginx `Too Many Requests` | Rate limit Nginx depasse |
| 500 | `INTERNAL_ERROR` | Exception non capturee (handler global, logs structures) |
| 502 | `UpstreamError` | Binance / CoinGecko / LLM down (propagation via httpx) |
| 503 | — | Healthcheck degrade (`status: degraded`) |

Structure garantie : toute 4xx/5xx renvoie l'enveloppe `ApiResponse` avec `error` peuple, jamais de stacktrace brute.

---

## 7. Rate limiting (Nginx)

Configuration : `infra/nginx/nginx.conf`.

| Zone | Rate | Burst | Applique sur | Usage |
|------|------|-------|--------------|-------|
| `api_limit` | 30 r/s | 20 | `location /api/` | Endpoints metier |
| `auth_limit` | 5 r/m | 3 | `location /api/auth/` | Brute-force login/register |

Algorithme : Nginx `limit_req_zone` (leaky bucket). Cle : `$binary_remote_addr` (10 MB = ~160k IP).

Depassement -> HTTP 429 (Nginx avec `limit_req_status 429;`). Header `Retry-After` envoye.

Ordre de livraison :

1. Nginx reject (429) — economies CPU.
2. FastAPI reject (422 validation, 401 auth) — appli healthy.
3. Service layer — transaction ouverte.

---

## 8. Observabilite

### 8.1 Logs

| Propriete | Valeur |
|-----------|--------|
| Format | JSON structure (`src/api/main.py:29`) |
| Niveau | `LOG_LEVEL` env var (`INFO` prod, `DEBUG` staging) |
| Sortie | stdout (Docker -> Loki via docker-loki plugin) |
| Champs standards | `asctime`, `levelname`, `name`, `message` |

### 8.2 Request ID

Chaque requete porte un header `X-Request-ID` :

- Genere par Nginx (`$request_id` 32-char hex) si absent.
- Propage au backend, injecte dans les logs via middleware (roadmap — actuellement logge par Nginx uniquement).
- Retourne dans la reponse pour correlation cote client.

### 8.3 Metriques Prometheus

Instrumentation via `prometheus-fastapi-instrumentator` (`src/api/main.py:68`).

| Metrique | Type | Labels |
|----------|------|--------|
| `http_requests_total` | counter | `method`, `handler`, `status`, `app_name` |
| `http_request_duration_seconds` | histogram | `method`, `handler`, `status` |
| `http_request_size_bytes` | summary | `method`, `handler` |
| `http_response_size_bytes` | summary | `method`, `handler` |
| `http_requests_in_progress` | gauge | `method` |

Exposition : `GET /metrics` (exclu d'OpenAPI via `include_in_schema=False`). Scrape Prometheus 15 s. Dashboards Grafana : `infra/grafana/dashboards/api_overview.json`.

### 8.4 SLO cibles

| SLO | Cible v1 | Mesure |
|-----|----------|--------|
| Disponibilite | 99.0 % | `up{job="api"}` + probe healthcheck |
| Latence p95 `/api/v1/crypto/*` | < 300 ms | `histogram_quantile(0.95, ...)` |
| Latence p95 `/api/v1/auth/*` | < 500 ms | idem (bcrypt cost 12) |
| Error rate 5xx | < 1 % | `rate(http_requests_total{status=~"5.."}[5m])` |

---

## 9. CORS

Configuration : `src/api/main.py:58` + `src/shared/config.py:80`.

| Propriete | Valeur |
|-----------|--------|
| `allow_origins` | env var `CORS_ORIGINS` (defaut : `http://localhost:8501`) |
| `allow_credentials` | `true` (cookie/JWT cross-site) |
| `allow_methods` | `GET, POST, PUT, DELETE, OPTIONS, PATCH` |
| `allow_headers` | `*` (dont `Authorization`, `Content-Type`, `X-Request-ID`) |
| `expose_headers` | `X-Request-ID` |
| `max_age` | 600 s (preflight cache) |

En prod, `CORS_ORIGINS` contient uniquement le domaine Streamlit derriere Nginx (`https://crypto.<domaine>`).

---

## 10. Documentation interactive

| UI | Path | Usage |
|----|------|-------|
| Swagger UI | `/api/docs` | Tests interactifs, auth Bearer en 2 clics |
| ReDoc | `/api/redoc` | Lecture statique, print-friendly, export PDF |
| OpenAPI JSON | `/api/openapi.json` | Import Postman / Insomnia, generation SDK |

La UI Swagger supporte l'onglet **Authorize** (icone cadenas) pour injecter le token Bearer. Les endpoints proteges sont marques d'un cadenas.

### 10.1 Captures a fournir (livrable screenshots)

Les captures suivantes doivent figurer dans le dossier RNCP bloc 3 (PDF annexe) :

| # | Capture | Contenu attendu |
|---|---------|-----------------|
| 1 | `swagger-overview.png` | Page `/api/docs` complete, les 8 tags visibles (`auth`, `crypto`, `signals`, `news`, `portfolio`, `watchlist`, `chat`, `system`) |
| 2 | `swagger-auth-login.png` | Endpoint `POST /api/v1/auth/login` deplie, exemple body JSON, bouton **Try it out** |
| 3 | `swagger-authorize-dialog.png` | Modale **Authorize** avec champ Bearer rempli |
| 4 | `swagger-signals-active.png` | Reponse 200 de `GET /api/v1/signals/active` avec enveloppe `ApiResponse` et un signal reel (BTCUSDT ou ETHUSDT) |
| 5 | `swagger-422-validation.png` | Tentative register avec password trop court -> 422 + `error.code: VALIDATION_ERROR` |
| 6 | `redoc-landing.png` | Page `/api/redoc` avec sidebar des tags, version `1.0.0` et titre |
| 7 | `redoc-schemas-panel.png` | Panneau `ApiResponse`, `SignalResponse`, `UserResponse` deplie cote ReDoc |
| 8 | `swagger-rate-limit-429.png` | Retour 429 apres burst sur `/api/v1/auth/login` (Nginx) |

Captures a prendre sur l'environnement de staging `https://staging.crypto.<domaine>/api/docs` apres deploiement CD reussi.

---

## 11. Versioning

| Regle | Valeur |
|-------|--------|
| Version en URL | `/api/v1/*` (actuelle) |
| Version en header | non supporte (simplicite) |
| Breaking change -> | `/api/v2/*` monte en parallele, v1 maintenue 6 mois |
| Deprecation | Header `Deprecation: true` + `Sunset: <RFC 8594 date>` 3 mois avant retrait |
| Changelog | `docs/CHANGELOG-API.md` (roadmap) |

Criteres breaking change (RFC 9745 style) :

- Retrait/renommage d'un champ dans `data`.
- Changement de type d'un champ existant.
- Ajout d'un champ obligatoire dans un body.
- Changement de status code en succes.

Non-breaking (pas de bump) : ajout d'un endpoint, ajout d'un champ optionnel, ajout d'un `code` d'erreur.

---

## 12. Tests

La couverture et la strategie de tests associes sont documentees dans [[rncp/bloc3-deploiement/test-coverage-report]].

| Niveau | Tool | Cible | Exemples |
|--------|------|-------|----------|
| Unit | pytest + pytest-asyncio | `src/api/services/*` | `test_create_access_token_payload` |
| Integration | pytest + httpx.AsyncClient + docker-compose | routers + DB | `test_login_returns_jwt_and_200` |
| Contract | Schemathesis (roadmap) | `openapi.json` | Property-based, 1000 cases |
| E2E | Playwright | Streamlit -> API | `test_user_can_create_watchlist_entry` |
| Load | k6 | staging | 100 VU sur `/api/v1/crypto/*`, p95 < 300 ms |

Seuil de coverage : `--cov-fail-under=78` (`pyproject.toml:76`), objectif 80 % apres stabilisation v1.1.

---

## 13. References croisees

- [[CryptoBot/avril/architecture/c04-api-components]] — composants & dependances
- [[CryptoBot/avril/architecture/cl03-api-schemas]] — ~30 schemas Pydantic detailles
- [[CryptoBot/avril/architecture/sq01-auth-jwt-flow]] — sequence JWT login/refresh
- [[CryptoBot/avril/architecture/sq02-dashboard-request]] — sequence dashboard Streamlit -> API
- [[CryptoBot/avril/code/api]] — cartographie du code
- [[rncp/bloc3-deploiement/api-openapi]] — spec executable OpenAPI 3.1

---

## 14. Roadmap contract v2

| Item | Priorite | Justification |
|------|----------|---------------|
| `POST /api/v1/auth/refresh` | haute | Prolonger session sans re-login |
| `DELETE /api/v1/auth/me` | haute | RGPD art. 17 (droit a l'effacement) |
| WebSocket `/api/v1/signals/ws` | moyenne | Reduire latence push < 1 s |
| SSE `/api/v1/chat/stream` | moyenne | UX LLM streaming |
| OAuth2 Google | basse | Simplifier onboarding |
| GraphQL gateway | basse | Mobile app future |
