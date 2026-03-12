"""ETL collectors — re-exports for convenient imports."""

from __future__ import annotations

from src.etl.collectors.binance import BinanceCollector
from src.etl.collectors.ccxt_collector import CCXTCollector
from src.etl.collectors.coingecko import CoinGeckoCollector
from src.etl.collectors.fear_greed import FearGreedCollector
from src.etl.collectors.news import NewsCollector

__all__ = [
    "BinanceCollector",
    "CCXTCollector",
    "CoinGeckoCollector",
    "FearGreedCollector",
    "NewsCollector",
]
