import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pandas as pd
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List

from api.dependencies import get_db
from api.schemas.signals import SignalResponse
from src.models.ohlcv import OHLCV
from src.analytics.technical_calculator import TechnicalCalculator
from src.analytics.technical_signals import TechnicalSignals
from src.analytics.signal_scorer import score_candle

router = APIRouter(prefix="/signals", tags=["signals"])

_calc = TechnicalCalculator()


def _safe(series: pd.Series, idx: int):
    val = series.iloc[idx]
    return None if pd.isna(val) else float(val)


@router.get("", response_model=List[SignalResponse])
def get_signals(
    symbol: str = Query(..., description="Paire de trading (ex: BTC/USDT)"),
    timeframe: str = "1d",
    exchange: Optional[str] = None,
    limit: int = Query(default=100, ge=10, le=500),
    db: Session = Depends(get_db),
):
    fetch_limit = limit + 50

    query = (
        db.query(OHLCV)
        .filter(OHLCV.symbol == symbol.upper(), OHLCV.timeframe == timeframe)
    )
    if exchange:
        query = query.filter(OHLCV.exchange == exchange.lower())

    rows = query.order_by(OHLCV.timestamp.desc()).limit(fetch_limit).all()

    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"Aucune donnée pour {symbol.upper()} / {timeframe} — vérifiez /ohlcv/symbols",
        )

    # Remettre dans l'ordre chronologique pour les calculs
    rows = list(reversed(rows))

    df = pd.DataFrame(
        [
            {
                "timestamp": r.timestamp,
                "open": r.open,
                "high": r.high,
                "low": r.low,
                "close": r.close,
                "volume": r.volume,
                "symbol": r.symbol,
                "timeframe": r.timeframe,
                "exchange": r.exchange,
            }
            for r in rows
        ]
    )

    sma_20 = _calc.calculate_sma(df, window=20)
    sma_50 = _calc.calculate_sma(df, window=50) if len(df) >= 50 else pd.Series([None] * len(df))
    ema_20 = _calc.calculate_ema(df, window=20)
    rsi_14 = _calc.calculate_rsi(df, window=14)
    macd_df = _calc.calculate_macd(df)
    bb_df = _calc.calculate_bollinger_bands(df)

    # Détection des croisements MACD sur la série complète
    if isinstance(macd_df, pd.DataFrame) and "MACD" in macd_df and "MACD_signal" in macd_df:
        df_cross = TechnicalSignals.macd_cross(macd_df, macd_col="MACD", signal_col="MACD_signal")
        cross_up_series = df_cross["MACD_cross_up"]
        cross_down_series = df_cross["MACD_cross_down"]
    else:
        cross_up_series = pd.Series([False] * len(df))
        cross_down_series = pd.Series([False] * len(df))

    results = []
    # On ne retourne que les `limit` dernières lignes (après warm-up)
    start = max(0, len(df) - limit)
    for i in range(start, len(df)):
        row = df.iloc[i]

        macd_line = _safe(macd_df["MACD"], i) if isinstance(macd_df, pd.DataFrame) and "MACD" in macd_df else None
        macd_signal = _safe(macd_df["MACD_signal"], i) if isinstance(macd_df, pd.DataFrame) and "MACD_signal" in macd_df else None
        macd_hist = _safe(macd_df["MACD_hist"], i) if isinstance(macd_df, pd.DataFrame) and "MACD_hist" in macd_df else None

        bb_upper = _safe(bb_df["BB_upper"], i) if isinstance(bb_df, pd.DataFrame) and "BB_upper" in bb_df else None
        bb_mid = _safe(bb_df["BB_middle"], i) if isinstance(bb_df, pd.DataFrame) and "BB_middle" in bb_df else None
        bb_lower = _safe(bb_df["BB_lower"], i) if isinstance(bb_df, pd.DataFrame) and "BB_lower" in bb_df else None

        sig, score, reasons = score_candle(
            close=_safe(df["close"], i),
            rsi=_safe(rsi_14, i),
            macd_line=macd_line,
            macd_signal_val=macd_signal,
            bb_upper=bb_upper,
            bb_lower=bb_lower,
            sma_20=_safe(sma_20, i),
            sma_50=_safe(sma_50, i),
            macd_cross_up=bool(cross_up_series.iloc[i]),
            macd_cross_down=bool(cross_down_series.iloc[i]),
        )

        results.append(
            SignalResponse(
                timestamp=row["timestamp"],
                symbol=row["symbol"],
                timeframe=row["timeframe"],
                exchange=row["exchange"],
                open=row["open"],
                high=row["high"],
                low=row["low"],
                close=row["close"],
                volume=row["volume"],
                sma_20=_safe(sma_20, i),
                sma_50=_safe(sma_50, i),
                ema_20=_safe(ema_20, i),
                rsi_14=_safe(rsi_14, i),
                macd_line=macd_line,
                macd_signal=macd_signal,
                macd_histogram=macd_hist,
                bb_upper=bb_upper,
                bb_middle=bb_mid,
                bb_lower=bb_lower,
                signal=sig,
                signal_score=score,
                signal_reasons=reasons,
            )
        )

    return results
