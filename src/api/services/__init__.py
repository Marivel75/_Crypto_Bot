"""API services — business logic layer re-exports."""

from src.api.services.auth_service import (
    authenticate_user,
    create_access_token,
    decode_access_token,
    get_user_by_id,
    register_user,
)
from src.api.services.chat_service import chat
from src.api.services.crypto_service import (
    get_indicators,
    get_latest,
    get_market_overview,
    get_prices,
    list_tracked,
)
from src.api.services.news_service import get_by_id, get_sentiment
from src.api.services.news_service import get_latest as get_news_latest
from src.api.services.signal_service import get_active, get_by_symbol, get_detail, get_performance
from src.api.services.user_data_service import (
    add_portfolio_entry,
    add_watchlist_symbol,
    delete_portfolio_entry,
    get_portfolio,
    get_watchlist,
    remove_watchlist_symbol,
    update_portfolio_entry,
)

__all__ = [
    # auth
    "authenticate_user",
    "create_access_token",
    "decode_access_token",
    "get_user_by_id",
    "register_user",
    # chat
    "chat",
    # crypto
    "get_indicators",
    "get_latest",
    "get_market_overview",
    "get_prices",
    "list_tracked",
    # news
    "get_by_id",
    "get_news_latest",
    "get_sentiment",
    # signals
    "get_active",
    "get_by_symbol",
    "get_detail",
    "get_performance",
    # user data
    "add_portfolio_entry",
    "add_watchlist_symbol",
    "delete_portfolio_entry",
    "get_portfolio",
    "get_watchlist",
    "remove_watchlist_symbol",
    "update_portfolio_entry",
]
