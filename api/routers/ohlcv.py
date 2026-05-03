from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, List
from datetime import datetime

from api.dependencies import get_db
from api.schemas.ohlcv import OHLCVResponse, SymbolInfo
from src.models.ohlcv import OHLCV

router = APIRouter(prefix="/ohlcv", tags=["ohlcv"])


@router.get("", response_model=List[OHLCVResponse])
def get_ohlcv(
    symbol: Optional[str] = None,
    timeframe: Optional[str] = None,
    exchange: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    query = db.query(OHLCV)

    if symbol:
        query = query.filter(OHLCV.symbol == symbol.upper())
    if timeframe:
        query = query.filter(OHLCV.timeframe == timeframe)
    if exchange:
        query = query.filter(OHLCV.exchange == exchange.lower())
    if start_date:
        query = query.filter(OHLCV.timestamp >= start_date)
    if end_date:
        query = query.filter(OHLCV.timestamp <= end_date)

    return query.order_by(OHLCV.timestamp.desc()).limit(limit).all()


@router.get("/symbols", response_model=List[SymbolInfo])
def get_symbols(
    exchange: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(
        OHLCV.symbol,
        OHLCV.exchange,
        OHLCV.timeframe,
        func.count(OHLCV.id).label("count"),
        func.max(OHLCV.timestamp).label("latest_timestamp"),
    ).group_by(OHLCV.symbol, OHLCV.exchange, OHLCV.timeframe)

    if exchange:
        query = query.filter(OHLCV.exchange == exchange.lower())

    rows = query.order_by(OHLCV.symbol).all()
    return [
        SymbolInfo(
            symbol=r.symbol,
            exchange=r.exchange,
            timeframe=r.timeframe,
            count=r.count,
            latest_timestamp=r.latest_timestamp,
        )
        for r in rows
    ]


@router.get("/distinct-count")
def get_distinct_count(
    symbol: str = Query(..., description="Paire de trading (ex: BTC/USDT)"),
    timeframe: str = Query(..., description="Timeframe (ex: 1d)"),
    db: Session = Depends(get_db),
):
    """Retourne le nombre de timestamps distincts par exchange pour (symbol, timeframe).

    Utile pour estimer le nombre de bougies uniques disponibles pour le ML,
    indépendamment des doublons accumulés par des fetches successifs.
    """
    rows = (
        db.query(
            OHLCV.exchange,
            func.count(func.distinct(OHLCV.timestamp)).label("distinct_count"),
        )
        .filter(OHLCV.symbol == symbol.upper(), OHLCV.timeframe == timeframe)
        .group_by(OHLCV.exchange)
        .order_by(func.count(func.distinct(OHLCV.timestamp)).desc())
        .all()
    )
    return [{"exchange": r.exchange, "distinct_count": r.distinct_count} for r in rows]


@router.get("/latest", response_model=List[OHLCVResponse])
def get_latest(
    symbol: Optional[str] = None,
    timeframe: str = "1d",
    exchange: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(OHLCV).filter(OHLCV.timeframe == timeframe)

    if symbol:
        query = query.filter(OHLCV.symbol == symbol.upper())
    if exchange:
        query = query.filter(OHLCV.exchange == exchange.lower())

    return query.order_by(OHLCV.timestamp.desc()).limit(50).all()
