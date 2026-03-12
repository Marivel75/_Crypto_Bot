"""Shared utilities — structured logging setup and async retry helper."""

from __future__ import annotations

import asyncio
import logging
import sys
from collections.abc import Callable, Coroutine
from typing import Any, TypeVar

from src.shared.config import settings

T = TypeVar("T")

logger = logging.getLogger(__name__)


def setup_logging(name: str = "cryptobot") -> logging.Logger:
    """Configure structured logging for a service.

    Attaches a single ``StreamHandler`` to stdout if one is not already
    present, so repeated calls are idempotent.

    Args:
        name: Logger name (used as root for the service's hierarchy).

    Returns:
        Configured ``Logger`` instance.
    """
    root = logging.getLogger(name)
    root.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))

    # Avoid duplicate handlers when the function is called multiple times
    if not root.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        root.addHandler(handler)

    return root


async def with_retry(
    coro_factory: Callable[[], Coroutine[Any, Any, T]],
    *,
    max_attempts: int = 5,
    base_delay: float = 1.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> T:
    """Execute a coroutine with exponential-backoff retry.

    Args:
        coro_factory: Zero-argument callable that returns a fresh coroutine on
            each call. Must be called without ``await`` here.
        max_attempts: Maximum number of total attempts before re-raising.
        base_delay: Base delay in seconds; doubles on each retry.
        exceptions: Tuple of exception types to catch and retry on.

    Returns:
        The return value of the successful coroutine execution.

    Raises:
        The last caught exception if all attempts are exhausted.
    """
    last_exc: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            return await coro_factory()
        except exceptions as exc:
            last_exc = exc
            if attempt == max_attempts:
                raise
            # Exponential backoff: 1s, 2s, 4s, 8s, …
            delay = base_delay * (2 ** (attempt - 1))
            logger.warning(
                "Attempt %d/%d failed: %s. Retrying in %.1fs",
                attempt,
                max_attempts,
                exc,
                delay,
            )
            await asyncio.sleep(delay)
    raise last_exc  # type: ignore[misc]
