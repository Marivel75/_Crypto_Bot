"""Tests for the frontend API client — HTTP calls mocked with respx."""

from __future__ import annotations

from unittest.mock import patch

import httpx
import pytest
import respx

from src.frontend.api_client import APIClient


@pytest.fixture()
def api_client() -> APIClient:
    """Create an APIClient pointing to a test URL."""
    with patch("src.frontend.api_client.frontend_settings") as mock_settings:
        mock_settings.api_url = "http://testserver"
        mock_settings.api_timeout = 5.0
        mock_settings.api_connect_timeout = 2.0
        client = APIClient()
    return client


class TestAPIClientGet:
    """Test GET requests and error handling."""

    @respx.mock
    def test_get_success(self, api_client: APIClient) -> None:
        respx.get("http://testserver/api/v1/crypto/list").mock(
            return_value=httpx.Response(200, json={"data": [{"symbol": "BTC"}]})
        )
        result = api_client.get("/api/v1/crypto/list")
        assert result is not None
        assert result["data"] == [{"symbol": "BTC"}]

    @respx.mock
    def test_get_timeout_returns_none(self, api_client: APIClient) -> None:
        respx.get("http://testserver/api/v1/crypto/list").mock(side_effect=httpx.TimeoutException("timeout"))
        result = api_client.get("/api/v1/crypto/list")
        assert result is None

    @respx.mock
    def test_get_connect_error_returns_none(self, api_client: APIClient) -> None:
        respx.get("http://testserver/api/v1/crypto/list").mock(side_effect=httpx.ConnectError("connection refused"))
        result = api_client.get("/api/v1/crypto/list")
        assert result is None

    @respx.mock
    def test_get_401_clears_token(self, api_client: APIClient) -> None:
        respx.get("http://testserver/api/v1/auth/me").mock(
            return_value=httpx.Response(401, json={"error": "unauthorized"})
        )
        result = api_client.get("/api/v1/auth/me")
        assert result is None

    @respx.mock
    def test_get_500_returns_none(self, api_client: APIClient) -> None:
        respx.get("http://testserver/api/v1/crypto/list").mock(
            return_value=httpx.Response(500, json={"error": "internal"})
        )
        result = api_client.get("/api/v1/crypto/list")
        assert result is None


class TestAPIClientPost:
    """Test POST requests."""

    @respx.mock
    def test_post_success(self, api_client: APIClient) -> None:
        respx.post("http://testserver/api/v1/auth/login").mock(
            return_value=httpx.Response(
                200,
                json={"data": {"access_token": "jwt123"}},
            )
        )
        result = api_client.post(
            "/api/v1/auth/login",
            json={"email": "test@test.com", "password": "pass"},
        )
        assert result is not None
        assert result["data"]["access_token"] == "jwt123"  # noqa: S105


class TestAPIClientDomainMethods:
    """Test domain-specific helper methods."""

    @respx.mock
    def test_login_returns_token(self, api_client: APIClient) -> None:
        respx.post("http://testserver/api/v1/auth/login").mock(
            return_value=httpx.Response(
                200,
                json={"data": {"access_token": "tok_abc"}},
            )
        )
        token = api_client.login("user@test.com", "password")
        assert token == "tok_abc"  # noqa: S105

    @respx.mock
    def test_login_failure_returns_none(self, api_client: APIClient) -> None:
        respx.post("http://testserver/api/v1/auth/login").mock(
            return_value=httpx.Response(401, json={"error": "bad credentials"})
        )
        token = api_client.login("user@test.com", "wrong")
        assert token is None

    @respx.mock
    def test_fetch_crypto_list(self, api_client: APIClient) -> None:
        respx.get("http://testserver/api/v1/crypto/list").mock(
            return_value=httpx.Response(
                200,
                json={"data": [{"symbol": "BTC"}, {"symbol": "ETH"}]},
            )
        )
        result = api_client.fetch_crypto_list()
        assert result is not None
        assert len(result) == 2

    @respx.mock
    def test_fetch_ohlcv(self, api_client: APIClient) -> None:
        respx.get("http://testserver/api/v1/crypto/BTC/prices").mock(
            return_value=httpx.Response(
                200,
                json={"data": [{"price_close": 67000}]},
            )
        )
        result = api_client.fetch_ohlcv("BTC", "4h", limit=100)
        assert result is not None
        assert len(result) == 1

    @respx.mock
    def test_fetch_signal_performance(self, api_client: APIClient) -> None:
        respx.get("http://testserver/api/v1/signals/performance").mock(
            return_value=httpx.Response(
                200,
                json={"data": {"win_rate": 65.0, "total_signals": 50}},
            )
        )
        result = api_client.fetch_signal_performance()
        assert result is not None
        assert result["win_rate"] == 65.0

    @respx.mock
    def test_fetch_signal_detail(self, api_client: APIClient) -> None:
        respx.get("http://testserver/api/v1/signals/42/detail").mock(
            return_value=httpx.Response(
                200,
                json={"data": {"id": 42, "signal_type": "BUY"}},
            )
        )
        result = api_client.fetch_signal_detail(42)
        assert result is not None
        assert result["signal_type"] == "BUY"

    @respx.mock
    def test_fetch_news_detail(self, api_client: APIClient) -> None:
        respx.get("http://testserver/api/v1/news/7").mock(
            return_value=httpx.Response(
                200,
                json={"data": {"id": 7, "title": "BTC hits ATH"}},
            )
        )
        result = api_client.fetch_news_detail(7)
        assert result is not None
        assert result["title"] == "BTC hits ATH"

    @respx.mock
    def test_chat_returns_tuple(self, api_client: APIClient) -> None:
        respx.post("http://testserver/api/v1/chat").mock(
            return_value=httpx.Response(
                200,
                json={
                    "data": {
                        "reply": "BTC is bullish",
                        "disclaimer": "Not financial advice",
                    }
                },
            )
        )
        reply, disclaimer = api_client.chat("What about BTC?")
        assert reply == "BTC is bullish"
        assert disclaimer == "Not financial advice"

    @respx.mock
    def test_chat_api_down_returns_none_tuple(self, api_client: APIClient) -> None:
        respx.post("http://testserver/api/v1/chat").mock(side_effect=httpx.ConnectError("down"))
        reply, disclaimer = api_client.chat("hello")
        assert reply is None
        assert disclaimer is None

    @respx.mock
    def test_fetch_news_with_filters(self, api_client: APIClient) -> None:
        respx.get("http://testserver/api/v1/news/latest").mock(
            return_value=httpx.Response(
                200,
                json={"data": [{"title": "ETF News"}]},
            )
        )
        result = api_client.fetch_news(source="Decrypt", keyword="ETF", limit=10)
        assert result is not None
        assert len(result) == 1

    @respx.mock
    def test_fetch_market_overview(self, api_client: APIClient) -> None:
        respx.get("http://testserver/api/v1/crypto/market-overview").mock(
            return_value=httpx.Response(
                200,
                json={"data": {"total_market_cap": 2500000000000}},
            )
        )
        result = api_client.fetch_market_overview()
        assert result is not None
        assert result["total_market_cap"] == 2500000000000
