"""Technical indicator computation for OHLCV data using pandas-ta."""

from __future__ import annotations

import logging
from decimal import Decimal

import numpy as np
import pandas as pd

from src.shared.models.crypto import IndicatorRecord

logger = logging.getLogger(__name__)

# Timeframes that get RSI + Bollinger Bands
_RSI_BB_TIMEFRAMES = ("1h", "2h", "3h", "4h", "1D")

# Timeframes that get trend analysis
_TREND_TIMEFRAMES = ("1D", "1W", "1M")


def compute_indicators_for_symbol(
    rows: list[dict[str, object]],
    symbol: str,
    timeframe: str,
) -> list[IndicatorRecord]:
    """Compute all applicable indicators for one symbol/timeframe.

    Args:
        rows: OHLCV data as list of dicts with keys: timestamp, price_open,
              price_high, price_low, price_close, volume_24h.
              Must be sorted oldest-first.
        symbol: Trading pair (e.g. "BTCUSDT").
        timeframe: Timeframe string (e.g. "4h", "1D").

    Returns:
        List of IndicatorRecord, one per row that has enough data for computation.
    """
    if len(rows) < 20:
        logger.warning(
            "Not enough data to compute indicators for %s/%s: %d rows (need >= 20)",
            symbol,
            timeframe,
            len(rows),
        )
        return []

    df = _build_dataframe(rows)
    records: list[IndicatorRecord] = []

    # Compute RSI + Bollinger for applicable timeframes
    rsi_series: pd.Series | None = None
    bb_df: pd.DataFrame | None = None
    if timeframe in _RSI_BB_TIMEFRAMES:
        rsi_series = compute_rsi(df["close"])
        bb_df = _compute_bollinger_internal(df)

    # Compute trend for applicable timeframes
    trend_data: dict[int, tuple[float, str]] = {}
    if timeframe in _TREND_TIMEFRAMES:
        trend_data = _compute_trend_slope(df)

    # Compute volume relatif for all timeframes
    vol_rel = _compute_volume_relatif(df)

    for i in range(len(df)):
        ts = df.index[i]

        rsi_val: Decimal | None = None
        bb_upper: Decimal | None = None
        bb_middle: Decimal | None = None
        bb_lower: Decimal | None = None
        pvb: Decimal | None = None

        if rsi_series is not None and not pd.isna(rsi_series.iloc[i]):
            rsi_val = Decimal(str(round(float(rsi_series.iloc[i]), 4)))

        if bb_df is not None and not pd.isna(bb_df["BBU_20_2.0"].iloc[i]):
            bb_upper = Decimal(str(round(float(bb_df["BBU_20_2.0"].iloc[i]), 8)))
            bb_middle = Decimal(str(round(float(bb_df["BBM_20_2.0"].iloc[i]), 8)))
            bb_lower = Decimal(str(round(float(bb_df["BBL_20_2.0"].iloc[i]), 8)))
            pvb = _compute_price_vs_bollinger(
                float(df["close"].iloc[i]),
                float(bb_df["BBU_20_2.0"].iloc[i]),
                float(bb_df["BBL_20_2.0"].iloc[i]),
            )

        slope_val: Decimal | None = None
        trend_type_val: str | None = None
        if i in trend_data:
            slope, ttype = trend_data[i]
            slope_val = Decimal(str(round(slope, 6)))
            trend_type_val = ttype

        metadata: dict[str, object] = {}
        if vol_rel is not None and not pd.isna(vol_rel.iloc[i]):
            metadata["volume_relatif"] = round(float(vol_rel.iloc[i]), 4)

        # Only emit records where at least one indicator was computed
        has_data = any(
            [
                rsi_val is not None,
                bb_upper is not None,
                slope_val is not None,
                metadata.get("volume_relatif") is not None,
            ]
        )
        if not has_data:
            continue

        records.append(
            IndicatorRecord(
                symbol=symbol,
                timeframe=timeframe,
                timestamp=ts.to_pydatetime(),
                rsi=rsi_val,
                bollinger_upper=bb_upper,
                bollinger_middle=bb_middle,
                bollinger_lower=bb_lower,
                price_vs_bollinger=pvb,
                harmonic_pattern=None,  # Deferred to Phase 2
                trend_slope=slope_val,
                trend_type=trend_type_val,
                metadata=metadata,
            )
        )

    logger.info(
        "Computed %d indicator records for %s/%s",
        len(records),
        symbol,
        timeframe,
    )
    return records


