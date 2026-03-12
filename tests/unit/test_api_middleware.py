"""Unit tests for API middleware (S12: rate limiting headers)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


class TestRateLimitHeadersMiddleware:
    """Test rate limit response headers middleware."""

    @pytest.mark.asyncio
    async def test_rate_limit_headers_present_on_response(self, client: AsyncClient) -> None:
        """Rate limit headers should be added to all responses."""
        resp = await client.get("/api/v1/health")
        assert resp.status_code == 200

        # Check headers are present
        assert "X-RateLimit-Limit" in resp.headers
        assert "X-RateLimit-Remaining" in resp.headers
        assert "X-RateLimit-Reset" in resp.headers

    @pytest.mark.asyncio
    async def test_rate_limit_header_values_valid(self, client: AsyncClient) -> None:
        """Rate limit header values should be numeric and valid."""
        resp = await client.get("/api/v1/health")

        limit = int(resp.headers["X-RateLimit-Limit"])
        remaining = int(resp.headers["X-RateLimit-Remaining"])
        reset = int(resp.headers["X-RateLimit-Reset"])

        # For default endpoints: 30 req/sec limit
        assert limit == 30
        # After first request, 29 remaining
        assert 0 <= remaining <= limit
        # Reset should be in future
        import time
        assert reset >= int(time.time())

    @pytest.mark.asyncio
    async def test_rate_limit_different_for_auth_endpoints(self, unauthed_client: AsyncClient) -> None:
        """Auth endpoints should have stricter rate limits."""
        # Auth endpoints have limit of 5 req/min
        resp = await unauthed_client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "wrong"},
        )

        # Even though login fails, headers should still be present
        assert "X-RateLimit-Limit" in resp.headers
        limit = int(resp.headers["X-RateLimit-Limit"])
        assert limit == 5  # Auth endpoint limit

    @pytest.mark.asyncio
    async def test_request_id_header_present(self, client: AsyncClient) -> None:
        """Request ID header should be added to track requests."""
        resp = await client.get("/api/v1/health")
        assert "X-Request-Id" in resp.headers
        assert resp.headers["X-Request-Id"].startswith("req_")

    @pytest.mark.asyncio
    async def test_cors_headers_include_rate_limit_headers(self, client: AsyncClient) -> None:
        """CORS should expose rate limit headers to clients."""
        resp = await client.get("/api/v1/health")

        # Check CORS expose headers
        expose_headers = resp.headers.get("Access-Control-Expose-Headers", "")
        assert "X-RateLimit-Limit" in expose_headers
        assert "X-RateLimit-Remaining" in expose_headers
        assert "X-RateLimit-Reset" in expose_headers
        assert "X-Request-Id" in expose_headers
