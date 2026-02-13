"""
Module d'export des modèles de données.
"""

from src.models.ohlcv import Base as OHLCVBase, OHLCV
from src.models.ticker import Base as TickerBase, TickerSnapshot
from src.models.market_data_base import MarketDataBase
from src.models.global_snapshot import GlobalMarketSnapshot
from src.models.global_market_cap import GlobalMarketCap
from src.models.global_market_volume import GlobalMarketVolume
from src.models.global_market_dominance import GlobalMarketDominance
from src.models.top_crypto_snapshot import TopCryptoSnapshot
from src.models.top_crypto import TopCrypto
from src.models.crypto_detail_snapshot import CryptoDetailSnapshot
from src.models.crypto_detail import CryptoDetail

# Exporter les bases et modèles pour une utilisation simplifiée
__all__ = [
    "OHLCVBase",
    "OHLCV",
    "TickerBase",
    "TickerSnapshot",
    "MarketDataBase",
    "GlobalMarketSnapshot",
    "GlobalMarketCap",
    "GlobalMarketVolume",
    "GlobalMarketDominance",
    "TopCryptoSnapshot",
    "TopCrypto",
    "CryptoDetailSnapshot",
    "CryptoDetail",
]
