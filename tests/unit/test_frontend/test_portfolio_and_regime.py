"""Tests for portfolio chart and regime badge components."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import plotly.graph_objects as go
import pytest

from src.frontend.components.portfolio_charts import (
    render_portfolio_history_chart,
    render_portfolio_pie,
)
from src.frontend.components.regime_badge import render_regime_badge


class TestPortfolioPie:
    """Test portfolio asset allocation pie chart rendering."""

    @patch("src.frontend.components.portfolio_charts.st")
    def test_empty_allocation_shows_info_message(self, mock_st: MagicMock) -> None:
        """Empty allocation dict should display info message."""
        render_portfolio_pie({})
        mock_st.info.assert_called_once()

    @patch("src.frontend.components.portfolio_charts.st")
    def test_none_allocation_shows_info_message(self, mock_st: MagicMock) -> None:
        """None allocation should display info message."""
        render_portfolio_pie(None)
        mock_st.info.assert_called_once()

    @patch("src.frontend.components.portfolio_charts.st")
    def test_single_asset_allocation_renders_pie(self, mock_st: MagicMock) -> None:
        """Single asset allocation should render pie chart."""
        allocation = {"BTC": 5000.0}
        render_portfolio_pie(allocation)
        mock_st.plotly_chart.assert_called_once()
        fig = mock_st.plotly_chart.call_args[0][0]
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 1
        assert fig.data[0].labels == ("BTC",)
        assert fig.data[0].values == (5000.0,)

    @patch("src.frontend.components.portfolio_charts.st")
    def test_multiple_assets_allocation_renders_pie(self, mock_st: MagicMock) -> None:
        """Multiple assets should render pie chart with all symbols."""
        allocation = {"BTC": 5000.0, "ETH": 3000.0, "SOL": 2000.0}
        render_portfolio_pie(allocation)
        mock_st.plotly_chart.assert_called_once()
        fig = mock_st.plotly_chart.call_args[0][0]
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 1
        # Order is dict insertion order (Python 3.7+)
        assert set(fig.data[0].labels) == {"BTC", "ETH", "SOL"}
        assert sum(fig.data[0].values) == pytest.approx(10000.0)

    @patch("src.frontend.components.portfolio_charts.st")
    def test_pie_chart_uses_dark_layout(self, mock_st: MagicMock) -> None:
        """Pie chart should use dark theme layout."""
        allocation = {"BTC": 5000.0}
        render_portfolio_pie(allocation)
        fig = mock_st.plotly_chart.call_args[0][0]
        assert fig.layout.template == "plotly_dark"
        assert fig.layout.paper_bgcolor == "#0e1117"

    @patch("src.frontend.components.portfolio_charts.st")
    def test_pie_chart_height_set(self, mock_st: MagicMock) -> None:
        """Pie chart should have correct height."""
        allocation = {"BTC": 5000.0}
        render_portfolio_pie(allocation)
        fig = mock_st.plotly_chart.call_args[0][0]
        assert fig.layout.height == 350

    @patch("src.frontend.components.portfolio_charts.st")
    def test_pie_chart_marker_colors_cycling(self, mock_st: MagicMock) -> None:
        """Pie chart should cycle through color palette."""
        allocation = {
            "BTC": 5000.0,
            "ETH": 3000.0,
            "SOL": 2000.0,
            "ADA": 1000.0,
        }
        render_portfolio_pie(allocation)
        fig = mock_st.plotly_chart.call_args[0][0]
        # Should use first 4 colors from palette
        assert len(fig.data[0].marker.colors) == 4

    @patch("src.frontend.components.portfolio_charts.st")
    def test_large_allocation_with_many_assets(self, mock_st: MagicMock) -> None:
        """Pie chart should handle many assets gracefully."""
        allocation = {f"ASSET{i}": 1000.0 * (i + 1) for i in range(10)}
        render_portfolio_pie(allocation)
        fig = mock_st.plotly_chart.call_args[0][0]
        assert len(fig.data[0].labels) == 10
        assert sum(fig.data[0].values) == pytest.approx(55000.0)

    @patch("src.frontend.components.portfolio_charts.st")
    def test_zero_value_assets_included(self, mock_st: MagicMock) -> None:
        """Assets with zero value should still be included."""
        allocation = {"BTC": 5000.0, "ETH": 0.0}
        render_portfolio_pie(allocation)
        fig = mock_st.plotly_chart.call_args[0][0]
        assert len(fig.data[0].labels) == 2


class TestPortfolioHistoryChart:
    """Test portfolio value history line chart rendering."""

    @patch("src.frontend.components.portfolio_charts.st")
    def test_empty_history_shows_info_message(self, mock_st: MagicMock) -> None:
        """Empty history list should display info message."""
        render_portfolio_history_chart([])
        mock_st.info.assert_called_once()

    @patch("src.frontend.components.portfolio_charts.st")
    def test_none_history_shows_info_message(self, mock_st: MagicMock) -> None:
        """None history should display info message."""
        render_portfolio_history_chart(None)
        mock_st.info.assert_called_once()

    @patch("src.frontend.components.portfolio_charts.st")
    def test_single_point_history_renders_chart(self, mock_st: MagicMock) -> None:
        """Single data point should render line chart."""
        history = [{"timestamp": "2025-01-01", "total_value": 5000.0}]
        render_portfolio_history_chart(history)
        mock_st.plotly_chart.assert_called_once()
        fig = mock_st.plotly_chart.call_args[0][0]
        assert isinstance(fig, go.Figure)
        assert len(fig.data) == 1
        assert len(fig.data[0].x) == 1
        assert fig.data[0].y[0] == pytest.approx(5000.0)

    @patch("src.frontend.components.portfolio_charts.st")
    def test_multiple_points_history_renders_chart(self, mock_st: MagicMock) -> None:
        """Multiple data points should render line chart."""
        history = [
            {"timestamp": "2025-01-01", "total_value": 5000.0},
            {"timestamp": "2025-01-02", "total_value": 5500.0},
            {"timestamp": "2025-01-03", "total_value": 5200.0},
        ]
        render_portfolio_history_chart(history)
        fig = mock_st.plotly_chart.call_args[0][0]
        assert len(fig.data[0].x) == 3
        assert len(fig.data[0].y) == 3
        assert fig.data[0].y == (5000.0, 5500.0, 5200.0)

    @patch("src.frontend.components.portfolio_charts.st")
    def test_history_with_invalid_values_filtered(self, mock_st: MagicMock) -> None:
        """History records with missing fields should be skipped."""
        history = [
            {"timestamp": "2025-01-01", "total_value": 5000.0},
            {"timestamp": "2025-01-02"},  # Missing total_value
            {"total_value": 5200.0},  # Missing timestamp
            {"timestamp": "2025-01-03", "total_value": 5300.0},
        ]
        render_portfolio_history_chart(history)
        fig = mock_st.plotly_chart.call_args[0][0]
        # Only valid records should be included
        assert len(fig.data[0].x) == 2
        assert len(fig.data[0].y) == 2

    @patch("src.frontend.components.portfolio_charts.st")
    def test_history_with_non_numeric_values_filtered(self, mock_st: MagicMock) -> None:
        """History records with non-numeric values should be skipped."""
        history = [
            {"timestamp": "2025-01-01", "total_value": 5000.0},
            {"timestamp": "2025-01-02", "total_value": "invalid"},
            {"timestamp": "2025-01-03", "total_value": 5300.0},
        ]
        render_portfolio_history_chart(history)
        fig = mock_st.plotly_chart.call_args[0][0]
        assert len(fig.data[0].x) == 2

    @patch("src.frontend.components.portfolio_charts.st")
    def test_positive_performance_uses_green_color(self, mock_st: MagicMock) -> None:
        """Positive net gain should use green color."""
        history = [
            {"timestamp": "2025-01-01", "total_value": 5000.0},
            {"timestamp": "2025-01-02", "total_value": 5500.0},  # Gain
        ]
        render_portfolio_history_chart(history)
        fig = mock_st.plotly_chart.call_args[0][0]
        # Green color for positive performance
        assert fig.data[0].line.color == "#26a69a"
        assert fig.data[0].fillcolor == "rgba(38,166,154,0.1)"

    @patch("src.frontend.components.portfolio_charts.st")
    def test_negative_performance_uses_red_color(self, mock_st: MagicMock) -> None:
        """Negative net loss should use red color."""
        history = [
            {"timestamp": "2025-01-01", "total_value": 5500.0},
            {"timestamp": "2025-01-02", "total_value": 5000.0},  # Loss
        ]
        render_portfolio_history_chart(history)
        fig = mock_st.plotly_chart.call_args[0][0]
        # Red color for negative performance
        assert fig.data[0].line.color == "#ef5350"
        assert fig.data[0].fillcolor == "rgba(239,83,80,0.1)"

    @patch("src.frontend.components.portfolio_charts.st")
    def test_flat_performance_uses_green_color(self, mock_st: MagicMock) -> None:
        """No change should use green color (default)."""
        history = [
            {"timestamp": "2025-01-01", "total_value": 5000.0},
            {"timestamp": "2025-01-02", "total_value": 5000.0},  # No change
        ]
        render_portfolio_history_chart(history)
        fig = mock_st.plotly_chart.call_args[0][0]
        assert fig.data[0].line.color == "#26a69a"

    @patch("src.frontend.components.portfolio_charts.st")
    def test_chart_uses_dark_layout(self, mock_st: MagicMock) -> None:
        """Chart should use dark theme layout."""
        history = [{"timestamp": "2025-01-01", "total_value": 5000.0}]
        render_portfolio_history_chart(history)
        fig = mock_st.plotly_chart.call_args[0][0]
        assert fig.layout.template == "plotly_dark"
        assert fig.layout.paper_bgcolor == "#0e1117"

    @patch("src.frontend.components.portfolio_charts.st")
    def test_chart_height_set(self, mock_st: MagicMock) -> None:
        """Chart should have correct height."""
        history = [{"timestamp": "2025-01-01", "total_value": 5000.0}]
        render_portfolio_history_chart(history)
        fig = mock_st.plotly_chart.call_args[0][0]
        assert fig.layout.height == 350

    @patch("src.frontend.components.portfolio_charts.st")
    def test_chart_axes_labeled(self, mock_st: MagicMock) -> None:
        """Chart should have labeled axes."""
        history = [{"timestamp": "2025-01-01", "total_value": 5000.0}]
        render_portfolio_history_chart(history)
        fig = mock_st.plotly_chart.call_args[0][0]
        assert fig.layout.xaxis.title.text is not None
        assert fig.layout.yaxis.title.text is not None

    @patch("src.frontend.components.portfolio_charts.st")
    def test_all_valid_records_with_mixed_precision(self, mock_st: MagicMock) -> None:
        """History should handle values with different numeric precision."""
        history = [
            {"timestamp": "2025-01-01", "total_value": 5000},  # int
            {"timestamp": "2025-01-02", "total_value": 5100.5},  # float
            {"timestamp": "2025-01-03", "total_value": "5200.75"},  # string (should convert)
        ]
        render_portfolio_history_chart(history)
        fig = mock_st.plotly_chart.call_args[0][0]
        assert len(fig.data[0].y) == 3


class TestRegimeBadge:
    """Test market regime badge rendering."""

    @patch("src.frontend.components.regime_badge.st")
    def test_bull_regime_renders_correct_badge(self, mock_st: MagicMock) -> None:
        """Bull regime should render with bull styling."""
        render_regime_badge("BULL")
        mock_st.markdown.assert_called_once()
        html = mock_st.markdown.call_args[0][0]
        assert "#26a69a" in html  # Bull color
        assert "📈" in html  # Bull icon

    @patch("src.frontend.components.regime_badge.st")
    def test_bear_regime_renders_correct_badge(self, mock_st: MagicMock) -> None:
        """Bear regime should render with bear styling."""
        render_regime_badge("BEAR")
        mock_st.markdown.assert_called_once()
        html = mock_st.markdown.call_args[0][0]
        assert "#ef5350" in html  # Bear color
        assert "📉" in html  # Bear icon

    @patch("src.frontend.components.regime_badge.st")
    def test_sideways_regime_renders_correct_badge(self, mock_st: MagicMock) -> None:
        """Sideways regime should render with sideways styling."""
        render_regime_badge("SIDEWAYS")
        mock_st.markdown.assert_called_once()
        html = mock_st.markdown.call_args[0][0]
        assert "#ffeb3b" in html  # Sideways color
        assert "➡️" in html  # Sideways icon

    @patch("src.frontend.components.regime_badge.st")
    def test_none_regime_defaults_to_sideways(self, mock_st: MagicMock) -> None:
        """None regime should default to SIDEWAYS."""
        render_regime_badge(None)
        mock_st.markdown.assert_called_once()
        html = mock_st.markdown.call_args[0][0]
        assert "#ffeb3b" in html  # Sideways color

    @patch("src.frontend.components.regime_badge.st")
    def test_lowercase_regime_converted_to_uppercase(self, mock_st: MagicMock) -> None:
        """Lowercase regime input should be converted to uppercase."""
        render_regime_badge("bull")
        mock_st.markdown.assert_called_once()
        html = mock_st.markdown.call_args[0][0]
        assert "#26a69a" in html  # Bull color

    @patch("src.frontend.components.regime_badge.st")
    def test_mixed_case_regime_converted(self, mock_st: MagicMock) -> None:
        """Mixed case regime should be converted to uppercase."""
        render_regime_badge("BeAr")
        mock_st.markdown.assert_called_once()
        html = mock_st.markdown.call_args[0][0]
        assert "#ef5350" in html  # Bear color

    @patch("src.frontend.components.regime_badge.st")
    @patch("src.frontend.components.regime_badge.logger")
    def test_unknown_regime_defaults_to_sideways_with_warning(self, mock_logger: MagicMock, mock_st: MagicMock) -> None:
        """Unknown regime should default to SIDEWAYS and log warning."""
        render_regime_badge("UNKNOWN")
        mock_logger.warning.assert_called_once()
        html = mock_st.markdown.call_args[0][0]
        assert "#ffeb3b" in html  # Sideways color

    @patch("src.frontend.components.regime_badge.st")
    def test_badge_has_border_styling(self, mock_st: MagicMock) -> None:
        """Badge should have proper border styling."""
        render_regime_badge("BULL")
        html = mock_st.markdown.call_args[0][0]
        assert "border: 2px solid" in html
        assert "border-radius: 8px" in html

    @patch("src.frontend.components.regime_badge.st")
    def test_badge_has_padding(self, mock_st: MagicMock) -> None:
        """Badge should have proper padding."""
        render_regime_badge("BULL")
        html = mock_st.markdown.call_args[0][0]
        assert "padding: 12px 16px" in html

    @patch("src.frontend.components.regime_badge.st")
    def test_badge_uses_unsafe_html(self, mock_st: MagicMock) -> None:
        """Badge rendering should use unsafe_allow_html=True."""
        render_regime_badge("BULL")
        assert mock_st.markdown.call_args[1]["unsafe_allow_html"] is True

    @patch("src.frontend.components.regime_badge.st")
    def test_all_regime_types_render_without_error(self, mock_st: MagicMock) -> None:
        """All three regime types should render successfully."""
        for regime in ["BULL", "BEAR", "SIDEWAYS"]:
            mock_st.reset_mock()
            render_regime_badge(regime)
            assert mock_st.markdown.called
