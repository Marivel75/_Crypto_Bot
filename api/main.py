import sys
from pathlib import Path
from contextlib import asynccontextmanager

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text

from api.routers import health, ohlcv, market, signals, news, ml, alerts, paper_trading
from api.dependencies import engine
from src.models.ohlcv import Base as OHLCVBase
from src.models.ticker import Base as TickerBase
from src.models.market_data_base import MarketDataBase
from src.models.news import Base as NewsBase
from src.models.alert_subscriber import Base as AlertBase
from src.models.paper_trade import Base as PaperTradeBase
from config.settings import config

# Create all tables if they don't exist yet (idempotent — works on SQLite and PostgreSQL)
OHLCVBase.metadata.create_all(bind=engine)
TickerBase.metadata.create_all(bind=engine)
MarketDataBase.metadata.create_all(bind=engine)
NewsBase.metadata.create_all(bind=engine)
AlertBase.metadata.create_all(bind=engine)
PaperTradeBase.metadata.create_all(bind=engine)

# Lightweight migration: add entities and topics columns if missing.
# Uses inspect() to check existing columns — works on SQLite and PostgreSQL.
_NEW_COLUMNS = [
    ("entities", "JSON"),
    ("topics",   "JSON"),
]
_existing_cols = {col["name"] for col in inspect(engine).get_columns("news_articles")}
with engine.connect() as _conn:
    for _col, _type in _NEW_COLUMNS:
        if _col not in _existing_cols:
            _conn.execute(text(f"ALTER TABLE news_articles ADD COLUMN {_col} {_type}"))
    _conn.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Démarrage du collecteur de prix WebSocket (thread daemon)
    from src.collectors.ws_price_collector import start_ws_collector
    pairs = config.get("pairs", [])
    if pairs:
        start_ws_collector(pairs)
    yield
    # Arrêt : le thread est daemon, il se termine avec le process


app = FastAPI(
    title="Crypto Bot API",
    description="API de données crypto : OHLCV, market data, indicateurs techniques",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(ohlcv.router)
app.include_router(market.router)
app.include_router(signals.router)
app.include_router(news.router)
app.include_router(ml.router)
app.include_router(alerts.router)
app.include_router(paper_trading.router)


@app.get("/")
def root():
    return {
        "name": "Crypto Bot API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": ["/health", "/ohlcv", "/market", "/signals", "/news", "/ml", "/alerts", "/paper-trading"],
    }
