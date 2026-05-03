"""Backtester walk-forward avec purge et embargo pour données de séries temporelles.

Évalue une stratégie (modèle sklearn) sur des fenêtres glissantes de dates en
respectant l'intégrité temporelle : pas de mélange, pas de fuite entre train et test.

Métriques calculées par fold et en agrégat :
  - accuracy, win_rate
  - PnL (log-returns sur signaux BUY)
  - Sharpe ratio annualisé
  - Profit factor (gains bruts / pertes brutes)
  - Maximum drawdown
  - Comparaison vs buy-and-hold
"""

from __future__ import annotations

import logging
import math
from typing import Any, Protocol

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Jours de purge et d'embargo par défaut entre chaque fenêtre
_PURGE_DAYS: int = 1
_EMBARGO_DAYS: int = 1

# Facteur d'annualisation pour le Sharpe (bougies journalières)
_TRADING_DAYS_PER_YEAR: int = 365


class Strategy(Protocol):
    """Interface minimale qu'une stratégie doit implémenter."""

    def fit(self, X: pd.DataFrame, y: pd.Series) -> None: ...
    def predict(self, X: pd.DataFrame) -> np.ndarray: ...


# ---------------------------------------------------------------------------
# Fonctions de métriques financières
# ---------------------------------------------------------------------------

def compute_sharpe(returns: list[float], periods_per_year: int = _TRADING_DAYS_PER_YEAR) -> float:
    """Sharpe ratio annualisé (taux sans risque = 0).

    Args:
        returns: Liste de rendements par trade ou par période.
        periods_per_year: Facteur d'annualisation.

    Returns:
        Sharpe ratio, ou 0.0 si l'écart-type est nul.
    """
    if len(returns) < 2:
        return 0.0
    arr = np.array(returns, dtype=float)
    std = float(np.std(arr, ddof=1))
    if std == 0:
        return 0.0
    return float((np.mean(arr) / std) * math.sqrt(periods_per_year))


def compute_profit_factor(returns: list[float]) -> float:
    """Ratio gains bruts / pertes brutes.

    Returns:
        > 1.0 = stratégie profitable. inf si aucune perte. 0.0 si aucun gain.
    """
    gross_profit = sum(r for r in returns if r > 0)
    gross_loss = abs(sum(r for r in returns if r < 0))
    if gross_loss == 0:
        return float("inf") if gross_profit > 0 else 1.0
    return gross_profit / gross_loss


def compute_max_drawdown(returns: list[float]) -> float:
    """Drawdown maximum (pic vers creux) sur une séquence de rendements.

    Returns:
        Fraction positive (ex: 0.25 = drawdown de 25 %).
    """
    if not returns:
        return 0.0
    cumulative = np.cumprod([1 + r for r in returns])
    peak = np.maximum.accumulate(cumulative)
    drawdown = (peak - cumulative) / np.where(peak == 0, 1, peak)
    return float(np.max(drawdown))


# ---------------------------------------------------------------------------
# Backtester principal
# ---------------------------------------------------------------------------

