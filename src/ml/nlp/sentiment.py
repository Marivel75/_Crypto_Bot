"""Sentiment analysis for crypto news using TF-IDF + Logistic Regression."""

from __future__ import annotations

import logging

import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

logger = logging.getLogger(__name__)

# Sentiment label constants (internal): 1=positive, 0=neutral, -1=negative
_LABEL_POSITIVE = 1
_LABEL_NEGATIVE = -1


class SentimentAnalyzer:
    """Train and run sentiment inference on crypto news text.

    The analyser maps raw text to a continuous score in [-1.0, 1.0]:
    - Positive (bullish news) → scores close to +1.0
    - Negative (bearish news) → scores close to -1.0
    - Neutral → scores close to 0.0

    Uses a scikit-learn Pipeline: TF-IDF vectoriser + Logistic Regression.
    The pipeline can be serialised to disk with :meth:`save` and loaded with
    :meth:`load`.

    Example::

        analyzer = SentimentAnalyzer()
        analyzer.train(texts, labels)
        score = analyzer.predict("Bitcoin ETF approved by SEC")
    """

    def __init__(self) -> None:
        self._pipeline: Pipeline | None = None
        self._is_trained: bool = False
        logger.info("SentimentAnalyzer initialised (untrained)")

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def train(self, texts: list[str], labels: list[int]) -> None:
        """Fit the TF-IDF + LR pipeline.

        Args:
            texts: List of raw news article texts / titles.
            labels: Integer sentiment labels per text.
                    Must be drawn from {-1, 0, 1}:
                    -1 = negative, 0 = neutral, 1 = positive.

        Raises:
            ValueError: If texts and labels have different lengths, or if
                        fewer than 3 unique labels are present.
        """
        if len(texts) != len(labels):
            raise ValueError(f"texts length {len(texts)} != labels length {len(labels)}")
        if len(texts) < 2:
            raise ValueError("Need at least 2 samples to train")

        unique_labels = set(labels)
        invalid = unique_labels - {-1, 0, 1}
        if invalid:
            raise ValueError(f"labels must be in {{-1, 0, 1}}, found: {invalid}")

        vectorizer = TfidfVectorizer(
            max_features=10_000,
            ngram_range=(1, 2),
            sublinear_tf=True,
            strip_accents="unicode",
            min_df=2,
        )
        classifier = LogisticRegression(
            max_iter=1000,
            class_weight="balanced",
            solver="lbfgs",
            C=1.0,
            random_state=42,
        )
        self._pipeline = Pipeline(
            [("tfidf", vectorizer), ("clf", classifier)],
            memory=None,
        )
        self._pipeline.fit(texts, labels)
        self._is_trained = True
        logger.info(
            "SentimentAnalyzer trained on %d samples (%d unique classes)",
            len(texts),
            len(unique_labels),
        )

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------

    def predict(self, text: str) -> float:
        """Predict the sentiment score for a single text.

        Args:
            text: Raw news text or headline.

        Returns:
            Sentiment score in [-1.0, 1.0].

        Raises:
            RuntimeError: If called before :meth:`train` or :meth:`load`.
        """
        if not self._is_trained or self._pipeline is None:
            raise RuntimeError("SentimentAnalyzer must be trained before predict()")

        scores = self._score_texts([text])
        return float(scores[0])

    def batch_predict(self, texts: list[str]) -> list[float]:
        """Predict sentiment scores for a batch of texts.

        Args:
            texts: List of raw news texts.

        Returns:
            List of sentiment scores in [-1.0, 1.0], one per input text.

        Raises:
            RuntimeError: If called before :meth:`train` or :meth:`load`.
        """
        if not self._is_trained or self._pipeline is None:
            raise RuntimeError("SentimentAnalyzer must be trained before batch_predict()")

        if not texts:
            return []

        return [float(s) for s in self._score_texts(texts)]

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, path: str) -> None:
        """Serialise the trained pipeline to disk with joblib.

        Args:
            path: File path to write (e.g. ``"sentiment_pipeline.joblib"``).

        Raises:
            RuntimeError: If the analyser has not been trained yet.
        """
        if not self._is_trained or self._pipeline is None:
            raise RuntimeError("Cannot save an untrained SentimentAnalyzer")
        joblib.dump(self._pipeline, path)
        logger.info("SentimentAnalyzer pipeline saved to %s", path)

    def load(self, path: str) -> None:
        """Load a serialised pipeline from disk.

        Args:
            path: File path previously written by :meth:`save`.

        Raises:
            FileNotFoundError: If the pipeline file does not exist.
            RuntimeError: If the loaded object is not a valid sklearn Pipeline.
        """
        try:
            loaded = joblib.load(path)
        except FileNotFoundError:
            logger.error("Sentiment pipeline file not found: %s", path)
            raise
        except Exception:
            logger.exception("Failed to load sentiment pipeline from %s", path)
            raise

        if not hasattr(loaded, "predict_proba"):
            raise RuntimeError(
                f"Loaded object from {path} does not have a predict_proba method — expected a trained sklearn Pipeline"
            )

        self._pipeline = loaded
        self._is_trained = True
        logger.info("SentimentAnalyzer pipeline loaded from %s", path)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _score_texts(self, texts: list[str]) -> np.ndarray:
        """Convert class probabilities to a [-1, 1] continuous score.

        The pipeline's ``predict_proba`` returns one column per class.
        We weight: score = P(positive) * 1 + P(neutral) * 0 + P(negative) * -1.

        Args:
            texts: Batch of input texts.

        Returns:
            1-D numpy array of float scores.
        """
        if self._pipeline is None:
            raise RuntimeError("Sentiment pipeline is not trained; call fit() before predict_proba.")
        clf: LogisticRegression = self._pipeline.named_steps["clf"]
        classes: np.ndarray = clf.classes_  # e.g. [-1, 0, 1]

        probas = self._pipeline.predict_proba(texts)  # shape (N, n_classes)

        # Build weight vector aligned to clf.classes_ order
        weights = np.array([float(c) for c in classes])
        scores: np.ndarray = probas @ weights
        return np.clip(scores, -1.0, 1.0)  # type: ignore[no-any-return]
