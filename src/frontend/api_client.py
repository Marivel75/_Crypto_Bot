"""Centralized HTTP client for calling the backend API.

Every page uses this client. All errors are caught and surfaced
via ``st.error`` — the UI never crashes on API failures.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx
import streamlit as st

from src.frontend.config import frontend_settings
from src.frontend.i18n import t

logger = logging.getLogger(__name__)

_TIMEOUT = httpx.Timeout(
    frontend_settings.api_timeout,
    connect=frontend_settings.api_connect_timeout,
)


class APIClient:
    """Thin wrapper around ``httpx`` that adds JWT auth and error handling."""

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
                return response.json()  # type: ignore[no-any-return]
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

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    def login(self, email: str, password: str) -> str | None:
        """Authenticate with email/password and return JWT token, or None on failure."""
        resp = self.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        if resp is None:
            return None
        data = resp.get("data", {})
        if isinstance(data, dict):
            return data.get("access_token")  # type: ignore[no-any-return]
        return None

    def register(
        self,
        username: str,
        email: str,
        password: str,
        persona_type: str = "trader",
    ) -> dict[str, Any] | None:
        """Register a new user. Returns the data dict or None on failure."""
        resp = self.post(
            "/api/v1/auth/register",
            json={
                "username": username,
                "email": email,
                "password": password,
                "persona_type": persona_type,
            },
        )
        if resp is None:
            return None
        return resp.get("data")  # type: ignore[no-any-return]

    def get_me(self) -> dict[str, Any] | None:
        """Return current user info or None."""
        resp = self.get("/api/v1/auth/me")
        if resp is None:
            return None
        return resp.get("data")  # type: ignore[no-any-return]

    # ------------------------------------------------------------------
    # Crypto
    # ------------------------------------------------------------------

    def fetch_crypto_list(self) -> list[dict[str, Any]] | None:
        """Return the list of tracked crypto symbols and names."""
        resp = self.get("/api/v1/crypto/list")
        if resp is None:
            return None
        return resp.get("data", [])  # type: ignore[no-any-return]

    def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int = 200) -> list[dict[str, Any]] | None:
        """Return OHLCV records for a symbol/timeframe pair."""
        resp = self.get(
            f"/api/v1/crypto/{symbol}/prices",
            params={"timeframe": timeframe, "limit": limit},
        )
        if resp is None:
            return None
        return resp.get("data", [])  # type: ignore[no-any-return]

    def fetch_indicators(self, symbol: str, timeframe: str) -> list[dict[str, Any]] | None:
        """Return indicator records (rsi, bollinger_*, trend_*) for a symbol/timeframe."""
        resp = self.get(
            f"/api/v1/crypto/{symbol}/indicators",
            params={"timeframe": timeframe},
        )
        if resp is None:
            return None
        return resp.get("data", [])  # type: ignore[no-any-return]

    def fetch_latest(self, symbol: str) -> dict[str, Any] | None:
        """Return the latest OHLCV + indicators snapshot for a symbol."""
        resp = self.get(f"/api/v1/crypto/{symbol}/latest")
        if resp is None:
            return None
        return resp.get("data")  # type: ignore[no-any-return]

    def fetch_market_overview(self) -> dict[str, Any] | None:
        """Return market overview (total_symbols, top_gainers, top_losers)."""
        resp = self.get("/api/v1/crypto/market-overview")
        if resp is None:
            return None
        return resp.get("data")  # type: ignore[no-any-return]

    # ------------------------------------------------------------------
    # Signals
    # ------------------------------------------------------------------

    def fetch_active_signals(self) -> list[dict[str, Any]] | None:
        """Return all currently active signals."""
        resp = self.get("/api/v1/signals/active")
        if resp is None:
            return None
        return resp.get("data", [])  # type: ignore[no-any-return]

    def fetch_signals(self, symbol: str | None = None) -> list[dict[str, Any]] | None:
        """Return signals, optionally filtered by symbol."""
        resp = self.get(f"/api/v1/signals/{symbol}") if symbol else self.get("/api/v1/signals/active")
        if resp is None:
            return None
        return resp.get("data", [])  # type: ignore[no-any-return]

    def fetch_signal_detail(self, signal_id: str | int) -> dict[str, Any] | None:
        """Return detailed info for a single signal."""
        resp = self.get(f"/api/v1/signals/{signal_id}/detail")
        if resp is None:
            return None
        return resp.get("data")  # type: ignore[no-any-return]

    def fetch_signal_performance(self) -> dict[str, Any] | None:
        """Return signal performance stats dict (win_rate, total_signals, etc.)."""
        resp = self.get("/api/v1/signals/performance")
        if resp is None:
            return None
        return resp.get("data")  # type: ignore[no-any-return]

    # ------------------------------------------------------------------
    # News
    # ------------------------------------------------------------------

    def fetch_news(
        self,
        source: str | None = None,
        keyword: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]] | None:
        """Return latest news articles with optional source/keyword filters."""
        params: dict[str, Any] = {"limit": limit}
        if source:
            params["source"] = source
        if keyword:
            params["keyword"] = keyword
        resp = self.get("/api/v1/news/latest", params=params)
        if resp is None:
            return None
        return resp.get("data", [])  # type: ignore[no-any-return]

    def fetch_news_detail(self, news_id: str | int) -> dict[str, Any] | None:
        """Return detail of a single news article."""
        resp = self.get(f"/api/v1/news/{news_id}")
        if resp is None:
            return None
        return resp.get("data")  # type: ignore[no-any-return]

    def fetch_news_sentiment(self) -> list[dict[str, Any]] | None:
        """Return aggregated sentiment per symbol."""
        resp = self.get("/api/v1/news/sentiment")
        if resp is None:
            return None
        return resp.get("data", [])  # type: ignore[no-any-return]

    # ------------------------------------------------------------------
    # Portfolio (JWT required)
    # ------------------------------------------------------------------

    def fetch_portfolio(self) -> list[dict[str, Any]] | None:
        """Return the authenticated user's portfolio positions."""
        resp = self.get("/api/v1/portfolio")
        if resp is None:
            return None
        return resp.get("data", [])  # type: ignore[no-any-return]

    def add_portfolio_position(self, position: dict[str, Any]) -> dict[str, Any] | None:
        """Add a new portfolio position. Returns the created position or None."""
        resp = self.post("/api/v1/portfolio", json=position)
        if resp is None:
            return None
        return resp.get("data")  # type: ignore[no-any-return]

    def update_portfolio_position(self, position_id: str | int, data: dict[str, Any]) -> dict[str, Any] | None:
        """Update an existing portfolio position."""
        resp = self.put(f"/api/v1/portfolio/{position_id}", json=data)
        if resp is None:
            return None
        return resp.get("data")  # type: ignore[no-any-return]

    def delete_portfolio_position(self, position_id: str | int) -> dict[str, Any] | None:
        """Delete a portfolio position."""
        resp = self.delete(f"/api/v1/portfolio/{position_id}")
        if resp is None:
            return None
        return resp  # type: ignore[no-any-return]

    # ------------------------------------------------------------------
    # Watchlist (JWT required)
    # ------------------------------------------------------------------

    def fetch_watchlist(self) -> list[dict[str, Any]] | None:
        """Return the authenticated user's watchlist."""
        resp = self.get("/api/v1/watchlist")
        if resp is None:
            return None
        return resp.get("data", [])  # type: ignore[no-any-return]

    def add_to_watchlist(self, symbol: str) -> dict[str, Any] | None:
        """Add a symbol to the watchlist."""
        resp = self.post("/api/v1/watchlist", json={"symbol": symbol})
        if resp is None:
            return None
        return resp.get("data")  # type: ignore[no-any-return]

    def remove_from_watchlist(self, symbol: str) -> dict[str, Any] | None:
        """Remove a symbol from the watchlist."""
        resp = self.delete(f"/api/v1/watchlist/{symbol}")
        if resp is None:
            return None
        return resp  # type: ignore[no-any-return]

    # ------------------------------------------------------------------
    # Chat (JWT required)
    # ------------------------------------------------------------------

    def chat(self, message: str) -> tuple[str | None, str | None]:
        """Send a chat message and return (reply, disclaimer) tuple."""
        resp = self.post("/api/v1/chat", json={"message": message})
        if resp is None:
            return None, None
        data = resp.get("data", {})
        if isinstance(data, dict):
            return data.get("reply"), data.get("disclaimer")
        return None, None

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
                    ind_copy = dict(ind)
                    ind_copy["timeframe"] = tf
                    results.append(ind_copy)
        return results if results else None
