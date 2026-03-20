"""CCXT unified fallback collector — multi-exchange OHLCV fetcher."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

UTC = timezone.utc
from decimal import Decimal

import ccxt.async_support as ccxt_async  # type: ignore[import-untyped]

from src.shared.exceptions import ExternalAPIError
from src.shared.models.crypto import OHLCVRecord
from src.shared.utils import with_retry

logger = logging.getLogger(__name__)

_TIMEFRAME_MAP: dict[str, str] = {
    "1m": "1m",
    "5m": "5m",
    "1h": "1h",
    "2h": "2h",
    "4h": "4h",
    "1D": "1d",
    "1W": "1w",
    "1M": "1M",
}


class CCXTCollector:
    """Async OHLCV collector using CCXT as a fallback for Binance.

    Defaults to the Binance exchange via CCXT, but can target any
    CCXT-supported exchange by passing ``exchange_id``.

    Uses the same ``OHLCVRecord`` output format as ``BinanceCollector``
    so the two are interchangeable.
    """

    def __init__(self, exchange_id: str = "binance") -> None:
        self._exchange: ccxt_async.Exchange = getattr(ccxt_async, exchange_id)({"enableRateLimit": True})

    async def close(self) -> None:
        """Close the underlying CCXT exchange connection."""
        await self._exchange.close()

    async def __aenter__(self) -> CCXTCollector:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.close()

    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 500,
    ) -> list[OHLCVRecord]:
        """Fetch OHLCV candles via CCXT.

        Args:
            symbol: Trading pair in Binance format (e.g. ``BTCUSDT``).
                    Automatically converted to CCXT format (``BTC/USDT``).
            timeframe: Internal timeframe label, e.g. ``"1h"``, ``"4h"``.
            limit: Number of candles to retrieve.

        Returns:
            List of ``OHLCVRecord`` instances ordered oldest-first.
        """
        ccxt_tf = _TIMEFRAME_MAP.get(timeframe)
        if ccxt_tf is None:
            raise ValueError(f"Unsupported timeframe '{timeframe}'. Valid: {list(_TIMEFRAME_MAP)}")

        ccxt_symbol = self._to_ccxt_symbol(symbol)
        logger.info(
            "Fetching CCXT OHLCV: exchange=%s symbol=%s timeframe=%s limit=%d",
            self._exchange.id,
            ccxt_symbol,
            ccxt_tf,
            limit,
        )

        raw: list[list[float]] = await with_retry(
            lambda: self._exchange.fetch_ohlcv(ccxt_symbol, ccxt_tf, limit=limit),
            max_attempts=3,
            base_delay=2.0,
            exceptions=(ccxt_async.NetworkError, ccxt_async.ExchangeError),
        )

        records: list[OHLCVRecord] = []
        for i, candle in enumerate(raw):
            try:
                records.append(self._parse_candle(candle, symbol, timeframe))
            except (ValueError, TypeError, IndexError) as exc:
                logger.warning("Skipping malformed CCXT candle %d for %s: %s", i, symbol, exc)

        logger.info("CCXT OHLCV collected: symbol=%s records=%d", symbol, len(records))
        return records

    @staticmethod
    def _to_ccxt_symbol(binance_symbol: str) -> str:
        """Convert ``BTCUSDT`` to ``BTC/USDT``."""
        for quote in ("USDT", "USDC", "BUSD", "BTC", "ETH", "BNB"):
            if binance_symbol.endswith(quote):
                base = binance_symbol[: -len(quote)]
                return f"{base}/{quote}"
        raise ExternalAPIError(f"Cannot convert symbol '{binance_symbol}' to CCXT format")

    @staticmethod
    def _parse_candle(candle: list[float], symbol: str, timeframe: str) -> OHLCVRecord:
        """Parse a CCXT candle ``[timestamp, O, H, L, C, V]`` into an OHLCVRecord."""
        timestamp = datetime.fromtimestamp(candle[0] / 1000, tz=UTC)
        return OHLCVRecord(
            symbol=symbol,
            price_open=Decimal(str(candle[1])),
            price_high=Decimal(str(candle[2])),
            price_low=Decimal(str(candle[3])),
            price_close=Decimal(str(candle[4])),
            volume_24h=Decimal(str(candle[5])),
            market_cap=None,
            timestamp=timestamp,
            source="ccxt",
            timeframe=timeframe,
        )
