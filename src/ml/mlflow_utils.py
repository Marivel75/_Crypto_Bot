"""MLflow utility helpers for experiment tracking.

Tout le tracking MLflow du projet passe par ce module.
Les autres modules importent ces helpers plutôt que d'appeler l'API MLflow
directement, ce qui garde le couplage MLflow concentré ici.

Si le serveur MLflow est inaccessible, les fonctions loguent un warning
sans lever d'exception (dégradation gracieuse).
"""

from __future__ import annotations

import logging
import os
from typing import Any

import mlflow
import mlflow.sklearn

logger = logging.getLogger(__name__)

MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")


def log_experiment(
    experiment_name: str,
    params: dict[str, Any],
    metrics: dict[str, float],
    tags: dict[str, str] | None = None,
    artifact_paths: list[str] | None = None,
) -> str | None:
    """Lance un run MLflow et logue paramètres, métriques et artefacts optionnels.

    Args:
        experiment_name: Nom de l'expérience MLflow (créée si inexistante).
        params: Hyperparamètres (clés string, valeurs scalaires).
        metrics: Métriques (clés string, valeurs float).
        tags: Tags optionnels attachés au run.
        artifact_paths: Chemins locaux de fichiers à uploader comme artefacts.

    Returns:
        Le ``run_id`` MLflow du run créé, ou None si le tracking a échoué.
    """
    try:
        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        mlflow.set_experiment(experiment_name)

        with mlflow.start_run(tags=tags) as run:
            mlflow.log_params(params)
            mlflow.log_metrics(metrics)

            if artifact_paths:
                for path in artifact_paths:
                    try:
                        mlflow.log_artifact(path)
                    except Exception as exc:
                        logger.warning("Artefact non uploadé %s : %s", path, exc)

            run_id: str = run.info.run_id
            logger.info(
                "MLflow run créé : experiment=%r run_id=%s", experiment_name, run_id
            )
        return run_id

    except Exception as exc:
        logger.warning("MLflow tracking indisponible (non-bloquant) : %s", exc)
        return None


def log_backtest_metrics(
    experiment_name: str,
    symbol: str,
    model_version: str,
    metrics: dict[str, float],
    params: dict[str, Any] | None = None,
) -> str | None:
    """Logue les résultats d'un backtest walk-forward comme run MLflow dédié.

    Args:
        experiment_name: Nom de l'expérience MLflow.
        symbol: Paire tradée (utilisée comme tag).
        model_version: Type de modèle (utilisé comme tag).
        metrics: Métriques du backtest (sharpe, win_rate, total_pnl…).
        params: Paramètres optionnels (n_folds, train_window…).

    Returns:
        Le ``run_id`` du run créé, ou None si le tracking a échoué.
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
