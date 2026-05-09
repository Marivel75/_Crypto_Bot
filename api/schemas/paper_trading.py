from pydantic import BaseModel, ConfigDict, field_validator
from typing import Optional, List
from datetime import datetime


class PortfolioCreate(BaseModel):
    name: str
    initial_capital: float

    @field_validator("initial_capital")
    @classmethod
    def capital_must_be_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Le capital initial doit être positif")
        return v


class PortfolioResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    initial_capital: float
    cash: float
    created_at: datetime


class OrderCreate(BaseModel):
    portfolio_id: str
    symbol: str
    quantity: Optional[float] = None
    amount_usdt: Optional[float] = None
    signal_source: str = "manual"
    signal_score: Optional[float] = None

    @field_validator("symbol")
    @classmethod
    def symbol_uppercase(cls, v: str) -> str:
        return v.upper()


class TradeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    portfolio_id: str
    symbol: str
    side: str
    quantity: float
    entry_price: float
    entry_time: datetime
    exit_price: Optional[float] = None
    exit_time: Optional[datetime] = None
    status: str
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None
    signal_source: str
    signal_score: Optional[float] = None
    created_at: datetime


class OpenPositionOut(BaseModel):
    id: str
    symbol: str
    quantity: float
    entry_price: float
    current_price: float
    pnl_latent: float
    pnl_latent_pct: float
    signal_source: str
    entry_time: datetime


class ClosedTradeOut(BaseModel):
    id: str
    symbol: str
    quantity: float
    entry_price: float
    exit_price: Optional[float]
    pnl: Optional[float]
    pnl_pct: Optional[float]
    signal_source: str
    entry_time: datetime
    exit_time: Optional[datetime]


class PortfolioMetrics(BaseModel):
    total_capital: float
    total_realized_pnl: float
    latent_pnl: float
    win_rate: float
    total_closed_trades: int
    total_open_trades: int
    best_trade_pnl: Optional[float]
    worst_trade_pnl: Optional[float]


class PortfolioSummary(BaseModel):
    portfolio: PortfolioResponse
    metrics: PortfolioMetrics
    open_positions: List[OpenPositionOut]
    closed_trades: List[ClosedTradeOut]
