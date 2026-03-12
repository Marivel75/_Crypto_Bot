"""Feature engineering — convert indicator/OHLCV history into a feature matrix."""

from __future__ import annotations

import logging
from decimal import Decimal

import numpy as np
import pandas as pd

from src.shared.models.crypto import IndicatorRecord, OHLCVRecord

logger = logging.getLogger(__name__)


def _safe_float(val: Decimal | None) -> float:
    """Convert a nullable Decimal to float, returning NaN when absent.

    Args:
        val: Decimal value or None.

    Returns:
        Float equivalent, or ``float('nan')`` if ``val`` is None.
    """
    if val is None:
        return np.nan
    return float(val)


def build_feature_matrix(
    indicators_by_tf: dict[str, list[IndicatorRecord]],
    ohlcv: list[OHLCVRecord] | None = None,
    sentiment_scores: list[float] | None = None,
    fear_greed: list[float] | None = None,
) -> pd.DataFrame:
    """Build a pandas DataFrame of features for ML training/prediction.

    Each row corresponds to a timestamp. Features include:
    - RSI per timeframe
    - RSI gap between adjacent TFs
    - Bollinger position per TF
    - Bollinger squeeze flag per TF
    - Trend slope per TF
    - Harmonic pattern one-hot per TF
    - Volume (from OHLCV)
    - Fear & Greed index
    - Sentiment score

    Args:
        indicators_by_tf: Mapping from timeframe to list of indicators (sorted by time).
        ohlcv: Optional OHLCV records for volume features (same timeframe as primary).
        sentiment_scores: Optional sentiment scores aligned by timestamp.
        fear_greed: Optional Fear & Greed index values aligned by timestamp.

    Returns:
        DataFrame with one row per timestamp, NaN for missing values.
    """
    # Use the first available TF as the primary index
    primary_tf = next(iter(indicators_by_tf), None)
    if primary_tf is None:
        logger.warning("No indicator data provided to build_feature_matrix")
        return pd.DataFrame()

    primary_indicators = indicators_by_tf[primary_tf]
    if not primary_indicators:
        return pd.DataFrame()

    timestamps = [ind.timestamp for ind in primary_indicators]
    rows: list[dict[str, float]] = []

    for i, _ind in enumerate(primary_indicators):
        row: dict[str, float] = {}

        # Primary TF indicators
        for tf, tf_indicators in indicators_by_tf.items():
            ind_at_i = tf_indicators[i] if i < len(tf_indicators) else None

            if ind_at_i is not None:
                row[f"rsi_{tf}"] = _safe_float(ind_at_i.rsi)
                row[f"bollinger_pos_{tf}"] = _safe_float(ind_at_i.price_vs_bollinger)
                row[f"trend_slope_{tf}"] = _safe_float(ind_at_i.trend_slope)

                # Bollinger squeeze flag
                upper = _safe_float(ind_at_i.bollinger_upper)
                lower = _safe_float(ind_at_i.bollinger_lower)
                middle = _safe_float(ind_at_i.bollinger_middle)
                if not np.isnan(upper) and not np.isnan(lower) and not np.isnan(middle) and middle != 0:
                    row[f"bollinger_bw_{tf}"] = (upper - lower) / middle
                else:
                    row[f"bollinger_bw_{tf}"] = np.nan

                # Harmonic pattern one-hot
                pattern = ind_at_i.harmonic_pattern
                for p in ("gartley", "butterfly", "bat", "crab"):
                    row[f"harmonic_{p}_{tf}"] = 1.0 if pattern and pattern.lower() == p else 0.0
            else:
                row[f"rsi_{tf}"] = np.nan
                row[f"bollinger_pos_{tf}"] = np.nan
                row[f"trend_slope_{tf}"] = np.nan
                row[f"bollinger_bw_{tf}"] = np.nan
                for p in ("gartley", "butterfly", "bat", "crab"):
                    row[f"harmonic_{p}_{tf}"] = 0.0

        # RSI gaps between adjacent TFs
        tf_list = list(indicators_by_tf.keys())
        for j in range(len(tf_list) - 1):
            tf_a = tf_list[j]
            tf_b = tf_list[j + 1]
            rsi_a = row.get(f"rsi_{tf_a}", np.nan)
            rsi_b = row.get(f"rsi_{tf_b}", np.nan)
            if not np.isnan(rsi_a) and not np.isnan(rsi_b):
                row[f"rsi_gap_{tf_a}_{tf_b}"] = rsi_a - rsi_b
            else:
                row[f"rsi_gap_{tf_a}_{tf_b}"] = np.nan

        # Volume
        if ohlcv and i < len(ohlcv):
            row["volume"] = float(ohlcv[i].volume_24h)
        else:
            row["volume"] = np.nan

        # Sentiment
        if sentiment_scores and i < len(sentiment_scores):
            row["sentiment"] = sentiment_scores[i]
        else:
            row["sentiment"] = np.nan

        # Fear & Greed
        if fear_greed and i < len(fear_greed):
            row["fear_greed"] = fear_greed[i]
        else:
            row["fear_greed"] = np.nan

        rows.append(row)

    df = pd.DataFrame(rows, index=pd.DatetimeIndex(timestamps, name="timestamp"))
    logger.info("Built feature matrix: %d rows x %d columns", len(df), len(df.columns))
    return df
