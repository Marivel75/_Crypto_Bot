# 06 — Architecture Applicative

## 1. Architecture Globale

### 1.1 Vue d'ensemble du système

```
┌──────────────────────────────────────────────────────────────────────────┐
│                    SOURCES DE DONNÉES EXTERNES                           │
│  [Binance] [CoinGecko] [CCXT] [News RSS] [Alternative.me] [Regulatory]  │
└─────────────────────────────────┬──────────────────────────────────────┘
                                  │
                    ┌─────────────▼──────────────┐
                    │   ETL PIPELINE             │
                    │  (src/etl/*)               │
                    │  APScheduler + Collectors  │
                    │  Transformers + Loaders    │
                    └─────────────┬──────────────┘
                                  │
            ┌─────────────────────┴─────────────────────┐
            │                                           │
    ┌───────▼────────┐                      ┌──────────▼───────┐
    │  TimescaleDB   │                      │    MinIO (S3)    │
    │  + PostgreSQL  │                      │  (Artifacts ML,  │
    │ (OHLCV, users) │                      │   datasets, etc) │
    └────────┬────────┘                      └──────────────────┘
             │
    ┌────────┴──────────────────┐
    │                           │
┌───▼────────────────┐   ┌─────▼──────────────────┐
│  ML ENGINE         │   │  FastAPI Backend       │
│  (src/ml/*)        │   │  (src/api/*)           │
│  • Rule Engine     │   │  • Routers (8)         │
│  • Indicators      │   │  • Services            │
│  • Models (Phase2) │   │  • Dependencies        │
│  • MLflow          │   │  • Response Envelope   │
│  • Backtesting     │   │  • Exception Handlers  │
│  • Signal Gen      │   └──────┬────────────────┘
└────────┬───────────┘          │
         │                      │
         │             ┌────────▼──────────────┐
         │             │  Streamlit Frontend   │
         │             │  (src/frontend/*)     │
         │             │  • Multi-page app     │
         │             │  • API Client         │
         │             │  • Plotly Charts      │
         │             │  • Components         │
         │             │  • i18n (FR/EN)       │
         └─────────────│ • Caching (cache_data)│
                       └───────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│                INFRASTRUCTURE                                            │
│  Docker Compose | Nginx (reverse proxy) | GitHub Actions (CI/CD)       │
│  Prometheus metrics | Health checks | Logging                           │
└──────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Principes architecturaux

| Principe | Description | Bénéfice |
|----------|-----------|----------|
| **Séparation par équipe** | Chaque équipe a son répertoire et ses responsabilités | Réduction du couplage, autonomie |
| **Communication via API** | Les modules communiquent via HTTP REST seulement | Pas d'imports croisés entre équipes |
| **Modèles partagés** | `src/shared/models/` contient les Pydantic models | Contrats de données explicites |
| **Async/await partout** | SQLAlchemy async, httpx async, asyncio | Performance I/O, scalabilité |
| **Gestion d'erreurs structurée** | Hiérarchie d'exceptions + handlers HTTP | Pas de fuite d'info interne |
| **Configuration centralisée** | `src/shared/config.py` (pydantic-settings) | Single source of truth |
| **Couches de Repository** | Pattern Repository pour l'accès aux données | Abstraction BD, testabilité |

---

## 2. Architecture API (FastAPI)

### 2.1 Couches architecturales

```
┌─────────────────────────────────────────────────┐
│          HTTP Client (Streamlit Frontend)       │
└────────────────┬────────────────────────────────┘
                 │ REST JSON
        ┌────────▼───────────┐
        │  FastAPI Routes    │  ← 8 routers (auth, crypto, signals, news,
        │  (src/api/routers) │     portfolio, watchlist, chat, system)
        └────────┬───────────┘
                 │ Dependency Injection
        ┌────────▼──────────────────┐
        │  Services Layer           │  ← Business logic
        │  (src/api/services)       │   (auth_service, crypto_service,
        │                           │    signal_service, chat_service, etc)
        └────────┬──────────────────┘
                 │
        ┌────────▼──────────────────┐
        │  Repository Layer         │  ← Data access
        │  (SQLAlchemy async)       │   (queries, writes)
        └────────┬──────────────────┘
                 │ SQL
        ┌────────▼──────────────────┐
        │  TimescaleDB             │  ← Persistent data
        │  (users, prices, signals)│
        └───────────────────────────┘
