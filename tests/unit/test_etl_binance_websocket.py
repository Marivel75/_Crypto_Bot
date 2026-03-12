"""Comprehensive unit tests for Binance WebSocket collector.

All WebSocket interactions are mocked via unittest.mock. No real network calls.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.etl.collectors.binance_websocket import BinanceWebSocketCollector
from src.shared.exceptions import ExternalAPIError
from src.shared.models.crypto import OHLCVRecord

logger = logging.getLogger(__name__)

# Fixed timestamp for deterministic testing (never datetime.now())
FIXED_TS = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
FIXED_TS_MS = int(FIXED_TS.timestamp() * 1000)


class TestBinanceWebSocketCollector:
    """Unit tests for BinanceWebSocketCollector."""

    def test_init_default_params(self) -> None:
        """Initialization with defaults sets priority symbols and 1m/5m timeframes."""
        collector = BinanceWebSocketCollector()
        assert len(collector.symbols) > 0  # Should include BTCUSDT, ETHUSDT, etc.
        assert "BTCUSDT" in collector.symbols or "BTC" in str(collector.symbols)
        assert collector.timeframes == ["1m", "5m"]

    def test_init_custom_params(self) -> None:
        """Initialization with custom symbols and timeframes."""
        symbols = ["BTCUSDT", "ETHUSDT"]
        timeframes = ["1h", "4h"]
        collector = BinanceWebSocketCollector(symbols=symbols, timeframes=timeframes)
        assert collector.symbols == symbols
        assert collector.timeframes == timeframes

    async def test_context_manager(self) -> None:
        """Context manager properly initializes and cleans up."""
        async with BinanceWebSocketCollector() as collector:
            assert isinstance(collector, BinanceWebSocketCollector)
        # After exit, resources should be cleaned (no exceptions)

    @pytest.mark.asyncio
    async def test_close_idempotent(self) -> None:
        """Calling close() multiple times does not raise."""
        collector = BinanceWebSocketCollector()
        await collector.close()
        await collector.close()  # Should not error

    def test_parse_kline_message_valid_closed_candle(self) -> None:
        """A valid kline message with closed candle is parsed into OHLCVRecord."""
        msg = {
            "stream": "btcusdt@kline_1m",
            "data": {
                "e": "kline",
                "E": FIXED_TS_MS + 1000,
                "s": "BTCUSDT",
                "k": {
                    "t": FIXED_TS_MS,
                    "T": FIXED_TS_MS + 60_000,
                    "s": "BTCUSDT",
                    "i": "1m",
                    "f": 100,
                    "L": 200,
                    "o": "50000.00",
                    "h": "51000.00",
                    "l": "49500.00",
                    "c": "50500.00",
                    "v": "123.456",
                    "q": "6234567.89",
                    "x": True,  # Candle closed
                    "Q": "61.728",
                    "B": "0",
                },
            },
        }
        record = BinanceWebSocketCollector._parse_kline_message(msg)
        assert record is not None
        assert isinstance(record, OHLCVRecord)
        assert record.symbol == "BTCUSDT"
        assert record.timeframe == "1m"
        assert record.source == "binance_ws"
        assert record.price_open == Decimal("50000.00")
        assert record.price_high == Decimal("51000.00")
        assert record.price_low == Decimal("49500.00")
        assert record.price_close == Decimal("50500.00")
        assert record.volume_24h == Decimal("123.456")
        assert record.timestamp == FIXED_TS

    def test_parse_kline_message_unclosed_candle_ignored(self) -> None:
        """Unclosed candles (x=false) are ignored and None is returned."""
        msg = {
            "stream": "btcusdt@kline_1m",
            "data": {
                "e": "kline",
                "E": FIXED_TS_MS + 1000,
                "s": "BTCUSDT",
                "k": {
                    "t": FIXED_TS_MS,
                    "T": FIXED_TS_MS + 60_000,
                    "s": "BTCUSDT",
                    "i": "1m",
                    "o": "50000.00",
                    "h": "51000.00",
                    "l": "49500.00",
                    "c": "50500.00",
                    "v": "123.456",
                    "x": False,  # Candle not closed
                },
            },
        }
        record = BinanceWebSocketCollector._parse_kline_message(msg)
        assert record is None

    def test_parse_kline_message_missing_data_field_returns_none(self) -> None:
        """Missing 'data' field in message returns None."""
        msg = {"stream": "btcusdt@kline_1m"}
        record = BinanceWebSocketCollector._parse_kline_message(msg)
        assert record is None

    def test_parse_kline_message_missing_kline_field_returns_none(self) -> None:
        """Missing 'k' (kline) field in data returns None."""
        msg = {
            "stream": "btcusdt@kline_1m",
            "data": {
                "e": "kline",
                "E": FIXED_TS_MS,
                "s": "BTCUSDT",
                # No 'k' field
            },
        }
        record = BinanceWebSocketCollector._parse_kline_message(msg)
        assert record is None

    def test_parse_kline_message_malformed_price_returns_none(self) -> None:
        """Unparseable price values (non-numeric) are handled gracefully."""
        msg = {
            "stream": "btcusdt@kline_1m",
            "data": {
                "e": "kline",
                "E": FIXED_TS_MS + 1000,
                "s": "BTCUSDT",
                "k": {
                    "t": FIXED_TS_MS,
                    "T": FIXED_TS_MS + 60_000,
                    "s": "BTCUSDT",
                    "i": "1m",
                    "o": "NOT_A_NUMBER",  # Invalid
                    "h": "51000.00",
                    "l": "49500.00",
                    "c": "50500.00",
                    "v": "123.456",
                    "x": True,
                },
            },
        }
        record = BinanceWebSocketCollector._parse_kline_message(msg)
        assert record is None

    def test_parse_kline_message_various_timeframes(self) -> None:
        """Different timeframe intervals are parsed correctly."""
        for tf_name in ["1m", "5m", "1h", "4h", "1D"]:
            msg = {
                "stream": f"btcusdt@kline_{tf_name}",
                "data": {
                    "e": "kline",
                    "E": FIXED_TS_MS + 1000,
                    "s": "BTCUSDT",
                    "k": {
                        "t": FIXED_TS_MS,
                        "T": FIXED_TS_MS + 60_000,
                        "s": "BTCUSDT",
                        "i": tf_name,
                        "o": "50000.00",
                        "h": "51000.00",
                        "l": "49500.00",
                        "c": "50500.00",
                        "v": "123.456",
                        "x": True,
                    },
                },
            }
            record = BinanceWebSocketCollector._parse_kline_message(msg)
            assert record is not None
            assert record.timeframe == tf_name

    def test_parse_kline_message_lowercase_symbol_uppercase_output(self) -> None:
        """Lowercase symbols in kline are uppercased in output."""
        msg = {
            "stream": "ethusdt@kline_1m",
            "data": {
                "e": "kline",
                "E": FIXED_TS_MS + 1000,
                "s": "ethusdt",  # Lowercase
                "k": {
                    "t": FIXED_TS_MS,
                    "T": FIXED_TS_MS + 60_000,
                    "s": "ethusdt",
                    "i": "1m",
                    "o": "3000.00",
                    "h": "3100.00",
                    "l": "2900.00",
                    "c": "3050.00",
                    "v": "1000.00",
                    "x": True,
                },
            },
        }
        record = BinanceWebSocketCollector._parse_kline_message(msg)
        assert record is not None
        assert record.symbol == "ETHUSDT"

    def test_parse_kline_message_zero_volume_is_valid(self) -> None:
        """Zero volume is valid (though unusual in practice)."""
        msg = {
            "stream": "btcusdt@kline_1m",
            "data": {
                "e": "kline",
                "E": FIXED_TS_MS + 1000,
                "s": "BTCUSDT",
                "k": {
                    "t": FIXED_TS_MS,
                    "T": FIXED_TS_MS + 60_000,
                    "s": "BTCUSDT",
                    "i": "1m",
                    "o": "50000.00",
                    "h": "51000.00",
                    "l": "49500.00",
                    "c": "50500.00",
                    "v": "0.00",  # Zero volume
                    "x": True,
                },
            },
        }
        record = BinanceWebSocketCollector._parse_kline_message(msg)
        assert record is not None
        assert record.volume_24h == Decimal("0.00")

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession.ws_connect")
    async def test_connect_success(self, mock_ws_connect: AsyncMock) -> None:
        """Successful connection establishes WebSocket."""
        mock_ws = MagicMock()
        mock_ws_connect.return_value = mock_ws

        collector = BinanceWebSocketCollector(symbols=["BTCUSDT"], timeframes=["1m"])
        await collector.connect()

        assert collector._ws is mock_ws
        mock_ws_connect.assert_called_once()

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession.ws_connect")
    async def test_connect_failure_raises_external_api_error(self, mock_ws_connect: AsyncMock) -> None:
        """Connection failure raises ExternalAPIError."""
        mock_ws_connect.side_effect = RuntimeError("Connection refused")

        collector = BinanceWebSocketCollector()
        with pytest.raises(ExternalAPIError):
            await collector.connect()

    @pytest.mark.asyncio
    async def test_stream_with_closed_messages(self) -> None:
        """Stream yields records from closed kline messages."""
        mock_ws = AsyncMock()

        # Create two mock messages
        msg1 = MagicMock()
        msg1.type = "text"  # Simulate aiohttp.WSMsgType.TEXT
        msg1.data = json.dumps(
            {
                "stream": "btcusdt@kline_1m",
                "data": {
                    "e": "kline",
                    "E": FIXED_TS_MS + 1000,
                    "s": "BTCUSDT",
                    "k": {
                        "t": FIXED_TS_MS,
                        "T": FIXED_TS_MS + 60_000,
                        "s": "BTCUSDT",
                        "i": "1m",
                        "o": "50000.00",
                        "h": "51000.00",
                        "l": "49500.00",
                        "c": "50500.00",
                        "v": "123.456",
                        "x": True,
                    },
                },
            }
        )

        # Simulate iterator that yields messages then raises StopAsyncIteration
        async def mock_aiter() -> object:
            yield msg1

        mock_ws.__aiter__.return_value = mock_aiter()

        collector = BinanceWebSocketCollector()
        collector._ws = mock_ws

        records = []
        async for record in collector.stream():
            records.append(record)
            if len(records) >= 1:  # Stop after one to avoid infinite loop
                break

        assert len(records) == 1
        assert records[0].symbol == "BTCUSDT"
        assert records[0].source == "binance_ws"

    @pytest.mark.asyncio
    async def test_stream_skips_malformed_json(self) -> None:
        """Malformed JSON messages are skipped with a warning."""
        mock_ws = AsyncMock()

        # Create a message with bad JSON
        msg_bad = MagicMock()
        msg_bad.type = "text"
        msg_bad.data = "{ this is not valid json"

        async def mock_aiter() -> object:
            yield msg_bad

        mock_ws.__aiter__.return_value = mock_aiter()

        collector = BinanceWebSocketCollector()
        collector._ws = mock_ws

        records = []
        with pytest.warns(None) as warning_list:
            async for record in collector.stream():
                records.append(record)
                break  # Exit loop after bad message

        # No valid records should be yielded
        assert len(records) == 0
