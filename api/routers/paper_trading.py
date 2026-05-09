from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from api.dependencies import get_db
from api.schemas.paper_trading import (
    PortfolioCreate,
    PortfolioResponse,
    OrderCreate,
    TradeResponse,
    PortfolioSummary,
    PortfolioMetrics,
    OpenPositionOut,
    ClosedTradeOut,
)
from src.models.paper_trade import PaperPortfolio, PaperTrade
from src.paper_trading.paper_trader import PaperTrader

router = APIRouter(prefix="/paper-trading", tags=["paper-trading"])


@router.post("/portfolios", response_model=PortfolioResponse, status_code=201)
def create_portfolio_endpoint(body: PortfolioCreate, db: Session = Depends(get_db)):
    return PaperTrader(db).create_portfolio(name=body.name, initial_capital=body.initial_capital)


@router.get("/portfolios", response_model=List[PortfolioResponse])
def list_portfolios(db: Session = Depends(get_db)):
    return db.query(PaperPortfolio).order_by(PaperPortfolio.created_at.desc()).all()


@router.get("/portfolios/{portfolio_id}", response_model=PortfolioSummary)
def get_portfolio(portfolio_id: str, db: Session = Depends(get_db)):
    try:
        data = PaperTrader(db).get_portfolio_summary(portfolio_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return PortfolioSummary(
        portfolio=PortfolioResponse(**data["portfolio"]),
        metrics=PortfolioMetrics(**data["metrics"]),
        open_positions=[OpenPositionOut(**p) for p in data["open_positions"]],
        closed_trades=[ClosedTradeOut(**t) for t in data["closed_trades"]],
    )


@router.post("/orders", response_model=TradeResponse, status_code=201)
def place_order(body: OrderCreate, db: Session = Depends(get_db)):
    if body.quantity is None and body.amount_usdt is None:
        raise HTTPException(status_code=422, detail="Fournir quantity ou amount_usdt")
    try:
        trade = PaperTrader(db).open_position(
            portfolio_id=body.portfolio_id,
            symbol=body.symbol,
            quantity=body.quantity,
            amount_usdt=body.amount_usdt,
            signal_source=body.signal_source,
            signal_score=body.signal_score,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return trade


@router.post("/orders/{trade_id}/close", response_model=TradeResponse)
def close_order(trade_id: str, db: Session = Depends(get_db)):
    try:
        trade = PaperTrader(db).close_position(trade_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return trade


@router.get("/orders", response_model=List[TradeResponse])
def list_orders(
    portfolio_id: Optional[str] = None,
    symbol: Optional[str] = None,
    status: Optional[str] = Query(default=None, pattern="^(OPEN|CLOSED)$"),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    q = db.query(PaperTrade)
    if portfolio_id:
        q = q.filter(PaperTrade.portfolio_id == portfolio_id)
    if symbol:
        q = q.filter(PaperTrade.symbol == symbol.upper())
    if status:
        q = q.filter(PaperTrade.status == status)
    return q.order_by(PaperTrade.created_at.desc()).limit(limit).all()
