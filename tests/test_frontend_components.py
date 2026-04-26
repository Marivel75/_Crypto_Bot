"""Tests pour frontend/components/ — fonctions pures + figure Plotly."""

import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import plotly.graph_objects as go

from frontend.components.candlestick import render_candlestick, _compute_macd_crosses
from frontend.components.indicators import (
    _rsi_label,
    _bb_position_label,
    _macd_label,
    _safe_float,
)


# ---------------------------------------------------------------------------
# _compute_macd_crosses
# ---------------------------------------------------------------------------

class TestComputeMacdCrosses:
    def test_detects_bullish_cross(self):
        # MACD passe au-dessus du signal entre i=1 et i=2
        ml = [1.0, 1.0, 2.0, 2.5]
        ms = [1.5, 1.5, 1.8, 1.8]
        buy, sell = _compute_macd_crosses(ml, ms)
        assert 2 in buy
        assert sell == []

    def test_detects_bearish_cross(self):
        ml = [2.0, 2.0, 1.0, 0.5]
        ms = [1.5, 1.5, 1.8, 1.8]
        buy, sell = _compute_macd_crosses(ml, ms)
        assert 2 in sell
        assert buy == []

    def test_no_cross_returns_empty(self):
        ml = [1.0, 1.0, 1.0]
        ms = [2.0, 2.0, 2.0]
        buy, sell = _compute_macd_crosses(ml, ms)
        assert buy == []
        assert sell == []

    def test_none_values_are_skipped(self):
        ml = [None, None, 2.0, 2.5]
        ms = [None, None, 1.5, 1.5]
        buy, sell = _compute_macd_crosses(ml, ms)
        assert buy == []
        assert sell == []

    def test_multiple_crosses(self):
        ml     = [1.0, 2.0, 1.5, 0.5, 1.5]
        ms     = [1.5, 1.8, 1.8, 0.8, 0.5]
        buy, sell = _compute_macd_crosses(ml, ms)
        assert len(buy) >= 1
        assert len(sell) >= 1

    def test_single_element_returns_empty(self):
        buy, sell = _compute_macd_crosses([1.0], [0.5])
        assert buy == []
        assert sell == []

    def test_empty_lists_return_empty(self):
        buy, sell = _compute_macd_crosses([], [])
        assert buy == []
        assert sell == []


# ---------------------------------------------------------------------------
# render_candlestick
# ---------------------------------------------------------------------------

def _make_candle(i: int, ts: str = "2026-04-01T00:00:00") -> dict:
    return {
        "timestamp": ts,
        "open": 60000.0 + i,
        "high": 61000.0 + i,
        "low":  59000.0 + i,
        "close": 60500.0 + i,
        "volume": 1000.0 + i,
        "sma_20": 60200.0 + i,
        "sma_50": 59800.0 + i if i >= 30 else None,
        "ema_20": 60300.0 + i,
        "bb_upper": 62000.0 + i,
        "bb_middle": 60000.0 + i,
        "bb_lower": 58000.0 + i,
        "macd_line": 100.0 + i * 0.5,
        "macd_signal": 95.0 + i * 0.5,
    }