def _build_dataframe(rows: list[dict[str, object]]) -> pd.DataFrame:
    """Build a pandas DataFrame from OHLCV row dicts."""
    df = pd.DataFrame(rows)

    required = {"price_open", "price_high", "price_low", "price_close", "timestamp"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"OHLCV data missing required columns: {missing}")

    df = df.rename(
        columns={
            "price_open": "open",
            "price_high": "high",
            "price_low": "low",
            "price_close": "close",
            "volume_24h": "volume",
        }
    )
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.set_index("timestamp")
    for col in ("open", "high", "low", "close", "volume"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def compute_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Compute Relative Strength Index (Wilder's smoothing).

    Args:
        close: Series of closing prices.
        period: Lookback period. Defaults to 14.

    Returns:
        RSI values in range [0, 100]. First ``period`` values are NaN.
    """
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)

    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()

    # When avg_loss is 0, RSI = 100 (all gains). When avg_gain is 0, RSI = 0.
    rsi = pd.Series(np.nan, index=close.index)
    valid = avg_gain.notna() & avg_loss.notna()
    both_zero = valid & (avg_gain == 0) & (avg_loss == 0)
    loss_zero = valid & (avg_loss == 0) & (avg_gain > 0)
    gain_zero = valid & (avg_gain == 0) & (avg_loss > 0)
    normal = valid & (avg_loss > 0) & (avg_gain >= 0)

    rsi[both_zero] = 50.0
    rsi[loss_zero] = 100.0
    rsi[gain_zero] = 0.0
    rs = avg_gain[normal] / avg_loss[normal]
    rsi[normal] = 100.0 - (100.0 / (1.0 + rs))
    return rsi


def compute_bollinger_bands(
    close: pd.Series,
    period: int = 20,
    std_dev: float = 2.0,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Compute Bollinger Bands and return (upper, middle, lower) series.

    Args:
        close: Series of closing prices.
        period: Moving average window. Defaults to 20.
        std_dev: Number of standard deviations. Defaults to 2.0.

    Returns:
        Tuple of (upper, middle, lower) pandas Series.
    """
    middle = close.rolling(window=period).mean()
    rolling_std = close.rolling(window=period).std()
    upper = middle + std_dev * rolling_std
    lower = middle - std_dev * rolling_std
    return upper, middle, lower


def compute_price_vs_bollinger(
    price: float,
    upper: float,
    lower: float,
) -> float:
    """Compute relative position of price within Bollinger Bands.

    Returns value in [-1, +1] where -1 = lower band, 0 = middle, +1 = upper.
    """
    band_width = upper - lower
    if band_width <= 0:
        return 0.0
    midpoint = (upper + lower) / 2
    position = (price - midpoint) / (band_width / 2)
    return max(-1.0, min(1.0, position))


def compute_trend(
    close: pd.Series,
    period: int = 20,
) -> tuple[float, str]:
    """Compute trend slope and type from the last ``period`` closing prices.

    Returns (slope, trend_type) where trend_type is "stable" or "aggressive".
    """
    values = close.dropna().values[-period:]
    if len(values) < period:
        return 0.0, "stable"

    x = np.arange(len(values), dtype=np.float64)
    x_mean = x.mean()
    x_var = ((x - x_mean) ** 2).sum()
    y = values.astype(np.float64)
    y_mean = y.mean()
    slope = float(((x - x_mean) * (y - y_mean)).sum() / x_var) if x_var else 0.0
    normalized = slope / y_mean if y_mean != 0 else 0.0
    trend_type = "stable" if abs(normalized) < 0.005 else "aggressive"
    return normalized, trend_type


def _compute_bollinger_internal(
    df: pd.DataFrame,
    length: int = 20,
    std: float = 2.0,
) -> pd.DataFrame:
    """Compute Bollinger Bands (MA20, 2 std dev)."""
    upper, middle, lower = compute_bollinger_bands(df["close"], period=length, std_dev=std)
    return pd.DataFrame(
        {
            f"BBU_{length}_{std}": upper,
            f"BBM_{length}_{std}": middle,
            f"BBL_{length}_{std}": lower,
        },
        index=df.index,
    )


def _compute_price_vs_bollinger(
    price: float,
    upper: float,
    lower: float,
) -> Decimal | None:
    """Compute relative position of price within Bollinger Bands.

    Returns value in [-1, +1] where:
    - -1 = at or below lower band
    - 0 = at middle band
    - +1 = at or above upper band
    """
    band_width = upper - lower
    if band_width <= 0:
        return None
    midpoint = (upper + lower) / 2
    position = (price - midpoint) / (band_width / 2)
    # Clamp to [-1, 1]
    position = max(-1.0, min(1.0, position))
    return Decimal(str(round(position, 6)))


def _compute_trend_slope(
    df: pd.DataFrame,
    window: int = 20,
) -> dict[int, tuple[float, str]]:
    """Compute trend line slope via linear regression over a rolling window.

    Returns dict mapping row index to (slope, trend_type).
    trend_type is "stable" if abs(slope) < threshold, else "aggressive".
    """
    results: dict[int, tuple[float, str]] = {}
    closes = df["close"].values

    if len(closes) < window:
        return results

    x = np.arange(window, dtype=np.float64)
    x_mean = x.mean()
    x_var = ((x - x_mean) ** 2).sum()

    for i in range(window - 1, len(closes)):
        y = closes[i - window + 1 : i + 1].astype(np.float64)
        if np.any(np.isnan(y)):
            continue
        y_mean = y.mean()
        slope = float(((x - x_mean) * (y - y_mean)).sum() / x_var)

        # Normalize slope by price to get percentage change per candle
        normalized = slope / y_mean if y_mean != 0 else 0.0
        trend_type = "stable" if abs(normalized) < 0.005 else "aggressive"
        results[i] = (normalized, trend_type)

    return results


def _compute_volume_relatif(df: pd.DataFrame, period: int = 20) -> pd.Series | None:
    """Compute volume relative to its 20-period moving average.

    Values > 1 indicate above-average volume.
    """
    if "volume" not in df.columns:
        return None
    vol_ma = df["volume"].rolling(window=period).mean()
    # Guard against division by zero when moving average is 0
    vol_ma = vol_ma.replace(0, np.nan)
    result = df["volume"] / vol_ma
    return result
