"""Integration tests for TimescaleDB loader functions.

These tests mock ``async_session_factory`` from ``src.shared.database`` so
the loader functions never touch a real PostgreSQL instance.  We verify that:

* Empty inputs short-circuit without touching the session.
* Non-empty inputs open a session, execute the expected SQL, commit, and
  return the correct row-count.
* ``fetch_ohlcv_for_indicators`` passes the right parameters and returns
  rows in chronological order.

PostgreSQL-specific syntax (ON CONFLICT, ::jsonb) lives only in the loader;
the session is fully mocked here, so SQLite compatibility is not a concern.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.shared.models.crypto import IndicatorRecord, NewsArticle, OHLCVRecord

# ---------------------------------------------------------------------------
# Fixed timestamps — never use datetime.now() in tests
# ---------------------------------------------------------------------------
_TS_BASE = datetime(2025, 1, 15, 12, 0, 0, tzinfo=UTC)
_TS_LATER = datetime(2025, 1, 15, 13, 0, 0, tzinfo=UTC)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_session_mock(rowcount: int = 1) -> AsyncMock:
    """Return a fully-async session mock whose execute() returns *rowcount*."""
    result_mock = MagicMock()
    result_mock.rowcount = rowcount

    session_mock = AsyncMock()
    session_mock.execute = AsyncMock(return_value=result_mock)
    session_mock.commit = AsyncMock()

    # Support ``async with async_session_factory() as session``
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=session_mock)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


def _make_ohlcv_record(
    symbol: str = "BTCUSDT",
    timeframe: str = "1h",
    ts: datetime = _TS_BASE,
) -> OHLCVRecord:
    return OHLCVRecord(
        symbol=symbol,
        timeframe=timeframe,
        timestamp=ts,
        price_open=Decimal("29000.00"),
        price_high=Decimal("29500.00"),
        price_low=Decimal("28800.00"),
        price_close=Decimal("29200.00"),
        volume_24h=Decimal("12345.67"),
        market_cap=Decimal("567000000.00"),
        source="binance",
    )


def _make_indicator_record(
    symbol: str = "BTCUSDT",
    timeframe: str = "1h",
    ts: datetime = _TS_BASE,
) -> IndicatorRecord:
    return IndicatorRecord(
        symbol=symbol,
        timeframe=timeframe,
        timestamp=ts,
        rsi=Decimal("45.30"),
        bollinger_upper=Decimal("30000.00"),
        bollinger_middle=Decimal("29000.00"),
        bollinger_lower=Decimal("28000.00"),
        price_vs_bollinger=Decimal("0.12"),
        harmonic_pattern=None,
        trend_slope=Decimal("0.05"),
        trend_type="stable",
        metadata={"extra": "value"},
    )


def _make_news_article(url: str = "https://example.com/btc-news") -> NewsArticle:
    return NewsArticle(
        title="Bitcoin Breaks $30k",
        content="BTC surges past the psychological resistance level.",
        source="decrypt",
        url=url,
        published_at=_TS_BASE,
        sentiment_score=Decimal("0.75"),
        keywords=["bitcoin", "price", "breakout"],
        reliability_score=Decimal("0.9"),
    )


# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------


class TestTimescaleDBLoader:
    """Tests for src/etl/loaders/timescaledb.py."""

    # ------------------------------------------------------------------
    # insert_ohlcv_batch
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_insert_ohlcv_batch_empty(self) -> None:
        """Empty record list must return 0 without opening a session."""
        with patch("src.etl.loaders.timescaledb.async_session_factory") as mock_factory:
            from src.etl.loaders.timescaledb import insert_ohlcv_batch

            result = await insert_ohlcv_batch([])

        assert result == 0
        mock_factory.assert_not_called()

    @pytest.mark.asyncio
    async def test_insert_ohlcv_batch_success(self) -> None:
        """Batch execute sends all params in a single call; rowcount is returned."""
        records = [
            _make_ohlcv_record(ts=_TS_BASE),
            _make_ohlcv_record(ts=_TS_LATER),
        ]
        session_cm = _make_session_mock(rowcount=2)

        with patch(
            "src.etl.loaders.timescaledb.async_session_factory",
            return_value=session_cm,
        ):
            from src.etl.loaders.timescaledb import insert_ohlcv_batch

            result = await insert_ohlcv_batch(records)

        session = session_cm.__aenter__.return_value
        assert result == 2
        assert session.execute.call_count == 1
        session.commit.assert_awaited_once()

        # Verify the params list passed to the single execute call
        call_params = session.execute.call_args_list[0].args[1]
        assert isinstance(call_params, list)
        assert len(call_params) == 2
        assert call_params[0]["symbol"] == "BTCUSDT"
        assert call_params[0]["timeframe"] == "1h"
        assert call_params[0]["timestamp"] == _TS_BASE
        assert call_params[0]["price_open"] == pytest.approx(29000.00)
        assert call_params[0]["price_close"] == pytest.approx(29200.00)
        assert call_params[0]["source"] == "binance"

    # ------------------------------------------------------------------
    # insert_indicators_batch
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_insert_indicators_batch_empty(self) -> None:
        """Empty list must return 0 without opening a session."""
        with patch("src.etl.loaders.timescaledb.async_session_factory") as mock_factory:
            from src.etl.loaders.timescaledb import insert_indicators_batch

            result = await insert_indicators_batch([])

        assert result == 0
        mock_factory.assert_not_called()

    @pytest.mark.asyncio
    async def test_insert_indicators_batch_success(self) -> None:
        """Batch execute sends all params in a single call; rowcount is returned."""
        records = [
            _make_indicator_record(ts=_TS_BASE),
            _make_indicator_record(ts=_TS_LATER),
        ]
        session_cm = _make_session_mock(rowcount=2)

        with patch(
            "src.etl.loaders.timescaledb.async_session_factory",
            return_value=session_cm,
        ):
            from src.etl.loaders.timescaledb import insert_indicators_batch

            result = await insert_indicators_batch(records)

        session = session_cm.__aenter__.return_value
        assert result == 2
        assert session.execute.call_count == 1
        session.commit.assert_awaited_once()

        # Verify the params list passed to the single execute call
        call_params = session.execute.call_args_list[0].args[1]
        assert isinstance(call_params, list)
        assert len(call_params) == 2
        assert call_params[0]["symbol"] == "BTCUSDT"
        assert call_params[0]["timeframe"] == "1h"
        assert call_params[0]["timestamp"] == _TS_BASE
        assert call_params[0]["rsi"] == pytest.approx(45.30)
        assert call_params[0]["trend_type"] == "stable"
        assert call_params[0]["harmonic_pattern"] is None
        assert json.loads(call_params[0]["metadata"]) == {"extra": "value"}

    # ------------------------------------------------------------------
    # insert_news_batch
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_insert_news_batch_empty(self) -> None:
        """Empty article list must return 0 without opening a session."""
        with patch("src.etl.loaders.timescaledb.async_session_factory") as mock_factory:
            from src.etl.loaders.timescaledb import insert_news_batch

            result = await insert_news_batch([])

        assert result == 0
        mock_factory.assert_not_called()

    @pytest.mark.asyncio
    async def test_insert_news_batch_success(self) -> None:
        """Batch execute sends all params in a single call; rowcount is returned."""
        articles = [
            _make_news_article(url="https://example.com/article-1"),
            _make_news_article(url="https://example.com/article-2"),
        ]
        session_cm = _make_session_mock(rowcount=2)

        with patch(
            "src.etl.loaders.timescaledb.async_session_factory",
            return_value=session_cm,
        ):
            from src.etl.loaders.timescaledb import insert_news_batch

            result = await insert_news_batch(articles)

        session = session_cm.__aenter__.return_value
        assert result == 2
        assert session.execute.call_count == 1
        session.commit.assert_awaited_once()

        # Verify the params list passed to the single execute call
        call_params = session.execute.call_args_list[0].args[1]
        assert isinstance(call_params, list)
        assert len(call_params) == 2
        assert call_params[0]["title"] == "Bitcoin Breaks $30k"
        assert call_params[0]["source"] == "decrypt"
        assert call_params[0]["url"] == "https://example.com/article-1"
        assert call_params[0]["published_at"] == _TS_BASE
        assert call_params[0]["sentiment_score"] == pytest.approx(0.75)
        assert call_params[0]["reliability_score"] == pytest.approx(0.9)
        # keywords is serialised as a JSON-compatible string
        assert "bitcoin" in call_params[0]["keywords"]

    # ------------------------------------------------------------------
    # fetch_ohlcv_for_indicators
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_fetch_ohlcv_for_indicators(self) -> None:
        """Loader passes symbol, timeframe, limit to the query and reverses order."""
        # The DB returns rows newest-first; the loader should reverse to oldest-first.
        raw_rows = [
            {
                "timestamp": _TS_LATER,
                "price_open": 29500.0,
                "price_high": 30000.0,
                "price_low": 29300.0,
                "price_close": 29800.0,
                "volume_24h": 9000.0,
            },
            {
                "timestamp": _TS_BASE,
                "price_open": 29000.0,
                "price_high": 29500.0,
                "price_low": 28800.0,
                "price_close": 29200.0,
                "volume_24h": 12345.0,
            },
        ]

        mappings_mock = MagicMock()
        mappings_mock.all.return_value = raw_rows

        result_mock = MagicMock()
        result_mock.mappings.return_value = mappings_mock

        session_mock = AsyncMock()
        session_mock.execute = AsyncMock(return_value=result_mock)

        session_cm = AsyncMock()
        session_cm.__aenter__ = AsyncMock(return_value=session_mock)
        session_cm.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "src.etl.loaders.timescaledb.async_session_factory",
            return_value=session_cm,
        ):
            from src.etl.loaders.timescaledb import fetch_ohlcv_for_indicators

            rows = await fetch_ohlcv_for_indicators("BTCUSDT", "1h", limit=200)

        # Verify query parameters
        call_params = session_mock.execute.call_args.args[1]
        assert call_params["symbol"] == "BTCUSDT"
        assert call_params["timeframe"] == "1h"
        assert call_params["limit"] == 200

        # Rows must be returned in chronological order (oldest first)
        assert len(rows) == 2
        assert rows[0]["timestamp"] == _TS_BASE
        assert rows[1]["timestamp"] == _TS_LATER
