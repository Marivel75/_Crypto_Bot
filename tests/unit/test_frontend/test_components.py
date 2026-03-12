"""Tests for frontend components — pure logic and Plotly figure generation."""

from __future__ import annotations

import plotly.graph_objects as go

from src.frontend.components.candlestick import _DARK_LAYOUT, render_candlestick
from src.frontend.components.indicators import _safe_float
from src.frontend.components.news_feed import render_sentiment_chart, render_word_cloud


class TestCandlestick:
    """Test candlestick chart rendering."""

    def test_empty_data_returns_empty_figure(self) -> None:
        fig = render_candlestick([], symbol="BTC", timeframe="4h")
        assert isinstance(fig, go.Figure)
        assert "Aucune donn" in fig.layout.title.text

    def test_renders_with_ohlcv_data(self) -> None:
        ohlcv = [
            {
                "timestamp": "2025-01-01T00:00:00",
                "price_open": 100.0,
                "price_high": 110.0,
                "price_low": 95.0,
                "price_close": 105.0,
                "volume_24h": 1000.0,
            },
            {
                "timestamp": "2025-01-01T04:00:00",
                "price_open": 105.0,
                "price_high": 115.0,
                "price_low": 100.0,
                "price_close": 110.0,
                "volume_24h": 1200.0,
            },
        ]
        fig = render_candlestick(ohlcv, symbol="BTC", timeframe="4h")
        assert isinstance(fig, go.Figure)
        # Should have candlestick + volume bar = at least 2 traces
        assert len(fig.data) >= 2

    def test_renders_with_bollinger_overlay(self) -> None:
        ohlcv = [
            {
                "timestamp": "2025-01-01",
                "price_open": 100,
                "price_high": 110,
                "price_low": 95,
                "price_close": 105,
                "volume_24h": 1000,
            },
        ]
        indicators = {
            "bollinger_upper": 112.0,
            "bollinger_middle": 105.0,
            "bollinger_lower": 98.0,
        }
        fig = render_candlestick(ohlcv, indicators=indicators, symbol="ETH", timeframe="1h")
        assert isinstance(fig, go.Figure)
        # Candlestick + volume + 3 BB lines = 5 traces
        assert len(fig.data) == 5

    def test_dark_layout_has_required_keys(self) -> None:
        assert "template" in _DARK_LAYOUT
        assert _DARK_LAYOUT["template"] == "plotly_dark"
        assert "paper_bgcolor" in _DARK_LAYOUT
        assert "plot_bgcolor" in _DARK_LAYOUT


class TestSafeFloat:
    """Test the _safe_float helper from indicators module."""

    def test_valid_float(self) -> None:
        assert _safe_float(3.14) == 3.14

    def test_valid_int(self) -> None:
        assert _safe_float(42) == 42.0

    def test_valid_string(self) -> None:
        assert _safe_float("2.5") == 2.5

    def test_none_returns_none(self) -> None:
        assert _safe_float(None) is None

    def test_invalid_string_returns_none(self) -> None:
        assert _safe_float("not_a_number") is None

    def test_empty_string_returns_none(self) -> None:
        assert _safe_float("") is None


class TestSentimentChart:
    """Test sentiment chart generation."""

    def test_returns_none_on_empty_data(self) -> None:
        assert render_sentiment_chart(None) is None
        assert render_sentiment_chart([]) is None

    def test_returns_figure_with_data(self) -> None:
        data = [
            {"symbol": "BTC", "sentiment_score": 0.72},
            {"symbol": "ETH", "sentiment_score": -0.15},
        ]
        fig = render_sentiment_chart(data)
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 1  # Single bar trace


class TestWordCloud:
    """Test word cloud generation."""

    def test_returns_none_on_empty_data(self) -> None:
        assert render_word_cloud(None) is None
        assert render_word_cloud([]) is None

    def test_returns_figure_with_data(self) -> None:
        keywords = [
            {"word": "ETF", "count": 15},
            {"word": "SEC", "count": 10},
            {"word": "halving", "count": 8},
        ]
        fig = render_word_cloud(keywords)
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 1  # Single scatter trace
