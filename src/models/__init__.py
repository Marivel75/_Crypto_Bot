"""
Module d'export des modèles de données.
"""

from src.models.ohlcv import OHLCV
from src.models.ohlcv import Base as OHLCVBase
from src.models.ticker import Base as TickerBase
from src.models.ticker import TickerSnapshot

# Exporter les bases et modèles pour une utilisation simplifiée
__all__ = ["OHLCVBase", "OHLCV", "TickerBase", "TickerSnapshot"]
