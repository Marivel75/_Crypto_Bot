"""Unit tests for the frontend API client (Semaine 3 endpoints).

Tests all new endpoint methods with mocked httpx.Client.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from src.frontend.api_client import APIClient


@pytest.fixture
def mock_session_state() -> dict:
    """Mock Streamlit session state."""
    return {"token": "test-token-123"}  # noqa: S105


@pytest.fixture
def api_client(mock_session_state: dict) -> APIClient:
    """Create an APIClient instance with mocked session state."""
    with patch("streamlit.session_state", mock_session_state):
        return APIClient()


class TestAuthRefresh:
    """Tests for JWT token refresh endpoint."""

    def test_refresh_token_success(self, api_client: APIClient) -> None:
        """Test successful token refresh."""
        mock_response = {
            "success": True,
            "data": {"access_token": "new-token-456"},  # noqa: S105
        }

        with patch.object(api_client, "post", return_value=mock_response):
            new_token = api_client.refresh_token()
            assert new_token == "new-token-456"  # noqa: S105

    def test_refresh_token_failure(self, api_client: APIClient) -> None:
        """Test failed token refresh."""
        with patch.object(api_client, "post", return_value=None):
            result = api_client.refresh_token()
            assert result is None


class TestPortfolioSummary:
    """Tests for portfolio summary endpoint."""

    def test_fetch_portfolio_summary_success(self, api_client: APIClient) -> None:
        """Test successful portfolio summary fetch."""
        summary_data = {
            "total_value": 15000.0,
            "total_cost": 12000.0,
            "pnl_pct": 25.0,
            "asset_allocation": {"BTC": 8000, "ETH": 7000},
        }
        mock_response = {"success": True, "data": summary_data}

        with patch.object(api_client, "get", return_value=mock_response):
            result = api_client.fetch_portfolio_summary()
            assert result == summary_data

    def test_fetch_portfolio_summary_none(self, api_client: APIClient) -> None:
        """Test portfolio summary with API failure."""
        with patch.object(api_client, "get", return_value=None):
            result = api_client.fetch_portfolio_summary()
            assert result is None


class TestPortfolioHistory:
    """Tests for portfolio history endpoint."""

    def test_fetch_portfolio_history_success(self, api_client: APIClient) -> None:
        """Test successful portfolio history fetch."""
        history_data = [
            {"timestamp": "2025-01-01", "total_value": 10000.0},
            {"timestamp": "2025-01-02", "total_value": 11000.0},
            {"timestamp": "2025-01-03", "total_value": 10500.0},
        ]
        mock_response = {"success": True, "data": history_data}

        with patch.object(api_client, "get", return_value=mock_response):
            result = api_client.fetch_portfolio_history()
            assert result == history_data
            assert len(result) == 3

    def test_fetch_portfolio_history_with_limit(self, api_client: APIClient) -> None:
        """Test portfolio history with custom limit."""
        mock_response = {"success": True, "data": []}

        with patch.object(api_client, "get", return_value=mock_response):
            api_client.fetch_portfolio_history(limit=30)
            api_client.get.assert_called_once()


class TestWatchlistPrices:
    """Tests for watchlist with prices endpoint."""

    def test_fetch_watchlist_prices_success(self, api_client: APIClient) -> None:
        """Test successful watchlist prices fetch."""
        prices_data = [
            {"symbol": "BTC", "price": 42000.0, "change_24h": 2.5},
            {"symbol": "ETH", "price": 2200.0, "change_24h": 1.8},
        ]
        mock_response = {"success": True, "data": prices_data}

        with patch.object(api_client, "get", return_value=mock_response):
            result = api_client.fetch_watchlist_prices()
            assert result == prices_data
            assert len(result) == 2


class TestSignalsHistory:
    """Tests for signals history endpoint with filters."""

    def test_fetch_signals_history_success(self, api_client: APIClient) -> None:
        """Test successful signals history fetch."""
        history_data = {
            "items": [
                {
                    "id": 1,
                    "symbol": "BTC",
                    "direction": "BUY",
                    "confidence": 0.85,
                    "created_at": "2025-01-01T10:00:00",
                }
            ],
            "total": 1,
        }
        mock_response = {"success": True, "data": history_data}

        with patch.object(api_client, "get", return_value=mock_response):
            result = api_client.fetch_signals_history()
            assert result == history_data
            assert len(result["items"]) == 1

    def test_fetch_signals_history_none(self, api_client: APIClient) -> None:
        """Test signals history with API failure."""
        with patch.object(api_client, "get", return_value=None):
            result = api_client.fetch_signals_history()
            assert result is None


class TestSystemMetrics:
    """Tests for system metrics endpoint."""

    def test_fetch_system_metrics_success(self, api_client: APIClient) -> None:
        """Test successful system metrics fetch."""
        metrics_data = {
            "uptime_hours": 24.5,
            "request_count": 1250,
            "error_rate": 0.02,
            "db_size_mb": 512.5,
            "market_regime": "BULL",
            "volatility": {"BTC": 18.5, "ETH": 22.3},
        }
        mock_response = {"success": True, "data": metrics_data}

        with patch.object(api_client, "get", return_value=mock_response):
            result = api_client.fetch_system_metrics()
            assert result == metrics_data
            assert result["market_regime"] == "BULL"

    def test_fetch_system_metrics_none(self, api_client: APIClient) -> None:
        """Test system metrics with API failure."""
        with patch.object(api_client, "get", return_value=None):
            result = api_client.fetch_system_metrics()
            assert result is None
