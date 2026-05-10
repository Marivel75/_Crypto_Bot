"""Cache mémoire thread-safe pour les prix live (WebSocket)."""

import threading
from datetime import datetime
from typing import Optional


class LivePriceCache:
    """Singleton — stocke le dernier prix reçu par symbole."""

    _instance: Optional["LivePriceCache"] = None
    _init_lock = threading.Lock()

    def __new__(cls) -> "LivePriceCache":
        if cls._instance is None:
            with cls._init_lock:
                if cls._instance is None:
                    obj = super().__new__(cls)
                    obj._prices: dict[str, float] = {}
                    obj._timestamps: dict[str, datetime] = {}
                    obj._lock = threading.Lock()
                    cls._instance = obj
        return cls._instance

    def update(self, symbol: str, price: float) -> None:
        with self._lock:
            self._prices[symbol] = price
            self._timestamps[symbol] = datetime.utcnow()

    def get(self, symbol: str) -> Optional[float]:
        return self._prices.get(symbol)

    def get_with_ts(self, symbol: str) -> tuple[Optional[float], Optional[datetime]]:
        return self._prices.get(symbol), self._timestamps.get(symbol)

    def all_prices(self) -> dict[str, float]:
        with self._lock:
            return dict(self._prices)

    def all_with_ts(self) -> dict[str, dict]:
        with self._lock:
            return {
                sym: {"price": self._prices[sym], "updated_at": self._timestamps[sym].isoformat()}
                for sym in self._prices
            }

    @property
    def is_populated(self) -> bool:
        return bool(self._prices)


live_price_cache = LivePriceCache()
