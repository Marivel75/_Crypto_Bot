"""Feature builder — high-level API over ``feature_engineering.py``.

This module exposes a ``FeatureBuilder`` class that wraps the low-level
``build_feature_matrix`` function with label computation and train/test
temporal splitting.  It is the primary entry point used by ``trainer.py``.

Label encoding:
    BUY  ->  1
    SELL -> -1
    HOLD ->  0
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from src.ml.models.feature_engineering import build_feature_matrix
from src.shared.models.crypto import IndicatorRecord, OHLCVRecord

logger = logging.getLogger(__name__)

# Mapping from signal string to integer label
LABEL_MAP: dict[str, int] = {"BUY": 1, "HOLD": 0, "SELL": -1}
REVERSE_LABEL_MAP: dict[int, str] = {v: k for k, v in LABEL_MAP.items()}


def _compute_future_returns(
    ohlcv: list[OHLCVRecord],
    lookahead: int = 1,
) -> list[float]:
    """Compute percentage return ``lookahead`` candles into the future.

    For row i: return = (close[i + lookahead] - close[i]) / close[i].
    The last ``lookahead`` rows have NaN returns.

    Args:
        ohlcv: OHLCV records sorted chronologically.
        lookahead: Number of candles to look ahead.

    Returns:
        List of float returns (NaN at the tail).
    """
    closes = [float(r.price_close) for r in ohlcv]
    returns: list[float] = []
    for i in range(len(closes)):
        if i + lookahead < len(closes):
            ret = (closes[i + lookahead] - closes[i]) / closes[i]
            returns.append(ret)
        else:
            returns.append(np.nan)
    return returns


def _returns_to_labels(
    returns: list[float],
    buy_threshold: float = 0.005,
    sell_threshold: float = -0.005,
) -> list[int | None]:
    """Convert future returns to BUY/HOLD/SELL integer labels.

    Args:
        returns: List of return values (may contain NaN).
        buy_threshold: Minimum positive return to label as BUY.
        sell_threshold: Maximum negative return to label as SELL.

    Returns:
        List of integer labels (1=BUY, 0=HOLD, -1=SELL) or None for NaN rows.
    """
    labels: list[int | None] = []
    for r in returns:
        if np.isnan(r):
            labels.append(None)
        elif r >= buy_threshold:
            labels.append(LABEL_MAP["BUY"])
        elif r <= sell_threshold:
            labels.append(LABEL_MAP["SELL"])
        else:
            labels.append(LABEL_MAP["HOLD"])
    return labels


class FeatureBuilder:
    """Build ML-ready feature matrices and labels from raw indicator data.

    Args:
        buy_threshold: Minimum return to label candle as BUY.
        sell_threshold: Maximum return to label candle as SELL.
        lookahead: Candles ahead used to compute the label.
        primary_tf: Primary timeframe for index alignment.
    """

    def __init__(
        self,
        buy_threshold: float = 0.005,
        sell_threshold: float = -0.005,
        lookahead: int = 1,
        primary_tf: str = "4h",
    ) -> None:
        self._buy_threshold = buy_threshold
        self._sell_threshold = sell_threshold
        self._lookahead = lookahead
        self._primary_tf = primary_tf

    def build(
        self,
        indicators_by_tf: dict[str, list[IndicatorRecord]],
        ohlcv: list[OHLCVRecord] | None = None,
        sentiment_scores: list[float] | None = None,
        fear_greed: list[float] | None = None,
    ) -> tuple[pd.DataFrame, pd.Series]:
        """Build (features, labels) for ML training.

        Args:
            indicators_by_tf: Mapping from timeframe to sorted list of indicators.
            ohlcv: Optional OHLCV records for volume features and label derivation.
            sentiment_scores: Optional per-row sentiment scores.
            fear_greed: Optional per-row Fear & Greed index values.

        Returns:
            Tuple of ``(X, y)`` where X is the feature DataFrame and y is a
            Series of integer labels (1=BUY, 0=HOLD, -1=SELL).
            Rows with NaN labels (lookahead tail) are dropped.
        """
        features = build_feature_matrix(
            indicators_by_tf=indicators_by_tf,
            ohlcv=ohlcv,
            sentiment_scores=sentiment_scores,
            fear_greed=fear_greed,
        )

        if features.empty:
            logger.warning("build_feature_matrix returned empty DataFrame")
            return features, pd.Series(dtype=int)

        # Compute labels from future returns
        if ohlcv and len(ohlcv) >= len(features):
            returns = _compute_future_returns(ohlcv, lookahead=self._lookahead)
            raw_labels = _returns_to_labels(
                returns[: len(features)],
                buy_threshold=self._buy_threshold,
                sell_threshold=self._sell_threshold,
            )
        else:
            logger.warning("No OHLCV data for label derivation — defaulting all labels to HOLD")
            raw_labels = [LABEL_MAP["HOLD"]] * len(features)

        labels_series = pd.Series(raw_labels, index=features.index, name="label")

        # Drop rows where label is None (tail lookahead rows)
        valid_mask = labels_series.notna()
        features = features.loc[valid_mask]
        labels_series = labels_series.loc[valid_mask].astype(int)

        logger.info(
            "FeatureBuilder.build: %d rows, %d features, label distribution: %s",
            len(features),
            len(features.columns),
            labels_series.value_counts().to_dict(),
        )
        return features, labels_series

    def build_for_prediction(
        self,
        indicators_by_tf: dict[str, list[IndicatorRecord]],
        ohlcv: list[OHLCVRecord] | None = None,
        sentiment_scores: list[float] | None = None,
        fear_greed: list[float] | None = None,
    ) -> pd.DataFrame:
        """Build feature matrix for inference (no labels needed).

        Args:
            indicators_by_tf: Mapping from timeframe to sorted indicators.
            ohlcv: Optional OHLCV records for volume features.
            sentiment_scores: Optional sentiment scores.
            fear_greed: Optional Fear & Greed values.

        Returns:
            Feature DataFrame (may contain NaN; caller must handle them).
        """
        return build_feature_matrix(
            indicators_by_tf=indicators_by_tf,
            ohlcv=ohlcv,
            sentiment_scores=sentiment_scores,
            fear_greed=fear_greed,
        )

    @staticmethod
    def temporal_split(
        features: pd.DataFrame,
        labels: pd.Series,
        test_fraction: float = 0.2,
    ) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
        """Split features and labels using a temporal (chronological) boundary.

        NEVER uses random splitting on time-series data.

        Args:
            features: Feature DataFrame with DatetimeIndex sorted ascending.
            labels: Label Series aligned with features.
            test_fraction: Fraction of data to use as test set (tail end).

        Returns:
            Tuple of ``(X_train, X_test, y_train, y_test)``.
        """
        split_idx = int(len(features) * (1 - test_fraction))
        x_train = features.iloc[:split_idx]
        x_test = features.iloc[split_idx:]
        y_train = labels.iloc[:split_idx]
        y_test = labels.iloc[split_idx:]
        logger.info(
            "Temporal split: train=%d rows, test=%d rows (test_fraction=%.0f%%)",
            len(x_train),
            len(x_test),
            test_fraction * 100,
        )
        return x_train, x_test, y_train, y_test
