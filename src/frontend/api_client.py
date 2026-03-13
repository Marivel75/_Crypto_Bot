"""Centralized HTTP client for calling the backend API.

Every page uses this client. All errors are caught and surfaced
via ``st.error`` — the UI never crashes on API failures.
"""

from __future__ import annotations

import logging
from typing import Any, TypeVar

import httpx
import streamlit as st
from pydantic import BaseModel, TypeAdapter

from src.api.schemas import (
    ChatResponse,
    CryptoListItem,
    HealthResponse,
    IndicatorResponse,
    LoginResponse,
    MarketOverviewResponse,
    NewsResponse,
    NewsSentimentResponse,
    OHLCVResponse,
    PortfolioEntryResponse,
    SignalDetailResponse,
    SignalResponse,
    UserResponse,
    WatchlistEntryResponse,
)
from src.frontend.config import frontend_settings
from src.frontend.i18n import t

logger = logging.getLogger(__name__)

_TIMEOUT = httpx.Timeout(
    frontend_settings.api_timeout,
    connect=frontend_settings.api_connect_timeout,
)

T = TypeVar("T", bound=BaseModel)


class APIClient:
    """Type-safe HTTP client with Pydantic-based response deserialization.

    All responses are validated against Pydantic models before returning.
    """

    def __init__(self) -> None:
        self._base_url = frontend_settings.api_url
        self._client = httpx.Client(base_url=self._base_url, timeout=_TIMEOUT)

    # ------------------------------------------------------------------
    # Core HTTP verbs
    # ------------------------------------------------------------------

    def _headers(self) -> dict[str, str]:
        token: str | None = st.session_state.get("token")
        if token:
            return {"Authorization": f"Bearer {token}"}
        return {}

    def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any] | None:
        """Perform a GET request and return the parsed JSON body."""
        return self._request("GET", path, params=params)

    def post(self, path: str, json: dict[str, Any] | None = None) -> dict[str, Any] | None:
        """Perform a POST request and return the parsed JSON body."""
        return self._request("POST", path, json=json)

    def put(self, path: str, json: dict[str, Any] | None = None) -> dict[str, Any] | None:
        """Perform a PUT request and return the parsed JSON body."""
        return self._request("PUT", path, json=json)

    def delete(self, path: str) -> dict[str, Any] | None:
        """Perform a DELETE request and return the parsed JSON body."""
        return self._request("DELETE", path)

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """Execute HTTP request with error handling.

        Returns the parsed JSON response (as dict), or None on error.
        """
        try:
            response = self._client.request(
                method,
                path,
                params=params,
                json=json,
                headers=self._headers(),
            )
            response.raise_for_status()
            try:
                return response.json()
            except ValueError:
                logger.error("Invalid JSON response from %s %s", method, path)
                st.error(t("api.invalid_response"))
                return None
        except httpx.RequestError as exc:
            logger.warning("API request error: %s %s — %s", method, path, exc)
            st.error(t("api.unavailable"))
            return None
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if status == 401:
                st.warning(t("api.session_expired"))
                st.session_state.pop("token", None)
            else:
                logger.error("HTTP %d sur %s %s", status, method, path)
                st.error(t("api.http_error", status=status))
            return None

    def _decode_response(self, response_dict: dict[str, Any] | None, model: type[T]) -> T | None:
        """Decode a raw response dict into a Pydantic model.

        Parameters
        ----------
        response_dict : dict | None
            Raw JSON response from API (from _request()).
        model : type[T]
            Target Pydantic model class (e.g., LoginResponse, OHLCVResponse).

        Returns
        -------
        T | None
            Deserialized and validated model instance, or None if response_dict is None.

        Raises
        ------
        ValueError
            If response_dict doesn't match the model schema (logged but not raised to caller).
        """
        if response_dict is None:
            return None
        try:
            adapter = TypeAdapter(model)
            return adapter.validate_python(response_dict)
        except Exception as exc:
            logger.error("Failed to decode response as %s: %s", model.__name__, exc)
            st.error(t("api.invalid_response"))
            return None

    def _extract_data(self, response_dict: dict[str, Any] | None, model: type[T]) -> T | None:
        """Extract and validate the 'data' field from an ApiResponse.

        This is the common pattern: unwrap ApiResponse[T] → T | None.

        Parameters
        ----------
        response_dict : dict | None
            Raw ApiResponse envelope.
        model : type[T]
            Type of the data field (e.g., LoginResponse).

        Returns
        -------
        T | None
            The validated data, or None if response_dict is None or data field is None.
        """
        if response_dict is None:
            return None
        data_dict = response_dict.get("data")
        if data_dict is None:
            return None
        return self._decode_response(data_dict, model)

    def _extract_list(self, response_dict: dict[str, Any] | None, item_model: type[T]) -> list[T] | None:
        """Extract and validate a list from the 'data' field of an ApiResponse.

        Parameters
        ----------
        response_dict : dict | None
            Raw ApiResponse envelope.
        item_model : type[T]
            Type of items in the list.

        Returns
        -------
        list[T] | None
            List of validated items, or None if response_dict is None.
        """
        if response_dict is None:
            return None
        data_list = response_dict.get("data", [])
        if not isinstance(data_list, list):
            logger.error("Expected list in response.data, got %s", type(data_list))
            return None
        try:
            adapter = TypeAdapter(list[item_model])
            return adapter.validate_python(data_list)
        except Exception as exc:
            logger.error("Failed to decode list of %s: %s", item_model.__name__, exc)
            st.error(t("api.invalid_response"))
            return None

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    def login(self, email: str, password: str) -> str | None:
        """Authenticate with email/password and return JWT token, or None on failure."""
        resp = self.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        login_resp = self._extract_data(resp, LoginResponse)
        return login_resp.access_token if login_resp else None

    def register(
        self,
        username: str,
        email: str,
        password: str,
        persona_type: str = "trader",
    ) -> UserResponse | None:
        """Register a new user. Returns the validated UserResponse or None on failure."""
        resp = self.post(
            "/api/v1/auth/register",
            json={
                "username": username,
                "email": email,
                "password": password,
                "persona_type": persona_type,
            },
        )
        return self._extract_data(resp, UserResponse)

    def get_me(self) -> UserResponse | None:
        """Return current user info or None."""
        resp = self.get("/api/v1/auth/me")
        return self._extract_data(resp, UserResponse)

    # ------------------------------------------------------------------
    # Crypto
    # ------------------------------------------------------------------

    def fetch_crypto_list(self) -> list[CryptoListItem] | None:
        """Return the list of tracked crypto symbols and names."""
        resp = self.get("/api/v1/crypto/list")
        return self._extract_list(resp, CryptoListItem)

    def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int = 200) -> list[OHLCVResponse] | None:
        """Return OHLCV records for a symbol/timeframe pair."""
        resp = self.get(
            f"/api/v1/crypto/{symbol}/prices",
            params={"timeframe": timeframe, "limit": limit},
        )
        return self._extract_list(resp, OHLCVResponse)

    def fetch_indicators(self, symbol: str, timeframe: str) -> list[IndicatorResponse] | None:
        """Return indicator records (rsi, bollinger_*, trend_*) for a symbol/timeframe."""
        resp = self.get(
            f"/api/v1/crypto/{symbol}/indicators",
            params={"timeframe": timeframe},
        )
        return self._extract_list(resp, IndicatorResponse)

    def fetch_latest(self, symbol: str) -> dict[str, Any] | None:
        """Return the latest OHLCV + indicators snapshot for a symbol.

        Note: Returns dict instead of typed model because response structure varies.
        """
        resp = self.get(f"/api/v1/crypto/{symbol}/latest")
        if resp is None:
            return None
        return resp.get("data")

    def fetch_market_overview(self) -> MarketOverviewResponse | None:
        """Return market overview (total_symbols, top_gainers, top_losers)."""
        resp = self.get("/api/v1/crypto/market-overview")
        return self._extract_data(resp, MarketOverviewResponse)

    # ------------------------------------------------------------------
    # Signals
    # ------------------------------------------------------------------

    def fetch_active_signals(self) -> list[SignalResponse] | None:
        """Return all currently active signals."""
        resp = self.get("/api/v1/signals/active")
        return self._extract_list(resp, SignalResponse)

    def fetch_signals(self, symbol: str | None = None) -> list[SignalResponse] | None:
        """Return signals, optionally filtered by symbol."""
        path = f"/api/v1/signals/{symbol}" if symbol else "/api/v1/signals/active"
        resp = self.get(path)
        return self._extract_list(resp, SignalResponse)

    def fetch_signal_detail(self, signal_id: str | int) -> SignalDetailResponse | None:
        """Return detailed info for a single signal."""
        resp = self.get(f"/api/v1/signals/{signal_id}/detail")
        return self._extract_data(resp, SignalDetailResponse)

    def fetch_signal_performance(self) -> dict[str, Any] | None:
        """Return signal performance stats dict (win_rate, total_signals, etc.)."""
        resp = self.get("/api/v1/signals/performance")
        if resp is None:
            return None
        return resp.get("data")

    # ------------------------------------------------------------------
    # News
    # ------------------------------------------------------------------

    def fetch_news(
        self,
        source: str | None = None,
        keyword: str | None = None,
        limit: int = 20,
    ) -> list[NewsResponse] | None:
        """Return latest news articles with optional source/keyword filters."""
        params: dict[str, Any] = {"limit": limit}
        if source:
            params["source"] = source
        if keyword:
            params["keyword"] = keyword
        resp = self.get("/api/v1/news/latest", params=params)
        return self._extract_list(resp, NewsResponse)

    def fetch_news_detail(self, news_id: str | int) -> NewsResponse | None:
        """Return detail of a single news article."""
        resp = self.get(f"/api/v1/news/{news_id}")
        return self._extract_data(resp, NewsResponse)

    def fetch_news_sentiment(self) -> list[NewsSentimentResponse] | None:
        """Return aggregated sentiment per symbol."""
        resp = self.get("/api/v1/news/sentiment")
        return self._extract_list(resp, NewsSentimentResponse)

    # ------------------------------------------------------------------
    # Portfolio (JWT required)
    # ------------------------------------------------------------------

    def fetch_portfolio(self) -> list[PortfolioEntryResponse] | None:
        """Return the authenticated user's portfolio positions."""
        resp = self.get("/api/v1/portfolio")
        return self._extract_list(resp, PortfolioEntryResponse)

    def add_portfolio_position(self, position: dict[str, Any]) -> PortfolioEntryResponse | None:
        """Add a new portfolio position. Returns the created position or None."""
        resp = self.post("/api/v1/portfolio", json=position)
        return self._extract_data(resp, PortfolioEntryResponse)

    def update_portfolio_position(self, position_id: str | int, data: dict[str, Any]) -> PortfolioEntryResponse | None:
        """Update an existing portfolio position."""
        resp = self.put(f"/api/v1/portfolio/{position_id}", json=data)
        return self._extract_data(resp, PortfolioEntryResponse)

    def delete_portfolio_position(self, position_id: str | int) -> dict[str, Any] | None:
        """Delete a portfolio position. Returns the response envelope (or None on error)."""
        resp = self.delete(f"/api/v1/portfolio/{position_id}")
        return resp

    # ------------------------------------------------------------------
    # Watchlist (JWT required)
    # ------------------------------------------------------------------

    def fetch_watchlist(self) -> list[WatchlistEntryResponse] | None:
        """Return the authenticated user's watchlist."""
        resp = self.get("/api/v1/watchlist")
        return self._extract_list(resp, WatchlistEntryResponse)

    def add_to_watchlist(self, symbol: str) -> WatchlistEntryResponse | None:
        """Add a symbol to the watchlist."""
        resp = self.post("/api/v1/watchlist", json={"symbol": symbol})
        return self._extract_data(resp, WatchlistEntryResponse)

    def remove_from_watchlist(self, symbol: str) -> dict[str, Any] | None:
        """Remove a symbol from the watchlist. Returns the response envelope."""
        resp = self.delete(f"/api/v1/watchlist/{symbol}")
        return resp

    # ------------------------------------------------------------------
    # Chat (JWT required)
    # ------------------------------------------------------------------

    def chat(self, message: str) -> tuple[str | None, str | None]:
        """Send a chat message and return (reply, disclaimer) tuple."""
        resp = self.post("/api/v1/chat", json={"message": message})
        chat_resp = self._extract_data(resp, ChatResponse)
        if chat_resp is None:
            return None, None
        return chat_resp.reply, chat_resp.disclaimer

    # ------------------------------------------------------------------
    # System
    # ------------------------------------------------------------------

    def health(self) -> HealthResponse | None:
        """Check application health status."""
        resp = self.get("/api/v1/health")  # S11: consistent /api/v1 prefix
        return self._extract_data(resp, HealthResponse)

    def refresh_token(self) -> str | None:
        """Refresh JWT token and return new access token, or None on failure."""
        resp = self.post("/api/v1/auth/refresh")
        if resp is None:
            return None
        login_resp = self._extract_data(resp, LoginResponse)
        if login_resp:
            st.session_state["token"] = login_resp.access_token
            return login_resp.access_token
        return None

    # ------------------------------------------------------------------
    # Portfolio extended endpoints (Semaine 3)
    # ------------------------------------------------------------------

    def fetch_portfolio_summary(self) -> dict[str, Any] | None:
        """Return portfolio summary: total_value, total_cost, pnl_pct, asset_allocation."""
        resp = self.get("/api/v1/portfolio/summary")
        if resp is None:
            return None
        return resp.get("data")

    def fetch_portfolio_history(self, limit: int = 90) -> list[dict[str, Any]] | None:
        """Return portfolio value history over time (daily snapshots)."""
        resp = self.get("/api/v1/portfolio/history", params={"limit": limit})
        return self._extract_list(resp, dict)  # type: ignore

    # ------------------------------------------------------------------
    # Watchlist extended endpoints (Semaine 3)
    # ------------------------------------------------------------------

    def fetch_watchlist_prices(self) -> list[dict[str, Any]] | None:
        """Return watchlist with live prices and 24h change."""
        resp = self.get("/api/v1/watchlist/prices")
        return self._extract_list(resp, dict)  # type: ignore

    # ------------------------------------------------------------------
    # Signals extended endpoints (Semaine 3)
    # ------------------------------------------------------------------

    def fetch_signals_history(
        self,
        symbol: str | None = None,
        direction: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any] | None:
        """Return paginated signal history with filters.

        Returns dict with 'items' (list) and 'total' (int).
        """
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if symbol:
            params["symbol"] = symbol
        if direction:
            params["direction"] = direction
        if date_from:
            params["date_from"] = date_from
        if date_to:
            params["date_to"] = date_to
        resp = self.get("/api/v1/signals/history", params=params)
        if resp is None:
            return None
        return resp.get("data")

    # ------------------------------------------------------------------
    # System endpoints (Semaine 3)
    # ------------------------------------------------------------------

    def fetch_system_metrics(self) -> dict[str, Any] | None:
        """Return system metrics: uptime, request_count, error_rate, db_size."""
        resp = self.get("/api/v1/system/metrics")
        if resp is None:
            return None
        return resp.get("data")

    # ------------------------------------------------------------------
    # Legacy helpers (kept for backward compatibility)
    # ------------------------------------------------------------------

    def fetch_multi_timeframe(self, symbol: str) -> list[dict[str, Any]] | None:
        """Return multi-timeframe indicator data for a symbol (best-effort)."""
        results: list[dict[str, Any]] = []
        for tf in ["1h", "4h", "1D"]:
            indicators = self.fetch_indicators(symbol, tf)
            if indicators:
                for ind in indicators[:1]:
                    ind_dict = ind.model_dump()
                    ind_dict["timeframe"] = tf
                    results.append(ind_dict)
        return results if results else None