```

### 2.2 Structure des fichiers

```
src/api/
├── main.py                     # FastAPI app, CORS, middleware, exception handlers
├── config.py                   # API-specific settings (overrides src/shared/config)
├── dependencies.py             # Dependency injection: get_db, get_current_user, oauth2_scheme
├── schemas.py                  # Pydantic models for request/response (ApiResponse, ErrorDetail, etc)
├── routers/
│   ├── __init__.py
│   ├── auth.py                 # POST /auth/register, POST /auth/login, GET /auth/me
│   ├── crypto.py               # GET /crypto/list, GET /crypto/{symbol}/prices, GET /crypto/{symbol}/indicators
│   ├── signals.py              # GET /signals/active, GET /signals/{symbol}, GET /signals/{id}/detail, GET /signals/performance
│   ├── news.py                 # GET /news/latest, GET /news/{id}, GET /news/sentiment
│   ├── portfolio.py            # GET/POST/PUT/DELETE /portfolio, /portfolio/{id}
│   ├── watchlist.py            # GET /watchlist, POST /watchlist, DELETE /watchlist/{symbol}
│   ├── chat.py                 # POST /chat (chatbot IA)
│   └── system.py               # GET /health, GET /system/sources-status
├── services/
│   ├── __init__.py
│   ├── auth_service.py         # Hash password, create JWT, validate JWT
│   ├── crypto_service.py       # Query OHLCV, indicators, market overview
│   ├── signal_service.py       # Fetch active signals, performance stats
│   ├── chat_service.py         # Call LLM (GPT-4o-mini or Claude)
│   ├── news_service.py         # Query latest news, sentiment aggregation
│   └── user_data_service.py    # Portfolio, watchlist CRUD
├── Dockerfile                  # Multi-stage build
└── requirements.txt
```

### 2.3 Pattern API REST

#### Response Envelope (Obligatoire)

Toutes les réponses suivent ce format :

```python
{
    "data": T | None,           # Données du succès
    "error": ErrorDetail | None, # Erreur si failure
    "meta": PaginationMeta | None # Pagination si liste
}
```

Exemple success :
```json
{
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "symbol": "BTCUSDT",
    "timeframe": "4h",
    "direction": "BUY",
    "confidence": 0.75,
    "entry_price": 42500.00,
    "stop_loss": 41500.00,
    "take_profit": [44000.00, 45500.00],
    "timestamp": "2026-03-12T14:30:00Z"
  },
  "error": null,
  "meta": null
}
```

Exemple list avec pagination :
```json
{
  "data": [
    { "id": "...", "symbol": "BTCUSDT", ... },
    { "id": "...", "symbol": "ETHUSDT", ... }
  ],
  "error": null,
  "meta": {
    "total": 42,
    "page": 1,
    "limit": 20
  }
}
```

Exemple error :
```json
{
  "data": null,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid password: must contain uppercase, digit, special char"
  },
  "meta": null
}
```

#### Endpoints Clés

**Authentication**
| Méthode | Endpoint | Description |
|---------|----------|-------------|
| POST | `/api/v1/auth/register` | `{username, email, password, persona_type}` → `{access_token}` |
| POST | `/api/v1/auth/login` | `{email, password}` → `{access_token, token_type}` |
| GET | `/api/v1/auth/me` | Retourne profil utilisateur courant |

**Crypto Data**
| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/api/v1/crypto/list` | Liste des 30 cryptos suivies |
| GET | `/api/v1/crypto/{symbol}/prices` | OHLCV (params: timeframe, start, end, limit) |
| GET | `/api/v1/crypto/{symbol}/indicators` | RSI, Bollinger, trend lines (params: timeframe) |
| GET | `/api/v1/crypto/{symbol}/latest` | Dernier prix + indicateurs |
| GET | `/api/v1/crypto/market-overview` | Top movers, Fear & Greed, market cap total |

**Trading Signals**
| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/api/v1/signals/active` | Signaux émis dans les 24h |
| GET | `/api/v1/signals/{symbol}` | Tous les signaux passés pour une crypto |
| GET | `/api/v1/signals/{id}/detail` | Signal avec règles déclenchées, TF, règles pondérées |
| GET | `/api/v1/signals/performance` | Win rate, profit factor, drawdown max |

**News & Sentiment**
| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/api/v1/news/latest` | Dernières news (params: source, keyword, limit) |
| GET | `/api/v1/news/{id}` | Article avec sentiment, text mining |
| GET | `/api/v1/news/sentiment` | Score sentiment agrégé par crypto |

**User Data**
| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/api/v1/portfolio` | Positions de l'utilisateur (JWT requis) |
| POST | `/api/v1/portfolio` | Ajouter une position |
| PUT | `/api/v1/portfolio/{id}` | Modifier une position |
| DELETE | `/api/v1/portfolio/{id}` | Supprimer une position |
| GET | `/api/v1/watchlist` | Watchlist utilisateur |
| POST | `/api/v1/watchlist` | Ajouter un symbol |
| DELETE | `/api/v1/watchlist/{symbol}` | Retirer un symbol |

**Chatbot**
| Méthode | Endpoint | Description |
|---------|----------|-------------|
| POST | `/api/v1/chat` | `{message}` → Réponse LLM avec contexte |

**System**
| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/health` | Healthcheck (status DB, services) |
| GET | `/api/v1/system/sources-status` | Uptime des sources, dernière collecte |

### 2.4 Dependency Injection (FastAPI)

```python
# src/api/dependencies.py

# 1. get_db: Fournit une AsyncSession
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Ouvre une transaction DB, la commit en succès, rollback en erreur."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            logger.exception("DB session error, rolling back")
            await session.rollback()
            raise

# 2. get_current_user: Extrait JWT du header Authorization: Bearer <token>
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> UserOrm:
    """Valide JWT, cherche l'utilisateur en DB, retourne UserOrm."""
    payload = jwt.decode(token, settings.api_secret_key, algorithms=["HS256"])
    user_id = payload.get("sub")
    result = await db.execute(select(UserOrm).where(UserOrm.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise AuthenticationError("User not found")
    return user
```

Usage dans une route :
```python
@router.get("/api/v1/portfolio", response_model=ApiResponse[list[PortfolioResponse]])
async def get_portfolio(
    current_user: UserOrm = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[PortfolioResponse]]:
    """Retourne le portefeuille de l'utilisateur courant."""
    portfolio = await user_data_service.get_portfolio(db, current_user.id)
    return ApiResponse(data=portfolio)
```

### 2.5 Service Layer Pattern

Chaque router délègue la logique métier à un service :

```python
# src/api/services/crypto_service.py

class CryptoService:
    """Agrège les requêtes OHLCV, indicateurs, market overview."""

    async def get_prices(
        self,
        db: AsyncSession,
        symbol: str,
        timeframe: str,
        limit: int = 100,
    ) -> list[CryptoPrice]:
        """Récupère les OHLCV pour un symbol + timeframe."""
        # Query DB avec pagination
        result = await db.execute(
            select(CryptoPriceOrm)
            .where(
                (CryptoPriceOrm.symbol == symbol) &
                (CryptoPriceOrm.timeframe == timeframe)
            )
            .order_by(CryptoPriceOrm.timestamp.desc())
            .limit(limit)
        )
        rows = result.scalars().all()
        return [CryptoPrice.model_validate(row) for row in rows]

    async def get_indicators(
        self,
        db: AsyncSession,
        symbol: str,
        timeframe: str,
    ) -> dict[str, Any]:
        """Récupère les derniers indicateurs (RSI, Bollinger, trend)."""
        # Peut combiner plusieurs requêtes
        rsi = await self._get_rsi(db, symbol, timeframe)
        bollinger = await self._get_bollinger(db, symbol, timeframe)
        return {"rsi": rsi, "bollinger": bollinger}
```

