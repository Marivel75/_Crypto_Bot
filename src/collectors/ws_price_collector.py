"""Collecteur de prix temps réel via WebSocket Binance (miniTicker)."""

import asyncio
import json
import threading
from typing import List

import websockets

from logger_settings import logger
from src.services.live_price_cache import live_price_cache

_BINANCE_WS = "wss://stream.binance.com:9443/stream"
_RECONNECT_DELAY = 5   # secondes entre deux tentatives
_PING_INTERVAL = 20    # keepalive Binance


def _to_stream(symbol: str) -> str:
    """'BTC/USDT' → 'btcusdt@miniTicker'"""
    return symbol.replace("/", "").lower() + "@miniTicker"


def _build_symbol_map(symbols: List[str]) -> dict[str, str]:
    """{'BTCUSDT': 'BTC/USDT', ...}"""
    return {s.replace("/", "").upper(): s for s in symbols}


async def _watch(symbols: List[str]) -> None:
    symbol_map = _build_symbol_map(symbols)
    streams = "/".join(_to_stream(s) for s in symbols)
    url = f"{_BINANCE_WS}?streams={streams}"

    while True:
        try:
            async with websockets.connect(url, ping_interval=_PING_INTERVAL) as ws:
                logger.info(f"WS Binance connecté — {len(symbols)} symboles suivis")
                async for raw_msg in ws:
                    try:
                        msg = json.loads(raw_msg)
                        payload = msg.get("data", {})
                        binance_sym = payload.get("s", "")   # ex: "BTCUSDT"
                        price_str = payload.get("c")          # close/current price
                        if binance_sym and price_str:
                            price = float(price_str)
                            symbol = symbol_map.get(binance_sym)
                            if symbol and price > 0:
                                live_price_cache.update(symbol, price)
                    except (KeyError, ValueError):
                        pass  # message malformé, on passe
        except asyncio.CancelledError:
            logger.info("WS price collector arrêté")
            return
        except Exception as exc:
            logger.warning(f"WS déconnecté ({exc}) — reconnexion dans {_RECONNECT_DELAY}s")
            await asyncio.sleep(_RECONNECT_DELAY)


def start_ws_collector(symbols: List[str]) -> threading.Thread:
    """Démarre le collecteur WebSocket dans un thread daemon.

    Le thread survit à l'appel et se reconnecte automatiquement en cas de coupure.
    """
    if not symbols:
        logger.warning("WS price collector : aucun symbole configuré, démarrage ignoré")
        return

    def _run() -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(_watch(symbols))
        finally:
            loop.close()

    thread = threading.Thread(target=_run, daemon=True, name="ws-price-collector")
    thread.start()
    logger.info(f"WS price collector démarré — symboles : {symbols}")
    return thread
