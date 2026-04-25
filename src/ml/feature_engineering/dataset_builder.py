"""
Construction des datasets supervisés pour le ML.

Responsabilités :
  - Créer la variable cible (target) sans data leakage
  - Supprimer les lignes avec NaN (warm-up des indicateurs + horizon final)
  - Fournir des splits temporels corrects (TimeSeriesSplit)

Règle fondamentale anti-data-leakage :
  La target à t est construite à partir de close(t + horizon).
  On supprime les n dernières lignes qui n'ont pas de target valide.
  On ne shuffe jamais les données avant un split temporel.
"""

from typing import List, Tuple

import numpy as np
import pandas as pd
from sklearn.model_selection import TimeSeriesSplit

from logger_settings import logger

# Colonnes brutes / méta à exclure de X
_META_COLUMNS = {
    "id",
    "timestamp",
    "symbol",
    "timeframe",
    "exchange",
    "date",
    "created_at",
    "updated_at",
    # Prix bruts : le modèle travaille sur des features dérivées, pas les prix absolus
    "open",
    "high",
    "low",
    "close",
    "volume",
    # Colonnes déjà enrichies par le pipeline ETL
    "price_range",
    "price_change",
    "price_change_pct",
}


class DatasetBuilder:
    """
    Construit X et y à partir d'un DataFrame enrichi par ``FeatureBuilder``.

    Args:
        horizon: Nombre de bougies dans le futur à prédire (défaut : 1).
        mode:    ``'direction'`` → classification binaire (1 = hausse, 0 = baisse/neutre).
                 ``'return'``    → régression (return en % sur l'horizon).

    Usage::

        builder = DatasetBuilder(horizon=4, mode='direction')
        X, y = builder.build(df_features)
        splits = builder.time_series_split(X, y, n_splits=5)
    """

    def __init__(self, horizon: int = 1, mode: str = "direction"):
        if mode not in ("direction", "return"):
            raise ValueError("mode doit être 'direction' ou 'return'.")
        if horizon < 1:
            raise ValueError("horizon doit être >= 1.")
        self.horizon = horizon
        self.mode = mode

    # ------------------------------------------------------------------
    # API publique
    # ------------------------------------------------------------------

    def build(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Produit (X, y) prêts pour l'entraînement.

        Args:
            df: DataFrame issu de ``FeatureBuilder.build()``.

        Returns:
            ``(X, y)`` sans aucun NaN, index réinitialisé.

        Notes:
            - Les ``horizon`` dernières lignes sont supprimées car elles n'ont
              pas de target future valide.
            - Les premières lignes sont supprimées à cause du warm-up des
              indicateurs (SMA50 = 50 premières valeurs NaN, etc.).
        """
        df = df.copy()

        df["target"] = self._build_target(df["close"])

        feature_cols = self._feature_columns(df)
        df_ml = df[feature_cols + ["target"]].dropna().reset_index(drop=True)

        n_dropped = len(df) - len(df_ml)
        logger.info(
            f"DatasetBuilder.build : {n_dropped} lignes supprimées (NaN / horizon). "
            f"Dataset : {len(df_ml)} lignes × {len(feature_cols)} features. "
            f"Horizon={self.horizon}, mode='{self.mode}'."
        )

        X = df_ml[feature_cols]
        y = df_ml["target"]
        return X, y

    def time_series_split(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        n_splits: int = 5,
    ) -> List[Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]]:
        """
        Découpe en folds temporels (sans data leakage).

        Chaque fold garantit que l'ensemble de validation est strictement
        postérieur à l'ensemble d'entraînement.

        Args:
            X: Features.
            y: Target.
            n_splits: Nombre de folds (défaut : 5).

        Returns:
            Liste de tuples ``(X_train, X_val, y_train, y_val)``.
        """
        tscv = TimeSeriesSplit(n_splits=n_splits)
        splits = [
            (
                X.iloc[tr],
                X.iloc[val],
                y.iloc[tr],
                y.iloc[val],
            )
            for tr, val in tscv.split(X)
        ]
        logger.info(f"DatasetBuilder.time_series_split : {n_splits} folds créés.")
        return splits

    def train_test_split_temporal(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        test_ratio: float = 0.2,
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
        """
        Split train / test en respectant l'ordre chronologique.

        Args:
            X: Features.
            y: Target.
            test_ratio: Proportion réservée au test (défaut : 0.2).

        Returns:
            ``(X_train, X_test, y_train, y_test)``
        """
        if not (0 < test_ratio < 1):
            raise ValueError("test_ratio doit être entre 0 et 1 (exclu).")

        split_idx = int(len(X) * (1 - test_ratio))
        X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
        y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

        logger.info(
            f"DatasetBuilder.train_test_split_temporal : "
            f"train={len(X_train)}, test={len(X_test)} (ratio={test_ratio})."
        )
        return X_train, X_test, y_train, y_test

    # ------------------------------------------------------------------
    # Méthodes privées
    # ------------------------------------------------------------------

    def _build_target(self, close: pd.Series) -> pd.Series:
        """Construit la target future sans data leakage."""
        future_close = close.shift(-self.horizon)

        if self.mode == "direction":
            return (future_close > close).astype(float)
        else:
            return (future_close - close) / close.replace(0, np.nan)

    def _feature_columns(self, df: pd.DataFrame) -> List[str]:
        """Retourne les colonnes à utiliser comme features (X)."""
        return [c for c in df.columns if c not in _META_COLUMNS and c != "target"]