Router l'utilise :
```python
@crypto_router.get("/crypto/{symbol}/prices")
async def get_prices(
    symbol: str,
    timeframe: str = "1h",
    limit: int = Query(100, le=500),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[CryptoPriceResponse]]:
    """Endpoint — valide params, appelle service, retourne ApiResponse."""
    symbol = symbol.upper()
    prices = await crypto_service.get_prices(db, symbol, timeframe, limit)
    return ApiResponse(data=[CryptoPriceResponse.model_validate(p) for p in prices])
```

### 2.6 Authentication Flow

```
User (Frontend)
    │
    ├─ 1. POST /api/v1/auth/register
    │     { username, email, password, persona_type }
    │     ↓
    └─→ auth_service.register()
        └─ Hash password (bcrypt 12 rounds)
        └─ Insert UserOrm
        └─ Return success

User logs in
    │
    ├─ 2. POST /api/v1/auth/login
    │     { email, password }
    │     ↓
    └─→ auth_service.login()
        └─ Récupère UserOrm par email
        └─ Valide password vs hash
        └─ Crée JWT (payload: sub=user_id, exp=now+24h)
        └─ Return { access_token, token_type: "bearer" }

Protected request
    │
    ├─ 3. GET /api/v1/portfolio
    │     Header: Authorization: Bearer <jwt_token>
    │     ↓
    └─→ get_current_user dependency
        └─ Décode JWT (HS256 + settings.api_secret_key)
        └─ Valide signature et expiration
        └─ Récupère user ID du payload (sub)
        └─ Cherche UserOrm en DB
        └─ Retourne UserOrm ou lève AuthenticationError
        └─ Route reçoit UserOrm
```

### 2.7 Middleware & Exception Handlers

**CORS Middleware**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,      # Liste depuis .env
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],  # Restrient
    allow_headers=["*"],
)
```

**Exception Handlers**
```python
# CryptoBotError (hiérarchie custom)
@app.exception_handler(CryptoBotError)
async def cryptobot_error_handler(request: Request, exc: CryptoBotError) -> JSONResponse:
    """Mappe l'exception à HTTP status et ApiResponse."""
    return JSONResponse(
        status_code=exc.status_code,
        content=ApiResponse(
            error=ErrorDetail(code=exc.__class__.__name__, message=exc.message)
        ).model_dump(mode="json"),
    )

# Validation Pydantic
@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Enveloppe erreurs 422 dans ApiResponse."""
    # ...

# Generic errors (no leak of stack trace)
@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Log complet, retourne message générique."""
    logger.exception("Unhandled error: %s", exc)
    return JSONResponse(
        status_code=500,
        content=ApiResponse(
            error=ErrorDetail(code="INTERNAL_ERROR", message="An unexpected error occurred")
        ).model_dump(mode="json"),
    )
```

**Prometheus Metrics**
```python
Instrumentator(
    should_group_status_codes=False,
    excluded_handlers=["/health", "/metrics"],
).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
```

---

## 3. Architecture ML

### 3.1 Flux du Signal

```
TimescaleDB (OHLCV)
    │
    ├─ 1. Signal Generator
    │     (src/ml/signal_generator.py)
    │     ↓
    │  ┌──────────────────────────────────────┐
    │  │ RuleEngine.evaluate()                │  ← Phase 1 (règles explicites)
    │  │  • RSI multi-TF (1h, 2h, 3h, 4h)    │
    │  │  • Bollinger Bands (squeeze, bands)  │
    │  │  • Harmonic patterns (bat, gartley)  │
    │  │  • Trend lines (weekly, monthly)     │
    │  │                                       │
    │  │  Returns:                            │
    │  │  {                                   │
    │  │   "direction": "BUY|SELL|HOLD",      │
    │  │   "confidence_score": 0.0-1.0,       │
    │  │   "rules_triggered": ["RSI_3TF", ...],│
    │  │   "timeframe": "4h"                  │
    │  │  }                                   │
    │  └──────────────────────────────────────┘
    │     │
    │     ├─ (Optional) ML Predictor
    │     │  • XGBoost, LightGBM, LSTM
    │     │  • Blend confidence (60% ML / 40% rules)
    │     │
    │     └─ Confidence >= 0.6?
    │        └─ YES: Emit TradingSignal
    │        └─ NO: Drop signal
    │
    └─→ TradingSignalOrm → TimescaleDB (trading_signals)
```

### 3.2 Structure du ML

```
src/ml/
├── signal_generator.py         # Orchestrateur signal (règles + ML)
│   └─ SignalGenerator class
│      ├─ generate(symbol, indicators) → TradingSignal | None
│      └─ Confidence filtering (>= 0.6)
│
├── rules/                      # Phase 1 rule engine
│   └─ rule_engine.py
│      ├─ RSI multi-TF
│      ├─ Bollinger Bands
│      ├─ Harmonic patterns
│      └─ Trend lines
│
├── models/                     # Phase 2 (XGBoost, LightGBM, LSTM)
│   ├─ xgboost_model.py
│   ├─ lgb_model.py
│   └─ lstm_model.py
│
├── backtesting/                # Walk-forward backtesting
│   ├─ walk_forward.py
│   ├─ purging.py              # Temporal leakage prevention
│   └─ embargo.py              # Embargo period between train/test
│
├── repositories/               # Data access
│   └─ signal_repository.py    # Read/write signals
│
├── mlflow_utils.py             # Expériment tracking (MLflow)
├── config/                     # Seuils indicateurs
├── nlp/                        # News sentiment analysis
├── dvc.yaml                    # DVC pipeline (data versioning)
└── requirements.txt
```

### 3.3 Rule Engine — API

```python
from src.ml.rules.rule_engine import RuleEngine

