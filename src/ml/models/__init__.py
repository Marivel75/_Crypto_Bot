"""ML model training and inference sub-package.

Heavy dependencies (mlflow, xgboost) are imported lazily — only
``Backtester`` is available at import time without optional extras.
"""

from __future__ import annotations

from src.ml.models.backtester import Backtester

# Expose stable public aliases used by external callers.
WalkForwardBacktester = Backtester


def __getattr__(name: str) -> type:
    """Lazily import heavy ML dependencies on attribute access.

    Args:
        name: Attribute name requested by the caller.

    Returns:
        The requested class (ModelPredictor or ModelTrainer).

    Raises:
        AttributeError: If ``name`` is not a recognised lazy export.
    """
    if name in ("ModelPredictor", "Predictor"):
        from src.ml.models.predictor import ModelPredictor

        return ModelPredictor
    if name == "ModelTrainer":
        from src.ml.models.trainer import ModelTrainer

        return ModelTrainer
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "Backtester",
    "ModelPredictor",
    "ModelTrainer",
    "Predictor",
    "WalkForwardBacktester",
]