class TestRenderCandlestick:
    def test_returns_figure(self):
        data = [_make_candle(i) for i in range(30)]
        fig = render_candlestick(data, "BTC/USDT", "1d")
        assert isinstance(fig, go.Figure)

    def test_empty_data_returns_figure_with_annotation(self):
        fig = render_candlestick([], "BTC/USDT", "1d")
        assert isinstance(fig, go.Figure)
        assert len(fig.layout.annotations) > 0

    def test_candlestick_trace_present(self):
        data = [_make_candle(i) for i in range(10)]
        fig = render_candlestick(data)
        trace_types = [t.type for t in fig.data]
        assert "candlestick" in trace_types

    def test_volume_bar_trace_present(self):
        data = [_make_candle(i) for i in range(10)]
        fig = render_candlestick(data)
        trace_types = [t.type for t in fig.data]
        assert "bar" in trace_types

    def test_sma_traces_added(self):
        data = [_make_candle(i) for i in range(30)]
        fig = render_candlestick(data)
        names = [t.name for t in fig.data]
        assert "SMA 20" in names

    def test_bb_traces_added(self):
        data = [_make_candle(i) for i in range(20)]
        fig = render_candlestick(data)
        names = [t.name for t in fig.data]
        assert "BB Upper" in names
        assert "BB Lower" in names

    def test_macd_cross_markers_added_on_cross(self):
        # Force un croisement haussier entre candle 1 et 2
        data = [_make_candle(i) for i in range(5)]
        data[0]["macd_line"] = 90.0;  data[0]["macd_signal"] = 95.0
        data[1]["macd_line"] = 90.0;  data[1]["macd_signal"] = 95.0
        data[2]["macd_line"] = 100.0; data[2]["macd_signal"] = 95.0  # cross up
        fig = render_candlestick(data)
        names = [t.name for t in fig.data]
        assert any("MACD Cross" in (n or "") for n in names)

    def test_title_contains_symbol_and_timeframe(self):
        data = [_make_candle(i) for i in range(5)]
        fig = render_candlestick(data, "ETH/USDT", "4h")
        assert "ETH/USDT" in fig.layout.title.text
        assert "4h" in fig.layout.title.text

    def test_no_crash_with_none_indicator_values(self):
        data = [_make_candle(i) for i in range(5)]
        for row in data:
            row["bb_upper"] = None
            row["macd_line"] = None
            row["macd_signal"] = None
        fig = render_candlestick(data)
        assert isinstance(fig, go.Figure)


# ---------------------------------------------------------------------------
# _safe_float
# ---------------------------------------------------------------------------

class TestSafeFloat:
    def test_converts_int(self):
        assert _safe_float(42) == 42.0

    def test_converts_string(self):
        assert _safe_float("3.14") == 3.14

    def test_none_returns_none(self):
        assert _safe_float(None) is None

    def test_invalid_string_returns_none(self):
        assert _safe_float("abc") is None


# ---------------------------------------------------------------------------
# _rsi_label
# ---------------------------------------------------------------------------

class TestRsiLabel:
    def test_overbought_above_70(self):
        label = _rsi_label(75.0)
        assert "surach" in label.lower()

    def test_oversold_below_30(self):
        label = _rsi_label(25.0)
        assert "surv" in label.lower()

    def test_neutral_between_30_and_70(self):
        label = _rsi_label(50.0)
        assert "neutre" in label.lower()

    def test_boundary_exactly_70_is_overbought(self):
        label = _rsi_label(70.0)
        assert "surach" in label.lower()

    def test_boundary_exactly_30_is_oversold(self):
        label = _rsi_label(30.0)
        assert "surv" in label.lower()


# ---------------------------------------------------------------------------
# _bb_position_label
# ---------------------------------------------------------------------------

class TestBbPositionLabel:
    def test_above_upper_band(self):
        label = _bb_position_label(close=65000, bb_upper=63000, bb_lower=57000)
        assert "dessus" in label.lower()

    def test_near_upper_band(self):
        label = _bb_position_label(close=62500, bb_upper=63000, bb_lower=57000)
        assert "sup" in label.lower()

    def test_below_lower_band(self):
        label = _bb_position_label(close=55000, bb_upper=63000, bb_lower=57000)
        assert "inf" in label.lower()

    def test_near_lower_band(self):
        label = _bb_position_label(close=57500, bb_upper=63000, bb_lower=57000)
        assert "inf" in label.lower()

    def test_middle_band(self):
        label = _bb_position_label(close=60000, bb_upper=63000, bb_lower=57000)
        assert "milieu" in label.lower()

    def test_zero_width_band_returns_middle(self):
        label = _bb_position_label(close=60000, bb_upper=60000, bb_lower=60000)
        assert "milieu" in label.lower()


# ---------------------------------------------------------------------------
# _macd_label
# ---------------------------------------------------------------------------

class TestMacdLabel:
    def test_bullish_when_line_above_signal(self):
        label = _macd_label(macd_line=1.5, macd_signal=1.0)
        assert "haussier" in label.lower()

    def test_bearish_when_line_below_signal(self):
        label = _macd_label(macd_line=0.8, macd_signal=1.0)
        assert "baissier" in label.lower()

    def test_neutral_when_equal(self):
        label = _macd_label(macd_line=1.0, macd_signal=1.0)
        assert "neutre" in label.lower()