class RuleEngine:
    """Évalue les indicateurs techniques selon des seuils explicites."""

    def evaluate(
        self,
        symbol: str,
        indicators: dict[str, Any],
        # indicators = {
        #     "rsi_1h": 65.2,
        #     "rsi_2h": 67.1,
        #     "rsi_3h": 68.5,
        #     "rsi_4h": 70.0,
        #     "bb_upper": 44000.0,
        #     "bb_lower": 40000.0,
        #     "bb_middle": 42000.0,
        #     ... autres indicateurs
        # }
    ) -> dict[str, Any]:
        """
        Returns:
        {
            "direction": "BUY" | "SELL" | "HOLD",
            "confidence_score": 0.0-1.0,
            "rules_triggered": ["RSI_3TF_CONVERGENCE", "BB_SQUEEZE", ...],
            "timeframe": "4h"
        }
        """
        ...
```

### 3.4 Signal Generator

```python
from src.ml.signal_generator import SignalGenerator

class SignalGenerator:
    """Orchestre rule engine + optional ML predictor."""

    def __init__(
        self,
        rule_engine: RuleEngine,
        predictor: Predictor | None = None,  # Optional ML phase 2
    ) -> None:
        self._rules = rule_engine
        self._predictor = predictor  # None → rules-only mode

    async def generate(
        self,
        symbol: str,
        indicators: dict[str, Any],
    ) -> TradingSignal | None:
        """
        1. Appelle rule_engine.evaluate()
        2. (Optional) Appelle predictor.predict()
        3. Fusionne confidences (60% ML / 40% rules) si predictor présent
        4. Filtre : confidence >= 0.6
        5. Crée TradingSignal (entry_price, SL, TP, leverage)
        6. Sauvegarde en DB

        Returns:
            TradingSignal if confidence >= 0.6, else None
        """
        ...
```

### 3.5 Walk-Forward Backtesting

```python
from src.ml.backtesting.walk_forward import WalkForwardBacktester

class WalkForwardBacktester:
    """Backtesting temporel sans data leakage."""

    def __init__(
        self,
        historical_data: DataFrame,    # OHLCV + indicators
        train_window: int,              # Ex: 252 jours (1 an)
        test_window: int,               # Ex: 63 jours (1 trimestre)
        embargo_days: int,              # Ex: 5 jours (données de train)
    ) -> None:
        ...

    def run(self) -> BacktestResults:
        """
        Loop temporelle (ne remonte pas le temps):

        for period in walk_forward_windows:
            # 1. train_data = [t0, t0 + train_window)
            # 2. embargo = [t0 + train_window, t0 + train_window + embargo_days)
            # 3. test_data = [t0 + train_window + embargo_days, t1)

            model = train_model(train_data)      # Train sur le passé uniquement
            predictions = model.predict(test_data) # Test sur le futur

            metrics = evaluate_predictions(predictions, test_data)
            results.append(metrics)

        return BacktestResults(
            win_rate=...,
            profit_factor=...,
            max_drawdown=...,
            sharpe_ratio=...,
        )
        """
        ...
```

### 3.6 MLflow Integration

```python
import mlflow

# Tracking experiments
with mlflow.start_run(run_name="xgboost_v2"):
    # Log parameters
    mlflow.log_params({
        "max_depth": 5,
        "learning_rate": 0.05,
        "n_estimators": 100,
    })

    # Train model
    model = XGBRegressor(...)
    model.fit(X_train, y_train)

    # Log metrics
    y_pred = model.predict(X_test)
    mse = mean_squared_error(y_test, y_pred)
    mlflow.log_metric("mse", mse)

    # Save model
    mlflow.sklearn.log_model(model, "xgboost_model")

    # Log artifacts (feature importance, plots)
    mlflow.log_artifact("feature_importance.png")
```

MLflow UI: http://localhost:5000

---

## 4. Architecture Frontend (Streamlit)

### 4.1 Structure Multi-pages

```
src/frontend/
├── app.py                      # Point d'entrée, auth sidebar, theme
├── api_client.py               # Client HTTP centralisé (isolation)
├── config.py                   # Settings frontend (pydantic-settings)
│
├── pages/                      # Pages Streamlit multi-page
│   ├── 1_dashboard.py         # Noah : bougies + indicateurs + signaux
│   ├── 2_news.py              # Sarah : fil de news + sentiment + alertes
│   ├── 3_portfolio.py          # Aleksandar : suivi portefeuille + PnL
│   ├── 4_analytics.py          # Heatmap correlations, performance
│   └── 5_settings.py           # Préférences utilisateur
│
├── components/                 # Composants réutilisables
│   ├── candlestick.py         # Graphique bougie (Plotly)
│   ├── indicators.py           # RSI, Bollinger, trend lines
│   ├── signal_card.py          # Affichage signal
│   ├── news_feed.py            # Fil actualité avec sentiment
│   └── chatbot.py              # Widget chatbot IA
│
├── i18n/                       # Internationalization (FR/EN)
│   ├── __init__.py
│   ├── fr.py                   # Textes français
│   └── en.py                   # Textes anglais
│
├── Dockerfile
└── requirements.txt
```

### 4.2 App.py — Authentification & Sidebar

```python
# src/frontend/app.py

import streamlit as st
from src.frontend.api_client import APIClient

# Page config (DOIT être le premier appel Streamlit)
st.set_page_config(
    page_title="Crypto Bot",
    page_icon=":material/candlestick_chart:",
    layout="wide",
)

