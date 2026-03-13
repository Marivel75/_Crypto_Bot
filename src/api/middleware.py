"""FastAPI middleware for request/response processing.

Includes:
- Rate limit response headers (X-RateLimit-*)
- Request tracking
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from collections.abc import Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = logging.getLogger(__name__)

# Configuration for rate limiting headers
RATE_LIMIT_CONFIG = {
    "default": {
        "limit": 30,  # requests per second
        "window": 1,  # seconds
    },
    "auth": {
        "limit": 5,  # requests per minute for auth endpoints
        "window": 60,
    },
}


class RateLimitHeadersMiddleware(BaseHTTPMiddleware):
    """Add rate limit response headers.

    Tracks requests per IP and adds informational headers to all responses:
    - X-RateLimit-Limit: max requests allowed in the window
    - X-RateLimit-Remaining: requests remaining in current window
    - X-RateLimit-Reset: unix timestamp when window resets

    This is for HEADERS ONLY — actual rate limiting is enforced by nginx.
    """

    def __init__(self, app: Callable) -> None:
        super().__init__(app)
        # Per-IP, per-endpoint request tracking: {(ip, endpoint): {count, window_start}}
        self._request_counters: dict[tuple[str, str], dict[str, int | float]] = defaultdict(
            lambda: {"count": 0, "window_start": time.time()}
        )

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and add rate limit headers to response."""
        # Get client IP (handle X-Forwarded-For for proxied requests)
        client_ip = request.client.host if request.client else "unknown"
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()

        # Determine which rate limit config applies
        path = request.url.path
        config_key = "auth" if "/auth" in path else "default"
        config = RATE_LIMIT_CONFIG[config_key]

        # Track request
        counter_key = (client_ip, config_key)
        counter = self._request_counters[counter_key]
        current_time = time.time()

        # Reset window if expired
        if current_time - counter["window_start"] >= config["window"]:
            counter["count"] = 0
            counter["window_start"] = current_time

        counter["count"] += 1
        limit = config["limit"]
        remaining = max(0, limit - counter["count"])
        reset_time = int(counter["window_start"] + config["window"])

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_time)

        return response


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Add request ID tracking for logging."""

    def __init__(self, app: Callable) -> None:
        super().__init__(app)
        self._request_counter = 0

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add request ID to logs."""
        self._request_counter += 1
        request_id = f"req_{self._request_counter}"
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-Id"] = request_id

        return response
