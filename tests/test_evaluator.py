"""
Tests unitaires pour ModelEvaluator.
"""

import numpy as np
import pandas as pd
import pytest

from src.ml.models.evaluator import ModelEvaluator


# ---------------------------------------------------------------------------
# Helpers pour construire des fold_results factices
# ---------------------------------------------------------------------------

def _make_fold(fold_idx: int, y_val: pd.Series, y_pred: np.ndarray) -> dict:
    """Construit un dict fold compatible avec cross_validate()."""
    n = len(y_val)
    proba_1 = y_pred.astype(float)
    proba_0 = 1 - proba_1
    y_proba = np.column_stack([proba_0, proba_1])
    return {
        "fold":       fold_idx,
        "train_size": n * 2,
        "val_size":   n,
        "accuracy":   float((y_pred == y_val.values).mean()),
        "y_val":      y_val,
        "y_pred":     y_pred,
        "y_proba":    y_proba,
    }


def _perfect_folds(n: int = 50) -> list:
    """Modèle parfait : toutes les prédictions correctes."""
    rng = np.random.default_rng(0)
    y = pd.Series(rng.integers(0, 2, n), name="target")
    folds = []
    for i in range(1, 4):
        folds.append(_make_fold(i, y, y.values.copy()))
    return folds


def _random_folds(n: int = 50) -> list:
    """Modèle aléatoire."""
    rng = np.random.default_rng(42)
    y = pd.Series(rng.integers(0, 2, n), name="target")
    folds = []
    for i in range(1, 4):
        pred = rng.integers(0, 2, n)
        folds.append(_make_fold(i, y, pred))
    return folds


# ---------------------------------------------------------------------------
# Tests evaluate_folds()
# ---------------------------------------------------------------------------

class TestEvaluateFolds:
    def test_returns_dict_with_expected_keys(self):
        evaluator = ModelEvaluator()
        result = evaluator.evaluate_folds(_random_folds())
        assert "per_fold" in result
        assert "mean" in result
        assert "std" in result

    def test_per_fold_length(self):
        evaluator = ModelEvaluator()
        folds = _random_folds()
        result = evaluator.evaluate_folds(folds)
        assert len(result["per_fold"]) == len(folds)

    def test_mean_accuracy_between_0_and_1(self):
        evaluator = ModelEvaluator()
        result = evaluator.evaluate_folds(_random_folds())
        assert 0.0 <= result["mean"]["accuracy"] <= 1.0

    def test_perfect_model_accuracy_one(self):
        evaluator = ModelEvaluator()
        result = evaluator.evaluate_folds(_perfect_folds())
        assert pytest.approx(result["mean"]["accuracy"], abs=1e-6) == 1.0

    def test_perfect_model_f1_one(self):
        evaluator = ModelEvaluator()
        result = evaluator.evaluate_folds(_perfect_folds())
        assert pytest.approx(result["mean"]["f1"], abs=1e-6) == 1.0

    def test_ml_metrics_present(self):
        evaluator = ModelEvaluator()
        result = evaluator.evaluate_folds(_random_folds())
        for key in ("accuracy", "precision", "recall", "f1"):
            assert key in result["mean"]

    def test_financial_metrics_present_without_returns(self):
        """Les métriques financières simulées sont calculées même sans returns réels."""
        evaluator = ModelEvaluator()
        result = evaluator.evaluate_folds(_random_folds())
        for key in ("win_rate", "profit_factor", "sharpe"):
            assert key in result["mean"]

    def test_win_rate_between_0_and_1(self):
        evaluator = ModelEvaluator()
        result = evaluator.evaluate_folds(_random_folds())
        assert 0.0 <= result["mean"]["win_rate"] <= 1.0

    def test_perfect_model_win_rate_one(self):
        evaluator = ModelEvaluator()
        result = evaluator.evaluate_folds(_perfect_folds())
        assert pytest.approx(result["mean"]["win_rate"], abs=1e-6) == 1.0

    def test_std_non_negative(self):
        evaluator = ModelEvaluator()
        result = evaluator.evaluate_folds(_random_folds())
        for v in result["std"].values():
            assert v >= 0.0