# Thème adaptatif (CSS light/dark)
_THEME_CSS = """..."""
st.markdown(f"<style>{_THEME_CSS}</style>", unsafe_allow_html=True)

# ============================================================================
# Sidebar — Auth
# ============================================================================
with st.sidebar:
    st.title("Crypto Bot")

    if "token" not in st.session_state:
        st.session_state.token = None

    if st.session_state.token is None:
        # Not logged in
        tab1, tab2 = st.tabs(["Login", "Register"])

        with tab1:
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            if st.button("Login"):
                api = APIClient()
                response = api.post("/auth/login", {"email": email, "password": password})
                if response and response.get("data"):
                    st.session_state.token = response["data"]["access_token"]
                    st.success("Logged in!")
                    st.rerun()
                else:
                    st.error("Invalid credentials")

        with tab2:
            username = st.text_input("Username")
            email = st.text_input("Email")
            password = st.text_input("Password", type="password", key="reg_pwd")
            persona = st.selectbox("Persona", ["trader", "journalist", "investor"])
            if st.button("Register"):
                api = APIClient()
                response = api.post("/auth/register", {
                    "username": username,
                    "email": email,
                    "password": password,
                    "persona_type": persona,
                })
                if response and response.get("data"):
                    st.success("Account created! Please log in.")
                else:
                    st.error("Registration failed")
    else:
        # Logged in
        st.write(f"Logged in as: {st.session_state.get('username', 'User')}")
        if st.button("Logout"):
            st.session_state.token = None
            st.session_state.username = None
            st.rerun()
```

### 4.3 API Client — Isolation & Caching

```python
# src/frontend/api_client.py

import httpx
import streamlit as st

class APIClient:
    """HTTP client centralisé : JWT auth, error handling, timeouts."""

    def __init__(self) -> None:
        self._base_url = st.secrets.get("API_URL", "http://api:8000")
        self._client = httpx.Client(base_url=self._base_url, timeout=10)

    def _headers(self) -> dict[str, str]:
        """Ajoute JWT token au header."""
        token = st.session_state.get("token")
        if token:
            return {"Authorization": f"Bearer {token}"}
        return {}

    def get(self, path: str, params: dict | None = None) -> dict | None:
        """GET avec error handling."""
        try:
            response = self._client.get(path, params=params, headers=self._headers())
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            st.error(f"API Error: {e}")
            return None

    def post(self, path: str, json: dict | None = None) -> dict | None:
        """POST avec error handling."""
        try:
            response = self._client.post(path, json=json, headers=self._headers())
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            st.error(f"API Error: {e}")
            return None

    # put(), delete() similaires...
```

### 4.4 Caching & Performance

```python
# src/frontend/pages/1_dashboard.py

import streamlit as st
from src.frontend.api_client import APIClient

api = APIClient()

# Cache API responses (5 minutes TTL)
@st.cache_data(ttl=300)
def fetch_crypto_list():
    """Récupère la liste des cryptos une fois tous les 5 min."""
    response = api.get("/crypto/list")
    return response.get("data", []) if response else []

@st.cache_data(ttl=300)
def fetch_prices(symbol: str, timeframe: str):
    """Cache prices par symbol + timeframe."""
    response = api.get(f"/crypto/{symbol}/prices", {"timeframe": timeframe})
    return response.get("data", []) if response else []

@st.cache_data(ttl=300)
def fetch_active_signals():
    """Cache signaux actifs (24h)."""
    response = api.get("/signals/active")
    return response.get("data", []) if response else []

# Utilisation
symbols = fetch_crypto_list()
symbol = st.selectbox("Select crypto", symbols)

timeframe = st.radio("Timeframe", ["1h", "4h", "1d"])
prices = fetch_prices(symbol, timeframe)

# Plotly chart
import plotly.graph_objects as go
fig = go.Figure(data=go.Candlestick(
    x=[p["timestamp"] for p in prices],
    open=[p["open"] for p in prices],
    high=[p["high"] for p in prices],
    low=[p["low"] for p in prices],
    close=[p["close"] for p in prices],
))
st.plotly_chart(fig, use_container_width=True)
```

### 4.5 I18n (Français/Anglais)

```python
# src/frontend/i18n/__init__.py

from src.frontend.config import frontend_settings
from src.frontend.i18n import fr, en

_TRANSLATIONS = {
    "fr": fr.TRANSLATIONS,
    "en": en.TRANSLATIONS,
}

def t(key: str, lang: str | None = None) -> str:
    """Récupère texte traduit."""
    lang = lang or frontend_settings.language  # Depuis .env ou session
    translations = _TRANSLATIONS.get(lang, en.TRANSLATIONS)
    keys = key.split(".")
    result = translations
    for k in keys:
        result = result.get(k, key)
    return result if isinstance(result, str) else key

# Usage
st.title(t("dashboard.title"))  # "Crypto Bot Dashboard" ou "Tableau de bord Crypto Bot"
```

---

## 5. Architecture ETL (Collecte de données)

### 5.1 Flux ETL

```
Collectors        Transformers      Loaders
─────────────────────────────────────────────

OHLCV Binance ──→ Validation ──→ TimescaleDB
                  Enrichissem.    (hypertable)

CoinGecko Market ─→ Validation ──→ TimescaleDB
Data                Format         (market_data)

News RSS ──────→ Parse + Fetch ──→ TimescaleDB
             NLP (sentim.)        (news)

Alternative.me ──→ Transform ──→ TimescaleDB
Fear & Greed     Aggreg.         (sentiment)

           ↓ ETL Jobs (APScheduler)

Indicators ──→ Compute (RSI, ──→ TimescaleDB
            Bollinger, etc)   (indicators)

Signals ──→ Rule Engine ────→ TimescaleDB
        → Optional ML          (signals)
        → Scoring
