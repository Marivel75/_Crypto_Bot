"""MLflow utility helpers for experiment tracking and model registry.

All experiment tracking for the ML module is centralised here.  Other
modules import these helpers rather than calling the MLflow API directly,
which keeps MLflow coupling confined to a single file.
"""

from __future__ import annotations

import logging
from typing import Any

import mlflow
import mlflow.sklearn
import mlflow.xgboost
from mlflow.entities import Run
from mlflow.tracking import MlflowClient

from src.shared.config import settings

logger = logging.getLogger(__name__)


def _get_client() -> MlflowClient:
    """Return an initialised :class:`mlflow.tracking.MlflowClient`."""
    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
    return MlflowClient()


def log_experiment(
    experiment_name: str,
    params: dict[str, Any],
    metrics: dict[str, float],
    tags: dict[str, str] | None = None,
    artifact_paths: list[str] | None = None,
) -> str:
    """Start an MLflow run and log parameters, metrics, and optional artifacts.

    Args:
        experiment_name: MLflow experiment name (created if it does not exist).
        params: Hyperparameter dict (string keys, scalar values).
        metrics: Metric dict (string keys, float values).
        tags: Optional string tags to attach to the run.
        artifact_paths: Local file paths to upload as run artifacts.

    Returns:
        The MLflow ``run_id`` of the created run.
    """
    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
    mlflow.set_experiment(experiment_name)

    with mlflow.start_run(tags=tags) as run:
        mlflow.log_params(params)
        mlflow.log_metrics(metrics)

        if artifact_paths:
            for path in artifact_paths:
                try:
                    mlflow.log_artifact(path)
                    logger.debug("Uploaded artifact: %s", path)
                except Exception as exc:
                    logger.warning("Failed to upload artifact %s: %s", path, exc)

        run_id: str = run.info.run_id
        logger.info(
            "MLflow run created: experiment=%r run_id=%s",
            experiment_name,
            run_id,
        )

    return run_id


def register_model(
    run_id: str,
    artifact_path: str,
    model_name: str,
) -> str:
    """Register a model artifact from a completed run into the model registry.

    Args:
        run_id: The MLflow run that produced the model artifact.
        artifact_path: Path of the artifact within the run (e.g. ``"model"``).
        model_name: Registered model name in the registry.

    Returns:
        The version string of the newly registered model version.
    """
    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
    model_uri = f"runs:/{run_id}/{artifact_path}"

    try:
        result = mlflow.register_model(model_uri=model_uri, name=model_name)
        version = result.version
        logger.info(
            "Registered model %r version=%s from run_id=%s",
            model_name,
            version,
            run_id,
        )
        return str(version)
    except Exception as exc:
        logger.error(
            "Failed to register model %r from run %s: %s",
            model_name,
            run_id,
            exc,
        )
        raise


def promote_model_stage(
    model_name: str,
    version: str,
    stage: str,
    archive_existing: bool = True,
) -> None:
    """Transition a model version to a new lifecycle stage.

    Valid stages: ``"Staging"``, ``"Production"``, ``"Archived"``, ``"None"``.

    Args:
        model_name: Registered model name.
        version: Model version to promote.
        stage: Target lifecycle stage.
        archive_existing: When ``True``, all existing model versions currently
            in ``stage`` are transitioned to ``"Archived"`` before promoting
            the new one.  Prevents multiple Production versions.
    """
    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
    client = _get_client()

    if archive_existing:
        existing = client.get_latest_versions(model_name, stages=[stage])
        for mv in existing:
            if mv.version != version:
                client.transition_model_version_stage(
                    name=model_name,
                    version=mv.version,
                    stage="Archived",
                )
                logger.info(
                    "Archived model %r version=%s (replaced by version=%s)",
                    model_name,
                    mv.version,
                    version,
                )

    client.transition_model_version_stage(
        name=model_name,
        version=version,
        stage=stage,
    )
    logger.info(
        "Promoted model %r version=%s to stage=%r",
        model_name,
        version,
        stage,
    )


def get_latest_production_run(model_name: str) -> Run | None:
    """Return the MLflow ``Run`` that produced the current Production model.

    Args:
        model_name: Registered model name.

    Returns:
        The :class:`mlflow.entities.Run` object, or ``None`` if no
        Production version exists.
    """
    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
    client = _get_client()

    versions = client.get_latest_versions(model_name, stages=["Production"])
    if not versions:
        logger.warning("No Production version found for model %r", model_name)
        return None

    mv = versions[0]
    run = client.get_run(mv.run_id)
    logger.debug(
        "Production run for %r: run_id=%s version=%s",
        model_name,
        mv.run_id,
        mv.version,
    )
    return run


def log_backtest_metrics(
    experiment_name: str,
    symbol: str,
    model_version: str,
    metrics: dict[str, float],
    params: dict[str, Any] | None = None,
) -> str:
    """Log walk-forward backtest results as a dedicated MLflow run.

    Args:
        experiment_name: MLflow experiment name.
        symbol: Trading pair being backtested (used as a tag).
        model_version: Model version string (used as a tag).
        metrics: Backtest metric dict (sharpe, win_rate, etc.).
        params: Optional parameter dict (n_folds, purge_periods, etc.).

    Returns:
        The MLflow ``run_id`` of the created run.
    """
    tags = {
        "symbol": symbol,
        "model_version": model_version,
        "run_type": "backtest",
    }
    return log_experiment(
        experiment_name=experiment_name,
        params=params or {},
        metrics=metrics,
        tags=tags,
    )
