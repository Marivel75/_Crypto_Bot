"""Analytics module for market analysis and volatility computation.

Provides utilities for cross-symbol correlation, volatility analysis,
and market regime detection (trending/ranging/volatile).
"""

from __future__ import annotations

import logging
from typing import Literal

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class CorrelationMatrix(BaseModel):
    """Cross-symbol correlation matrix result.

    Attributes:
        symbols: Sorted list of symbol pairs.
        correlations: Dict mapping symbol pair tuple to correlation value.
        timestamp: When the correlation was computed.
    """

    symbols: list[str] = Field(description="Symbols in correlation matrix")
    correlations: dict[str, float] = Field(description="Pairwise correlations")
    timestamp: pd.Timestamp = Field(description="Computation timestamp")


class VolatilityResult(BaseModel):
    """Historical volatility computation result.

    Attributes:
        symbol: Trading pair symbol.
        volatility: Annualised volatility (standard deviation of returns).
        rolling_window: Number of periods used in rolling window.
        timestamp: When computation occurred.
    """

    symbol: str = Field(description="Trading symbol")
    volatility: float = Field(description="Annualised volatility", ge=0)
    rolling_window: int = Field(description="Window size in periods", ge=1)
    timestamp: pd.Timestamp = Field(description="Computation timestamp")


class MarketRegime(BaseModel):
    """Market regime classification result.

    Attributes:
        regime: One of 'trending', 'ranging', or 'volatile'.
        confidence: Confidence score in [0, 1] for the classification.
        detail: Human-readable explanation.
    """

    regime: Literal["trending", "ranging", "volatile"] = Field(description="Market regime classification")
    confidence: float = Field(description="Classification confidence", ge=0, le=1)
    detail: str = Field(description="Explanation of regime classification")


def compute_correlation_matrix(
    df: pd.DataFrame,
    *,
    min_periods: int = 20,
) -> CorrelationMatrix:
    """Compute cross-symbol correlation matrix from price data.

    Args:
        df: DataFrame with columns named by symbol (e.g., 'BTCUSDT', 'ETHUSDT'),
            values are prices, and a DatetimeIndex. Index must be sorted ascending.
        min_periods: Minimum number of observations per pair. Pairs with fewer
            observations are set to NaN.

    Returns:
        CorrelationMatrix with all pairwise correlations.

    Raises:
        ValueError: If DataFrame is empty or has fewer than 2 columns.
    """
    if df.empty or len(df.columns) < 2:
        raise ValueError(
            f"compute_correlation_matrix requires a non-empty DataFrame with ≥2 columns, got shape {df.shape}"
        )

    # Compute pairwise correlations
    corr_matrix = df.corr(min_periods=min_periods)

    # Flatten to dict: key is comma-separated symbol pair, value is correlation
    correlations: dict[str, float] = {}
    for i, col1 in enumerate(df.columns):
        for j, col2 in enumerate(df.columns):
            if i < j:
                key = f"{col1},{col2}"
                value = float(corr_matrix.loc[col1, col2])
                correlations[key] = value

    result = CorrelationMatrix(
        symbols=list(df.columns),
        correlations=correlations,
        timestamp=pd.Timestamp.now(),
    )
    logger.info(
        "compute_correlation_matrix: %d symbols, %d pairs",
        len(result.symbols),
        len(result.correlations),
    )
    return result


