"""HTTP client for the Crypto Bot FastAPI backend.

All methods return parsed JSON (dict or list) on success, None on any error.
No JWT/auth — the backend is unauthenticated.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from frontend.config import frontend_settings

logger = logging.getLogger(__name__)

_TIMEOUT = 10.0


class APIClient:
    """Thin synchronous wrapper around httpx for the Crypto Bot API."""

    def __init__(self, base_url: str | None = None) -> None:
        self._base = (base_url or frontend_settings.api_url).rstrip("/")

    # ------------------------------------------------------------------
    # Low-level helper
    # ------------------------------------------------------------------

    def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """GET *path* and return the parsed JSON body, or None on error."""
        url = f"{self._base}{path}"
        try:
            with httpx.Client(timeout=_TIMEOUT) as client:
                r = client.get(url, params=params)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 404:
                return None
            logger.warning("GET %s → HTTP %s", path, r.status_code)
            return None
        except httpx.RequestError as exc:
            logger.error("GET %s failed: %s", path, exc)
            return None

    def post(self, path: str, json: dict[str, Any] | None = None) -> dict[str, Any]:
        """POST *path* and return the parsed JSON body.

        Always returns a dict — on error the dict contains an ``"error"`` key.
        """
        url = f"{self._base}{path}"
        try:
            with httpx.Client(timeout=_TIMEOUT) as client:
                r = client.post(url, json=json)
            if r.status_code in (200, 201):
                return r.json()
            try:
                detail = r.json().get("detail", f"Erreur HTTP {r.status_code}")
            except Exception:
                detail = f"Erreur HTTP {r.status_code}"
            logger.warning("POST %s → HTTP %s : %s", path, r.status_code, detail)
            return {"error": detail}
        except httpx.RequestError as exc:
            logger.error("POST %s failed: %s", path, exc)
            return {"error": str(exc)}

    # ------------------------------------------------------------------
    # OHLCV endpoints
    # ------------------------------------------------------------------

    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1d",
        limit: int = 200,
        exchange: str | None = None,
    ) -> list[dict[str, Any]] | None:
        """GET /ohlcv — filtered by symbol/timeframe, ordered DESC by timestamp."""
        params: dict[str, Any] = {"symbol": symbol, "timeframe": timeframe, "limit": limit}
        if exchange:
            params["exchange"] = exchange
        result = self.get("/ohlcv", params)
        if not isinstance(result, list):
            return None
        return result

    def fetch_symbols(self, exchange: str | None = None) -> list[dict[str, Any]] | None:
        """GET /ohlcv/symbols — list of available (symbol, exchange, timeframe, count)."""
        params = {"exchange": exchange} if exchange else None
        result = self.get("/ohlcv/symbols", params)
        return result if isinstance(result, list) else None

    def fetch_distinct_count(self, symbol: str, timeframe: str) -> int:
        """GET /ohlcv/distinct-count — nombre de timestamps uniques pour (symbol, timeframe)."""
        result = self.get("/ohlcv/distinct-count", {"symbol": symbol, "timeframe": timeframe})
        if isinstance(result, list) and result:
            return max(r.get("distinct_count", 0) for r in result)
        return 0

    def fetch_latest(self, timeframe: str = "1d") -> list[dict[str, Any]] | None:
        """GET /ohlcv/latest — most recent candle per symbol for the given timeframe."""
        result = self.get("/ohlcv/latest", {"timeframe": timeframe})
        return result if isinstance(result, list) else None

    # ------------------------------------------------------------------
    # Signals endpoint
    # ------------------------------------------------------------------

    def fetch_signals(
        self,
        symbol: str,
        timeframe: str = "1d",
        limit: int = 100,
        exchange: str | None = None,
    ) -> list[dict[str, Any]] | None:
        """GET /signals — OHLCV + computed technical indicators per candle.

        Returns None when the symbol is unknown (404) or on network error.
        Rows are ordered ASC by timestamp (oldest first) by the API.
        """
        params: dict[str, Any] = {"symbol": symbol, "timeframe": timeframe, "limit": limit}
        if exchange:
            params["exchange"] = exchange
        result = self.get("/signals", params)
        if not isinstance(result, list):
            return None
        return result

    # ------------------------------------------------------------------
    # Market endpoints
    # ------------------------------------------------------------------

    def fetch_market_top(
        self, limit: int = 20, currency: str = "usd"
    ) -> dict[str, Any] | None:
        """GET /market/top — latest top-crypto snapshot with ranked list."""
        result = self.get("/market/top", {"limit": limit, "currency": currency})
        return result if isinstance(result, dict) else None

    def fetch_market_global(self) -> dict[str, Any] | None:
        """GET /market/global — global market cap, volume, dominance."""
        result = self.get("/market/global")
        return result if isinstance(result, dict) else None

    def fetch_fear_greed(self) -> dict[str, Any] | None:
        """GET /market/fear-greed — current Fear & Greed index (0–100)."""
        result = self.get("/market/fear-greed")
        return result if isinstance(result, dict) else None

    def fetch_ticker(
        self,
        symbol: str | None = None,
        exchange: str | None = None,
    ) -> list[dict[str, Any]] | None:
        """GET /market/ticker — ticker snapshots, optionally filtered."""
        params: dict[str, Any] = {}
        if symbol:
            params["symbol"] = symbol
        if exchange:
            params["exchange"] = exchange
        result = self.get("/market/ticker", params or None)
        return result if isinstance(result, list) else None

    # ------------------------------------------------------------------
    # News endpoints
    # ------------------------------------------------------------------

    def fetch_news(
        self,
        source: str | None = None,
        sentiment: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]] | None:
        """GET /news — recent articles, newest first."""
        params: dict[str, Any] = {"limit": limit}
        if source:
            params["source"] = source
        if sentiment:
            params["sentiment"] = sentiment
        result = self.get("/news", params)
        return result if isinstance(result, list) else None

    def fetch_news_sources(self) -> list[str] | None:
        """GET /news/sources — distinct source names in DB."""
        result = self.get("/news/sources")
        return result if isinstance(result, list) else None

    def fetch_news_sentiment(self) -> list[dict[str, Any]] | None:
        """GET /news/sentiment — per-source sentiment aggregates."""
        result = self.get("/news/sentiment")
        return result if isinstance(result, list) else None

    # ------------------------------------------------------------------
    # ML endpoints
    # ------------------------------------------------------------------

    def run_backtest(
        self,
        symbol: str,
        timeframe: str = "1d",
        model_type: str = "random_forest",
        train_window: int = 180,
        test_window: int = 30,
    ) -> dict[str, Any]:
        """GET /ml/backtest — lance un backtest walk-forward et retourne les résultats.

        Retourne toujours un dict :
          - succès  : résultats complets (clé "folds" présente)
          - échec   : {"error": "message explicite"}
        """
        url = f"{self._base}/ml/backtest"
        params: dict[str, Any] = {
            "symbol": symbol,
            "timeframe": timeframe,
            "model_type": model_type,
            "train_window": train_window,
            "test_window": test_window,
        }
        try:
            with httpx.Client(timeout=120.0) as client:
                r = client.get(url, params=params)
            if r.status_code == 200:
                return r.json()
            # Récupère le message d'erreur de l'API (422, 404, 500…)
            try:
                detail = r.json().get("detail", f"Erreur HTTP {r.status_code}")
            except Exception:
                detail = f"Erreur HTTP {r.status_code}"
            logger.warning("Backtest %s → %s : %s", params, r.status_code, detail)
            return {"error": detail}
        except httpx.RequestError as exc:
            logger.error("Backtest request failed: %s", exc)
            return {"error": f"API inaccessible : {exc}"}

    def subscribe_alert(self, email: str) -> dict[str, Any]:
        """POST /alerts/subscribe — abonne un email aux alertes de collecte."""
        try:
            with httpx.Client(timeout=10.0) as client:
                r = client.post(f"{self._base}/alerts/subscribe", json={"email": email})
            return r.json()
        except Exception as exc:
            return {"error": str(exc)}

    def unsubscribe_alert(self, email: str) -> dict[str, Any]:
        """DELETE /alerts/unsubscribe/{email} — désabonne un email."""
        try:
            with httpx.Client(timeout=10.0) as client:
                r = client.delete(f"{self._base}/alerts/unsubscribe/{email}")
            return r.json() if r.status_code != 404 else {"error": "Email non abonné"}
        except Exception as exc:
            return {"error": str(exc)}

    # ------------------------------------------------------------------
    # Paper Trading endpoints
    # ------------------------------------------------------------------

    def create_portfolio(self, name: str, initial_capital: float) -> dict[str, Any]:
        """POST /paper-trading/portfolios — crée un nouveau portefeuille fictif."""
        return self.post("/paper-trading/portfolios", {"name": name, "initial_capital": initial_capital})

    def list_portfolios(self) -> list[dict[str, Any]] | None:
        """GET /paper-trading/portfolios — liste tous les portefeuilles."""
        result = self.get("/paper-trading/portfolios")
        return result if isinstance(result, list) else None

    def get_portfolio_summary(self, portfolio_id: str) -> dict[str, Any] | None:
        """GET /paper-trading/portfolios/{id} — résumé complet (métriques + positions)."""
        result = self.get(f"/paper-trading/portfolios/{portfolio_id}")
        return result if isinstance(result, dict) else None

    def place_order(
        self,
        portfolio_id: str,
        symbol: str,
        quantity: float | None = None,
        amount_usdt: float | None = None,
        signal_source: str = "manual",
        signal_score: float | None = None,
    ) -> dict[str, Any]:
        """POST /paper-trading/orders — ouvre une position BUY."""
        payload: dict[str, Any] = {"portfolio_id": portfolio_id, "symbol": symbol, "signal_source": signal_source}
        if quantity is not None:
            payload["quantity"] = quantity
        if amount_usdt is not None:
            payload["amount_usdt"] = amount_usdt
        if signal_score is not None:
            payload["signal_score"] = signal_score
        return self.post("/paper-trading/orders", payload)

    def close_order(self, trade_id: str) -> dict[str, Any]:
        """POST /paper-trading/orders/{id}/close — ferme une position ouverte."""
        return self.post(f"/paper-trading/orders/{trade_id}/close")

    def list_orders(
        self,
        portfolio_id: str | None = None,
        symbol: str | None = None,
        status: str | None = None,
        limit: int = 200,
    ) -> list[dict[str, Any]] | None:
        """GET /paper-trading/orders — historique des trades."""
        params: dict[str, Any] = {"limit": limit}
        if portfolio_id:
            params["portfolio_id"] = portfolio_id
        if symbol:
            params["symbol"] = symbol
        if status:
            params["status"] = status
        result = self.get("/paper-trading/orders", params)
        return result if isinstance(result, list) else None
