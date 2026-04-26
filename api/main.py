import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import health, ohlcv, market, signals, news, ml
from api.dependencies import engine
from src.models.news import Base as NewsBase

# Create news_articles table if it doesn't exist yet (idempotent)
NewsBase.metadata.create_all(bind=engine)

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


@app.get("/")
def root():
    return {
        "name": "Crypto Bot API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": ["/health", "/ohlcv", "/market", "/signals", "/news", "/ml"],
    }
