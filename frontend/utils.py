"""Shared helpers for the Streamlit frontend."""

from __future__ import annotations

from typing import Any

# Canonical ordering for timeframe sorting.
_TF_ORDER: dict[str, int] = {
    "1m": 0, "3m": 1, "5m": 2, "15m": 3, "30m": 4,
    "1h": 5, "2h": 6, "4h": 7, "8h": 8, "12h": 9,
    "1d": 10, "3d": 11, "1w": 12, "1M": 13,
}


def extract_timeframes(symbols_data: list[dict[str, Any]]) -> list[str]:
    """Return the sorted unique timeframes present in /ohlcv/symbols data."""
    tfs = {d["timeframe"] for d in symbols_data if d.get("timeframe")}
    return sorted(tfs, key=lambda x: _TF_ORDER.get(x, 99))


def extract_symbols(symbols_data: list[dict[str, Any]]) -> list[str]:
    """Return the sorted unique symbols present in /ohlcv/symbols data."""
    syms = {d["symbol"] for d in symbols_data if d.get("symbol")}
    return sorted(syms)
