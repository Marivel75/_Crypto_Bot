"""Tests pour frontend/utils.py — extract_timeframes, extract_symbols, fmt_ts."""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from frontend.utils import extract_timeframes, extract_symbols, fmt_ts


# ---------------------------------------------------------------------------
# extract_timeframes
# ---------------------------------------------------------------------------

class TestExtractTimeframes:
    def _data(self, timeframes):
        return [{"symbol": "BTC/USDT", "timeframe": tf, "exchange": "binance", "count": 1}
                for tf in timeframes]

    def test_returns_sorted_canonical_order(self):
        data = self._data(["1d", "1h", "4h"])
        assert extract_timeframes(data) == ["1h", "4h", "1d"]

    def test_deduplicates(self):
        data = self._data(["1h", "1h", "1d"])
        assert extract_timeframes(data) == ["1h", "1d"]

    def test_empty_input(self):
        assert extract_timeframes([]) == []

    def test_unknown_timeframe_goes_last(self):
        data = self._data(["1d", "custom"])
        result = extract_timeframes(data)
        assert result[-1] == "custom"
        assert "1d" in result

    def test_skips_missing_timeframe_key(self):
        data = [{"symbol": "BTC/USDT", "exchange": "binance", "count": 1}]
        assert extract_timeframes(data) == []

    def test_full_canonical_order(self):
        tfs = ["1w", "1d", "4h", "1h", "15m", "5m", "1m"]
        data = self._data(tfs)
        result = extract_timeframes(data)
        assert result == ["1m", "5m", "15m", "1h", "4h", "1d", "1w"]


# ---------------------------------------------------------------------------
# extract_symbols
# ---------------------------------------------------------------------------

class TestExtractSymbols:
    def _data(self, symbols):
        return [{"symbol": s, "timeframe": "1d", "exchange": "binance", "count": 1}
                for s in symbols]

    def test_returns_sorted_alphabetically(self):
        data = self._data(["ETH/USDT", "BTC/USDT", "ADA/USDT"])
        assert extract_symbols(data) == ["ADA/USDT", "BTC/USDT", "ETH/USDT"]

    def test_deduplicates(self):
        data = self._data(["BTC/USDT", "BTC/USDT", "ETH/USDT"])
        assert extract_symbols(data) == ["BTC/USDT", "ETH/USDT"]

    def test_empty_input(self):
        assert extract_symbols([]) == []

    def test_skips_missing_symbol_key(self):
        data = [{"timeframe": "1d", "exchange": "binance", "count": 1}]
        assert extract_symbols(data) == []

    def test_mixed_symbols_and_timeframes(self):
        data = [
            {"symbol": "BTC/USDT", "timeframe": "1h", "exchange": "binance", "count": 100},
            {"symbol": "BTC/USDT", "timeframe": "1d", "exchange": "binance", "count": 365},
            {"symbol": "ETH/USDT", "timeframe": "1d", "exchange": "kraken",  "count": 200},
        ]
        assert extract_symbols(data) == ["BTC/USDT", "ETH/USDT"]


# ---------------------------------------------------------------------------
# fmt_ts
# ---------------------------------------------------------------------------

class TestFmtTs:
    def test_daily_midnight_returns_date_only(self):
        assert fmt_ts("2026-04-25T00:00:00") == "2026-04-25"

    def test_daily_with_microseconds_returns_date_only(self):
        assert fmt_ts("2026-04-25 00:00:00.000000") == "2026-04-25"

    def test_intraday_1h_returns_date_and_time(self):
        assert fmt_ts("2026-04-25T10:00:00") == "2026-04-25 10:00"

    def test_intraday_4h_returns_date_and_time(self):
        assert fmt_ts("2026-04-25T08:00:00") == "2026-04-25 08:00"

    def test_strips_T_separator(self):
        result = fmt_ts("2026-04-25T14:30:00")
        assert "T" not in result

    def test_none_returns_empty_string(self):
        assert fmt_ts(None) == ""

    def test_empty_string_returns_empty_string(self):
        assert fmt_ts("") == ""

    def test_strips_timezone_suffix(self):
        assert fmt_ts("2026-04-25T10:00:00+02:00") == "2026-04-25 10:00"

    def test_strips_z_suffix(self):
        assert fmt_ts("2026-04-25T10:00:00Z") == "2026-04-25 10:00"