# ---------------------------------------------------------------------------
# Tests avec returns réels
# ---------------------------------------------------------------------------

class TestEvaluateFoldsWithReturns:
    def test_financial_metrics_with_returns(self):
        rng = np.random.default_rng(7)
        n = 50
        y = pd.Series(rng.integers(0, 2, n), name="target")
        returns = pd.Series(rng.normal(0, 0.01, n), index=y.index)

        folds = [_make_fold(i, y, rng.integers(0, 2, n)) for i in range(1, 4)]
        evaluator = ModelEvaluator()
        result = evaluator.evaluate_folds(folds, returns=returns)

        assert "sharpe" in result["mean"]
        assert "win_rate" in result["mean"]
        assert "profit_factor" in result["mean"]

    def test_profit_factor_non_negative(self):
        rng = np.random.default_rng(99)
        n = 100
        y = pd.Series(rng.integers(0, 2, n), name="target")
        returns = pd.Series(rng.normal(0, 0.01, n), index=y.index)
        folds = [_make_fold(1, y, rng.integers(0, 2, n))]

        evaluator = ModelEvaluator()
        result = evaluator.evaluate_folds(folds, returns=returns)
        assert result["mean"]["profit_factor"] >= 0.0


# ---------------------------------------------------------------------------
# Tests compare_models()
# ---------------------------------------------------------------------------

class TestCompareModels:
    def test_returns_dataframe(self):
        evaluator = ModelEvaluator()
        df = evaluator.compare_models({
            "dummy": _random_folds(),
            "lr":    _random_folds(),
        })
        assert isinstance(df, pd.DataFrame)

    def test_index_contains_model_names(self):
        evaluator = ModelEvaluator()
        df = evaluator.compare_models({
            "dummy": _random_folds(),
            "rf":    _perfect_folds(),
        })
        assert "dummy" in df.index
        assert "rf" in df.index

    def test_columns_contain_metrics(self):
        evaluator = ModelEvaluator()
        df = evaluator.compare_models({"m": _random_folds()})
        for col in ("accuracy", "f1"):
            assert col in df.columns

    def test_n_rows_matches_n_models(self):
        evaluator = ModelEvaluator()
        models = {"a": _random_folds(), "b": _random_folds(), "c": _perfect_folds()}
        df = evaluator.compare_models(models)
        assert len(df) == 3


# ---------------------------------------------------------------------------
# Tests _compute_financial_stats() (méthode statique interne)
# ---------------------------------------------------------------------------

class TestComputeFinancialStats:
    def test_all_wins(self):
        pnl = np.array([1.0, 2.0, 0.5])
        stats = ModelEvaluator._compute_financial_stats(pnl)
        assert stats["win_rate"] == pytest.approx(1.0)
        # Pas de pertes → profit_factor très élevé (numérateur / epsilon)
        assert stats["profit_factor"] > 1e6

    def test_all_losses(self):
        pnl = np.array([-1.0, -2.0])
        stats = ModelEvaluator._compute_financial_stats(pnl)
        assert stats["win_rate"] == pytest.approx(0.0)
        assert stats["profit_factor"] == pytest.approx(0.0, abs=1e-6)

    def test_mixed(self):
        pnl = np.array([1.0, -1.0, 1.0, -1.0])
        stats = ModelEvaluator._compute_financial_stats(pnl)
        assert stats["win_rate"] == pytest.approx(0.5)
        assert stats["profit_factor"] == pytest.approx(1.0)
        assert stats["sharpe"] == pytest.approx(0.0, abs=1e-6)

    def test_empty_pnl(self):
        stats = ModelEvaluator._compute_financial_stats(np.array([]))
        assert stats["win_rate"] == 0.0