```

### 5.2 APScheduler Jobs

```python
# src/etl/main.py et src/etl/jobs.py

scheduler = AsyncIOScheduler()

# Priority 13 symbols — 1 min
scheduler.add_job(
    job_collect_ohlcv_priority,
    "interval",
    minutes=1,
    id="collect_ohlcv_priority",
    max_instances=1,  # Evite chevauchement
)

# All 30 symbols — 5 min
scheduler.add_job(
    job_collect_ohlcv_all,
    "interval",
    minutes=5,
    id="collect_ohlcv_all",
)

# Market data (CoinGecko) — 5 min
scheduler.add_job(
    job_collect_market_data,
    "interval",
    minutes=5,
    id="collect_market_data",
)

# News — 15 min
scheduler.add_job(
    job_collect_news,
    "interval",
    minutes=15,
    id="collect_news",
)

# Fear & Greed — 60 min
scheduler.add_job(
    job_collect_fear_greed,
    "interval",
    hours=1,
    id="collect_fear_greed",
)

# Indicateurs techniques — 5 min
scheduler.add_job(
    job_compute_indicators,
    "interval",
    minutes=5,
    id="compute_indicators",
)

# Génération de signaux — intégré dans compute_indicators
# (rule engine + optional ML)

# Réconciliation (détect. gaps) — 60 min
scheduler.add_job(
    job_reconciliation,
    "interval",
    hours=1,
    id="reconciliation",
)

# Évaluation signaux passés (P&L) — 60 min
scheduler.add_job(
    job_evaluate_signal_outcomes,
    "interval",
    hours=1,
    id="evaluate_signal_outcomes",
)

# Export datasets (Parquet → MinIO) — quotidien 03:00 UTC
scheduler.add_job(
    job_export_datasets,
    "cron",
    hour=3,
    minute=0,
    id="export_datasets",
)
```

### 5.3 Idempotence

Tous les jobs doivent être **idempotents** (safe to re-run) :

```python
async def job_collect_ohlcv_priority() -> None:
    """Collecte OHLCV pour les 13 symbols prioritaires."""
    # ✅ GOOD: Upsert (INSERT ... ON CONFLICT UPDATE)
    await timescaledb.upsert_ohlcv(symbol, timeframe, candles)
    # Pas de problème si job re-run 5 minutes plus tard

    # ❌ BAD: INSERT simple
    # await timescaledb.insert_ohlcv(...)
    # Risque de duplicatas en cas de re-run
```

Contrainte unique en DB :
```sql
CREATE UNIQUE INDEX idx_crypto_prices_unique
ON crypto_prices (symbol, timeframe, "timestamp");
```

---

## 6. Modèles de Données Partagés

### 6.1 Modèles Pydantic (src/shared/models/)

```python
# src/shared/models/signal.py
from pydantic import BaseModel, Field
from datetime import datetime
from decimal import Decimal

class TradingSignal(BaseModel):
    """Modèle signal émis par le ML engine."""

    id: str
    symbol: str = Field(..., min_length=2, max_length=20)
    timeframe: str = Field(..., pattern=r"^(1m|5m|15m|1h|4h|1d|1w)$")
    direction: Literal["BUY", "SELL", "HOLD"]
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    entry_price: Decimal = Field(..., gt=0)
    stop_loss: Decimal = Field(..., gt=0)
    take_profit: list[Decimal] = Field(default_factory=list)
    leverage_suggested: int = Field(default=1, ge=1, le=2)
    rules_triggered: list[str] = Field(default_factory=list)
    indicators_used: list[str] = Field(default_factory=list)
    model_version: str = "rules_v1"  # ou "xgboost_v2", "lgb_v1", etc
    timestamp: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

### 6.2 ORM Models (src/shared/db_models.py)

```python
from sqlalchemy import Column, String, Numeric, Text, DateTime, Integer
from sqlalchemy.dialects.postgresql import JSONB, UUID

class TradingSignalOrm(Base):
    """Table trading_signals."""

    __tablename__ = "trading_signals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol = Column(String(20), nullable=False, index=True)
    timeframe = Column(String(10), nullable=False)
    direction = Column(String(10), nullable=False)  # BUY, SELL, HOLD
    confidence_score = Column(Numeric(3, 2), nullable=False)
    entry_price = Column(Numeric(20, 8), nullable=False)
    stop_loss = Column(Numeric(20, 8), nullable=False)
    take_profit = Column(JSONB, nullable=False, server_default="[]")
    leverage_suggested = Column(Integer, default=1)
    rules_triggered = Column(JSONB, nullable=False, server_default="[]")
    indicators_used = Column(JSONB, nullable=False, server_default="[]")
    model_version = Column(String(50), default="rules_v1")
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default="NOW()",
    )

    __table_args__ = (
        Index("idx_signals_symbol_timestamp", "symbol", "timestamp", postgresql_using="btree"),
    )
```

---

## 7. Hiérarchie d'Exceptions

```python
# src/shared/exceptions.py

class CryptoBotError(Exception):
    """Base exception — HTTP status_code en attribut."""
    status_code: int = 500

class NotFoundError(CryptoBotError):
    status_code: int = 404  # Resource not found

class ValidationError(CryptoBotError):
    status_code: int = 422  # Invalid input

class AuthenticationError(CryptoBotError):
    status_code: int = 401  # JWT invalid/expired

class AuthorizationError(CryptoBotError):
    status_code: int = 403  # User lacks permission

class ExternalAPIError(CryptoBotError):
    status_code: int = 502  # Upstream API failed

class RateLimitError(ExternalAPIError):
    status_code: int = 429  # Rate limit exceeded

# ETL-specific
class CollectorError(CryptoBotError):
    """Unrecoverable collector error."""

class DataSourceUnavailable(CollectorError):
    """External source down."""

class LoaderError(CryptoBotError):
    """Data insert into DB failed."""

class TransformError(CryptoBotError):
    """Indicator computation failed."""

class ConflictError(CryptoBotError):
    status_code: int = 409  # Resource already exists
```

