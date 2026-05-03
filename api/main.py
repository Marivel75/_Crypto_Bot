import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy import text

from api.routers import health, ohlcv, market, signals, news, ml, alerts
from api.dependencies import engine
from src.models.news import Base as NewsBase
from src.models.alert_subscriber import Base as AlertBase

# Create tables if they don't exist yet (idempotent)
NewsBase.metadata.create_all(bind=engine)
AlertBase.metadata.create_all(bind=engine)

# Migration légère : ajoute les colonnes entities et topics si absentes (SQLite)
_NEW_COLUMNS = [
    ("entities", "JSON"),
    ("topics",   "JSON"),
]
with engine.connect() as _conn:
    for _col, _type in _NEW_COLUMNS:
        try:
            _conn.execute(text(f"ALTER TABLE news_articles ADD COLUMN {_col} {_type}"))
            _conn.commit()
        except Exception:
            pass  # colonne déjà présente

app = FastAPI(
    title="Crypto Bot API",
    description="API de données crypto : OHLCV, market data, indicateurs techniques",
    version="1.0.0",
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


@app.get("/")
def root():
    return {
        "name": "Crypto Bot API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": ["/health", "/ohlcv", "/market", "/signals", "/news", "/ml", "/alerts"],
    }
