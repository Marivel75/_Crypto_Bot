"""
Tests unitaires pour BaselineModel.
"""

import numpy as np
import pandas as pd
import pytest

from src.ml.models.baseline import BaselineModel


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def simple_dataset():
    """Dataset synthétique binaire minimal (200 lignes, 5 features)."""
    rng = np.random.default_rng(42)
    n = 200
    X = pd.DataFrame(
        rng.normal(0, 1, (n, 5)),
        columns=["f1", "f2", "f3", "f4", "f5"],
    )
    y = pd.Series(rng.integers(0, 2, n), name="target")
    return X, y


@pytest.fixture
def imbalanced_dataset():
    """Dataset déséquilibré : 80 % de classe 1."""
    rng = np.random.default_rng(0)
    n = 200
    X = pd.DataFrame(rng.normal(0, 1, (n, 3)), columns=["a", "b", "c"])
    y = pd.Series(rng.choice([0, 1], size=n, p=[0.2, 0.8]), name="target")
    return X, y


# ---------------------------------------------------------------------------
# Tests d'instanciation
# ---------------------------------------------------------------------------

class TestBaselineModelInit:
    def test_default_type(self):
        m = BaselineModel()
        assert m.model_type == "logistic_regression"

    def test_valid_types(self):
        for t in ("dummy", "logistic_regression", "random_forest", "xgboost"):
            m = BaselineModel(model_type=t)
            assert m.model_type == t

    def test_invalid_type_raises(self):
        with pytest.raises(ValueError, match="model_type"):
            BaselineModel(model_type="unknown_model")

    def test_not_fitted_initially(self):
        m = BaselineModel()
        assert not m.is_fitted

    def test_repr_not_fitted(self):
        m = BaselineModel()
        assert "not fitted" in repr(m)


# ---------------------------------------------------------------------------
# Tests fit()
# ---------------------------------------------------------------------------

class TestBaselineModelFit:
    @pytest.mark.parametrize("model_type", ["dummy", "logistic_regression", "random_forest"])
    def test_fit_returns_self(self, model_type, simple_dataset):
        X, y = simple_dataset
        m = BaselineModel(model_type=model_type)
        result = m.fit(X, y)
        assert result is m

    @pytest.mark.parametrize("model_type", ["dummy", "logistic_regression", "random_forest"])
    def test_is_fitted_after_fit(self, model_type, simple_dataset):
        X, y = simple_dataset
        m = BaselineModel(model_type=model_type).fit(X, y)
        assert m.is_fitted

    def test_feature_names_stored(self, simple_dataset):
        X, y = simple_dataset
        m = BaselineModel().fit(X, y)
        assert m.feature_names_ == list(X.columns)

    def test_repr_fitted(self, simple_dataset):
        X, y = simple_dataset
        m = BaselineModel().fit(X, y)
        assert "fitted" in repr(m)
        assert "not fitted" not in repr(m)


# ---------------------------------------------------------------------------
# Tests predict()
# ---------------------------------------------------------------------------

class TestBaselineModelPredict:
    def test_predict_raises_if_not_fitted(self, simple_dataset):
        X, _ = simple_dataset
        m = BaselineModel()
        with pytest.raises(RuntimeError, match="fit"):
            m.predict(X)

    @pytest.mark.parametrize("model_type", ["dummy", "logistic_regression", "random_forest"])
    def test_predict_shape(self, model_type, simple_dataset):
        X, y = simple_dataset
        m = BaselineModel(model_type=model_type).fit(X, y)
        preds = m.predict(X)
        assert preds.shape == (len(X),)

    @pytest.mark.parametrize("model_type", ["dummy", "logistic_regression", "random_forest"])
    def test_predict_binary_values(self, model_type, simple_dataset):
        X, y = simple_dataset
        m = BaselineModel(model_type=model_type).fit(X, y)
        preds = m.predict(X)
        assert set(np.unique(preds)).issubset({0, 1})


# ---------------------------------------------------------------------------
# Tests predict_proba()
# ---------------------------------------------------------------------------

class TestBaselineModelPredictProba:
    def test_predict_proba_raises_if_not_fitted(self, simple_dataset):
        X, _ = simple_dataset
        m = BaselineModel()
        with pytest.raises(RuntimeError, match="fit"):
            m.predict_proba(X)

    @pytest.mark.parametrize("model_type", ["dummy", "logistic_regression", "random_forest"])
    def test_proba_shape(self, model_type, simple_dataset):
        X, y = simple_dataset
        m = BaselineModel(model_type=model_type).fit(X, y)
        proba = m.predict_proba(X)
        assert proba.shape == (len(X), 2)

    @pytest.mark.parametrize("model_type", ["dummy", "logistic_regression", "random_forest"])
    def test_proba_sums_to_one(self, model_type, simple_dataset):
        X, y = simple_dataset
        m = BaselineModel(model_type=model_type).fit(X, y)
        proba = m.predict_proba(X)
        np.testing.assert_allclose(proba.sum(axis=1), np.ones(len(X)), atol=1e-6)

    @pytest.mark.parametrize("model_type", ["dummy", "logistic_regression", "random_forest"])
    def test_proba_between_0_and_1(self, model_type, simple_dataset):
        X, y = simple_dataset
        m = BaselineModel(model_type=model_type).fit(X, y)
        proba = m.predict_proba(X)
        assert (proba >= 0).all() and (proba <= 1).all()


