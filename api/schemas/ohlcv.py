from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class OHLCVResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    timestamp: datetime
    symbol: str
    timeframe: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    price_range: Optional[float] = None
    price_change: Optional[float] = None
    price_change_pct: Optional[float] = None
    date: Optional[str] = None
    exchange: str


class SymbolInfo(BaseModel):
    symbol: str
    exchange: str
    timeframe: str
    count: int
    latest_timestamp: Optional[datetime] = None
