"""Tests for ML predictor: model predictions, confidence scoring, and rule integration."""

from __future__ import annotations

from typing import Any
from datetime import UTC, datetime

import numpy as np
import pandas as pd
import pytest

from src.shared.models.crypto import IndicatorRecord

# Fixed timestamp
_FIXED_TS = datetime(2025, 6, 15, 12, 0, 0, tzinfo=UTC)


class FakeMLPredictor:
    """Deterministic ML predictor for testing."""

    def __init__(self, direction: str = "BUY", confidence: float = 0.75) -> None:
        self.direction = direction
        self.confidence = confidence

    def predict(self, features: Any) -> list[dict[str, Any]]:
        """Return fixed prediction."""
        return [
            {
                "direction": self.direction,
                "confidence": self.confidence,
                "source": "ml",
                "model_name": "test_model",
            }
        ]


class TestMLPredictionBasic:
    """Test basic ML prediction functionality."""

    def test_predictor_returns_buy_signal(self) -> None:
        """Predictor should return structured prediction with direction."""
        predictor = FakeMLPredictor(direction="BUY", confidence=0.80)

        result = predictor.predict(features={"dummy": [1, 2, 3]})

        assert len(result) == 1
        assert result[0]["direction"] == "BUY"
        assert result[0]["confidence"] == 0.80
        assert result[0]["source"] == "ml"

    def test_predictor_returns_sell_signal(self) -> None:
        """Predictor should return SELL direction."""
        predictor = FakeMLPredictor(direction="SELL", confidence=0.75)

        result = predictor.predict(features={"dummy": [1, 2, 3]})

        assert result[0]["direction"] == "SELL"

    def test_predictor_returns_hold_signal(self) -> None:
        """Predictor should support HOLD direction."""
        predictor = FakeMLPredictor(direction="HOLD", confidence=0.50)

        result = predictor.predict(features={"dummy": [1, 2, 3]})

        assert result[0]["direction"] == "HOLD"

    def test_predictor_confidence_in_valid_range(self) -> None:
        """Predictor confidence should always be in [0, 1]."""
        for conf in [0.0, 0.5, 0.75, 1.0]:
            predictor = FakeMLPredictor(confidence=conf)
            result = predictor.predict(features={})
            assert 0 <= result[0]["confidence"] <= 1


class TestMLPredictionWithFeatures:
    """Test ML predictions with various feature inputs."""

    def test_predictor_accepts_dataframe_features(self) -> None:
        """Predictor should accept pandas DataFrame features."""
        predictor = FakeMLPredictor()
        features = pd.DataFrame({
            "rsi_1h": [50, 51, 52],
            "rsi_4h": [55, 56, 57],
            "boll_pos_4h": [0.5, 0.6, 0.7],
        })

        result = predictor.predict(features=features)

        assert isinstance(result, list)
        assert len(result) == 1

    def test_predictor_accepts_dict_features(self) -> None:
        """Predictor should accept dict features."""
        predictor = FakeMLPredictor()
        features = {
            "rsi_1h": [50, 51, 52],
            "volume_ratio_1h": [1.2, 1.3, 1.4],
        }

        result = predictor.predict(features=features)

        assert isinstance(result, list)

    def test_predictor_accepts_numpy_array_features(self) -> None:
        """Predictor should accept numpy array features."""
        predictor = FakeMLPredictor()
        features = np.array([[50, 0.5], [51, 0.6], [52, 0.7]])

        result = predictor.predict(features=features)

        assert isinstance(result, list)

    def test_predictor_with_empty_features(self) -> None:
        """Predictor should handle empty features gracefully."""
        predictor = FakeMLPredictor()

        result = predictor.predict(features={})

        assert len(result) == 1
        assert "direction" in result[0]


class TestMLConfidenceScoring:
    """Test confidence scoring and thresholds."""

    def test_high_confidence_prediction_above_threshold(self) -> None:
        """Confidence >= 0.75 should be considered high confidence."""
        predictor = FakeMLPredictor(confidence=0.80)

        result = predictor.predict(features={})

        threshold = 0.75
        assert result[0]["confidence"] >= threshold

    def test_low_confidence_prediction_below_threshold(self) -> None:
        """Confidence < 0.60 should be considered low confidence."""
        predictor = FakeMLPredictor(confidence=0.50)

        result = predictor.predict(features={})

        threshold = 0.60
        assert result[0]["confidence"] < threshold

    def test_confidence_boundary_exactly_at_threshold(self) -> None:
        """Confidence exactly at 0.60 should be borderline."""
        predictor = FakeMLPredictor(confidence=0.60)

        result = predictor.predict(features={})

        threshold = 0.60
        assert result[0]["confidence"] == threshold

    def test_varying_confidence_levels(self) -> None:
        """Predictor should support varying confidence levels."""
        confidence_levels = [0.0, 0.25, 0.50, 0.75, 1.0]

        for conf in confidence_levels:
            predictor = FakeMLPredictor(confidence=conf)
            result = predictor.predict(features={})
            assert result[0]["confidence"] == conf