# ---------------------------------------------------------------------------
# Tests cross_validate()
# ---------------------------------------------------------------------------

class TestBaselineModelCrossValidate:
    def test_returns_list_of_dicts(self, simple_dataset):
        X, y = simple_dataset
        m = BaselineModel()
        results = m.cross_validate(X, y, n_splits=3)
        assert isinstance(results, list)
        assert all(isinstance(r, dict) for r in results)

    def test_n_splits_folds(self, simple_dataset):
        X, y = simple_dataset
        m = BaselineModel()
        results = m.cross_validate(X, y, n_splits=4)
        assert len(results) == 4

    def test_fold_keys(self, simple_dataset):
        X, y = simple_dataset
        m = BaselineModel()
        results = m.cross_validate(X, y, n_splits=3)
        required_keys = {"fold", "train_size", "val_size", "accuracy", "y_val", "y_pred", "y_proba"}
        for r in results:
            assert required_keys.issubset(r.keys())

    def test_accuracy_between_0_and_1(self, simple_dataset):
        X, y = simple_dataset
        m = BaselineModel()
        results = m.cross_validate(X, y, n_splits=3)
        for r in results:
            assert 0.0 <= r["accuracy"] <= 1.0

    def test_fold_indices_incremental(self, simple_dataset):
        X, y = simple_dataset
        m = BaselineModel()
        results = m.cross_validate(X, y, n_splits=3)
        fold_nums = [r["fold"] for r in results]
        assert fold_nums == [1, 2, 3]

    def test_y_pred_shape_matches_val(self, simple_dataset):
        X, y = simple_dataset
        m = BaselineModel()
        results = m.cross_validate(X, y, n_splits=3)
        for r in results:
            assert len(r["y_pred"]) == r["val_size"]
            assert len(r["y_val"]) == r["val_size"]

    def test_proba_shape_matches_val(self, simple_dataset):
        X, y = simple_dataset
        m = BaselineModel()
        results = m.cross_validate(X, y, n_splits=3)
        for r in results:
            assert r["y_proba"].shape == (r["val_size"], 2)


# ---------------------------------------------------------------------------
# Tests feature_importances()
# ---------------------------------------------------------------------------

class TestBaselineModelFeatureImportances:
    def test_importances_raises_if_not_fitted(self):
        m = BaselineModel()
        with pytest.raises(RuntimeError):
            m.feature_importances()

    def test_dummy_returns_none(self, simple_dataset):
        X, y = simple_dataset
        m = BaselineModel(model_type="dummy").fit(X, y)
        assert m.feature_importances() is None

    def test_lr_returns_series(self, simple_dataset):
        X, y = simple_dataset
        m = BaselineModel(model_type="logistic_regression").fit(X, y)
        imp = m.feature_importances()
        assert isinstance(imp, pd.Series)

    def test_rf_returns_series(self, simple_dataset):
        X, y = simple_dataset
        m = BaselineModel(model_type="random_forest").fit(X, y)
        imp = m.feature_importances()
        assert isinstance(imp, pd.Series)

    def test_importances_length_matches_features(self, simple_dataset):
        X, y = simple_dataset
        for model_type in ("logistic_regression", "random_forest"):
            m = BaselineModel(model_type=model_type).fit(X, y)
            imp = m.feature_importances()
            assert len(imp) == X.shape[1]

    def test_importances_index_matches_feature_names(self, simple_dataset):
        X, y = simple_dataset
        m = BaselineModel(model_type="random_forest").fit(X, y)
        imp = m.feature_importances()
        assert list(imp.index) == sorted(X.columns, key=lambda c: imp[c], reverse=True) or \
               set(imp.index) == set(X.columns)

    def test_rf_importances_sum_to_one(self, simple_dataset):
        X, y = simple_dataset
        m = BaselineModel(model_type="random_forest").fit(X, y)
        imp = m.feature_importances()
        assert pytest.approx(imp.sum(), abs=1e-6) == 1.0

    def test_rf_importances_sorted_descending(self, simple_dataset):
        X, y = simple_dataset
        m = BaselineModel(model_type="random_forest").fit(X, y)
        imp = m.feature_importances()
        assert list(imp) == sorted(imp, reverse=True)

    def test_lr_importances_non_negative(self, simple_dataset):
        X, y = simple_dataset
        m = BaselineModel(model_type="logistic_regression").fit(X, y)
        imp = m.feature_importances()
        assert (imp >= 0).all()


# ---------------------------------------------------------------------------
# Tests dummy classifier behavior
# ---------------------------------------------------------------------------

class TestDummyClassifier:
    def test_dummy_predicts_majority_class(self, imbalanced_dataset):
        """Le DummyClassifier doit prédire uniquement la classe majoritaire."""
        X, y = imbalanced_dataset
        m = BaselineModel(model_type="dummy").fit(X, y)
        preds = m.predict(X)
        majority = int(y.mode()[0])
        assert set(np.unique(preds)) == {majority}
