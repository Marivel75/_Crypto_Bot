"""Binance WebSocket collector — real-time OHLCV streaming for priority symbols.

This collector connects to Binance's public WebSocket stream and decodes
kline (candlestick) messages in real-time. It supports multiple symbols
multiplexed on a single stream for efficiency.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

import aiohttp  # type: ignore[import-untyped]

from src.shared.exceptions import ExternalAPIError
from src.shared.models.crypto import OHLCVRecord

logger = logging.getLogger(__name__)

_BINANCE_WEBSOCKET_URL = "wss://stream.binance.com:9443/stream"


class BinanceWebSocketCollector:
    """Real-time OHLCV collector via Binance WebSocket streams.

    Multiplexes multiple symbol/timeframe streams into a single connection.
    Use as an async context manager or call close() to clean up resources.

    Attributes:
        symbols: Trading pairs to subscribe to (e.g., ["BTCUSDT", "ETHUSDT"]).
        timeframes: List of interval strings (e.g., ["1m", "5m", "1h"]).
    """

    def __init__(
        self,
        symbols: list[str] | None = None,
        timeframes: list[str] | None = None,
    ) -> None:
        """Initialize the WebSocket collector.

        Args:
            symbols: Trading pairs to stream (default: priority symbols).
            timeframes: Kline intervals to subscribe (default: ["1m", "5m"]).
        """
        from src.shared.constants import PRIORITY_SYMBOLS

        self.symbols = symbols or list(PRIORITY_SYMBOLS)
        self.timeframes = timeframes or ["1m", "5m"]
        self._session: aiohttp.ClientSession | None = None
        self._ws: aiohttp.ClientWebSocketResponse | None = None

    async def __aenter__(self) -> BinanceWebSocketCollector:
        """Enter async context."""
        return self

    async def __aexit__(self, *_: object) -> None:
        """Exit async context and clean up."""
        await self.close()

    async def close(self) -> None:
        """Close WebSocket connection and session."""
        if self._ws:
            await self._ws.close()
        if self._session:
            await self._session.close()

    async def connect(self) -> None:
        """Establish WebSocket connection and subscribe to streams."""
        if self._session is None:
            self._session = aiohttp.ClientSession()

        # Build subscription stream names
        streams = []
        for symbol in self.symbols:
            for tf in self.timeframes:
                # Binance WebSocket stream name: lowercase symbol + kline interval
                stream_name = f"{symbol.lower()}@kline_{tf}"
                streams.append(stream_name)

        # Connect to multiplexed stream
        stream_names = "/".join(streams)
        url = f"{_BINANCE_WEBSOCKET_URL}?streams={stream_names}"

        logger.info("Connecting to Binance WebSocket: %d streams", len(streams))
        try:
            self._ws = await self._session.ws_connect(url, heartbeat=30)
            logger.info("Binance WebSocket connected")
        except Exception as exc:
            logger.error("Failed to connect to Binance WebSocket: %s", exc)
            raise ExternalAPIError(
                f"Binance WebSocket connection failed: {exc}",
                detail=str(exc),
            ) from exc

    async def stream(self) -> AsyncGenerator[OHLCVRecord, None]:
        """Stream OHLCV records from the WebSocket.

        Yields OHLCVRecord instances as they arrive from the server.

        Raises:
            ExternalAPIError: On connection loss or message parsing errors.
        """
        if self._ws is None:
            await self.connect()

        try:
            async for msg in self._ws:  # type: ignore[union-attr]
                if msg.type == aiohttp.WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        record = self._parse_kline_message(data)
                        if record:
                            yield record
                    except (json.JSONDecodeError, KeyError, ValueError) as exc:
                        logger.warning("Failed to parse WebSocket message: %s", exc)
                        continue
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    logger.error("WebSocket error: %s", msg.data)
                    raise ExternalAPIError(
                        f"WebSocket error: {msg.data}",
                        detail=str(msg.data),
                    )
                elif msg.type == aiohttp.WSMsgType.CLOSED:
                    logger.info("WebSocket closed by server")
                    break
        except asyncio.CancelledError:
            logger.info("WebSocket stream cancelled")
            raise
        except Exception as exc:
            logger.error("WebSocket stream error: %s", exc)
            raise ExternalAPIError(
                f"WebSocket stream error: {exc}",
                detail=str(exc),
            ) from exc

    @staticmethod
    def _parse_kline_message(data: dict[str, object]) -> OHLCVRecord | None:
        """Parse a Binance WebSocket kline message into an OHLCVRecord.

        Binance kline message format:
        {
            "stream": "btcusdt@kline_1m",
            "data": {
                "e": "kline",
                "E": 1234567890123,
                "s": "BTCUSDT",
                "k": {
                    "t": 1234567860000,  # Kline start time
                    "T": 1234567919999,  # Kline close time
                    "s": "BTCUSDT",
                    "i": "1m",
                    "f": 100,
                    "L": 200,
                    "o": "50000.00",
                    "h": "51000.00",
                    "l": "49500.00",
                    "c": "50500.00",
                    "v": "1234.56",
                    "q": "61234567.89",
                    "x": false,  # is_closed
                    ...
                }
            }
        }

        Returns:
            OHLCVRecord if message is valid and kline is closed, None otherwise.
        """
        try:
            stream_data = data.get("data", {})
            if not isinstance(stream_data, dict):
                return None

            kline = stream_data.get("k", {})
            if not isinstance(kline, dict):
                return None

            # Only process closed candles (x=true)
            if not kline.get("x", False):
                return None

            symbol = str(kline.get("s", "")).upper()
            timeframe = str(kline.get("i", ""))
            open_time_ms = int(float(kline.get("t", 0)))  # type: ignore[arg-type]
            timestamp = datetime.fromtimestamp(open_time_ms / 1000, tz=timezone.utc)

            # Parse prices with explicit Decimal validation
            try:
                price_open = Decimal(str(kline.get("o", "0")))
                price_high = Decimal(str(kline.get("h", "0")))
                price_low = Decimal(str(kline.get("l", "0")))
                price_close = Decimal(str(kline.get("c", "0")))
                volume_24h = Decimal(str(kline.get("v", "0")))
            except (ValueError, TypeError, InvalidOperation):
                # Malformed price values
                return None

            return OHLCVRecord(
                symbol=symbol,
                price_open=price_open,
                price_high=price_high,
                price_low=price_low,
                price_close=price_close,
                volume_24h=volume_24h,
                market_cap=None,
                timestamp=timestamp,
                source="binance_ws",
                timeframe=timeframe,
            )
        except (KeyError, ValueError, TypeError) as exc:
            logger.warning("Failed to parse kline message: %s", exc)
            return None