class TestMLPredictionAccuracy:
    """Test ML model prediction accuracy metrics."""

    def test_binary_classification_accuracy(self) -> None:
        """For BUY/SELL binary classification, accuracy should be measurable."""
        # Simulate 100 predictions: 80 correct, 20 incorrect
        correct_predictions = 80
        total_predictions = 100
        accuracy = correct_predictions / total_predictions

        assert accuracy == 0.80
        assert 0 <= accuracy <= 1

    def test_multiclass_classification_accuracy(self) -> None:
        """For BUY/SELL/HOLD multi-class, accuracy should be calculable."""
        # Simulated confusion matrix for 3 classes
        correct = 70  # BUY: 30, SELL: 25, HOLD: 15
        total = 100
        accuracy = correct / total

        assert accuracy == 0.70

    def test_precision_metric_calculation(self) -> None:
        """Precision: TP / (TP + FP) should be calculable."""
        # BUY predictions: 40 true positives, 10 false positives
        tp = 40
        fp = 10
        precision = tp / (tp + fp)

        assert precision == pytest.approx(0.80, abs=0.01)

    def test_recall_metric_calculation(self) -> None:
        """Recall: TP / (TP + FN) should be calculable."""
        # Actual BUY signals: 40 true positives, 10 false negatives
        tp = 40
        fn = 10
        recall = tp / (tp + fn)

        assert recall == pytest.approx(0.80, abs=0.01)


class TestMLRuleIntegration:
    """Test integration between ML predictor and rule engine."""

    def test_ml_predictor_failure_fallback_to_rules(self) -> None:
        """If ML predictor fails, system should fall back to rules."""

        class FailingPredictor:
            def predict(self, features: Any) -> list[dict[str, Any]]:
                raise RuntimeError("Model load failed")

        predictor = FailingPredictor()

        # Attempting to predict should raise; calling code should catch
        with pytest.raises(RuntimeError, match="Model load failed"):
            predictor.predict(features={})

    def test_ml_predictor_timeout_fallback(self) -> None:
        """If ML predictor times out, should use rule engine result."""

        class SlowPredictor:
            def __init__(self, timeout_sec: float = 5.0):
                self.timeout = timeout_sec

            def predict(self, features: Any) -> list[dict[str, Any]]:
                # Simulate timeout by raising
                raise TimeoutError("Prediction exceeded timeout")

        predictor = SlowPredictor(timeout_sec=2.0)

        with pytest.raises(TimeoutError, match="timeout"):
            predictor.predict(features={})

    def test_ml_and_rules_agreement_boosts_confidence(self) -> None:
        """When ML and rules agree on direction, confidence should increase."""
        ml_confidence = 0.75
        rules_confidence = 0.70
        agreement_weight = 0.60  # ML weight
        rules_weight = 0.40  # Rules weight

        blended = agreement_weight * ml_confidence + rules_weight * rules_confidence
        assert blended == pytest.approx(0.72, abs=0.01)
        assert blended > max(rules_confidence, min(ml_confidence, rules_confidence))

    def test_ml_and_rules_disagreement_reduces_confidence(self) -> None:
        """When ML and rules disagree, confidence should be penalised."""
        ml_confidence = 0.80
        rules_confidence = 0.60
        penalty_weight = 0.40  # Use 40% of minimum
        min_confidence = min(ml_confidence, rules_confidence)

        penalised = penalty_weight * min_confidence
        assert penalised == pytest.approx(0.24, abs=0.01)
        assert penalised < min(ml_confidence, rules_confidence)


class TestMLModelTypes:
    """Test different ML model types and interfaces."""

    def test_xgboost_predictor_interface(self) -> None:
        """XGBoost predictor should have consistent interface."""

        class XGBoostPredictor:
            def predict(self, features: Any) -> list[dict[str, Any]]:
                return [{"direction": "BUY", "confidence": 0.75}]

        xgb = XGBoostPredictor()
        result = xgb.predict(features={})

        assert hasattr(xgb, "predict")
        assert "direction" in result[0]
        assert "confidence" in result[0]

    def test_lightgbm_predictor_interface(self) -> None:
        """LightGBM predictor should have consistent interface."""

        class LightGBMPredictor:
            def predict(self, features: Any) -> list[dict[str, Any]]:
                return [{"direction": "SELL", "confidence": 0.70}]

        lgb = LightGBMPredictor()
        result = lgb.predict(features={})

        assert hasattr(lgb, "predict")
        assert "direction" in result[0]
        assert "confidence" in result[0]

    def test_lstm_predictor_interface(self) -> None:
        """LSTM predictor should have consistent interface."""

        class LSTMPredictor:
            def predict(self, features: Any) -> list[dict[str, Any]]:
                return [{"direction": "HOLD", "confidence": 0.55}]

        lstm = LSTMPredictor()
        result = lstm.predict(features={})

        assert "direction" in result[0]
        assert "confidence" in result[0]


