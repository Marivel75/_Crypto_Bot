"""Unit tests for SentimentAnalyzer."""

from __future__ import annotations

import pytest

from src.ml.nlp.sentiment import SentimentAnalyzer

# ---------------------------------------------------------------------------
# Training data fixture
# ---------------------------------------------------------------------------

_POSITIVE_TEXTS = [
    "Bitcoin ETF approved by SEC, markets rally",
    "Ethereum upgrade successful, price surges to new highs",
    "Crypto adoption growing rapidly across institutions",
    "Major bank announces Bitcoin custody service",
    "DeFi total value locked reaches all-time high",
]

_NEGATIVE_TEXTS = [
    "Crypto exchange hacked, millions stolen",
    "Bitcoin crashes below support level amid sell-off",
    "Regulatory crackdown on crypto intensifies globally",
    "Major stablecoin depegs causing market panic",
    "Crypto firm files for bankruptcy after liquidity crisis",
]

_NEUTRAL_TEXTS = [
    "Bitcoin trading volume remains steady at current levels",
    "New cryptocurrency project launches on testnet",
    "Blockchain conference scheduled for next quarter",
    "Crypto market cap unchanged in sideways trading",
    "Developer community discusses protocol upgrade timeline",
]


def _training_data() -> tuple[list[str], list[int]]:
    """Return (texts, labels) for training."""
    texts = _POSITIVE_TEXTS + _NEGATIVE_TEXTS + _NEUTRAL_TEXTS
    labels = [1] * len(_POSITIVE_TEXTS) + [-1] * len(_NEGATIVE_TEXTS) + [0] * len(_NEUTRAL_TEXTS)
    return texts, labels


# ---------------------------------------------------------------------------
# Tests: initialisation and training
# ---------------------------------------------------------------------------


class TestTraining:
    def test_predict_before_train_raises(self) -> None:
        analyzer = SentimentAnalyzer()
        with pytest.raises(RuntimeError, match="must be trained"):
            analyzer.predict("some text")

    def test_batch_predict_before_train_raises(self) -> None:
        analyzer = SentimentAnalyzer()
        with pytest.raises(RuntimeError, match="must be trained"):
            analyzer.batch_predict(["text"])

    def test_train_with_mismatched_lengths_raises(self) -> None:
        analyzer = SentimentAnalyzer()
        with pytest.raises(ValueError, match="length"):
            analyzer.train(["a", "b"], [1])

    def test_train_with_insufficient_samples_raises(self) -> None:
        analyzer = SentimentAnalyzer()
        with pytest.raises(ValueError, match="at least 2"):
            analyzer.train(["a"], [1])

    def test_train_with_invalid_labels_raises(self) -> None:
        analyzer = SentimentAnalyzer()
        with pytest.raises(ValueError, match="must be in"):
            analyzer.train(["a", "b", "c"], [1, -1, 5])

    def test_train_succeeds(self) -> None:
        analyzer = SentimentAnalyzer()
        texts, labels = _training_data()
        analyzer.train(texts, labels)
        # Should not raise
        score = analyzer.predict("test text")
        assert isinstance(score, float)


# ---------------------------------------------------------------------------
# Tests: prediction quality
# ---------------------------------------------------------------------------


class TestPredictionQuality:
    @pytest.fixture()
    def trained_analyzer(self) -> SentimentAnalyzer:
        analyzer = SentimentAnalyzer()
        texts, labels = _training_data()
        analyzer.train(texts, labels)
        return analyzer

    def test_positive_text_scores_positive(self, trained_analyzer: SentimentAnalyzer) -> None:
        score = trained_analyzer.predict("Bitcoin price surges after ETF approval")
        assert score > 0.0

    def test_negative_text_scores_negative(self, trained_analyzer: SentimentAnalyzer) -> None:
        score = trained_analyzer.predict("Crypto exchange hack causes massive losses and panic")
        assert score < 0.0

    def test_score_in_valid_range(self, trained_analyzer: SentimentAnalyzer) -> None:
        score = trained_analyzer.predict("Random text about the market")
        assert -1.0 <= score <= 1.0

    def test_batch_predict_returns_correct_length(self, trained_analyzer: SentimentAnalyzer) -> None:
        texts = ["Good news about crypto", "Bad news about exchange", "Neutral statement"]
        scores = trained_analyzer.batch_predict(texts)
        assert len(scores) == 3
        assert all(-1.0 <= s <= 1.0 for s in scores)

    def test_batch_predict_empty_returns_empty(self, trained_analyzer: SentimentAnalyzer) -> None:
        assert trained_analyzer.batch_predict([]) == []


# ---------------------------------------------------------------------------
# Tests: persistence
# ---------------------------------------------------------------------------


class TestPersistence:
    def test_save_before_train_raises(self, tmp_path) -> None:
        analyzer = SentimentAnalyzer()
        with pytest.raises(RuntimeError, match="untrained"):
            analyzer.save(str(tmp_path / "model.joblib"))

    def test_save_and_load_roundtrip(self, tmp_path) -> None:
        analyzer = SentimentAnalyzer()
        texts, labels = _training_data()
        analyzer.train(texts, labels)

        model_path = str(tmp_path / "model.joblib")
        analyzer.save(model_path)

        loaded = SentimentAnalyzer()
        loaded.load(model_path)

        original_score = analyzer.predict("Bitcoin rally continues")
        loaded_score = loaded.predict("Bitcoin rally continues")
        assert abs(original_score - loaded_score) < 1e-6
