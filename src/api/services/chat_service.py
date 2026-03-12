"""Chat service — LLM-powered crypto assistant."""

from __future__ import annotations

import asyncio
import logging

import httpx
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.config import settings
from src.shared.database import async_session_factory
from src.shared.exceptions import ExternalAPIError
from src.shared.models.orm import (
    PortfolioEntryOrm,
    TradingSignalOrm,
    WatchlistEntryOrm,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a crypto market analysis assistant. "
    "You provide informational insights based on market data, signals, and news. "
    "You NEVER provide financial advice. "
    "Always remind users that past performance does not guarantee future results."
)

DISCLAIMER = "Je ne suis pas un conseiller financier. Ces informations sont purement indicatives."

FINANCE_KEYWORDS = (
    "buy",
    "sell",
    "invest",
    "trade",
    "acheter",
    "vendre",
    "investir",
    "trader",
    "long",
    "short",
    "leverage",
    "levier",
)


async def chat(
    db: AsyncSession,
    message: str,
    user_id: str,
) -> dict[str, str | None]:
    """Process a user message and return the LLM reply with optional disclaimer.

    Builds a context string from the user's portfolio, watchlist, and recent
    signals, then calls the configured LLM. A financial disclaimer is appended
    when the message contains finance-related keywords.

    Args:
        db: Active async database session (used to build user context).
        message: Raw message text from the user.
        user_id: UUID string of the authenticated user.

    Returns:
        Dict with keys ``reply`` (str) and ``disclaimer`` (str | None).

    Raises:
        ExternalAPIError: If no LLM API key is configured or the upstream call fails.
    """
    context = await _build_context(db, user_id)
    reply = await _call_llm(message, context)

    disclaimer = None
    message_lower = message.lower()
    if any(kw in message_lower for kw in FINANCE_KEYWORDS):
        disclaimer = DISCLAIMER

    return {"reply": reply, "disclaimer": disclaimer}


async def _build_context(db: AsyncSession, user_id: str) -> str:
    """Build context from user's portfolio, watchlist, and recent signals concurrently."""

    async def _fetch_signals() -> list[TradingSignalOrm]:
        async with async_session_factory() as session:
            result = await session.execute(
                select(TradingSignalOrm).order_by(desc(TradingSignalOrm.created_at)).limit(5)
            )
            return list(result.scalars().all())

    async def _fetch_portfolio() -> list[PortfolioEntryOrm]:
        async with async_session_factory() as session:
            result = await session.execute(select(PortfolioEntryOrm).where(PortfolioEntryOrm.user_id == user_id))
            return list(result.scalars().all())

    async def _fetch_watchlist() -> list[WatchlistEntryOrm]:
        async with async_session_factory() as session:
            result = await session.execute(select(WatchlistEntryOrm).where(WatchlistEntryOrm.user_id == user_id))
            return list(result.scalars().all())

    signals, portfolio, watchlist = await asyncio.gather(_fetch_signals(), _fetch_portfolio(), _fetch_watchlist())

    parts: list[str] = []

    if signals:
        signal_lines = [f"- {s.symbol} {s.signal_type} (confidence: {s.confidence_score})" for s in signals]
        parts.append("Recent signals:\n" + "\n".join(signal_lines))

    if portfolio:
        portfolio_lines = [f"- {p.symbol}: {p.quantity} @ {p.entry_price}" for p in portfolio]  # type: ignore[attr-defined]
        parts.append("User portfolio:\n" + "\n".join(portfolio_lines))

    if watchlist:
        symbols: list[str] = [str(w.symbol) for w in watchlist]
        parts.append(f"User watchlist: {', '.join(symbols)}")

    return "\n\n".join(parts) if parts else "No user context available."


_llm_client: httpx.AsyncClient | None = None


def _get_llm_client() -> httpx.AsyncClient:
    """Return a reusable httpx client for LLM API calls."""
    global _llm_client  # noqa: PLW0603
    if _llm_client is None or _llm_client.is_closed:
        _llm_client = httpx.AsyncClient(timeout=httpx.Timeout(30.0))
    return _llm_client


async def _call_llm(message: str, context: str) -> str:
    """Dispatch the message to the first available LLM provider.

    Tries OpenAI if ``OPENAI_API_KEY`` is set, otherwise falls back to
    Anthropic if ``ANTHROPIC_API_KEY`` is set.

    Args:
        message: User's message text.
        context: Pre-built context string (portfolio, watchlist, signals).

    Returns:
        LLM-generated reply string.

    Raises:
        ExternalAPIError: If no API key is configured.
    """
    full_system = f"{SYSTEM_PROMPT}\n\nContext:\n{context}"
    client = _get_llm_client()

    if settings.openai_api_key:
        return await _call_openai(client, full_system, message)
    if settings.anthropic_api_key:
        return await _call_anthropic(client, full_system, message)

    raise ExternalAPIError("No LLM API key configured. Set OPENAI_API_KEY or ANTHROPIC_API_KEY.")


async def _call_openai(client: httpx.AsyncClient, system: str, message: str) -> str:
    """Send a request to the OpenAI Chat Completions API.

    Args:
        client: Shared httpx.AsyncClient instance.
        system: System prompt (includes user context).
        message: User message to forward.

    Returns:
        Content string from the first choice in the API response.

    Raises:
        ExternalAPIError: On any HTTP error from the OpenAI API.
    """
    try:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            json={
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": message},
                ],
                "max_tokens": 1000,
            },
        )
        response.raise_for_status()
        data = response.json()
        try:
            return str(data["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError) as exc:
            logger.error("Unexpected OpenAI response structure: %s", data)
            raise ExternalAPIError("Unexpected response from OpenAI API") from exc
    except httpx.HTTPError as exc:
        logger.error("OpenAI API error: %s", exc)
        raise ExternalAPIError("Failed to call OpenAI API") from exc


async def _call_anthropic(client: httpx.AsyncClient, system: str, message: str) -> str:
    """Send a request to the Anthropic Messages API.

    Args:
        client: Shared httpx.AsyncClient instance.
        system: System prompt (includes user context).
        message: User message to forward.

    Returns:
        Text content from the first content block in the API response.

    Raises:
        ExternalAPIError: On any HTTP error from the Anthropic API.
    """
    try:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": settings.anthropic_api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-haiku-4-5-20251001",
                "max_tokens": 1000,
                "system": system,
                "messages": [{"role": "user", "content": message}],
            },
        )
        response.raise_for_status()
        data = response.json()
        try:
            return str(data["content"][0]["text"])
        except (KeyError, IndexError, TypeError) as exc:
            logger.error("Unexpected Anthropic response structure: %s", data)
            raise ExternalAPIError("Unexpected response from Anthropic API") from exc
    except httpx.HTTPError as exc:
        logger.error("Anthropic API error: %s", exc)
        raise ExternalAPIError("Failed to call Anthropic API") from exc
