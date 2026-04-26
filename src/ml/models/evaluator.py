"""
Évaluation des modèles baseline : métriques ML et métriques financières.

Deux familles de métriques :
  - ML       : accuracy, precision, recall, F1 (classification standard)
  - Finance  : win rate, profit factor, Sharpe ratio simulé

Le Sharpe ratio simulé est calculé sur des rendements fictifs : on suppose
qu'on prend position de +1 (long) quand le modèle prédit une hausse et de -1
(short) quand il prédit une baisse, puis on multiplie par le rendement réel
observé. Cela mesure si le modèle a une valeur prédictive utilisable.

Usage::

    evaluator = ModelEvaluator()
    results = model.cross_validate(X, y)
    summary = evaluator.evaluate_folds(results)
    evaluator.compare_models({"lr": results_lr, "rf": results_rf})
"""

from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score

from logger_settings import logger


class ModelEvaluator:
    """
    Calcule et agrège les métriques ML et financières sur les folds de validation croisée.

    Les métriques financières nécessitent les probabilités (y_proba) en plus des
    prédictions pour calculer des stratégies à seuil variable, mais les métriques
    de base fonctionnent avec y_pred uniquement.

    Usage::

        evaluator = ModelEvaluator()
        fold_results = model.cross_validate(X, y)
        summary = evaluator.evaluate_folds(fold_results)
        print(summary)
    """

    # ------------------------------------------------------------------
    # API publique
    # ------------------------------------------------------------------

    def evaluate_folds(
        self,
        fold_results: List[Dict[str, Any]],
        returns: Optional[pd.Series] = None,
    ) -> Dict[str, Any]:
        """
        Agrège les métriques sur l'ensemble des folds de cross-validation.

        Args:
            fold_results : Sortie de ``BaselineModel.cross_validate()``.
                           Chaque dict contient : fold, train_size, val_size,
                           accuracy, y_val, y_pred, y_proba.
            returns      : Série des rendements réels (log-returns) alignée sur
                           l'index original. Si None, les métriques financières
                           sont ignorées.

        Returns:
            Dict avec les clés :
                - ``'per_fold'`` : liste de dicts, une par fold
                - ``'mean'``     : moyennes sur tous les folds
                - ``'std'``      : écarts-types sur tous les folds
        """
        per_fold = []

        for fold in fold_results:
            fold_metrics = self._evaluate_single_fold(fold, returns)
            per_fold.append(fold_metrics)
            logger.info(
                f"  Fold {fold['fold']} | "
                f"acc={fold_metrics['accuracy']:.4f} "
                f"f1={fold_metrics['f1']:.4f} "
                f"sharpe={fold_metrics.get('sharpe', float('nan')):.3f}"
            )

        # Agrégation : moyenne et std par métrique
        metric_keys = [k for k in per_fold[0] if k != "fold"]
        mean = {k: float(np.mean([f[k] for f in per_fold])) for k in metric_keys}
        std  = {k: float(np.std([f[k]  for f in per_fold])) for k in metric_keys}

        logger.info(
            f"ModelEvaluator.evaluate_folds : "
            f"accuracy={mean['accuracy']:.4f}±{std['accuracy']:.4f} | "
            f"f1={mean['f1']:.4f}±{std['f1']:.4f} | "
            f"sharpe={mean.get('sharpe', float('nan')):.3f}"
        )

        return {"per_fold": per_fold, "mean": mean, "std": std}

    def compare_models(
        self,
        models_results: Dict[str, List[Dict[str, Any]]],
        returns: Optional[pd.Series] = None,
    ) -> pd.DataFrame:
        """
        Compare plusieurs modèles sur les mêmes folds.

        Args:
            models_results : Dict ``{nom_modèle: fold_results}``
                             où chaque valeur est la sortie de cross_validate().
            returns        : Rendements réels pour les métriques financières.

        Returns:
            DataFrame (un modèle par ligne, une métrique par colonne).
            Colonnes : accuracy, precision, recall, f1, win_rate, profit_factor, sharpe.
        """
        rows = []
        for model_name, fold_results in models_results.items():
            summary = self.evaluate_folds(fold_results, returns)
            row = {"model": model_name}
            row.update(summary["mean"])
            rows.append(row)

        df = pd.DataFrame(rows).set_index("model")
        df = df.round(4)

        logger.info(f"ModelEvaluator.compare_models :\n{df.to_string()}")
        return df

    def print_summary(self, summary: Dict[str, Any], model_name: str = "") -> None:
        """
        Affiche un résumé lisible des métriques moyennes.

        Args:
            summary    : Sortie de ``evaluate_folds()``.
            model_name : Nom optionnel affiché dans le titre.
        """
        title = f"=== {model_name} ===" if model_name else "=== Résultats ==="
        mean = summary["mean"]
        std  = summary["std"]

        lines = [title]
        lines.append(f"  Accuracy       : {mean['accuracy']:.4f} ± {std['accuracy']:.4f}")
        lines.append(f"  Precision      : {mean['precision']:.4f} ± {std['precision']:.4f}")
        lines.append(f"  Recall         : {mean['recall']:.4f} ± {std['recall']:.4f}")
        lines.append(f"  F1-score       : {mean['f1']:.4f} ± {std['f1']:.4f}")

        if "win_rate" in mean:
            lines.append(f"  Win rate       : {mean['win_rate']:.4f} ± {std['win_rate']:.4f}")
        if "profit_factor" in mean:
            pf = mean['profit_factor']
            lines.append(f"  Profit factor  : {pf:.4f} ± {std['profit_factor']:.4f}")
        if "sharpe" in mean:
            lines.append(f"  Sharpe simulé  : {mean['sharpe']:.4f} ± {std['sharpe']:.4f}")

        print("\n".join(lines))

    # ------------------------------------------------------------------
    # Méthodes privées
    # ------------------------------------------------------------------

    def _evaluate_single_fold(
        self,
        fold: Dict[str, Any],
        returns: Optional[pd.Series] = None,
    ) -> Dict[str, float]:
        """
        Calcule toutes les métriques pour un fold donné.

        Args:
            fold    : Dict issu de cross_validate() contenant y_val, y_pred, y_proba.
            returns : Série des rendements réels (index aligné avec y_val).

        Returns:
            Dict de métriques scalaires.
        """
        y_val  = fold["y_val"]
        y_pred = fold["y_pred"]

        metrics: Dict[str, float] = {
            "fold":      fold["fold"],
            "accuracy":  accuracy_score(y_val, y_pred),
            "precision": precision_score(y_val, y_pred, zero_division=0.0),
            "recall":    recall_score(y_val, y_pred, zero_division=0.0),
            "f1":        f1_score(y_val, y_pred, zero_division=0.0),
        }

        # Métriques financières : nécessitent les rendements réels
        if returns is not None:
            fin = self._financial_metrics(y_val, y_pred, returns)
            metrics.update(fin)
        else:
            # Métriques financières simples sans rendements réels
            fin = self._financial_metrics_no_returns(y_val, y_pred, fold["y_proba"])
            metrics.update(fin)

        return metrics

    def _financial_metrics(
        self,
        y_val: pd.Series,
        y_pred: np.ndarray,
        returns: pd.Series,
    ) -> Dict[str, float]:
        """
        Métriques financières avec rendements réels.

        La stratégie simulée : signal = +1 si prédit hausse, -1 si prédit baisse.
        PnL = signal × rendement_réel.

        Args:
            y_val   : Vraies labels (0/1).
            y_pred  : Prédictions du modèle (0/1).
            returns : Rendements log réels, indexés comme y_val.

        Returns:
            Dict avec win_rate, profit_factor, sharpe.
        """
        # Aligne les rendements sur l'index de validation
        r = returns.reindex(y_val.index).fillna(0.0)
        signal = np.where(y_pred == 1, 1.0, -1.0)
        pnl    = signal * r.values

        return self._compute_financial_stats(pnl)

    def _financial_metrics_no_returns(
        self,
        y_val: pd.Series,
        y_pred: np.ndarray,
        y_proba: np.ndarray,
    ) -> Dict[str, float]:
        """
        Métriques financières simulées sans rendements réels.

        On utilise les probabilités prédites comme proxy de rendement espéré :
          - Signal = +1 si prédit hausse, -1 sinon
          - PnL simulé = signal × (2 × y_val - 1)
            (i.e. +1 si correct, -1 si incorrect)

        Cette approche mesure la cohérence directionnelle du modèle.

        Args:
            y_val   : Vraies labels (0/1).
            y_pred  : Prédictions (0/1).
            y_proba : Probabilités (n_samples, 2).

        Returns:
            Dict avec win_rate, profit_factor, sharpe.
        """
        signal     = np.where(y_pred == 1, 1.0, -1.0)
        true_direction = 2 * y_val.values - 1   # +1 hausse, -1 baisse
        pnl        = signal * true_direction

        return self._compute_financial_stats(pnl)

    @staticmethod
    def _compute_financial_stats(pnl: np.ndarray) -> Dict[str, float]:
        """
        Calcule win rate, profit factor et Sharpe à partir d'un vecteur de PnL.

        Args:
            pnl : Array de PnL par trade (peut être positif ou négatif).

        Returns:
            Dict avec win_rate, profit_factor, sharpe.
        """
        wins   = pnl[pnl > 0]
        losses = pnl[pnl < 0]

        win_rate = float(len(wins) / len(pnl)) if len(pnl) > 0 else 0.0

        # Profit factor = somme des gains / |somme des pertes|
        gross_profit = float(wins.sum())   if len(wins)   > 0 else 0.0
        gross_loss   = float(-losses.sum()) if len(losses) > 0 else 1e-9  # évite /0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

        # Sharpe annualisé (hypothèse : 1 trade par bougie, 8760 bougies/an pour 1h)
        pnl_std = float(np.std(pnl))
        if pnl_std > 1e-9:
            sharpe = float(np.mean(pnl) / pnl_std * np.sqrt(8760))
        else:
            sharpe = 0.0

        return {
            "win_rate":      win_rate,
            "profit_factor": profit_factor,
            "sharpe":        sharpe,
        }