Usage dans routes :
```python
@router.get("/crypto/{symbol}/prices")
async def get_prices(symbol: str, db: AsyncSession = Depends(get_db)):
    if not symbol:
        raise ValidationError("Symbol cannot be empty", detail={"field": "symbol"})

    result = await db.execute(select(CryptoPriceOrm).where(...).limit(100))
    prices = result.scalars().all()

    if not prices:
        raise NotFoundError(f"No prices found for {symbol}")

    return ApiResponse(data=prices)
```

---

## 8. Patterns & Principes d'Architecture

### 8.1 Repository Pattern

Abstrait l'accès aux données :

```python
class CryptoPriceRepository:
    """Data access layer pour les prix."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_latest(self, symbol: str, timeframe: str, limit: int = 100):
        """Récupère les N dernières bougies."""
        result = await self._db.execute(
            select(CryptoPriceOrm)
            .where(
                (CryptoPriceOrm.symbol == symbol) &
                (CryptoPriceOrm.timeframe == timeframe)
            )
            .order_by(CryptoPriceOrm.timestamp.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def upsert(self, candles: list[CandleData]) -> None:
        """Insert ou update les bougies (idempotent)."""
        for candle in candles:
            stmt = insert(CryptoPriceOrm).values(
                symbol=candle.symbol,
                timeframe=candle.timeframe,
                timestamp=candle.timestamp,
                open=candle.open,
                high=candle.high,
                low=candle.low,
                close=candle.close,
                volume=candle.volume,
            ).on_conflict_do_update(
                index_elements=["symbol", "timeframe", "timestamp"],
                set_={
                    "open": candle.open,
                    "high": candle.high,
                    "low": candle.low,
                    "close": candle.close,
                    "volume": candle.volume,
                }
            )
            await self._db.execute(stmt)
        await self._db.commit()
```

Service l'utilise :
```python
class CryptoService:
    def __init__(self, repo: CryptoPriceRepository) -> None:
        self._repo = repo

    async def get_prices(self, symbol: str, timeframe: str, limit: int = 100):
        return await self._repo.get_latest(symbol, timeframe, limit)
```

### 8.2 Service Pattern

Logique métier séparée de l'API :

```python
class SignalService:
    """Business logic pour les signaux."""

    def __init__(self, signal_repo: SignalRepository) -> None:
        self._repo = signal_repo

    async def get_active_signals(self, db: AsyncSession, hours: int = 24):
        """Retourne les signaux des dernières N heures."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        return await self._repo.find_by_date_range(cutoff, datetime.utcnow())

    async def get_performance_stats(self, db: AsyncSession) -> dict:
        """Calcule win rate, profit factor, max drawdown."""
        signals = await self._repo.get_all_with_outcomes(db)

        wins = len([s for s in signals if s.outcome_pnl and s.outcome_pnl > 0])
        total = len(signals)
        win_rate = wins / total if total > 0 else 0

        gross_profit = sum([s.outcome_pnl for s in signals if s.outcome_pnl > 0])
        gross_loss = abs(sum([s.outcome_pnl for s in signals if s.outcome_pnl < 0]))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

        return {
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "total_signals": total,
        }
```

Router l'utilise :
```python
@signals_router.get("/signals/active")
async def get_active_signals(
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[list[SignalResponse]]:
    signals = await signal_service.get_active_signals(db)
    return ApiResponse(
        data=[SignalResponse.model_validate(s) for s in signals]
    )
```

### 8.3 Async/Await Partout

```python
# ✅ GOOD: Async I/O
async def fetch_binance_prices(symbol: str) -> list[dict]:
    """Appel async à Binance REST API."""
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://api.binance.com/api/v3/klines?symbol={symbol}") as resp:
            return await resp.json()

# ❌ BAD: Blocking requests library
def fetch_binance_prices_sync(symbol: str):
    import requests
    return requests.get(f"https://api.binance.com/api/v3/klines?symbol={symbol}").json()

# Usage en route FastAPI
@router.get("/crypto/{symbol}/binance")
async def get_binance_prices(symbol: str):
    prices = await fetch_binance_prices(symbol)  # Non-blocking
    return ApiResponse(data=prices)
```

### 8.4 Configuration Centralisée

```python
# src/shared/config.py
from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    """Centralized config — lit .env, valide avec Pydantic."""

    # Database
    database_url: str = "postgresql+asyncpg://user:pass@timescaledb:5432/cryptobot"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_secret_key: str  # NEVER hardcode — doit être dans .env

    # CORS
    cors_origins: list[str] = ["http://localhost:8501", "http://frontend:8501"]

    # ML
    signal_confidence_threshold: float = 0.6

    # Log level
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

settings = Settings()  # Singleton, valide au démarrage
```

Usage partout :
```python
from src.shared.config import settings

# Dans main.py
app = FastAPI(
    title="CryptoBot API",
    version="1.0.0",
)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, ...)

# Dans route
@router.post("/signals")
async def create_signal(signal: TradingSignal):
    if signal.confidence_score < settings.signal_confidence_threshold:
        raise ValidationError("Confidence too low")
    ...
```

---

## 9. Communication Inter-équipes

### 9.1 Interfaces HTTP (APIs)

Équipes communiquent VIA HTTP REST seulement :

```
Frontend (Streamlit)
    ↓ HTTP
    ├─ GET /api/v1/crypto/...
    ├─ POST /api/v1/auth/...
    ├─ GET /api/v1/signals/...
    └─ etc
    ↓ HTTP
Backend (FastAPI)
    ↓ SQL
    ├─ TimescaleDB
    └─ MinIO (via ML)
```

