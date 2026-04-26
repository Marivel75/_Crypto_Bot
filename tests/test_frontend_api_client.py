"""Tests pour frontend/api_client.py — méthodes GET avec httpx mocké."""

import sys
import os
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from frontend.api_client import APIClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_response(status: int, body):
    """Build a mock httpx response."""
    r = MagicMock()
    r.status_code = status
    r.json.return_value = body
    return r


def _patch_get(response):
    """Context manager that patches httpx.Client.get for one call."""
    return patch(
        "frontend.api_client.httpx.Client",
        return_value=MagicMock(
            __enter__=MagicMock(return_value=MagicMock(get=MagicMock(return_value=response))),
            __exit__=MagicMock(return_value=False),
        ),
    )


# ---------------------------------------------------------------------------
# APIClient.get (low-level)
# ---------------------------------------------------------------------------

class TestAPIClientGet:
    def test_returns_json_on_200(self):
        resp = _mock_response(200, {"status": "ok"})
        with _patch_get(resp):
            result = APIClient().get("/health")
        assert result == {"status": "ok"}

    def test_returns_none_on_404(self):
        resp = _mock_response(404, {})
        with _patch_get(resp):
            result = APIClient().get("/signals")
        assert result is None

    def test_returns_none_on_server_error(self):
        resp = _mock_response(500, {})
        with _patch_get(resp):
            result = APIClient().get("/ohlcv")
        assert result is None

    def test_returns_none_on_network_error(self):
        import httpx
        with patch("frontend.api_client.httpx.Client") as mock_cls:
            mock_cls.return_value.__enter__.side_effect = httpx.RequestError("timeout")
            result = APIClient().get("/health")
        assert result is None


# ---------------------------------------------------------------------------
# fetch_ohlcv
# ---------------------------------------------------------------------------

class TestFetchOhlcv:
    _sample = [
        {"symbol": "BTC/USDT", "timeframe": "1d", "open": 60000.0, "close": 61000.0,
         "high": 62000.0, "low": 59000.0, "volume": 1000.0, "timestamp": "2026-04-25T00:00:00"},
    ]

    def test_returns_list_on_success(self):
        resp = _mock_response(200, self._sample)
        with _patch_get(resp):
            result = APIClient().fetch_ohlcv("BTC/USDT", "1d")
        assert isinstance(result, list)
        assert len(result) == 1

    def test_passes_correct_params(self):
        resp = _mock_response(200, [])
        with patch("frontend.api_client.httpx.Client") as mock_cls:
            mock_get = MagicMock(return_value=resp)
            mock_cls.return_value.__enter__.return_value.get = mock_get
            mock_cls.return_value.__exit__ = MagicMock(return_value=False)
            APIClient().fetch_ohlcv("ETH/USDT", "4h", limit=50)
        call_kwargs = mock_get.call_args
        params = call_kwargs[1].get("params") or call_kwargs[0][1]
        assert params["symbol"] == "ETH/USDT"
        assert params["timeframe"] == "4h"
        assert params["limit"] == 50

    def test_returns_none_on_non_list_response(self):
        resp = _mock_response(200, {"error": "unexpected"})
        with _patch_get(resp):
            result = APIClient().fetch_ohlcv("BTC/USDT", "1d")
        assert result is None

    def test_returns_none_on_404(self):
        resp = _mock_response(404, {})
        with _patch_get(resp):
            result = APIClient().fetch_ohlcv("UNKNOWN/USDT", "1d")
        assert result is None


# ---------------------------------------------------------------------------
# fetch_signals
# ---------------------------------------------------------------------------

class TestFetchSignals:
    _sample = [
        {"symbol": "BTC/USDT", "timeframe": "1d", "close": 65000.0,
         "rsi_14": 55.3, "sma_20": 63000.0, "timestamp": "2026-04-25T00:00:00"},
    ]

    def test_returns_list_on_success(self):
        resp = _mock_response(200, self._sample)
        with _patch_get(resp):
            result = APIClient().fetch_signals("BTC/USDT", "1d")
        assert isinstance(result, list)
        assert result[0]["rsi_14"] == 55.3

    def test_returns_none_on_404(self):
        resp = _mock_response(404, {})
        with _patch_get(resp):
            result = APIClient().fetch_signals("UNKNOWN/USDT", "1d")
        assert result is None


# ---------------------------------------------------------------------------
# fetch_market_global
# ---------------------------------------------------------------------------

class TestFetchMarketGlobal:
    _sample = {
        "snapshot_time": "2026-04-25T10:00:00",
        "market_cap_usd": 2.3e12,
        "volume_usd": 9.8e10,
        "dominance": [{"asset": "btc", "percentage": 54.2}],
    }

    def test_returns_dict_on_success(self):
        resp = _mock_response(200, self._sample)
        with _patch_get(resp):
            result = APIClient().fetch_market_global()
        assert isinstance(result, dict)
        assert "market_cap_usd" in result

    def test_returns_none_on_list_response(self):
        resp = _mock_response(200, [])
        with _patch_get(resp):
            result = APIClient().fetch_market_global()
        assert result is None


# ---------------------------------------------------------------------------
# fetch_market_top
# ---------------------------------------------------------------------------

class TestFetchMarketTop:
    _sample = {
        "snapshot_time": "2026-04-25T10:00:00",
        "vs_currency": "usd",
        "cryptos": [
            {"rank": 1, "symbol": "BTC", "price": 65000.0},
            {"rank": 2, "symbol": "ETH", "price": 3000.0},
        ],
    }

    def test_returns_dict_with_cryptos(self):
        resp = _mock_response(200, self._sample)
        with _patch_get(resp):
            result = APIClient().fetch_market_top(limit=10)
        assert isinstance(result, dict)
        assert len(result["cryptos"]) == 2

    def test_returns_none_on_unknown_currency(self):
        resp = _mock_response(404, {})
        with _patch_get(resp):
            result = APIClient().fetch_market_top(currency="XYZ")
        assert result is None


# ---------------------------------------------------------------------------
# fetch_symbols
# ---------------------------------------------------------------------------

class TestFetchSymbols:
    _sample = [
        {"symbol": "BTC/USDT", "exchange": "binance", "timeframe": "1d", "count": 365},
        {"symbol": "ETH/USDT", "exchange": "binance", "timeframe": "1h", "count": 720},
    ]

    def test_returns_list(self):
        resp = _mock_response(200, self._sample)
        with _patch_get(resp):
            result = APIClient().fetch_symbols()
        assert isinstance(result, list)
        assert len(result) == 2

    def test_returns_none_on_non_list(self):
        resp = _mock_response(200, {"error": "bad"})
        with _patch_get(resp):
            result = APIClient().fetch_symbols()
        assert result is None
