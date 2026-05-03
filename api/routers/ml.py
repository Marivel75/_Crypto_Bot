"""Endpoints ML : backtesting walk-forward sur données historiques."""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pandas as pd
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from api.dependencies import get_db
from api.schemas.ml import BacktestResponse, BacktestFoldResult, BacktestSummary, BacktestBaseline
from src.models.ohlcv import OHLCV
from src.ml.feature_engineering.feature_builder import FeatureBuilder
from src.ml.models.baseline import BaselineModel
from src.ml.backtesting.backtester import Backtester
from src.ml.mlflow_utils import log_backtest_metrics

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ml", tags=["ml"])

_VALID_MODELS = ("dummy", "logistic_regression", "random_forest", "xgboost")


def _build_backtest_dataframe(rows: list) -> pd.DataFrame:
    """Construit un DataFrame prêt pour le Backtester à partir des lignes OHLCV.

    Applique le FeatureBuilder, construit la target (direction à t+1),
    définit le DatetimeIndex et ajoute price_close.

    Les doublons de timestamp (multi-exchange, fetches multiples) sont dédupliqués
    en gardant la ligne avec le volume le plus élevé — heuristique simple pour
    conserver la bougie la plus représentative.
    """
    df_raw = pd.DataFrame([{
        "timestamp": r.timestamp,
        "open": float(r.open),
        "high": float(r.high),
        "low": float(r.low),
        "close": float(r.close),
        "volume": float(r.volume),
        "symbol": r.symbol,
        "timeframe": r.timeframe,
        "exchange": r.exchange,
    } for r in rows])

    # Déduplication : un seul point par timestamp (volume max = bougie la plus liquide)
    df_raw = (
        df_raw.sort_values("volume", ascending=False)
        .drop_duplicates(subset=["timestamp"])
        .sort_values("timestamp")
        .reset_index(drop=True)
    )

    builder = FeatureBuilder()
    df_feat = builder.build(df_raw)

    # Target : 1 si close(t+1) > close(t), sinon 0
    df_feat["label"] = (df_feat["close"].shift(-1) > df_feat["close"]).astype(int)
    df_feat["price_close"] = df_feat["close"]

    # DatetimeIndex requis par le Backtester
    df_feat["timestamp"] = pd.to_datetime(df_feat["timestamp"])
    df_feat = df_feat.set_index("timestamp").sort_index()

    # Supprimer les colonnes méta et les NaN (warm-up indicateurs + dernière ligne sans target)
    meta = {"open", "high", "low", "close", "volume", "symbol", "timeframe",
            "exchange", "date", "price_range", "price_change", "price_change_pct"}
    df_feat = df_feat.drop(columns=[c for c in meta if c in df_feat.columns])
    df_feat = df_feat.dropna()

    return df_feat


@router.get("/backtest", response_model=BacktestResponse)
def run_backtest(
    symbol: str = Query(..., description="Paire de trading (ex: BTC/USDT)"),
    timeframe: str = Query("1d", description="Timeframe (ex: 1d, 4h)"),
    model_type: str = Query("random_forest", description="dummy | logistic_regression | random_forest | xgboost"),
    train_window: int = Query(180, ge=30, le=730, description="Jours d'entraînement par fold"),
    test_window: int = Query(30, ge=7, le=180, description="Jours de test par fold"),
    db: Session = Depends(get_db),
):
    if model_type not in _VALID_MODELS:
        raise HTTPException(status_code=422, detail=f"model_type doit être parmi {_VALID_MODELS}")

    # Sélectionne l'exchange avec le plus de données pour ce (symbol, timeframe)
    from sqlalchemy import func as sqlfunc
    best_exchange = (
        db.query(OHLCV.exchange, sqlfunc.count(OHLCV.id).label("n"))
        .filter(OHLCV.symbol == symbol.upper(), OHLCV.timeframe == timeframe)
        .group_by(OHLCV.exchange)
        .order_by(sqlfunc.count(OHLCV.id).desc())
        .first()
    )
    if not best_exchange:
        raise HTTPException(
            status_code=404,
            detail=f"Aucune donnée pour {symbol.upper()} / {timeframe}",
        )

    rows = (
        db.query(OHLCV)
        .filter(
            OHLCV.symbol == symbol.upper(),
            OHLCV.timeframe == timeframe,
            OHLCV.exchange == best_exchange.exchange,
        )
        .order_by(OHLCV.timestamp.asc())
        .all()
    )

    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"Aucune donnée pour {symbol.upper()} / {timeframe}",
        )

    try:
        data = _build_backtest_dataframe(rows)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erreur construction features : {exc}")

    try:
        backtester = Backtester(train_window=train_window, test_window=test_window)
        strategy = BaselineModel(model_type=model_type)
        results = backtester.walk_forward(data, strategy)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erreur backtesting : {exc}")

    if results.empty:
        raise HTTPException(
            status_code=422,
            detail="Aucun fold valide — réduisez train_window ou test_window, "
                   "ou collectez plus de données historiques.",
        )

    summary_dict = backtester.compute_metrics(results)
    baseline_dict = backtester.compare_baseline(results, data)

    log_backtest_metrics(
        experiment_name="backtest",
        symbol=symbol.upper(),
        model_version=model_type,
        metrics={
            "accuracy": summary_dict["accuracy"],
            "win_rate": summary_dict["win_rate"],
            "sharpe": summary_dict["sharpe"],
            "profit_factor": float(summary_dict["profit_factor"]),
            "max_drawdown": summary_dict["max_drawdown"],
            "total_pnl": summary_dict["total_pnl"],
            "n_folds": float(summary_dict["n_folds"]),
            "strategy_pnl": baseline_dict["strategy_pnl"],
            "baseline_return": baseline_dict["baseline_return"],
            "excess_return": baseline_dict["excess_return"],
        },
        params={
            "model_type": model_type,
            "timeframe": timeframe,
            "train_window": train_window,
            "test_window": test_window,
            "n_candles": len(data),
        },
    )

    folds = [
        BacktestFoldResult(
            fold=int(row["fold"]),
            train_start=row["train_start"],
            train_end=row["train_end"],
            test_start=row["test_start"],
            test_end=row["test_end"],
            n_train=int(row["n_train"]),
            n_test=int(row["n_test"]),
            accuracy=float(row["accuracy"]),
            win_rate=float(row["win_rate"]),
            pnl=float(row["pnl"]),
            sharpe=float(row["sharpe"]),
            profit_factor=float(row["profit_factor"]),
            max_drawdown=float(row["max_drawdown"]),
        )
        for _, row in results.iterrows()
    ]

    return BacktestResponse(
        symbol=symbol.upper(),
        timeframe=timeframe,
        model_type=model_type,
        train_window=train_window,
        test_window=test_window,
        n_candles=len(data),
        folds=folds,
        summary=BacktestSummary(**summary_dict),
        baseline=BacktestBaseline(**baseline_dict),
    )