**Jamais d'imports croisés entre équipes** :
- ❌ `from src.ml.rules import RuleEngine` (dans src/api/)
- ❌ `from src.api.services import AuthService` (dans src/frontend/)
- ❌ `from src.frontend.components import Candlestick` (dans src/api/)

### 9.2 Contrats Pydantic

Tous les échanges sont typés via Pydantic :

```python
# Request
class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    persona_type: Literal["trader", "journalist", "investor"]

# Response
class RegisterResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

# Enveloppe
class ApiResponse(BaseModel, Generic[T]):
    data: T | None = None
    error: ErrorDetail | None = None
    meta: PaginationMeta | None = None
```

Frontend reçoit JSON typé :
```python
response = api.post("/auth/register", {...})
# response est dict avec "data", "error", "meta"
# Frontend parse via Pydantic si besoin
```

### 9.3 Coordination Async

ETL écrit signaux → API les lit → Frontend les affiche :

```
ETL (job_compute_indicators)
    ↓
signal_generator.generate(symbol, indicators)
    ↓
Sauvegarde TradingSignalOrm en DB (INSERT)
    ↓
API (signal_service.get_active_signals)
    ↓
SELECT * FROM trading_signals WHERE timestamp > now() - interval '24 hours'
    ↓
Frontend (@st.cache_data fetch_active_signals)
    ↓
Affiche signaux dans le dashboard
```

Tous les trois modules sont **découplés** :
- ETL ne connaît pas l'API
- API ne connaît pas le frontend
- Frontend ne connaît que l'API

---

## 10. Tableau Récapitulatif

| Aspect | Technologie | Justification |
|--------|-------------|---------------|
| **Langage principal** | Python 3.11+ | Moderne, async/await natif, ML libraries |
| **Web framework** | FastAPI | Performance, async, OpenAPI auto, dépendances |
| **Frontend** | Streamlit | Dev rapide, Plotly natif, pas de JS |
| **Base de données** | TimescaleDB | Séries temporelles (hypertables), compression |
| **Cache/Object storage** | MinIO (S3 compat) | Datasets, modèles, artifacts MLflow |
| **ML Tracking** | MLflow | Expériments, versioning, artifact store |
| **Data Versioning** | DVC | Datasets, reproducibilité |
| **Task Scheduling** | APScheduler | Async-native, pas de broker externe |
| **Reverse proxy** | Nginx | Rate limiting, HTTPS, static caching |
| **Containerization** | Docker Compose | Orchestration simple, dev→prod |
| **CI/CD** | GitHub Actions | Natif GitHub, secrets management |
| **HTTP Client** | httpx + aiohttp | Async, timeout, retry logic |
| **Type checking** | mypy --strict | Garantit type safety |
| **Code quality** | ruff (lint + format) | Remplace flake8, black, isort |
| **Testing** | pytest + pytest-asyncio | Async tests, mocking (respx) |

---

## 11. Dépendances Graph (Dépend de / Dépendance)

```
Frontend (Streamlit)
    └─ dépend de: API (HTTP REST)
       └─ dépend de: TimescaleDB (SQL async)
       └─ dépend de: Shared Models (Pydantic)
       └─ dépend de: Exceptions (hierarchy)
       └─ dépend de: Config (Settings)

ML Engine
    └─ dépend de: TimescaleDB (read OHLCV)
    └─ dépend de: Shared Models (Signal)
    └─ dépend de: Config (thresholds)
    └─ écrit dans: TimescaleDB (trading_signals)

ETL Pipeline
    └─ dépend de: External APIs (Binance, CoinGecko, RSS)
    └─ dépend de: TimescaleDB (write OHLCV, news, fear_greed)
    └─ dépend de: MinIO (export datasets)
    └─ dépend de: ML Engine (signal generation)
    └─ dépend de: Shared Models (validation)
    └─ dépend de: Config (API keys)

API Backend
    └─ dépend de: TimescaleDB (read/write)
    └─ dépend de: Shared Models (request/response)
    └─ dépend de: Exceptions (error handling)
    └─ dépend de: Config (JWT secret, CORS)
```

**Invariants** :
- Pas de cycle : Frontend → API → DB → ML (pas de retour)
- Pas d'imports croisés : ML n'importe pas API, Frontend n'importe pas ETL
- Seul couplage accepté : via HTTP REST ou Pydantic shared models

---

## 12. Checklist d'Architecture

- [ ] FastAPI app avec CORS, exception handlers, Prometheus
- [ ] Dependency injection : get_db, get_current_user
- [ ] Response envelope (ApiResponse) sur tous les endpoints
- [ ] 8 routers : auth, crypto, signals, news, portfolio, watchlist, chat, system
- [ ] Service layer pour chaque domaine (CryptoService, SignalService, etc)
- [ ] Repository pattern pour accès aux données
- [ ] Pydantic models pour toutes les requêtes/réponses
- [ ] Hiérarchie d'exceptions structurée
- [ ] Configuration centralisée (pydantic-settings)
- [ ] Async/await pour I/O (SQLAlchemy async, httpx)
- [ ] APScheduler avec jobs idempotents
- [ ] Rule Engine + optional ML Predictor
- [ ] SignalGenerator avec filtering (confidence >= 0.6)
- [ ] Walk-forward backtesting avec purging + embargo
- [ ] MLflow pour experiment tracking
- [ ] Streamlit multi-page app
- [ ] APIClient centralisé (isolation)
- [ ] Caching avec @st.cache_data (TTL)
- [ ] i18n (FR/EN)
- [ ] Health checks sur tous les services
- [ ] Logs structurés (logging module)
- [ ] Tests (unit, integration, E2E) ≥ 80% coverage

---

*Spécification d'Architecture Applicative — Crypto Bot V1*
*Auteur : Winston, System Architect*
*Date : 2026-03-12*
