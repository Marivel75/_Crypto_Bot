"""Model inference — load from MLflow and predict signal direction + confidence."""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

import mlflow
import mlflow.pyfunc
import numpy as np
import pandas as pd

from src.shared.config import settings
from src.shared.constants import SIGNAL_CONFIDENCE_THRESHOLD

logger = logging.getLogger(__name__)

# Minimum probability returned by the fallback rule-based predictor.
_RULE_CONFIDENCE_BASE = Decimal("0.55")


class ModelPredictor:
    """Load an MLflow model and produce trading direction predictions.

    Falls back to a rule-based heuristic when no model is available or
    when the model fails to load.

    Args:
        model_uri: MLflow model URI, e.g.
            ``"models:/my_experiment/Production"`` or
            ``"runs:/<run_id>/model"``.
    """

    def __init__(self, model_uri: str) -> None:
        self._model_uri = model_uri
        self._model: Any = None
        mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
        self._load_model()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _load_model(self) -> None:
        """Attempt to load the model from MLflow; silently fall back on error."""
        try:
            self._model = mlflow.pyfunc.load_model(self._model_uri)
            logger.info("Model loaded from MLflow URI: %s", self._model_uri)
        except Exception as exc:
            logger.warning(
                "Could not load model from %s — rule-based fallback active: %s",
                self._model_uri,
                exc,
            )
            self._model = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def predict(self, features: pd.DataFrame) -> list[dict[str, Any]]:
        """Predict trading direction and confidence for each row in features.

        Args:
            features: DataFrame where each row is one prediction request.
                      Columns must match the training feature set.

        Returns:
            List of dicts, one per input row::

                {
                    "direction": "BUY" | "SELL",
                    "confidence": float,  # 0.0–1.0
                    "source": "ml" | "rules",
                }
        """
        if features.empty:
            return []

        if self._model is not None:
            return self._predict_ml(features)
        return self._predict_rules(features)

    # ------------------------------------------------------------------
    # ML path
    # ------------------------------------------------------------------

    def _predict_ml(self, features: pd.DataFrame) -> list[dict[str, Any]]:
        if self._model is None:
            raise RuntimeError("ML model is not loaded; call load() before predict.")  # narrowing for type checker

        try:
            raw = self._model.predict(features)
        except Exception as exc:
            logger.error("ML model inference failed — falling back to rules: %s", exc)
            return self._predict_rules(features)

        results: list[dict[str, Any]] = []

        # raw may be probabilities (shape N×2) or binary labels (shape N,)
        arr = np.asarray(raw)
        probas_buy = arr[:, 1] if arr.ndim == 2 and arr.shape[1] == 2 else arr.astype(float)

        for prob in probas_buy:
            direction = "BUY" if prob >= 0.5 else "SELL"
            confidence = float(prob) if direction == "BUY" else float(1.0 - prob)
            results.append({"direction": direction, "confidence": confidence, "source": "ml"})

        logger.debug("ML predictions: %d rows", len(results))
        return results

    # ------------------------------------------------------------------
    # Rule-based fallback
    # ------------------------------------------------------------------

    def _predict_rules(self, features: pd.DataFrame) -> list[dict[str, Any]]:
        """Simple heuristic fallback using RSI and Bollinger position.

        Emits BUY when RSI is oversold (<40 on average across timeframes)
        and price is below the Bollinger middle band.  Emits SELL when RSI
        is overbought (>65) and price is above the band.  Otherwise HOLD is
        represented as a low-confidence SELL to stay below the emission
        threshold.

        Args:
            features: Feature DataFrame.

        Returns:
            List of prediction dicts with ``source="rules"``.
        """
        results: list[dict[str, Any]] = []

        rsi_cols = [c for c in features.columns if c.startswith("rsi_")]
        boll_cols = [c for c in features.columns if c.startswith("boll_pos_")]

        for _, row in features.iterrows():
            rsi_vals = row[rsi_cols].dropna()
            boll_vals = row[boll_cols].dropna()

            avg_rsi = float(rsi_vals.mean()) if not rsi_vals.empty else 50.0
            avg_boll = float(boll_vals.mean()) if not boll_vals.empty else 0.0

            if avg_rsi < 40 and avg_boll < 0:
                direction = "BUY"
                confidence = min(0.75, 0.55 + (40 - avg_rsi) / 100)
            elif avg_rsi > 65 and avg_boll > 0:
                direction = "SELL"
                confidence = min(0.75, 0.55 + (avg_rsi - 65) / 100)
            else:
                direction = "SELL"
                confidence = 0.40  # deliberately below threshold — won't be emitted

            results.append({"direction": direction, "confidence": confidence, "source": "rules"})

        logger.debug("Rule-based predictions: %d rows", len(results))
        return results

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    @property
    def is_ml_active(self) -> bool:
        """Return True if the ML model is loaded (not using the fallback)."""
        return self._model is not None

    def confidence_threshold(self) -> Decimal:
        """Return the project-wide signal confidence emission threshold."""
        return SIGNAL_CONFIDENCE_THRESHOLD
