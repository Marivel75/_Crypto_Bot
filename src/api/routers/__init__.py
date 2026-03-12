"""Router package — exposes all FastAPI routers."""

from src.api.routers import auth, chat, crypto, news, portfolio, signals, system, watchlist

__all__ = ["auth", "chat", "crypto", "news", "portfolio", "signals", "system", "watchlist"]