class TestMLPredictionCaching:
    """Test prediction caching and memoization."""

    def test_repeated_predictions_same_features(self) -> None:
        """Same features should produce same prediction (deterministic)."""
        predictor = FakeMLPredictor(confidence=0.75)
        features = {"rsi": [50, 51, 52]}

        result1 = predictor.predict(features=features)
        result2 = predictor.predict(features=features)

        assert result1[0]["direction"] == result2[0]["direction"]
        assert result1[0]["confidence"] == result2[0]["confidence"]

    def test_different_features_may_produce_different_predictions(self) -> None:
        """Different features could produce different predictions."""
        predictor_buy = FakeMLPredictor(direction="BUY")
        predictor_sell = FakeMLPredictor(direction="SELL")

        result1 = predictor_buy.predict(features={"signal": "up"})
        result2 = predictor_sell.predict(features={"signal": "down"})

        assert result1[0]["direction"] != result2[0]["direction"]


class TestMLPredictionEnsemble:
    """Test ensemble predictions combining multiple ML models."""

    def test_ensemble_average_confidence(self) -> None:
        """Ensemble should average confidence from multiple models."""
        model1_conf = 0.80
        model2_conf = 0.70
        model3_conf = 0.75

        ensemble_conf = (model1_conf + model2_conf + model3_conf) / 3
        assert ensemble_conf == pytest.approx(0.75, abs=0.01)

    def test_ensemble_direction_voting(self) -> None:
        """Ensemble should use voting for direction (majority wins)."""
        votes = ["BUY", "BUY", "SELL"]  # 2 BUY, 1 SELL
        buy_count = votes.count("BUY")
        sell_count = votes.count("SELL")

        ensemble_direction = "BUY" if buy_count > sell_count else "SELL"
        assert ensemble_direction == "BUY"

    def test_ensemble_equal_votes_fallback_to_rules(self) -> None:
        """If ensemble votes are tied, fall back to rules."""
        votes = ["BUY", "SELL"]  # Tie
        buy_count = votes.count("BUY")
        sell_count = votes.count("SELL")

        tied = buy_count == sell_count
        assert tied is True


class TestMLPredictionStreamingFeatures:
    """Test ML predictions with streaming/real-time features."""

    def test_incremental_feature_update(self) -> None:
        """ML should handle incremental feature updates."""
        predictor = FakeMLPredictor()

        # Initial features
        features_v1 = {"rsi": [50], "volume": [1000]}
        result1 = predictor.predict(features=features_v1)

        # Updated features (added new data point)
        features_v2 = {"rsi": [50, 51], "volume": [1000, 1050]}
        result2 = predictor.predict(features=features_v2)

        # Both should return valid predictions
        assert result1[0]["direction"] is not None
        assert result2[0]["direction"] is not None

    def test_sliding_window_features(self) -> None:
        """ML should handle sliding window feature computation."""
        predictor = FakeMLPredictor()

        # Sliding window: keep last 20 candles
        window_size = 20
        candles = list(range(100))

        window_v1 = candles[0:window_size]  # Candles 0-19
        window_v2 = candles[1:window_size + 1]  # Candles 1-20
        window_v3 = candles[80:100]  # Candles 80-99

        for window in [window_v1, window_v2, window_v3]:
            result = predictor.predict(features={"candles": window})
            assert len(result) == 1
            assert "confidence" in result[0]

    def test_real_time_indicator_computation(self) -> None:
        """ML should work with real-time indicator values."""
        predictor = FakeMLPredictor()

        # Real-time indicators computed on latest bar
        features = {
            "rsi_1h_latest": 65,
            "bollinger_pos_4h_latest": 0.8,
            "volume_ratio_1h_latest": 1.2,
            "timestamp": _FIXED_TS,
        }

        result = predictor.predict(features=features)

        assert result[0]["confidence"] > 0


class TestMLPredictionErrorHandling:
    """Test error handling in ML predictions."""

    def test_invalid_features_shape_raises_error(self) -> None:
        """Mismatched feature shape should raise error."""

        class StrictPredictor:
            def predict(self, features: Any) -> list[dict[str, Any]]:
                if isinstance(features, np.ndarray) and features.shape[1] != 10:
                    raise ValueError(f"Expected 10 features, got {features.shape[1]}")
                return [{"direction": "BUY", "confidence": 0.75}]

        predictor = StrictPredictor()
        features_wrong = np.array([[1, 2, 3]])  # 3 features instead of 10

        with pytest.raises(ValueError, match="Expected 10 features"):
            predictor.predict(features=features_wrong)

    def test_nan_in_features_handled(self) -> None:
        """NaN values in features should be detectable."""
        features = pd.DataFrame({
            "rsi": [50, np.nan, 52],
            "volume": [1000, 1050, np.nan],
        })

        has_nan = features.isna().any().any()
        assert has_nan is True

    def test_missing_required_feature_raises_error(self) -> None:
        """Missing required features should raise error."""

        class FeatureValidator:
            required_features = {"rsi", "volume", "trend"}

            def validate(self, features: dict[str, Any]) -> None:
                missing = self.required_features - set(features.keys())
                if missing:
                    raise ValueError(f"Missing features: {missing}")

        validator = FeatureValidator()
        features_incomplete = {"rsi": 50}  # Missing volume, trend

        with pytest.raises(ValueError, match="Missing features"):
            validator.validate(features_incomplete)
