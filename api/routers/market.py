from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, List

from api.dependencies import get_db
from api.schemas.market import (
    TopCryptoSnapshotResponse,
    TopCryptoResponse,
    GlobalMarketResponse,
    DominanceItem,
    TickerResponse,
)
from src.models.top_crypto_snapshot import TopCryptoSnapshot
from src.models.top_crypto import TopCrypto
from src.models.global_snapshot import GlobalMarketSnapshot
from src.models.global_market_cap import GlobalMarketCap
from src.models.global_market_volume import GlobalMarketVolume
from src.models.global_market_dominance import GlobalMarketDominance
from src.models.ticker import TickerSnapshot

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/top", response_model=TopCryptoSnapshotResponse)
def get_top_cryptos(
    limit: int = Query(default=20, ge=1, le=100),
    currency: str = "usd",
    db: Session = Depends(get_db),
):
    snapshot = (
        db.query(TopCryptoSnapshot)
        .filter(func.lower(TopCryptoSnapshot.vs_currency) == currency.lower())
        .order_by(TopCryptoSnapshot.snapshot_time.desc())
        .first()
    )
    if not snapshot:
        raise HTTPException(status_code=404, detail="Aucun snapshot disponible")

    cryptos = (
        db.query(TopCrypto)
        .filter(TopCrypto.snapshot_id == snapshot.id)
        .order_by(TopCrypto.rank)
        .limit(limit)
        .all()
    )

    return TopCryptoSnapshotResponse(
        snapshot_time=snapshot.snapshot_time,
        vs_currency=snapshot.vs_currency,
        cryptos=[TopCryptoResponse.model_validate(c) for c in cryptos],
    )


@router.get("/global", response_model=GlobalMarketResponse)
def get_global_market(db: Session = Depends(get_db)):
    snapshot = (
        db.query(GlobalMarketSnapshot)
        .order_by(GlobalMarketSnapshot.timestamp.desc())
        .first()
    )
    if not snapshot:
        raise HTTPException(status_code=404, detail="Aucun snapshot disponible")

    cap_usd = (
        db.query(GlobalMarketCap.value)
        .filter(
            GlobalMarketCap.snapshot_id == snapshot.id,
            func.lower(GlobalMarketCap.currency) == "usd",
        )
        .scalar()
    )

    volume_usd = (
        db.query(GlobalMarketVolume.value)
        .filter(
            GlobalMarketVolume.snapshot_id == snapshot.id,
            func.lower(GlobalMarketVolume.currency) == "usd",
        )
        .scalar()
    )

    dominance_rows = (
        db.query(GlobalMarketDominance)
        .filter(GlobalMarketDominance.snapshot_id == snapshot.id)
        .order_by(GlobalMarketDominance.percentage.desc())
        .limit(10)
        .all()
    )

    return GlobalMarketResponse(
        snapshot_time=snapshot.timestamp,
        active_cryptocurrencies=snapshot.active_cryptocurrencies,
        markets=snapshot.markets,
        market_cap_change_24h=snapshot.market_cap_change_24h,
        volume_change_24h=snapshot.volume_change_24h,
        market_cap_usd=cap_usd,
        volume_usd=volume_usd,
        dominance=[DominanceItem(asset=r.asset, percentage=r.percentage) for r in dominance_rows],
    )


@router.get("/ticker", response_model=List[TickerResponse])
def get_ticker(
    symbol: Optional[str] = None,
    exchange: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    query = db.query(TickerSnapshot)

    if symbol:
        query = query.filter(TickerSnapshot.symbol == symbol.upper())
    if exchange:
        query = query.filter(TickerSnapshot.exchange == exchange.lower())

    return query.order_by(TickerSnapshot.snapshot_time.desc()).limit(limit).all()