class Backtester:
    """Walk-forward backtester avec purge et embargo.

    À chaque fold :
      1. Fenêtre d'entraînement : ``train_window`` jours
      2. Purge : ``purge_days`` jours exclus en fin de train (anti-leakage)
      3. Fenêtre de test : ``test_window`` jours
      4. Embargo : ``embargo_days`` jours exclus après le test

    Args:
        train_window: Jours d'entraînement par fold (défaut 180).
        test_window: Jours de test par fold (défaut 30).
        purge_days: Jours de purge entre train et test (défaut 1).
        embargo_days: Jours d'embargo après chaque test (défaut 1).
    """

    def __init__(
        self,
        train_window: int = 180,
        test_window: int = 30,
        purge_days: int = _PURGE_DAYS,
        embargo_days: int = _EMBARGO_DAYS,
    ) -> None:
        if train_window <= 0 or test_window <= 0:
            raise ValueError("train_window et test_window doivent être des entiers positifs")
        self.train_window = train_window
        self.test_window = test_window
        self.purge_days = purge_days
        self.embargo_days = embargo_days

    # ------------------------------------------------------------------
    # API publique
    # ------------------------------------------------------------------

    def walk_forward(self, data: pd.DataFrame, strategy: Strategy) -> pd.DataFrame:
        """Exécute le backtest walk-forward sur l'ensemble des données.

        Le DataFrame doit contenir :
        - Un ``DatetimeIndex`` trié en ordre croissant.
        - Toutes les colonnes de features utilisées par la stratégie.
        - Une colonne ``label`` (int : 1 = hausse, 0 = baisse/stagnation).
        - Une colonne ``price_close`` (prix de clôture, pour le PnL).

        Args:
            data: DataFrame features + label, indexé par date.
            strategy: Objet implémentant l'interface :class:`Strategy`.

        Returns:
            DataFrame des résultats par fold (vide si aucun fold valide) avec
            colonnes : fold, train_start, train_end, test_start, test_end,
            n_train, n_test, accuracy, win_rate, pnl, sharpe,
            profit_factor, max_drawdown.

        Raises:
            ValueError: Si des colonnes obligatoires sont absentes ou si les
                données couvrent une période trop courte.
        """
        self._validate(data)
        data = data.sort_index()
        dates = data.index.normalize().unique().sort_values()
        total_days = (dates[-1] - dates[0]).days
        min_days = self.train_window + self.purge_days + self.test_window + self.embargo_days

        if total_days < min_days:
            raise ValueError(
                f"Les données couvrent {total_days} jours ; "
                f"il en faut au moins {min_days} "
                f"(train={self.train_window}, purge={self.purge_days}, "
                f"test={self.test_window}, embargo={self.embargo_days})"
            )

        feature_cols = [c for c in data.columns if c not in {"label", "price_close"}]
        fold_results: list[dict[str, Any]] = []
        fold_idx = 0
        cursor = dates[0]

        while True:
            train_end = cursor + pd.Timedelta(days=self.train_window)
            test_start = train_end + pd.Timedelta(days=self.purge_days)
            test_end = test_start + pd.Timedelta(days=self.test_window)
            next_cursor = test_end + pd.Timedelta(days=self.embargo_days)

            if test_end > dates[-1]:
                break

            train_df = data.loc[(data.index >= cursor) & (data.index < train_end)]
            test_df = data.loc[(data.index >= test_start) & (data.index < test_end)]

            if train_df.empty or test_df.empty:
                cursor = next_cursor
                fold_idx += 1
                continue

            X_train = train_df[feature_cols]
            y_train = train_df["label"]
            X_test = test_df[feature_cols]
            y_test = test_df["label"]
            prices = test_df["price_close"]

            try:
                strategy.fit(X_train, y_train)
                preds = strategy.predict(X_test)
            except Exception as exc:
                logger.error("Fold %d — échec de la stratégie : %s", fold_idx, exc)
                cursor = next_cursor
                fold_idx += 1
                continue

            metrics = self._fold_metrics(preds, y_test, prices)

            fold_results.append({
                "fold": fold_idx,
                "train_start": cursor,
                "train_end": train_end,
                "test_start": test_start,
                "test_end": test_end,
                "n_train": len(train_df),
                "n_test": len(test_df),
                **metrics,
            })

            logger.info(
                "Fold %d | acc=%.3f win=%.3f pnl=%.4f sharpe=%.2f pf=%.2f mdd=%.2f",
                fold_idx,
                metrics["accuracy"],
                metrics["win_rate"],
                metrics["pnl"],
                metrics["sharpe"],
                metrics["profit_factor"],
                metrics["max_drawdown"],
            )

            cursor = next_cursor
            fold_idx += 1

        if not fold_results:
            logger.warning("Aucun fold valide produit par le walk-forward")
            return pd.DataFrame()

        return pd.DataFrame(fold_results)

    def compute_metrics(self, results: pd.DataFrame) -> dict[str, float]:
        """Agrège les métriques de tous les folds en un résumé global.

        Args:
            results: Sortie de :meth:`walk_forward`.

        Returns:
            Dict avec : accuracy, win_rate, sharpe, profit_factor,
            max_drawdown, total_pnl, n_folds.
        """
        if results.empty:
            return {
                "accuracy": 0.0,
                "win_rate": 0.0,
                "sharpe": 0.0,
                "profit_factor": 0.0,
                "max_drawdown": 0.0,
                "total_pnl": 0.0,
                "n_folds": 0,
            }

        pnl = results["pnl"]
        gains = pnl[pnl > 0]
        losses = pnl[pnl < 0]
        profit_factor = (
            float(gains.sum() / abs(losses.sum())) if losses.sum() != 0 else 999.0
        )
        std_pnl = float(pnl.std()) if len(pnl) > 1 else 1.0
        sharpe = float(pnl.mean() / std_pnl) * math.sqrt(_TRADING_DAYS_PER_YEAR) if std_pnl else 0.0

        return {
            "accuracy": float(results["accuracy"].mean()),
            "win_rate": float(results["win_rate"].mean()),
            "sharpe": round(sharpe, 4),
            "profit_factor": round(profit_factor, 4),
            "max_drawdown": float(results["max_drawdown"].max()),
            "total_pnl": round(float(pnl.sum()), 6),
            "n_folds": len(results),
        }

    def compare_baseline(
        self,
        results: pd.DataFrame,
        data: pd.DataFrame,
    ) -> dict[str, float]:
        """Compare le rendement de la stratégie vs buy-and-hold sur la même période.

        Args:
            results: Sortie de :meth:`walk_forward`.
            data: DataFrame original avec colonne ``price_close``.

        Returns:
            Dict avec : strategy_pnl, baseline_return, excess_return, sharpe.
        """
        if results.empty or "price_close" not in data.columns:
            return {"strategy_pnl": 0.0, "baseline_return": 0.0, "excess_return": 0.0, "sharpe": 0.0}

        test_start = results["test_start"].min()
        test_end = results["test_end"].max()
        period = data.loc[(data.index >= test_start) & (data.index < test_end), "price_close"]

        if len(period) < 2:
            baseline = 0.0
        else:
            baseline = float((period.iloc[-1] - period.iloc[0]) / period.iloc[0])

        summary = self.compute_metrics(results)
        strategy_pnl = summary["total_pnl"]
        excess = strategy_pnl - baseline

        comparison = {
            "strategy_pnl": round(strategy_pnl, 6),
            "baseline_return": round(baseline, 6),
            "excess_return": round(excess, 6),
            "sharpe": summary["sharpe"],
        }
        logger.info("Comparaison baseline : %s", comparison)
        return comparison

    # ------------------------------------------------------------------
    # Helpers privés
    # ------------------------------------------------------------------

    @staticmethod
    def _validate(data: pd.DataFrame) -> None:
        missing = {"label", "price_close"} - set(data.columns)
        if missing:
            raise ValueError(f"Colonnes manquantes dans data : {missing}")
        if not isinstance(data.index, pd.DatetimeIndex):
            raise ValueError("data doit avoir un DatetimeIndex")

    @staticmethod
    def _fold_metrics(
        preds: np.ndarray,
        y_test: pd.Series,
        prices: pd.Series,
    ) -> dict[str, float]:
        """Calcule toutes les métriques financières et ML pour un fold."""
        prices_arr = prices.values.astype(float)
        labels_arr = y_test.values

        accuracy = float((preds == labels_arr).mean())

        buy_mask = preds == 1
        win_rate = (
            float((labels_arr[buy_mask] == 1).sum() / buy_mask.sum())
            if buy_mask.sum() > 0 else 0.0
        )

        # PnL : log-return sur les positions BUY correctement prédites
        log_returns: list[float] = []
        for i in range(len(preds) - 1):
            if preds[i] == 1 and prices_arr[i] > 0:
                log_returns.append(float(np.log(prices_arr[i + 1] / prices_arr[i])))

        pnl = float(sum(log_returns))
        sharpe = compute_sharpe(log_returns)
        pf = compute_profit_factor(log_returns)
        if pf == float("inf"):
            pf = 999.0
        mdd = compute_max_drawdown(log_returns)

        return {
            "accuracy": accuracy,
            "win_rate": win_rate,
            "pnl": round(pnl, 6),
            "sharpe": round(sharpe, 4),
            "profit_factor": round(pf, 4),
            "max_drawdown": round(mdd, 4),
        }