def compute_volatility(
    df: pd.DataFrame,
    *,
    window: int = 20,
    periods_per_year: int = 252,
) -> VolatilityResult:
    """Compute annualised historical volatility from a single price series.

    Volatility is computed as the standard deviation of log returns,
    annualised by the given period count.

    Args:
        df: Series or DataFrame with a price column (must have only 1 column if DataFrame).
            Index must be sorted ascending.
        window: Rolling window size in periods.
        periods_per_year: Annualisation factor (default 252 for daily data,
            1440 for minute data, etc.).

    Returns:
        VolatilityResult with annualised volatility and computation timestamp.

    Raises:
        ValueError: If series is empty, has fewer than window+1 observations,
            or if DataFrame has multiple columns.
    """
    if isinstance(df, pd.DataFrame):
        if len(df.columns) != 1:
            raise ValueError(f"compute_volatility requires a single-column DataFrame, got {len(df.columns)} columns")
        series = df.iloc[:, 0]
    else:
        series = df

    if len(series) < window + 1:
        raise ValueError(f"compute_volatility requires ≥{window + 1} observations, got {len(series)}")

    # Compute log returns
    log_returns = np.log(series / series.shift(1)).dropna()

    if len(log_returns) < 2:
        raise ValueError(f"Insufficient data for volatility computation: {len(log_returns)} returns")

    # Annualised volatility
    volatility = float(log_returns.std() * np.sqrt(periods_per_year))

    symbol = series.name if series.name else "unknown"

    result = VolatilityResult(
        symbol=str(symbol),
        volatility=volatility,
        rolling_window=window,
        timestamp=pd.Timestamp.now(),
    )
    logger.info(
        "compute_volatility: symbol=%s, volatility=%.4f, periods=%d",
        result.symbol,
        result.volatility,
        len(log_returns),
    )
    return result


def detect_market_regime(
    df: pd.DataFrame,
    *,
    short_window: int = 14,
    long_window: int = 50,
    volatility_threshold: float = 0.02,
) -> MarketRegime:
    """Classify market regime as trending, ranging, or volatile.

    Classification logic:
    - **Trending**: Price is above/below both short and long moving averages
      AND volatility is below threshold.
    - **Volatile**: Standard deviation of short returns exceeds threshold.
    - **Ranging**: Price oscillates around moving average band.

    Args:
        df: Series or DataFrame with a close price column.
            Must have ≥long_window observations.
        short_window: Short moving average period (default 14).
        long_window: Long moving average period (default 50).
        volatility_threshold: Threshold for classification as volatile (default 0.02 = 2%).

    Returns:
        MarketRegime with classification and confidence score.

    Raises:
        ValueError: If series has insufficient data.
    """
    if isinstance(df, pd.DataFrame):
        if len(df.columns) != 1:
            raise ValueError(f"detect_market_regime requires a single-column DataFrame, got {len(df.columns)} columns")
        series = df.iloc[:, 0]
    else:
        series = df

    if len(series) < long_window + 1:
        raise ValueError(f"detect_market_regime requires ≥{long_window + 1} observations, got {len(series)}")

    # Compute moving averages
    ma_short = series.rolling(short_window).mean()
    ma_long = series.rolling(long_window).mean()

    # Current values (latest)
    current_price = float(series.iloc[-1])
    ma_short_val = float(ma_short.iloc[-1])
    ma_long_val = float(ma_long.iloc[-1])

    # Compute volatility
    returns = series.pct_change().dropna()
    current_volatility = float(returns.std())

    # Determine regime
    regime: Literal["trending", "ranging", "volatile"]
    confidence: float
    detail: str

    if current_volatility > volatility_threshold:
        regime = "volatile"
        confidence = min(1.0, current_volatility / (volatility_threshold * 2))
        detail = f"High volatility ({current_volatility:.4f} > {volatility_threshold:.4f}); price oscillating sharply"
    elif current_price > ma_short_val > ma_long_val:
        regime = "trending"
        confidence = min(1.0, (current_price - ma_long_val) / (ma_short_val - ma_long_val + 1e-9))
        detail = f"Strong uptrend: price {current_price:.2f} > MA{short_window} > MA{long_window}"
    elif current_price < ma_short_val < ma_long_val:
        regime = "trending"
        confidence = min(1.0, (ma_long_val - current_price) / (ma_long_val - ma_short_val + 1e-9))
        detail = f"Strong downtrend: price {current_price:.2f} < MA{short_window} < MA{long_window}"
    else:
        regime = "ranging"
        distance_to_ma = abs(current_price - ma_short_val)
        max_distance = abs(ma_short_val - ma_long_val) + 1e-9
        confidence = max(0.0, 1.0 - (distance_to_ma / max_distance))
        detail = f"Range-bound: price {current_price:.2f} oscillating around MAs"

    result = MarketRegime(regime=regime, confidence=confidence, detail=detail)
    logger.info(
        "detect_market_regime: regime=%s, confidence=%.4f, volatility=%.4f",
        regime,
        confidence,
        current_volatility,
    )
    return result
