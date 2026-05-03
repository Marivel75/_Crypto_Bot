"""
Modèles baseline pour la prédiction de direction de prix crypto.

Trois niveaux de baseline :
  - Niveau 0 : DummyClassifier (prédit toujours la classe majoritaire) — plancher absolu
  - Niveau 1 : LogisticRegression (modèle linéaire, nécessite un scaling)
  - Niveau 2 : RandomForestClassifier (non-linéaire, robuste, souvent difficile à battre)

Usage::

    model = BaselineModel(model_type='random_forest')
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    results = model.cross_validate(X, y, n_splits=5)
"""

from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

try:
    from xgboost import XGBClassifier
    _XGBOOST_AVAILABLE = True
except ImportError:
    _XGBOOST_AVAILABLE = False

from logger_settings import logger

# Types de modèles disponibles
_MODEL_TYPES = ("dummy", "logistic_regression", "random_forest", "xgboost")


class BaselineModel:
    """
    Wrapper unifié pour les modèles baseline.

    Le scaling (StandardScaler) est intégré dans un Pipeline sklearn pour la
    régression logistique — obligatoire car les features ont des échelles très
    différentes (RSI ∈ [0,100], log_return ∈ [-0.1, 0.1]...).
    Le Random Forest est invariant au scaling mais le Pipeline est quand même
    appliqué par cohérence.

    Args:
        model_type : ``'dummy'`` | ``'logistic_regression'`` | ``'random_forest'``
        random_state : graine pour la reproductibilité (défaut : 42)

    Attributes:
        pipeline : Pipeline sklearn (scaler + modèle) — None avant fit()
        is_fitted : True après un appel à fit()
    """

    def __init__(self, model_type: str = "logistic_regression", random_state: int = 42):
        if model_type not in _MODEL_TYPES:
            raise ValueError(f"model_type doit être parmi {_MODEL_TYPES}. Reçu : '{model_type}'")
        if model_type == "xgboost" and not _XGBOOST_AVAILABLE:
            raise ImportError("xgboost n'est pas installé : pip install xgboost")

        self.model_type = model_type
        self.random_state = random_state
        self.pipeline: Optional[Pipeline] = None
        self.is_fitted = False
        self.feature_names_: List[str] = []

    # ------------------------------------------------------------------
    # API publique
    # ------------------------------------------------------------------

    def fit(self, X: pd.DataFrame, y: pd.Series) -> "BaselineModel":
        """
        Entraîne le modèle.

        Args:
            X : Features (DataFrame sans NaN).
            y : Target binaire (0/1).

        Returns:
            self (pour le chaînage).
        """
        self.feature_names_ = list(X.columns)
        self.pipeline = self._build_pipeline()
        self.pipeline.fit(X, y)
        self.is_fitted = True
        logger.info(
            f"BaselineModel({self.model_type}).fit : {len(X)} lignes, "
            f"{len(self.feature_names_)} features."
        )
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Prédit la classe (0 ou 1)."""
        self._check_fitted()
        return self.pipeline.predict(X)

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """
        Retourne les probabilités de chaque classe.
        Le DummyClassifier supporte predict_proba — pas de cas particulier nécessaire.

        Returns:
            Array de shape (n_samples, 2) : [proba_baisse, proba_hausse]
        """
        self._check_fitted()
        return self.pipeline.predict_proba(X)

    def cross_validate(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        n_splits: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Validation croisée temporelle (TimeSeriesSplit).

        Pour chaque fold, entraîne un modèle frais et évalue sur la validation.
        Retourne les métriques par fold ainsi que les prédictions pour le calcul
        du Sharpe ratio simulé dans ModelEvaluator.

        Args:
            X        : Features complètes (avant split).
            y        : Target complète.
            n_splits : Nombre de folds (défaut : 5).

        Returns:
            Liste de dicts, un par fold::

                {
                    "fold": int,
                    "train_size": int,
                    "val_size": int,
                    "accuracy": float,
                    "y_val": pd.Series,
                    "y_pred": np.ndarray,
                    "y_proba": np.ndarray,
                }
        """
        tscv = TimeSeriesSplit(n_splits=n_splits)
        results = []

        for fold_idx, (train_idx, val_idx) in enumerate(tscv.split(X)):
            X_tr, X_val = X.iloc[train_idx], X.iloc[val_idx]
            y_tr, y_val = y.iloc[train_idx], y.iloc[val_idx]

            # Modèle frais à chaque fold — pas de fuite entre folds
            pipeline = self._build_pipeline()
            pipeline.fit(X_tr, y_tr)

            y_pred  = pipeline.predict(X_val)
            y_proba = pipeline.predict_proba(X_val)
            accuracy = (y_pred == y_val.values).mean()

            results.append({
                "fold":       fold_idx + 1,
                "train_size": len(X_tr),
                "val_size":   len(X_val),
                "accuracy":   accuracy,
                "y_val":      y_val,
                "y_pred":     y_pred,
                "y_proba":    y_proba,
            })

            logger.info(
                f"  Fold {fold_idx+1}/{n_splits} | "
                f"train={len(X_tr)} val={len(X_val)} | "
                f"accuracy={accuracy:.4f}"
            )

        logger.info(
            f"BaselineModel({self.model_type}).cross_validate : "
            f"accuracy moyenne = {np.mean([r['accuracy'] for r in results]):.4f}"
        )
        return results

    def feature_importances(self) -> Optional[pd.Series]:
        """
        Retourne l'importance des features si disponible.

        - RandomForest → feature_importances_ (Gini)
        - LogisticRegression → |coef_| (poids absolus)
        - Dummy → None

        Returns:
            pd.Series trié par importance décroissante, ou None pour Dummy.
        """
        self._check_fitted()
        model = self.pipeline.named_steps["model"]

        if hasattr(model, "feature_importances_"):
            importances = model.feature_importances_
        elif hasattr(model, "coef_"):
            # coef_ shape : (1, n_features) pour binaire
            importances = np.abs(model.coef_[0])
        else:
            return None

        return (
            pd.Series(importances, index=self.feature_names_)
            .sort_values(ascending=False)
        )

    # ------------------------------------------------------------------
    # Méthodes privées
    # ------------------------------------------------------------------

    def _build_pipeline(self) -> Pipeline:
        """Construit le Pipeline scaler + modèle selon model_type."""
        if self.model_type == "dummy":
            model = DummyClassifier(strategy="most_frequent", random_state=self.random_state)

        elif self.model_type == "logistic_regression":
            # max_iter=1000 : nécessaire sur des datasets avec beaucoup de features
            # class_weight='balanced' : compense le déséquilibre hausse/baisse
            # C=0.1 : régularisation légèrement plus forte que le défaut (C=1)
            model = LogisticRegression(
                max_iter=1000,
                class_weight="balanced",
                C=0.1,
                random_state=self.random_state,
            )

        elif self.model_type == "random_forest":
            # n_estimators=200 : bon compromis perf/temps sur nos datasets (~500 lignes)
            # max_depth=6 : limite le surapprentissage (les marchés sont bruités)
            # min_samples_leaf=10 : évite les feuilles sur 1-2 exemples
            # class_weight='balanced' : gère le déséquilibre des classes
            model = RandomForestClassifier(
                n_estimators=200,
                max_depth=6,
                min_samples_leaf=10,
                class_weight="balanced",
                random_state=self.random_state,
                n_jobs=-1,
            )

        else:  # xgboost
            # n_estimators=300 : plus d'arbres compensés par un faible learning_rate
            # max_depth=4 : arbres peu profonds pour éviter l'overfit sur séries temporelles
            # learning_rate=0.05 : descente de gradient lente = meilleure généralisation
            # subsample=0.8 + colsample_bytree=0.8 : stochastique pour réduire la variance
            # scale_pos_weight : compense le déséquilibre de classes (ratio négatif/positif)
            model = XGBClassifier(
                n_estimators=300,
                max_depth=4,
                learning_rate=0.05,
                subsample=0.8,
                colsample_bytree=0.8,
                scale_pos_weight=1,
                use_label_encoder=False,
                eval_metric="logloss",
                random_state=self.random_state,
                n_jobs=-1,
                verbosity=0,
            )

        # XGBoost n'a pas besoin de scaling (basé sur des arbres)
        # mais on le conserve pour uniformité du pipeline
        return Pipeline([
            ("scaler", StandardScaler()),
            ("model",  model),
        ])

    def _check_fitted(self) -> None:
        if not self.is_fitted:
            raise RuntimeError("Le modèle n'est pas encore entraîné. Appelez fit() d'abord.")

    def __repr__(self) -> str:
        status = "fitted" if self.is_fitted else "not fitted"
        return f"BaselineModel(type='{self.model_type}', {status})"
