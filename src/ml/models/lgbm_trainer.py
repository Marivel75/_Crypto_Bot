"""LightGBM model trainer with MLflow experiment tracking.

Mirrors the XGBoost trainer interface with temporal train/test splits.
NEVER uses random splits for time-series data.
"""

from __future__ import annotations

import logging
from typing import Any

import lightgbm as lgb
import mlflow
import mlflow.lightgbm
import numpy as np
import pandas as pd
from mlflow.models import infer_signature
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score

from src.shared.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Feature column definitions (same as XGBoost trainer)
# ---------------------------------------------------------------------------

_RSI_COLS = ["rsi_1h", "rsi_2h", "rsi_3h", "rsi_4h"]
_BOLL_COLS = ["boll_pos_1h", "boll_pos_4h"]
_TREND_COLS = ["trend_slope_1h", "trend_slope_4h"]
_VOL_COLS = ["volume_ratio_1h", "volume_ratio_4h"]

FEATURE_COLS: list[str] = _RSI_COLS + _BOLL_COLS + _TREND_COLS + _VOL_COLS


class LightGBMTrainer:
    """Train LightGBM classifiers with MLflow tracking.

    Uses the same feature engineering as ModelTrainer (XGBoost) to enable
    direct model comparison.

    Args:
        experiment_name: MLflow experiment to log runs under.
    """

    def __init__(self, experiment_name: str) -> None:
        self._experiment_name = experiment_name
        mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
        mlflow.set_experiment(experiment_name)
        logger.info("LightGBMTrainer initialised — experiment: %s", experiment_name)

    # ------------------------------------------------------------------
    # Feature engineering
    # ------------------------------------------------------------------

    def prepare_features(
        self,
        ohlcv: list[dict[str, Any]],
        indicators: list[dict[str, Any]],
    ) -> pd.DataFrame:
        """Merge OHLCV and indicator rows into a feature DataFrame.

        Identical to ModelTrainer.prepare_features for consistent feature sets.

        Args:
            ohlcv: List of OHLCV dicts (keys: symbol, timestamp, timeframe,
                   price_close, volume_24h, …).
            indicators: List of indicator dicts (keys: symbol, timestamp,
                        timeframe, rsi, price_vs_bollinger, trend_slope, …).

        Returns:
            DataFrame with FEATURE_COLS columns, indexed by timestamp.
            Rows with any NaN are dropped.
        """
        ohlcv_df = pd.DataFrame(ohlcv)
        ind_df = pd.DataFrame(indicators)

        if ohlcv_df.empty or ind_df.empty:
            logger.warning("Empty input to prepare_features — returning empty DataFrame")
            return pd.DataFrame(columns=FEATURE_COLS)

        ohlcv_df["timestamp"] = pd.to_datetime(ohlcv_df["timestamp"])
        ind_df["timestamp"] = pd.to_datetime(ind_df["timestamp"])

        # Pivot indicators to wide format: one row per (symbol, timestamp)
        rows: list[dict[str, Any]] = []
        for ts, group in ind_df.groupby(["symbol", "timestamp"]):
            symbol, timestamp = ts  # type: ignore[misc]
            row: dict[str, Any] = {"symbol": symbol, "timestamp": timestamp}
            for _, r in group.iterrows():
                tf = r.get("timeframe", "")
                row[f"rsi_{tf}"] = float(r.get("rsi") or np.nan)
                row[f"boll_pos_{tf}"] = float(r.get("price_vs_bollinger") or np.nan)
                row[f"trend_slope_{tf}"] = float(r.get("trend_slope") or np.nan)
            rows.append(row)

        wide = pd.DataFrame(rows).set_index("timestamp").sort_index()

        # Volume ratio: current volume / 20-period rolling mean (per symbol, TF)
        for tf in ("1h", "4h"):
            sub = ohlcv_df[ohlcv_df["timeframe"] == tf][["timestamp", "symbol", "volume_24h"]].copy()
            sub = sub.sort_values("timestamp")
            sub["vol_roll"] = sub.groupby("symbol")["volume_24h"].transform(
                lambda s: s.rolling(20, min_periods=1).mean()
            )
            sub["volume_ratio"] = sub["volume_24h"] / sub["vol_roll"].replace(0, np.nan)
            sub = sub.set_index("timestamp")
            wide[f"volume_ratio_{tf}"] = wide.index.map(sub.groupby("timestamp")["volume_ratio"].first())

        # Keep only defined feature columns that exist
        existing = [c for c in FEATURE_COLS if c in wide.columns]
        missing = set(FEATURE_COLS) - set(existing)
        if missing:
            logger.warning("Missing feature columns (filled with NaN): %s", missing)
            for col in missing:
                wide[col] = np.nan

        features = wide[FEATURE_COLS].dropna()
        logger.info("prepare_features: %d rows after NaN drop", len(features))
        return features

    # ------------------------------------------------------------------
    # Temporal split
    # ------------------------------------------------------------------

    def temporal_split(
        self,
        df: pd.DataFrame,
        train_ratio: float = 0.8,
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Split a time-indexed DataFrame into train and test sets temporally.

        Identical to ModelTrainer.temporal_split for consistency.

        Args:
            df: DataFrame with a DatetimeIndex, sorted ascending.
            train_ratio: Fraction of rows used for training. Default 0.8.

        Returns:
            Tuple of (train_df, test_df).

        Raises:
            ValueError: If df is empty or train_ratio is out of (0, 1).
        """
        if df.empty:
            raise ValueError("Cannot split an empty DataFrame")
        if not (0.0 < train_ratio < 1.0):
            raise ValueError(f"train_ratio must be in (0, 1), got {train_ratio}")

        df = df.sort_index()
        cutoff = int(len(df) * train_ratio)
        train, test = df.iloc[:cutoff], df.iloc[cutoff:]
        logger.info(
            "Temporal split: %d train rows / %d test rows (ratio=%.2f)",
            len(train),
            len(test),
            train_ratio,
        )
        return train, test

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def train(
        self,
        features: pd.DataFrame,
        labels: pd.Series,
    ) -> str:
        """Train a LightGBM classifier and log everything to MLflow.

        Args:
            features: Feature DataFrame (rows = samples, cols = FEATURE_COLS).
            labels: Binary target (1 = BUY direction, 0 = SELL/HOLD).

        Returns:
            MLflow run_id of the logged model.

        Raises:
            ValueError: If features and labels have different lengths or
                        if there are fewer than 10 training samples.
        """
        if len(features) != len(labels):
            raise ValueError(f"features length {len(features)} != labels length {len(labels)}")
        if len(features) < 10:
            raise ValueError(f"Need at least 10 samples to train, got {len(features)}")

        train_feat, test_feat = self.temporal_split(features)
        train_labels = labels.loc[train_feat.index]
        test_labels = labels.loc[test_feat.index]

        params: dict[str, Any] = {
            "objective": "binary",
            "metric": "binary_logloss",
            "num_leaves": 31,
            "learning_rate": 0.05,
            "feature_fraction": 0.8,
            "bagging_fraction": 0.8,
            "bagging_freq": 5,
            "max_depth": -1,
            "random_state": 42,
            "verbose": -1,
        }

        # Create LightGBM datasets
        train_data = lgb.Dataset(train_feat, label=train_labels, free_raw_data=False)
        test_data = lgb.Dataset(test_feat, label=test_labels, reference=train_data, free_raw_data=False)

        with mlflow.start_run() as run:
            run_id = run.info.run_id
            mlflow.log_params(params)
            mlflow.log_param("train_samples", len(train_feat))
            mlflow.log_param("test_samples", len(test_feat))
            mlflow.log_param("feature_cols", FEATURE_COLS)

            # Train LightGBM
            model = lgb.train(
                params,
                train_data,
                num_boost_round=300,
                valid_sets=[test_data],
                valid_names=["test"],
                callbacks=[lgb.log_evaluation(period=0)],  # suppress verbose output
            )

            # Predict on test set
            preds_proba = model.predict(test_feat)
            preds = (preds_proba >= 0.5).astype(int)

            metrics: dict[str, float] = {
                "accuracy": float(accuracy_score(test_labels, preds)),
                "f1": float(f1_score(test_labels, preds, zero_division=0)),
                "roc_auc": float(roc_auc_score(test_labels, preds_proba)),
            }
            mlflow.log_metrics(metrics)
            logger.info("Training metrics: %s", metrics)

            # Log model with signature
            signature = infer_signature(train_feat, model.predict(train_feat))
            mlflow.lightgbm.log_model(
                model,
                artifact_path="model",
                signature=signature,
                registered_model_name=self._experiment_name,
            )
            logger.info("LightGBM model logged to MLflow run %s", run_id)

        return str(run_id)
