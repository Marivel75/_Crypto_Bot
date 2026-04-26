from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime


class TopCryptoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    rank: Optional[int] = None
    crypto_id: str
    symbol: str
    name: str
    price: Optional[float] = None
    market_cap: Optional[float] = None
    volume_24h: Optional[float] = None
    price_change_pct_24h: Optional[float] = None


class TopCryptoSnapshotResponse(BaseModel):
    snapshot_time: datetime
    vs_currency: str
    cryptos: List[TopCryptoResponse]


class DominanceItem(BaseModel):
    asset: str
    percentage: float


class GlobalMarketResponse(BaseModel):
    snapshot_time: datetime
    active_cryptocurrencies: Optional[int] = None
    markets: Optional[int] = None
    market_cap_change_24h: Optional[float] = None
    volume_change_24h: Optional[float] = None
    market_cap_usd: Optional[float] = None
    volume_usd: Optional[float] = None
    dominance: List[DominanceItem]


class TickerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    symbol: str
    exchange: str
    price: Optional[float] = None
    volume_24h: Optional[float] = None
    price_change_24h: Optional[float] = None
    price_change_pct_24h: Optional[float] = None
    high_24h: Optional[float] = None
    low_24h: Optional[float] = None
    snapshot_time: datetime
