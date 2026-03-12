"""Walk-forward backtester with purging and embargo windows.

Temporal integrity is enforced throughout:
- Training window: ``train_window`` days of history.
- Purging gap: 1 day removed between train end and test start (avoids leakage
  from labels whose outcome overlaps the training boundary).
- Embargo gap: 1 day removed after each test window (avoids contamination from
  post-test labelling).
- Test window: ``test_window`` days per fold.
"""

from __future__ import annotations

import logging
from typing import Any, Protocol

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Days removed at the boundary between train and test to prevent leakage.
PURGE_DAYS: int = 1
# Days removed after the test window before the next train window begins.
EMBARGO_DAYS: int = 1


class Strategy(Protocol):
    """Minimal protocol a strategy must implement to be backtestable."""

    def fit(self, X: pd.DataFrame, y: pd.Series) -> None:
        """Train the strategy on historical features and labels."""
        ...

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Return predictions (0/1) for the provided feature rows."""
        ...


class Backtester:
    """Walk-forward backtester with purging and embargo.

    Args:
        train_window: Number of days in each training window. Default 180.
        test_window: Number of days in each test window. Default 30.
    """

    def __init__(
        self,
        train_window: int = 180,
        test_window: int = 30,
    ) -> None:
        if train_window <= 0 or test_window <= 0:
            raise ValueError("train_window and test_window must be positive integers")
        self.train_window = train_window
        self.test_window = test_window
        logger.info(
            "Backtester: train=%d days, test=%d days, purge=%d day, embargo=%d day",
            train_window,
            test_window,
            PURGE_DAYS,
            EMBARGO_DAYS,
        )

    # ------------------------------------------------------------------
    # Walk-forward
    # ------------------------------------------------------------------

    def walk_forward(
        self,
        data: pd.DataFrame,
        strategy: Strategy,
    ) -> pd.DataFrame:
        """Run a walk-forward backtest over the full dataset.

        The DataFrame must have:
        - A DatetimeIndex (sorted ascending).
        - All feature columns used by ``strategy.fit`` / ``strategy.predict``.
        - A ``label`` column (int: 1 = BUY, 0 = SELL/HOLD).
        - A ``price_close`` column (used for PnL calculation).

        Args:
            data: Feature + label DataFrame, time-indexed.
            strategy: Object implementing the :class:`Strategy` protocol.

        Returns:
            DataFrame of fold results with columns:
            ``fold``, ``train_start``, ``train_end``, ``test_start``,
            ``test_end``, ``n_train``, ``n_test``, ``accuracy``,
            ``win_rate``, ``pnl``.

        Raises:
            ValueError: If required columns are missing or data is too short.
        """
        required = {"label", "price_close"}
        missing = required - set(data.columns)
        if missing:
            raise ValueError(f"data is missing required columns: {missing}")

        data = data.sort_index()
        dates = data.index.normalize().unique().sort_values()

        total_days = (dates[-1] - dates[0]).days
        min_days = self.train_window + PURGE_DAYS + self.test_window + EMBARGO_DAYS
        if total_days < min_days:
            raise ValueError(f"Dataset spans only {total_days} days; need at least {min_days}")

        fold_results: list[dict[str, Any]] = []
        fold_idx = 0
        train_start_date = dates[0]

        while True:
            train_end_date = train_start_date + pd.Timedelta(days=self.train_window)
            purge_end_date = train_end_date + pd.Timedelta(days=PURGE_DAYS)
            test_end_date = purge_end_date + pd.Timedelta(days=self.test_window)
            embargo_end_date = test_end_date + pd.Timedelta(days=EMBARGO_DAYS)

            if test_end_date > dates[-1]:
                break

            train_mask = (data.index >= train_start_date) & (data.index < train_end_date)
            test_mask = (data.index >= purge_end_date) & (data.index < test_end_date)

            train_df = data.loc[train_mask]
            test_df = data.loc[test_mask]

            if train_df.empty or test_df.empty:
                train_start_date = embargo_end_date
                continue

            feature_cols = [c for c in data.columns if c not in {"label", "price_close"}]
            X_train = train_df[feature_cols]
            y_train = train_df["label"]
            X_test = test_df[feature_cols]
            y_test = test_df["label"]

            try:
                strategy.fit(X_train, y_train)
                preds = strategy.predict(X_test)
            except Exception as exc:
                logger.error("Fold %d strategy failed: %s", fold_idx, exc)
                train_start_date = embargo_end_date
                fold_idx += 1
                continue

            fold_pnl = self._compute_fold_pnl(preds, y_test, test_df["price_close"])
            correct = int((preds == y_test.values).sum())
            accuracy = correct / len(y_test) if len(y_test) > 0 else 0.0

            buy_preds = preds == 1
            win_rate = float((y_test.values[buy_preds] == 1).sum()) / buy_preds.sum() if buy_preds.sum() > 0 else 0.0

            fold_results.append(
                {
                    "fold": fold_idx,
                    "train_start": train_start_date,
                    "train_end": train_end_date,
                    "test_start": purge_end_date,
                    "test_end": test_end_date,
                    "n_train": len(train_df),
                    "n_test": len(test_df),
                    "accuracy": accuracy,
                    "win_rate": win_rate,
                    "pnl": fold_pnl,
                }
            )

            logger.info(
                "Fold %d: acc=%.3f win_rate=%.3f pnl=%.4f (train=%d test=%d)",
                fold_idx,
                accuracy,
                win_rate,
                fold_pnl,
                len(train_df),
                len(test_df),
            )

            train_start_date = embargo_end_date
            fold_idx += 1

        if not fold_results:
            logger.warning("Walk-forward produced no folds")
            return pd.DataFrame()

        return pd.DataFrame(fold_results)

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    def compute_metrics(self, results: pd.DataFrame) -> dict[str, float]:
        """Aggregate fold-level results into overall backtest metrics.

        Args:
            results: Output DataFrame from :meth:`walk_forward`.

        Returns:
            Dict with keys: ``accuracy``, ``win_rate``, ``sharpe``,
            ``profit_factor``, ``n_folds``, ``total_pnl``.
        """
        if results.empty:
            logger.warning("compute_metrics called with empty results")
            return {
                "accuracy": 0.0,
                "win_rate": 0.0,
                "sharpe": 0.0,
                "profit_factor": 0.0,
                "n_folds": 0,
                "total_pnl": 0.0,
            }

        pnl_series = results["pnl"]
        total_pnl = float(pnl_series.sum())

        gains = pnl_series[pnl_series > 0]
        losses = pnl_series[pnl_series < 0]
        profit_factor = float(gains.sum() / abs(losses.sum())) if losses.sum() != 0 else float("inf")

        mean_pnl = float(pnl_series.mean())
        std_pnl = float(pnl_series.std()) if len(pnl_series) > 1 else 1.0
        sharpe = mean_pnl / std_pnl if std_pnl != 0 else 0.0

        metrics = {
            "accuracy": float(results["accuracy"].mean()),
            "win_rate": float(results["win_rate"].mean()),
            "sharpe": sharpe,
            "profit_factor": profit_factor,
            "n_folds": len(results),
            "total_pnl": total_pnl,
        }
        logger.info("Backtest metrics: %s", metrics)
        return metrics

    def compare_baseline(
        self,
        results: pd.DataFrame,
        prices: pd.DataFrame,
    ) -> dict[str, float]:
        """Compare strategy returns against a buy-and-hold baseline.

        Args:
            results: Walk-forward results from :meth:`walk_forward`.
            prices: DataFrame with a DatetimeIndex and a ``price_close`` column
                    covering the same period as ``results``.

        Returns:
            Dict with keys: ``strategy_total_pnl``, ``baseline_return``,
            ``excess_return``, ``strategy_sharpe``.
        """
        if results.empty or prices.empty:
            return {
                "strategy_total_pnl": 0.0,
                "baseline_return": 0.0,
                "excess_return": 0.0,
                "strategy_sharpe": 0.0,
            }

        prices = prices.sort_index()
        start_price = float(prices["price_close"].iloc[0])
        end_price = float(prices["price_close"].iloc[-1])
        baseline_return = (end_price - start_price) / start_price if start_price else 0.0

        strategy_metrics = self.compute_metrics(results)
        strategy_pnl = strategy_metrics["total_pnl"]
        excess = strategy_pnl - baseline_return

        comparison = {
            "strategy_total_pnl": strategy_pnl,
            "baseline_return": baseline_return,
            "excess_return": excess,
            "strategy_sharpe": strategy_metrics["sharpe"],
        }
        logger.info("Baseline comparison: %s", comparison)
        return comparison

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_fold_pnl(
        preds: np.ndarray,
        labels: pd.Series,
        prices: pd.Series,
    ) -> float:
        """Compute simple long-only PnL for one fold.

        Only enters a trade when the prediction is BUY (1) and the label
        confirms a correct call.

        Args:
            preds: Model predictions (0 or 1).
            labels: Ground-truth labels.
            prices: Close prices aligned with labels.

        Returns:
            Sum of log returns for correctly predicted BUY signals.
        """
        prices_arr = prices.values.astype(float)
        total_pnl = 0.0
        for i in range(len(preds) - 1):
            if preds[i] == 1 and prices_arr[i] > 0:
                log_ret = np.log(prices_arr[i + 1] / prices_arr[i])
                total_pnl += float(log_ret)
        return total_pnl
